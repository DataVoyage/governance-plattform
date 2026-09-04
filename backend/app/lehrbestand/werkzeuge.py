"""Fünf Tool-Objekte — jede Technologie, jeder Zustand der Vererbung.

Was hier vorkommen muss:

* **Jede der vier Technologien** einmal, damit die Technologiematrix an jeder
  Spalte etwas zu zeigen hat.
* **Ein Werkzeug an zwei Prozessen**: nur daran wird sichtbar, dass die
  Einstufung das Maximum ist und dass die maßgebliche Kante benannt wird
  (A.4.4).
* **Ein Werkzeug ohne Prozesskante** — der gelbe Zustand „nicht zugeordnet"
  aus A.13.3. Es erbt nichts, und das ist kein Fehler, sondern der
  Ausgangszustand des Altbestands.
* **Ein Werkzeug ohne Attestierung**: ohne die drei Erklärungen aus A.6 gibt
  es keine Prozesskante, und die Wirkungsart bleibt offen.
* **Vorgefundene Objekte** aus dem Import, unbestätigt — der einzige Zustand,
  in dem ein Objekt keinen Anker hat.
"""

from __future__ import annotations

from app.bestand.kontext import Kontext
from app.models.enums import Ausfuehrungsidentitaet, ImportTyp, Lauftyp, Zugriffsart
from app.schemas.integration import ImportAnfrage, ImportDatensatz
from app.services import asset
from app.sync.importer import importiere

QUELLE = "zentrale-entwicklungsplattform"


class Werkzeug:
    """Ein Tool-Objekt des Lehrbestands."""

    __slots__ = (
        "schluessel",
        "name",
        "technologie",
        "einheit",
        "prozesse",
        "daten",
        "attestiert",
        "angelegt_vor",
        "lauftyp",
        "identitaet",
    )

    def __init__(
        self,
        schluessel: str,
        name: str,
        technologie: str | None,
        einheit: str,
        *,
        prozesse: tuple[str, ...] = (),
        daten: tuple[tuple[str, str], ...] = (),
        attestiert: bool = True,
        angelegt_vor: int | None = None,
        lauftyp: str = Lauftyp.GEPLANT,
        identitaet: str = Ausfuehrungsidentitaet.BENANNTER_DIENST,
    ) -> None:
        self.schluessel = schluessel
        self.name = name
        self.technologie = technologie
        self.einheit = einheit
        self.prozesse = prozesse
        self.daten = daten
        self.attestiert = attestiert
        #: Tage vor heute. Ohne Angabe gestaffelt aus der Reihenfolge.
        self.angelegt_vor = angelegt_vor
        #: Ausfuehrungsart und Identitaet gehoeren zusammen (A.13.2, Element 6
        #: und 7): interaktiv heisst, ein Mensch bedient — dann laeuft es unter
        #: dessen Identitaet. Geplant heisst, niemand ist da; dann ist eine
        #: benannte Dienstidentitaet die einzige, die sich zuordnen laesst.
        self.lauftyp = lauftyp
        self.identitaet = identitaet


WERKZEUGE: tuple[Werkzeug, ...] = (
    Werkzeug(
        "im_rahmen",
        "Im Rahmen — liest, was der Prozess erklärt",
        "apps-script",
        "logistik-de",
        prozesse=("kette1",),
        daten=(("intern", Zugriffsart.LESEN),),
        # Ein Mensch startet es und sieht das Ergebnis — deshalb laeuft es
        # unter seiner Identitaet, und das ist im Rahmen.
        lauftyp=Lauftyp.INTERAKTIV,
        identitaet=Ausfuehrungsidentitaet.PERSOENLICH,
    ),
    Werkzeug(
        "zwei_kanten",
        "An zwei Prozessen — erbt das Maximum",
        "python-kubernetes",
        "logistik-de",
        prozesse=("kette1", "kette3"),
        # Schreibend — und erlaubt: „vertraulich" ist Ergebnis von Kette 2.
        daten=(("vertraulich", Zugriffsart.LESEN_SCHREIBEN),),
    ),
    Werkzeug(
        "ausserhalb",
        "Außerhalb des Rahmens — greift auf Ungefragtes zu",
        "appsheet",
        "logistik-de",
        prozesse=("tier3",),
        # „ohne_kategorie" steht an keinem Prozess: der Zugriff ist damit
        # nicht erklärt und erscheint als Abweichung.
        # „ohne_kategorie" steht an keinem Prozess, und geschrieben wird dort
        # schon gar nicht: zwei Abweichungen in einem Element.
        daten=(
            ("personenbezogen", Zugriffsart.LESEN),
            ("ohne_kategorie", Zugriffsart.SCHREIBEN),
        ),
        lauftyp=Lauftyp.GETRIGGERT,
    ),
    Werkzeug(
        "ohne_prozess",
        "Ohne Prozesskante — Attestierung veraltet",
        "bigquery-gcs",
        "logistik",
        daten=(("oeffentlich", Zugriffsart.LESEN),),
        # Aelter als die Gueltigkeit von 365 Tagen: die Attestierung traegt
        # nicht mehr, und das Cockpit sagt es. Ohne Prozesskante geht das
        # gefahrlos — es gibt keine Reihenfolge, die verletzt werden koennte.
        angelegt_vor=390,
    ),
    Werkzeug(
        "ohne_attest",
        "Ohne Attestierung — nicht verknüpfbar",
        "apps-script",
        "logistik-fr",
        attestiert=False,
        # Vorgefunden im Altbestand: laeuft unter einem geteilten Konto. Das
        # erste der sechs Verbote aus A.13.2 Schicht 2, und es bleibt stehen —
        # aufgeloest wird der andere.
        lauftyp=Lauftyp.INTERAKTIV,
        identitaet=Ausfuehrungsidentitaet.GETEILTES_KONTO,
    ),
)


def baue(kontext: Kontext) -> None:
    """Legt die fünf Werkzeuge an, attestiert sie und setzt ihre Kanten."""
    for nummer, werkzeug in enumerate(WERKZEUGE):
        wann = werkzeug.angelegt_vor if werkzeug.angelegt_vor is not None else 250 - nummer * 2
        with kontext.aktion(vor_tagen=wann, stunde=9):
            tool = asset.lege_tool_an(
                kontext.db,
                kontext.wer("toolowner"),
                {
                    "name": werkzeug.name,
                    "technologie": werkzeug.technologie,
                    "organisationseinheit_id": kontext.einheit(werkzeug.einheit).id,
                    "technischer_owner_user_id": kontext.person("toolowner").id,
                    "stellvertretung_user_id": kontext.person("governance").id,
                    "lauftyp": werkzeug.lauftyp,
                    "ausfuehrungsidentitaet": werkzeug.identitaet,
                },
            )
        kontext.tools[werkzeug.schluessel] = tool

        if werkzeug.attestiert:
            with kontext.aktion(vor_tagen=wann - 1, stunde=10):
                asset.attestiere(
                    kontext.db,
                    kontext.wer("toolowner"),
                    tool,
                    {
                        "attest_entscheidung_ueber_personen": False,
                        "attest_mensch_dazwischen": True,
                        "attest_undeklarierte_quellen": False,
                    },
                )

        for schluessel in werkzeug.prozesse:
            with kontext.aktion(vor_tagen=wann - 2, stunde=11):
                asset.verknuepfe_tool_mit_prozess(
                    kontext.db, kontext.wer("toolowner"), tool, kontext.prozess(schluessel)
                )
        for datenobjekt, art in werkzeug.daten:
            with kontext.aktion(vor_tagen=wann - 3, stunde=12):
                asset.verknuepfe_tool_mit_datenobjekt(
                    kontext.db,
                    kontext.wer("toolowner"),
                    tool,
                    kontext.datenobjekt(datenobjekt),
                    zugriffsart=art,
                )


def vorgefunden(kontext: Kontext) -> None:
    """Der Import: ein Tool und eine Quelle, beide unbestätigt.

    Sie kommen ohne Anker an — niemand hat sie zugeordnet. Damit sind sie nur
    den global lesenden Rollen sichtbar, und die Bestätigung verlangt die
    Zuordnung (E-55). Es ist der einzige Zustand, in dem ein Objekt niemandem
    gehört, und er muss im Bestand vorkommen.
    """
    with kontext.aktion(vor_tagen=40, stunde=8):
        importiere(
            kontext.db,
            ImportAnfrage(
                quelle=QUELLE,
                datensaetze=[
                    ImportDatensatz(
                        typ=ImportTyp.TOOL,
                        externe_id="T-VORGEFUNDEN",
                        name="Vorgefunden — noch nicht zugeordnet",
                        metadaten={"beschreibung": "Vom Sync im Bestand gefunden."},
                    ),
                    ImportDatensatz(
                        typ=ImportTyp.DATENOBJEKT,
                        externe_id="D-VORGEFUNDEN",
                        name="Vorgefundene Ablage — noch nicht zugeordnet",
                        metadaten={"beschreibung": "Vom Sync im Bestand gefunden."},
                    ),
                ],
            ),
            akteur_user_id=kontext.person("plattform").id,
        )
