"""FastAPI-Abhaengigkeiten: Session, angemeldeter Nutzer, Service-Identitaet."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core.permissions import Principal, Zuweisung
from app.core.security import AuthError, claims_to_identity, verify_token
from app.db import get_db
from app.models.enums import Rolle, ScopeTyp
from app.models.organisation import Rollenzuweisung, User

DbSession = Annotated[Session, Depends(get_db)]
Konfig = Annotated[Settings, Depends(get_settings)]


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Anmeldung ueber die zentrale Unternehmensidentitaet erforderlich",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ", 1)[1].strip()


def hole_oder_lege_user_an(db: Session, subject: str, email: str, name: str) -> User:
    """Nutzer werden bei der ersten Anmeldung aus den Token-Claims uebernommen.

    Die Anwendung fuehrt keine eigene Nutzerverwaltung mit Passwoertern; das
    Identitaetssystem bleibt fuehrend (Architektur 10.1). Rollen werden davon
    unabhaengig durch die App-Administrator-Rolle vergeben.
    """
    user = db.execute(select(User).where(User.subject == subject)).scalar_one_or_none()
    if user is None:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is not None:
            user.subject = subject
    if user is None:
        user = User(subject=subject, email=email, name=name)
        db.add(user)
        db.flush()
    else:
        if user.name != name:
            user.name = name
        if user.email != email:
            user.email = email
    return user


#: Rollen, die ein Erstzugangs-Subject bei der ersten Anmeldung erhaelt.
BOOTSTRAP_ROLLEN = (Rolle.APP_ADMINISTRATOR, Rolle.GOVERNANCE)


def gewaehre_erstzugang(db: Session, user: User, settings: Settings) -> None:
    """Vergibt die Startrollen an ein konfiguriertes Erstzugangs-Subject.

    Idempotent: bestehende Zuweisungen werden nicht verdoppelt. Steht das
    Subject nicht in der Konfiguration, passiert nichts.
    """
    if user.subject not in settings.bootstrap_admin_list:
        return
    vorhanden = {
        z.rolle
        for z in db.execute(
            select(Rollenzuweisung).where(
                Rollenzuweisung.user_id == user.id,
                Rollenzuweisung.scope_typ == ScopeTyp.GLOBAL,
            )
        ).scalars()
    }
    for rolle in BOOTSTRAP_ROLLEN:
        if rolle not in vorhanden:
            db.add(Rollenzuweisung(user_id=user.id, rolle=rolle, scope_typ=ScopeTyp.GLOBAL))
    db.flush()


def lade_principal(db: Session, user: User) -> Principal:
    zuweisungen = db.execute(
        select(Rollenzuweisung).where(Rollenzuweisung.user_id == user.id)
    ).scalars()
    return Principal(
        user_id=user.id,
        email=user.email,
        name=user.name,
        zuweisungen=[Zuweisung(z.rolle, z.scope_typ, z.scope_id) for z in zuweisungen],
    )


def get_principal(
    db: DbSession,
    settings: Konfig,
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    token = _bearer(authorization)
    try:
        claims = verify_token(token, settings)
        subject, email, name = claims_to_identity(claims)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token nicht gueltig: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    user = hole_oder_lege_user_an(db, subject, email, name)
    gewaehre_erstzugang(db, user, settings)
    if not user.ist_aktiv:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nutzer ist deaktiviert")
    return lade_principal(db, user)


AktuellerNutzer = Annotated[Principal, Depends(get_principal)]


def get_service_client(
    settings: Konfig,
    x_service_token: Annotated[str | None, Header()] = None,
) -> str:
    """Service-Authentifizierung fuer die Governance-Query-API (Abschnitt 7.3).

    Andockende Anwendungen sind keine Personen; sie melden sich mit einem
    Service-Token an, nicht ueber den interaktiven OIDC-Fluss.
    """
    tokens = settings.service_token_map
    if not x_service_token or x_service_token not in tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gueltige Service-Authentifizierung erforderlich",
        )
    return tokens[x_service_token]


ServiceClient = Annotated[str, Depends(get_service_client)]
