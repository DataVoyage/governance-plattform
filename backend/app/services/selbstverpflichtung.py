"""Selbstverpflichtungs-Modul (Architektur 8.4, Leitdokument A.10).

Die Aussagen aus A.10.2 und A.10.3 sind strukturierte Checkboxen, nicht
Freitext: jede nummerierte Aussage ist ein eigener Wahrheitswert mit optionalem
Kommentar. Ein Freitextfeld waere weder auswertbar noch pruefbar — und genau
die Auswertbarkeit traegt Cockpit und Lenkung.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import Principal, verlange
from app.models.base import now_utc
from app.models.enums import SelbstverpflichtungTyp
from app.models.governance import Prozessobjekt, Selbstverpflichtung, ToolObjekt
from app.services import konfiguration
from app.services.asset import darf_tool_schreiben
from app.services.changelog import protokolliere_erstellung
from app.services.prozess import Ungueltig, darf_schreiben


@dataclass(frozen=True)
class Aussage:
    id: str
    text: str


#: Leitdokument A.10.2 — Selbstverpflichtung des Prozesseigners.
AUSSAGEN_PROZESSEIGNER: tuple[Aussage, ...] = (
    Aussage("P1", "Das Prozessobjekt ist vollstaendig und aktuell beschrieben."),
    Aussage("P2", "Die Bewertung wurde nach bestem Wissen und vollstaendig durchgefuehrt."),
    Aussage(
        "P3",
        "Alle Input- und Output-Datenobjekte sind referenziert und korrekt kategorisiert.",
    ),
    Aussage("P4", "Eine Stellvertretung ist benannt und ueber ihre Rolle informiert."),
    Aussage(
        "P5",
        "Bei Aenderungen an Zweck, verarbeiteten Daten oder Reichweite wird neu bewertet.",
    ),
    Aussage("P6", "Die ausgeloesten Massnahmenklassen sind bekannt und werden umgesetzt."),
)

#: Leitdokument A.10.3 — Selbstverpflichtung des technischen Owners.
AUSSAGEN_TECHNISCHER_OWNER: tuple[Aussage, ...] = (
    Aussage(
        "T1",
        "Das Tool-Objekt laeuft im vorgesehenen Rahmen: nur die freigegebenen "
        "Datenobjekte, die freigegebene Reichweite, die freigegebenen externen Ziele.",
    ),
    Aussage("T2", "Die zentrale Unternehmensidentitaet wird nicht umgangen."),
    Aussage("T3", "Es werden keine statischen Zugangsdaten verwendet."),
    Aussage("T4", "Zugriffe sind nachvollziehbar protokolliert."),
    Aussage("T5", "Abhaengigkeiten und Betriebsverantwortung sind dokumentiert."),
    Aussage(
        "T6",
        "Bei einer Ueberschreitung des Rahmens wird unverzueglich ein Gate-2-Vorgang eingereicht.",
    ),
)

KATALOG: dict[SelbstverpflichtungTyp, tuple[Aussage, ...]] = {
    SelbstverpflichtungTyp.PROZESSEIGNER: AUSSAGEN_PROZESSEIGNER,
    SelbstverpflichtungTyp.TECHNISCHER_OWNER: AUSSAGEN_TECHNISCHER_OWNER,
}


def pruefe_aussagen(typ: SelbstverpflichtungTyp, aussagen: dict[str, dict]) -> None:
    erwartet = {a.id for a in KATALOG[typ]}
    unbekannt = sorted(set(aussagen) - erwartet)
    if unbekannt:
        raise Ungueltig(f"Unbekannte Aussagen fuer diesen Typ: {', '.join(unbekannt)}")


def ist_vollstaendig(typ: SelbstverpflichtungTyp, aussagen: dict[str, dict]) -> bool:
    """Vollstaendig heisst: jede Aussage des Katalogs ist bestaetigt."""
    return all(bool(aussagen.get(a.id, {}).get("bestaetigt", False)) for a in KATALOG[typ])


def gueltig_bis(db: Session, tier: int | None, ab: datetime) -> datetime | None:
    """Ab Tier 3 gilt die jaehrliche Erneuerungspflicht (Leitdokument A.10.5)."""
    if tier is None or tier < 3:
        return None
    return ab + timedelta(days=konfiguration.lies_int(db, "selbstverpflichtung_gueltigkeit_tage"))


def abgeben(
    db: Session,
    principal: Principal,
    *,
    typ: SelbstverpflichtungTyp,
    prozess: Prozessobjekt | None = None,
    tool: ToolObjekt | None = None,
    aussagen: dict[str, dict],
) -> Selbstverpflichtung:
    """Nimmt eine Selbstverpflichtung entgegen; frueherer Stand bleibt erhalten."""
    if typ == SelbstverpflichtungTyp.PROZESSEIGNER:
        if prozess is None:
            raise Ungueltig("Eine Prozesseigner-Selbstverpflichtung braucht ein Prozessobjekt")
        verlange(
            darf_schreiben(db, principal, prozess.prozessgeber_org_id),
            "Die Selbstverpflichtung gibt der Prozesseigner ab",
        )
    else:
        if tool is None:
            raise Ungueltig("Eine Owner-Selbstverpflichtung braucht ein Tool-Objekt")
        verlange(
            darf_tool_schreiben(db, principal, tool),
            "Die Selbstverpflichtung gibt der technische Owner ab",
        )

    pruefe_aussagen(typ, aussagen)
    zeitpunkt = now_utc()
    tier = _tier_des_ziels(prozess, tool)
    eintrag = Selbstverpflichtung(
        typ=typ,
        prozessobjekt_id=prozess.id if prozess is not None else None,
        tool_objekt_id=tool.id if tool is not None else None,
        aussagen=aussagen,
        vollstaendig=ist_vollstaendig(typ, aussagen),
        abgegeben_von=principal.user_id,
        abgegeben_am=zeitpunkt,
        gueltig_bis=gueltig_bis(db, tier, zeitpunkt),
    )
    db.add(eintrag)
    db.flush()
    protokolliere_erstellung(db, eintrag, akteur_user_id=principal.user_id)
    return eintrag


def _tier_des_ziels(prozess: Prozessobjekt | None, tool: ToolObjekt | None) -> int | None:
    from app.services.asset import erbe_klassifikation
    from app.services.prozess import neueste_bewertung

    if prozess is not None:
        bewertung = neueste_bewertung(prozess)
        return bewertung.tier if bewertung is not None else None
    if tool is not None:
        return erbe_klassifikation(tool).tier
    return None


def aktuelle_fuer_prozess(db: Session, prozess_id: uuid.UUID) -> Selbstverpflichtung | None:
    return db.execute(
        select(Selbstverpflichtung)
        .where(Selbstverpflichtung.prozessobjekt_id == prozess_id)
        .order_by(Selbstverpflichtung.abgegeben_am.desc())
        .limit(1)
    ).scalar_one_or_none()


def aktuelle_fuer_tool(db: Session, tool_id: uuid.UUID) -> Selbstverpflichtung | None:
    return db.execute(
        select(Selbstverpflichtung)
        .where(Selbstverpflichtung.tool_objekt_id == tool_id)
        .order_by(Selbstverpflichtung.abgegeben_am.desc())
        .limit(1)
    ).scalar_one_or_none()


def historie_fuer_prozess(db: Session, prozess_id: uuid.UUID) -> list[Selbstverpflichtung]:
    return list(
        db.execute(
            select(Selbstverpflichtung)
            .where(Selbstverpflichtung.prozessobjekt_id == prozess_id)
            .order_by(Selbstverpflichtung.abgegeben_am.desc())
        ).scalars()
    )


def ist_abgelaufen(eintrag: Selbstverpflichtung, jetzt: datetime | None = None) -> bool:
    if eintrag.gueltig_bis is None:
        return False
    zeitpunkt = jetzt or datetime.now(UTC)
    frist = eintrag.gueltig_bis
    if frist.tzinfo is None:
        frist = frist.replace(tzinfo=UTC)
    return frist < zeitpunkt


def ist_gedeckt(db: Session, prozess: Prozessobjekt, jetzt: datetime | None = None) -> bool:
    """Liegt eine vollstaendige, nicht abgelaufene Selbstverpflichtung vor?"""
    eintrag = aktuelle_fuer_prozess(db, prozess.id)
    if eintrag is None or not eintrag.vollstaendig:
        return False
    return not ist_abgelaufen(eintrag, jetzt)
