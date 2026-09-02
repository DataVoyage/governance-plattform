"""Nachweis, HTTP-Schicht (Leitdokument A.13.7, Architektur 10.4).

Das Aenderungsprotokoll war nur ueber die Datenbank oder die Delta-Abfrage der
Query-API zu lesen — die erste ist niemandem zumutbar, die zweite ist fuer
andockende Anwendungen gedacht und liefert bewusst keine Inhalte. Eine Pruefung
braucht beides: die einzelne Handlung und das, was sie geaendert hat.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import AktuellerNutzer, DbSession
from app.schemas.verwaltung import FeldaenderungAus, NachweiseintragAus
from app.services import verwaltung as verwaltung_service

router = APIRouter(tags=["Nachweis"])


@router.get("/nachweis", response_model=list[NachweiseintragAus])
def nachweis(
    principal: AktuellerNutzer,
    db: DbSession,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[NachweiseintragAus]:
    """Schreibende Aktionen mit Zeitpunkt, Person und Vorher/Nachher.

    Nicht nach Bereichen geschnitten: der Nachweis ist der Ort, an dem eine
    Pruefung eine einzelne Handlung wiederfindet, und ein Ausschnitt wuerde
    genau das verhindern. Deshalb sehen ihn nur die bereichsuebergreifend
    lesenden Rollen und der App-Administrator.
    """
    eintraege = verwaltung_service.nachweis(
        db, principal, entity_type=entity_type, entity_id=entity_id, limit=limit
    )
    return [
        NachweiseintragAus(
            cursor=e.cursor,
            entity_type=e.entity_type,
            entity_id=e.entity_id,
            aktion=e.aktion,
            zeitpunkt=e.zeitpunkt,
            akteur=e.akteur,
            gegenstand=e.gegenstand,
            aenderungen=[FeldaenderungAus(**vars(a)) for a in e.aenderungen],
        )
        for e in eintraege
    ]
