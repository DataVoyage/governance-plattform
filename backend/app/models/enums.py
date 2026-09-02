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


class Lauftyp(StrEnum):
    """Wie ein Tool angestossen wird (Leitdokument A.6).

    Ausdruecklich **keine** eigene Tier-Achse: die Ausfuehrungsart steuert
    technische Entscheidungen und wirkt in der Bewertung hoechstens als
    Korrekturfaktor bei Grenzfaellen.
    """

    INTERAKTIV = "interaktiv"
    GETRIGGERT = "getriggert"
    GEPLANT = "geplant"


class Wirkungsart(StrEnum):
    """Die Triage aus Leitdokument A.6: veraendert das Tool oder gestaltet es?"""

    VERAENDERND = "veraendernd"
    GESTALTEND = "gestaltend"


class Ausfuehrungsidentitaet(StrEnum):
    """Unter welcher Identitaet ein Tool laeuft (Leitdokument A.13.2 Schicht 1).

    ``geteiltes_konto`` ist kein zulaessiger Rahmenwert, sondern der erklaerte
    Verstoss: A.13.2 Schicht 2 verbietet die umgangene Unternehmensidentitaet
    organisationsweit. Der Wert steht trotzdem hier, weil er erfassbar sein
    muss — was nicht erfasst werden kann, kann auch nicht gefunden werden.
    """

    PERSOENLICH = "persoenlich"
    BENANNTER_DIENST = "benannter_dienst"
    GETEILTES_KONTO = "geteiltes_konto"


class Klassenbewertung(StrEnum):
    """Wie eine Technologie eine Anforderungsklasse abdeckt (Leitdokument A.9.3).

    A.9.3 macht daraus einen Entscheidungsschritt: ein ``nicht_erfuellbar`` bei
    einer ausgeloesten Klasse ist ein Ausschlusskriterium, ein
    ``kompensierbar`` verlangt eine dokumentierte Massnahme. ``erfuellt``
    heisst: die Technologie traegt die Klasse ohne Zusatz.
    """

    ERFUELLT = "erfuellt"
    KOMPENSIERBAR = "kompensierbar"
    NICHT_ERFUELLBAR = "nicht_erfuellbar"


class Befundart(StrEnum):
    """Was der Abgleich Klasse gegen Technologie ergeben hat.

    ``ungeprueft`` ist eine eigene Art und kein stiller Erfolg: eine Klasse
    ohne Matrixeintrag ist nicht abgedeckt, sondern unbeantwortet.
    """

    ERFUELLT = "erfuellt"
    KOMPENSIERT = "kompensiert"
    KOMPENSATION_FEHLT = "kompensation_fehlt"
    AUSSCHLUSS = "ausschluss"
    UNGEPRUEFT = "ungeprueft"


class Schicht2Verbot(StrEnum):
    """Die sechs organisationsweiten Verbote aus Leitdokument A.13.2 Schicht 2.

    Abschliessend wie die Gate-2-Ausloeser und aus demselben Grund: eine Liste,
    die um einen freien Grund ergaenzt werden kann, ist keine Liste mehr. Diese
    Verbote sind durch keine Prozessbewertung freischaltbar — deshalb faellt bei
    ihrer Verletzung die erste Eskalationsstufe weg (A.13.5).
    """

    IDENTITAET_UMGANGEN = "identitaet_umgangen"
    STATISCHE_ZUGANGSDATEN = "statische_zugangsdaten"
    UNDEKLARIERTE_QUELLEN = "undeklarierte_quellen"
    ENTSCHEIDUNG_OHNE_MENSCH = "entscheidung_ohne_mensch"
    DATEN_INS_OFFENE_NETZ = "daten_ins_offene_netz"
    PROTOKOLLIERUNG_UMGANGEN = "protokollierung_umgangen"


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
    """Kategorie eines Datenobjekts — genau die fuenf aus Leitdokument A.7.

    Eine sechste Kategorie „mitarbeiterbezogen" gab es hier zwischenzeitlich;
    sie ist entfallen. A.7 schliesst sie ausdruecklich aus: „Mitbestimmungs-
    relevanz ist keine Kategorie, sondern ein abgeleitetes Flag. Sie kann bei
    jeder Datenkategorie auftreten, weil sie am Verwendungszweck haengt, nicht
    an der Datenart." Siehe ``docs/entscheidungen.md``, E-19.
    """

    OEFFENTLICH = "oeffentlich"
    INTERN = "intern"
    VERTRAULICH = "vertraulich"
    PERSONENBEZOGEN = "personenbezogen"
    BESONDERE_KATEGORIE = "besondere_kategorie"


#: Aufsteigende Schutzbeduerftigkeit der fuenf Kategorien aus A.7. Traegt die
#: „Obergrenze der Datenkategorie" im Erlaubnisrahmen (A.13.2 Schicht 1): der
#: Rahmen deckt alles bis zu dieser Stufe ab, nichts darueber.
DATENKATEGORIE_ORDNUNG: dict[str, int] = {
    Datenkategorie.OEFFENTLICH: 0,
    Datenkategorie.INTERN: 1,
    Datenkategorie.VERTRAULICH: 2,
    Datenkategorie.PERSONENBEZOGEN: 3,
    Datenkategorie.BESONDERE_KATEGORIE: 4,
}

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

#: Kategorien mit Personenbezug (Leitdokument A.7, Stufen 4 und 5).
PERSONENBEZOGENE_KATEGORIEN: frozenset[str] = frozenset(
    {Datenkategorie.PERSONENBEZOGEN, Datenkategorie.BESONDERE_KATEGORIE}
)

#: Kategorie, die Leistungs- und Verhaltensdaten einschliesst — A.7 nennt in
#: der besonderen Kategorie ausdruecklich Entgelt, Gesundheit und
#: Leistungsbewertung.
LEISTUNGSDATEN_KATEGORIEN: frozenset[str] = frozenset({Datenkategorie.BESONDERE_KATEGORIE})

#: Ab dieser Stufe ist ein Ergebnis einzelnen Beschaeftigten zurechenbar
#: (Leitdokument A.8.3, Dimension MB).
MB_STUFE_ZURECHENBAR = 2

#: Zugriffsarten, die den Prozessausgang direkt veraendern koennen
#: (Leitdokument A.6, Signaltabelle „veraendert vs. gestaltet").
SCHREIBENDE_ZUGRIFFSARTEN: frozenset[str] = frozenset(
    {Zugriffsart.SCHREIBEN, Zugriffsart.LESEN_SCHREIBEN}
)
