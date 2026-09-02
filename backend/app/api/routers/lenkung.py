"""Compliance und Lenkung, HTTP-Schicht (Architektur 8.6)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.api.deps import AktuellerNutzer, DbSession
from app.models.enums import Schicht2Verbot
from app.schemas.lenkung import (
    Abbrechen,
    Aufloesen,
    LenkungAus,
    MeldungAus,
    ZustandAus,
    ZustandMelden,
)
from app.schemas.rahmen import Schicht2VerbotAus
from app.services import asset as asset_service
from app.services import lenkung as lenkung_service
from app.services import rahmen as rahmen_service

router = APIRouter(tags=["Compliance und Lenkung"])


@router.get("/tools/{tool_id}/compliance", response_model=list[ZustandAus])
def verlauf(tool_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> list:
    """Die Zeitreihe; der aktuelle Zustand ist der erste Eintrag."""
    asset_service.hole_tool_sichtbar(db, principal, tool_id)
    return lenkung_service.verlauf(db, tool_id)


@router.post(
    "/tools/{tool_id}/compliance", response_model=MeldungAus, status_code=status.HTTP_201_CREATED
)
def melden(
    tool_id: uuid.UUID, daten: ZustandMelden, principal: AktuellerNutzer, db: DbSession
) -> MeldungAus:
    """Manuelle Meldung eines Zustands.

    Bei ``rot`` entsteht automatisch ein Lenkungsvorgang in Stufe 1 mit der
    tier-abhaengigen Frist (Leitdokument A.13.5) — bei einem Verstoss gegen
    Schicht 2 unmittelbar in Stufe 2, weil dort nichts zu klaeren ist.
    """
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    zustand, vorgang = lenkung_service.melde_zustand(
        db,
        principal,
        tool,
        farbe=daten.farbe,
        begruendung=daten.begruendung,
        abweichung_art=daten.abweichung_art,
        schicht2_verbot=daten.schicht2_verbot,
    )
    return MeldungAus(
        zustand=ZustandAus.model_validate(zustand),
        lenkungsvorgang=LenkungAus.model_validate(vorgang) if vorgang is not None else None,
    )


@router.get("/schicht2-verbote", response_model=list[Schicht2VerbotAus])
def schicht2_verbote() -> list[Schicht2VerbotAus]:
    """Die sechs organisationsweiten Verbote aus A.13.2 Schicht 2.

    Abschliessend wie die Gate-2-Ausloeser: die Oberflaeche laesst genau diese
    sechs melden und keinen freien siebten Grund. Zu jedem steht dabei, ob die
    Anwendung ihn selbst erkennt — vier tut sie, zwei betreffen Vorgaenge in der
    Zielplattform, von denen sie nichts sieht.
    """
    return [
        Schicht2VerbotAus(
            schluessel=verbot,
            automatisch_erkennbar=verbot in rahmen_service.AUTOMATISCH_ERKENNBAR,
        )
        for verbot in Schicht2Verbot
    ]


@router.get("/lenkungsvorgaenge", response_model=list[LenkungAus])
def liste(
    principal: AktuellerNutzer,
    db: DbSession,
    nur_offen: bool = True,
    eskalationsstufe: int | None = None,
) -> list:
    return lenkung_service.liste(
        db, principal, nur_offen=nur_offen, eskalationsstufe=eskalationsstufe
    )


@router.get("/lenkungsvorgaenge/{vorgang_id}", response_model=LenkungAus)
def detail(vorgang_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> LenkungAus:
    vorgang = lenkung_service.hole(db, vorgang_id)
    asset_service.hole_tool_sichtbar(db, principal, vorgang.tool_objekt_id)
    return LenkungAus.model_validate(vorgang)


@router.post("/lenkungsvorgaenge/{vorgang_id}/aufloesung", response_model=LenkungAus)
def aufloesen(
    vorgang_id: uuid.UUID, daten: Aufloesen, principal: AktuellerNutzer, db: DbSession
) -> LenkungAus:
    vorgang = lenkung_service.hole(db, vorgang_id)
    return LenkungAus.model_validate(
        lenkung_service.loese_auf(
            db,
            principal,
            vorgang,
            art=daten.art,
            bewertung_id=daten.bewertung_id,
            kommentar=daten.kommentar,
        )
    )


@router.post("/lenkungsvorgaenge/{vorgang_id}/abbruch", response_model=LenkungAus)
def abbrechen(
    vorgang_id: uuid.UUID, daten: Abbrechen, principal: AktuellerNutzer, db: DbSession
) -> LenkungAus:
    vorgang = lenkung_service.hole(db, vorgang_id)
    return LenkungAus.model_validate(
        lenkung_service.brich_ab(db, principal, vorgang, daten.kommentar)
    )
