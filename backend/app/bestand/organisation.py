"""Aufbauschritt 1: Organisation, Menschen und Rollen.

Die Grobgliederung kommt in dieser Anwendung **nie** von Hand, sondern aus der
zentralen Entwicklungsplattform (P-App-4). Der Aufbau geht denselben Weg: der
Sync-Lauf legt Fachbereiche, Organisationseinheiten und Teams an, betrieben von
der Plattform-Rolle. Nur der erste Administrator entsteht davor — ohne ihn
koennte niemand die erste Rolle vergeben.
"""

from __future__ import annotations

import unicodedata

from sqlalchemy import select

from app.bestand.kontext import Kontext, Unstimmig
from app.models.enums import Ebene, ImportTyp, Rolle, ScopeTyp
from app.models.organisation import Fachbereich, Rollenzuweisung, User
from app.schemas.integration import ImportAnfrage, ImportDatensatz
from app.services import verwaltung
from app.services.changelog import protokolliere_erstellung
from app.sync.importer import importiere

#: Die Quelle, aus der die Stammdaten stammen — dieselbe wie im Beispielexport.
QUELLE = "zentrale-entwicklungsplattform"

#: Die Maildomaene der Gruppe.
DOMAENE = "handelsgruppe.de"

#: Fachbereich: Schluessel, Code, Name, Laender mit eigener Gesellschaft.
#:
#: Nicht jeder Fachbereich ist in jedem Land eigenstaendig aufgestellt — der
#: Einkauf Nonfood steuert von zwei Standorten aus, der Vertrieb sitzt in jedem
#: Land. Genau diese Ungleichverteilung macht den Bereichsfilter im Cockpit
#: aussagekraeftig.
FACHBEREICHE: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("einkauf-food", "fb-einkauf-food", "Einkauf Food", ("DE", "PL", "CZ", "RO")),
    ("einkauf-nonfood", "fb-einkauf-nonfood", "Einkauf Nonfood", ("DE", "PL")),
    (
        "vertrieb",
        "fb-vertrieb",
        "Vertrieb und Filialbetrieb",
        ("DE", "PL", "CZ", "RO", "IT", "ES", "HR"),
    ),
    ("logistik", "fb-logistik", "Logistik und Supply Chain", ("DE", "PL", "CZ", "RO")),
    ("personal", "fb-personal", "Personal", ("DE", "PL", "CZ")),
    ("finanzen", "fb-finanzen", "Finanzen und Controlling", ("DE", "PL", "IT")),
    ("expansion", "fb-expansion", "Expansion und Immobilien", ("DE", "PL", "RO")),
    ("marketing", "fb-marketing", "Marketing und Kundenbindung", ("DE", "CZ")),
    ("qs", "fb-qs", "Qualitätssicherung", ("DE", "PL")),
    ("it", "fb-it", "IT und Digitalisierung", ("DE",)),
)

#: Team, Organisationseinheit, Ansprechpartner — importierte Stammdaten.
TEAMS: tuple[tuple[str, str, str], ...] = (
    ("Category Management Molkerei", "einkauf-food-de", "cm.molkerei"),
    ("Category Management Obst und Gemüse", "einkauf-food", "cm.obst"),
    ("Aktionssteuerung Food", "einkauf-food", "aktionssteuerung"),
    ("Category Management Haushaltswaren", "einkauf-nonfood", "cm.haushalt"),
    ("Filialsteuerung Region Nord", "vertrieb-de", "filialsteuerung.nord"),
    ("Filialsteuerung Region Süd", "vertrieb-de", "filialsteuerung.sued"),
    ("Kassenprozesse", "vertrieb", "kassenprozesse"),
    ("Lagersteuerung Zentrallager", "logistik-de", "lagersteuerung"),
    ("Transportdisposition", "logistik", "transportdisposition"),
    ("Personalplanung Filiale", "personal-de", "personalplanung"),
    ("Entgeltabrechnung", "personal", "entgeltabrechnung"),
    ("Konzernrechnungswesen", "finanzen", "rechnungswesen"),
    ("Vertriebscontrolling", "finanzen-de", "vertriebscontrolling"),
    ("Standortentwicklung", "expansion", "standortentwicklung"),
    ("Kundenbindung und Kundenkarte", "marketing", "kundenbindung"),
    ("Eigenmarkenqualität", "qs", "eigenmarkenqualitaet"),
    ("Warenwirtschaft Betrieb", "it-de", "warenwirtschaft"),
)


class Person:
    """Ein Mensch in der Gruppe, mit Vorgesetztem und Rollen.

    Die Rollen stehen als ``rolle@bereich``: ``global``, ``fb:<Fachbereich>``
    oder ``oe:<Organisationseinheit>``. Rolle und Bereich sind orthogonal
    (P-App-3) — die Schreibweise haelt das sichtbar.
    """

    __slots__ = ("schluessel", "name", "funktion", "fuehrungskraft", "rollen", "aktiv")

    def __init__(
        self,
        schluessel: str,
        name: str,
        funktion: str,
        fuehrungskraft: str | None,
        *rollen: str,
        aktiv: bool = True,
    ) -> None:
        self.schluessel = schluessel
        self.name = name
        self.funktion = funktion
        self.fuehrungskraft = fuehrungskraft
        self.rollen = rollen
        self.aktiv = aktiv


#: Der erste Administrator. Er entsteht vor allen anderen und ohne fremdes
#: Zutun — genau wie im Betrieb ueber ``GP_BOOTSTRAP_ADMIN_SUBJECTS``.
ERSTZUGANG = "petersen"

#: Zugaenge fuer die Vorfuehrung — je Rolle einer, dazu die beiden Faelle, an
#: denen sich der Unterschied zeigt: derselbe Rollenname mit zwei
#: Geltungsbereichen, und ein Zugang ganz ohne Rolle.
#:
#: Sie tragen **keinen erfundenen Personennamen**, sondern die Bezeichnung
#: ihrer Zugangsart — ein Konto namens „governance" sagt, wofuer es da ist.
#: Kennung und Name sind dasselbe eine Wort: die Anmeldemaske verlangt beides,
#: und vor Publikum soll das in zwei Sekunden getippt sein. Weil beide Felder
#: denselben Wert tragen, bleibt der Datensatz beim Anmelden unveraendert.
#:
#: Sonderrechte haben sie keine — dieselben Rollen wie alle anderen. Was jeder
#: von ihnen sieht und darf, steht in ``docs/demo-zugaenge.md``.
DEMOZUGAENGE: tuple[Person, ...] = (
    Person("governance", "governance", "Governance, unternehmensweit", None, "governance@global"),
    Person(
        "auditor",
        "auditor",
        "Auditor, unternehmensweit, ausschliesslich lesend",
        None,
        "auditor@global",
    ),
    Person(
        "plattform", "plattform", "Plattformbetrieb, unternehmensweit", None, "plattform@global"
    ),
    Person(
        "administrator",
        "administrator",
        "App-Administrator, unternehmensweit",
        None,
        "app_administrator@global",
    ),
    # Alle fuenf bereichsgebundenen Zugaenge liegen im **selben** Fachbereich,
    # der Logistik. Das ist Absicht: verteilt man sie ueber verschiedene
    # Bereiche, sieht jeder etwas anderes und man kann nicht unterscheiden, ob
    # der Unterschied von der Rolle oder vom Bereich kommt. Nebeneinander im
    # selben Bereich zeigen sie beide Haelften der Regel (P-App-3):
    #
    #   prozessowner  gegen  bereichsowner     dieselbe Rolle, engerer Bereich
    #   prozessowner  gegen  toolowner/datenowner  gleicher Bereich, andere Rolle
    #
    # Die zweite Zeile ist die, die am leichtesten vergessen wird — sie war bis
    # E-57 auch falsch umgesetzt (R-7).
    Person(
        "prozessowner",
        "prozessowner",
        "Prozess-Owner, Fachbereich Logistik",
        None,
        "prozess_owner@fb:logistik",
    ),
    Person(
        "bereichsowner",
        "bereichsowner",
        "Prozess-Owner, nur Landesgesellschaft Logistik DE",
        None,
        "prozess_owner@oe:logistik-de",
    ),
    Person(
        "prozessumsetzer",
        "prozessumsetzer",
        "Prozess-Umsetzer, Landesgesellschaft Logistik DE",
        None,
        "prozess_umsetzer@oe:logistik-de",
    ),
    Person(
        "toolowner",
        "toolowner",
        "Technischer Owner, Fachbereich Logistik",
        None,
        "technischer_owner@fb:logistik",
    ),
    Person(
        "datenowner",
        "datenowner",
        "Datenobjekt-Owner, Fachbereich Logistik",
        None,
        "datenobjekt_owner@fb:logistik",
    ),
    # Das Gegenueber: dieselbe Rolle wie `prozessowner`, anderer Fachbereich.
    # Ohne ihn liesse sich nur zeigen, dass ein engerer Bereich weniger sieht —
    # nicht, dass eine Rolle allein ueberhaupt nichts traegt.
    Person(
        "fremdowner",
        "fremdowner",
        "Prozess-Owner, Fachbereich Personal",
        None,
        "prozess_owner@fb:personal",
    ),
    # Angemeldet, aber ohne Rolle: der Fall, in dem die Anwendung nichts zeigt
    # und nichts anbietet.
    Person("ohnerolle", "ohnerolle", "Angemeldet, ohne jede Rollenzuweisung", None),
)

PERSONEN: tuple[Person, ...] = (
    # --- Konzernfunktionen -------------------------------------------------
    Person(
        "petersen", "Jörg Petersen", "Leiter Anwendungsbetrieb", None, "app_administrator@global"
    ),
    Person(
        "rehm", "Claudia Rehm", "Anwendungsadministration", "petersen", "app_administrator@global"
    ),
    Person(
        "wilms", "Andrea Wilms", "Leiterin Governance und Compliance", None, "governance@global"
    ),
    Person("renner", "Tobias Renner", "Referent Governance", "wilms", "governance@global"),
    Person("stadler", "Miriam Stadler", "Konzerndatenschutz", "wilms", "governance@global"),
    Person("boehm", "Katrin Böhm", "Leiterin Konzernrevision", None, "auditor@global"),
    Person("feldmann", "Uwe Feldmann", "Konzernrevision", "boehm", "auditor@global"),
    Person(
        "lauterbach", "Sven Lauterbach", "Leiter Entwicklungsplattform", None, "plattform@global"
    ),
    Person("kellermann", "Nina Kellermann", "Plattformbetrieb", "lauterbach", "plattform@global"),
    # --- Einkauf Food ------------------------------------------------------
    Person(
        "brandes",
        "Michael Brandes",
        "Bereichsleiter Einkauf Food",
        None,
        "prozess_owner@fb:einkauf-food",
    ),
    Person(
        "kuepper",
        "Sabine Küpper",
        "Einkaufsleitung Molkerei",
        "brandes",
        "prozess_owner@fb:einkauf-food",
    ),
    Person(
        "oswald",
        "Daniel Oswald",
        "Fachanwendungen Einkauf",
        "brandes",
        "technischer_owner@fb:einkauf-food",
    ),
    Person(
        "thelen",
        "Anja Thelen",
        "Stammdaten Einkauf",
        "brandes",
        "datenobjekt_owner@fb:einkauf-food",
    ),
    Person(
        "wozniak",
        "Marek Woźniak",
        "Einkauf Polen",
        "brandes",
        "prozess_umsetzer@oe:einkauf-food-pl",
    ),
    Person(
        "novotny",
        "Petr Novotný",
        "Einkauf Tschechien",
        "brandes",
        "prozess_umsetzer@oe:einkauf-food-cz",
    ),
    Person(
        "radu",
        "Ioana Radu",
        "Einkauf Rumänien",
        "brandes",
        "technischer_owner@oe:einkauf-food-ro",
        "prozess_umsetzer@oe:einkauf-food-ro",
    ),
    # --- Einkauf Nonfood ---------------------------------------------------
    Person(
        "gruber",
        "Stefan Gruber",
        "Bereichsleiter Einkauf Nonfood",
        None,
        "prozess_owner@fb:einkauf-nonfood",
    ),
    Person(
        "ehlers",
        "Britta Ehlers",
        "Einkaufsleitung Haushalt",
        "gruber",
        "prozess_owner@fb:einkauf-nonfood",
    ),
    Person(
        "vogler",
        "Tim Vogler",
        "Fachanwendungen Nonfood",
        "gruber",
        "technischer_owner@fb:einkauf-nonfood",
    ),
    Person(
        "kaminska",
        "Agnieszka Kamińska",
        "Einkauf Nonfood Polen",
        "gruber",
        "prozess_umsetzer@oe:einkauf-nonfood-pl",
    ),
    Person(
        "ritter",
        "Holger Ritter",
        "Stammdaten Nonfood",
        "gruber",
        "datenobjekt_owner@fb:einkauf-nonfood",
    ),
    # --- Vertrieb und Filialbetrieb ---------------------------------------
    Person(
        "hofmann",
        "Christine Hofmann",
        "Bereichsleiterin Vertrieb",
        None,
        "prozess_owner@fb:vertrieb",
    ),
    Person(
        "baumgart",
        "Rolf Baumgart",
        "Leitung Filialprozesse",
        "hofmann",
        "prozess_owner@fb:vertrieb",
    ),
    Person(
        "seidel",
        "Markus Seidel",
        "Fachanwendungen Filiale",
        "hofmann",
        "technischer_owner@fb:vertrieb",
    ),
    Person(
        "lenz", "Julia Lenz", "Fachanwendungen Kasse", "hofmann", "technischer_owner@fb:vertrieb"
    ),
    Person(
        "dvorak", "Jan Dvořák", "Vertrieb Tschechien", "hofmann", "prozess_umsetzer@oe:vertrieb-cz"
    ),
    Person(
        "ferrari", "Luca Ferrari", "Vertrieb Italien", "hofmann", "prozess_umsetzer@oe:vertrieb-it"
    ),
    Person(
        "moreno", "Elena Moreno", "Vertrieb Spanien", "hofmann", "prozess_umsetzer@oe:vertrieb-es"
    ),
    Person(
        "kovac", "Ivan Kovač", "Vertrieb Kroatien", "hofmann", "prozess_umsetzer@oe:vertrieb-hr"
    ),
    Person(
        "teichmann",
        "Sandra Teichmann",
        "Stammdaten Vertrieb",
        "hofmann",
        "datenobjekt_owner@fb:vertrieb",
    ),
    # Ausgeschieden: ihre Prozessobjekte tragen sie noch als Owner. Genau das
    # findet die Cockpit-Zeile „Prozesse ohne tragenden Owner".
    Person(
        "kortmann",
        "Ursula Kortmann",
        "Filialprozesse (ausgeschieden)",
        "hofmann",
        "prozess_owner@fb:vertrieb",
        aktiv=False,
    ),
    # Uebernahme ohne Rollenvergabe — derselbe Befund, anderer Grund.
    Person("deffner", "Martin Deffner", "Filialprozesse", "hofmann"),
    # --- Logistik ----------------------------------------------------------
    Person(
        "schaefer", "Bernd Schäfer", "Bereichsleiter Logistik", None, "prozess_owner@fb:logistik"
    ),
    Person(
        "arnold",
        "Katja Arnold",
        "Leitung Transportsteuerung",
        "schaefer",
        "prozess_owner@fb:logistik",
    ),
    Person(
        "pohl",
        "Andreas Pohl",
        "Fachanwendungen Logistik",
        "schaefer",
        "technischer_owner@fb:logistik",
    ),
    Person(
        "wieczorek",
        "Tomasz Wieczorek",
        "Lagersteuerung Polen",
        "schaefer",
        "technischer_owner@oe:logistik-pl",
    ),
    Person(
        "burkhardt",
        "Simone Burkhardt",
        "Stammdaten Logistik",
        "schaefer",
        "datenobjekt_owner@fb:logistik",
    ),
    Person(
        "eckert",
        "Frank Eckert",
        "Zentrallager Deutschland",
        "schaefer",
        "prozess_umsetzer@oe:logistik-de",
    ),
    # --- Personal ----------------------------------------------------------
    Person(
        "niemeyer",
        "Gabriele Niemeyer",
        "Bereichsleiterin Personal",
        None,
        "prozess_owner@fb:personal",
    ),
    Person(
        "reinhardt",
        "Patrick Reinhardt",
        "Leitung Personalsteuerung",
        "niemeyer",
        "prozess_owner@fb:personal",
    ),
    Person(
        "albrecht",
        "Sonja Albrecht",
        "Fachanwendungen Personal",
        "niemeyer",
        "technischer_owner@fb:personal",
    ),
    Person(
        "kraus",
        "Dennis Kraus",
        "Fachanwendungen Entgelt",
        "niemeyer",
        "technischer_owner@fb:personal",
    ),
    Person(
        "sikora", "Barbara Sikora", "Personal Polen", "niemeyer", "prozess_umsetzer@oe:personal-pl"
    ),
    Person(
        "weidner",
        "Martina Weidner",
        "Stammdaten Personal",
        "niemeyer",
        "datenobjekt_owner@fb:personal",
    ),
    # --- Finanzen und Controlling -----------------------------------------
    Person("koehler", "Ralf Köhler", "Bereichsleiter Finanzen", None, "prozess_owner@fb:finanzen"),
    Person(
        "baier",
        "Yvonne Baier",
        "Leitung Vertriebscontrolling",
        "koehler",
        "prozess_owner@fb:finanzen",
    ),
    Person(
        "steiner",
        "Marco Steiner",
        "Fachanwendungen Finanzen",
        "koehler",
        "technischer_owner@fb:finanzen",
    ),
    Person(
        "winkler",
        "Thomas Winkler",
        "Fachanwendungen Controlling",
        "koehler",
        "technischer_owner@fb:finanzen",
    ),
    Person(
        "gutmann",
        "Petra Gutmann",
        "Stammdaten Finanzen",
        "koehler",
        "datenobjekt_owner@fb:finanzen",
    ),
    Person(
        "conti", "Giulia Conti", "Controlling Italien", "koehler", "prozess_umsetzer@oe:finanzen-it"
    ),
    # --- Expansion und Immobilien -----------------------------------------
    Person("haas", "Norbert Haas", "Bereichsleiter Expansion", None, "prozess_owner@fb:expansion"),
    Person(
        "fricke",
        "Isabel Fricke",
        "Leitung Standortentwicklung",
        "haas",
        "prozess_owner@fb:expansion",
    ),
    Person(
        "meixner",
        "Jan Meixner",
        "Fachanwendungen Expansion",
        "haas",
        "technischer_owner@fb:expansion",
    ),
    Person(
        "popescu",
        "Andrei Popescu",
        "Expansion Rumänien",
        "haas",
        "prozess_umsetzer@oe:expansion-ro",
    ),
    Person(
        "lorenz", "Heike Lorenz", "Stammdaten Immobilien", "haas", "datenobjekt_owner@fb:expansion"
    ),
    # --- Marketing und Kundenbindung --------------------------------------
    Person(
        "bergmann",
        "Nicole Bergmann",
        "Bereichsleiterin Marketing",
        None,
        "prozess_owner@fb:marketing",
    ),
    Person(
        "roth", "Sebastian Roth", "Leitung Kundenbindung", "bergmann", "prozess_owner@fb:marketing"
    ),
    Person(
        "kilian",
        "Robert Kilian",
        "Fachanwendungen Marketing",
        "bergmann",
        "technischer_owner@fb:marketing",
    ),
    Person(
        "svobodova",
        "Lucie Svobodová",
        "Marketing Tschechien",
        "bergmann",
        "prozess_umsetzer@oe:marketing-cz",
    ),
    Person(
        "haenel", "Corinna Hänel", "Stammdaten Kunde", "bergmann", "datenobjekt_owner@fb:marketing"
    ),
    # --- Qualitätssicherung ------------------------------------------------
    Person(
        "ziegler",
        "Doris Ziegler",
        "Bereichsleiterin Qualitätssicherung",
        None,
        "prozess_owner@fb:qs",
    ),
    Person(
        "mertens", "Kai Mertens", "Leitung Eigenmarkenqualität", "ziegler", "prozess_owner@fb:qs"
    ),
    Person(
        "straub", "Elke Straub", "Fachanwendungen Qualität", "ziegler", "technischer_owner@fb:qs"
    ),
    Person(
        "adamczyk",
        "Piotr Adamczyk",
        "Qualitätssicherung Polen",
        "ziegler",
        "prozess_umsetzer@oe:qs-pl",
    ),
    Person("wendt", "Georg Wendt", "Stammdaten Qualität", "ziegler", "datenobjekt_owner@fb:qs"),
    # --- IT und Digitalisierung -------------------------------------------
    Person(
        "neubauer",
        "Alexander Neubauer",
        "Bereichsleiter IT",
        None,
        "prozess_owner@fb:it",
        "technischer_owner@fb:it",
    ),
    Person(
        "hartwig",
        "Susanne Hartwig",
        "Leitung Warenwirtschaft",
        "neubauer",
        "technischer_owner@fb:it",
    ),
    Person(
        "pieper", "Lars Pieper", "Betrieb Schnittstellen", "neubauer", "technischer_owner@fb:it"
    ),
    Person("baumann", "Kevin Baumann", "Datenplattform", "neubauer", "technischer_owner@fb:it"),
    Person("dietrich", "Verena Dietrich", "Stammdaten IT", "neubauer", "datenobjekt_owner@fb:it"),
    # --- Zugaenge fuer die Vorfuehrung -------------------------------------
    *DEMOZUGAENGE,
)


#: Umlaute werden ersetzt, nicht abgestreift — „koehler" ist die Kennung, die
#: ein deutsches Identitaetssystem vergibt, „kohler" waere ein anderer Name.
#: Alles Uebrige (Häček, Akut, Ogonek) faellt bei der Zerlegung weg.
UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def umsetzer_fuer(einheit: str) -> str | None:
    """Wer die lokale Abweichung dieser Landesgesellschaft pflegen darf.

    Der Prozess-Umsetzer ist die einzige Rolle, die genau eine Sache darf und
    sonst nichts (Matrix 5.3). Damit sie im Bestand ueberhaupt sichtbar wird,
    schreibt hier nicht der Prozess-Owner, sondern der Zustaendige vor Ort.
    """
    gesucht = f"prozess_umsetzer@oe:{einheit}"
    for person in PERSONEN:
        if gesucht in person.rollen:
            return person.schluessel
    return None


def _kennung(name: str) -> str:
    """Vorname.Nachname in der Schreibweise der Unternehmenskennung."""
    ersetzt = name.lower().translate(UMLAUTE)
    zerlegt = unicodedata.normalize("NFKD", ersetzt)
    ohne_zeichen = "".join(z for z in zerlegt if not unicodedata.combining(z))
    return ".".join(teil for teil in ohne_zeichen.split() if teil)


def _lege_person_an(kontext: Kontext, person: Person, akteur_id, beschreibung: str = "") -> User:
    # Die Vorfuehrzugaenge tragen ihre Kennung im Schluessel: sie muss im
    # Vortrag eintippbar sein und darf sich nicht aus dem Namen ergeben.
    kennung = person.schluessel if person in DEMOZUGAENGE else _kennung(person.name)
    fuehrungskraft = (
        None if person.fuehrungskraft is None else kontext.person(person.fuehrungskraft).id
    )
    nutzer = User(
        subject=kennung,
        email=f"{kennung}@{DOMAENE}",
        name=person.name,
        ist_aktiv=True,
        fuehrungskraft_user_id=fuehrungskraft,
    )
    kontext.db.add(nutzer)
    kontext.db.flush()
    protokolliere_erstellung(
        kontext.db, nutzer, akteur_user_id=akteur_id, beschreibung=beschreibung
    )
    return nutzer


def _bereich(kontext: Kontext, angabe: str) -> tuple[ScopeTyp, object]:
    if angabe == "global":
        return ScopeTyp.GLOBAL, None
    art, _, schluessel = angabe.partition(":")
    if art == "fb":
        return ScopeTyp.FACHBEREICH, kontext.fachbereich(schluessel).id
    if art == "oe":
        return ScopeTyp.ORGANISATIONSEINHEIT, kontext.einheit(schluessel).id
    raise Unstimmig(f"Unbekannte Bereichsangabe: {angabe}")


def _importdaten() -> ImportAnfrage:
    """Der Export, den die zentrale Entwicklungsplattform liefern wuerde."""
    datensaetze: list[ImportDatensatz] = []
    for schluessel, code, name, laender in FACHBEREICHE:
        datensaetze.append(
            ImportDatensatz(
                typ=ImportTyp.FACHBEREICH,
                externe_id=f"FB-{schluessel.upper()}",
                name=name,
                metadaten={"code": code},
            )
        )
        datensaetze.append(
            ImportDatensatz(
                typ=ImportTyp.ORGANISATIONSEINHEIT,
                externe_id=f"OE-{schluessel.upper()}-INT",
                name=f"{name} International",
                metadaten={
                    "fachbereich_externe_id": f"FB-{schluessel.upper()}",
                    "ebene": Ebene.INT.value,
                },
            )
        )
        for land in laender:
            datensaetze.append(
                ImportDatensatz(
                    typ=ImportTyp.ORGANISATIONSEINHEIT,
                    externe_id=f"OE-{schluessel.upper()}-{land}",
                    name=f"{name} {land}",
                    metadaten={
                        "fachbereich_externe_id": f"FB-{schluessel.upper()}",
                        "ebene": Ebene.LAND.value,
                        "land_code": land,
                    },
                )
            )
    for name, einheit, postfach in TEAMS:
        teile = einheit.rsplit("-", 1)
        fachbereich = einheit if len(teile) == 1 or len(teile[1]) != 2 else teile[0]
        land = "INT" if fachbereich == einheit else teile[1].upper()
        datensaetze.append(
            ImportDatensatz(
                typ=ImportTyp.TEAM,
                externe_id=f"TEAM-{postfach.upper()}",
                name=name,
                owner_hinweis=f"{postfach}@{DOMAENE}",
                metadaten={"organisationseinheit_externe_id": (f"OE-{fachbereich.upper()}-{land}")},
            )
        )
    return ImportAnfrage(quelle=QUELLE, datensaetze=datensaetze)


def baue(kontext: Kontext) -> None:
    """Legt Erstzugang, Organisation, Teams, Menschen und Rollen an."""
    db = kontext.db

    # Der Erstzugang: entsteht wie im Betrieb aus der ersten Anmeldung, mit den
    # beiden Startrollen. Ohne ihn gaebe es niemanden, der Rollen vergeben darf.
    erster = next(p for p in PERSONEN if p.schluessel == ERSTZUGANG)
    with kontext.aktion(vor_tagen=760):
        nutzer = _lege_person_an(
            kontext,
            erster,
            None,
            "Erstzugang aus der zentralen Unternehmensidentität",
        )
        kontext.personen[erster.schluessel] = nutzer
        for rolle in (Rolle.APP_ADMINISTRATOR, Rolle.GOVERNANCE):
            zuweisung = Rollenzuweisung(user_id=nutzer.id, rolle=rolle, scope_typ=ScopeTyp.GLOBAL)
            db.add(zuweisung)
            db.flush()
            protokolliere_erstellung(
                db,
                zuweisung,
                akteur_user_id=nutzer.id,
                beschreibung="Startrolle des Erstzugangs (GP_BOOTSTRAP_ADMIN_SUBJECTS)",
            )
    admin_id = nutzer.id

    with kontext.aktion(vor_tagen=755):
        ergebnis = importiere(db, _importdaten(), akteur_user_id=admin_id)
    if ergebnis.fehler:
        raise Unstimmig(f"Der Stammdatenimport meldet Fehler: {ergebnis.fehler}")

    for schluessel, _code, _name, laender in FACHBEREICHE:
        fachbereich = _finde_fachbereich(kontext, schluessel)
        kontext.fachbereiche[schluessel] = fachbereich
        for einheit in fachbereich.organisationseinheiten:
            if einheit.ebene == Ebene.INT:
                kontext.einheiten[schluessel] = einheit
            else:
                kontext.einheiten[f"{schluessel}-{(einheit.land_code or '').lower()}"] = einheit
        fehlend = [
            land for land in laender if f"{schluessel}-{land.lower()}" not in kontext.einheiten
        ]
        if fehlend:
            raise Unstimmig(f"Landesgesellschaften fehlen in {schluessel}: {fehlend}")

    # Die uebrigen Menschen legt der App-Administrator an — in dieser Anwendung
    # der einzige Weg, jemandem vor seiner ersten Anmeldung eine Rolle oder eine
    # Fuehrungskraft zu geben.
    with kontext.aktion(vor_tagen=750):
        for person in PERSONEN:
            if person.schluessel == ERSTZUGANG:
                continue
            kontext.personen[person.schluessel] = _lege_person_an(kontext, person, admin_id)

    with kontext.aktion(vor_tagen=748):
        for person in PERSONEN:
            if person.schluessel == ERSTZUGANG:
                continue
            for angabe in person.rollen:
                rolle, _, bereich = angabe.partition("@")
                scope_typ, scope_id = _bereich(kontext, bereich)
                zuweisung = Rollenzuweisung(
                    user_id=kontext.person(person.schluessel).id,
                    rolle=Rolle(rolle),
                    scope_typ=scope_typ,
                    scope_id=scope_id,
                )
                db.add(zuweisung)
                db.flush()
                protokolliere_erstellung(db, zuweisung, akteur_user_id=admin_id)
    kontext.vergiss_rollen()


def deaktiviere_ausgeschiedene(kontext: Kontext) -> None:
    """Setzt die Ausgeschiedenen inaktiv — zum Schluss, nicht zu Beginn.

    Sie haben ihre Prozessobjekte selbst angelegt und bewertet; erst danach
    haben sie das Unternehmen verlassen. Andersherum waere die Historie falsch.
    """
    admin = kontext.wer(ERSTZUGANG)
    for person in PERSONEN:
        if person.aktiv:
            continue
        with kontext.aktion(vor_tagen=40):
            verwaltung.aendere_user(
                kontext.db, admin, kontext.person(person.schluessel), ist_aktiv=False
            )


def _finde_fachbereich(kontext: Kontext, schluessel: str) -> Fachbereich:
    treffer = kontext.db.execute(
        select(Fachbereich).where(Fachbereich.externe_id == f"FB-{schluessel.upper()}")
    ).scalar_one_or_none()
    if treffer is None:
        raise Unstimmig(f"Der Import hat den Fachbereich {schluessel} nicht angelegt")
    return treffer
