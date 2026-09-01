"""Gemeinsame Bausteine der Modellschicht."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import GUID, TZDateTime


def now_utc() -> datetime:
    return datetime.now(UTC)


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(GUID, primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    erstellt_am: Mapped[datetime] = mapped_column(
        TZDateTime, default=now_utc, server_default=func.now()
    )
    geaendert_am: Mapped[datetime] = mapped_column(
        TZDateTime, default=now_utc, onupdate=now_utc, server_default=func.now()
    )
