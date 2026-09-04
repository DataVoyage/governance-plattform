"""Bewertungs-Modul, HTTP-Schicht (Architektur 8.2)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.api.deps import AktuellerNutzer, DbSession
from app.models.governance import Alarm
from app.schemas.bewertung import (
    AlarmAus,
    BelegAus,
    BewertungAbschluss,
    BewertungAus,
    ErgebnisAus,
    FrageAus,
    KKlasseAus,
    WizardAnfrage,
    WizardSchritt,
)
from app.services import bewertung as bewertung_service
from app.services import prozess as prozess_service
from app.services import vorschlag as vorschlag_service
from app.services.bewertungsbaum import BAUM, BLOCK_JE_FRAGE

router = APIRouter(prefix="/prozesse/{prozess_id}", tags=["Bewertung"])

_BLOCK_TITEL = {b.block: b.titel for b in BAUM}
_BLOCK_NUMMER = {b.block: i + 1 for i, b in enumerate(BAUM)}


def _frage_aus(frage, vorschlaege: dict[str, vorschlag_service.Vorschlag]) -> FrageAus:
    block = BLOCK_JE_FRAGE[frage.id]
    hinweis = vorschlaege.get(frage.id)
    return FrageAus(
        id=frage.id,
        text=frage.text,
        block=block.value,
        block_titel=_BLOCK_TITEL[block],
        nummer=_BLOCK_NUMMER[block],
        anzahl_bloecke=len(BAUM),
        vorschlag=hinweis.wert if hinweis else None,
        belege=[
            BelegAus(text=b.text, quelle=b.quelle) for b in (hinweis.belege if hinweis else ())
        ],
    )


def _ergebnis_aus(stand) -> ErgebnisAus:
    werte = bewertung_service.profil(stand)
    tier_wert = bewertung_service.tier(stand)
    kennungen = bewertung_service.leite_k_klassen_ab(werte)
    return ErgebnisAus(
        tier=tier_wert,
        profil=werte,
        ausgeloeste_k_klassen=kennungen,
        klassen=[
            KKlasseAus(
                kennung=kennung,
                name=bewertung_service.K_KLASSEN_BESCHREIBUNG[kennung],
                erklaerung=bewertung_service.K_KLASSEN_ERKLAERUNG[kennung],
            )
            for kennung in kennungen
        ],
        auflagen=bewertung_service.auflagen(tier_wert),
    )


@router.post("/bewertung/wizard", response_model=WizardSchritt)
def wizard_schritt(
    prozess_id: uuid.UUID,
    anfrage: WizardAnfrage,
    principal: AktuellerNutzer,
    db: DbSession,
) -> WizardSchritt:
    """Liefert die naechste Frage — oder das Ergebnis, wenn der Baum durch ist.

    Der Aufruf ist zustandslos: der Client schickt alle bisherigen Antworten
    mit, der Server bestimmt daraus die naechste Frage. Damit liegt die
    Reihenfolge in der Geschaeftslogik und nicht in der Oberflaeche.

    Die naechste Frage kommt mit dem Vorschlag, den die Datenlage hergibt
    (A.8.4). Geprueft werden dabei auch die bisherigen Antworten: wer vom
    Vorschlag abweicht, ohne das zu begruenden, kommt nicht weiter — der
    Widerspruch faellt dort auf, wo er entsteht, und nicht erst am Ende.
    """
    prozess = prozess_service.hole_sichtbar(db, principal, prozess_id)
    bewertung_service.pruefe_antworten(anfrage.antworten)
    vorschlaege = vorschlag_service.fuer_prozess(prozess)
    bewertung_service.pruefe_begruendungen(vorschlaege, anfrage.antworten, anfrage.begruendungen)
    stand = bewertung_service.durchlaufe(anfrage.antworten)

    vorschau = None
    if stand.abgeschlossen and not stand.verboten:
        vorschau = _ergebnis_aus(stand)
    return WizardSchritt(
        naechste_frage=(
            _frage_aus(stand.naechste_frage, vorschlaege) if stand.naechste_frage else None
        ),
        abgeschlossen=stand.abgeschlossen,
        verboten=stand.verboten,
        vorschau=vorschau,
    )


@router.post("/bewertungen", response_model=BewertungAbschluss, status_code=status.HTTP_201_CREATED)
def abschliessen(
    prozess_id: uuid.UUID,
    anfrage: WizardAnfrage,
    principal: AktuellerNutzer,
    db: DbSession,
) -> BewertungAbschluss:
    prozess = prozess_service.hole_sichtbar(db, principal, prozess_id)
    ergebnis = bewertung_service.speichere(
        db,
        principal,
        prozess,
        anfrage.antworten,
        begruendungen=anfrage.begruendungen,
    )
    if isinstance(ergebnis, Alarm):
        return BewertungAbschluss(alarm=AlarmAus.model_validate(ergebnis))
    return BewertungAbschluss(bewertung=BewertungAus.model_validate(ergebnis))


@router.get("/bewertungen", response_model=list[BewertungAus])
def historie(prozess_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> list:
    prozess_service.hole_sichtbar(db, principal, prozess_id)
    return bewertung_service.historie(db, prozess_id)
