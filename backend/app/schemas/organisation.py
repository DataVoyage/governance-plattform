"""Vertraege fuer Organisationsmodell, Nutzer und Rollen."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.enums import Ebene, Rolle, ScopeTyp


class FachbereichAnlegen(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=32)


class FachbereichAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    quelle: str | None = None


class OrganisationseinheitAnlegen(BaseModel):
    fachbereich_id: uuid.UUID
    ebene: Ebene
    land_code: str | None = Field(default=None, min_length=2, max_length=2)

    @model_validator(mode="after")
    def land_code_passt_zur_ebene(self) -> OrganisationseinheitAnlegen:
        if self.ebene == Ebene.LAND and not self.land_code:
            raise ValueError("Eine Organisationseinheit auf Ebene LAND braucht einen land_code")
        if self.ebene == Ebene.INT and self.land_code:
            raise ValueError("Eine Organisationseinheit auf Ebene INT hat keinen land_code")
        return self


class OrganisationseinheitAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fachbereich_id: uuid.UUID
    ebene: Ebene
    land_code: str | None = None


class UserAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str
    ist_aktiv: bool
    fuehrungskraft_user_id: uuid.UUID | None = None


class PersonAus(BaseModel):
    """Wer eine Rolle in einem Bereich traegt — fuer Auswahllisten.

    Bewusst schmaler als ``UserAus``: ein Formular braucht Kennung und Name,
    nicht E-Mail, Status und Fuehrungskraft (docs/rollen-und-scopes.md, 6).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class UserAnlegen(BaseModel):
    """Vorabanlage eines Nutzers, etwa um ihm vor der ersten Anmeldung
    eine Rolle oder eine Fuehrungskraft zuzuordnen."""

    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    subject: str | None = None
    fuehrungskraft_user_id: uuid.UUID | None = None


class RollenzuweisungAnlegen(BaseModel):
    user_id: uuid.UUID
    rolle: Rolle
    scope_typ: ScopeTyp
    scope_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def scope_id_passt_zum_typ(self) -> RollenzuweisungAnlegen:
        if self.scope_typ == ScopeTyp.GLOBAL and self.scope_id is not None:
            raise ValueError("Ein globaler Scope hat keine scope_id")
        if self.scope_typ != ScopeTyp.GLOBAL and self.scope_id is None:
            raise ValueError(f"Scope-Typ {self.scope_typ} verlangt eine scope_id")
        return self


class RollenzuweisungAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    rolle: Rolle
    scope_typ: ScopeTyp
    scope_id: uuid.UUID | None = None


class ProfilAus(BaseModel):
    """Sicht des angemeldeten Nutzers auf sich selbst."""

    id: uuid.UUID
    email: str
    name: str
    rollen: list[RollenzuweisungAus]
