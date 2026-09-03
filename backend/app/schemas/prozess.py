"""Vertraege des Prozess-Moduls (Architektur 8.1).

Genau die zehn Felder aus Leitdokument A.5 sind eingebbar. Reichweite,
Kritikalitaet und Mitbestimmungsflag sind abgeleitet und erscheinen nur in der
Ausgabe — sie werden nie entgegengenommen (Leitdokument P1).

Die Laengengrenzen der Freitextfelder sind keine Willkuer, sondern die
strukturelle Bremse gegen Detailtiefe aus A.5: „Keine Freitextfelder ausser den
vorgesehenen; harte Zeichenbegrenzung." Wer mehr braucht, verlinkt einen
weiteren Prozess — die Tiefe liegt im Graphen, nicht im Datensatz.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Ausfallfolge, Kundenkreis, ProzessStatus, Reichweite

#: Harte Zeichenbegrenzungen der Freitextfelder (Leitdokument A.5).
LAENGE_SUPPLIER = 200
LAENGE_SCHRITTE = 1000
LAENGE_OUTPUT = 200

#: Mehr Schritte in der P-Spalte heissen: falsche Flughoehe (Leitdokument A.5).
#: Das ist eine Warnung, keine Ablehnung — die Entscheidung bleibt beim Owner.
HOECHSTZAHL_SCHRITTE = 7


class ProzessBasis(BaseModel):
    # 1
    name: str = Field(min_length=1, max_length=255)
    # 2
    owner_user_id: uuid.UUID
    # 3 — Pflichtfeld, kein Speichern ohne Stellvertretung
    stellvertretung_user_id: uuid.UUID
    # 4
    prozessgeber_org_id: uuid.UUID
    # 5
    supplier: str = Field(default="", max_length=LAENGE_SUPPLIER)
    # 6 — Referenz auf bestehende Datenobjekte, kein Freitext (Leitdokument P5)
    input_datenobjekt_ids: list[uuid.UUID] = Field(default_factory=list)
    # 7
    process_steps: str = Field(default="", max_length=LAENGE_SCHRITTE)
    # 8 — Ergebnis in Worten und, als Schreibkante des SIPOC, als Referenz
    output: str = Field(default="", max_length=LAENGE_OUTPUT)
    output_datenobjekt_ids: list[uuid.UUID] = Field(default_factory=list)
    # 9
    customer: Kundenkreis
    # 10
    ausfallfolge: Ausfallfolge


class ProzessAnlegen(ProzessBasis):
    umsetzung_land_org_ids: list[uuid.UUID] = Field(default_factory=list)
    vorgelagert_ids: list[uuid.UUID] = Field(default_factory=list)
    nachgelagert_ids: list[uuid.UUID] = Field(default_factory=list)
    #: Kein SIPOC-Feld, sondern der erklaerte Rahmen (A.13.2 Schicht 1). Beim
    #: Anlegen loest er kein Gate aus — ein Entwurf hat noch keinen Rahmen, den
    #: er verlassen koennte. Spaeter ergaenzte Ziele schon (A.11).
    erlaubte_externe_ziele: list[str] = Field(default_factory=list)


class ProzessAendern(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    owner_user_id: uuid.UUID | None = None
    stellvertretung_user_id: uuid.UUID | None = None
    prozessgeber_org_id: uuid.UUID | None = None
    supplier: str | None = Field(default=None, max_length=LAENGE_SUPPLIER)
    input_datenobjekt_ids: list[uuid.UUID] | None = None
    process_steps: str | None = Field(default=None, max_length=LAENGE_SCHRITTE)
    output: str | None = Field(default=None, max_length=LAENGE_OUTPUT)
    output_datenobjekt_ids: list[uuid.UUID] | None = None
    customer: Kundenkreis | None = None
    ausfallfolge: Ausfallfolge | None = None
    status: ProzessStatus | None = None
    erlaubte_externe_ziele: list[str] | None = None
    vorgelagert_ids: list[uuid.UUID] | None = None
    nachgelagert_ids: list[uuid.UUID] | None = None


class UmsetzungAnlegen(BaseModel):
    land_org_id: uuid.UUID
    lokale_abweichung: str | None = None


class UmsetzungAendern(BaseModel):
    lokale_abweichung: str | None = None


class UmsetzungAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    prozessobjekt_id: uuid.UUID
    land_org_id: uuid.UUID
    lokale_abweichung: str | None = None


class ProzessrechteAus(BaseModel):
    """Was der Anfragende mit **diesem** Prozessobjekt tun darf.

    Eine Auskunft, keine Sicherung: die Pruefung beim Schreiben laeuft
    unabhaengig weiter (Architektur 10.2). Sie erspart der Oberflaeche, die
    Regeln ein zweites Mal zu kennen — und dem Anwender, eine Eingabe zu
    machen, die er nicht speichern darf.
    """

    bearbeiten: bool = False
    bewerten: bool = False
    selbstverpflichten: bool = False
    gate_einreichen: bool = False
    umsetzung_pflegen: bool = False


class ProzessAus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    owner_user_id: uuid.UUID
    stellvertretung_user_id: uuid.UUID
    prozessgeber_org_id: uuid.UUID
    supplier: str
    process_steps: str
    output: str
    customer: Kundenkreis
    ausfallfolge: Ausfallfolge
    status: ProzessStatus
    erlaubte_externe_ziele: list[str] = Field(default_factory=list)
    erstellt_am: datetime
    geaendert_am: datetime

    # Abgeleitet und schreibgeschuetzt (Architektur 8.1)
    reichweite: Reichweite | None = None
    kritikalitaet: int = 0
    mitbestimmung_flag: bool = False
    #: Zahl der Schritte in der P-Spalte und die Flughoehen-Warnung aus A.5.
    schritt_anzahl: int = 0
    schritte_zu_viele: bool = False

    input_datenobjekt_ids: list[uuid.UUID] = Field(default_factory=list)
    output_datenobjekt_ids: list[uuid.UUID] = Field(default_factory=list)
    vorgelagert_ids: list[uuid.UUID] = Field(default_factory=list)
    nachgelagert_ids: list[uuid.UUID] = Field(default_factory=list)
    umsetzungen: list[UmsetzungAus] = Field(default_factory=list)
    tool_objekt_ids: list[uuid.UUID] = Field(default_factory=list)

    # Stand der neuesten Bewertung — abgeleitet, nur zur Anzeige (Phase 2).
    tier: int | None = None
    ausgeloeste_k_klassen: list[str] = Field(default_factory=list)
    bewertung_gueltig_bis: datetime | None = None

    rechte: ProzessrechteAus = Field(default_factory=ProzessrechteAus)
