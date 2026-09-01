"""Cockpit-Modul, HTTP-Schicht (Architektur 8.7).

Jede Zeile ist eine eigene, aufrufbare Ansicht; jeder Eintrag traegt sein
Zielmodul samt Filter mit, damit ein Klick direkt dort landet, wo die Sache
abgearbeitet wird.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import AktuellerNutzer, DbSession
from app.services import cockpit as cockpit_service

router = APIRouter(prefix="/cockpit", tags=["Cockpit"])


class EintragAus(BaseModel):
    id: uuid.UUID
    titel: str
    hinweis: str = ""
    ziel_modul: str = ""
    ziel_filter: dict[str, str] = Field(default_factory=dict)


class ZeileAus(BaseModel):
    schluessel: str
    titel: str
    beschreibung: str
    anzahl: int
    eintraege: list[EintragAus] = Field(default_factory=list)
    aggregat: dict | None = None


class ZeilenkopfAus(BaseModel):
    """Uebersicht ohne die Einzeltreffer — der Einstieg ins Cockpit."""

    schluessel: str
    titel: str
    beschreibung: str
    anzahl: int
    aggregat: dict | None = None


def _zu_schema(zeile: cockpit_service.Zeile) -> ZeileAus:
    return ZeileAus(
        schluessel=zeile.schluessel,
        titel=zeile.titel,
        beschreibung=zeile.beschreibung,
        anzahl=zeile.anzahl,
        eintraege=[EintragAus(**vars(e)) for e in zeile.eintraege],
        aggregat=zeile.aggregat,
    )


@router.get("", response_model=list[ZeilenkopfAus])
def uebersicht(
    principal: AktuellerNutzer, db: DbSession, fachbereich_id: uuid.UUID | None = None
) -> list[ZeilenkopfAus]:
    return [
        ZeilenkopfAus(
            schluessel=z.schluessel,
            titel=z.titel,
            beschreibung=z.beschreibung,
            anzahl=z.anzahl,
            aggregat=z.aggregat,
        )
        for z in cockpit_service.uebersicht(db, principal, fachbereich_id=fachbereich_id)
    ]


@router.get("/{schluessel}", response_model=ZeileAus)
def zeile(
    schluessel: str,
    principal: AktuellerNutzer,
    db: DbSession,
    fachbereich_id: uuid.UUID | None = None,
    eskalationsstufe: int | None = None,
) -> ZeileAus:
    return _zu_schema(
        cockpit_service.hole_zeile(
            db,
            principal,
            schluessel,
            fachbereich_id=fachbereich_id,
            eskalationsstufe=eskalationsstufe,
        )
    )
