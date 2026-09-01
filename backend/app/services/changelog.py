"""Lueckenloser Nachweis jeder schreibenden Aktion (Architektur 3.2, 10.4).

Es gibt genau einen Schreibpfad in den ``change_log`` — diesen hier. Dieselbe
Struktur traegt die Delta-Abfrage der Governance-Query-API (Abschnitt 7.3); es
existiert bewusst keine zweite, separate Protokollierung fuer Sync-Zwecke.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import ChangeLog
from app.models.base import now_utc
from app.models.enums import ChangeAktion


def _json_safe(wert: Any) -> Any:
    if isinstance(wert, uuid.UUID):
        return str(wert)
    if isinstance(wert, datetime | date):
        return wert.isoformat()
    if isinstance(wert, Decimal):
        return float(wert)
    if isinstance(wert, dict):
        return {k: _json_safe(v) for k, v in wert.items()}
    if isinstance(wert, list | tuple | set):
        return [_json_safe(v) for v in wert]
    return wert


def snapshot(objekt: Any) -> dict[str, Any]:
    """Serialisiert die Spaltenwerte einer ORM-Entitaet JSON-sicher."""
    mapper = objekt.__mapper__
    return {spalte.key: _json_safe(getattr(objekt, spalte.key)) for spalte in mapper.column_attrs}


def diff(vorher: dict[str, Any] | None, nachher: dict[str, Any] | None) -> dict[str, Any]:
    """Liefert nur die tatsaechlich veraenderten Felder als Vorher/Nachher-Paar."""
    vorher = vorher or {}
    nachher = nachher or {}
    geaendert: dict[str, Any] = {}
    for schluessel in set(vorher) | set(nachher):
        alt, neu = vorher.get(schluessel), nachher.get(schluessel)
        if alt != neu:
            geaendert[schluessel] = {"vorher": alt, "nachher": neu}
    return geaendert


def protokolliere(
    db: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    aktion: ChangeAktion,
    vorher: dict[str, Any] | None = None,
    nachher: dict[str, Any] | None = None,
    akteur_user_id: uuid.UUID | None = None,
    akteur_beschreibung: str = "",
) -> ChangeLog:
    eintrag = ChangeLog(
        entity_type=entity_type,
        entity_id=entity_id,
        aktion=aktion,
        vorher=vorher,
        nachher=nachher,
        akteur_user_id=akteur_user_id,
        akteur_beschreibung=akteur_beschreibung,
        zeitpunkt=now_utc(),
    )
    db.add(eintrag)
    db.flush()
    return eintrag


def protokolliere_erstellung(
    db: Session, objekt: Any, *, akteur_user_id: uuid.UUID | None = None, beschreibung: str = ""
) -> ChangeLog:
    return protokolliere(
        db,
        entity_type=objekt.__tablename__,
        entity_id=objekt.id,
        aktion=ChangeAktion.ERSTELLT,
        vorher=None,
        nachher=snapshot(objekt),
        akteur_user_id=akteur_user_id,
        akteur_beschreibung=beschreibung,
    )


def protokolliere_aenderung(
    db: Session,
    objekt: Any,
    vorher: dict[str, Any],
    *,
    akteur_user_id: uuid.UUID | None = None,
    beschreibung: str = "",
) -> ChangeLog | None:
    """Schreibt nur, wenn sich tatsaechlich etwas geaendert hat.

    Ein Speichern ohne inhaltliche Aenderung erzeugt keinen Eintrag — sonst
    wuerde der Nachweis mit Rauschen gefuellt und die Delta-Abfrage lieferte
    andockenden Anwendungen Arbeit ohne Anlass.
    """
    nachher = snapshot(objekt)
    veraendert = diff(vorher, nachher)
    veraendert.pop("geaendert_am", None)
    if not veraendert:
        return None
    return protokolliere(
        db,
        entity_type=objekt.__tablename__,
        entity_id=objekt.id,
        aktion=ChangeAktion.GEAENDERT,
        vorher=vorher,
        nachher=nachher,
        akteur_user_id=akteur_user_id,
        akteur_beschreibung=beschreibung,
    )


def protokolliere_loeschung(
    db: Session, objekt: Any, *, akteur_user_id: uuid.UUID | None = None, beschreibung: str = ""
) -> ChangeLog:
    return protokolliere(
        db,
        entity_type=objekt.__tablename__,
        entity_id=objekt.id,
        aktion=ChangeAktion.GELOESCHT,
        vorher=snapshot(objekt),
        nachher=None,
        akteur_user_id=akteur_user_id,
        akteur_beschreibung=beschreibung,
    )


def eintraege_seit(
    db: Session,
    *,
    since: int = 0,
    entity_types: list[str] | None = None,
    limit: int = 500,
) -> list[ChangeLog]:
    """Delta-Abfrage (Architektur 7.3): alles mit ``cursor > since``.

    Der Cursor ist zustandslos: derselbe ``since``-Wert liefert bei
    unveraenderter Datenlage dasselbe Ergebnis.
    """
    stmt = select(ChangeLog).where(ChangeLog.cursor > since)
    if entity_types:
        stmt = stmt.where(ChangeLog.entity_type.in_(entity_types))
    stmt = stmt.order_by(ChangeLog.cursor).limit(limit)
    return list(db.execute(stmt).scalars())
