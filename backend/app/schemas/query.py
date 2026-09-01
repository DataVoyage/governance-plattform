"""Vertraege der Governance-Query-API (Architektur 7.3).

Diese Schemata sind der veroeffentlichte Vertrag gegenueber andockenden
Anwendungen. Beispiele stehen bewusst mit dabei: die aus FastAPI erzeugte
OpenAPI-Dokumentation soll ohne weitere Bearbeitung verstaendlich sein.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TierAus(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"tier": 3, "profil": {"ki": 0, "ds": 3, "mb": 1, "it": 1, "rg": 2, "ur": 2}}
        }
    )

    tier: int = Field(description="1 bis 3; 3 ist die hoechste Stufe.")
    profil: dict[str, int] = Field(
        description="Stufen der sechs Themenbloecke: ki, ds, mb, it, rg, ur."
    )


class KKlassenAus(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"ausgeloest": ["K1", "K2", "K3", "K4", "K5", "K7", "K8", "K9"]}
        }
    )

    ausgeloest: list[str] = Field(description="Die aus dem Profil abgeleiteten Massnahmenklassen.")


class DatenobjektRef(BaseModel):
    id: str
    name: str


class ErlaubnisrahmenAus(BaseModel):
    """Schicht 1 aus Leitdokument A.13.2 — was das Tool-Objekt darf."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "erlaubte_datenobjekte": [
                    {"id": "6d0a…", "name": "Kreditorenstamm"},
                ],
                "erlaubte_reichweite": "bereich",
                "erlaubte_externe_ziele": ["sftp.partner.example"],
                "tier": 3,
                "quelle_prozess_ids": ["1f2e…"],
            }
        }
    )

    erlaubte_datenobjekte: list[DatenobjektRef] = Field(
        description="Vereinigung der Datenobjekte aller verknuepften Prozessobjekte."
    )
    erlaubte_reichweite: str | None = Field(
        default=None, description="Hoechste geerbte Reichweite; null ohne Prozesskante."
    )
    erlaubte_externe_ziele: list[str] = Field(
        default_factory=list,
        description="Von der Governance erklaerte externe Ziele. Ein neues Ziel loest Gate 2 aus.",
    )
    tier: int | None = Field(default=None, description="Hoechstes geerbtes Tier.")
    quelle_prozess_ids: list[str] = Field(
        default_factory=list, description="Die Prozessobjekte, aus denen der Rahmen stammt."
    )


class AenderungAus(BaseModel):
    entity_type: str
    entity_id: str
    aktion: str
    zeitpunkt: str
    cursor: int


class AenderungenAus(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "changes": [
                    {
                        "entity_type": "bewertung",
                        "entity_id": "9a1c…",
                        "aktion": "erstellt",
                        "zeitpunkt": "2026-09-01T10:00:00+00:00",
                        "cursor": 10482,
                    }
                ],
                "naechster_cursor": 10483,
            }
        }
    )

    changes: list[AenderungAus]
    naechster_cursor: int = Field(
        description="Beim naechsten Lauf als 'since' mitgeben. Der Cursor ist eine "
        "Sequenznummer, keine Zeitangabe."
    )
