"""Unternehmerisches Risiko als komposite Ebene (Leitdokument A.8.4, AP-19).

UR ist keine einzelne Aussage. Es besteht aus **wie weit reicht der Prozess**
und **was passiert, wenn er ausfaellt**. Keiner der beiden Werte traegt allein:
Ein kritischer Ausfall, der eine Person betrifft, ist kein Unternehmensrisiko;
eine geringe Stoerung, die das ganze Unternehmen trifft, kann eines sein.

Beide Anteile sind **erklaerte Erwartungen** des Prozess-Owners — Kundenkreis
und Ausfallfolge, beide kontrollierte Listen (E-1). Die erlaubte Reichweite ist
die gerechnete Normalform des Kundenkreises (``ableitung.leite_reichweite_ab``).
Damit ist UR vollstaendig ableitbar, und nach P1 wird es deshalb **nicht
erfragt**: bis AP-19 kannte der Bewertungsbaum dafuer drei Fragen, deren
richtige Antwort die Anwendung bereits kannte und als Vorschlag danebenstellte
(E-65).

Die Kompositionstabelle liegt als **gepflegte Stammdaten** in der Datenbank,
nicht als Konstante im Code: sie ist eine Bewertungsgrundlage, und eine, die
nur mit einer Auslieferung aenderbar waere, veraltet zwischen zwei Releases
(analog E-42). Die Standardbelegung steht hier und wird beim ersten Zugriff
angelegt, wenn ein Feld fehlt.

**Die Kette gehoert nicht hierher.** Was ein nachgelagerter Prozess an Risiko
mitbringt, ist kein *eigenes* Betriebsrisiko, sondern Abhaengigkeit. Es wirkt
deshalb auf der Tier-Stufe, nicht in dieser Dimension (E-67) — nur so laesst
sich Schritt 6a aus A.8.5 ueberhaupt formulieren, der das eigene Betriebsrisiko
bei Tier 2 kappt. ``ur_der_kette`` liefert den Anteil, ``bewertung.tier``
verrechnet ihn.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import Principal, verlange
from app.models.enums import (
    AUSFALLFOLGE_STUFE,
    Ausfallfolge,
    Reichweite,
)
from app.models.governance import Prozessobjekt, UrKomposition
from app.services import ableitung
from app.services.changelog import protokolliere_aenderung, snapshot
from app.services.prozess import NichtGefunden, Ungueltig

#: Hoechste Stufe, die eine Dimension annehmen kann.
HOECHSTE_STUFE = 3

#: Die Standardbelegung (Spezifikation `docs/tier-als-lenkungsobjekt.md`, 3.2).
#:
#: Zeilen sind die Ausfallfolge, Spalten die erlaubte Reichweite. Gelesen wird
#: sie als „was passiert" mal „wen trifft es".
STANDARDTABELLE: dict[tuple[str, str], int] = {
    (Ausfallfolge.KEINE, Reichweite.PERSOENLICH): 0,
    (Ausfallfolge.KEINE, Reichweite.TEAM): 0,
    (Ausfallfolge.KEINE, Reichweite.BEREICH): 0,
    (Ausfallfolge.KEINE, Reichweite.UNTERNEHMEN): 0,
    (Ausfallfolge.KEINE, Reichweite.EXTERN): 1,
    (Ausfallfolge.GERING, Reichweite.PERSOENLICH): 0,
    (Ausfallfolge.GERING, Reichweite.TEAM): 1,
    (Ausfallfolge.GERING, Reichweite.BEREICH): 1,
    (Ausfallfolge.GERING, Reichweite.UNTERNEHMEN): 2,
    (Ausfallfolge.GERING, Reichweite.EXTERN): 2,
    (Ausfallfolge.SPUERBAR, Reichweite.PERSOENLICH): 1,
    (Ausfallfolge.SPUERBAR, Reichweite.TEAM): 1,
    (Ausfallfolge.SPUERBAR, Reichweite.BEREICH): 2,
    (Ausfallfolge.SPUERBAR, Reichweite.UNTERNEHMEN): 3,
    (Ausfallfolge.SPUERBAR, Reichweite.EXTERN): 3,
    (Ausfallfolge.KRITISCH, Reichweite.PERSOENLICH): 1,
    (Ausfallfolge.KRITISCH, Reichweite.TEAM): 2,
    (Ausfallfolge.KRITISCH, Reichweite.BEREICH): 3,
    (Ausfallfolge.KRITISCH, Reichweite.UNTERNEHMEN): 3,
    (Ausfallfolge.KRITISCH, Reichweite.EXTERN): 3,
}


@dataclass(frozen=True)
class UrStand:
    """Die UR-Stufe samt den beiden Anteilen, aus denen sie entsteht.

    Beide Anteile stehen mit dabei, weil eine gerechnete Stufe ohne ihren
    Rechenweg auf dem Bildschirm eine Behauptung waere. Der Wizard zeigt sie
    als Ausgangslage an, nicht als Frage (E-65).
    """

    stufe: int
    reichweite: Reichweite
    ausfallfolge: Ausfallfolge


def initialisiere(db: Session) -> int:
    """Legt fehlende Felder der Kompositionstabelle an. Idempotent."""
    vorhanden = {
        (e.ausfallfolge, e.reichweite) for e in db.execute(select(UrKomposition)).scalars()
    }
    neu = 0
    for (ausfallfolge, reichweite), stufe in STANDARDTABELLE.items():
        if (ausfallfolge, reichweite) in vorhanden:
            continue
        db.add(UrKomposition(ausfallfolge=ausfallfolge, reichweite=reichweite, stufe=stufe))
        neu += 1
    if neu:
        db.flush()
    return neu


def tabelle(db: Session) -> list[UrKomposition]:
    """Die vollstaendige Tabelle, nach Ausfallfolge und Reichweite geordnet."""
    initialisiere(db)
    eintraege = list(db.execute(select(UrKomposition)).scalars())
    return sorted(
        eintraege,
        key=lambda e: (
            list(AUSFALLFOLGE_STUFE).index(e.ausfallfolge),
            _reichweite_rang(e.reichweite),
        ),
    )


def _reichweite_rang(reichweite: str) -> int:
    return list(Reichweite).index(Reichweite(reichweite))


def stufe_fuer(db: Session, ausfallfolge: str, reichweite: str) -> int:
    """Die hinterlegte Stufe fuer ein Feld der Tabelle."""
    eintrag = db.execute(
        select(UrKomposition).where(
            UrKomposition.ausfallfolge == ausfallfolge,
            UrKomposition.reichweite == reichweite,
        )
    ).scalar_one_or_none()
    if eintrag is not None:
        return eintrag.stufe
    # Vor dem ersten Zugriff auf die Tabelle: die Standardbelegung gilt auch
    # ungespeichert, damit eine frische Datenbank nicht anders rechnet.
    return STANDARDTABELLE[(Ausfallfolge(ausfallfolge), Reichweite(reichweite))]


def ur_stufe(db: Session, prozess: Prozessobjekt) -> UrStand:
    """Das **eigene** unternehmerische Risiko eines Prozessobjekts.

    Ohne Kettenanteil — der wirkt auf der Tier-Stufe (E-67).
    """
    reichweite = prozess.reichweite or ableitung.leite_reichweite_ab(prozess)
    ausfallfolge = prozess.ausfallfolge
    return UrStand(
        stufe=stufe_fuer(db, ausfallfolge, reichweite),
        reichweite=Reichweite(reichweite),
        ausfallfolge=Ausfallfolge(ausfallfolge),
    )


def _eigene_stufe(db: Session, prozess: Prozessobjekt, _zwischen: dict) -> int:
    if prozess.id not in _zwischen:
        _zwischen[prozess.id] = ur_stufe(db, prozess).stufe
    return _zwischen[prozess.id]


def ur_der_kette(db: Session, prozess: Prozessobjekt) -> tuple[int, Prozessobjekt | None]:
    """Das hoechste UR aller **transitiven Nachfolger**, samt seiner Quelle.

    Die Richtung folgt A.4.2: Wer einen kritischen Prozess beliefert, ist selbst
    kritisch. Gezaehlt wird das **komposite** UR des Nachfolgers, nicht seine
    blosse Ausfallfolge — ein Prozess mit kritischem Ausfall, der nur eine
    Person betrifft, reisst niemanden mit. Genau an diesem Unterschied ist die
    frueher daneben gefuehrte ``kritikalitaet`` am Prozessobjekt gescheitert:
    Sie kannte die Reichweite nicht und behauptete deshalb eine Kettenwirkung,
    die das Tier gar nicht hatte (E-72).

    Der eigene Wert ist **nicht** enthalten. Ist die zweite Stelle ``None``,
    bringt die Kette nichts bei.
    """
    zwischen: dict[uuid.UUID, int] = {}
    besucht: set[uuid.UUID] = {prozess.id}
    hoechste = 0
    quelle: Prozessobjekt | None = None
    stapel = list(prozess.nachgelagert)
    while stapel:
        aktuell = stapel.pop()
        if aktuell.id in besucht:
            continue
        besucht.add(aktuell.id)
        stufe = _eigene_stufe(db, aktuell, zwischen)
        if stufe > hoechste:
            hoechste, quelle = stufe, aktuell
        stapel.extend(aktuell.nachgelagert)
    return hoechste, quelle


def setze_feld(
    db: Session,
    principal: Principal,
    ausfallfolge: str,
    reichweite: str,
    *,
    stufe: int,
    begruendung: str,
) -> UrKomposition:
    """Aendert ein Feld der Kompositionstabelle — nur die Governance-Rolle.

    Die Begruendung ist Pflicht. Ein Feld dieser Tabelle entscheidet ueber das
    Tier ganzer Prozessgruppen; wer das aendert, schuldet den Satz, warum.
    """
    verlange(principal.ist_governance, "Die Kompositionstabelle pflegt die Governance-Rolle")
    if ausfallfolge not in set(Ausfallfolge):
        raise NichtGefunden(f"Unbekannte Ausfallfolge: {ausfallfolge}")
    if reichweite not in set(Reichweite):
        raise NichtGefunden(f"Unbekannte Reichweite: {reichweite}")
    if not 0 <= stufe <= HOECHSTE_STUFE:
        raise Ungueltig(f"Die Stufe liegt zwischen 0 und {HOECHSTE_STUFE}")
    if not begruendung.strip():
        raise Ungueltig(
            "Ein Feld der Kompositionstabelle ist zu begründen — es entscheidet "
            "über das Tier ganzer Prozessgruppen"
        )

    initialisiere(db)
    eintrag = db.execute(
        select(UrKomposition).where(
            UrKomposition.ausfallfolge == ausfallfolge,
            UrKomposition.reichweite == reichweite,
        )
    ).scalar_one_or_none()
    if eintrag is None:  # pragma: no cover — initialisiere legt jedes Feld an
        raise NichtGefunden("Feld der Kompositionstabelle nicht gefunden")
    vorher = snapshot(eintrag)
    eintrag.stufe = stufe
    eintrag.begruendung = begruendung
    eintrag.geaendert_von = principal.user_id
    db.flush()
    protokolliere_aenderung(db, eintrag, vorher, akteur_user_id=principal.user_id)
    return eintrag
