"""Nachweis- und Konfigurationstabellen (Architektur 3.2, 6.6, 10.4)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import GUID, Base
from app.models.base import TimestampMixin, uuid_pk
from app.models.enums import ChangeAktion


class ChangeLog(Base):
    """Lueckenloser Nachweis (Leitdokument A.13.7) und Quelle der Delta-Abfrage.

    ``cursor`` ist eine monoton steigende Sequenznummer, keine Zeitangabe —
    robust gegen Uhrzeitverschiebungen zwischen Systemen (Architektur 7.3).
    Die Tabelle ist ausschliesslich anhaengend; es gibt keinen Schreibpfad in
    der Anwendung, der einen Eintrag aendert oder loescht (Architektur 10.4).
    """

    __tablename__ = "change_log"

    cursor: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[uuid.UUID] = mapped_column(GUID, default=uuid.uuid4, unique=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(GUID, index=True)
    aktion: Mapped[ChangeAktion] = mapped_column(String(16))
    vorher: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    nachher: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    akteur_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id"), nullable=True
    )
    akteur_beschreibung: Mapped[str] = mapped_column(String(255), default="")
    zeitpunkt: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Konfiguration(Base, TimestampMixin):
    """Inhaltliche Governance-Einstellungen (Architektur 6.6).

    Aenderbar durch die Governance-Rolle im laufenden Betrieb, ohne Deployment.
    """

    __tablename__ = "konfiguration"

    id: Mapped[uuid.UUID] = uuid_pk()
    schluessel: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    wert: Mapped[str] = mapped_column(Text)
    beschreibung: Mapped[str] = mapped_column(Text, default="")
