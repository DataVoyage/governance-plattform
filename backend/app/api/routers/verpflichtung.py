"""Selbstverpflichtung und Gates, HTTP-Schicht (Architektur 8.4, 8.5)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.api.deps import AktuellerNutzer, DbSession
from app.models.enums import GateTyp, SelbstverpflichtungTyp
from app.schemas.verpflichtung import (
    AussageAus,
    BenachrichtigungAus,
    DeckungAus,
    GateAus,
    GateEinreichen,
    GateEntscheiden,
    KatalogAus,
    SelbstverpflichtungAbgeben,
    SelbstverpflichtungAus,
)
from app.services import asset as asset_service
from app.services import erinnerung as erinnerung_service
from app.services import gate as gate_service
from app.services import prozess as prozess_service
from app.services import selbstverpflichtung as sv_service

router = APIRouter(tags=["Selbstverpflichtung und Gates"])


# --- Selbstverpflichtung --------------------------------------------------


@router.get("/selbstverpflichtungen/katalog", response_model=list[KatalogAus])
def katalog(principal: AktuellerNutzer) -> list[KatalogAus]:
    """Die nummerierten Aussagen aus A.10.2 und A.10.3.

    Die Oberflaeche baut ihre Checkliste aus diesem Katalog, damit Aussagen und
    Reihenfolge an genau einer Stelle stehen.
    """
    del principal
    return [
        KatalogAus(
            typ=typ,
            aussagen=[AussageAus(id=a.id, text=a.text, ab_tier=a.ab_tier) for a in aussagen],
            version=sv_service.KATALOG_VERSION,
        )
        for typ, aussagen in sv_service.KATALOG.items()
    ]


def _deckung_aus(db, eintrag, *, typ, prozess=None, tool=None, tier: int | None) -> DeckungAus:
    stand = sv_service.deckung(db, eintrag, prozess=prozess, tool=tool)
    return DeckungAus(
        gedeckt=stand.gedeckt,
        grund=stand.grund,
        grundtext=stand.grundtext,
        verlangte_aussagen=[a.id for a in sv_service.verlangte_aussagen(typ, tier)],
        tier=tier,
        aktuelle=SelbstverpflichtungAus.model_validate(eintrag) if eintrag else None,
    )


@router.get("/prozesse/{prozess_id}/selbstverpflichtung", response_model=DeckungAus)
def deckung_prozess(prozess_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> DeckungAus:
    """Der Stand der Erklaerung samt Grund, falls sie nicht traegt.

    Die Oberflaeche fragt genau diesen Endpunkt und muss die Regeln aus A.10.4
    und A.10.5 nicht nachbauen — sie zeigt an, was der Server entschieden hat.
    """
    prozess = prozess_service.hole_sichtbar(db, principal, prozess_id)
    bewertung = prozess_service.neueste_bewertung(prozess)
    return _deckung_aus(
        db,
        sv_service.aktuelle_fuer_prozess(db, prozess_id),
        typ=SelbstverpflichtungTyp.PROZESSEIGNER,
        prozess=prozess,
        tier=bewertung.tier if bewertung is not None else None,
    )


@router.get("/tools/{tool_id}/selbstverpflichtung/deckung", response_model=DeckungAus)
def deckung_tool(tool_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> DeckungAus:
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    return _deckung_aus(
        db,
        sv_service.aktuelle_fuer_tool(db, tool_id),
        typ=SelbstverpflichtungTyp.TECHNISCHER_OWNER,
        tool=tool,
        tier=asset_service.erbe_klassifikation(tool).tier,
    )


@router.post(
    "/selbstverpflichtungen/{eintrag_id}/bestaetigung",
    response_model=SelbstverpflichtungAus,
)
def bestaetigen(
    eintrag_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession
) -> SelbstverpflichtungAus:
    """Die Jahresbestaetigung ab Tier 3 — ein Klick statt eines Durchgangs."""
    eintrag = sv_service.hole(db, eintrag_id)
    if eintrag.prozessobjekt_id is not None:
        prozess_service.hole_sichtbar(db, principal, eintrag.prozessobjekt_id)
    elif eintrag.tool_objekt_id is not None:
        asset_service.hole_tool_sichtbar(db, principal, eintrag.tool_objekt_id)
    return SelbstverpflichtungAus.model_validate(sv_service.bestaetige(db, principal, eintrag))


@router.post(
    "/selbstverpflichtungen",
    response_model=SelbstverpflichtungAus,
    status_code=status.HTTP_201_CREATED,
)
def abgeben(
    daten: SelbstverpflichtungAbgeben, principal: AktuellerNutzer, db: DbSession
) -> SelbstverpflichtungAus:
    prozess = None
    tool = None
    if daten.typ == SelbstverpflichtungTyp.PROZESSEIGNER:
        if daten.prozessobjekt_id is None:
            raise prozess_service.Ungueltig(
                "Eine Prozesseigner-Selbstverpflichtung braucht ein Prozessobjekt"
            )
        prozess = prozess_service.hole_sichtbar(db, principal, daten.prozessobjekt_id)
    else:
        if daten.tool_objekt_id is None:
            raise prozess_service.Ungueltig(
                "Eine Owner-Selbstverpflichtung braucht ein Tool-Objekt"
            )
        tool = asset_service.hole_tool_sichtbar(db, principal, daten.tool_objekt_id)

    eintrag = sv_service.abgeben(
        db,
        principal,
        typ=daten.typ,
        prozess=prozess,
        tool=tool,
        aussagen={k: v.model_dump() for k, v in daten.aussagen.items()},
    )
    return SelbstverpflichtungAus.model_validate(eintrag)


@router.get(
    "/prozesse/{prozess_id}/selbstverpflichtungen", response_model=list[SelbstverpflichtungAus]
)
def historie_prozess(prozess_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> list:
    prozess_service.hole_sichtbar(db, principal, prozess_id)
    return sv_service.historie_fuer_prozess(db, prozess_id)


@router.get("/tools/{tool_id}/selbstverpflichtung", response_model=SelbstverpflichtungAus | None)
def aktuelle_tool(tool_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession):
    asset_service.hole_tool_sichtbar(db, principal, tool_id)
    return sv_service.aktuelle_fuer_tool(db, tool_id)


# --- Gates ----------------------------------------------------------------


@router.post(
    "/prozesse/{prozess_id}/gates", response_model=GateAus, status_code=status.HTTP_201_CREATED
)
def einreichen(
    prozess_id: uuid.UUID,
    daten: GateEinreichen,
    principal: AktuellerNutzer,
    db: DbSession,
) -> GateAus:
    prozess = prozess_service.hole_sichtbar(db, principal, prozess_id)
    vorgang = gate_service.einreichen(
        db,
        principal,
        prozess,
        gate_typ=daten.gate_typ,
        ausloeser=daten.ausloeser.value if daten.ausloeser is not None else None,
        begruendung=daten.begruendung,
    )
    return GateAus.model_validate(vorgang)


@router.get("/prozesse/{prozess_id}/gates", response_model=list[GateAus])
def historie_gates(prozess_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> list:
    prozess_service.hole_sichtbar(db, principal, prozess_id)
    return gate_service.historie(db, prozess_id)


@router.get("/gates", response_model=list[GateAus])
def offene_gates(principal: AktuellerNutzer, db: DbSession) -> list:
    return gate_service.offene_vorgaenge(db, principal)


@router.post("/gates/{gate_id}/entscheidung", response_model=GateAus)
def entscheiden(
    gate_id: uuid.UUID, daten: GateEntscheiden, principal: AktuellerNutzer, db: DbSession
) -> GateAus:
    vorgang = gate_service.hole(db, gate_id)
    prozess_service.hole_sichtbar(db, principal, vorgang.prozessobjekt_id)
    return GateAus.model_validate(
        gate_service.entscheiden(
            db, principal, vorgang, status=daten.status, kommentar=daten.kommentar
        )
    )


@router.get("/gates/ausloeser", response_model=list[str])
def gate2_ausloeser(principal: AktuellerNutzer) -> list[str]:
    """Die fuenf zulaessigen Ausloeser — die Liste in A.11 ist abschliessend."""
    del principal
    from app.models.enums import Gate2Ausloeser

    return [a.value for a in Gate2Ausloeser]


# --- Benachrichtigungen ---------------------------------------------------


@router.get("/benachrichtigungen", response_model=list[BenachrichtigungAus])
def eigene_benachrichtigungen(principal: AktuellerNutzer, db: DbSession) -> list:
    return erinnerung_service.benachrichtigungen(db, principal.user_id)


@router.get("/selbstverpflichtungen/ueberfaellig", response_model=list[SelbstverpflichtungAus])
def ueberfaellige(principal: AktuellerNutzer, db: DbSession) -> list:
    """Vorgriff auf die Cockpit-Zeile aus Phase 6, hier als Datenzustand."""
    del principal
    return erinnerung_service.ueberfaellige(db)


# Gate 1 ist die Tier-3-Erstfreigabe; der Typ steht hier nur der Lesbarkeit
# halber im Modul, damit die Bedeutung nicht in der Oberflaeche verloren geht.
GATE_ERSTFREIGABE = GateTyp.GATE_1
