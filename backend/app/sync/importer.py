"""Import-/Sync-Logik der Adapterschicht (Architektur 7.2).

Zwei Regeln tragen dieses Modul:

* Stammdaten kommen von aussen, Governance-Daten entstehen innen (P-App-4).
  Ein Sync aktualisiert nur importierte Felder und fasst governance-gepflegte
  Felder — Kategorie, Klassifikation, Owner-Zuordnung — nie an.
* Nichts wird automatisch zusammengefuehrt, was nicht ueber
  ``(quelle, externe_id)`` eindeutig identisch ist.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import AssetStatus, ChangeAktion, Ebene, Herkunft, ImportTyp
from app.models.governance import Datenobjekt, ToolObjekt
from app.models.organisation import Fachbereich, Organisationseinheit, Team
from app.schemas.integration import (
    ImportAnfrage,
    ImportDatensatz,
    ImportErgebnis,
    ImportFehler,
    Zusammenfuehrungsvorschlag,
)
from app.services.changelog import protokolliere, protokolliere_aenderung, snapshot

#: Felder, die ein Sync niemals ueberschreibt (Architektur 7.2, Punkt 1).
GESCHUETZTE_FELDER: frozenset[str] = frozenset(
    {"kategorie", "technischer_owner_user_id", "status", "fachbereich_id"}
)


def _normalisiert(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


class ImportKontext:
    """Sammelt Ergebnis und Akteur eines Import-Laufs."""

    def __init__(self, quelle: str, akteur_user_id: uuid.UUID | None = None) -> None:
        self.quelle = quelle
        self.akteur_user_id = akteur_user_id
        self.ergebnis = ImportErgebnis(quelle=quelle)

    def angelegt(self) -> None:
        self.ergebnis.angelegt += 1

    def aktualisiert(self, veraendert: bool) -> None:
        if veraendert:
            self.ergebnis.aktualisiert += 1
        else:
            self.ergebnis.unveraendert += 1

    def fehler(self, externe_id: str, grund: str) -> None:
        self.ergebnis.fehler.append(ImportFehler(externe_id=externe_id, grund=grund))

    def vorschlag(self, vorschlag: Zusammenfuehrungsvorschlag) -> None:
        self.ergebnis.vorschlaege.append(vorschlag)


def _finde_nach_externer_id(db: Session, modell: Any, quelle: str, externe_id: str) -> Any:
    return db.execute(
        select(modell).where(modell.quelle == quelle, modell.externe_id == externe_id)
    ).scalar_one_or_none()


def _finde_namensdublette(db: Session, modell: Any, name: str, quelle: str) -> Any:
    """Sucht einen gleichnamigen Datensatz anderer oder fehlender Herkunft."""
    kandidaten = db.execute(select(modell)).scalars()
    ziel = _normalisiert(name)
    for kandidat in kandidaten:
        if _normalisiert(kandidat.name) != ziel:
            continue
        if kandidat.quelle == quelle:
            continue
        return kandidat
    return None


def _uebernehme(objekt: Any, felder: dict[str, Any]) -> bool:
    """Setzt Felder, ueberspringt geschuetzte, meldet ob sich etwas aenderte."""
    veraendert = False
    for feld, wert in felder.items():
        if feld in GESCHUETZTE_FELDER:
            continue
        if getattr(objekt, feld) != wert:
            setattr(objekt, feld, wert)
            veraendert = True
    return veraendert


# --- Typ-spezifische Abbildung -------------------------------------------


def _felder_fachbereich(datensatz: ImportDatensatz) -> dict[str, Any]:
    code = datensatz.metadaten.get("code") or datensatz.externe_id
    return {"name": datensatz.name, "code": str(code)[:32]}


def _felder_team(db: Session, datensatz: ImportDatensatz, quelle: str) -> dict[str, Any]:
    org_id = None
    org_externe_id = datensatz.metadaten.get("organisationseinheit_externe_id")
    if org_externe_id:
        org = _finde_nach_externer_id(db, Organisationseinheit, quelle, str(org_externe_id))
        if org is None:
            raise ValueError(
                f"Organisationseinheit '{org_externe_id}' ist in dieser Quelle nicht bekannt"
            )
        org_id = org.id
    return {
        "name": datensatz.name,
        "owner_hinweis": datensatz.owner_hinweis,
        "organisationseinheit_id": org_id,
    }


def _felder_organisationseinheit(
    db: Session, datensatz: ImportDatensatz, quelle: str
) -> dict[str, Any]:
    meta = datensatz.metadaten
    fb_externe_id = meta.get("fachbereich_externe_id")
    if not fb_externe_id:
        raise ValueError("Organisationseinheit braucht 'fachbereich_externe_id' in metadaten")
    fachbereich = _finde_nach_externer_id(db, Fachbereich, quelle, str(fb_externe_id))
    if fachbereich is None:
        raise ValueError(f"Fachbereich '{fb_externe_id}' ist in dieser Quelle nicht bekannt")
    ebene_roh = str(meta.get("ebene", "")).upper()
    if ebene_roh not in (Ebene.INT, Ebene.LAND):
        raise ValueError("metadaten.ebene muss 'INT' oder 'LAND' sein")
    land_code = meta.get("land_code")
    if ebene_roh == Ebene.LAND and not land_code:
        raise ValueError("Eine LAND-Organisationseinheit braucht 'land_code'")
    if ebene_roh == Ebene.INT:
        land_code = None
    return {
        "fachbereich_id": fachbereich.id,
        "ebene": Ebene(ebene_roh),
        "land_code": str(land_code).upper()[:2] if land_code else None,
    }


def _felder_asset(datensatz: ImportDatensatz) -> dict[str, Any]:
    felder: dict[str, Any] = {
        "name": datensatz.name,
        "metadaten": datensatz.metadaten,
        "herkunft": Herkunft.IMPORTIERT,
    }
    if "beschreibung" in datensatz.metadaten:
        felder["beschreibung"] = str(datensatz.metadaten["beschreibung"])
    return felder


MODELL_JE_TYP: dict[ImportTyp, Any] = {
    ImportTyp.FACHBEREICH: Fachbereich,
    ImportTyp.ORGANISATIONSEINHEIT: Organisationseinheit,
    ImportTyp.TEAM: Team,
    ImportTyp.TOOL: ToolObjekt,
    ImportTyp.DATENOBJEKT: Datenobjekt,
}


def _felder(db: Session, datensatz: ImportDatensatz, quelle: str) -> dict[str, Any]:
    if datensatz.typ == ImportTyp.FACHBEREICH:
        return _felder_fachbereich(datensatz)
    if datensatz.typ == ImportTyp.ORGANISATIONSEINHEIT:
        return _felder_organisationseinheit(db, datensatz, quelle)
    if datensatz.typ == ImportTyp.TEAM:
        return _felder_team(db, datensatz, quelle)
    felder = _felder_asset(datensatz)
    if datensatz.typ == ImportTyp.TOOL and "technologie" in datensatz.metadaten:
        felder["technologie"] = str(datensatz.metadaten["technologie"])[:64]
    return felder


def _neuer_datensatz(modell: Any, felder: dict[str, Any], quelle: str, externe_id: str) -> Any:
    werte = dict(felder)
    if modell in (ToolObjekt, Datenobjekt):
        # Neu importierte Assets sind bewusst unbestaetigt (Architektur 7.2, Punkt 2)
        # und erscheinen im Cockpit als "neu importiert, noch nicht zugeordnet".
        werte["status"] = AssetStatus.IMPORTIERT_UNBESTAETIGT
    return modell(quelle=quelle, externe_id=externe_id, **werte)


def verarbeite_datensatz(db: Session, kontext: ImportKontext, datensatz: ImportDatensatz) -> None:
    modell = MODELL_JE_TYP[datensatz.typ]
    try:
        felder = _felder(db, datensatz, kontext.quelle)
    except ValueError as exc:
        kontext.fehler(datensatz.externe_id, str(exc))
        return

    bestehend = _finde_nach_externer_id(db, modell, kontext.quelle, datensatz.externe_id)
    if bestehend is not None:
        vorher = snapshot(bestehend)
        veraendert = _uebernehme(bestehend, felder)
        db.flush()
        if veraendert:
            protokolliere_aenderung(
                db,
                bestehend,
                vorher,
                akteur_user_id=kontext.akteur_user_id,
                beschreibung=f"Import aus {kontext.quelle}",
            )
        kontext.aktualisiert(veraendert)
        return

    if hasattr(modell, "name"):
        dublette = _finde_namensdublette(db, modell, datensatz.name, kontext.quelle)
        if dublette is not None:
            kontext.vorschlag(
                Zusammenfuehrungsvorschlag(
                    typ=datensatz.typ,
                    externe_id=datensatz.externe_id,
                    name=datensatz.name,
                    kandidat_id=dublette.id,
                    kandidat_name=dublette.name,
                    begruendung=(
                        "Gleicher Name, aber keine Uebereinstimmung der externen ID — "
                        "eine automatische Zusammenfuehrung koennte eine falsche "
                        "Klassifikation vererben"
                    ),
                )
            )
            return

    objekt = _neuer_datensatz(modell, felder, kontext.quelle, datensatz.externe_id)
    db.add(objekt)
    db.flush()
    protokolliere(
        db,
        entity_type=objekt.__tablename__,
        entity_id=objekt.id,
        aktion=ChangeAktion.ERSTELLT,
        nachher=snapshot(objekt),
        akteur_user_id=kontext.akteur_user_id,
        akteur_beschreibung=f"Import aus {kontext.quelle}",
    )
    kontext.angelegt()


#: Reihenfolge, in der Typen verarbeitet werden — Fachbereiche vor Einheiten,
#: Einheiten vor Teams, damit Verweise innerhalb eines Laufs aufloesbar sind.
TYP_REIHENFOLGE: dict[ImportTyp, int] = {
    ImportTyp.FACHBEREICH: 0,
    ImportTyp.ORGANISATIONSEINHEIT: 1,
    ImportTyp.TEAM: 2,
    ImportTyp.DATENOBJEKT: 3,
    ImportTyp.TOOL: 4,
}


def importiere(
    db: Session, anfrage: ImportAnfrage, *, akteur_user_id: uuid.UUID | None = None
) -> ImportErgebnis:
    kontext = ImportKontext(anfrage.quelle, akteur_user_id)
    for datensatz in sorted(anfrage.datensaetze, key=lambda d: TYP_REIHENFOLGE[d.typ]):
        verarbeite_datensatz(db, kontext, datensatz)
    return kontext.ergebnis
