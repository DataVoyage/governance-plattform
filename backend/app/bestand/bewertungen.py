"""Aufbauschritt 5: die Bewertungen.

Der Katalog gibt je Prozessobjekt das **Profil** an — sechs Stufen — und nicht
die achtzehn Einzelantworten. Der Baum rechnet beides ineinander um: innerhalb
eines Blocks bestimmt die erste mit „ja" beantwortete Frage die Stufe, also
folgen die Antworten eindeutig aus der Stufe. Ein Profil ist lesbar, achtzehn
Wahrheitswerte sind es nicht.

Vor dem Speichern prueft dieser Schritt jede Antwort gegen den Vorschlag aus
A.8.4 und sammelt die Stellen, an denen sie widerspricht. Wo das gewollt ist,
steht im Katalog eine Begruendung — das ist der Fall, den A.8.4 ausdruecklich
zulaesst. Wo keine steht, ist der Katalog falsch, und der Aufbau sagt das,
statt eine Bewertung zu erzeugen, die die Anwendung so nie angenommen haette.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.bestand.kontext import Kontext, Unstimmig
from app.bestand.prozesse import PROZESSE, handelnder
from app.models.governance import Bewertung
from app.services import ableitung
from app.services import bewertung as bewertung_service
from app.services import vorschlag as vorschlag_service
from app.services.bewertungsbaum import BAUM, KI_VERBOTEN, Block, Themenblock

#: Der Kuerzel-Block der Dimension, wie er im Profil steht.
BLOCK_JE_KUERZEL = {block.block.value: block for block in BAUM}


@dataclass(frozen=True)
class Einstufung:
    """Das Profil eines Prozessobjekts und der Weg, auf dem es entstand."""

    prozess: str
    ki: int
    ds: int
    mb: int
    it: int
    rg: int
    #: ``None`` heisst: der gerechneten Kritikalitaet folgen. Sie ist die einzige
    #: Dimension, die vollstaendig aus den Daten faellt (A.8.4).
    ur: int | None = None
    #: Tage vor heute; ``None`` heisst kurz nach dem Anlegen des Prozesses.
    bewertet_vor: int | None = None
    #: Die jaehrliche Erneuerung ab Tier 3 (A.10.5). Ohne sie laeuft die
    #: Bewertung ab und das Cockpit meldet es.
    erneuert_vor: int | None = None
    #: Der schnelle Durchlauf endet beim ersten Tier-3-Treffer (A.8.5).
    schnell: bool = False
    #: Trifft den Verbotstatbestand aus Schritt 1b: es entsteht keine Bewertung,
    #: sondern ein Governance-Alarm.
    verboten: bool = False
    begruendungen: dict[str, str] = field(default_factory=dict)


EINSTUFUNGEN: tuple[Einstufung, ...] = (
    # --- Einkauf Food ------------------------------------------------------
    Einstufung("konditionsverhandlung", ki=0, ds=1, mb=0, it=2, rg=2, erneuert_vor=95),
    Einstufung("artikelanlage", ki=0, ds=1, mb=0, it=3, rg=2, erneuert_vor=140),
    Einstufung("aktionsplanung", ki=0, ds=0, mb=0, it=2, rg=1),
    Einstufung("eigenmarkenkalkulation", ki=0, ds=0, mb=0, it=1, rg=1),
    Einstufung("lieferantenbewertung-food", ki=0, ds=1, mb=0, it=1, rg=1),
    Einstufung("persoenliche-artikelauswertung", ki=0, ds=0, mb=0, it=1, rg=0),
    # --- Einkauf Nonfood ---------------------------------------------------
    Einstufung("saisonplanung", ki=0, ds=0, mb=0, it=2, rg=1),
    Einstufung("gefahrstoffpruefung", ki=0, ds=0, mb=0, it=1, rg=2),
    # --- Vertrieb und Filialbetrieb ---------------------------------------
    Einstufung("bestellvorschlag", ki=1, ds=0, mb=0, it=3, rg=1, erneuert_vor=60),
    Einstufung("frischedisposition", ki=1, ds=0, mb=0, it=2, rg=1, erneuert_vor=210),
    Einstufung("abschriftensteuerung", ki=0, ds=0, mb=0, it=1, rg=1, erneuert_vor=150),
    Einstufung("inventurabwicklung", ki=0, ds=0, mb=0, it=2, rg=3, erneuert_vor=250),
    # Ohne Erneuerung: die Jahresfrist ist verstrichen (A.10.5).
    Einstufung("kassenabschluss", ki=0, ds=1, mb=0, it=3, rg=3),
    Einstufung("schwundanalyse", ki=0, ds=2, mb=3, it=2, rg=1, erneuert_vor=175),
    Einstufung("regalpflege", ki=0, ds=0, mb=1, it=1, rg=0),
    Einstufung("filialbesuche", ki=0, ds=0, mb=1, it=1, rg=0),
    Einstufung("preisauszeichnung", ki=0, ds=0, mb=0, it=2, rg=2),
    Einstufung("sortimentsveroeffentlichung", ki=0, ds=0, mb=0, it=1, rg=1),
    # --- Logistik ----------------------------------------------------------
    Einstufung("tourenoptimierung", ki=1, ds=2, mb=2, it=2, rg=1),
    # Ohne Erneuerung: abgelaufen.
    Einstufung("wareneingang", ki=0, ds=0, mb=0, it=3, rg=2),
    # Der Bestandskorrektur-Automat bucht ohne Menschen dazwischen; damit
    # veraendert der Prozess den Arbeitsablauf im Lager spuerbar (Frage 3c).
    Einstufung("nachschubsteuerung", ki=0, ds=0, mb=1, it=3, rg=1, erneuert_vor=115),
    Einstufung("frachtkostenabrechnung", ki=0, ds=0, mb=0, it=2, rg=2),
    Einstufung("kuehlkettenueberwachung", ki=0, ds=0, mb=0, it=2, rg=3, erneuert_vor=35),
    Einstufung("zollabwicklung", ki=0, ds=0, mb=0, it=2, rg=3, erneuert_vor=190),
    # --- Personal ----------------------------------------------------------
    Einstufung("personaleinsatzplanung", ki=1, ds=2, mb=3, it=2, rg=2, erneuert_vor=80),
    Einstufung("entgeltlauf", ki=0, ds=3, mb=3, it=3, rg=3, erneuert_vor=45),
    Einstufung("bewerbervorauswahl", ki=3, ds=3, mb=3, it=2, rg=2),
    Einstufung("fehlzeitenauswertung", ki=0, ds=3, mb=3, it=2, rg=2, erneuert_vor=155),
    Einstufung("schulungssteuerung", ki=0, ds=2, mb=2, it=1, rg=2),
    # Der schnelle Durchlauf: nach der Datenschutzstufe 3 ist die Sache klar.
    Einstufung("befragungsauswertung", ki=0, ds=3, mb=0, it=0, rg=0, schnell=True),
    Einstufung("leistungsdialog", ki=0, ds=3, mb=3, it=2, rg=2, erneuert_vor=230),
    # --- Finanzen und Controlling -----------------------------------------
    Einstufung("monatsabschluss", ki=0, ds=0, mb=0, it=3, rg=3, erneuert_vor=70),
    # Die Erneuerung liegt so, dass die Jahresfrist der Erklaerung in den
    # naechsten Wochen ablaeuft: der Erinnerungslauf hat damit einen Fall.
    Einstufung("kreditorenpruefung", ki=0, ds=1, mb=0, it=2, rg=3, erneuert_vor=332),
    Einstufung("budgetplanung-prozess", ki=0, ds=0, mb=0, it=2, rg=2),
    Einstufung("filialergebnis", ki=0, ds=0, mb=0, it=2, rg=2, erneuert_vor=125),
    # Ohne Erneuerung: abgelaufen.
    Einstufung("steuerkennzahlen-meldung", ki=0, ds=0, mb=0, it=2, rg=3),
    Einstufung("anlagenzugaenge", ki=0, ds=0, mb=0, it=2, rg=2),
    # --- Expansion und Immobilien -----------------------------------------
    Einstufung("standortbewertung", ki=1, ds=0, mb=0, it=2, rg=1),
    Einstufung("mietvertragsverwaltung", ki=0, ds=1, mb=0, it=2, rg=2),
    Einstufung("bauprojektsteuerung", ki=0, ds=0, mb=0, it=1, rg=1),
    # --- Marketing und Kundenbindung --------------------------------------
    Einstufung("kundenkartenprogramm", ki=0, ds=3, mb=0, it=2, rg=2, erneuert_vor=105),
    Einstufung("couponsteuerung", ki=2, ds=3, mb=0, it=2, rg=2),
    Einstufung("newsletterversand", ki=0, ds=2, mb=0, it=2, rg=2),
    Einstufung("werbemittelplanung-prozess", ki=0, ds=0, mb=0, it=1, rg=1),
    Einstufung("reklamationsbearbeitung", ki=0, ds=2, mb=0, it=2, rg=2),
    # --- Qualitätssicherung ------------------------------------------------
    Einstufung("eigenmarkenpruefung", ki=0, ds=0, mb=0, it=2, rg=3, erneuert_vor=90),
    Einstufung("rueckrufabwicklung", ki=0, ds=0, mb=0, it=2, rg=3, erneuert_vor=55),
    Einstufung("hygienekontrolle", ki=0, ds=0, mb=0, it=1, rg=2),
    # Begruendete Abweichung nach A.8.4: die Datenlage schlaegt Stufe 3 vor,
    # der Prozesseigner widerspricht — und sagt, warum.
    Einstufung(
        "arbeitssicherheit",
        ki=0,
        ds=3,
        mb=1,
        it=2,
        rg=2,
        erneuert_vor=200,
        begruendungen={
            "3a": (
                "Unfallmeldungen sind Gesundheitsdaten, aber keine Leistungs- oder "
                "Verhaltensdaten. Die Auswertung erfolgt ausschließlich je Filiale "
                "und Gefährdungsart; eine Zurechnung zu einzelnen Beschäftigten "
                "findet nicht statt und ist mit dem Betriebsrat so vereinbart."
            )
        },
    ),
    Einstufung("lieferantenaudit", ki=0, ds=0, mb=0, it=1, rg=2),
    # --- IT und Digitalisierung -------------------------------------------
    Einstufung("schnittstellenbetrieb", ki=0, ds=1, mb=0, it=3, rg=1, erneuert_vor=20),
    Einstufung("berechtigungsreview", ki=0, ds=2, mb=2, it=3, rg=2, erneuert_vor=160),
    Einstufung("datenplattform", ki=0, ds=0, mb=0, it=3, rg=2, erneuert_vor=100),
    # --- Der Verbotstatbestand --------------------------------------------
    Einstufung("emotionsanalyse-kasse", ki=KI_VERBOTEN, ds=3, mb=3, it=2, rg=1, verboten=True),
)


def _block_antworten(block: Themenblock, stufe: int) -> dict[str, bool]:
    """Die Antworten, die genau zu dieser Stufe fuehren.

    Der Baum endet innerhalb eines Blocks bei der ersten Frage mit „ja". Nach
    ihr wird nichts mehr gefragt — und deshalb hier auch nichts mehr
    beantwortet. Eine Antwort auf eine nie gestellte Frage waere eine erfundene
    Aussage, und der Vorschlagsabgleich wuerde sie gegen die Datenlage halten.
    """
    antworten: dict[str, bool] = {}
    for frage in block.fragen:
        if frage.abbruch_bei_nein:
            antworten[frage.id] = stufe != 0
            if stufe == 0:
                return antworten
            continue
        if frage.verbot_bei_ja:
            antworten[frage.id] = stufe == KI_VERBOTEN
            if stufe == KI_VERBOTEN:
                return antworten
            continue
        antworten[frage.id] = frage.stufe_bei_ja == stufe
        if frage.stufe_bei_ja == stufe:
            return antworten
    return antworten


def antworten_aus_profil(profil: dict[str, int], schnell: bool = False) -> dict[str, bool]:
    """Rechnet ein Sechser-Profil in die Antworten des Baums zurueck."""
    antworten: dict[str, bool] = {}
    for block in BAUM:
        stufe = profil.get(block.block.value, 0)
        antworten.update(_block_antworten(block, stufe))
        if schnell and stufe >= 3:
            break
    return antworten


def profil_von(einstufung: Einstufung, kritikalitaet: int) -> dict[str, int]:
    """Das Profil, mit der Kritikalitaet als Vorgabe fuer die Risikodimension."""
    return {
        Block.KI.value: einstufung.ki,
        Block.DS.value: einstufung.ds,
        Block.MB.value: einstufung.mb,
        Block.IT.value: einstufung.it,
        Block.RG.value: einstufung.rg,
        Block.UR.value: einstufung.ur if einstufung.ur is not None else kritikalitaet,
    }


def _pruefe_begruendungen(kontext: Kontext, einstufung: Einstufung) -> list[str]:
    """Sammelt Abweichungen ohne Begruendung, statt bei der ersten zu scheitern."""
    prozess = kontext.prozess(einstufung.prozess)
    profil = profil_von(einstufung, ableitung.leite_kritikalitaet_ab(prozess))
    antworten = antworten_aus_profil(profil, einstufung.schnell)
    vorschlaege = vorschlag_service.fuer_prozess(prozess)
    return [
        f"{einstufung.prozess}: Frage {abweichung.frage_id} — geantwortet "
        f"{'ja' if abweichung.antwort else 'nein'}, abgeleitet "
        f"{'ja' if abweichung.vorschlag else 'nein'}; es fehlt eine Begründung"
        for abweichung in vorschlag_service.abweichungen(vorschlaege, antworten)
        if not einstufung.begruendungen.get(abweichung.frage_id)
    ]


KATALOG = {p.schluessel: p for p in PROZESSE}


def _speichere(kontext: Kontext, einstufung: Einstufung, vor_tagen: int) -> Bewertung | None:
    prozess = kontext.prozess(einstufung.prozess)
    profil = profil_von(einstufung, ableitung.leite_kritikalitaet_ab(prozess))
    antworten = antworten_aus_profil(profil, einstufung.schnell)
    modus = (
        bewertung_service.Modus.SCHNELL
        if einstufung.schnell
        else bewertung_service.Modus.VOLLSTAENDIG
    )
    with kontext.aktion(vor_tagen, stunde=10, minute=(vor_tagen * 13) % 60):
        ergebnis = bewertung_service.speichere(
            kontext.db,
            kontext.wer(handelnder(kontext, KATALOG[einstufung.prozess])),
            prozess,
            antworten,
            modus=modus,
            begruendungen=dict(einstufung.begruendungen),
        )
    if isinstance(ergebnis, Bewertung):
        kontext.bewertungen[einstufung.prozess] = ergebnis
        return ergebnis
    return None


def erstbewertung_vor(einstufung: Einstufung) -> int:
    """Kurz nach dem Anlegen — vor der ersten Aktivierung."""
    if einstufung.bewertet_vor is not None:
        return einstufung.bewertet_vor
    return max(15, KATALOG[einstufung.prozess].angelegt_vor - 20)


def baue(kontext: Kontext) -> None:
    """Die Erstbewertung jedes Prozessobjekts."""
    fehlend: list[str] = []
    for einstufung in EINSTUFUNGEN:
        fehlend.extend(_pruefe_begruendungen(kontext, einstufung))
    if fehlend:
        raise Unstimmig(
            "Bewertungsantworten widersprechen der Datenlage, ohne dass der Katalog "
            "das begründet:\n  " + "\n  ".join(fehlend)
        )

    for einstufung in EINSTUFUNGEN:
        _speichere(kontext, einstufung, erstbewertung_vor(einstufung))


def erneuere(kontext: Kontext) -> None:
    """Die jaehrliche Erneuerung ab Tier 3 (A.10.5).

    Ein zweiter, eigenstaendiger Durchlauf mit demselben Ergebnis. Er steht
    bewusst **nach** Selbstverpflichtung, Gate und Aktivierung: genau so laeuft
    es im Betrieb, und nur so entsteht die Historie, die das Modul anzeigt.
    Wo er fehlt, ist die Bewertung heute abgelaufen — auch das kommt vor.
    """
    for einstufung in EINSTUFUNGEN:
        if einstufung.erneuert_vor is not None:
            _speichere(kontext, einstufung, einstufung.erneuert_vor)
