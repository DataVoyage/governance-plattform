"""Datenbank-Session und Basisklasse (Schicht ``Datenzugriff``, Abschnitt 6.4).

Die Anwendung laeuft auf PostgreSQL — in Produktion, in der Entwicklung und in
den Tests. Es gibt keinen zweiten Dialekt und deshalb auch keine
Dialektweichen: UUID-Spalten sind native ``uuid``, Zeitstempel sind
``timestamptz``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import Request
from sqlalchemy import DateTime, String, create_engine
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

#: UUID-Primaerschluessel, nativ in PostgreSQL.
GUID = PGUUID(as_uuid=True)

#: Zeitstempel mit Zeitzone; PostgreSQL liefert sie zeitzonenbehaftet zurueck.
TZDateTime = DateTime(timezone=True)


class Base(DeclarativeBase):
    type_annotation_map = {  # noqa: RUF012
        uuid.UUID: PGUUID(as_uuid=True),
        datetime: DateTime(timezone=True),
        str: String,
    }


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine():
    global _engine
    if _engine is None:
        kwargs: dict[str, Any] = {"pool_pre_ping": True, "future": True}
        _engine = create_engine(get_settings().database_url, **kwargs)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _SessionLocal


def reset_engine() -> None:
    """Nur fuer Tests: erzwingt Neuaufbau von Engine und Sessionmaker."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_db(request: Request) -> Session:
    """Liefert die Sitzung dieser Anfrage.

    Angelegt und abgeschlossen wird sie von ``sitzungs_middleware`` in
    ``app.main``. Der Commit gehoert dorthin und nicht in den Abbau dieser
    Abhaengigkeit: der laeuft, nachdem die Antwort die Anwendung verlassen hat.
    Ein Client, der auf ein ``201`` sofort mit einer Folgeanfrage reagiert,
    faende den eben angelegten Datensatz dann gelegentlich noch nicht — genau
    dieser Fehler war unter PostgreSQL reproduzierbar.
    """
    return request.state.db
