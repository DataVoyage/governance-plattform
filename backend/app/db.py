"""Datenbank-Session und Basisklasse (Schicht ``Datenzugriff``, Abschnitt 6.4)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

from sqlalchemy import CHAR, String, TypeDecorator, create_engine
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class GUID(TypeDecorator):
    """UUID-Spalte, die auf PostgreSQL nativ und sonst als CHAR(36) arbeitet.

    Die Anwendung laeuft produktiv auf PostgreSQL; die Testsuite laeuft gegen
    SQLite, damit sie ohne Container-Start reproduzierbar ist. Nur dieser
    Typ-Adapter, nicht die Fachlogik, kennt den Unterschied.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value: Any, dialect: Any) -> uuid.UUID | None:
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class Base(DeclarativeBase):
    type_annotation_map = {  # noqa: RUF012
        uuid.UUID: GUID,
        str: String,
    }


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine():
    global _engine
    if _engine is None:
        url = get_settings().database_url
        kwargs: dict[str, Any] = {"pool_pre_ping": True, "future": True}
        if url.startswith("sqlite"):
            kwargs.pop("pool_pre_ping")
        _engine = create_engine(url, **kwargs)
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


def get_db() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
