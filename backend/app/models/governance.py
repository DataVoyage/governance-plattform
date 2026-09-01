"""Governance-Entitaeten (Architektur Abschnitt 3.2)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import GUID, Base, TZDateTime
from app.models.base import TimestampMixin, uuid_pk
from app.models.enums import (
    AlarmTyp,
    AssetStatus,
    Aufloesungsart,
    Ausfallfolge,
    ComplianceFarbe,
    GateStatus,
    GateTyp,
    Herkunft,
    Kundenkreis,
    LenkungStatus,
    ProzessStatus,
    Reichweite,
    SelbstverpflichtungTyp,
    Zugriffsart,
)

# --- n:m-Verknuepfungstabellen -------------------------------------------

prozess_input_datenobjekte = Table(
    "prozess_input_datenobjekte",
    Base.metadata,
    Column("prozessobjekt_id", GUID, ForeignKey("prozessobjekte.id"), primary_key=True),
    Column("datenobjekt_id", GUID, ForeignKey("datenobjekte.id"), primary_key=True),
)

prozess_output_datenobjekte = Table(
    "prozess_output_datenobjekte",
    Base.metadata,
    Column("prozessobjekt_id", GUID, ForeignKey("prozessobjekte.id"), primary_key=True),
    Column("datenobjekt_id", GUID, ForeignKey("datenobjekte.id"), primary_key=True),
)

prozess_kette = Table(
    "prozess_kette",
    Base.metadata,
    Column("vorgaenger_id", GUID, ForeignKey("prozessobjekte.id"), primary_key=True),
    Column("nachfolger_id", GUID, ForeignKey("prozessobjekte.id"), primary_key=True),
)

prozess_tool = Table(
    "prozess_tool",
    Base.metadata,
    Column("prozessobjekt_id", GUID, ForeignKey("prozessobjekte.id"), primary_key=True),
    Column("tool_objekt_id", GUID, ForeignKey("tool_objekte.id"), primary_key=True),
)


class ToolDatenobjekt(Base):
    """Tool liest oder schreibt ein Datenobjekt (Architektur 3.1)."""

    __tablename__ = "tool_datenobjekte"

    tool_objekt_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("tool_objekte.id"), primary_key=True
    )
    datenobjekt_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("datenobjekte.id"), primary_key=True
    )
    zugriffsart: Mapped[Zugriffsart] = mapped_column(String(24), default=Zugriffsart.LESEN)


# --- Prozessobjekt --------------------------------------------------------


class Prozessobjekt(Base, TimestampMixin):
    __tablename__ = "prozessobjekte"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255))
    owner_user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id"))
    # Pflichtfeld — kein Speichern ohne Stellvertretung (Architektur 3.2).
    stellvertretung_user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id"))
    prozessgeber_org_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("organisationseinheiten.id")
    )
    supplier: Mapped[str] = mapped_column(Text, default="")
    process_steps: Mapped[str] = mapped_column(Text, default="")
    output: Mapped[str] = mapped_column(Text, default="")
    customer: Mapped[Kundenkreis] = mapped_column(String(24), default=Kundenkreis.TEAM)
    ausfallfolge: Mapped[Ausfallfolge] = mapped_column(String(24), default=Ausfallfolge.KEINE)
    status: Mapped[ProzessStatus] = mapped_column(String(24), default=ProzessStatus.ENTWURF)

    # Abgeleitet, nie eingegeben (Leitdokument P1, Architektur 8.1).
    reichweite: Mapped[Reichweite | None] = mapped_column(String(24), nullable=True)
    kritikalitaet: Mapped[int] = mapped_column(Integer, default=0)
    mitbestimmung_flag: Mapped[bool] = mapped_column(Boolean, default=False)

    input_datenobjekte: Mapped[list[Datenobjekt]] = relationship(
        secondary=prozess_input_datenobjekte, back_populates="input_fuer_prozesse"
    )
    output_datenobjekte: Mapped[list[Datenobjekt]] = relationship(
        secondary=prozess_output_datenobjekte, back_populates="output_von_prozessen"
    )
    nachgelagert: Mapped[list[Prozessobjekt]] = relationship(
        secondary=prozess_kette,
        primaryjoin=id == prozess_kette.c.vorgaenger_id,
        secondaryjoin=id == prozess_kette.c.nachfolger_id,
        back_populates="vorgelagert",
    )
    vorgelagert: Mapped[list[Prozessobjekt]] = relationship(
        secondary=prozess_kette,
        primaryjoin=id == prozess_kette.c.nachfolger_id,
        secondaryjoin=id == prozess_kette.c.vorgaenger_id,
        back_populates="nachgelagert",
    )
    tool_objekte: Mapped[list[ToolObjekt]] = relationship(
        secondary=prozess_tool, back_populates="prozessobjekte"
    )
    umsetzungen: Mapped[list[ProzessUmsetzung]] = relationship(
        back_populates="prozessobjekt", cascade="all, delete-orphan"
    )
    bewertungen: Mapped[list[Bewertung]] = relationship(
        back_populates="prozessobjekt", cascade="all, delete-orphan"
    )


class ProzessUmsetzung(Base, TimestampMixin):
    """n:m Prozessobjekt zu LAND-Organisationseinheit (Architektur 4.2)."""

    __tablename__ = "prozess_umsetzungen"

    id: Mapped[uuid.UUID] = uuid_pk()
    prozessobjekt_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("prozessobjekte.id"))
    land_org_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("organisationseinheiten.id"))
    lokale_abweichung: Mapped[str | None] = mapped_column(Text, nullable=True)

    prozessobjekt: Mapped[Prozessobjekt] = relationship(back_populates="umsetzungen")

    __table_args__ = (
        UniqueConstraint("prozessobjekt_id", "land_org_id", name="uq_prozess_umsetzung"),
    )


# --- Bewertung ------------------------------------------------------------


class Bewertung(Base, TimestampMixin):
    """Versionierte Bewertung (Leitdokument A.8.5) — nie ueberschrieben."""

    __tablename__ = "bewertungen"

    id: Mapped[uuid.UUID] = uuid_pk()
    prozessobjekt_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("prozessobjekte.id"))
    ki_stufe: Mapped[int] = mapped_column(Integer)
    ds_stufe: Mapped[int] = mapped_column(Integer)
    mb_stufe: Mapped[int] = mapped_column(Integer)
    it_stufe: Mapped[int] = mapped_column(Integer)
    rg_stufe: Mapped[int] = mapped_column(Integer)
    ur_stufe: Mapped[int] = mapped_column(Integer)
    tier: Mapped[int] = mapped_column(Integer)
    gesperrt: Mapped[bool] = mapped_column(Boolean, default=False)
    vollstaendig: Mapped[bool] = mapped_column(Boolean, default=True)
    ausgeloeste_k_klassen: Mapped[list[str]] = mapped_column(JSON, default=list)
    antworten: Mapped[dict] = mapped_column(JSON, default=dict)
    bewertet_von: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id"))
    bewertet_am: Mapped[datetime] = mapped_column(TZDateTime())
    gueltig_bis: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)

    prozessobjekt: Mapped[Prozessobjekt] = relationship(back_populates="bewertungen")


class Alarm(Base, TimestampMixin):
    """Governance-Alarm, etwa EU-AI-Act-Verbotstatbestand (Architektur 8.2)."""

    __tablename__ = "alarme"

    id: Mapped[uuid.UUID] = uuid_pk()
    typ: Mapped[AlarmTyp] = mapped_column(String(48))
    prozessobjekt_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("prozessobjekte.id"), nullable=True
    )
    beschreibung: Mapped[str] = mapped_column(Text, default="")
    ausgeloest_von: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id"))
    quittiert: Mapped[bool] = mapped_column(Boolean, default=False)


# --- Assets ---------------------------------------------------------------


class Datenobjekt(Base, TimestampMixin):
    __tablename__ = "datenobjekte"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255))
    beschreibung: Mapped[str] = mapped_column(Text, default="")
    # Governance-gepflegtes Feld — vom Sync nie ueberschrieben (Architektur 7.2).
    kategorie: Mapped[str | None] = mapped_column(String(48), nullable=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id"), nullable=True
    )
    fachbereich_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("fachbereiche.id"), nullable=True
    )
    herkunft: Mapped[Herkunft] = mapped_column(String(16), default=Herkunft.MANUELL)
    quelle: Mapped[str | None] = mapped_column(String(128), nullable=True)
    externe_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[AssetStatus] = mapped_column(String(32), default=AssetStatus.BESTAETIGT)
    metadaten: Mapped[dict] = mapped_column(JSON, default=dict)

    input_fuer_prozesse: Mapped[list[Prozessobjekt]] = relationship(
        secondary=prozess_input_datenobjekte, back_populates="input_datenobjekte"
    )
    output_von_prozessen: Mapped[list[Prozessobjekt]] = relationship(
        secondary=prozess_output_datenobjekte, back_populates="output_datenobjekte"
    )

    __table_args__ = (UniqueConstraint("quelle", "externe_id", name="uq_datenobjekt_quelle"),)


class ToolObjekt(Base, TimestampMixin):
    __tablename__ = "tool_objekte"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255))
    beschreibung: Mapped[str] = mapped_column(Text, default="")
    technologie: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kategorie: Mapped[str | None] = mapped_column(String(48), nullable=True)
    technischer_owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id"), nullable=True
    )
    organisationseinheit_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("organisationseinheiten.id"), nullable=True
    )
    herkunft: Mapped[Herkunft] = mapped_column(String(16), default=Herkunft.MANUELL)
    quelle: Mapped[str | None] = mapped_column(String(128), nullable=True)
    externe_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[AssetStatus] = mapped_column(String(32), default=AssetStatus.BESTAETIGT)
    metadaten: Mapped[dict] = mapped_column(JSON, default=dict)
    letzte_aktivitaet_am: Mapped[datetime | None] = mapped_column(
        TZDateTime(), nullable=True
    )

    prozessobjekte: Mapped[list[Prozessobjekt]] = relationship(
        secondary=prozess_tool, back_populates="tool_objekte"
    )

    __table_args__ = (UniqueConstraint("quelle", "externe_id", name="uq_tool_quelle"),)


# --- Selbstverpflichtung, Gates, Compliance, Lenkung ----------------------


class Selbstverpflichtung(Base, TimestampMixin):
    """Strukturierte Checkliste (Leitdokument A.10.2/A.10.3), kein Freitext."""

    __tablename__ = "selbstverpflichtungen"

    id: Mapped[uuid.UUID] = uuid_pk()
    typ: Mapped[SelbstverpflichtungTyp] = mapped_column(String(32))
    prozessobjekt_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("prozessobjekte.id"), nullable=True
    )
    tool_objekt_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("tool_objekte.id"), nullable=True
    )
    # Struktur je Aussage: {"bestaetigt": bool, "kommentar": str}
    aussagen: Mapped[dict] = mapped_column(JSON, default=dict)
    vollstaendig: Mapped[bool] = mapped_column(Boolean, default=False)
    abgegeben_von: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id"))
    abgegeben_am: Mapped[datetime] = mapped_column(TZDateTime())
    gueltig_bis: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)
    erinnerung_gesendet_am: Mapped[datetime | None] = mapped_column(
        TZDateTime(), nullable=True
    )


class GateVorgang(Base, TimestampMixin):
    __tablename__ = "gate_vorgaenge"

    id: Mapped[uuid.UUID] = uuid_pk()
    prozessobjekt_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("prozessobjekte.id"))
    gate_typ: Mapped[GateTyp] = mapped_column(String(4))
    ausloeser: Mapped[str | None] = mapped_column(String(64), nullable=True)
    begruendung: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[GateStatus] = mapped_column(String(24), default=GateStatus.EINGEREICHT)
    eingereicht_von: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id"))
    entschieden_von: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id"), nullable=True
    )
    entscheidungskommentar: Mapped[str] = mapped_column(Text, default="")
    entschieden_am: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)


class ComplianceZustand(Base, TimestampMixin):
    """Zeitreihe je Tool-Objekt (Leitdokument A.13.3/A.13.4)."""

    __tablename__ = "compliance_zustaende"

    id: Mapped[uuid.UUID] = uuid_pk()
    tool_objekt_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("tool_objekte.id"))
    farbe: Mapped[ComplianceFarbe] = mapped_column(String(8))
    begruendung: Mapped[str] = mapped_column(Text, default="")
    abweichung_art: Mapped[str | None] = mapped_column(String(64), nullable=True)
    festgestellt_am: Mapped[datetime] = mapped_column(TZDateTime())
    festgestellt_von: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id"), nullable=True
    )


class Lenkungsvorgang(Base, TimestampMixin):
    """Leitdokument A.13.5 und A.13.6."""

    __tablename__ = "lenkungsvorgaenge"

    id: Mapped[uuid.UUID] = uuid_pk()
    tool_objekt_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("tool_objekte.id"))
    compliance_zustand_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("compliance_zustaende.id"), nullable=True
    )
    eskalationsstufe: Mapped[int] = mapped_column(Integer, default=1)
    frist: Mapped[datetime] = mapped_column(TZDateTime())
    zugewiesen_an: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id"), nullable=True
    )
    status: Mapped[LenkungStatus] = mapped_column(String(24), default=LenkungStatus.OFFEN)
    aufloesungsart: Mapped[Aufloesungsart | None] = mapped_column(String(32), nullable=True)
    aufloesung_bewertung_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("bewertungen.id"), nullable=True
    )
    aufgeloest_am: Mapped[datetime | None] = mapped_column(TZDateTime(), nullable=True)
    beschreibung: Mapped[str] = mapped_column(Text, default="")


class Benachrichtigung(Base, TimestampMixin):
    """Erinnerungen und Eskalationsmeldungen — hier persistiert, Versand extern."""

    __tablename__ = "benachrichtigungen"

    id: Mapped[uuid.UUID] = uuid_pk()
    empfaenger_user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id"))
    anlass: Mapped[str] = mapped_column(String(64))
    betreff: Mapped[str] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text, default="")
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True)
    gelesen: Mapped[bool] = mapped_column(Boolean, default=False)
