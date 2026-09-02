"""Nutzer- und Rollenverwaltung — ausschliesslich App-Administrator (Matrix 5.3)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import AktuellerNutzer, DbSession
from app.core.permissions import verlange
from app.models.enums import Rolle, ScopeTyp
from app.models.organisation import Organisationseinheit, Rollenzuweisung, User
from app.schemas.organisation import (
    RollenzuweisungAnlegen,
    RollenzuweisungAus,
    UserAnlegen,
    UserAus,
)
from app.schemas.verwaltung import (
    RolleAus,
    UserAendern,
    WirkungAus,
)
from app.services import verwaltung as verwaltung_service
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


@router.patch("/users/{user_id}", response_model=UserAus)
def aendere_user(
    user_id: uuid.UUID, daten: UserAendern, principal: AktuellerNutzer, db: DbSession
) -> User:
    """Aktivstatus und Fuehrungskraft.

    Die Fuehrungskraft ist keine Zierde: ab Eskalationsstufe 2 geht die Meldung
    an sie (A.13.5). Ohne einen Weg, sie zu setzen, liefe die Eskalation an den
    Betroffenen selbst zurueck.
    """
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Nutzer nicht gefunden")
    gesetzt = daten.model_dump(exclude_unset=True)
    return verwaltung_service.aendere_user(
        db,
        principal,
        user,
        ist_aktiv=daten.ist_aktiv,
        fuehrungskraft_user_id=daten.fuehrungskraft_user_id,
        fuehrungskraft_setzen="fuehrungskraft_user_id" in gesetzt,
    )


@router.get("/rollen", response_model=list[RolleAus])
def rollen(principal: AktuellerNutzer) -> list[RolleAus]:
    """Die acht Rollen mit ihrer Erklaerung aus A.15."""
    del principal
    return [RolleAus(**r) for r in verwaltung_service.alle_rollen()]


@router.get("/rollenzuweisungen/wirkung", response_model=WirkungAus)
def wirkung(
    user_id: uuid.UUID,
    rolle: Rolle,
    scope_typ: ScopeTyp,
    principal: AktuellerNutzer,
    db: DbSession,
    scope_id: uuid.UUID | None = None,
) -> WirkungAus:
    """„Diese Zuweisung gibt Zugriff auf N Prozessobjekte."

    Vor der Entscheidung, nicht danach: „Prozess-Owner auf FIN-INT" sagt
    niemandem, wie viel Zugriff das ist.
    """
    return WirkungAus(
        **vars(
            verwaltung_service.wirkung(
                db,
                principal,
                user_id=user_id,
                rolle=rolle,
                scope_typ=scope_typ,
                scope_id=scope_id,
            )
        )
    )
