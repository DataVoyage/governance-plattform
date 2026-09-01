"""Anmeldung und Selbstauskunft (Architektur 10.1)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from app.api.deps import AktuellerNutzer, DbSession, Konfig, hole_oder_lege_user_an
from app.core.security import issue_dev_token
from app.models.organisation import Rollenzuweisung
from app.schemas.organisation import ProfilAus, RollenzuweisungAus

router = APIRouter(prefix="/auth", tags=["Anmeldung"])


class DevTokenAnfrage(BaseModel):
    subject: str
    email: EmailStr
    name: str


class TokenAus(BaseModel):
    access_token: str
    token_type: str = "Bearer"


@router.post("/dev-token", response_model=TokenAus)
def dev_token(anfrage: DevTokenAnfrage, db: DbSession, settings: Konfig) -> TokenAus:
    """Stellt lokal ein Token aus — ausschliesslich im Entwicklungsmodus.

    In Produktion ist ``GP_AUTH_DEV_MODE`` aus und diese Route antwortet mit
    404, damit es keinen zweiten Anmeldeweg neben der zentralen Identitaet
    gibt (Architektur 10.1).
    """
    if not settings.auth_dev_mode:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nicht verfuegbar")
    hole_oder_lege_user_an(db, anfrage.subject, str(anfrage.email), anfrage.name)
    return TokenAus(
        access_token=issue_dev_token(settings, anfrage.subject, str(anfrage.email), anfrage.name)
    )


@router.get("/me", response_model=ProfilAus)
def profil(principal: AktuellerNutzer, db: DbSession) -> ProfilAus:
    zuweisungen = db.execute(
        select(Rollenzuweisung).where(Rollenzuweisung.user_id == principal.user_id)
    ).scalars()
    return ProfilAus(
        id=principal.user_id,
        email=principal.email,
        name=principal.name,
        rollen=[RollenzuweisungAus.model_validate(z) for z in zuweisungen],
    )
