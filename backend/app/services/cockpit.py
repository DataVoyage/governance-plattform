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
    ComplianceFarbe,
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
from app.services import erinnerung, konfiguration, lenkung
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
        "Tool-Objekte, die an keinem Prozessobjekt haengen und deshalb nichts erben.",
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
        "Offene Lenkungsvorgaenge, nach Stufe filterbar.",
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
    """Tool-Objekte, deren aktueller Compliance-Zustand nicht gruen ist."""
    zeile = Zeile(
        "rahmenabweichungen",
        "Rahmenabweichungen",
        "Tool-Objekte, deren neuester Compliance-Zustand gelb oder rot ist.",
    )
    for tool in _sichtbare_tools(db, principal, filter.get("fachbereich_id")):
        zustand = lenkung.aktueller_zustand(db, tool.id)
        if zustand is None or zustand.farbe == ComplianceFarbe.GRUEN:
            continue
        zeile.eintraege.append(
            Eintrag(
                id=tool.id,
                titel=tool.name,
                hinweis=f"{zustand.farbe}: {zustand.begruendung}".strip(": "),
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
        "Ohne Kategorie traegt ein Datenobjekt nichts zur Bewertung bei.",
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
        "Kritikalitaetsketten",
        "Prozesse, deren Kritikalitaet aus einem nachgelagerten Prozess geerbt ist.",
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
                f"(ueber: {quellen})",
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
        "Wie sich die Einstufungen ueber Technologien und ueber die Zeit verteilen.",
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
        f"Tool-Objekte ohne Aktivitaet seit mehr als {grenze_tage} Tagen oder stillgelegt.",
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
                else f"letzte Aktivitaet {letzte.date().isoformat()}",
                ziel_modul="tools",
                ziel_filter={"id": str(tool.id)},
            )
        )
    return zeile


def ueberfaellige_selbstverpflichtungen(db: Session, principal: Principal, **filter) -> Zeile:
    jetzt = filter.get("jetzt")
    zeile = Zeile(
        "ueberfaellige_selbstverpflichtungen",
        "Ueberfaellige Selbstverpflichtungen",
        "Die Jahresfrist ist ohne Bestaetigung verstrichen.",
    )
    sichtbare_prozesse = {p.id: p for p in _sichtbare_prozesse(db, principal)}
    sichtbare_tools = {t.id: t for t in _sichtbare_tools(db, principal)}
    for eintrag in erinnerung.ueberfaellige(db, jetzt):
        if eintrag.prozessobjekt_id is not None:
            prozess = sichtbare_prozesse.get(eintrag.prozessobjekt_id)
            if prozess is None:
                continue
            zeile.eintraege.append(
                Eintrag(
                    id=eintrag.id,
                    titel=prozess.name,
                    hinweis="Selbstverpflichtung des Prozesseigners ueberfaellig",
                    ziel_modul="prozesse",
                    ziel_filter={"id": str(prozess.id)},
                )
            )
        elif eintrag.tool_objekt_id is not None:
            tool = sichtbare_tools.get(eintrag.tool_objekt_id)
            if tool is None:
                continue
            zeile.eintraege.append(
                Eintrag(
                    id=eintrag.id,
                    titel=tool.name,
                    hinweis="Selbstverpflichtung des technischen Owners ueberfaellig",
                    ziel_modul="tools",
                    ziel_filter={"id": str(tool.id)},
                )
            )
    return zeile


def widersprueche(db: Session, principal: Principal, **filter) -> Zeile:
    """Wo die Erklaerung dem gemessenen Zustand widerspricht.

    Der technische Owner bestaetigt mit Aussage T1, dass sein Tool im
    vorgesehenen Rahmen laeuft. Steht der aktuelle Compliance-Zustand
    gleichzeitig auf rot, widersprechen sich Erklaerung und Feststellung — und
    genau das gehoert ins Cockpit.
    """
    del filter
    zeile = Zeile(
        "widersprueche",
        "Widersprueche zwischen Erklaerung und Zustand",
        "Der Owner erklaert den Rahmen als eingehalten, der Zustand sagt etwas anderes.",
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
        if not erklaerung.aussagen.get("T1", {}).get("bestaetigt", False):
            continue
        zeile.eintraege.append(
            Eintrag(
                id=tool.id,
                titel=tool.name,
                hinweis="T1 bestaetigt, Zustand rot",
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
    "widersprueche": widersprueche,
}


def hole_zeile(db: Session, principal: Principal, schluessel: str, **filter) -> Zeile:
    if schluessel not in ZEILEN:
        raise prozess_service.NichtGefunden(f"Unbekannte Cockpit-Zeile: {schluessel}")
    return ZEILEN[schluessel](db, principal, **filter)


def uebersicht(db: Session, principal: Principal, **filter) -> list[Zeile]:
    """Alle Zeilen mit ihrer Trefferzahl — der Einstieg ins Cockpit."""
    return [ZEILEN[schluessel](db, principal, **filter) for schluessel in ZEILEN]
