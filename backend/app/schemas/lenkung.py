"""Vertraege fuer Compliance-Zustand und Lenkung (Architektur 8.6)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Aufloesungsart, ComplianceFarbe, LenkungStatus, Schicht2Verbot


class AbweichungMelden(BaseModel):
    """Der eine Knopf. Ein Feld, und das kennt die Anwendung nicht (E-64).

    Farbe, Abweichungsart und das verletzte Verbot standen frueher hier zur
    Auswahl. Alle drei misst die Anwendung selbst; sie zu erfragen hiess, eine
    Antwort zu erlauben, die dem eigenen Befund widerspricht.
    """

    #: Was beobachtet wurde. Pflicht: ohne sie stuende im Vorgang nur, dass
    #: jemand etwas bemerkt hat.
    begruendung: str = Field(min_length=1)


class ZustandAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tool_objekt_id: uuid.UUID
    farbe: ComplianceFarbe
    begruendung: str
    abweichung_art: str | None = None
    schicht2_verbot: Schicht2Verbot | None = None
    festgestellt_am: datetime
    festgestellt_von: uuid.UUID | None = None


class ComplianceAus(BaseModel):
    """Der Zustand eines Werkzeugs: gerechnet, mit seinem Verlauf darunter.

    ``farbe`` ist keine gespeicherte Angabe, sondern die Messung von jetzt
    (A.13.3). Der ``verlauf`` bleibt die Zeitreihe: was gemeldet und wie
    geschlossen wurde, mit Datum und Namen. Beides nebeneinander, weil das eine
    den Stand sagt und das andere den Weg dorthin.
    """

    farbe: ComplianceFarbe
    #: Was die Anwendung gerade selbst sieht; leer heisst: nichts.
    offene_abweichungen: list[str] = Field(default_factory=list)
    verlauf: list[ZustandAus] = Field(default_factory=list)


class LenkungsrechteAus(BaseModel):
    """Wer diesen Vorgang schliessen darf (A.13.6)."""

    aufloesen: bool = False
    abbrechen: bool = False


class LenkungAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tool_objekt_id: uuid.UUID
    compliance_zustand_id: uuid.UUID | None = None
    eskalationsstufe: int
    schicht2_verbot: Schicht2Verbot | None = None
    frist: datetime
    zugewiesen_an: uuid.UUID | None = None
    status: LenkungStatus
    aufloesungsart: Aufloesungsart | None = None
    aufloesung_bewertung_id: uuid.UUID | None = None
    aufgeloest_am: datetime | None = None
    beschreibung: str
    #: Getrennt von der Feststellung (E-63): zwei Aussagen, zwei Felder.
    aufloesungskommentar: str = ""
    #: Was die Anwendung am Werkzeug gerade selbst misst. Leer heisst: sie
    #: sieht nichts mehr, was einer Aufloesung als „angepasst" widerspraeche.
    offene_abweichungen: list[str] = Field(default_factory=list)
    erstellt_am: datetime

    rechte: LenkungsrechteAus = Field(default_factory=LenkungsrechteAus)


class MeldungAus(BaseModel):
    """Was die Meldung ausgeloest hat.

    ``zustand`` fehlt, wenn nichts passiert ist: dann lief fuer dieses Werkzeug
    schon ein ungeklaerter Vorgang, und der steht daneben (E-64).
    """

    zustand: ZustandAus | None = None
    lenkungsvorgang: LenkungAus | None = None


class Aufloesen(BaseModel):
    """Genau eine der drei zulaessigen Aufloesungen aus A.13.6."""

    art: Aufloesungsart
    #: Pflicht bei ``rahmen_erweitern``: die neue, danach entstandene Bewertung.
    bewertung_id: uuid.UUID | None = None
    kommentar: str = ""


class Abbrechen(BaseModel):
    kommentar: str = ""
