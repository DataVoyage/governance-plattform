"""Vertraege des Asset-Management-Moduls (Architektur 8.3)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AssetStatus,
    Ausfuehrungsidentitaet,
    Datenkategorie,
    Herkunft,
    Lauftyp,
    Wirkungsart,
    Zugriffsart,
)


class KantenbeitragAus(BaseModel):
    """Was eine einzelne Prozesskante zum geerbten Maximum beitraegt."""

    prozess_id: uuid.UUID
    name: str
    kritikalitaet: int = 0
    reichweite: str | None = None
    tier: int | None = None
    mitbestimmung_flag: bool = False
    k_klassen: list[str] = Field(default_factory=list)
    massgeblich: bool = False


class GeerbtAus(BaseModel):
    """Maximum-Vererbung ueber alle Prozesskanten (Leitdokument A.4.4)."""

    kritikalitaet: int = 0
    reichweite: str | None = None
    tier: int | None = None
    mitbestimmung_flag: bool = False
    k_klassen: list[str] = Field(default_factory=list)
    quelle_prozess_ids: list[uuid.UUID] = Field(default_factory=list)
    beitraege: list[KantenbeitragAus] = Field(default_factory=list)


class ToolAnlegen(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    beschreibung: str = ""
    technologie: str | None = Field(default=None, max_length=64)
    kategorie: str | None = Field(default=None, max_length=48)
    technischer_owner_user_id: uuid.UUID | None = None
    stellvertretung_user_id: uuid.UUID | None = None
    organisationseinheit_id: uuid.UUID | None = None
    lauftyp: Lauftyp | None = None


class ToolAendern(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    beschreibung: str | None = None
    technologie: str | None = Field(default=None, max_length=64)
    kategorie: str | None = Field(default=None, max_length=48)
    technischer_owner_user_id: uuid.UUID | None = None
    stellvertretung_user_id: uuid.UUID | None = None
    organisationseinheit_id: uuid.UUID | None = None
    lauftyp: Lauftyp | None = None
    #: Gemessene Seite des Erlaubnisrahmens (A.13.2 Schicht 1, Elemente 4 und 7)
    #: und das Signal fuer eines der Schicht-2-Verbote.
    ausfuehrungsidentitaet: Ausfuehrungsidentitaet | None = None
    statische_zugangsdaten: bool | None = None
    protokollierung_umgangen: bool | None = None
    daten_ins_offene_netz: bool | None = None
    externe_ziele: list[str] | None = None
    metadaten: dict[str, Any] | None = None


class AttestierungAendern(BaseModel):
    """Die drei Erklaerungen aus Leitdokument A.6 — alle drei, oder keine.

    Ein Teil-Update waere hier falsch: die Attestierung ist eine Erklaerung zu
    einem Zeitpunkt, keine Sammlung unabhaengiger Felder. Wer sie erneuert,
    erklaert alle drei Fragen neu.
    """

    attest_entscheidung_ueber_personen: bool
    attest_mensch_dazwischen: bool
    attest_undeklarierte_quellen: bool


class ToolrechteAus(BaseModel):
    """Was der Anfragende mit **diesem** Tool-Objekt tun darf.

    Eine Auskunft, keine Sicherung — siehe ``services/rechte.py``.
    """

    bearbeiten: bool = False
    attestieren: bool = False
    verknuepfen: bool = False
    zustand_melden: bool = False
    kompensieren: bool = False
    selbstverpflichten: bool = False
    bestaetigen: bool = False


class DatenobjektrechteAus(BaseModel):
    """Vier getrennte Rechte, weil vier verschiedene Rollen sie tragen
    (docs/rollen-und-scopes.md, 7.4)."""

    #: Name, Beschreibung, Quellsystem — Datenobjekt-Owner oder gebender Prozess.
    bearbeiten: bool = False
    #: Die Kategorie — nur der Datenobjekt-Owner des Fachbereichs.
    kategorisieren: bool = False
    #: Den Fachbereich wechseln — nur die Governance.
    anker_aendern: bool = False
    bestaetigen: bool = False


class ToolAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    beschreibung: str
    technologie: str | None = None
    kategorie: str | None = None
    technischer_owner_user_id: uuid.UUID | None = None
    stellvertretung_user_id: uuid.UUID | None = None
    organisationseinheit_id: uuid.UUID | None = None
    lauftyp: Lauftyp | None = None
    ausfuehrungsidentitaet: Ausfuehrungsidentitaet | None = None
    statische_zugangsdaten: bool | None = None
    protokollierung_umgangen: bool | None = None
    daten_ins_offene_netz: bool | None = None
    externe_ziele: list[str] = Field(default_factory=list)
    herkunft: Herkunft
    quelle: str | None = None
    externe_id: str | None = None
    status: AssetStatus
    metadaten: dict[str, Any] = Field(default_factory=dict)
    letzte_aktivitaet_am: datetime | None = None
    prozessobjekt_ids: list[uuid.UUID] = Field(default_factory=list)
    geerbt: GeerbtAus = Field(default_factory=GeerbtAus)

    # Attestierungen nach A.6. ``None`` heisst unbeantwortet — ohne Antwort
    # keine Prozessverknuepfung.
    attest_entscheidung_ueber_personen: bool | None = None
    attest_mensch_dazwischen: bool | None = None
    attest_undeklarierte_quellen: bool | None = None
    attestiert_am: datetime | None = None
    attestiert_von_user_id: uuid.UUID | None = None
    #: Wer erklaert hat, im Klartext. A.6 verlangt die Attestierung
    #: ausdruecklich mit Namen; der Name gehoert damit zum Datensatz und nicht
    #: in eine Auswahlliste, die je nach Rolle anders ausfaellt.
    attestiert_von_name: str | None = None
    #: Wer erklaert hat, im Klartext. A.6 verlangt die Attestierung
    #: ausdruecklich „mit Namen"; der Name gehoert damit zum Datensatz und
    #: nicht in eine Auswahlliste, die je nach Rolle anders ausfaellt.
    attestiert_von_name: str | None = None
    attestierung_vollstaendig: bool = False
    #: Triage aus A.6; ``None``, solange Attestierung 2 offen ist.
    wirkungsart: Wirkungsart | None = None
    #: Welches Signal die Triage traegt — die Oberflaeche schreibt den Satz.
    wirkungsart_grund: str = "offen"

    #: Bei importierten Datensaetzen am Ursprungssystem zu pflegen.
    schreibgeschuetzte_felder: list[str] = Field(default_factory=list)

    rechte: ToolrechteAus = Field(default_factory=ToolrechteAus)


class DatenobjektAnlegen(BaseModel):
    """Zwei Wege, einen Fachbereich zu bekommen — keiner fragt (P1).

    Entweder nennt der Anlegende den gebenden Prozess, dann ist der Fachbereich
    der des Prozessgebers und das Datenobjekt haengt als dessen Output; oder er
    nennt den Fachbereich selbst, dann muss er dessen Datenobjekt-Owner sein.
    """

    name: str = Field(min_length=1, max_length=255)
    beschreibung: str = ""
    kategorie: Datenkategorie | None = None
    fachbereich_id: uuid.UUID | None = None
    prozessobjekt_id: uuid.UUID | None = None
    quellsystem: str | None = Field(default=None, max_length=255)


class DatenobjektAendern(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    beschreibung: str | None = None
    kategorie: Datenkategorie | None = None
    fachbereich_id: uuid.UUID | None = None
    quellsystem: str | None = Field(default=None, max_length=255)
    metadaten: dict[str, Any] | None = None


class DatenobjektAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    beschreibung: str
    kategorie: Datenkategorie | None = None
    fachbereich_id: uuid.UUID | None = None
    quellsystem: str | None = None
    herkunft: Herkunft
    quelle: str | None = None
    externe_id: str | None = None
    status: AssetStatus
    metadaten: dict[str, Any] = Field(default_factory=dict)
    schreibgeschuetzte_felder: list[str] = Field(default_factory=list)

    rechte: DatenobjektrechteAus = Field(default_factory=DatenobjektrechteAus)


class DatenobjektKatalogAus(BaseModel):
    """Die vier Felder der Stufe 1 (A.7) — fuer die Auswahl, nicht fuer die Pflege.

    Bewusst ein eigenes Schema statt der Detailantwort mit ausgeblendeten
    Feldern: der Katalog ist die eine, schmale Ausnahme von der Regel, dass
    ausserhalb des Bereichs nichts geliefert wird (docs/rollen-und-scopes.md,
    7.3). Was er nicht enthaelt, ist auch nicht da.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    fachbereich_id: uuid.UUID | None = None
    kategorie: Datenkategorie | None = None
    quellsystem: str | None = None


class ProzessVerknuepfung(BaseModel):
    prozessobjekt_id: uuid.UUID


class DatenobjektVerknuepfung(BaseModel):
    datenobjekt_id: uuid.UUID
    zugriffsart: Zugriffsart = Zugriffsart.LESEN


class ZugriffsartAendern(BaseModel):
    zugriffsart: Zugriffsart


class ToolDatenobjektAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tool_objekt_id: uuid.UUID
    datenobjekt_id: uuid.UUID
    zugriffsart: Zugriffsart


class DatennutzungAus(BaseModel):
    """Eine Datenkante des Tools, gepruft gegen den Prozessrahmen (A.4.6).

    Traegt den Namen des Datenobjekts mit, damit die Oberflaeche die Liste
    ohne zweite Abfrage anzeigen kann — und die Kategorie, weil sie die
    Zweckbindung entscheidet.
    """

    datenobjekt_id: uuid.UUID
    name: str
    kategorie: Datenkategorie | None = None
    zugriffsart: Zugriffsart
    im_prozessrahmen: bool = False
    kategorie_gedeckt: bool = False


class WirkungProzess(BaseModel):
    """Ein Prozessobjekt, das die Kategorie dieses Datenobjekts traegt."""

    id: uuid.UUID
    name: str
    tier: int | None = None
    mitbestimmung_flag: bool = False
    mitbestimmung_flag_neu: bool = False
    als_input: bool = False
    als_output: bool = False


class WirkungTool(BaseModel):
    id: uuid.UUID
    name: str
    zugriffsart: Zugriffsart | None = None
    ueber_prozess: bool = False


class WirkungAus(BaseModel):
    """Was eine Umklassifizierung beruehrt (Leitdokument A.4.5, A.4.7).

    Die Frage „was passiert, wenn Datenobjekt D hoeher eingestuft wird" soll
    eine Abfrage sein und keine Studie. Ausgewiesen wird, was heute
    berechenbar ist: die referenzierenden Prozesse samt kuenftigem
    Mitbestimmungsflag und die betroffenen Tool-Objekte.
    """

    kategorie_alt: Datenkategorie | None = None
    kategorie_neu: Datenkategorie | None = None
    prozesse: list[WirkungProzess] = Field(default_factory=list)
    tools: list[WirkungTool] = Field(default_factory=list)
    mitbestimmung_neu: int = 0
