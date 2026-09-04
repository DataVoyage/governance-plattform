"""Der Aufbau des kleinen Bestands — jeder Fall genau einmal.

Alles entsteht über die Dienstschicht, unter der Kennung dessen, der es im
Betrieb täte. Ein Aufbau, der die eigenen Regeln umgeht, um vollständig
auszusehen, sagt über sie nichts aus.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.bestand.aufbau import ZAEHLUNG, ordne_protokoll_chronologisch
from app.bestand.kontext import Kontext
from app.lehrbestand import (
    daten,
    gates,
    governance,
    organisation,
    prozesse,
    rahmen,
    werkzeuge,
)

#: Die Schritte, in genau dieser Reihenfolge. Jeder baut auf dem vorigen auf.
SCHRITTE: tuple[tuple[str, object], ...] = (
    ("Fachbereiche, Einheiten und Zugaenge", organisation.baue),
    ("Technologiematrix und Einstellungen", organisation.stammdaten),
    ("Datenobjekte — jede Kategorie einmal", daten.baue),
    ("Prozessobjekte, Kette und Umsetzungen", prozesse.baue),
    ("Bewertungen — Tier 1, 2 und 3", prozesse.bewerte),
    ("Selbstverpflichtung, Gate 1 und Inbetriebnahme", gates.lebenszyklus),
    ("Aufstieg auf Tier 3 im laufenden Betrieb", gates.aufstieg),
    ("Gate 2 an einem laufenden Prozess", gates.gate2),
    ("Tool-Objekte und ihre Kanten", werkzeuge.baue),
    ("Erlaubnisrahmen: eingehalten, verletzt, Schicht 2", rahmen.baue),
    ("Vorgefundene Objekte aus dem Import", werkzeuge.vorgefunden),
    ("Erklaerungen der technischen Owner", governance.erklaerungen),
    ("Governance-Entscheidungen: Gate, Lenkung, Matrix", governance.entscheidungen),
    ("Ein stehender Schicht-2-Verstoss", governance.stehender_verstoss),
    ("Die Datenlage bewegt sich", governance.datenlage_bewegt_sich),
    ("Alle Auswege aus dem Lenkungsprozess", governance.lenkungswege),
    ("Ein Gate-Vorgang in Pruefung", governance.gate_in_pruefung),
    ("Verbotstatbestand nach EU AI Act", governance.verbotstatbestand),
    ("Ausgeschiedener Owner, inaktives Werkzeug, Erinnerungen", governance.nachtraege),
)


@dataclass
class Bericht:
    """Was entstanden ist, und wie lange es gedauert hat."""

    zahlen: dict[str, int] = field(default_factory=dict)
    sekunden: float = 0.0

    def als_text(self) -> str:
        breite = max(len(name) for name in self.zahlen)
        zeilen = [f"  {name.ljust(breite)}  {zahl:>6}" for name, zahl in self.zahlen.items()]
        return "\n".join(zeilen)


def baue(db: Session, *, heute: datetime | None = None, melde=None) -> Bericht:
    """Baut den kleinen Bestand in einer Sitzung auf."""
    beginn = datetime.now(UTC)
    stichtag = (heute or beginn).replace(hour=0, minute=0, second=0, microsecond=0)
    kontext = Kontext(db=db, heute=stichtag, start=beginn)

    for name, schritt in SCHRITTE:
        schritt(kontext)
        db.commit()
        if melde is not None:
            melde(name)

    ordne_protokoll_chronologisch(db)
    db.commit()

    bericht = Bericht(sekunden=(datetime.now(UTC) - beginn).total_seconds())
    for name, modell in ZAEHLUNG:
        bericht.zahlen[name] = db.execute(select(func.count()).select_from(modell)).scalar_one()
    return bericht
