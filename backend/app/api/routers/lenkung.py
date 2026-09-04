"""Compliance und Lenkung, HTTP-Schicht (Architektur 8.6)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import AktuellerNutzer, DbSession
from app.models.enums import Schicht2Verbot
from app.models.governance import ToolObjekt
from app.schemas.lenkung import (
    Abbrechen,
    AbweichungMelden,
    Aufloesen,
    ComplianceAus,
    LenkungAus,
    LenkungsrechteAus,
    MeldungAus,
    ZustandAus,
)
from app.schemas.rahmen import Schicht2VerbotAus
from app.services import asset as asset_service
from app.services import lenkung as lenkung_service
from app.services import rahmen as rahmen_service
from app.services import rechte as rechte_service

router = APIRouter(tags=["Compliance und Lenkung"])


def _vorgang_aus(db, principal, vorgang) -> LenkungAus:
    """Ein Lenkungsvorgang samt dem, was der Anfragende damit tun darf."""
    ausgabe = LenkungAus.model_validate(vorgang)
    ausgabe.rechte = LenkungsrechteAus(
        **vars(rechte_service.fuer_lenkungsvorgang(db, principal, vorgang))
    )
    tool = db.get(ToolObjekt, vorgang.tool_objekt_id)
    if tool is not None:
        ausgabe.offene_abweichungen = lenkung_service.offene_abweichungen(db, tool)
    return ausgabe


@router.get("/tools/{tool_id}/compliance", response_model=ComplianceAus)
def compliance(tool_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> ComplianceAus:
    """Der gerechnete Zustand und die Zeitreihe dahinter.

    Die Farbe wird nicht gelesen, sondern gemessen (E-64). Ein Werkzeug, zu dem
    noch nie etwas gemeldet wurde, hat deshalb trotzdem einen Zustand — vorher
    stand dort nichts, obwohl die Anwendung es laengst beurteilen konnte.
    """
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    return ComplianceAus(
        farbe=lenkung_service.gemessene_farbe(db, tool),
        offene_abweichungen=lenkung_service.offene_abweichungen(db, tool),
        verlauf=[ZustandAus.model_validate(z) for z in lenkung_service.verlauf(db, tool.id)],
    )


@router.post(
    "/tools/{tool_id}/compliance", response_model=MeldungAus, status_code=status.HTTP_201_CREATED
)
def melden(
    tool_id: uuid.UUID,
    daten: AbweichungMelden,
    antwort: Response,
    principal: AktuellerNutzer,
    db: DbSession,
) -> MeldungAus:
    """Eine Compliance-Abweichung melden — die einzige Meldung, die es gibt.

    Es entsteht ein Lenkungsvorgang in Stufe 1 mit der tier-abhaengigen Frist
    (A.13.5), oder unmittelbar in Stufe 2, wenn die Daten ein Verbot aus
    Schicht 2 belegen: dort ist nichts zu klaeren.

    Laeuft fuer dieses Werkzeug schon ein ungeklaerter Vorgang, passiert
    nichts. Die Antwort ist dann **200** statt 201 und traegt den laufenden
    Vorgang ohne neuen Zustand — dieselbe Abweichung zweimal zu melden ist
    dieselbe Abweichung.
    """
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    zustand, vorgang = lenkung_service.melde_abweichung(
        db, principal, tool, begruendung=daten.begruendung
    )
    if zustand is None:
        antwort.status_code = status.HTTP_200_OK
    return MeldungAus(
        zustand=None if zustand is None else ZustandAus.model_validate(zustand),
        lenkungsvorgang=_vorgang_aus(db, principal, vorgang) if vorgang is not None else None,
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
    return [
        _vorgang_aus(db, principal, v)
        for v in lenkung_service.liste(
            db, principal, nur_offen=nur_offen, eskalationsstufe=eskalationsstufe
        )
    ]


@router.get("/lenkungsvorgaenge/{vorgang_id}", response_model=LenkungAus)
def detail(vorgang_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> LenkungAus:
    vorgang = lenkung_service.hole(db, vorgang_id)
    asset_service.hole_tool_sichtbar(db, principal, vorgang.tool_objekt_id)
    return _vorgang_aus(db, principal, vorgang)


@router.post("/lenkungsvorgaenge/{vorgang_id}/aufloesung", response_model=LenkungAus)
def aufloesen(
    vorgang_id: uuid.UUID, daten: Aufloesen, principal: AktuellerNutzer, db: DbSession
) -> LenkungAus:
    vorgang = lenkung_service.hole(db, vorgang_id)
    return _vorgang_aus(
        db,
        principal,
        lenkung_service.loese_auf(
            db,
            principal,
            vorgang,
            art=daten.art,
            bewertung_id=daten.bewertung_id,
            kommentar=daten.kommentar,
        ),
    )


@router.post("/lenkungsvorgaenge/{vorgang_id}/abbruch", response_model=LenkungAus)
def abbrechen(
    vorgang_id: uuid.UUID, daten: Abbrechen, principal: AktuellerNutzer, db: DbSession
) -> LenkungAus:
    vorgang = lenkung_service.hole(db, vorgang_id)
    return _vorgang_aus(
        db, principal, lenkung_service.brich_ab(db, principal, vorgang, daten.kommentar)
    )
