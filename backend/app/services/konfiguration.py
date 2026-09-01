"""Inhaltliche Governance-Einstellungen (Architektur 6.6).

Fristen, Vorlaufzeiten und Schwellen liegen bewusst nicht in ENV-Variablen:
sie sind Governance-Inhalt und muessen von der Governance-Rolle im laufenden
Betrieb aenderbar sein, ohne ein Deployment auszuloesen.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import Konfiguration

#: Schluessel -> (Standardwert, Beschreibung)
STANDARDWERTE: dict[str, tuple[str, str]] = {
    "selbstverpflichtung_gueltigkeit_tage": (
        "365",
        "Gueltigkeitsdauer einer Selbstverpflichtung ab Tier 3 (Leitdokument A.10.5)",
    ),
    "selbstverpflichtung_erinnerung_vorlauf_tage": (
        "60",
        "Vorlauf, mit dem vor Ablauf einer Selbstverpflichtung erinnert wird",
    ),
    "bewertung_gueltigkeit_tage_tier3": (
        "365",
        "Jaehrliche Erneuerungspflicht der Bewertung ab Tier 3",
    ),
    "lenkung_frist_tage_tier1": ("90", "Frist eines Lenkungsvorgangs bei Tier 1 (A.13.5)"),
    "lenkung_frist_tage_tier2": ("30", "Frist eines Lenkungsvorgangs bei Tier 2 (A.13.5)"),
    "lenkung_frist_tage_tier3": ("14", "Frist eines Lenkungsvorgangs bei Tier 3 (A.13.5)"),
    "asset_inaktiv_tage": ("180", "Ab wann ein Tool-Objekt im Cockpit als inaktiv gilt"),
}


def initialisiere(db: Session) -> int:
    """Legt fehlende Standardwerte an. Idempotent."""
    vorhanden = {k for (k,) in db.execute(select(Konfiguration.schluessel))}
    neu = 0
    for schluessel, (wert, beschreibung) in STANDARDWERTE.items():
        if schluessel in vorhanden:
            continue
        db.add(Konfiguration(schluessel=schluessel, wert=wert, beschreibung=beschreibung))
        neu += 1
    if neu:
        db.flush()
    return neu


def lies(db: Session, schluessel: str) -> str:
    eintrag = db.execute(
        select(Konfiguration).where(Konfiguration.schluessel == schluessel)
    ).scalar_one_or_none()
    if eintrag is not None:
        return eintrag.wert
    if schluessel in STANDARDWERTE:
        return STANDARDWERTE[schluessel][0]
    raise KeyError(f"Unbekannter Konfigurationsschluessel: {schluessel}")


def lies_int(db: Session, schluessel: str) -> int:
    return int(lies(db, schluessel))


def setze(db: Session, schluessel: str, wert: str) -> Konfiguration:
    eintrag = db.execute(
        select(Konfiguration).where(Konfiguration.schluessel == schluessel)
    ).scalar_one_or_none()
    if eintrag is None:
        beschreibung = STANDARDWERTE.get(schluessel, ("", ""))[1]
        eintrag = Konfiguration(schluessel=schluessel, wert=wert, beschreibung=beschreibung)
        db.add(eintrag)
    else:
        eintrag.wert = wert
    db.flush()
    return eintrag


def lenkungsfrist_tage(db: Session, tier: int) -> int:
    """Tier-abhaengige Frist eines Lenkungsvorgangs (Leitdokument A.13.5)."""
    tier = max(1, min(3, tier))
    return lies_int(db, f"lenkung_frist_tage_tier{tier}")
