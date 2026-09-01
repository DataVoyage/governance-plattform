"""Fachbereiche und Organisationseinheiten (Architektur Abschnitt 4).

Der Regelweg ist der Import (P-App-4). Die Schreibrouten hier decken den Fall
ab, dass eine Einheit vor Anbindung der zentralen Entwicklungsplattform
manuell gebraucht wird — deshalb sind sie der Governance-Rolle vorbehalten.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import AktuellerNutzer, DbSession
from app.core.permissions import verlange
from app.models.enums import Ebene
from app.models.organisation import Fachbereich, Organisationseinheit
from app.schemas.organisation import (
    FachbereichAnlegen,
    FachbereichAus,
    OrganisationseinheitAnlegen,
    OrganisationseinheitAus,
)
from app.services.changelog import protokolliere_erstellung

router = APIRouter(tags=["Organisation"])


@router.get("/fachbereiche", response_model=list[FachbereichAus])
def liste_fachbereiche(principal: AktuellerNutzer, db: DbSession) -> list[Fachbereich]:
    del principal  # jede angemeldete Rolle darf die Grobgliederung sehen
    return list(db.execute(select(Fachbereich).order_by(Fachbereich.name)).scalars())


@router.post("/fachbereiche", response_model=FachbereichAus, status_code=status.HTTP_201_CREATED)
def lege_fachbereich_an(
    daten: FachbereichAnlegen, principal: AktuellerNutzer, db: DbSession
) -> Fachbereich:
    verlange(
        principal.ist_governance or principal.ist_administrator,
        "Fachbereiche legt die Governance- oder App-Administrator-Rolle an",
    )
    if db.execute(select(Fachbereich).where(Fachbereich.code == daten.code)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Code ist bereits vergeben")
    fachbereich = Fachbereich(name=daten.name, code=daten.code)
    db.add(fachbereich)
    db.flush()
    protokolliere_erstellung(db, fachbereich, akteur_user_id=principal.user_id)
    return fachbereich


@router.get("/organisationseinheiten", response_model=list[OrganisationseinheitAus])
def liste_organisationseinheiten(
    principal: AktuellerNutzer,
    db: DbSession,
    fachbereich_id: uuid.UUID | None = None,
    ebene: Ebene | None = None,
) -> list[Organisationseinheit]:
    del principal
    stmt = select(Organisationseinheit)
    if fachbereich_id is not None:
        stmt = stmt.where(Organisationseinheit.fachbereich_id == fachbereich_id)
    if ebene is not None:
        stmt = stmt.where(Organisationseinheit.ebene == ebene)
    return list(db.execute(stmt).scalars())


@router.post(
    "/organisationseinheiten",
    response_model=OrganisationseinheitAus,
    status_code=status.HTTP_201_CREATED,
)
def lege_organisationseinheit_an(
    daten: OrganisationseinheitAnlegen, principal: AktuellerNutzer, db: DbSession
) -> Organisationseinheit:
    verlange(
        principal.ist_governance or principal.ist_administrator,
        "Organisationseinheiten legt die Governance- oder App-Administrator-Rolle an",
    )
    if db.get(Fachbereich, daten.fachbereich_id) is None:
        raise HTTPException(status_code=404, detail="Fachbereich nicht gefunden")
    bestehend = db.execute(
        select(Organisationseinheit).where(
            Organisationseinheit.fachbereich_id == daten.fachbereich_id,
            Organisationseinheit.ebene == daten.ebene,
            Organisationseinheit.land_code == daten.land_code,
        )
    ).scalar_one_or_none()
    if bestehend is not None:
        raise HTTPException(status_code=409, detail="Diese Organisationseinheit existiert bereits")
    einheit = Organisationseinheit(**daten.model_dump())
    db.add(einheit)
    db.flush()
    protokolliere_erstellung(db, einheit, akteur_user_id=principal.user_id)
    return einheit
