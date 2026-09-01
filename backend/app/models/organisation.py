"""Organisationsmodell und Identitaeten (Architektur Abschnitt 4 und 5)."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import GUID, Base
from app.models.base import TimestampMixin, uuid_pk
from app.models.enums import Ebene, Rolle, ScopeTyp


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    subject: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    ist_aktiv: Mapped[bool] = mapped_column(Boolean, default=True)
    # Fuer Eskalationsstufe 2 (Leitdokument A.13.5): Benachrichtigung der Fuehrungskraft.
    fuehrungskraft_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id"), nullable=True
    )

    rollenzuweisungen: Mapped[list[Rollenzuweisung]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Fachbereich(Base, TimestampMixin):
    __tablename__ = "fachbereiche"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    quelle: Mapped[str | None] = mapped_column(String(128), nullable=True)
    externe_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    organisationseinheiten: Mapped[list[Organisationseinheit]] = relationship(
        back_populates="fachbereich", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("quelle", "externe_id", name="uq_fachbereich_quelle"),)


class Organisationseinheit(Base, TimestampMixin):
    __tablename__ = "organisationseinheiten"

    id: Mapped[uuid.UUID] = uuid_pk()
    fachbereich_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("fachbereiche.id"))
    ebene: Mapped[Ebene] = mapped_column(String(8))
    land_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    quelle: Mapped[str | None] = mapped_column(String(128), nullable=True)
    externe_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    fachbereich: Mapped[Fachbereich] = relationship(back_populates="organisationseinheiten")

    __table_args__ = (
        UniqueConstraint("fachbereich_id", "ebene", "land_code", name="uq_orgeinheit"),
        UniqueConstraint("quelle", "externe_id", name="uq_orgeinheit_quelle"),
    )


class Team(Base, TimestampMixin):
    """Importierte Stammdaten (P-App-4) — in dieser Anwendung nicht pflegbar."""

    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255))
    quelle: Mapped[str] = mapped_column(String(128))
    externe_id: Mapped[str] = mapped_column(String(255))
    owner_hinweis: Mapped[str | None] = mapped_column(String(320), nullable=True)
    organisationseinheit_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("organisationseinheiten.id"), nullable=True
    )

    __table_args__ = (UniqueConstraint("quelle", "externe_id", name="uq_team_quelle"),)


class Rollenzuweisung(Base, TimestampMixin):
    """Tripel ``(user, rolle, scope)`` aus Architektur Abschnitt 5.2."""

    __tablename__ = "rollenzuweisungen"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id"))
    rolle: Mapped[Rolle] = mapped_column(String(32))
    scope_typ: Mapped[ScopeTyp] = mapped_column(String(32))
    scope_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True)

    user: Mapped[User] = relationship(back_populates="rollenzuweisungen")

    __table_args__ = (
        UniqueConstraint("user_id", "rolle", "scope_typ", "scope_id", name="uq_rollenzuweisung"),
    )
