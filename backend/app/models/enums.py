"""Fachliche Aufzaehlungen aus dem Leitdokument und der Architektur."""

from __future__ import annotations

from enum import StrEnum


class Ebene(StrEnum):
    INT = "INT"
    LAND = "LAND"


class ProzessStatus(StrEnum):
    ENTWURF = "entwurf"
    AKTIV = "aktiv"
    STILLGELEGT = "stillgelegt"


class Rolle(StrEnum):
    PROZESS_OWNER = "prozess_owner"
    PROZESS_UMSETZER = "prozess_umsetzer"
    TECHNISCHER_OWNER = "technischer_owner"
    DATENOBJEKT_OWNER = "datenobjekt_owner"
    GOVERNANCE = "governance"
    PLATTFORM = "plattform"
    AUDITOR = "auditor"
    APP_ADMINISTRATOR = "app_administrator"


class ScopeTyp(StrEnum):
    GLOBAL = "global"
    FACHBEREICH = "fachbereich"
    ORGANISATIONSEINHEIT = "organisationseinheit"


class Herkunft(StrEnum):
    IMPORTIERT = "importiert"
    MANUELL = "manuell"


class ImportTyp(StrEnum):
    TEAM = "team"
    TOOL = "tool"
    DATENOBJEKT = "datenobjekt"
    FACHBEREICH = "fachbereich"
    ORGANISATIONSEINHEIT = "organisationseinheit"


class AssetStatus(StrEnum):
    IMPORTIERT_UNBESTAETIGT = "importiert_unbestaetigt"
    BESTAETIGT = "bestaetigt"
    INAKTIV = "inaktiv"


class GateTyp(StrEnum):
    GATE_1 = "1"
    GATE_2 = "2"


class GateStatus(StrEnum):
    EINGEREICHT = "eingereicht"
    IN_PRUEFUNG = "in_pruefung"
    FREIGEGEBEN = "freigegeben"
    ABGELEHNT = "abgelehnt"


class Gate2Ausloeser(StrEnum):
    """Abschliessende Liste aus Leitdokument A.11 — kein sechster, freier Grund."""

    NEUE_DATENKATEGORIE = "neue_datenkategorie"
    REICHWEITENERWEITERUNG = "reichweitenerweiterung"
    NEUES_EXTERNES_ZIEL = "neues_externes_ziel"
    KI_KOMPONENTE_ERGAENZT = "ki_komponente_ergaenzt"
    KRITIKALITAET_GESTIEGEN = "kritikalitaet_gestiegen"


class SelbstverpflichtungTyp(StrEnum):
    PROZESSEIGNER = "prozesseigner"
    TECHNISCHER_OWNER = "technischer_owner"


class ComplianceFarbe(StrEnum):
    GRUEN = "gruen"
    GELB = "gelb"
    ROT = "rot"


class LenkungStatus(StrEnum):
    OFFEN = "offen"
    AUFGELOEST = "aufgeloest"
    ABGEBROCHEN = "abgebrochen"


class Aufloesungsart(StrEnum):
    """Die drei zulaessigen Aufloesungen aus Leitdokument A.13.6."""

    ANPASSEN = "anpassen"
    RAHMEN_ERWEITERN = "rahmen_erweitern"
    STILLLEGEN = "stilllegen"


class ChangeAktion(StrEnum):
    ERSTELLT = "erstellt"
    GEAENDERT = "geaendert"
    GELOESCHT = "geloescht"


class Zugriffsart(StrEnum):
    LESEN = "lesen"
    SCHREIBEN = "schreiben"
    LESEN_SCHREIBEN = "lesen_schreiben"


class AlarmTyp(StrEnum):
    KI_VERBOTSTATBESTAND = "ki_verbotstatbestand"


class Reichweite(StrEnum):
    """Abgeleitet, nie eingegeben (Leitdokument P1)."""

    PERSOENLICH = "persoenlich"
    TEAM = "team"
    BEREICH = "bereich"
    UNTERNEHMEN = "unternehmen"
    EXTERN = "extern"


class Kundenkreis(StrEnum):
    """SIPOC-Feld ``customer`` als kontrollierte Liste.

    Das Leitdokument leitet die Reichweite aus dem Kundenkreis ab. Eine
    Ableitung aus Freitext waere nicht bestimmbar und damit nicht pruefbar —
    deshalb ist dieses eine SIPOC-Feld eine Auswahl, keine freie Eingabe.
    """

    PERSOENLICH = "persoenlich"
    TEAM = "team"
    BEREICH = "bereich"
    UNTERNEHMEN = "unternehmen"
    EXTERN = "extern"


class Ausfallfolge(StrEnum):
    """Gestufte Folge eines Prozessausfalls — Basis der Kritikalitaet."""

    KEINE = "keine"
    GERING = "gering"
    SPUERBAR = "spuerbar"
    KRITISCH = "kritisch"


class Datenkategorie(StrEnum):
    """Kategorie eines Datenobjekts (Leitdokument A.7)."""

    OEFFENTLICH = "oeffentlich"
    INTERN = "intern"
    VERTRAULICH = "vertraulich"
    PERSONENBEZOGEN = "personenbezogen"
    MITARBEITERBEZOGEN = "mitarbeiterbezogen"
    BESONDERE_KATEGORIE = "besondere_kategorie"


#: Ordnungen fuer die Maximum-Vererbung (Leitdokument A.4.4).
REICHWEITE_ORDNUNG: dict[str, int] = {
    Reichweite.PERSOENLICH: 0,
    Reichweite.TEAM: 1,
    Reichweite.BEREICH: 2,
    Reichweite.UNTERNEHMEN: 3,
    Reichweite.EXTERN: 4,
}

KUNDENKREIS_ZU_REICHWEITE: dict[str, Reichweite] = {
    Kundenkreis.PERSOENLICH: Reichweite.PERSOENLICH,
    Kundenkreis.TEAM: Reichweite.TEAM,
    Kundenkreis.BEREICH: Reichweite.BEREICH,
    Kundenkreis.UNTERNEHMEN: Reichweite.UNTERNEHMEN,
    Kundenkreis.EXTERN: Reichweite.EXTERN,
}

AUSFALLFOLGE_STUFE: dict[str, int] = {
    Ausfallfolge.KEINE: 0,
    Ausfallfolge.GERING: 1,
    Ausfallfolge.SPUERBAR: 2,
    Ausfallfolge.KRITISCH: 3,
}

#: Datenkategorien, die die Mitbestimmung beruehren (Leitdokument A.8).
MITBESTIMMUNGSRELEVANTE_KATEGORIEN: frozenset[str] = frozenset({Datenkategorie.MITARBEITERBEZOGEN})
