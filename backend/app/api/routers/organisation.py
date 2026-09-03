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
from app.models.enums import Ebene, Rolle
from app.models.organisation import Fachbereich, Organisationseinheit
from app.schemas.organisation import (
    FachbereichAnlegen,
    FachbereichAus,
    OrganisationseinheitAnlegen,
    OrganisationseinheitAus,
    PersonAus,
)
from app.services import verwaltung as verwaltung_service
from app.services.changelog import protokolliere_erstellung

router = APIRouter(tags=["Organisation"])


@router.get("/fachbereiche", response_model=list[FachbereichAus])
def liste_fachbereiche(
    principal: AktuellerNutzer, db: DbSession, fuer_rolle: Rolle | None = None
) -> list[Fachbereich]:
    """Die Grobgliederung sieht jede angemeldete Rolle — sie ist Kontext, nicht Gegenstand.

    Mit ``fuer_rolle`` wird daraus eine Auswahlliste: nur die Fachbereiche, in
    denen der Anfragende diese Rolle traegt. Ein Formular fragt immer so
    (docs/rollen-und-scopes.md, 6); wer nur anzeigen will, fragt ohne.
    """
    if fuer_rolle is not None:
        return verwaltung_service.fachbereiche_fuer_rolle(db, principal, fuer_rolle)
    return list(db.execute(select(Fachbereich).order_by(Fachbereich.name)).scalars())


@router.get("/personen", response_model=list[PersonAus])
def liste_personen(
    principal: AktuellerNutzer,
    db: DbSession,
    rolle: Rolle,
    fachbereich_id: uuid.UUID | None = None,
    organisationseinheit_id: uuid.UUID | None = None,
) -> list:
    """Wer diese Rolle in diesem Bereich traegt — fuer Owner- und Vertretungsfelder.

    Bis hierher luden die Formulare dafuer ``/admin/users``. Das ist die
    Nutzerverwaltung: sie antwortet jeder Fachrolle mit 403, und die Felder
    blieben leer — bei der Stellvertretung, die Pflicht ist, war das Formular
    damit nicht absendbar.
    """
    if fachbereich_id is None and organisationseinheit_id is None:
        raise HTTPException(
            status_code=422,
            detail="Ein Bereich gehört dazu: fachbereich_id oder organisationseinheit_id",
        )
    return verwaltung_service.personen_mit_rolle(
        db,
        principal,
        rolle,
        fachbereich_id=fachbereich_id,
        organisationseinheit_id=organisationseinheit_id,
    )


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
    fuer_rolle: Rolle | None = None,
) -> list[Organisationseinheit]:
    """Ohne ``fuer_rolle`` die ganze Struktur — sie ist Kontext und benennt Objekte.

    Mit ``fuer_rolle`` nur die Einheiten, in denen der Anfragende diese Rolle
    traegt: die Bereiche, die er in einem Formular belegen darf.
    """
    if fuer_rolle is not None:
        treffer = verwaltung_service.einheiten_fuer_rolle(db, principal, fuer_rolle)
        if fachbereich_id is not None:
            treffer = [e for e in treffer if e.fachbereich_id == fachbereich_id]
        if ebene is not None:
            treffer = [e for e in treffer if e.ebene == ebene]
        return treffer
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
