"""Governance-Query-API, HTTP-Schicht (Architektur 7.3).

Der Anschlusspunkt fuer die spaetere Infrastruktur-Provisionierung: REST, JSON,
OpenAPI-dokumentiert — bewusst kein GraphQL und kein gRPC, damit ein
andockendes Team ohne zusaetzliches Tooling dagegen entwickeln kann.

Diese Routen authentifizieren sich **nicht** ueber die zentrale
Unternehmensidentitaet, sondern ueber ein Service-Token: eine andockende
Anwendung ist keine Person (Architektur 10.3).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import DbSession, ServiceClient
from app.schemas.query import (
    AenderungenAus,
    ErlaubnisrahmenAus,
    KKlassenAus,
    TierAus,
)
from app.services import query as query_service

router = APIRouter(prefix="/query", tags=["Governance-Query-API"])


@router.get(
    "/prozess/{prozess_id}/tier",
    response_model=TierAus,
    summary="Tier und Risikoprofil eines Prozessobjekts",
)
def tier(prozess_id: uuid.UUID, db: DbSession, client: ServiceClient) -> TierAus:
    """Liefert Tier und das Sechser-Profil der neuesten Bewertung.

    Dieselbe Fachlogik wie im Bewertungs-Wizard — es gibt keine zweite
    Implementierung.
    """
    del client
    return TierAus(**query_service.tier_und_profil(db, prozess_id))


@router.get(
    "/prozess/{prozess_id}/k-klassen",
    response_model=KKlassenAus,
    summary="Ausgeloeste Massnahmenklassen eines Prozessobjekts",
)
def k_klassen(prozess_id: uuid.UUID, db: DbSession, client: ServiceClient) -> KKlassenAus:
    """Liefert die aus dem Profil abgeleiteten K-Klassen."""
    del client
    return KKlassenAus(**query_service.k_klassen(db, prozess_id))


@router.get(
    "/tool/{tool_id}/erlaubnisrahmen",
    response_model=ErlaubnisrahmenAus,
    summary="Erlaubnisrahmen eines Tool-Objekts",
)
def erlaubnisrahmen(tool_id: uuid.UUID, db: DbSession, client: ServiceClient) -> ErlaubnisrahmenAus:
    """Sagt, was der Rahmen erlaubt — nicht, was zu tun ist.

    Die Antwort provisioniert nichts; die Entscheidung bleibt bei der
    andockenden Anwendung.
    """
    del client
    return ErlaubnisrahmenAus(**query_service.erlaubnisrahmen(db, tool_id))


@router.get(
    "/changes",
    response_model=AenderungenAus,
    summary="Delta-Abfrage seit einem Cursor",
)
def changes(
    db: DbSession,
    client: ServiceClient,
    since: int = 0,
    entity_type: Annotated[list[str] | None, Query()] = None,
    limit: int = 500,
) -> AenderungenAus:
    """Alles, was seit ``since`` passiert ist — in Reihenfolge, ohne Luecken.

    Der Cursor ist eine Sequenznummer, keine Zeitangabe. Eine andockende
    Anwendung speichert den zuletzt verarbeiteten Cursor und fragt beim
    naechsten Lauf nur an, was seither geschehen ist. Fuer den Erstabgleich
    bleiben die drei Vollabfragen der richtige Weg.
    """
    del client
    return AenderungenAus(
        **query_service.aenderungen(db, since=since, entity_types=entity_type, limit=limit)
    )
