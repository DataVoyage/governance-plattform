"""Import-/Sync-API (Architektur 7.2) und Konfigurationsansicht (6.6)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import AktuellerNutzer, DbSession
from app.core.permissions import verlange
from app.models.audit import Konfiguration
from app.schemas.integration import ImportAnfrage, ImportErgebnis
from app.services import konfiguration as konfig_service
from app.services.changelog import protokolliere_aenderung, snapshot
from app.sync.importer import importiere

router = APIRouter(tags=["Integration"])


@router.post("/import/assets", response_model=ImportErgebnis)
def import_assets(
    anfrage: ImportAnfrage, principal: AktuellerNutzer, db: DbSession
) -> ImportErgebnis:
    """Eingehender Adapter-Aufruf. Nur die Plattform-Rolle betreibt Adapter."""
    verlange(
        principal.ist_plattform or principal.ist_administrator,
        "Adapter betreibt ausschliesslich die Plattform-Rolle",
    )
    return importiere(db, anfrage, akteur_user_id=principal.user_id)


class KonfigurationAus(BaseModel):
    schluessel: str
    wert: str
    beschreibung: str = ""


class KonfigurationSetzen(BaseModel):
    wert: str = Field(min_length=1, max_length=255)


@router.get("/konfiguration", response_model=list[KonfigurationAus])
def liste_konfiguration(principal: AktuellerNutzer, db: DbSession) -> list[KonfigurationAus]:
    del principal
    konfig_service.initialisiere(db)
    return [
        KonfigurationAus(
            schluessel=schluessel,
            wert=konfig_service.lies(db, schluessel),
            beschreibung=beschreibung,
        )
        for schluessel, (_, beschreibung) in konfig_service.STANDARDWERTE.items()
    ]


@router.put("/konfiguration/{schluessel}", response_model=KonfigurationAus)
def setze_konfiguration(
    schluessel: str, daten: KonfigurationSetzen, principal: AktuellerNutzer, db: DbSession
) -> KonfigurationAus:
    """Inhaltliche Einstellungen aendert die Governance-Rolle im Betrieb.

    Die Aenderung laeuft wie jede andere schreibende Aktion ueber den
    ``change_log`` und ist damit selbst nachvollziehbar (Architektur 3.2).
    """
    verlange(principal.ist_governance, "Governance-Einstellungen ändert die Governance-Rolle")
    if schluessel not in konfig_service.STANDARDWERTE:
        raise HTTPException(status_code=404, detail="Unbekannter Konfigurationsschlüssel")
    konfig_service.initialisiere(db)
    bestehend = db.execute(
        select(Konfiguration).where(Konfiguration.schluessel == schluessel)
    ).scalar_one()
    vorher = snapshot(bestehend)
    eintrag = konfig_service.setze(db, schluessel, daten.wert)
    protokolliere_aenderung(db, eintrag, vorher, akteur_user_id=principal.user_id)
    return KonfigurationAus(
        schluessel=eintrag.schluessel, wert=eintrag.wert, beschreibung=eintrag.beschreibung
    )
