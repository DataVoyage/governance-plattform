"""Vertraege fuer Selbstverpflichtung und Gates (Architektur 8.4, 8.5)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Gate2Ausloeser, GateStatus, GateTyp, SelbstverpflichtungTyp


class AussageAus(BaseModel):
    id: str
    text: str


class KatalogAus(BaseModel):
    """Der Aussagenkatalog eines Typs — die Oberflaeche baut daraus die Liste."""

    typ: SelbstverpflichtungTyp
    aussagen: list[AussageAus]


class AussageEingabe(BaseModel):
    bestaetigt: bool = False
    kommentar: str = ""


class SelbstverpflichtungAbgeben(BaseModel):
    typ: SelbstverpflichtungTyp
    prozessobjekt_id: uuid.UUID | None = None
    tool_objekt_id: uuid.UUID | None = None
    aussagen: dict[str, AussageEingabe] = Field(default_factory=dict)


class SelbstverpflichtungAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    typ: SelbstverpflichtungTyp
    prozessobjekt_id: uuid.UUID | None = None
    tool_objekt_id: uuid.UUID | None = None
    aussagen: dict[str, AussageEingabe]
    vollstaendig: bool
    abgegeben_von: uuid.UUID
    abgegeben_am: datetime
    gueltig_bis: datetime | None = None
    erinnerung_gesendet_am: datetime | None = None


class GateEinreichen(BaseModel):
    gate_typ: GateTyp
    #: Bei Gate 2 Pflicht; die Liste aus A.11 ist abschliessend.
    ausloeser: Gate2Ausloeser | None = None
    begruendung: str = ""


class GateEntscheiden(BaseModel):
    status: GateStatus
    kommentar: str = ""


class GateAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prozessobjekt_id: uuid.UUID
    gate_typ: GateTyp
    ausloeser: str | None = None
    begruendung: str
    status: GateStatus
    eingereicht_von: uuid.UUID
    entschieden_von: uuid.UUID | None = None
    entscheidungskommentar: str
    entschieden_am: datetime | None = None
    erstellt_am: datetime


class BenachrichtigungAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    empfaenger_user_id: uuid.UUID
    anlass: str
    betreff: str
    text: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    gelesen: bool
    erstellt_am: datetime
