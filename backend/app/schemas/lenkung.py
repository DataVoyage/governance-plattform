"""Vertraege fuer Compliance-Zustand und Lenkung (Architektur 8.6)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Aufloesungsart, ComplianceFarbe, LenkungStatus


class ZustandMelden(BaseModel):
    farbe: ComplianceFarbe
    begruendung: str = ""
    abweichung_art: str | None = Field(default=None, max_length=64)


class ZustandAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tool_objekt_id: uuid.UUID
    farbe: ComplianceFarbe
    begruendung: str
    abweichung_art: str | None = None
    festgestellt_am: datetime
    festgestellt_von: uuid.UUID | None = None


class LenkungAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tool_objekt_id: uuid.UUID
    compliance_zustand_id: uuid.UUID | None = None
    eskalationsstufe: int
    frist: datetime
    zugewiesen_an: uuid.UUID | None = None
    status: LenkungStatus
    aufloesungsart: Aufloesungsart | None = None
    aufloesung_bewertung_id: uuid.UUID | None = None
    aufgeloest_am: datetime | None = None
    beschreibung: str
    erstellt_am: datetime


class MeldungAus(BaseModel):
    """Was eine Meldung ausgeloest hat — Zustand und ggf. der Vorgang dazu."""

    zustand: ZustandAus
    lenkungsvorgang: LenkungAus | None = None


class Aufloesen(BaseModel):
    """Genau eine der drei zulaessigen Aufloesungen aus A.13.6."""

    art: Aufloesungsart
    #: Pflicht bei ``rahmen_erweitern``: die neue, danach entstandene Bewertung.
    bewertung_id: uuid.UUID | None = None
    kommentar: str = ""


class Abbrechen(BaseModel):
    kommentar: str = ""
