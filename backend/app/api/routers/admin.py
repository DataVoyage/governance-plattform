"""Nutzer- und Rollenverwaltung — ausschliesslich App-Administrator (Matrix 5.3)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import AktuellerNutzer, DbSession
from app.core.permissions import verlange
from app.models.organisation import Organisationseinheit, Rollenzuweisung, User
from app.schemas.organisation import (
    RollenzuweisungAnlegen,
    RollenzuweisungAus,
    UserAnlegen,
    UserAus,
)
from app.services.changelog import protokolliere_erstellung, protokolliere_loeschung

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/users", response_model=list[UserAus])
def liste_users(principal: AktuellerNutzer, db: DbSession) -> list[User]:
    verlange(
        principal.ist_administrator or principal.sieht_global,
        "Nutzerliste ist der App-Administrator- und den globalen Rollen vorbehalten",
    )
    return list(db.execute(select(User).order_by(User.name)).scalars())


@router.post("/users", response_model=UserAus, status_code=status.HTTP_201_CREATED)
def lege_user_an(daten: UserAnlegen, principal: AktuellerNutzer, db: DbSession) -> User:
    verlange(principal.ist_administrator, "Nutzer verwaltet nur der App-Administrator")
    bestehend = db.execute(select(User).where(User.email == str(daten.email))).scalar_one_or_none()
    if bestehend is not None:
        raise HTTPException(status_code=409, detail="Nutzer mit dieser E-Mail existiert bereits")
    user = User(
        subject=daten.subject or f"vorangelegt:{daten.email}",
        email=str(daten.email),
        name=daten.name,
        fuehrungskraft_user_id=daten.fuehrungskraft_user_id,
    )
    db.add(user)
    db.flush()
    protokolliere_erstellung(db, user, akteur_user_id=principal.user_id)
    return user


@router.get("/rollenzuweisungen", response_model=list[RollenzuweisungAus])
def liste_rollen(
    principal: AktuellerNutzer, db: DbSession, user_id: uuid.UUID | None = None
) -> list[Rollenzuweisung]:
    verlange(
        principal.ist_administrator or principal.sieht_global,
        "Rollenuebersicht ist der App-Administrator- und den globalen Rollen vorbehalten",
    )
    stmt = select(Rollenzuweisung)
    if user_id is not None:
        stmt = stmt.where(Rollenzuweisung.user_id == user_id)
    return list(db.execute(stmt).scalars())


@router.post(
    "/rollenzuweisungen", response_model=RollenzuweisungAus, status_code=status.HTTP_201_CREATED
)
def weise_rolle_zu(
    daten: RollenzuweisungAnlegen, principal: AktuellerNutzer, db: DbSession
) -> Rollenzuweisung:
    verlange(principal.ist_administrator, "Rollen vergibt nur der App-Administrator")
    if db.get(User, daten.user_id) is None:
        raise HTTPException(status_code=404, detail="Nutzer nicht gefunden")
    if (
        daten.scope_typ == "organisationseinheit"
        and db.get(Organisationseinheit, daten.scope_id) is None
    ):
        raise HTTPException(status_code=404, detail="Organisationseinheit nicht gefunden")
    bestehend = db.execute(
        select(Rollenzuweisung).where(
            Rollenzuweisung.user_id == daten.user_id,
            Rollenzuweisung.rolle == daten.rolle,
            Rollenzuweisung.scope_typ == daten.scope_typ,
            Rollenzuweisung.scope_id == daten.scope_id,
        )
    ).scalar_one_or_none()
    if bestehend is not None:
        return bestehend
    zuweisung = Rollenzuweisung(**daten.model_dump())
    db.add(zuweisung)
    db.flush()
    protokolliere_erstellung(db, zuweisung, akteur_user_id=principal.user_id)
    return zuweisung


@router.delete("/rollenzuweisungen/{zuweisung_id}", status_code=status.HTTP_204_NO_CONTENT)
def entziehe_rolle(zuweisung_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> None:
    verlange(principal.ist_administrator, "Rollen entzieht nur der App-Administrator")
    zuweisung = db.get(Rollenzuweisung, zuweisung_id)
    if zuweisung is None:
        raise HTTPException(status_code=404, detail="Rollenzuweisung nicht gefunden")
    protokolliere_loeschung(db, zuweisung, akteur_user_id=principal.user_id)
    db.delete(zuweisung)
    db.flush()
