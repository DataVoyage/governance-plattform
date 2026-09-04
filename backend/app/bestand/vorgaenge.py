"""Aufbauschritt 6: Selbstverpflichtungen, Gates, Aktivierung, Lenkung.

Hier bekommt der Bestand seine Bewegung. Ein Prozessobjekt wird nicht durch
einen Statuswechsel aktiv, sondern durch eine Kette: bewerten, erklaeren, ab
Tier 3 durch Gate 1 gehen — und erst dann. Diese Reihenfolge steht so in A.10.5
und A.11, und sie steht auch hier so, weil ein Bestand, der sie umgeht, ueber
die Anwendung nichts aussagt.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy import select

from app.bestand import bewertungen as bewertungen_schritt
from app.bestand.kontext import Kontext
from app.bestand.prozesse import handelnder
from app.bestand.werkzeuge import WERKZEUGE
from app.models.audit import Konfiguration
from app.models.enums import (
    Aufloesungsart,
    Befundart,
    Gate2Ausloeser,
    GateStatus,
    GateTyp,
    Klassenbewertung,
    SelbstverpflichtungTyp,
)
from app.schemas.prozess import ProzessAendern
from app.services import asset, gate, klassen, konfiguration, lenkung
from app.services import prozess as prozess_service
from app.services import selbstverpflichtung as verpflichtung
from app.services.changelog import protokolliere_aenderung, snapshot

#: Prozessobjekte, zu denen der Eigner (noch) keine Erklaerung abgegeben hat.
OHNE_ERKLAERUNG: frozenset[str] = frozenset(
    {
        "eigenmarkenkalkulation",
        "sortimentsveroeffentlichung",
        "bauprojektsteuerung",
        "werbemittelplanung-prozess",
        "lieferantenaudit",
        "anlagenzugaenge",
        "befragungsauswertung",
    }
)

#: Erklaerungen, in denen eine verlangte Aussage offen geblieben ist. Sie sind
#: damit unvollstaendig — und ab Tier 3 ist das ein Aktivierungshindernis.
UNVOLLSTAENDIG: dict[str, str] = {
    "abschriftensteuerung": "PE5",
    "hygienekontrolle": "PE3",
    "regalpflege": "PE2",
}

#: Kommentare der Prozesseigner zu einzelnen Aussagen — nicht Pflicht, aber
#: das, was eine Erklaerung von einem Haken unterscheidet.
KOMMENTARE: dict[str, dict[str, str]] = {
    "entgeltlauf": {
        "PE4": "Die Abrechnung wird nicht zur Bewertung Einzelner verwendet; "
        "Auswertungen erfolgen ausschließlich aggregiert je Gesellschaft.",
    },
    "kundenkartenprogramm": {
        "PE3": "Empfänger sind ausschließlich die Kundin oder der Kunde selbst "
        "sowie der Versanddienstleister nach Auftragsverarbeitungsvertrag.",
    },
    "bestellvorschlag": {
        "PE2": "Über die drei referenzierten Datenobjekte hinaus werden keine "
        "Quellen gelesen; der Wetterdienst wurde 2025 wieder abgeschaltet.",
    },
}

#: Gate 1 ist ab Tier 3 die Erstfreigabe. Wo nichts steht, wurde freigegeben.
GATE1_AUSGANG: dict[str, tuple[str, str]] = {
    "bewerbervorauswahl": (
        GateStatus.IN_PRUEFUNG,
        "Die Datenschutz-Folgenabschätzung liegt vor, die Stellungnahme des "
        "Betriebsrats steht noch aus.",
    ),
    "couponsteuerung": (
        GateStatus.ABGELEHNT,
        "Die Zielgruppenbildung greift auf die vollständige Kaufhistorie zu. "
        "Vor einer Freigabe ist der Verarbeitungszweck einzugrenzen und die "
        "Aufbewahrungsdauer zu begrenzen.",
    ),
    "leistungsdialog": (
        GateStatus.EINGEREICHT,
        "Eingereicht, Prüfung durch die Governance noch nicht begonnen.",
    ),
}

#: Prozessobjekte, die nach der Freigabe nicht aktiv wurden.
BLEIBT_ENTWURF: frozenset[str] = frozenset(
    {
        "abschriftensteuerung",
        "befragungsauswertung",
        "bewerbervorauswahl",
        "couponsteuerung",
        "emotionsanalyse-kasse",
        "energiemonitoring",
        "leistungsdialog",
        "retourensteuerung-nonfood",
    }
)

#: Prozessobjekte, die es gab und die abgeloest wurden.
STILLGELEGT: dict[str, int] = {"filialbesuche": 70, "eigenmarkenkalkulation": 130}


@dataclass(frozen=True)
class Gate2:
    """Ein Gate-2-Vorgang mit einem der fuenf Ausloeser aus A.11."""

    prozess: str
    ausloeser: str
    begruendung: str
    vor_tagen: int
    ausgang: str | None = None
    kommentar: str = ""


GATE2_VORGAENGE: tuple[Gate2, ...] = (
    Gate2(
        "frischedisposition",
        Gate2Ausloeser.NEUE_DATENKATEGORIE,
        "Die Prognose soll künftig die Kassenbondaten mit Kartenbezug lesen, um "
        "Bedarfsspitzen je Filiale genauer zu treffen. Damit kommt eine "
        "personenbezogene Kategorie hinzu.",
        vor_tagen=175,
        ausgang=GateStatus.FREIGEGEBEN,
        kommentar="Freigegeben unter der Auflage, dass nur aggregierte Tageswerte "
        "gelesen werden und kein Kartenbezug in die Prognose eingeht.",
    ),
    Gate2(
        "preisauszeichnung",
        Gate2Ausloeser.REICHWEITENERWEITERUNG,
        "Die Preisauszeichnung wird von zwei auf sieben Landesgesellschaften ausgeweitet.",
        vor_tagen=120,
        ausgang=GateStatus.IN_PRUEFUNG,
    ),
    Gate2(
        "standortbewertung",
        Gate2Ausloeser.KI_KOMPONENTE_ERGAENZT,
        "Das Standortmodell soll um ein trainiertes Prognoseverfahren für die "
        "Umsatzschätzung ergänzt werden.",
        vor_tagen=65,
        ausgang=GateStatus.ABGELEHNT,
        kommentar="Abgelehnt, solange die Trainingsdaten und ihre Herkunft nicht "
        "dokumentiert sind. Ohne sie ist die KI-Transparenz nach K6 nicht zu führen.",
    ),
    Gate2(
        "nachschubsteuerung",
        Gate2Ausloeser.KRITIKALITAET_GESTIEGEN,
        "Nach der Zusammenlegung der Regionallager hängt der gesamte "
        "Filialnachschub an einem Standort; die Ausfallfolge steigt auf kritisch.",
        vor_tagen=30,
    ),
)


@dataclass(frozen=True)
class Meldung:
    """Ein Compliance-Zustand und, wenn er rot ist, sein Lenkungsvorgang."""

    tool: str
    begruendung: str
    vor_tagen: int
    melder: str
    #: Wie der Vorgang ausging — ``None`` heisst: er ist noch offen.
    aufloesung: str | None = None
    aufgeloest_vor: int = 0
    aufloesungskommentar: str = ""
    #: Der Vorgang war eine Fehlmeldung und wurde von der Governance abgebrochen.
    abgebrochen: bool = False
    #: Was am Werkzeug tatsaechlich geaendert wurde, bevor der Vorgang als
    #: „angepasst" schliesst. Seit E-63 ist das keine Beigabe: die Aufloesung
    #: wird nachgemessen, und ein Bestand, der „angepasst" behauptet, ohne dass
    #: sich etwas geaendert hat, kaeme nicht mehr durch. Schluessel mit
    #: ``attest_`` gehen ueber die Attestierung (A.6), die uebrigen ueber die
    #: Aenderung des Tool-Objekts.
    anpassung: Mapping[str, object] = field(default_factory=dict)


MELDUNGEN: tuple[Meldung, ...] = (
    # --- Schicht 2: erkannt, ohne erste Eskalationsstufe -------------------
    Meldung(
        "konditionsexport-portal",
        "Der Export läuft unter einem Sammelkonto des Einkaufs. Die Zuordnung zu "
        "einer Person ist damit nicht mehr möglich.",
        vor_tagen=95,
        melder="renner",
    ),
    Meldung(
        "zollanmeldung-uebertrag",
        "Im Übertragungsdienst sind dauerhaft gültige Zugangsdaten des Zollportals hinterlegt.",
        vor_tagen=8,
        melder="pohl",
    ),
    Meldung(
        "budgetkonsolidierung",
        "Die Mappe zieht Zahlen aus Tabellen, die nicht als Datenobjekt geführt sind.",
        vor_tagen=140,
        melder="winkler",
        aufloesung=Aufloesungsart.ANPASSEN,
        aufgeloest_vor=126,
        aufloesungskommentar="Die beiden Zuarbeiten sind als Datenobjekte "
        "aufgenommen und verknüpft; die Mappe liest nichts anderes mehr.",
        # Und damit faellt die Erklaerung aus A.6, die das Verbot belegt hat.
        anpassung={"attest_undeklarierte_quellen": False},
    ),
    Meldung(
        "artikelauswertung-mappe",
        "Die Mappe zieht neben den beiden Datenobjekten Zahlen aus einer privaten "
        "Tabelle des Bearbeiters.",
        vor_tagen=34,
        melder="renner",
    ),
    Meldung(
        "schwundcockpit",
        "Das Cockpit markiert Kassenplätze selbsttätig als auffällig; zwischen "
        "Ergebnis und Meldung an die Filialleitung steht kein Mensch.",
        vor_tagen=88,
        melder="stadler",
    ),
    Meldung(
        "lagerauswertung-pl",
        "Die Auswertung läuft unter einem Konto, das sich mehrere Beschäftigte im Lager teilen.",
        vor_tagen=115,
        melder="renner",
        aufloesung=Aufloesungsart.STILLLEGEN,
        aufgeloest_vor=100,
        aufloesungskommentar="Die Auswertung wurde abgelöst; die Zahlen kommen "
        "seither aus dem Nachschubmonitor.",
    ),
    # --- Schicht 2: am Werkzeug erklaert, danach gemessen (E-64) -----------
    Meldung(
        "sortimentsexport-web",
        "Der Export legt Sortimentsdaten zusätzlich in einem öffentlich "
        "erreichbaren Objektspeicher ab.",
        vor_tagen=52,
        melder="stadler",
    ),
    Meldung(
        "regalpflege-app",
        "Die App schreibt ihre Zugriffe nicht in das Protokoll der Zielplattform.",
        vor_tagen=48,
        melder="renner",
    ),
    Meldung(
        "preisliste-versand",
        "Der Versand legt die Preisliste zusätzlich in einer öffentlich erreichbaren Ablage ab.",
        vor_tagen=60,
        melder="stadler",
        aufloesung=Aufloesungsart.ANPASSEN,
        aufgeloest_vor=52,
        aufloesungskommentar="Die öffentliche Ablage ist entfernt; der Versand "
        "geht nur noch an die Filialpostfächer.",
        anpassung={"externe_ziele": [], "daten_ins_offene_netz": False},
    ),
    Meldung(
        "frischeverlust-mappe",
        "Hinweis aus dem Plattformbetrieb: die Mappe soll die Zugriffs-protokollierung umgehen.",
        # Gemeldet hat der Plattformbetrieb; erfasst die Governance — die
        # Plattform-Rolle liest bereichsuebergreifend, schreibt aber nicht.
        vor_tagen=44,
        melder="renner",
        abgebrochen=True,
        aufgeloest_vor=40,
        aufloesungskommentar="Fehlmeldung: die Protokollierung war für die ganze "
        "Ablage abgeschaltet, nicht für dieses Tool-Objekt.",
    ),
    # --- Schicht 1: Rahmenueberschreitungen --------------------------------
    Meldung(
        "kampagnenexport",
        "Der Export übermittelt an ein Ziel, das kein Prozessobjekt erklärt hat.",
        vor_tagen=26,
        melder="kilian",
    ),
    Meldung(
        "bestandskorrektur-automat",
        "Der Automat läuft geplant, obwohl zwischen Ergebnis und Buchung kein "
        "Mensch steht. Der Rahmen deckt dann nur die interaktive Ausführung.",
        vor_tagen=14,
        melder="pohl",
    ),
    Meldung(
        "kuehlkettenwaechter",
        "Der Wächter meldet die Temperaturabweichungen zusätzlich an das "
        "Telematikportal des Dienstleisters.",
        vor_tagen=58,
        melder="pohl",
        aufloesung=Aufloesungsart.RAHMEN_ERWEITERN,
        aufgeloest_vor=30,
        aufloesungskommentar="Der Rahmen ist um das Telematikportal erweitert; "
        "die Bewertung wurde dafür neu durchlaufen.",
    ),
    Meldung(
        "abschriftenmonitor",
        "Der Monitor läuft geplant unter einer persönlichen Kennung statt unter "
        "einer benannten Dienstidentität.",
        vor_tagen=48,
        melder="seidel",
    ),
    Meldung(
        "frischeprognose",
        "Die Prognose liest die Kaufhistorie der Kundenkarte. Sie hängt an keinem "
        "der Prozessobjekte dieses Tools und trägt eine höhere Datenkategorie, "
        "als der Rahmen deckt.",
        vor_tagen=36,
        melder="stadler",
    ),
    Meldung(
        "filialkennzahlen-tafel",
        "Die Tafel schreibt in die Abverkaufsdaten. Der Prozess führt sie als "
        "Eingang, nicht als Ergebnis — geschrieben werden darf dort nicht.",
        vor_tagen=18,
        melder="lenz",
    ),
    # --- Gruen: der Regelfall, und er gehoert in die Zeitreihe -------------
    Meldung(
        "bestellvorschlagsrechner",
        "Turnusmäßige Prüfung: Rahmen eingehalten.",
        40,
        "seidel",
    ),
    Meldung(
        "entgeltvorbereitung",
        "Turnusmäßige Prüfung: Rahmen eingehalten.",
        35,
        "kraus",
    ),
    Meldung(
        "kassenabschluss-melder",
        "Turnusmäßige Prüfung: Rahmen eingehalten.",
        33,
        "lenz",
    ),
    Meldung(
        "tourenrechner",
        "Turnusmäßige Prüfung: Rahmen eingehalten.",
        31,
        "pohl",
    ),
    Meldung(
        "probenplan-app",
        "Turnusmäßige Prüfung: Rahmen eingehalten.",
        29,
        "straub",
    ),
    Meldung(
        "rueckrufmelder",
        "Turnusmäßige Prüfung: Rahmen eingehalten.",
        27,
        "straub",
    ),
    Meldung(
        "schnittstellenwaechter",
        "Turnusmäßige Prüfung: Rahmen eingehalten.",
        24,
        "hartwig",
    ),
    Meldung(
        "ladestrecke-warenwirtschaft",
        "Turnusmäßige Prüfung: Rahmen eingehalten.",
        21,
        "baumann",
    ),
    Meldung(
        "couponzuteilung",
        "Turnusmäßige Prüfung: Rahmen eingehalten.",
        19,
        "kilian",
    ),
    Meldung(
        "dienstplanrechner",
        "Turnusmäßige Prüfung: Rahmen eingehalten.",
        16,
        "albrecht",
    ),
    Meldung(
        "wareneingangs-scanner",
        "Turnusmäßige Prüfung: Rahmen eingehalten.",
        12,
        "pohl",
    ),
    Meldung(
        "abschlusscockpit",
        "Turnusmäßige Prüfung: Rahmen eingehalten.",
        9,
        "steiner",
    ),
)

#: Tage, an denen der geplante Eskalationslauf gefahren wurde. Er rueckt jeden
#: Vorgang weiter, dessen Frist verstrichen ist (A.13.5).
ESKALATIONSLAEUFE: tuple[int, ...] = (70, 45, 20, 3)

#: Tool-Objekte, deren technischer Owner die kompensierenden Massnahmen
#: dokumentiert hat. Bei den uebrigen bleibt der Befund offen — „kompensierbar"
#: ist eine Aufgabe, kein Zustand (A.9.3).
KOMPENSIERT: frozenset[str] = frozenset(
    {
        "konditionsmappe",
        "kalkulationsmappe-eigenmarke",
        "aktionscockpit",
        "lieferantenscorecard",
        "gefahrstoffkataster-app",
        "inventurauswertung",
        "preisetiketten-erzeugung",
        "filialbesuchsbogen",
        "frachtabrechnungsmappe",
        "rechnungspruefung-app",
        "mietvertragsfristen",
        "unfallmeldung-app",
        "hygieneprotokoll-app",
        "probenplan-app",
        "schulungsnachweis-app",
        "wareneingangs-scanner",
        "kundenkonto-pflege",
        "reklamations-app",
        "standortmodell",
        "filialergebnis-report",
        "fehlzeitenreport",
        "bestellvorschlagsrechner",
        "kassenabschluss-melder",
        "tourenrechner",
        "entgeltvorbereitung",
        "kuehlkettenwaechter",
        "ladestrecke-warenwirtschaft",
        "schnittstellenwaechter",
        "couponzuteilung",
        "dienstplanrechner",
        "artikelanlage-import",
    }
)

MASSNAHMEN: dict[str, str] = {
    "K5": "Der Zugriff läuft ausschließlich über eine benannte Gruppe im "
    "Verzeichnisdienst; ihre Mitgliedschaft wird im jährlichen "
    "Berechtigungsreview bestätigt.",
    "K8": "Die Ergebnisse werden monatlich in das revisionssichere Archiv "
    "ausgeleitet; der Export ist protokolliert und wird stichprobenweise geprüft.",
    "K9": "Der Wiederanlauf ist beschrieben und halbjährlich erprobt; die "
    "Auswertung lässt sich innerhalb von zwei Arbeitstagen neu aufsetzen.",
}
STANDARDMASSNAHME = (
    "Die kompensierende Maßnahme ist beschrieben, mit dem Fachbereich abgestimmt "
    "und wird jährlich überprüft."
)

#: Tool-Objekte, deren technischer Owner keine Erklaerung nach A.10.3 abgegeben
#: hat. Ab geerbtem Tier 3 meldet das Cockpit es.
TOOLS_OHNE_ERKLAERUNG: frozenset[str] = frozenset(
    {
        "abschriftenmonitor",
        "altbestandsauswertung",
        "auditmappe",
        "befragungsauswertung-mappe",
        "energiemonitor",
        "frischeverlust-mappe",
        "kampagnenexport",
        "mengenplanung-rohentwurf",
        "retourenauswertung",
        "werbemittelplanung-mappe",
    }
)

#: Erklaerungen technischer Owner, in denen eine verlangte Aussage offen blieb.
TOOL_UNVOLLSTAENDIG: dict[str, str] = {
    "filialkennzahlen-tafel": "TO4",
    "frischeprognose": "TO2",
    "lagerauswertung-pl": "TO5",
}


# --- Selbstverpflichtungen -----------------------------------------------


def _aussagen(typ: str, tier: int | None, offen: str | None, kommentare: dict[str, str]) -> dict:
    return {
        aussage.id: {
            "bestaetigt": aussage.id != offen,
            "kommentar": kommentare.get(aussage.id, ""),
        }
        for aussage in verpflichtung.verlangte_aussagen(typ, tier)
    }


def lebenszyklus(kontext: Kontext) -> None:
    """Erklaeren, freigeben, in Betrieb nehmen — als ein Vorgang.

    Die drei Schritte stehen bewusst in **einem** Block: A.10.5 macht die
    vollstaendige Selbstverpflichtung und die Freigabe durch Gate 1 zur
    Bedingung der Aktivierung, und die Anwendung prueft das beim Statuswechsel.
    Wer sie auseinanderzieht, muesste die Pruefung umgehen — und ein Bestand,
    der die eigene Torwaechterregel umgeht, sagt ueber sie nichts aus.

    Fachlich ist das kein Kunstgriff: eine Freigabe wird in einer Sitzung
    erteilt und der Prozess danach in Betrieb genommen, nicht Wochen spaeter.
    """
    governance = kontext.wer("wilms")
    for einstufung in bewertungen_schritt.EINSTUFUNGEN:
        bewertung = kontext.bewertungen.get(einstufung.prozess)
        if bewertung is None:
            continue
        eintrag = bewertungen_schritt.KATALOG[einstufung.prozess]
        akteur = kontext.wer(handelnder(kontext, eintrag))
        prozess = kontext.prozess(einstufung.prozess)
        wann = max(6, bewertungen_schritt.erstbewertung_vor(einstufung) - 4)

        with kontext.aktion(wann, stunde=11):
            if einstufung.prozess not in OHNE_ERKLAERUNG:
                verpflichtung.abgeben(
                    kontext.db,
                    akteur,
                    typ=SelbstverpflichtungTyp.PROZESSEIGNER,
                    prozess=prozess,
                    aussagen=_aussagen(
                        SelbstverpflichtungTyp.PROZESSEIGNER,
                        bewertung.tier,
                        UNVOLLSTAENDIG.get(einstufung.prozess),
                        KOMMENTARE.get(einstufung.prozess, {}),
                    ),
                )

            if bewertung.tier >= 3 and einstufung.prozess != "befragungsauswertung":
                vorgang = gate.einreichen(
                    kontext.db,
                    akteur,
                    prozess,
                    gate_typ=GateTyp.GATE_1,
                    begruendung=(
                        f"Erstfreigabe nach Tier {bewertung.tier}. Ausgelöst durch "
                        f"{_hoechste_dimension(bewertung)}."
                    ),
                )
                status, kommentar = GATE1_AUSGANG.get(
                    einstufung.prozess,
                    (
                        GateStatus.FREIGEGEBEN,
                        "Freigegeben; die Auflagen aus dem Tier sind umgesetzt.",
                    ),
                )
                if status != GateStatus.EINGEREICHT:
                    gate.entscheiden(
                        kontext.db, governance, vorgang, status=status, kommentar=kommentar
                    )

            if einstufung.prozess not in BLEIBT_ENTWURF:
                prozess_service.aendern(kontext.db, akteur, prozess, ProzessAendern(status="aktiv"))


def stilllegungen(kontext: Kontext) -> None:
    """Prozessobjekte, die abgeloest wurden."""
    for schluessel, wann in STILLGELEGT.items():
        eintrag = bewertungen_schritt.KATALOG[schluessel]
        with kontext.aktion(wann, stunde=13):
            prozess_service.aendern(
                kontext.db,
                kontext.wer(handelnder(kontext, eintrag)),
                kontext.prozess(schluessel),
                ProzessAendern(status="stillgelegt"),
            )


def selbstverpflichtungen_erneuern(kontext: Kontext) -> None:
    """Nach der Neubewertung verfaellt die Erklaerung (A.10.4) — hier neu.

    Nicht ueberall: wo sie ausbleibt, meldet das Cockpit „hängt an einer
    überholten Bewertung". Das ist der haeufigste Fall im Betrieb und deshalb
    einer, den der Bestand zeigen muss.
    """
    ausgelassen = {"leistungsdialog", "zollabwicklung", "filialergebnis", "schwundanalyse"}
    for einstufung in bewertungen_schritt.EINSTUFUNGEN:
        if einstufung.erneuert_vor is None or einstufung.prozess in OHNE_ERKLAERUNG:
            continue
        if einstufung.prozess in ausgelassen:
            continue
        bewertung = kontext.bewertungen.get(einstufung.prozess)
        if bewertung is None:
            continue
        with kontext.aktion(max(4, einstufung.erneuert_vor - 1), stunde=15):
            verpflichtung.abgeben(
                kontext.db,
                kontext.wer(handelnder(kontext, bewertungen_schritt.KATALOG[einstufung.prozess])),
                typ=SelbstverpflichtungTyp.PROZESSEIGNER,
                prozess=kontext.prozess(einstufung.prozess),
                aussagen=_aussagen(
                    SelbstverpflichtungTyp.PROZESSEIGNER,
                    bewertung.tier,
                    UNVOLLSTAENDIG.get(einstufung.prozess),
                    KOMMENTARE.get(einstufung.prozess, {}),
                ),
            )


def selbstverpflichtungen_tool(kontext: Kontext) -> None:
    """Die Erklaerung des technischen Owners nach A.10.3.

    Sie enthaelt die Aussage TO3 — „das Tool-Objekt laeuft im erklaerten
    Rahmen". Abgegeben wurde sie, bevor die Abweichung auffiel; sie steht
    deshalb bei einigen Werkzeugen heute neben einem roten Zustand. Genau
    dieses Nebeneinander sucht die Cockpit-Zeile „Widersprueche", und es
    entsteht hier nicht kuenstlich, sondern weil die Reihenfolge stimmt.
    """
    for eintrag in WERKZEUGE:
        if eintrag.schluessel in TOOLS_OHNE_ERKLAERUNG or eintrag.attest is None:
            continue
        tool = kontext.tool(eintrag.schluessel)
        tier = asset.erbe_klassifikation(tool).tier
        with kontext.aktion(max(6, eintrag.attestiert_vor - 3), stunde=16):
            verpflichtung.abgeben(
                kontext.db,
                kontext.wer(eintrag.owner),
                typ=SelbstverpflichtungTyp.TECHNISCHER_OWNER,
                tool=tool,
                aussagen=_aussagen(
                    SelbstverpflichtungTyp.TECHNISCHER_OWNER,
                    tier,
                    TOOL_UNVOLLSTAENDIG.get(eintrag.schluessel),
                    {},
                ),
            )


# --- Gates ----------------------------------------------------------------


def gate2_vorgaenge(kontext: Kontext) -> None:
    """Die spaeteren Gates aus den fuenf Ausloesern des A.11."""
    governance = kontext.wer("wilms")
    for eintrag in GATE2_VORGAENGE:
        prozess = kontext.prozess(eintrag.prozess)
        with kontext.aktion(eintrag.vor_tagen, stunde=11):
            vorgang = gate.einreichen(
                kontext.db,
                kontext.wer(handelnder(kontext, bewertungen_schritt.KATALOG[eintrag.prozess])),
                prozess,
                gate_typ=GateTyp.GATE_2,
                ausloeser=eintrag.ausloeser,
                begruendung=eintrag.begruendung,
            )
        if eintrag.ausgang is None:
            continue
        with kontext.aktion(max(2, eintrag.vor_tagen - 8), stunde=15):
            gate.entscheiden(
                kontext.db,
                governance,
                vorgang,
                status=eintrag.ausgang,
                kommentar=eintrag.kommentar,
            )


def _hoechste_dimension(bewertung) -> str:
    namen = {
        "ki_stufe": "die KI-Dimension",
        "ds_stufe": "den Datenschutz",
        "mb_stufe": "die Mitbestimmung",
        "it_stufe": "die IT-Sicherheit",
        "rg_stufe": "die Regulatorik",
        "ur_stufe": "das unternehmerische Risiko",
    }
    treffer = [text for feld, text in namen.items() if getattr(bewertung, feld) >= 3]
    return ", ".join(treffer) if treffer else "die Gesamteinstufung"


# --- Technologiematrix und Kompensationen --------------------------------


def technologiematrix(kontext: Kontext) -> None:
    """Fuellt die Matrix und pflegt eine Entscheidung der Governance ein."""
    with kontext.aktion(740, stunde=9):
        klassen.initialisiere(kontext.db)

    with kontext.aktion(150, stunde=10):
        klassen.setze_feld(
            kontext.db,
            kontext.wer("wilms"),
            "python-kubernetes",
            "K9",
            bewertung=Klassenbewertung.KOMPENSIERBAR,
            begruendung="Nach dem Ausfall des Regionallagers im Frühjahr hat die Nachschau "
            "ergeben, dass für die Anwendungslogik kein Wiederanlaufplan besteht. "
            "Die Plattform trägt den Betrieb, nicht den Wiederanlauf der fachlichen "
            "Auswertung — das ist je Anwendung zu beschreiben.",
        )


def kompensationen(kontext: Kontext) -> None:
    """Dokumentiert die Massnahmen dort, wo der Owner sie erbracht hat."""
    for eintrag in WERKZEUGE:
        if eintrag.schluessel not in KOMPENSIERT:
            continue
        tool = kontext.tool(eintrag.schluessel)
        befund = klassen.pruefe_tool(kontext.db, tool)
        offen = [b.k_klasse for b in befund.befunde if b.art == Befundart.KOMPENSATION_FEHLT]
        for k_klasse in offen:
            # Nach der Matrixaenderung, nicht davor: eine Kompensation zu einem
            # Feld, das damals noch „erfuellt" war, haette es nicht gegeben.
            wann = max(5, min(eintrag.attestiert_vor - 5, 140))
            with kontext.aktion(wann, stunde=12):
                klassen.setze_kompensation(
                    kontext.db,
                    kontext.wer(eintrag.owner),
                    tool,
                    k_klasse,
                    MASSNAHMEN.get(k_klasse, STANDARDMASSNAHME),
                )


# --- Compliance-Zustaende und Lenkung ------------------------------------


def _passe_werkzeug_an(kontext: Kontext, meldung: Meldung) -> None:
    """Die Anpassung, die der Aufloesungskommentar behauptet — wirklich ausgefuehrt.

    Vor E-63 stand sie nur im Text. Seit die Aufloesung nachgemessen wird, muss
    der Bestand tun, was er sagt: sonst faellt er ueber seinen eigenen Riegel.
    Das ist kein Umweg, sondern der Beleg, dass der Riegel greift.
    """
    tool = kontext.tool(meldung.tool)
    handelnder = kontext.wer(meldung.melder)
    attest = {s: w for s, w in meldung.anpassung.items() if s.startswith("attest_")}
    uebrige = {s: w for s, w in meldung.anpassung.items() if not s.startswith("attest_")}
    if uebrige:
        asset.aendere_tool(kontext.db, handelnder, tool, dict(uebrige))
    if attest:
        werte = {
            feld: getattr(tool, feld)
            for feld in (
                "attest_entscheidung_ueber_personen",
                "attest_mensch_dazwischen",
                "attest_undeklarierte_quellen",
            )
        }
        werte.update(attest)
        asset.attestiere(kontext.db, handelnder, tool, werte)


def lenkungsvorgaenge(kontext: Kontext) -> None:
    """Meldungen, Eskalationslaeufe und Aufloesungen — in der Reihenfolge der Zeit.

    Die drei Arten von Ereignissen greifen ineinander: ein Vorgang, der vor
    hundert Tagen aufgeloest wurde, darf von einem Lauf vor siebzig Tagen nicht
    mehr weitergerueckt werden. Deshalb wird hier nicht nach Art sortiert,
    sondern nach Datum — so, wie es tatsaechlich passiert waere.
    """
    vorgaenge: dict[str, object] = {}

    def melden(meldung: Meldung):
        def tun(wann):
            _zustand, vorgang = lenkung.melde_abweichung(
                kontext.db,
                kontext.wer(meldung.melder),
                kontext.tool(meldung.tool),
                begruendung=meldung.begruendung,
                jetzt=wann,
            )
            vorgaenge[meldung.tool] = vorgang

        return tun

    def aufloesen(meldung: Meldung):
        def tun(wann):
            vorgang = vorgaenge.get(meldung.tool)
            if vorgang is None:
                return
            if meldung.anpassung:
                _passe_werkzeug_an(kontext, meldung)
            if meldung.abgebrochen:
                lenkung.brich_ab(
                    kontext.db, kontext.wer("wilms"), vorgang, meldung.aufloesungskommentar
                )
                return
            bewertung_id = (
                _neueste_bewertung_des_tools(kontext, meldung.tool)
                if meldung.aufloesung == Aufloesungsart.RAHMEN_ERWEITERN
                else None
            )
            lenkung.loese_auf(
                kontext.db,
                kontext.wer(meldung.melder),
                vorgang,
                art=meldung.aufloesung,
                bewertung_id=bewertung_id,
                kommentar=meldung.aufloesungskommentar,
                jetzt=wann,
            )

        return tun

    def eskalieren(wann):
        lenkung.eskaliere_faellige(kontext.db, jetzt=wann)

    ereignisse: list[tuple[int, int, object]] = []
    for meldung in MELDUNGEN:
        ereignisse.append((meldung.vor_tagen, 10, melden(meldung)))
        if meldung.aufloesung is not None or meldung.abgebrochen:
            ereignisse.append((meldung.aufgeloest_vor, 11, aufloesen(meldung)))
    ereignisse.extend((tag, 6, eskalieren) for tag in ESKALATIONSLAEUFE)

    for vor_tagen, stunde, tun in sorted(ereignisse, key=lambda e: (-e[0], e[1])):
        with kontext.aktion(vor_tagen, stunde=stunde) as wann:
            tun(wann)


def _neueste_bewertung_des_tools(kontext: Kontext, tool_schluessel: str):
    """Die juengste Bewertung eines Prozesses, an dem das Tool haengt."""
    tool = kontext.tool(tool_schluessel)
    kandidaten = [prozess_service.neueste_bewertung(prozess) for prozess in tool.prozessobjekte]
    vorhanden = [b for b in kandidaten if b is not None]
    if not vorhanden:
        return None
    return max(vorhanden, key=lambda b: b.bewertet_am).id


# --- Governance-Einstellungen --------------------------------------------


def einstellungen(kontext: Kontext) -> None:
    """Eine Regeländerung im laufenden Betrieb, wie A.6.6 sie vorsieht."""
    schluessel = "selbstverpflichtung_erinnerung_vorlauf_tage"
    with kontext.aktion(210, stunde=9):
        konfiguration.initialisiere(kontext.db)
        bestehend = kontext.db.execute(
            select(Konfiguration).where(Konfiguration.schluessel == schluessel)
        ).scalar_one()
        vorher = snapshot(bestehend)
        eintrag = konfiguration.setze(kontext.db, schluessel, "45")
        protokolliere_aenderung(
            kontext.db,
            eintrag,
            vorher,
            akteur_user_id=kontext.person("wilms").id,
            beschreibung="Vorlauf der Erinnerung verkürzt",
        )
