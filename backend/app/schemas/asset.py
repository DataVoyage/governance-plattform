"""Vertraege des Asset-Management-Moduls (Architektur 8.3)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AssetStatus, Datenkategorie, Herkunft, Zugriffsart


class GeerbtAus(BaseModel):
    """Maximum-Vererbung ueber alle Prozesskanten (Leitdokument A.4.4)."""

    kritikalitaet: int = 0
    reichweite: str | None = None
    tier: int | None = None
    mitbestimmung_flag: bool = False
    k_klassen: list[str] = Field(default_factory=list)
    quelle_prozess_ids: list[uuid.UUID] = Field(default_factory=list)


class ToolAnlegen(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    beschreibung: str = ""
    technologie: str | None = Field(default=None, max_length=64)
    kategorie: str | None = Field(default=None, max_length=48)
    technischer_owner_user_id: uuid.UUID | None = None
    organisationseinheit_id: uuid.UUID | None = None


class ToolAendern(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    beschreibung: str | None = None
    technologie: str | None = Field(default=None, max_length=64)
    kategorie: str | None = Field(default=None, max_length=48)
    technischer_owner_user_id: uuid.UUID | None = None
    organisationseinheit_id: uuid.UUID | None = None
    metadaten: dict[str, Any] | None = None


class ToolAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    beschreibung: str
    technologie: str | None = None
    kategorie: str | None = None
    technischer_owner_user_id: uuid.UUID | None = None
    organisationseinheit_id: uuid.UUID | None = None
    herkunft: Herkunft
    quelle: str | None = None
    externe_id: str | None = None
    status: AssetStatus
    metadaten: dict[str, Any] = Field(default_factory=dict)
    letzte_aktivitaet_am: datetime | None = None
    prozessobjekt_ids: list[uuid.UUID] = Field(default_factory=list)
    geerbt: GeerbtAus = Field(default_factory=GeerbtAus)
    #: Bei importierten Datensaetzen am Ursprungssystem zu pflegen.
    schreibgeschuetzte_felder: list[str] = Field(default_factory=list)


class DatenobjektAnlegen(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    beschreibung: str = ""
    kategorie: Datenkategorie | None = None
    owner_user_id: uuid.UUID | None = None
    fachbereich_id: uuid.UUID | None = None


class DatenobjektAendern(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    beschreibung: str | None = None
    kategorie: Datenkategorie | None = None
    owner_user_id: uuid.UUID | None = None
    fachbereich_id: uuid.UUID | None = None
    metadaten: dict[str, Any] | None = None


class DatenobjektAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    beschreibung: str
    kategorie: Datenkategorie | None = None
    owner_user_id: uuid.UUID | None = None
    fachbereich_id: uuid.UUID | None = None
    herkunft: Herkunft
    quelle: str | None = None
    externe_id: str | None = None
    status: AssetStatus
    metadaten: dict[str, Any] = Field(default_factory=dict)
    schreibgeschuetzte_felder: list[str] = Field(default_factory=list)


class ProzessVerknuepfung(BaseModel):
    prozessobjekt_id: uuid.UUID


class DatenobjektVerknuepfung(BaseModel):
    datenobjekt_id: uuid.UUID
    zugriffsart: Zugriffsart = Zugriffsart.LESEN


class ToolDatenobjektAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tool_objekt_id: uuid.UUID
    datenobjekt_id: uuid.UUID
    zugriffsart: Zugriffsart
