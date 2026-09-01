"""Vertraege des Prozess-Moduls (Architektur 8.1).

Genau die zehn Felder aus Leitdokument A.5 sind eingebbar. Reichweite,
Kritikalitaet und Mitbestimmungsflag sind abgeleitet und erscheinen nur in der
Ausgabe — sie werden nie entgegengenommen (Leitdokument P1).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Ausfallfolge, Kundenkreis, ProzessStatus, Reichweite


class ProzessBasis(BaseModel):
    # 1
    name: str = Field(min_length=1, max_length=255)
    # 2
    owner_user_id: uuid.UUID
    # 3 — Pflichtfeld, kein Speichern ohne Stellvertretung
    stellvertretung_user_id: uuid.UUID
    # 4
    prozessgeber_org_id: uuid.UUID
    # 5
    supplier: str = ""
    # 6 — Referenz auf bestehende Datenobjekte, kein Freitext (Leitdokument P5)
    input_datenobjekt_ids: list[uuid.UUID] = Field(default_factory=list)
    # 7
    process_steps: str = ""
    # 8
    output: str = ""
    # 9
    customer: Kundenkreis
    # 10
    ausfallfolge: Ausfallfolge


class ProzessAnlegen(ProzessBasis):
    umsetzung_land_org_ids: list[uuid.UUID] = Field(default_factory=list)
    vorgelagert_ids: list[uuid.UUID] = Field(default_factory=list)
    nachgelagert_ids: list[uuid.UUID] = Field(default_factory=list)


class ProzessAendern(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    owner_user_id: uuid.UUID | None = None
    stellvertretung_user_id: uuid.UUID | None = None
    prozessgeber_org_id: uuid.UUID | None = None
    supplier: str | None = None
    input_datenobjekt_ids: list[uuid.UUID] | None = None
    process_steps: str | None = None
    output: str | None = None
    customer: Kundenkreis | None = None
    ausfallfolge: Ausfallfolge | None = None
    status: ProzessStatus | None = None
    vorgelagert_ids: list[uuid.UUID] | None = None
    nachgelagert_ids: list[uuid.UUID] | None = None


class UmsetzungAnlegen(BaseModel):
    land_org_id: uuid.UUID
    lokale_abweichung: str | None = None


class UmsetzungAendern(BaseModel):
    lokale_abweichung: str | None = None


class UmsetzungAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prozessobjekt_id: uuid.UUID
    land_org_id: uuid.UUID
    lokale_abweichung: str | None = None


class ProzessAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    owner_user_id: uuid.UUID
    stellvertretung_user_id: uuid.UUID
    prozessgeber_org_id: uuid.UUID
    supplier: str
    process_steps: str
    output: str
    customer: Kundenkreis
    ausfallfolge: Ausfallfolge
    status: ProzessStatus
    erstellt_am: datetime
    geaendert_am: datetime

    # Abgeleitet und schreibgeschuetzt (Architektur 8.1)
    reichweite: Reichweite | None = None
    kritikalitaet: int = 0
    mitbestimmung_flag: bool = False

    input_datenobjekt_ids: list[uuid.UUID] = Field(default_factory=list)
    output_datenobjekt_ids: list[uuid.UUID] = Field(default_factory=list)
    vorgelagert_ids: list[uuid.UUID] = Field(default_factory=list)
    nachgelagert_ids: list[uuid.UUID] = Field(default_factory=list)
    umsetzungen: list[UmsetzungAus] = Field(default_factory=list)
    tool_objekt_ids: list[uuid.UUID] = Field(default_factory=list)
