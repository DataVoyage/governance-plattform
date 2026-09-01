"""Bewertungs-Modul (Architektur 8.2) — Baumdurchlauf, Tier und K-Klassen.

Es gibt genau eine Implementierung dieser Logik. Der Wizard in der Oberflaeche,
die Historie und spaeter die Governance-Query-API (Architektur 7.3) fragen alle
dieselben Funktionen — eine zweite, abweichende Berechnung waere der sicherste
Weg zu widerspruechlichen Auskuenften.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import Principal, verlange
from app.models.base import now_utc
from app.models.enums import AlarmTyp
from app.models.governance import Alarm, Bewertung, Prozessobjekt
from app.services import ableitung, konfiguration
from app.services.bewertungsbaum import (
    BAUM,
    FRAGE_JE_ID,
    KI_VERBOTEN,
    Block,
    Frage,
    Themenblock,
)
from app.services.changelog import protokolliere_erstellung
from app.services.prozess import Ungueltig, darf_schreiben


class Modus:
    """Die beiden im Leitdokument vorgesehenen Ausgaenge des Wizards."""

    SCHNELL = "schnell"
    VOLLSTAENDIG = "vollstaendig"


ALLE_MODI = (Modus.SCHNELL, Modus.VOLLSTAENDIG)


@dataclass
class Baumstand:
    """Zwischenstand eines Durchlaufs — bewusst ohne Tier-Anzeige.

    Der Wizard zeigt den Zwischenstand nicht an, um vorzeitige Selbstzensur der
    Antworten zu vermeiden (Architektur 8.2). Deshalb traegt dieses Objekt zwar
    die ermittelten Stufen, wird aber erst nach Abschluss nach aussen gegeben.
    """

    stufen: dict[Block, int] = field(default_factory=dict)
    naechste_frage: Frage | None = None
    abgeschlossen: bool = False
    verboten: bool = False
    vollstaendig: bool = True


def _werte_block_aus(
    themenblock: Themenblock, antworten: dict[str, bool]
) -> tuple[int | None, Frage | None, bool]:
    """Liefert ``(stufe, offene_frage, verboten)`` fuer einen Themenblock."""
    tentativ = 0
    for frage in themenblock.fragen:
        if frage.id not in antworten:
            return None, frage, False
        antwort = antworten[frage.id]
        if frage.abbruch_bei_nein:
            if not antwort:
                return 0, None, False
            tentativ = frage.stufe_bei_ja
            continue
        if antwort:
            return frage.stufe_bei_ja, None, frage.verbot_bei_ja
    return tentativ, None, False


def durchlaufe(antworten: dict[str, bool], modus: str = Modus.VOLLSTAENDIG) -> Baumstand:
    """Fuehrt den Baum bis zur naechsten offenen Frage oder bis zum Ende.

    Der Durchlauf ist zustandslos: aus denselben Antworten folgt immer derselbe
    Stand. Damit braucht der Wizard keine serverseitige Sitzung, und die
    Reihenfolge bleibt trotzdem serverseitig festgelegt.
    """
    if modus not in ALLE_MODI:
        raise Ungueltig(f"Unbekannter Modus: {modus}")

    stand = Baumstand()
    for themenblock in BAUM:
        stufe, offene_frage, verboten = _werte_block_aus(themenblock, antworten)
        if verboten:
            stand.stufen[themenblock.block] = KI_VERBOTEN
            stand.verboten = True
            stand.abgeschlossen = True
            stand.vollstaendig = False
            return stand
        if offene_frage is not None:
            stand.naechste_frage = offene_frage
            return stand
        assert stufe is not None
        stand.stufen[themenblock.block] = stufe
        # Die schnelle Variante endet beim ersten Tier-3-Treffer.
        if modus == Modus.SCHNELL and stufe >= 3:
            stand.abgeschlossen = True
            stand.vollstaendig = False
            return stand
    stand.abgeschlossen = True
    return stand


def profil(stand: Baumstand) -> dict[str, int]:
    """Das Sechser-Profil; nicht durchlaufene Bloecke stehen auf 0."""
    return {block.value: stand.stufen.get(block, 0) for block in Block}


def tier(stand: Baumstand) -> int:
    """Tier 1 bis 3 als hoechste erreichte Stufe, mindestens 1."""
    if stand.verboten:
        return 3
    erreicht = [s for s in stand.stufen.values() if s > 0]
    return max(1, min(3, max(erreicht, default=1)))


# --- K-Klassen (Leitdokument A.9.2) --------------------------------------
#
# Jede Klasse haengt an genau einer nachvollziehbaren Bedingung ueber dem
# Profil. Die Ableitung ist reine Rechnung ohne Datenbankzugriff, damit sie an
# jeder Stelle — Wizard, Historie, Query-API — identisch ist.

K_KLASSEN_BESCHREIBUNG: dict[str, str] = {
    "K1": "Dokumentationspflicht des Prozessobjekts",
    "K2": "Selbstverpflichtung des Prozesseigners",
    "K3": "Benannter technischer Owner mit Betriebsverantwortung",
    "K4": "Datenschutz-Folgenabschaetzung",
    "K5": "Zugriffs- und Rechtekonzept",
    "K6": "KI-Transparenz und -Dokumentation nach EU AI Act",
    "K7": "Mitbestimmungsverfahren einleiten",
    "K8": "Regulatorischer Nachweis und Aufbewahrung",
    "K9": "Notfall- und Wiederanlaufkonzept",
    "K10": "Gate-2-Pflicht vor Inbetriebnahme",
}


def leite_k_klassen_ab(werte: dict[str, int]) -> list[str]:
    """Leitet die ausgeloesten Massnahmenklassen aus dem Profil ab."""
    ki = werte.get("ki", 0)
    ds = werte.get("ds", 0)
    mb = werte.get("mb", 0)
    it = werte.get("it", 0)
    rg = werte.get("rg", 0)
    ur = werte.get("ur", 0)
    hoechste = max(ki, ds, mb, it, rg, ur)

    bedingungen: dict[str, bool] = {
        # Grundpflichten: gelten ab dem ersten Tier.
        "K1": True,
        "K2": True,
        # Ab Tier 2 braucht der Betrieb einen benannten Verantwortlichen.
        "K3": hoechste >= 2,
        "K4": ds >= 3,
        "K5": ds >= 2 or it >= 2,
        "K6": ki >= 1,
        "K7": mb >= 1,
        "K8": rg >= 2,
        "K9": ur >= 2,
        # Gate 2 vor Inbetriebnahme: nur bei hoechster Stufe in KI,
        # IT-Sicherheit oder unternehmerischem Risiko.
        "K10": ki >= 3 or it >= 3 or ur >= 3,
    }
    return [klasse for klasse, ausgeloest in bedingungen.items() if ausgeloest]


# --- Persistenz -----------------------------------------------------------


def pruefe_antworten(antworten: dict[str, bool]) -> None:
    unbekannt = sorted(set(antworten) - set(FRAGE_JE_ID))
    if unbekannt:
        raise Ungueltig(f"Unbekannte Frage-IDs: {', '.join(unbekannt)}")


def darf_bewerten(db: Session, principal: Principal, prozess: Prozessobjekt) -> bool:
    """Bewerten darf der Prozess-Owner im eigenen Bereich oder die Governance.

    Der Prozess-Umsetzer ist hier bewusst aussen vor (Matrix 5.3): er pflegt
    die lokale Abweichung, aber die Bewertung bleibt beim Prozessgeber.
    """
    return darf_schreiben(db, principal, prozess.prozessgeber_org_id)


def gueltig_bis(db: Session, tier_wert: int, ab: datetime) -> datetime | None:
    """Ab Tier 3 gilt die jaehrliche Erneuerungspflicht (Leitdokument A.10.5)."""
    if tier_wert < 3:
        return None
    tage = konfiguration.lies_int(db, "bewertung_gueltigkeit_tage_tier3")
    return ab + timedelta(days=tage)


def speichere(
    db: Session,
    principal: Principal,
    prozess: Prozessobjekt,
    antworten: dict[str, bool],
    modus: str = Modus.VOLLSTAENDIG,
) -> Bewertung | Alarm:
    """Schliesst einen Durchlauf ab und legt eine neue Bewertung an.

    Bei einem Treffer auf den Verbotstatbestand (Schritt 1b) wird **keine**
    Bewertung gespeichert, sondern ein Governance-Alarm erzeugt — das
    Prozessobjekt bleibt damit unbewertet und faellt im Cockpit auf.
    """
    verlange(
        darf_bewerten(db, principal, prozess),
        "Bewerten darf der Prozess-Owner im eigenen Bereich oder die Governance-Rolle",
    )
    pruefe_antworten(antworten)
    stand = durchlaufe(antworten, modus)
    if not stand.abgeschlossen:
        raise Ungueltig(
            f"Der Baumdurchlauf ist nicht abgeschlossen; offen ist Frage "
            f"{stand.naechste_frage.id if stand.naechste_frage else '?'}"
        )

    if stand.verboten:
        alarm = Alarm(
            typ=AlarmTyp.KI_VERBOTSTATBESTAND,
            prozessobjekt_id=prozess.id,
            beschreibung=(
                "Der Bewertungsdurchlauf hat einen nach EU AI Act verbotenen "
                "Tatbestand ergeben (Schritt 1b). Es wurde keine Bewertung "
                "gespeichert."
            ),
            ausgeloest_von=principal.user_id,
        )
        db.add(alarm)
        db.flush()
        protokolliere_erstellung(db, alarm, akteur_user_id=principal.user_id)
        return alarm

    werte = profil(stand)
    tier_wert = tier(stand)
    zeitpunkt = now_utc()
    bewertung = Bewertung(
        prozessobjekt_id=prozess.id,
        ki_stufe=werte["ki"],
        ds_stufe=werte["ds"],
        mb_stufe=werte["mb"],
        it_stufe=werte["it"],
        rg_stufe=werte["rg"],
        ur_stufe=werte["ur"],
        tier=tier_wert,
        gesperrt=False,
        vollstaendig=stand.vollstaendig,
        ausgeloeste_k_klassen=leite_k_klassen_ab(werte) if stand.vollstaendig else [],
        antworten=dict(antworten),
        bewertet_von=principal.user_id,
        bewertet_am=zeitpunkt,
        gueltig_bis=gueltig_bis(db, tier_wert, zeitpunkt),
    )
    db.add(bewertung)
    db.flush()
    db.refresh(prozess)
    ableitung.aktualisiere_kette(prozess)
    db.flush()
    protokolliere_erstellung(db, bewertung, akteur_user_id=principal.user_id)
    return bewertung


def historie(db: Session, prozess_id: uuid.UUID) -> list[Bewertung]:
    """Alle Bewertungen, neueste zuerst — vorherige bleiben unveraendert."""
    return list(
        db.execute(
            select(Bewertung)
            .where(Bewertung.prozessobjekt_id == prozess_id)
            .order_by(Bewertung.bewertet_am.desc(), Bewertung.erstellt_am.desc())
        ).scalars()
    )


def aktuelle(db: Session, prozess_id: uuid.UUID) -> Bewertung | None:
    treffer = historie(db, prozess_id)
    return treffer[0] if treffer else None


def ist_abgelaufen(bewertung: Bewertung, jetzt: datetime | None = None) -> bool:
    if bewertung.gueltig_bis is None:
        return False
    zeitpunkt = jetzt or datetime.now(UTC)
    frist = bewertung.gueltig_bis
    if frist.tzinfo is None:
        frist = frist.replace(tzinfo=UTC)
    return frist < zeitpunkt
