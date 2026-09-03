"""Die Reihenfolge des Aufbaus — und die Zaehlung am Ende.

Die Reihenfolge ist keine Bequemlichkeit, sondern der Lebenszyklus selbst:
Organisation, Datenobjekte, Prozessobjekte, Werkzeuge, Bewertung,
Selbstverpflichtung, Gate, Aktivierung. Wer sie umstellt, baut einen Bestand,
den die Anwendung so nie haette entstehen lassen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.bestand import bewertungen, daten, nachtraege, organisation, prozesse, vorgaenge, werkzeuge
from app.bestand.kontext import Kontext
from app.models.audit import ChangeLog
from app.models.governance import (
    Alarm,
    Benachrichtigung,
    Bewertung,
    ComplianceZustand,
    Datenobjekt,
    GateVorgang,
    Kompensation,
    Lenkungsvorgang,
    Prozessobjekt,
    Selbstverpflichtung,
    Technologiebewertung,
    ToolObjekt,
)
from app.models.organisation import Fachbereich, Organisationseinheit, Rollenzuweisung, Team, User

#: Was am Ende gezaehlt wird — die Zeilen, die den Bestand ausmachen.
ZAEHLUNG: tuple[tuple[str, type], ...] = (
    ("Fachbereiche", Fachbereich),
    ("Organisationseinheiten", Organisationseinheit),
    ("Teams", Team),
    ("Menschen", User),
    ("Rollenzuweisungen", Rollenzuweisung),
    ("Datenobjekte", Datenobjekt),
    ("Prozessobjekte", Prozessobjekt),
    ("Tool-Objekte", ToolObjekt),
    ("Bewertungen", Bewertung),
    ("Selbstverpflichtungen", Selbstverpflichtung),
    ("Gate-Vorgaenge", GateVorgang),
    ("Compliance-Zustaende", ComplianceZustand),
    ("Lenkungsvorgaenge", Lenkungsvorgang),
    ("Technologiematrix", Technologiebewertung),
    ("Kompensationen", Kompensation),
    ("Governance-Alarme", Alarm),
    ("Benachrichtigungen", Benachrichtigung),
    ("Protokolleintraege", ChangeLog),
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


#: Die Schritte des Aufbaus, in genau dieser Reihenfolge.
SCHRITTE: tuple[tuple[str, object], ...] = (
    ("Organisation, Menschen und Rollen", organisation.baue),
    ("Technologiematrix", vorgaenge.technologiematrix),
    ("Governance-Einstellungen", vorgaenge.einstellungen),
    ("Datenobjekte", daten.baue),
    ("Prozessobjekte und Ketten", prozesse.baue),
    ("Tool-Objekte und ihre Kanten", werkzeuge.baue),
    ("Erstbewertungen", bewertungen.baue),
    ("Selbstverpflichtung, Gate 1 und Inbetriebnahme", vorgaenge.lebenszyklus),
    ("Stilllegungen", vorgaenge.stilllegungen),
    ("Gate-2-Vorgaenge", vorgaenge.gate2_vorgaenge),
    ("Jaehrliche Erneuerung der Bewertungen", bewertungen.erneuere),
    ("Erneuerte Selbstverpflichtungen", vorgaenge.selbstverpflichtungen_erneuern),
    ("Selbstverpflichtungen der technischen Owner", vorgaenge.selbstverpflichtungen_tool),
    ("Kompensierende Massnahmen", vorgaenge.kompensationen),
    ("Compliance-Zustaende und Lenkungsvorgaenge", vorgaenge.lenkungsvorgaenge),
    ("Nachtraegliche Aenderungen der Datenlage", nachtraege.datenlage_hat_sich_bewegt),
    ("Neu erklaertes externes Ziel", nachtraege.neues_externes_ziel),
    ("Alt-Anwendungen im Migrationspfad", nachtraege.altanwendungen),
    ("Ausgeschiedene Beschaeftigte", organisation.deaktiviere_ausgeschiedene),
    ("Erinnerungslauf", nachtraege.erinnerungen),
)


def baue(db: Session, *, heute: datetime | None = None, melde=None) -> Bericht:
    """Baut den vollstaendigen Bestand in einer Sitzung auf.

    ``melde`` bekommt nach jedem Schritt seinen Namen — der Aufbau dauert ein
    paar Minuten, und eine stumme Minute sieht aus wie ein Haenger.
    """
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


def ordne_protokoll_chronologisch(db: Session) -> None:
    """Bringt den Protokoll-Cursor mit der Zeit in Einklang.

    Der Cursor ist eine monoton steigende Sequenznummer, und im Betrieb steigt
    er mit der Zeit, weil dort in der Zeit gearbeitet wird. Dieser Aufbau kann
    das nicht: er legt ein zwei Jahre altes Prozessobjekt vor einem halbjahr
    alten an, aber beides in derselben Minute. Ohne diesen Schritt stuenden im
    Nachweis die Eintraege in einer Reihenfolge, die keiner Uhr folgt.

    Umnummeriert wird nur der Cursor, nichts am Inhalt. Zweistufig, weil der
    Cursor der Primaerschluessel ist und eine Zwischenkollision sonst
    unvermeidlich waere.
    """
    db.execute(text("UPDATE change_log SET cursor = cursor + 100000000"))
    db.execute(
        text(
            "WITH neu AS ("
            "  SELECT cursor, row_number() OVER (ORDER BY zeitpunkt, cursor) AS rang"
            "  FROM change_log"
            ") "
            "UPDATE change_log AS c SET cursor = neu.rang FROM neu WHERE c.cursor = neu.cursor"
        )
    )
    db.execute(
        text(
            "SELECT setval(pg_get_serial_sequence('change_log', 'cursor'), "
            "COALESCE((SELECT max(cursor) FROM change_log), 1))"
        )
    )


def ist_leer(db: Session) -> bool:
    """Ist die Datenbank unberuehrt? Nur dann laeuft der Aufbau ohne ``--leeren``."""
    for _name, modell in ZAEHLUNG:
        if db.execute(select(func.count()).select_from(modell)).scalar_one():
            return False
    return True
