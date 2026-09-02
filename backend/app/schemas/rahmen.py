"""Vertraege des Erlaubnisrahmens (Leitdokument A.13.2).

Anders als der Vertrag der Query-API richtet sich dieser an die Oberflaeche und
enthaelt deshalb beide Seiten: was erlaubt ist **und** was gemessen wurde. Wer
eine Abweichung abstellen soll, braucht beides nebeneinander.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.models.enums import Schicht2Verbot


class RahmenElementAus(BaseModel):
    """Eines der sieben Elemente aus Schicht 1."""

    schluessel: str = Field(description="Fachlicher Schluessel, etwa 'datenkategorie'.")
    erlaubt: list[str] = Field(default_factory=list)
    gemessen: list[str] = Field(default_factory=list)
    abweichung: list[str] = Field(
        default_factory=list, description="Gemessene Werte, die der Rahmen nicht deckt."
    )
    messbar: bool = Field(
        default=True,
        description="Falsch, wo es zu diesem Element keine Messung gibt. Betrifft die "
        "Reichweite: sie ist nach A.4.4 geerbt und wird nirgends beobachtet.",
    )
    eingehalten: bool = True


class RahmenAus(BaseModel):
    elemente: list[RahmenElementAus] = Field(default_factory=list)
    tier: int | None = None
    quelle_prozess_ids: list[uuid.UUID] = Field(default_factory=list)
    eingehalten: bool = True
    #: Verbote aus Schicht 2, die die erfassten Daten selbst belegen. Nicht die
    #: ganze Wahrheit ueber das Tool — nur das, was ohne Meldung erkennbar ist.
    schicht2_befunde: list[Schicht2Verbot] = Field(default_factory=list)


class Schicht2VerbotAus(BaseModel):
    """Ein Eintrag der abschliessenden Verbotsliste, fuer die Meldeauswahl."""

    schluessel: Schicht2Verbot
    #: Erkennt die Anwendung dieses Verbot aus vorhandenen Daten selbst?
    automatisch_erkennbar: bool = False
