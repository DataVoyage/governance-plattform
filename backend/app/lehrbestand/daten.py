"""Die Datenobjekte — jede der fünf Kategorien aus A.7 genau einmal.

Dazu die beiden Sonderfälle, die im Betrieb am häufigsten vorkommen und in
einem Bestand deshalb nicht fehlen dürfen: eine Quelle **ohne** Kategorie
(sie steht im Cockpit als Aufgabe) und eine im **fremden** Fachbereich (an ihr
zeigt sich jede Sichtregel).

Die Namen nennen die Kategorie. Das ist die bewusste Gegenentscheidung zum
großen Bestand: dort heißt eine Quelle „Kassenjournal", hier heißt sie
„Personenbezogen — Fahrerdaten", weil man beim Prüfen wissen will, was man
vor sich hat.
"""

from __future__ import annotations

from app.bestand.kontext import Kontext
from app.models.enums import Datenkategorie
from app.services import asset

#: (Schlüssel, Name, Kategorie, Fachbereich, Quellsystem)
DATENOBJEKTE: tuple[tuple[str, str, str | None, str, str], ...] = (
    (
        "oeffentlich",
        "Öffentlich — Filialverzeichnis",
        Datenkategorie.OEFFENTLICH,
        "logistik",
        "Web",
    ),
    ("intern", "Intern — Tourenplanung", Datenkategorie.INTERN, "logistik", "SAP TM"),
    (
        "vertraulich",
        "Vertraulich — Frachtkonditionen",
        Datenkategorie.VERTRAULICH,
        "logistik",
        "SAP TM",
    ),
    (
        "personenbezogen",
        "Personenbezogen — Fahrerstammdaten",
        Datenkategorie.PERSONENBEZOGEN,
        "logistik",
        "SAP HCM",
    ),
    (
        "besondere",
        "Besondere Kategorie — Fahrerleistung",
        Datenkategorie.BESONDERE_KATEGORIE,
        "logistik",
        "Telematik",
    ),
    # Ohne Kategorie: erscheint im Cockpit als offene Aufgabe und macht die
    # Datenlage eines Prozesses unvollständig (A.8.4).
    ("ohne_kategorie", "Ohne Kategorie — Ablage ungeklärt", None, "logistik", "Fileshare"),
    # Im fremden Fachbereich: an ihm zeigt sich jede Sichtregel.
    (
        "fremd",
        "Fremder Bereich — Personalstammdaten",
        Datenkategorie.BESONDERE_KATEGORIE,
        "personal",
        "SAP HCM",
    ),
)


def baue(kontext: Kontext) -> None:
    """Legt die sieben Quellen an — jede vom Datenobjekt-Owner ihres Bereichs."""
    for nummer, (schluessel, name, kategorie, bereich, quellsystem) in enumerate(DATENOBJEKTE):
        # Die Logistik-Quellen legt ihr Datenobjekt-Owner an, die fremde die
        # Governance: im Fachbereich Personal gibt es bewusst keinen eigenen
        # Datenobjekt-Owner, damit die Rückfallebene aus A.16 einmal vorkommt.
        wer = "datenowner" if bereich == "logistik" else "governance"
        with kontext.aktion(vor_tagen=380 - nummer):
            objekt = asset.lege_datenobjekt_an(
                kontext.db,
                kontext.wer(wer),
                {
                    "name": name,
                    "beschreibung": f"Geführt im System {quellsystem}.",
                    "kategorie": kategorie,
                    "fachbereich_id": kontext.fachbereich(bereich).id,
                    "quellsystem": quellsystem,
                },
            )
        kontext.datenobjekte[schluessel] = objekt
