"""Prozess-Modul, HTTP-Schicht (Architektur 8.1)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import AktuellerNutzer, DbSession
from app.models.enums import ProzessStatus
from app.models.governance import ProzessUmsetzung
from app.schemas.prozess import (
    ProzessAendern,
    ProzessAnlegen,
    ProzessAus,
    UmsetzungAendern,
    UmsetzungAnlegen,
    UmsetzungAus,
)
from app.services import prozess as prozess_service

router = APIRouter(prefix="/prozesse", tags=["Prozesse"])


@router.get("", response_model=list[ProzessAus])
def liste(
    principal: AktuellerNutzer,
    db: DbSession,
    fachbereich_id: uuid.UUID | None = None,
    status_filter: ProzessStatus | None = None,
) -> list[ProzessAus]:
    treffer = prozess_service.liste(
        db, principal, fachbereich_id=fachbereich_id, status=status_filter
    )
    return [prozess_service.zu_schema(p) for p in treffer]


@router.post("", response_model=ProzessAus, status_code=status.HTTP_201_CREATED)
def anlegen(daten: ProzessAnlegen, principal: AktuellerNutzer, db: DbSession) -> ProzessAus:
    return prozess_service.zu_schema(prozess_service.anlegen(db, principal, daten))


@router.get("/{prozess_id}", response_model=ProzessAus)
def detail(prozess_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> ProzessAus:
    return prozess_service.zu_schema(prozess_service.hole_sichtbar(db, principal, prozess_id))


@router.patch("/{prozess_id}", response_model=ProzessAus)
def aendern(
    prozess_id: uuid.UUID, daten: ProzessAendern, principal: AktuellerNutzer, db: DbSession
) -> ProzessAus:
    prozess = prozess_service.hole_sichtbar(db, principal, prozess_id)
    return prozess_service.zu_schema(prozess_service.aendern(db, principal, prozess, daten))


@router.post(
    "/{prozess_id}/umsetzungen",
    response_model=UmsetzungAus,
    status_code=status.HTTP_201_CREATED,
)
def umsetzung_anlegen(
    prozess_id: uuid.UUID,
    daten: UmsetzungAnlegen,
    principal: AktuellerNutzer,
    db: DbSession,
) -> ProzessUmsetzung:
    prozess = prozess_service.hole_sichtbar(db, principal, prozess_id)
    return prozess_service.umsetzung_anlegen(
        db, principal, prozess, daten.land_org_id, daten.lokale_abweichung
    )


@router.patch("/{prozess_id}/umsetzungen/{umsetzung_id}", response_model=UmsetzungAus)
def umsetzung_aendern(
    prozess_id: uuid.UUID,
    umsetzung_id: uuid.UUID,
    daten: UmsetzungAendern,
    principal: AktuellerNutzer,
    db: DbSession,
) -> ProzessUmsetzung:
    prozess = prozess_service.hole_sichtbar(db, principal, prozess_id)
    umsetzung = _hole_umsetzung(prozess, umsetzung_id)
    return prozess_service.umsetzung_aendern(db, principal, umsetzung, daten.lokale_abweichung)


@router.delete("/{prozess_id}/umsetzungen/{umsetzung_id}", status_code=status.HTTP_204_NO_CONTENT)
def umsetzung_entfernen(
    prozess_id: uuid.UUID,
    umsetzung_id: uuid.UUID,
    principal: AktuellerNutzer,
    db: DbSession,
) -> None:
    prozess = prozess_service.hole_sichtbar(db, principal, prozess_id)
    umsetzung = _hole_umsetzung(prozess, umsetzung_id)
    prozess_service.umsetzung_entfernen(db, principal, prozess, umsetzung)


def _hole_umsetzung(prozess, umsetzung_id: uuid.UUID) -> ProzessUmsetzung:
    for umsetzung in prozess.umsetzungen:
        if umsetzung.id == umsetzung_id:
            return umsetzung
    raise HTTPException(status_code=404, detail="Umsetzung nicht gefunden")
