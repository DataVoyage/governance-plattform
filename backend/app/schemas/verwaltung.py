"""Vertraege der Verwaltung: Rollen, Wirkungsvorschau und Nachweis."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.models.enums import Rolle, ScopeTyp


class RolleAus(BaseModel):
    """Eine Rolle mit dem Satz, was sie darf (Leitdokument A.15)."""

    schluessel: Rolle
    erklaerung: str


class UserAendern(BaseModel):
    ist_aktiv: bool | None = None
    fuehrungskraft_user_id: uuid.UUID | None = None


class WirkungAus(BaseModel):
    rolle: Rolle
    scope_typ: ScopeTyp
    scope_name: str = ""
    prozessobjekte: int = 0
    tool_objekte: int = 0
    beispiele: list[str] = Field(default_factory=list)


class FeldaenderungAus(BaseModel):
    feld: str
    vorher: str
    nachher: str


class NachweiseintragAus(BaseModel):
    cursor: int
    entity_type: str
    entity_id: uuid.UUID
    aktion: str
    zeitpunkt: str
    akteur: str
    gegenstand: str = ""
    aenderungen: list[FeldaenderungAus] = Field(default_factory=list)
