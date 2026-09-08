"""Vertraege der Anforderungsklassen und der Technologiematrix (A.9, Teil C.1)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Befundart, Klassenbewertung


class AnforderungsklasseAus(BaseModel):
    """Eine Klasse mit Name, Zweck und Ausloeserbedingung (Leitdokument A.9.2)."""

    schluessel: str
    name: str
    zweck: str
    ausloeser: str


class TechnologieAus(BaseModel):
    schluessel: str
    name: str


class MatrixfeldAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    technologie: str
    k_klasse: str
    bewertung: Klassenbewertung
    begruendung: str
    geaendert_am: datetime | None = None


class MatrixfeldSetzen(BaseModel):
    bewertung: Klassenbewertung
    #: Pflicht: ein Matrixfeld entscheidet ueber den Betrieb einer Technologie.
    begruendung: str = Field(min_length=1)


class UrKompositionsfeldAus(BaseModel):
    """Ein Feld der Tabelle Ausfallfolge x Reichweite (Leitdokument A.8.4)."""

    model_config = ConfigDict(from_attributes=True)

    ausfallfolge: str
    reichweite: str
    stufe: int
    begruendung: str = ""
    geaendert_am: datetime | None = None


class UrKompositionsfeldSetzen(BaseModel):
    stufe: int = Field(ge=0, le=3)
    #: Pflicht: ein Feld hier entscheidet ueber das Tier ganzer Prozessgruppen.
    begruendung: str = Field(min_length=1)


class BefundAus(BaseModel):
    tool_id: uuid.UUID
    tool_name: str
    technologie: str | None = None
    k_klasse: str
    art: Befundart
    begruendung: str = ""
    massnahme: str = ""
    offen: bool = False


class ToolbefundAus(BaseModel):
    tool_id: uuid.UUID
    tool_name: str
    technologie: str | None = None
    k_klassen: list[str] = Field(default_factory=list)
    befunde: list[BefundAus] = Field(default_factory=list)
    ausschluss: bool = False
    offen: int = 0


class KompensationSetzen(BaseModel):
    massnahme: str = Field(min_length=1)


class KompensationAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tool_objekt_id: uuid.UUID
    k_klasse: str
    massnahme: str
    erfasst_von: uuid.UUID
    erfasst_am: datetime
