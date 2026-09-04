"""Cockpit-Modul (Architektur 8.7, Leitdokument A.14).

Kein einzelnes, ueberladenes Dashboard, sondern ein Satz gezielt aufrufbarer
Zeilen. Jede Zeile ist eine **Handlungsaufforderung**: sie liefert nicht nur
Zahlen, sondern zu jedem Eintrag das Zielmodul samt Filter, mit dem man ihn
abarbeitet.

Jede Zeile respektiert die Sichtbarkeitsregel aus Architektur 4.3: ein Nutzer
mit LAND-Scope sieht ausschliesslich Daten seines Bereichs, Governance- und
Auditor-Rollen sehen global.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import Principal
from app.models.enums import (
    AUSFALLFOLGE_STUFE,
    AssetStatus,
    Befundart,
    ComplianceFarbe,
    Herkunft,
    Rolle,
    SelbstverpflichtungTyp,
)
from app.models.governance import (
    Prozessobjekt,
    Selbstverpflichtung,
    ToolObjekt,
)
from app.models.organisation import Organisationseinheit, Rollenzuweisung, User
from app.services import asset as asset_service
from app.services import bewertung as bewertung_service
from app.services import klassen as klassen_service
from app.services import konfiguration, lenkung, selbstverpflichtung, vorschlag
from app.services import prozess as prozess_service


@dataclass
class Eintrag:
    """Ein Treffer samt dem Weg, ihn abzuarbeiten."""

    id: uuid.UUID
    titel: str
    hinweis: str = ""
    ziel_modul: str = ""
    ziel_filter: dict[str, str] = field(default_factory=dict)


@dataclass
class Zeile:
    schluessel: str
    titel: str
    beschreibung: str
    eintraege: list[Eintrag] = field(default_factory=list)
    aggregat: dict | None = None

    @property
    def anzahl(self) -> int:
        return len(self.eintraege)


# --- Hilfen ---------------------------------------------------------------


def _sichtbare_prozesse(
    db: Session, principal: Principal, fachbereich_id: uuid.UUID | None = None
) -> list[Prozessobjekt]:
    return prozess_service.liste(db, principal, fachbereich_id=fachbereich_id)


def _sichtbare_tools(
    db: Session, principal: Principal, fachbereich_id: uuid.UUID | None = None
) -> list[ToolObjekt]:
    tools = asset_service.liste_tools(db, principal)
    if fachbereich_id is None:
        return tools
    org_ids = set(
        db.execute(
            select(Organisationseinheit.id).where(
                Organisationseinheit.fachbereich_id == fachbereich_id
            )
        ).scalars()
    )
    return [t for t in tools if t.organisationseinheit_id in org_ids]


def _als_utc(zeitpunkt: datetime | None) -> datetime | None:
    if zeitpunkt is None:
        return None
    return zeitpunkt if zeitpunkt.tzinfo is not None else zeitpunkt.replace(tzinfo=UTC)


# --- Die Zeilen aus A.14 --------------------------------------------------


def prozesse_ohne_owner(db: Session, principal: Principal, **filter) -> Zeile:
    """Prozessobjekte, deren Owner faktisch nicht traegt.

    Das Feld ``owner_user_id`` ist Pflicht, kann also nicht leer sein. „Ohne
    Owner" heisst hier deshalb: der eingetragene Owner ist deaktiviert oder hat
    gar keine Prozess-Owner-Rolle — beides fuehrt dazu, dass niemand den
    Prozess tatsaechlich verantwortet.
    """
    zeile = Zeile(
        "prozesse_ohne_owner",
        "Prozesse ohne tragenden Owner",
        "Der eingetragene Owner ist deaktiviert oder hat keine Prozess-Owner-Rolle.",
    )
    mit_rolle = {
        z.user_id
        for z in db.execute(
            select(Rollenzuweisung).where(Rollenzuweisung.rolle == Rolle.PROZESS_OWNER)
        ).scalars()
    }
    for prozess in _sichtbare_prozesse(db, principal, filter.get("fachbereich_id")):
        owner = db.get(User, prozess.owner_user_id)
        if owner is not None and owner.ist_aktiv and owner.id in mit_rolle:
            continue
        grund = "Owner deaktiviert" if owner is None or not owner.ist_aktiv else "Owner ohne Rolle"
        zeile.eintraege.append(
            Eintrag(
                id=prozess.id,
                titel=prozess.name,
                hinweis=grund,
                ziel_modul="prozesse",
                ziel_filter={"id": str(prozess.id)},
            )
        )
    return zeile


def assets_ohne_prozesszuordnung(db: Session, principal: Principal, **filter) -> Zeile:
    zeile = Zeile(
        "assets_ohne_prozess",
        "Assets ohne Prozesszuordnung",
        "Tool-Objekte, die an keinem Prozessobjekt hängen und deshalb nichts erben.",
    )
    for tool in _sichtbare_tools(db, principal, filter.get("fachbereich_id")):
        if tool.prozessobjekte:
            continue
        hinweis = (
            "neu importiert, noch nicht zugeordnet"
            if tool.status == AssetStatus.IMPORTIERT_UNBESTAETIGT
            else "ohne Prozesskante"
        )
        zeile.eintraege.append(
            Eintrag(
                id=tool.id,
                titel=tool.name,
                hinweis=hinweis,
                ziel_modul="tools",
                ziel_filter={"id": str(tool.id)},
            )
        )
    return zeile


def non_compliant_je_stufe(db: Session, principal: Principal, **filter) -> Zeile:
    """Offene Lenkungsvorgaenge, gruppiert nach Eskalationsstufe."""
    stufe = filter.get("eskalationsstufe")
    zeile = Zeile(
        "non_compliant",
        "Non-compliante Anwendungen je Eskalationsstufe",
        "Offene Lenkungsvorgänge, nach Stufe filterbar.",
    )
    je_stufe: dict[int, int] = defaultdict(int)
    for vorgang in lenkung.liste(db, principal, nur_offen=True):
        je_stufe[vorgang.eskalationsstufe] += 1
        if stufe is not None and vorgang.eskalationsstufe != int(stufe):
            continue
        tool = db.get(ToolObjekt, vorgang.tool_objekt_id)
        zeile.eintraege.append(
            Eintrag(
                id=vorgang.id,
                titel=tool.name if tool is not None else str(vorgang.tool_objekt_id),
                hinweis=f"Stufe {vorgang.eskalationsstufe}, Frist "
                f"{vorgang.frist.date().isoformat()}",
                ziel_modul="lenkung",
                ziel_filter={"eskalationsstufe": str(vorgang.eskalationsstufe)},
            )
        )
    zeile.aggregat = {"je_stufe": {str(k): v for k, v in sorted(je_stufe.items())}}
    return zeile


def rahmenabweichungen(db: Session, principal: Principal, **filter) -> Zeile:
    """Tool-Objekte, deren **gerechneter** Zustand nicht gruen ist (E-64).

    Vorher las diese Zeile den letzten gemeldeten Zustand. Damit fehlte jedes
    Werkzeug, ueber das noch niemand etwas gemeldet hatte — auch dann, wenn die
    Anwendung seine Abweichung laengst messen konnte. Ein Cockpit, das auf eine
    Meldung wartet, zeigt nicht die Lage, sondern die Meldebereitschaft.
    """
    zeile = Zeile(
        "rahmenabweichungen",
        "Rahmenabweichungen",
        "Tool-Objekte, deren gerechneter Compliance-Zustand gelb oder rot ist.",
    )
    for tool in _sichtbare_tools(db, principal, filter.get("fachbereich_id")):
        farbe = lenkung.gemessene_farbe(db, tool)
        if farbe == ComplianceFarbe.GRUEN:
            continue
        offen = lenkung.offene_abweichungen(db, tool)
        zustand = lenkung.aktueller_zustand(db, tool.id)
        hinweis = ", ".join(offen) if offen else (zustand.begruendung if zustand else "")
        zeile.eintraege.append(
            Eintrag(
                id=tool.id,
                titel=tool.name,
                hinweis=f"{farbe}: {hinweis}".strip(": "),
                ziel_modul="tools",
                ziel_filter={"id": str(tool.id)},
            )
        )
    return zeile


def datenobjekte_ohne_kategorie(db: Session, principal: Principal, **filter) -> Zeile:
    del filter
    zeile = Zeile(
        "datenobjekte_ohne_kategorie",
        "Datenobjekte ohne Kategorie",
        "Ohne Kategorie trägt ein Datenobjekt nichts zur Bewertung bei.",
    )
    for datenobjekt in asset_service.liste_datenobjekte(db, principal, ohne_kategorie=True):
        zeile.eintraege.append(
            Eintrag(
                id=datenobjekt.id,
                titel=datenobjekt.name,
                hinweis="Kategorie fehlt",
                ziel_modul="datenobjekte",
                ziel_filter={"ohne_kategorie": "true"},
            )
        )
    return zeile


def kritikalitaetsketten(db: Session, principal: Principal, **filter) -> Zeile:
    """Prozesse, deren Kritikalitaet aus der Kette stammt, nicht aus sich selbst.

    Genau diese Faelle sind erklaerungsbeduerftig: der Prozess wirkt fuer sich
    harmlos und ist es wegen seiner Nachfolger nicht.
    """
    zeile = Zeile(
        "kritikalitaetsketten",
        "Kritikalitätsketten",
        "Prozesse, deren Kritikalität aus einem nachgelagerten Prozess geerbt ist.",
    )
    for prozess in _sichtbare_prozesse(db, principal, filter.get("fachbereich_id")):
        eigene = AUSFALLFOLGE_STUFE[prozess.ausfallfolge]
        if prozess.kritikalitaet <= eigene:
            continue
        quellen = ", ".join(p.name for p in prozess.nachgelagert) or "—"
        zeile.eintraege.append(
            Eintrag(
                id=prozess.id,
                titel=prozess.name,
                hinweis=f"eigene Ausfallfolge {eigene}, geerbt {prozess.kritikalitaet} "
                f"(über: {quellen})",
                ziel_modul="prozesse",
                ziel_filter={"id": str(prozess.id)},
            )
        )
    return zeile


def tier_verteilung(db: Session, principal: Principal, **filter) -> Zeile:
    """Tier-Verteilung je Technologie und je Monat (Leitdokument A.14)."""
    zeile = Zeile(
        "tier_verteilung",
        "Tier-Verteilung je Technologie und Zeit",
        "Wie sich die Einstufungen über Technologien und über die Zeit verteilen.",
    )
    je_technologie: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for tool in _sichtbare_tools(db, principal, filter.get("fachbereich_id")):
        tier = asset_service.erbe_klassifikation(tool).tier
        if tier is None:
            continue
        je_technologie[tool.technologie or "unbekannt"][str(tier)] += 1

    je_monat: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for prozess in _sichtbare_prozesse(db, principal, filter.get("fachbereich_id")):
        bewertung = prozess_service.neueste_bewertung(prozess)
        if bewertung is None:
            continue
        monat = (_als_utc(bewertung.bewertet_am) or datetime.now(UTC)).strftime("%Y-%m")
        je_monat[monat][str(bewertung.tier)] += 1

    zeile.aggregat = {
        "je_technologie": {k: dict(v) for k, v in sorted(je_technologie.items())},
        "je_monat": {k: dict(v) for k, v in sorted(je_monat.items())},
    }
    return zeile


def inaktive_assets(db: Session, principal: Principal, **filter) -> Zeile:
    """Tool-Objekte ohne Aktivitaet seit der konfigurierten Frist."""
    grenze_tage = konfiguration.lies_int(db, "asset_inaktiv_tage")
    jetzt = filter.get("jetzt") or datetime.now(UTC)
    zeile = Zeile(
        "inaktive_assets",
        "Inaktive Assets",
        f"Tool-Objekte ohne Aktivität seit mehr als {grenze_tage} Tagen oder stillgelegt.",
    )
    for tool in _sichtbare_tools(db, principal, filter.get("fachbereich_id")):
        letzte = _als_utc(tool.letzte_aktivitaet_am)
        stillgelegt = tool.status == AssetStatus.INAKTIV
        veraltet = letzte is not None and letzte < jetzt - timedelta(days=grenze_tage)
        if not stillgelegt and not veraltet:
            continue
        zeile.eintraege.append(
            Eintrag(
                id=tool.id,
                titel=tool.name,
                hinweis="stillgelegt"
                if stillgelegt
                else f"letzte Aktivität {letzte.date().isoformat()}",
                ziel_modul="tools",
                ziel_filter={"id": str(tool.id)},
            )
        )
    return zeile


def ueberfaellige_selbstverpflichtungen(db: Session, principal: Principal, **filter) -> Zeile:
    """Objekte, deren Selbstverpflichtung nicht (mehr) traegt.

    Bis AP-5 stand hier nur der Zeitablauf. A.10.4 kennt einen zweiten,
    haeufigeren Fall: die Erklaerung haengt an der Bewertung, zu der sie
    abgegeben wurde, und verfaellt mit ihr. Beides gehoert in dieselbe Zeile —
    fuer den Owner ist es dieselbe Handlung, und der Hinweis sagt ihm, welche
    Form sie hat: bestaetigen genuegt, oder neu abgeben.

    Ein Objekt ohne jede Erklaerung erscheint nur, wenn eine verlangt ist: erst
    ab Tier 3 ist die Selbstverpflichtung Aktivierungsbedingung (A.10.5).
    """
    jetzt = filter.get("jetzt")
    zeile = Zeile(
        "ueberfaellige_selbstverpflichtungen",
        "Selbstverpflichtungen ohne Deckung",
        "Die Jahresfrist ist verstrichen, die Erklärung fehlt, oder sie hängt an einer "
        "überholten Bewertung.",
    )
    for prozess in _sichtbare_prozesse(db, principal, filter.get("fachbereich_id")):
        bewertung = prozess_service.neueste_bewertung(prozess)
        stand = selbstverpflichtung.deckung_fuer_prozess(db, prozess, jetzt)
        if stand.gedeckt:
            continue
        if stand.grund == "keine" and (bewertung is None or bewertung.tier < 3):
            continue
        zeile.eintraege.append(
            Eintrag(
                id=prozess.id,
                titel=prozess.name,
                hinweis=f"Prozesseigner: {stand.grundtext}",
                ziel_modul="prozesse",
                ziel_filter={"id": str(prozess.id)},
            )
        )
    for tool in _sichtbare_tools(db, principal, filter.get("fachbereich_id")):
        tier = asset_service.erbe_klassifikation(tool).tier
        stand = selbstverpflichtung.deckung_fuer_tool(db, tool, jetzt)
        if stand.gedeckt:
            continue
        if stand.grund == "keine" and (tier is None or tier < 3):
            continue
        zeile.eintraege.append(
            Eintrag(
                id=tool.id,
                titel=tool.name,
                hinweis=f"Technischer Owner: {stand.grundtext}",
                ziel_modul="tools",
                ziel_filter={"id": str(tool.id)},
            )
        )
    return zeile


def attestierungen_veraltet(db: Session, principal: Principal, **filter) -> Zeile:
    """Tool-Objekte, deren Attestierung nach A.6 aelter als die Frist ist.

    Die drei Erklaerungen aus A.6 sind Momentaufnahmen: sie beschreiben, was
    ein Tool heute tut. Ein Jahr spaeter kann alles davon ueberholt sein, ohne
    dass jemand etwas geaendert haette, das die Plattform sieht. Die Frist
    steht in der Konfiguration und ist von der Governance-Rolle aenderbar.
    """
    grenze_tage = konfiguration.lies_int(db, "selbstverpflichtung_gueltigkeit_tage")
    jetzt = filter.get("jetzt") or datetime.now(UTC)
    zeile = Zeile(
        "attestierungen_veraltet",
        "Attestierungen älter als die Frist",
        f"Die Erklärungen nach A.6 liegen mehr als {grenze_tage} Tage zurück.",
    )
    for tool in _sichtbare_tools(db, principal, filter.get("fachbereich_id")):
        wann = _als_utc(tool.attestiert_am)
        if wann is None or wann >= jetzt - timedelta(days=grenze_tage):
            continue
        zeile.eintraege.append(
            Eintrag(
                id=tool.id,
                titel=tool.name,
                hinweis=f"attestiert am {wann.date().isoformat()}",
                ziel_modul="tools",
                ziel_filter={"id": str(tool.id)},
            )
        )
    return zeile


def widersprueche(db: Session, principal: Principal, **filter) -> Zeile:
    """Wo die Erklaerung dem gemessenen Zustand widerspricht.

    Der technische Owner bestaetigt mit einer Aussage aus A.10.3, dass sein Tool
    im erklaerten Rahmen laeuft. Steht der aktuelle Compliance-Zustand
    gleichzeitig auf rot, widersprechen sich Erklaerung und Feststellung — und
    genau das gehoert ins Cockpit.
    """
    del filter
    zeile = Zeile(
        "widersprueche",
        "Widersprüche zwischen Erklärung und Zustand",
        "Der Owner erklärt den Rahmen als eingehalten, der Zustand sagt etwas anderes.",
    )
    for tool in _sichtbare_tools(db, principal):
        zustand = lenkung.aktueller_zustand(db, tool.id)
        if zustand is None or zustand.farbe != ComplianceFarbe.ROT:
            continue
        erklaerung = db.execute(
            select(Selbstverpflichtung)
            .where(
                Selbstverpflichtung.tool_objekt_id == tool.id,
                Selbstverpflichtung.typ == SelbstverpflichtungTyp.TECHNISCHER_OWNER,
            )
            .order_by(Selbstverpflichtung.abgegeben_am.desc())
            .limit(1)
        ).scalar_one_or_none()
        if erklaerung is None:
            continue
        rahmen = selbstverpflichtung.AUSSAGE_RAHMEN_EINGEHALTEN
        if not erklaerung.aussagen.get(rahmen, {}).get("bestaetigt", False):
            continue
        zeile.eintraege.append(
            Eintrag(
                id=tool.id,
                titel=tool.name,
                hinweis=f"{rahmen} bestätigt, Zustand rot",
                ziel_modul="tools",
                ziel_filter={"id": str(tool.id)},
            )
        )
    return zeile


def antwort_widerspricht_datenlage(db: Session, principal: Principal, **filter) -> Zeile:
    """Wo eine gespeicherte Bewertungsantwort der heutigen Datenlage widerspricht.

    Drei Faelle sehen gleich aus und sind es nicht. Unterschieden werden sie
    ueber den Vorschlag, der zur Bewertung mitgespeichert wurde:

    * **Bewusst abgewichen, begruendet, Datenlage unveraendert.** Kein Befund,
      sondern eine dokumentierte Entscheidung — A.8.4 laesst die Abweichung
      ausdruecklich zu, wenn sie erklaert wird.
    * **Die Daten haben sich seit der Bewertung geaendert.** Ein Datenobjekt
      wurde umklassifiziert, ein Tool hat attestiert, ein Nachfolgeprozess ist
      kritischer geworden. Die Antwort von damals steht neben einer neuen
      Wirklichkeit, und eine Begruendung von damals bezieht sich auf eine Lage,
      die es nicht mehr gibt.
    * **Damals war nichts abzuleiten, heute schon.** Auch das ist ein Befund,
      aber kein Vorwurf: zum Zeitpunkt der Bewertung gab es die Grundlage fuer
      den Vorschlag noch nicht. Bewertungen von vor AP-4 fallen ebenfalls
      hierunter, weil zu ihnen ueberhaupt kein Vorschlag gerechnet wurde.

    Der Hinweis nennt den Fall beim Namen. Ohne den mitgespeicherten Vorschlag
    waeren alle drei nicht auseinanderzuhalten.
    """
    zeile = Zeile(
        "antwort_widerspricht_datenlage",
        "Antwort widerspricht Datenlage",
        "Die Bewertung sagt etwas anderes als die heutigen Daten — ohne dass das begründet wäre.",
    )
    for prozess in _sichtbare_prozesse(db, principal, filter.get("fachbereich_id")):
        aktuelle = prozess_service.neueste_bewertung(prozess)
        if aktuelle is None:
            continue
        heutige = vorschlag.fuer_prozess(prozess)
        for abweichung in vorschlag.abweichungen(heutige, aktuelle.antworten):
            damals = (aktuelle.vorschlaege or {}).get(abweichung.frage_id)
            if damals is None:
                grund = "damals nicht ableitbar, heute schon"
            elif damals != abweichung.vorschlag:
                grund = "Datenlage seit der Bewertung geändert"
            elif abweichung.frage_id in (aktuelle.abweichungen or {}):
                continue
            else:
                grund = "Abweichung ohne Begründung"
            beleg = abweichung.belege[0].text if abweichung.belege else ""
            zeile.eintraege.append(
                Eintrag(
                    id=prozess.id,
                    titel=prozess.name,
                    hinweis=f"Frage {abweichung.frage_id}: geantwortet "
                    f"{'ja' if abweichung.antwort else 'nein'}, abgeleitet "
                    f"{'ja' if abweichung.vorschlag else 'nein'} — {grund}. {beleg}".strip(),
                    ziel_modul="prozesse",
                    ziel_filter={"id": str(prozess.id)},
                )
            )
    return zeile


def technologie_erfuellt_klasse_nicht(db: Session, principal: Principal, **filter) -> Zeile:
    """Wo die Technologie eine ausgeloeste Anforderungsklasse nicht traegt (A.9.3).

    Drei Faelle stehen hier nebeneinander, weil alle drei denselben naechsten
    Schritt verlangen — jemand muss entscheiden:

    * **Ausschluss.** Die Matrix sagt ``nicht_erfuellbar``. Der Prozess laesst
      sich mit dieser Technologie nicht betreiben; eine Kompensation waere eine
      Umgehung des Kriteriums.
    * **Kompensation fehlt.** Die Matrix sagt ``kompensierbar``, und es steht
      keine Massnahme dabei. „Kompensierbar" ist eine Aufgabe, kein Zustand.
    * **Ungeprueft.** Am Tool steht keine Technologie, oder die Matrix kennt
      das Feld nicht. Eine fehlende Angabe ist kein Nachweis.

    Erfuellte und kompensierte Klassen erscheinen nicht — sie sind erledigt.
    """
    zeile = Zeile(
        "technologie_erfuellt_klasse_nicht",
        "Technologie erfüllt ausgelöste Anforderungsklasse nicht",
        "Die Technologie des Tools trägt eine Klasse nicht, die seine Prozesse auslösen.",
    )
    namen = bewertung_service.K_KLASSEN_BESCHREIBUNG
    for tool in _sichtbare_tools(db, principal, filter.get("fachbereich_id")):
        befund = klassen_service.pruefe_tool(db, tool)
        for eintrag in befund.befunde:
            if not eintrag.offen:
                continue
            grund = {
                Befundart.AUSSCHLUSS: "Ausschluss — die Technologie kann die Klasse nicht tragen",
                Befundart.KOMPENSATION_FEHLT: "kompensierbar, aber ohne dokumentierte Maßnahme",
                Befundart.UNGEPRUEFT: "ungeprüft — für diese Technologie gibt es kein Matrixfeld",
            }[eintrag.art]
            zeile.eintraege.append(
                Eintrag(
                    id=tool.id,
                    titel=tool.name,
                    hinweis=f"{eintrag.k_klasse} {namen.get(eintrag.k_klasse, '')}: {grund}.",
                    ziel_modul="tools",
                    ziel_filter={"id": str(tool.id)},
                )
            )
    return zeile


def altanwendungen_im_migrationspfad(db: Session, principal: Principal, **filter) -> Zeile:
    """Vorgefundene Anwendungen auf dem Weg in den Rahmen (Leitdokument A.16).

    Alt-Anwendungen sind die, die es vor dem Rahmenwerk schon gab: in dieser
    Anwendung erkennbar an ``herkunft = importiert``, denn sie sind vom Sync
    **vorgefunden** und nicht von jemandem angemeldet worden.

    A.16 gibt ihnen zwei Wege. Im **Meldepfad** stehen die, bei denen noch
    etwas zu tun ist — bestaetigen, einem Prozess zuordnen, den Prozess
    bewerten. Wer die Meldefrist verstreichen laesst, wechselt in den
    **Blockierungspfad**: dieselbe Aufgabe, aber die Frist ist abgelaufen.

    Eine Alt-Anwendung, die bestaetigt, zugeordnet und ueber ihren Prozess
    bewertet ist, hat den Weg hinter sich und erscheint hier nicht mehr — sie
    ist keine Alt-Anwendung mehr, sondern ein gefuehrtes Tool-Objekt.
    """
    frist_tage = konfiguration.lies_int(db, "altanwendung_meldefrist_tage")
    jetzt = filter.get("jetzt") or datetime.now(UTC)
    zeile = Zeile(
        "altanwendungen",
        "Alt-Anwendungen im Melde-/Blockierungspfad",
        "Vorgefundene Anwendungen, die den Weg in den Rahmen noch vor sich haben (A.16).",
    )
    for tool in _sichtbare_tools(db, principal, filter.get("fachbereich_id")):
        if tool.herkunft != Herkunft.IMPORTIERT:
            continue
        if tool.status == AssetStatus.IMPORTIERT_UNBESTAETIGT:
            aufgabe = "noch nicht bestätigt"
        elif not tool.prozessobjekte:
            aufgabe = "bestätigt, aber keinem Prozessobjekt zugeordnet"
        elif all(prozess_service.neueste_bewertung(p) is None for p in tool.prozessobjekte):
            aufgabe = "zugeordnet, aber der Prozess ist unbewertet"
        else:
            continue

        entdeckt = _als_utc(tool.erstellt_am) or jetzt
        tage = (jetzt - entdeckt).days
        pfad = "Blockierungspfad" if tage > frist_tage else "Meldepfad"
        zeile.eintraege.append(
            Eintrag(
                id=tool.id,
                titel=tool.name,
                hinweis=f"{pfad}: {aufgabe}. Seit {tage} Tagen vorgefunden, "
                f"Meldefrist {frist_tage} Tage.",
                ziel_modul="tools",
                ziel_filter={"id": str(tool.id)},
            )
        )
    return zeile


#: Die Zeilen in der Reihenfolge des Leitdokuments (A.14).
ZEILEN = {
    "prozesse_ohne_owner": prozesse_ohne_owner,
    "assets_ohne_prozess": assets_ohne_prozesszuordnung,
    "non_compliant": non_compliant_je_stufe,
    "rahmenabweichungen": rahmenabweichungen,
    "datenobjekte_ohne_kategorie": datenobjekte_ohne_kategorie,
    "kritikalitaetsketten": kritikalitaetsketten,
    "tier_verteilung": tier_verteilung,
    "inaktive_assets": inaktive_assets,
    "ueberfaellige_selbstverpflichtungen": ueberfaellige_selbstverpflichtungen,
    "attestierungen_veraltet": attestierungen_veraltet,
    "widersprueche": widersprueche,
    "antwort_widerspricht_datenlage": antwort_widerspricht_datenlage,
    "technologie_erfuellt_klasse_nicht": technologie_erfuellt_klasse_nicht,
    "altanwendungen": altanwendungen_im_migrationspfad,
}


def hole_zeile(db: Session, principal: Principal, schluessel: str, **filter) -> Zeile:
    if schluessel not in ZEILEN:
        raise prozess_service.NichtGefunden(f"Unbekannte Cockpit-Zeile: {schluessel}")
    return ZEILEN[schluessel](db, principal, **filter)


def uebersicht(db: Session, principal: Principal, **filter) -> list[Zeile]:
    """Alle Zeilen mit ihrer Trefferzahl — der Einstieg ins Cockpit."""
    return [ZEILEN[schluessel](db, principal, **filter) for schluessel in ZEILEN]
