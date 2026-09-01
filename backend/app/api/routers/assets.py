"""Asset-Management-Modul, HTTP-Schicht (Architektur 8.3).

Zwei Ansichten auf dieselben Daten: aus Prozesssicht (welche Tools haengen an
diesem Prozess) und aus Asset-Sicht (an welchen Prozessen haengt dieses Tool,
mit der jeweils hoechsten geerbten Klassifikation).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.api.deps import AktuellerNutzer, DbSession
from app.models.enums import AssetStatus, Herkunft
from app.models.governance import Datenobjekt, ToolObjekt
from app.schemas.asset import (
    DatenobjektAendern,
    DatenobjektAnlegen,
    DatenobjektAus,
    DatenobjektVerknuepfung,
    GeerbtAus,
    ProzessVerknuepfung,
    ToolAendern,
    ToolAnlegen,
    ToolAus,
    ToolDatenobjektAus,
)
from app.services import asset as asset_service
from app.services import prozess as prozess_service

router = APIRouter(tags=["Assets"])


def _tool_aus(tool: ToolObjekt) -> ToolAus:
    geerbt = asset_service.erbe_klassifikation(tool)
    return ToolAus(
        id=tool.id,
        name=tool.name,
        beschreibung=tool.beschreibung,
        technologie=tool.technologie,
        kategorie=tool.kategorie,
        technischer_owner_user_id=tool.technischer_owner_user_id,
        organisationseinheit_id=tool.organisationseinheit_id,
        herkunft=tool.herkunft,
        quelle=tool.quelle,
        externe_id=tool.externe_id,
        status=tool.status,
        metadaten=tool.metadaten,
        letzte_aktivitaet_am=tool.letzte_aktivitaet_am,
        prozessobjekt_ids=[p.id for p in tool.prozessobjekte],
        geerbt=GeerbtAus(**vars(geerbt)),
        schreibgeschuetzte_felder=_gesperrt(tool),
    )


def _gesperrt(objekt) -> list[str]:
    if objekt.herkunft != Herkunft.IMPORTIERT:
        return []
    return sorted(f for f in asset_service.STAMMDATENFELDER if hasattr(objekt, f))


def _datenobjekt_aus(datenobjekt: Datenobjekt) -> DatenobjektAus:
    ausgabe = DatenobjektAus.model_validate(datenobjekt)
    ausgabe.schreibgeschuetzte_felder = _gesperrt(datenobjekt)
    return ausgabe


# --- Tool-Objekte ---------------------------------------------------------


@router.get("/tools", response_model=list[ToolAus])
def liste_tools(
    principal: AktuellerNutzer,
    db: DbSession,
    status_filter: AssetStatus | None = None,
    ohne_prozess: bool = False,
) -> list[ToolAus]:
    treffer = asset_service.liste_tools(
        db, principal, status=status_filter, ohne_prozess=ohne_prozess
    )
    return [_tool_aus(t) for t in treffer]


@router.post("/tools", response_model=ToolAus, status_code=status.HTTP_201_CREATED)
def lege_tool_an(daten: ToolAnlegen, principal: AktuellerNutzer, db: DbSession) -> ToolAus:
    return _tool_aus(asset_service.lege_tool_an(db, principal, daten.model_dump()))


@router.get("/tools/{tool_id}", response_model=ToolAus)
def tool_detail(tool_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> ToolAus:
    return _tool_aus(asset_service.hole_tool_sichtbar(db, principal, tool_id))


@router.patch("/tools/{tool_id}", response_model=ToolAus)
def aendere_tool(
    tool_id: uuid.UUID, daten: ToolAendern, principal: AktuellerNutzer, db: DbSession
) -> ToolAus:
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    return _tool_aus(
        asset_service.aendere_tool(db, principal, tool, daten.model_dump(exclude_unset=True))
    )


@router.post("/tools/{tool_id}/bestaetigung", response_model=ToolAus)
def bestaetige_tool(tool_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> ToolAus:
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    return _tool_aus(asset_service.bestaetige_tool(db, principal, tool))


@router.delete("/tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
def entferne_tool(tool_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> None:
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    asset_service.entferne_tool(db, principal, tool)


@router.post(
    "/tools/{tool_id}/prozesse", response_model=ToolAus, status_code=status.HTTP_201_CREATED
)
def verknuepfe_prozess(
    tool_id: uuid.UUID,
    daten: ProzessVerknuepfung,
    principal: AktuellerNutzer,
    db: DbSession,
) -> ToolAus:
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    prozess = prozess_service.hole_sichtbar(db, principal, daten.prozessobjekt_id)
    return _tool_aus(asset_service.verknuepfe_tool_mit_prozess(db, principal, tool, prozess))


@router.delete("/tools/{tool_id}/prozesse/{prozess_id}", response_model=ToolAus)
def loese_prozess(
    tool_id: uuid.UUID, prozess_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession
) -> ToolAus:
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    prozess = prozess_service.hole_sichtbar(db, principal, prozess_id)
    return _tool_aus(asset_service.loese_tool_von_prozess(db, principal, tool, prozess))


@router.get("/tools/{tool_id}/datenobjekte", response_model=list[ToolDatenobjektAus])
def datenobjekte_eines_tools(tool_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> list:
    asset_service.hole_tool_sichtbar(db, principal, tool_id)
    return asset_service.datenobjekte_eines_tools(db, tool_id)


@router.post(
    "/tools/{tool_id}/datenobjekte",
    response_model=ToolDatenobjektAus,
    status_code=status.HTTP_201_CREATED,
)
def verknuepfe_datenobjekt(
    tool_id: uuid.UUID,
    daten: DatenobjektVerknuepfung,
    principal: AktuellerNutzer,
    db: DbSession,
):
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    datenobjekt = asset_service.hole_datenobjekt(db, daten.datenobjekt_id)
    return asset_service.verknuepfe_tool_mit_datenobjekt(
        db, principal, tool, datenobjekt, daten.zugriffsart
    )


# --- Datenobjekte ---------------------------------------------------------


@router.get("/datenobjekte", response_model=list[DatenobjektAus])
def liste_datenobjekte(
    principal: AktuellerNutzer,
    db: DbSession,
    ohne_kategorie: bool = False,
    status_filter: AssetStatus | None = None,
) -> list[DatenobjektAus]:
    treffer = asset_service.liste_datenobjekte(
        db, principal, ohne_kategorie=ohne_kategorie, status=status_filter
    )
    return [_datenobjekt_aus(d) for d in treffer]


@router.post("/datenobjekte", response_model=DatenobjektAus, status_code=status.HTTP_201_CREATED)
def lege_datenobjekt_an(
    daten: DatenobjektAnlegen, principal: AktuellerNutzer, db: DbSession
) -> DatenobjektAus:
    return _datenobjekt_aus(asset_service.lege_datenobjekt_an(db, principal, daten.model_dump()))


@router.get("/datenobjekte/{datenobjekt_id}", response_model=DatenobjektAus)
def datenobjekt_detail(
    datenobjekt_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession
) -> DatenobjektAus:
    del principal
    return _datenobjekt_aus(asset_service.hole_datenobjekt(db, datenobjekt_id))


@router.patch("/datenobjekte/{datenobjekt_id}", response_model=DatenobjektAus)
def aendere_datenobjekt(
    datenobjekt_id: uuid.UUID,
    daten: DatenobjektAendern,
    principal: AktuellerNutzer,
    db: DbSession,
) -> DatenobjektAus:
    datenobjekt = asset_service.hole_datenobjekt(db, datenobjekt_id)
    return _datenobjekt_aus(
        asset_service.aendere_datenobjekt(
            db, principal, datenobjekt, daten.model_dump(exclude_unset=True)
        )
    )


@router.post("/datenobjekte/{datenobjekt_id}/bestaetigung", response_model=DatenobjektAus)
def bestaetige_datenobjekt(
    datenobjekt_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession
) -> DatenobjektAus:
    datenobjekt = asset_service.hole_datenobjekt(db, datenobjekt_id)
    return _datenobjekt_aus(asset_service.bestaetige_datenobjekt(db, principal, datenobjekt))
