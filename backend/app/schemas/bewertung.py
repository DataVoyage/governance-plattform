"""Vertraege des Bewertungs-Moduls (Architektur 8.2)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BelegAus(BaseModel):
    """Ein Grund fuer einen Vorschlag, benannt in der Sprache seiner Quelle."""

    text: str
    quelle: str


class FrageAus(BaseModel):
    """Eine Frage des Baums mit ihren beiden Antwortoptionen.

    ``vorschlag`` ist dreiwertig: ``true``/``false`` heisst „die Datenlage sagt
    das", ``null`` heisst „die Daten geben nichts her". Nur im ersten Fall ist
    eine abweichende Antwort begruendungspflichtig.
    """

    id: str
    text: str
    block: str
    block_titel: str
    nummer: int
    anzahl_bloecke: int
    vorschlag: bool | None = None
    belege: list[BelegAus] = Field(default_factory=list)


class WizardAnfrage(BaseModel):
    modus: str = Field(default="vollstaendig", pattern="^(schnell|vollstaendig)$")
    antworten: dict[str, bool] = Field(default_factory=dict)
    #: Frage-ID auf Begruendungstext, fuer Antworten, die dem Vorschlag
    #: widersprechen. Ohne sie wird der Schritt nicht angenommen.
    begruendungen: dict[str, str] = Field(default_factory=dict)


class WizardSchritt(BaseModel):
    """Antwort des Servers auf einen Wizard-Schritt.

    Enthaelt bewusst **keinen** Zwischenstand: das Ergebnis erscheint erst am
    Ende, um vorzeitige Selbstzensur der Antworten zu vermeiden (Architektur
    8.2). Erst wenn ``abgeschlossen`` wahr ist, traegt ``vorschau`` das Profil.
    """

    naechste_frage: FrageAus | None = None
    abgeschlossen: bool = False
    verboten: bool = False
    vollstaendig: bool = True
    vorschau: ErgebnisAus | None = None


class KKlasseAus(BaseModel):
    """Eine ausgeloeste Massnahmenklasse — mit Namen, nicht nur als Kuerzel."""

    kennung: str
    name: str
    erklaerung: str


class ErgebnisAus(BaseModel):
    tier: int
    profil: dict[str, int]
    ausgeloeste_k_klassen: list[str] = Field(default_factory=list)
    #: Dieselben Klassen ausgeschrieben. Das Kuerzel bleibt daneben stehen,
    #: weil die Query-API und die Historie damit arbeiten.
    klassen: list[KKlasseAus] = Field(default_factory=list)
    #: Die Auflagen des erreichten Tiers nach A.8.6, kumuliert.
    auflagen: list[str] = Field(default_factory=list)
    vollstaendig: bool = True


class BewertungAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prozessobjekt_id: uuid.UUID
    ki_stufe: int
    ds_stufe: int
    mb_stufe: int
    it_stufe: int
    rg_stufe: int
    ur_stufe: int
    tier: int
    gesperrt: bool
    vollstaendig: bool
    ausgeloeste_k_klassen: list[str]
    antworten: dict[str, bool]
    vorschlaege: dict[str, bool] = Field(default_factory=dict)
    abweichungen: dict[str, str] = Field(default_factory=dict)
    bewertet_von: uuid.UUID
    bewertet_am: datetime
    gueltig_bis: datetime | None = None


class AlarmAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    typ: str
    prozessobjekt_id: uuid.UUID | None
    beschreibung: str
    ausgeloest_von: uuid.UUID
    quittiert: bool
    erstellt_am: datetime


class BewertungAbschluss(BaseModel):
    """Ergebnis eines abgeschlossenen Durchlaufs.

    Entweder eine gespeicherte Bewertung — oder, bei einem Treffer auf den
    Verbotstatbestand, ein Alarm und **keine** Bewertung.
    """

    bewertung: BewertungAus | None = None
    alarm: AlarmAus | None = None


WizardSchritt.model_rebuild()
