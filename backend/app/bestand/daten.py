"""Aufbauschritt 2: die Datenobjekte der Gruppe.

Ein Datenobjekt wird einmal eingeordnet und von vielen Prozessen und Werkzeugen
referenziert (Leitdokument A.4.5). Deshalb steht es hier vor allem anderen: die
Kategorie eines Datenobjekts traegt spaeter die halbe Bewertung.

Alle fuenf Kategorien aus A.7 kommen vor, und zwar in dem Verhaeltnis, in dem
sie in einem Handelsunternehmen tatsaechlich auftreten: viel Internes, einiges
Vertrauliche, ein klar umrissener personenbezogener Bestand im Personalwesen
und in der Kundenbindung — und eine Handvoll Objekte ohne Kategorie, weil das
in jedem echten Bestand so ist und weil das Cockpit genau danach fragt.
"""

from __future__ import annotations

from app.bestand.kontext import Kontext
from app.models.enums import Datenkategorie as K
from app.models.enums import ImportTyp
from app.schemas.integration import ImportAnfrage, ImportDatensatz
from app.services import asset
from app.sync.importer import importiere

#: Schluessel, Name, Kategorie, Fachbereich, Datenobjekt-Owner, Quellsystem.
#:
#: ``None`` als Kategorie ist kein Versehen: es sind die Ablagen, die entstanden
#: sind, bevor jemand nach ihrer Einordnung gefragt hat.
DATENOBJEKTE: tuple[tuple[str, str, str | None, str, str, str], ...] = (
    # --- Einkauf Food ------------------------------------------------------
    (
        "artikelstamm-food",
        "Artikelstammdaten Food",
        K.INTERN,
        "einkauf-food",
        "thelen",
        "Warenwirtschaft",
    ),
    (
        "lieferantenstamm",
        "Lieferantenstammdaten",
        K.INTERN,
        "einkauf-food",
        "thelen",
        "Warenwirtschaft",
    ),
    (
        "einkaufskonditionen",
        "Einkaufskonditionen",
        K.VERTRAULICH,
        "einkauf-food",
        "thelen",
        "Konditionssystem",
    ),
    (
        "aktionsplanung-food",
        "Aktionsplanung Food",
        K.VERTRAULICH,
        "einkauf-food",
        "thelen",
        "Aktionsplanung",
    ),
    (
        "eigenmarken-kalkulation",
        "Kalkulation Eigenmarken",
        K.VERTRAULICH,
        "einkauf-food",
        "thelen",
        "Kalkulationssystem",
    ),
    (
        "lieferantenbewertung",
        "Lieferantenbewertung",
        K.VERTRAULICH,
        "einkauf-food",
        "thelen",
        "Einkaufscockpit",
    ),
    (
        "mengenplanung-saison",
        "Mengenplanung Saisonware",
        K.INTERN,
        "einkauf-food",
        "thelen",
        "Absatzplanung",
    ),
    (
        "wettbewerbspreise",
        "Wettbewerbspreise",
        K.OEFFENTLICH,
        "einkauf-food",
        "thelen",
        "Preisbeobachtung",
    ),
    (
        "sortimentsliste",
        "Sortimentsliste",
        K.OEFFENTLICH,
        "einkauf-food",
        "thelen",
        "Warenwirtschaft",
    ),
    (
        "importkontingente",
        "Importkontingente",
        K.INTERN,
        "einkauf-food",
        "thelen",
        "Zollabwicklung",
    ),
    (
        "lieferantenportal-exporte",
        "Exporte aus dem Lieferantenportal",
        None,
        "einkauf-food",
        "thelen",
        "Lieferantenportal",
    ),
    # --- Einkauf Nonfood ---------------------------------------------------
    (
        "artikelstamm-nonfood",
        "Artikelstammdaten Nonfood",
        K.INTERN,
        "einkauf-nonfood",
        "ritter",
        "Warenwirtschaft",
    ),
    (
        "aktionsplanung-nonfood",
        "Aktionsplanung Nonfood",
        K.VERTRAULICH,
        "einkauf-nonfood",
        "ritter",
        "Aktionsplanung",
    ),
    (
        "lieferantenaudits",
        "Lieferantenaudits Nonfood",
        K.VERTRAULICH,
        "einkauf-nonfood",
        "ritter",
        "Auditdatenbank",
    ),
    (
        "gefahrstoffliste",
        "Gefahrstoffliste",
        K.INTERN,
        "einkauf-nonfood",
        "ritter",
        "Gefahrstoffkataster",
    ),
    (
        "retourenquoten",
        "Retourenquoten Nonfood",
        K.INTERN,
        "einkauf-nonfood",
        "ritter",
        "Warenwirtschaft",
    ),
    (
        "kalkulationsablage",
        "Kalkulationsablage Nonfood",
        None,
        "einkauf-nonfood",
        "ritter",
        "Ablage im Team",
    ),
    # --- Vertrieb und Filialbetrieb ---------------------------------------
    ("filialstammdaten", "Filialstammdaten", K.INTERN, "vertrieb", "teichmann", "Warenwirtschaft"),
    (
        "oeffnungszeiten",
        "Öffnungszeiten der Filialen",
        K.OEFFENTLICH,
        "vertrieb",
        "teichmann",
        "Filialverzeichnis",
    ),
    (
        "abverkauf-filiale",
        "Abverkaufsdaten je Filiale",
        K.INTERN,
        "vertrieb",
        "teichmann",
        "Kassensystem",
    ),
    (
        "bestand-filiale",
        "Bestandsdaten Filiale",
        K.INTERN,
        "vertrieb",
        "teichmann",
        "Warenwirtschaft",
    ),
    ("kassenjournal", "Kassenjournale", K.VERTRAULICH, "vertrieb", "teichmann", "Kassensystem"),
    (
        "bondaten",
        "Kassenbondaten mit Kartenbezug",
        K.PERSONENBEZOGEN,
        "vertrieb",
        "teichmann",
        "Kassensystem",
    ),
    (
        "inventurdifferenzen",
        "Inventurdifferenzen",
        K.VERTRAULICH,
        "vertrieb",
        "teichmann",
        "Warenwirtschaft",
    ),
    (
        "abschriften",
        "Abschriften und Verderb",
        K.INTERN,
        "vertrieb",
        "teichmann",
        "Warenwirtschaft",
    ),
    (
        "mhd-restlaufzeiten",
        "MHD-Restlaufzeiten",
        K.INTERN,
        "vertrieb",
        "teichmann",
        "Filial-Scanner",
    ),
    ("regalplanogramme", "Regalplanogramme", K.INTERN, "vertrieb", "teichmann", "Flächenplanung"),
    (
        "videoaufzeichnungen",
        "Videoaufzeichnungen Kassenzone",
        K.PERSONENBEZOGEN,
        "vertrieb",
        "teichmann",
        "Sicherheitstechnik",
    ),
    (
        "schwundstatistik",
        "Schwundstatistik je Filiale",
        K.VERTRAULICH,
        "vertrieb",
        "teichmann",
        "Warenwirtschaft",
    ),
    (
        "filialbesuchsberichte",
        "Filialbesuchsberichte",
        K.INTERN,
        "vertrieb",
        "teichmann",
        "Vertriebsportal",
    ),
    (
        "filialfotos",
        "Fotodokumentation Regalpflege",
        None,
        "vertrieb",
        "teichmann",
        "Ablage im Team",
    ),
    # --- Logistik ----------------------------------------------------------
    ("tourenplanung", "Tourenplanung", K.INTERN, "logistik", "burkhardt", "Transportmanagement"),
    (
        "wareneingangsavise",
        "Wareneingangsavise",
        K.INTERN,
        "logistik",
        "burkhardt",
        "Lagerverwaltung",
    ),
    ("lieferscheine", "Lieferscheine", K.INTERN, "logistik", "burkhardt", "Lagerverwaltung"),
    (
        "bestand-lager",
        "Bestandsdaten Zentrallager",
        K.INTERN,
        "logistik",
        "burkhardt",
        "Lagerverwaltung",
    ),
    ("frachtkosten", "Frachtkosten", K.VERTRAULICH, "logistik", "burkhardt", "Transportmanagement"),
    (
        "retourenmeldungen",
        "Retourenmeldungen",
        K.INTERN,
        "logistik",
        "burkhardt",
        "Lagerverwaltung",
    ),
    ("zollunterlagen", "Zollunterlagen", K.VERTRAULICH, "logistik", "burkhardt", "Zollabwicklung"),
    (
        "temperaturprotokolle",
        "Temperaturprotokolle Kühlkette",
        K.INTERN,
        "logistik",
        "burkhardt",
        "Telematik",
    ),
    (
        "fahrerdisposition",
        "Fahrerdisposition",
        K.PERSONENBEZOGEN,
        "logistik",
        "burkhardt",
        "Transportmanagement",
    ),
    (
        "rampenbelegung",
        "Rampenbelegung Zentrallager",
        K.INTERN,
        "logistik",
        "burkhardt",
        "Lagerverwaltung",
    ),
    (
        "transportauftraege-fremd",
        "Transportaufträge Fremdspediteure",
        None,
        "logistik",
        "burkhardt",
        "Ablage im Team",
    ),
    # --- Personal ----------------------------------------------------------
    (
        "personalstammdaten",
        "Personalstammdaten",
        K.PERSONENBEZOGEN,
        "personal",
        "weidner",
        "Personalsystem",
    ),
    (
        "dienstplaene",
        "Dienstpläne Filiale",
        K.PERSONENBEZOGEN,
        "personal",
        "weidner",
        "Personaleinsatzplanung",
    ),
    (
        "zeiterfassung",
        "Zeiterfassung Filiale",
        K.PERSONENBEZOGEN,
        "personal",
        "weidner",
        "Zeitwirtschaft",
    ),
    (
        "arbeitszeitkonten",
        "Arbeitszeitkonten",
        K.BESONDERE_KATEGORIE,
        "personal",
        "weidner",
        "Zeitwirtschaft",
    ),
    (
        "entgeltabrechnung",
        "Entgeltabrechnung",
        K.BESONDERE_KATEGORIE,
        "personal",
        "weidner",
        "Entgeltsystem",
    ),
    (
        "fehlzeiten",
        "Fehlzeiten je Beschäftigtem",
        K.BESONDERE_KATEGORIE,
        "personal",
        "weidner",
        "Zeitwirtschaft",
    ),
    (
        "leistungsbeurteilungen",
        "Leistungsbeurteilungen",
        K.BESONDERE_KATEGORIE,
        "personal",
        "weidner",
        "Personalsystem",
    ),
    (
        "bewerberdaten",
        "Bewerberdaten",
        K.PERSONENBEZOGEN,
        "personal",
        "weidner",
        "Bewerbermanagement",
    ),
    (
        "schulungsnachweise",
        "Schulungsnachweise",
        K.PERSONENBEZOGEN,
        "personal",
        "weidner",
        "Lernplattform",
    ),
    (
        "mitarbeiterbefragung",
        "Mitarbeiterbefragung",
        K.PERSONENBEZOGEN,
        "personal",
        "weidner",
        "Befragungsplattform",
    ),
    (
        "personalbedarfsprognose",
        "Personalbedarfsprognose",
        K.INTERN,
        "personal",
        "weidner",
        "Personaleinsatzplanung",
    ),
    (
        "gespraechsnotizen",
        "Gesprächsnotizen Bewerbung",
        None,
        "personal",
        "weidner",
        "Ablage im Team",
    ),
    # --- Finanzen und Controlling -----------------------------------------
    (
        "umsatzmeldung",
        "Umsatzmeldung Tagesabschluss",
        K.VERTRAULICH,
        "finanzen",
        "gutmann",
        "Buchhaltungssystem",
    ),
    (
        "kreditorenrechnungen",
        "Kreditorenrechnungen",
        K.VERTRAULICH,
        "finanzen",
        "gutmann",
        "Buchhaltungssystem",
    ),
    (
        "debitoren-offene-posten",
        "Offene Posten Debitoren",
        K.VERTRAULICH,
        "finanzen",
        "gutmann",
        "Buchhaltungssystem",
    ),
    (
        "anlagenbuchhaltung",
        "Anlagenbuchhaltung",
        K.VERTRAULICH,
        "finanzen",
        "gutmann",
        "Buchhaltungssystem",
    ),
    (
        "kostenstellenplan",
        "Kostenstellenplan",
        K.INTERN,
        "finanzen",
        "gutmann",
        "Buchhaltungssystem",
    ),
    ("budgetplanung", "Budgetplanung", K.VERTRAULICH, "finanzen", "gutmann", "Planungssystem"),
    (
        "steuerkennzahlen",
        "Steuerliche Kennzahlen",
        K.VERTRAULICH,
        "finanzen",
        "gutmann",
        "Buchhaltungssystem",
    ),
    (
        "filialergebnisrechnung",
        "Filialergebnisrechnung",
        K.VERTRAULICH,
        "finanzen",
        "gutmann",
        "Data Warehouse",
    ),
    # --- Expansion und Immobilien -----------------------------------------
    ("standortdaten", "Standortdaten", K.INTERN, "expansion", "lorenz", "Immobilienverwaltung"),
    ("mietvertraege", "Mietverträge", K.VERTRAULICH, "expansion", "lorenz", "Immobilienverwaltung"),
    (
        "baufortschritt",
        "Baufortschritt Neubauten",
        K.VERTRAULICH,
        "expansion",
        "lorenz",
        "Projektsteuerung",
    ),
    (
        "energieverbrauch",
        "Energieverbrauch je Filiale",
        K.INTERN,
        "expansion",
        "lorenz",
        "Gebäudeleittechnik",
    ),
    (
        "standortprognosen",
        "Standortprognosen",
        K.VERTRAULICH,
        "expansion",
        "lorenz",
        "Standortanalyse",
    ),
    (
        "sensordaten-kuehlung",
        "Sensordaten Kühlmöbel",
        None,
        "expansion",
        "lorenz",
        "Gebäudeleittechnik",
    ),
    # --- Marketing und Kundenbindung --------------------------------------
    (
        "kundenkartendaten",
        "Kundenkartendaten",
        K.PERSONENBEZOGEN,
        "marketing",
        "haenel",
        "Kundenbindungssystem",
    ),
    (
        "kaufhistorie",
        "Kaufhistorie Kundenkarte",
        K.PERSONENBEZOGEN,
        "marketing",
        "haenel",
        "Kundenbindungssystem",
    ),
    (
        "newsletter-verteiler",
        "Newsletter-Verteiler",
        K.PERSONENBEZOGEN,
        "marketing",
        "haenel",
        "Versandplattform",
    ),
    (
        "coupon-einloesungen",
        "Coupon-Einlösungen",
        K.PERSONENBEZOGEN,
        "marketing",
        "haenel",
        "Kundenbindungssystem",
    ),
    ("warenkorbanalysen", "Warenkorbanalysen", K.INTERN, "marketing", "haenel", "Data Warehouse"),
    ("werbemittelplanung", "Werbemittelplanung", K.INTERN, "marketing", "haenel", "Werbeplanung"),
    (
        "reklamationen",
        "Kundenreklamationen",
        K.PERSONENBEZOGEN,
        "marketing",
        "haenel",
        "Servicecenter",
    ),
    ("handzettelpreise", "Handzettelpreise", K.OEFFENTLICH, "marketing", "haenel", "Werbeplanung"),
    (
        "aktionscontrolling-ablage",
        "Ablage Aktionscontrolling",
        None,
        "marketing",
        "haenel",
        "Ablage im Team",
    ),
    # --- Qualitätssicherung ------------------------------------------------
    (
        "laborbefunde",
        "Laborbefunde Eigenmarke",
        K.VERTRAULICH,
        "qs",
        "wendt",
        "Laborinformationssystem",
    ),
    ("rueckrufmeldungen", "Rückrufmeldungen", K.VERTRAULICH, "qs", "wendt", "Qualitätsmanagement"),
    (
        "lieferantenzertifikate",
        "Zertifikate der Lieferanten",
        K.INTERN,
        "qs",
        "wendt",
        "Qualitätsmanagement",
    ),
    (
        "hygieneprotokolle",
        "Hygieneprotokolle Filiale",
        K.INTERN,
        "qs",
        "wendt",
        "Qualitätsmanagement",
    ),
    (
        "unfallmeldungen",
        "Unfallmeldungen",
        K.BESONDERE_KATEGORIE,
        "qs",
        "wendt",
        "Arbeitssicherheit",
    ),
    ("betriebsanweisungen", "Betriebsanweisungen", K.INTERN, "qs", "wendt", "Arbeitssicherheit"),
    (
        "auditfeststellungen",
        "Auditfeststellungen Lieferanten",
        None,
        "qs",
        "wendt",
        "Ablage im Team",
    ),
    # --- IT und Digitalisierung -------------------------------------------
    (
        "schnittstellenverzeichnis",
        "Schnittstellenverzeichnis",
        K.INTERN,
        "it",
        "dietrich",
        "Betriebsdokumentation",
    ),
    (
        "systemprotokolle",
        "Systemprotokolle Warenwirtschaft",
        K.INTERN,
        "it",
        "dietrich",
        "Warenwirtschaft",
    ),
    (
        "berechtigungsrollen",
        "Berechtigungsrollen Warenwirtschaft",
        K.VERTRAULICH,
        "it",
        "dietrich",
        "Berechtigungsverwaltung",
    ),
)

#: Was der Sync in den angebundenen Systemen vorgefunden hat. Diese Objekte
#: sind unbestaetigt und ohne Kategorie — sie sind gefunden, nicht gemeldet.
VORGEFUNDENE_DATENOBJEKTE: tuple[tuple[str, str, str], ...] = (
    ("DO-EXT-01", "Preisliste Aktionsware (Ablage Einkauf)", "Tabellenablage Einkauf"),
    ("DO-EXT-02", "Auswertung Frischeverluste", "Tabellenablage Vertrieb"),
    ("DO-EXT-03", "Bestandsabgleich Filiale und Lager", "Tabellenablage Logistik"),
    ("DO-EXT-04", "Kundenzufriedenheit Panel", "Tabellenablage Marketing"),
    ("DO-EXT-05", "Personalkennzahlen Monatsbericht", "Tabellenablage Personal"),
    ("DO-EXT-06", "Schnittstellendaten Kassensystem", "Tabellenablage IT"),
)


def _angelegt_vor() -> dict[str, int]:
    """Wann jedes Datenobjekt entstanden ist — abgeleitet, nicht gepflegt.

    Ein Datenobjekt gibt es, **bevor** der erste Prozess es referenziert. Statt
    zu jedem Eintrag ein Datum zu pflegen und es bei jeder Aenderung wieder von
    Hand nachzuziehen, wird es aus dem aeltesten Verweis gerechnet. Der Bestand
    ist damit in sich stimmig, ohne dass jemand darauf aufpassen muss.

    Die Ersterfassung war ein Projekt und kein Dauerzustand; sie liegt deshalb
    dicht beieinander in einem Zeitraum von wenigen Wochen.
    """
    from app.bestand.prozesse import PROZESSE
    from app.bestand.werkzeuge import WERKZEUGE

    aeltester: dict[str, int] = {}
    for prozess in PROZESSE:
        for schluessel in (*prozess.eingang, *prozess.ergebnis):
            aeltester[schluessel] = max(aeltester.get(schluessel, 0), prozess.angelegt_vor)
    for werkzeug in WERKZEUGE:
        for schluessel, _art in werkzeug.daten:
            aeltester[schluessel] = max(aeltester.get(schluessel, 0), werkzeug.angelegt_vor)
    return {
        schluessel: aeltester.get(schluessel, 705) + 12 + (nummer % 9)
        for nummer, (schluessel, *_rest) in enumerate(DATENOBJEKTE)
    }


def baue(kontext: Kontext) -> None:
    """Legt die gepflegten Datenobjekte an und importiert die vorgefundenen."""
    from app.bestand.organisation import QUELLE

    daten = _angelegt_vor()
    for nummer, (schluessel, name, kategorie, bereich, owner, quellsystem) in enumerate(
        DATENOBJEKTE
    ):
        vor_tagen = daten[schluessel]
        kontext.angelegt[f"do:{schluessel}"] = vor_tagen
        with kontext.aktion(vor_tagen, stunde=8 + (nummer % 9), minute=(nummer * 7) % 60):
            objekt = asset.lege_datenobjekt_an(
                kontext.db,
                kontext.wer(owner),
                {
                    "name": name,
                    "beschreibung": f"Geführt im System {quellsystem}.",
                    "kategorie": kategorie,
                    "owner_user_id": kontext.person(owner).id,
                    "fachbereich_id": kontext.fachbereich(bereich).id,
                    "quellsystem": quellsystem,
                },
            )
        kontext.datenobjekte[schluessel] = objekt

    with kontext.aktion(vor_tagen=95):
        anfrage = ImportAnfrage(
            quelle=QUELLE,
            datensaetze=[
                ImportDatensatz(
                    typ=ImportTyp.DATENOBJEKT,
                    externe_id=externe_id,
                    name=name,
                    metadaten={"beschreibung": f"Vom Sync vorgefunden in: {ablage}."},
                )
                for externe_id, name, ablage in VORGEFUNDENE_DATENOBJEKTE
            ],
        )
        importiere(kontext.db, anfrage, akteur_user_id=kontext.person("kellermann").id)
