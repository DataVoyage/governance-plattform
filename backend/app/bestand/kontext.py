"""Gemeinsamer Zustand des Aufbaus: Nachschlagen, Handeln, Zurueckdatieren."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import lade_principal
from app.core.permissions import Principal
from app.db import Base
from app.models.audit import ChangeLog
from app.models.governance import Bewertung, Datenobjekt, Prozessobjekt, ToolObjekt
from app.models.organisation import Fachbereich, Organisationseinheit, User

#: Zeitspalten, die nicht aus der echten Uhr stammen, sondern gerechnet sind.
#:
#: Eine Lenkungsfrist entsteht aus ``arbeitstage_addieren`` auf dem simulierten
#: Meldezeitpunkt und liegt deshalb schon richtig. Wuerde die Rueckdatierung sie
#: mitnehmen, verschoebe sie sich ein zweites Mal und der Vorgang haette eine
#: Frist, die zu seiner Stufe nicht passt.
ZEITEN_OHNE_VERSATZ: frozenset[str] = frozenset({"frist"})


class Unstimmig(Exception):
    """Der Katalog passt nicht zur Fachlogik.

    Wird gemeldet, statt still etwas anderes zu bauen: ein Bestand, der die
    Regeln umgeht, um vollstaendig auszusehen, ist wertlos.
    """


def _tabellen_zu_modell() -> dict[str, Any]:
    """Tabellenname auf ORM-Klasse — fuer die Rueckdatierung des Protokolls."""
    return {
        mapper.class_.__tablename__: mapper.class_
        for mapper in Base.registry.mappers
        if hasattr(mapper.class_, "__tablename__")
    }


def _als_zeitpunkt(text: str) -> datetime | None:
    """Erkennt ISO-Zeitstempel in einem Protokollwert, alles andere nicht."""
    if len(text) < 19 or text[4] != "-" or text[10] != "T":
        return None
    try:
        gelesen = datetime.fromisoformat(text)
    except ValueError:
        return None
    return gelesen if gelesen.tzinfo is not None else gelesen.replace(tzinfo=UTC)


@dataclass
class Kontext:
    """Alles, was die Aufbauschritte voneinander brauchen.

    Die Nachschlagewerke sind nach **Schluesseln** aufgebaut, nicht nach Namen:
    ``kontext.prozess("frischedispo")`` liest sich an jeder Stelle gleich und
    bleibt stabil, wenn sich ein Anzeigename aendert.
    """

    db: Session
    #: Der Tag, auf den sich alle Angaben „vor N Tagen" beziehen.
    heute: datetime
    #: Beginn des Aufbaus nach echter Uhr. Alles, was ab hier geschrieben
    #: wurde, ist ein Zeitstempel dieses Laufs und wird zurueckdatiert.
    start: datetime

    fachbereiche: dict[str, Fachbereich] = field(default_factory=dict)
    einheiten: dict[str, Organisationseinheit] = field(default_factory=dict)
    personen: dict[str, User] = field(default_factory=dict)
    datenobjekte: dict[str, Datenobjekt] = field(default_factory=dict)
    prozesse: dict[str, Prozessobjekt] = field(default_factory=dict)
    tools: dict[str, ToolObjekt] = field(default_factory=dict)
    bewertungen: dict[str, Bewertung] = field(default_factory=dict)
    #: Wann ein Katalogeintrag angelegt wurde, in Tagen vor heute. Damit kann
    #: ein spaeterer Schritt eine Kante datieren, ohne vor die Entstehung ihrer
    #: beiden Enden zu rutschen.
    angelegt: dict[str, int] = field(default_factory=dict)

    _principale: dict[str, Principal] = field(default_factory=dict)
    _modelle: dict[str, Any] = field(default_factory=_tabellen_zu_modell)

    # --- Nachschlagen ----------------------------------------------------

    def fachbereich(self, schluessel: str) -> Fachbereich:
        return self._hole(self.fachbereiche, schluessel, "Fachbereich")

    def einheit(self, schluessel: str) -> Organisationseinheit:
        return self._hole(self.einheiten, schluessel, "Organisationseinheit")

    def person(self, schluessel: str) -> User:
        return self._hole(self.personen, schluessel, "Person")

    def datenobjekt(self, schluessel: str) -> Datenobjekt:
        return self._hole(self.datenobjekte, schluessel, "Datenobjekt")

    def prozess(self, schluessel: str) -> Prozessobjekt:
        return self._hole(self.prozesse, schluessel, "Prozessobjekt")

    def tool(self, schluessel: str) -> ToolObjekt:
        return self._hole(self.tools, schluessel, "Tool-Objekt")

    def _hole(self, wo: dict[str, Any], schluessel: str, was: str) -> Any:
        if schluessel not in wo:
            raise Unstimmig(f"{was} „{schluessel}“ ist im Katalog nicht angelegt")
        return wo[schluessel]

    def wer(self, schluessel: str) -> Principal:
        """Der Handelnde — mit genau den Rollen, die er wirklich hat.

        Jeder Aufbauschritt laeuft unter der Kennung dessen, der ihn im Betrieb
        taete. Das ist keine Kosmetik fuer den Nachweis: die Dienste pruefen
        Berechtigungen, und ein Schritt, den der Zustaendige nicht ausfuehren
        duerfte, scheitert hier laut statt spaeter leise.
        """
        if schluessel not in self._principale:
            self._principale[schluessel] = lade_principal(self.db, self.person(schluessel))
        return self._principale[schluessel]

    def vergiss_rollen(self) -> None:
        """Verwirft die gemerkten Principale, wenn sich Rollen geaendert haben."""
        self._principale.clear()

    # --- Zeit ------------------------------------------------------------

    def zeitpunkt(self, vor_tagen: int, stunde: int = 9, minute: int = 20) -> datetime:
        """Ein Arbeitstag vor ``vor_tagen`` Tagen, zur angegebenen Uhrzeit.

        Faellt der Tag auf ein Wochenende, wird auf den Freitag davor
        vorgezogen. Menschen legen keine Prozessobjekte am Sonntag an, und ein
        Bestand, in dem sie es tun, faellt beim ersten Blick auf.
        """
        tag = self.heute - timedelta(days=vor_tagen)
        while tag.weekday() >= 5:
            tag -= timedelta(days=1)
        return tag.replace(hour=stunde, minute=minute, second=0, microsecond=0)

    @contextmanager
    def aktion(self, vor_tagen: int, stunde: int = 9, minute: int = 20) -> Iterator[datetime]:
        """Fuehrt einen Schritt aus und datiert ihn anschliessend zurueck.

        Innerhalb des Blocks laufen die Dienste ganz normal und schreiben mit
        der echten Uhr. Beim Verlassen wird jeder Zeitstempel, der waehrend
        dieses Laufs entstanden ist, um dieselbe Spanne verschoben — in den
        Datensaetzen und in den Protokolleintraegen.

        Die Regel ist bewusst einfach: verschoben wird, was **ab Beginn des
        Aufbaus** geschrieben wurde. Was ein Aufbauschritt selbst gesetzt hat —
        die letzte Aktivitaet eines Werkzeugs, ein Meldezeitpunkt — liegt davor
        und bleibt unangetastet.
        """
        ab_cursor = self._letzter_cursor()
        wann = self.zeitpunkt(vor_tagen, stunde, minute)
        yield wann
        self.db.flush()
        self._datiere_zurueck(ab_cursor, wann)

    def _letzter_cursor(self) -> int:
        stmt = select(ChangeLog.cursor).order_by(ChangeLog.cursor.desc()).limit(1)
        return self.db.execute(stmt).scalar_one_or_none() or 0

    def _datiere_zurueck(self, ab_cursor: int, wann: datetime) -> None:
        versatz = wann - datetime.now(UTC)
        eintraege = list(
            self.db.execute(select(ChangeLog).where(ChangeLog.cursor > ab_cursor)).scalars()
        )
        betroffen: set[tuple[str, uuid.UUID]] = set()
        for eintrag in eintraege:
            verschoben = self._verschoben(eintrag.zeitpunkt, versatz)
            if verschoben is not None:
                eintrag.zeitpunkt = verschoben
            eintrag.vorher = self._verschobene_werte(eintrag.vorher, versatz)
            eintrag.nachher = self._verschobene_werte(eintrag.nachher, versatz)
            betroffen.add((eintrag.entity_type, eintrag.entity_id))
        for tabelle, kennung in betroffen:
            self._verschiebe_datensatz(tabelle, kennung, versatz)
        self.db.flush()

    def _verschoben(self, wert: datetime | None, versatz: timedelta) -> datetime | None:
        """Verschiebt einen Zeitstempel, wenn er aus diesem Lauf stammt."""
        if wert is None:
            return None
        behaftet = wert if wert.tzinfo is not None else wert.replace(tzinfo=UTC)
        return behaftet + versatz if behaftet >= self.start else None

    def _verschobene_werte(self, stand: dict | None, versatz: timedelta) -> dict | None:
        """Dieselbe Verschiebung in einem Protokoll-Schnappschuss.

        Ohne sie stuende im Nachweis ein Eintrag von vor einem Jahr, in dem als
        Feldwert das heutige Datum steht — und der Nachweis waere genau da
        unglaubwuerdig, wo er gebraucht wird.
        """
        if not stand:
            return stand
        ergebnis: dict[str, Any] = {}
        for feld, wert in stand.items():
            neu = wert
            if isinstance(wert, str) and feld not in ZEITEN_OHNE_VERSATZ:
                gelesen = _als_zeitpunkt(wert)
                verschoben = None if gelesen is None else self._verschoben(gelesen, versatz)
                if verschoben is not None:
                    neu = verschoben.isoformat()
            ergebnis[feld] = neu
        return ergebnis

    def _verschiebe_datensatz(self, tabelle: str, kennung: uuid.UUID, versatz: timedelta) -> None:
        modell = self._modelle.get(tabelle)
        if modell is None:
            return
        objekt = self.db.get(modell, kennung)
        if objekt is None:
            return
        for spalte in modell.__mapper__.column_attrs:
            if spalte.key in ZEITEN_OHNE_VERSATZ:
                continue
            wert = getattr(objekt, spalte.key, None)
            if not isinstance(wert, datetime):
                continue
            verschoben = self._verschoben(wert, versatz)
            if verschoben is not None:
                setattr(objekt, spalte.key, verschoben)
