"""Vertraege der Import-/Sync-API (Architektur 7.2).

Quellenunabhaengig: die Plattform kennt nur dieses Format, nie die Quelle
dahinter. Ein spaeterer GCP- oder Apps-Script-Adapter bedient denselben
Vertrag, ohne dass der Kern sich aendert (Architektur 7.4).
"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ImportTyp


class ImportDatensatz(BaseModel):
    model_config = ConfigDict(extra="forbid")

    typ: ImportTyp
    externe_id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    owner_hinweis: str | None = Field(default=None, max_length=320)
    metadaten: dict[str, Any] = Field(default_factory=dict)


class ImportAnfrage(BaseModel):
    quelle: str = Field(min_length=1, max_length=128)
    datensaetze: list[ImportDatensatz]


class Zusammenfuehrungsvorschlag(BaseModel):
    """Namensaehnlichkeit ohne ``externe_id``-Treffer wird nie automatisch
    zusammengefuehrt (Architektur 7.2) — ein falsch verknuepftes Tool-Objekt
    wuerde eine falsche Klassifikation erben."""

    typ: ImportTyp
    externe_id: str
    name: str
    kandidat_id: uuid.UUID
    kandidat_name: str
    begruendung: str


class ImportFehler(BaseModel):
    externe_id: str
    grund: str


class ImportErgebnis(BaseModel):
    quelle: str
    angelegt: int = 0
    aktualisiert: int = 0
    unveraendert: int = 0
    vorschlaege: list[Zusammenfuehrungsvorschlag] = Field(default_factory=list)
    fehler: list[ImportFehler] = Field(default_factory=list)
