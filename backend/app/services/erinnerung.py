"""Erinnerungen zur jaehrlichen Erneuerung (Architektur 8.4).

Der Vorlauf steht in der ``konfiguration``-Tabelle und ist von der
Governance-Rolle im laufenden Betrieb aenderbar (Architektur 6.6) — er ist
Governance-Inhalt, keine technische Einstellung.

Benachrichtigungen werden hier nur erzeugt und persistiert; der Versand ist
Sache eines nachgelagerten Systems. Damit bleibt der Nachweis, wer wann woran
erinnert wurde, in dieser Anwendung, ohne dass sie ein Mailsystem betreiben
muss.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.governance import Benachrichtigung, Prozessobjekt, Selbstverpflichtung, ToolObjekt
from app.services import konfiguration

ANLASS_ERINNERUNG = "selbstverpflichtung_laeuft_ab"
ANLASS_UEBERFAELLIG = "selbstverpflichtung_ueberfaellig"


@dataclass
class Erinnerungslauf:
    erinnert: list[uuid.UUID] = field(default_factory=list)
    ueberfaellig: list[uuid.UUID] = field(default_factory=list)


def _als_utc(zeitpunkt: datetime | None) -> datetime | None:
    if zeitpunkt is None:
        return None
    return zeitpunkt if zeitpunkt.tzinfo is not None else zeitpunkt.replace(tzinfo=UTC)


def _empfaenger(db: Session, eintrag: Selbstverpflichtung) -> uuid.UUID:
    """Der zustaendige Owner — sonst ersatzweise, wer zuletzt abgegeben hat."""
    if eintrag.prozessobjekt_id is not None:
        prozess = db.get(Prozessobjekt, eintrag.prozessobjekt_id)
        if prozess is not None:
            return prozess.owner_user_id
    if eintrag.tool_objekt_id is not None:
        tool = db.get(ToolObjekt, eintrag.tool_objekt_id)
        if tool is not None and tool.technischer_owner_user_id is not None:
            return tool.technischer_owner_user_id
    return eintrag.abgegeben_von


def _bereits_benachrichtigt(db: Session, eintrag: Selbstverpflichtung, anlass: str) -> bool:
    return (
        db.execute(
            select(Benachrichtigung)
            .where(
                Benachrichtigung.entity_type == "selbstverpflichtungen",
                Benachrichtigung.entity_id == eintrag.id,
                Benachrichtigung.anlass == anlass,
            )
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )


def _benachrichtige(
    db: Session, eintrag: Selbstverpflichtung, anlass: str, betreff: str, text: str
) -> Benachrichtigung:
    nachricht = Benachrichtigung(
        empfaenger_user_id=_empfaenger(db, eintrag),
        anlass=anlass,
        betreff=betreff,
        text=text,
        entity_type="selbstverpflichtungen",
        entity_id=eintrag.id,
    )
    db.add(nachricht)
    db.flush()
    return nachricht


def lauf(db: Session, jetzt: datetime | None = None) -> Erinnerungslauf:
    """Ein Durchlauf ueber alle befristeten Selbstverpflichtungen.

    Idempotent: je Selbstverpflichtung und Anlass entsteht hoechstens eine
    Benachrichtigung, damit ein taeglicher CronJob nicht taeglich mahnt.
    """
    zeitpunkt = jetzt or datetime.now(UTC)
    vorlauf = timedelta(
        days=konfiguration.lies_int(db, "selbstverpflichtung_erinnerung_vorlauf_tage")
    )
    ergebnis = Erinnerungslauf()

    eintraege = db.execute(
        select(Selbstverpflichtung).where(Selbstverpflichtung.gueltig_bis.is_not(None))
    ).scalars()
    for eintrag in eintraege:
        frist = _als_utc(eintrag.gueltig_bis)
        assert frist is not None
        if frist < zeitpunkt:
            if not _bereits_benachrichtigt(db, eintrag, ANLASS_UEBERFAELLIG):
                _benachrichtige(
                    db,
                    eintrag,
                    ANLASS_UEBERFAELLIG,
                    "Selbstverpflichtung ueberfaellig",
                    "Die Frist ist ohne Bestaetigung verstrichen. Der Datensatz erscheint "
                    "im Cockpit unter 'ueberfaellige Selbstverpflichtungen'.",
                )
                ergebnis.ueberfaellig.append(eintrag.id)
            continue
        if frist - vorlauf <= zeitpunkt and eintrag.erinnerung_gesendet_am is None:
            _benachrichtige(
                db,
                eintrag,
                ANLASS_ERINNERUNG,
                "Selbstverpflichtung laeuft ab",
                f"Die Selbstverpflichtung laeuft am {frist.date().isoformat()} ab und "
                "ist vorher zu erneuern.",
            )
            eintrag.erinnerung_gesendet_am = zeitpunkt
            db.flush()
            ergebnis.erinnert.append(eintrag.id)
    return ergebnis


def ueberfaellige(db: Session, jetzt: datetime | None = None) -> list[Selbstverpflichtung]:
    """Cockpit-Zeile „ueberfaellige Selbstverpflichtungen" (Architektur 8.7)."""
    zeitpunkt = jetzt or datetime.now(UTC)
    eintraege = db.execute(
        select(Selbstverpflichtung).where(Selbstverpflichtung.gueltig_bis.is_not(None))
    ).scalars()
    return [e for e in eintraege if (_als_utc(e.gueltig_bis) or zeitpunkt) < zeitpunkt]


def benachrichtigungen(db: Session, empfaenger_user_id: uuid.UUID) -> list[Benachrichtigung]:
    return list(
        db.execute(
            select(Benachrichtigung)
            .where(Benachrichtigung.empfaenger_user_id == empfaenger_user_id)
            .order_by(Benachrichtigung.erstellt_am.desc())
        ).scalars()
    )
