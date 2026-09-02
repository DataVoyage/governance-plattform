"""Anforderungsklassen und Technologiematrix, HTTP-Schicht (Leitdokument A.9)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import AktuellerNutzer, DbSession
from app.schemas.klassen import (
    AnforderungsklasseAus,
    BefundAus,
    KompensationAus,
    KompensationSetzen,
    MatrixfeldAus,
    MatrixfeldSetzen,
    TechnologieAus,
    ToolbefundAus,
)
from app.services import asset as asset_service
from app.services import klassen as klassen_service
from app.services import prozess as prozess_service
from app.services.klassen import Toolbefund

router = APIRouter(tags=["Anforderungsklassen"])


def _befund_aus(befund: Toolbefund) -> ToolbefundAus:
    return ToolbefundAus(
        tool_id=befund.tool_id,
        tool_name=befund.tool_name,
        technologie=befund.technologie,
        k_klassen=befund.k_klassen,
        befunde=[
            BefundAus(
                tool_id=e.tool_id,
                tool_name=e.tool_name,
                technologie=e.technologie,
                k_klasse=e.k_klasse,
                art=e.art,
                begruendung=e.begruendung,
                massnahme=e.massnahme,
                offen=e.offen,
            )
            for e in befund.befunde
        ],
        ausschluss=befund.ausschluss,
        offen=befund.offen,
    )


@router.get("/anforderungsklassen", response_model=list[AnforderungsklasseAus])
def anforderungsklassen(principal: AktuellerNutzer) -> list[AnforderungsklasseAus]:
    """K1 bis K10 mit Name, Zweck und Ausloeserbedingung (A.9.2).

    Nachschlagewerk, kein Bestand: die Klassen sind Teil des Leitdokuments und
    aendern sich mit ihm, nicht im Betrieb.
    """
    del principal
    return [AnforderungsklasseAus(**k) for k in klassen_service.alle_klassen()]


@router.get("/technologien", response_model=list[TechnologieAus])
def technologien(principal: AktuellerNutzer) -> list[TechnologieAus]:
    """Die Technologien, die Tool-Auswahl und Matrix gemeinsam benutzen."""
    del principal
    return [
        TechnologieAus(schluessel=schluessel, name=name)
        for schluessel, name in klassen_service.TECHNOLOGIEN.items()
    ]


@router.get("/technologiematrix", response_model=list[MatrixfeldAus])
def technologiematrix(principal: AktuellerNutzer, db: DbSession) -> list:
    """Die vollstaendige Matrix Technologie x Klasse (Teil C.1)."""
    del principal
    return klassen_service.matrix(db)


@router.put(
    "/technologiematrix/{technologie}/{k_klasse}",
    response_model=MatrixfeldAus,
)
def setze_matrixfeld(
    technologie: str,
    k_klasse: str,
    daten: MatrixfeldSetzen,
    principal: AktuellerNutzer,
    db: DbSession,
) -> MatrixfeldAus:
    """Aendert ein Matrixfeld — ausschliesslich die Governance-Rolle.

    Die Aenderung wirkt sofort in allen Befunden: sie werden bei jedem Aufruf
    gerechnet und nicht gespeichert, damit es keinen zweiten, veralteten Stand
    gibt.
    """
    eintrag = klassen_service.setze_feld(
        db,
        principal,
        technologie,
        k_klasse,
        bewertung=daten.bewertung,
        begruendung=daten.begruendung,
    )
    return MatrixfeldAus.model_validate(eintrag)


@router.get("/tools/{tool_id}/klassenbefund", response_model=ToolbefundAus)
def toolbefund(tool_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> ToolbefundAus:
    """Die ausgeloesten Klassen dieses Tools gegen seine Technologie (A.9.3)."""
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    return _befund_aus(klassen_service.pruefe_tool(db, tool))


@router.get("/prozesse/{prozess_id}/klassenbefund", response_model=list[ToolbefundAus])
def prozessbefund(
    prozess_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession
) -> list[ToolbefundAus]:
    """Der Abgleich fuer jedes Tool am Prozessobjekt."""
    prozess = prozess_service.hole_sichtbar(db, principal, prozess_id)
    return [_befund_aus(b) for b in klassen_service.pruefe_prozess(db, prozess)]


@router.put("/tools/{tool_id}/kompensationen/{k_klasse}", response_model=KompensationAus)
def setze_kompensation(
    tool_id: uuid.UUID,
    k_klasse: str,
    daten: KompensationSetzen,
    principal: AktuellerNutzer,
    db: DbSession,
) -> KompensationAus:
    """Haelt die kompensierende Massnahme zu einer Klasse fest (A.9.3)."""
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    return KompensationAus.model_validate(
        klassen_service.setze_kompensation(db, principal, tool, k_klasse, daten.massnahme)
    )
