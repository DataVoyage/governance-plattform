"""Sieben Prozessobjekte — jede Stufe, jeder Status, eine Kette.

Was hier vorkommen muss, und warum:

* **Tier 1, 2 und 3**, damit jede Auflagenstufe und jede Frist einmal wirkt.
* **Eine Kette** aus drei Gliedern. An ihr zeigt sich die Kritikalität nach
  A.4.2: das harmlose Vorderglied wird kritisch, weil sein Nachfolger es ist —
  und zwar transitiv über zwei Kanten.
* **Zwei Umsetzungen** an einem Prozess. Erst ab der zweiten hebt sich die
  Reichweite auf „unternehmen" (A.4.4); mit nur einem Land wäre die Regel
  unsichtbar.
* **Ein Prozess ohne Bewertung** — der Ausgangszustand jeder Neuanlage und
  eine Zeile im Cockpit.
* **Ein Prozess im fremden Fachbereich**, an dem jede Sichtregel eine
  Gegenprobe hat.

Die Kette liest sich von hinten: „Kette 3 — kritisch" ist das Ende, „Kette 1"
der Anfang. Wer die Namen nebeneinander sieht, weiß, wohin die Kritikalität
fließt.
"""

from __future__ import annotations

from app.bestand.kontext import Kontext
from app.models.enums import Ausfallfolge, Kundenkreis
from app.schemas.prozess import ProzessAnlegen
from app.services import bewertung as bewertung_service
from app.services import prozess as prozess_service


class Eintrag:
    """Ein Prozessobjekt des Lehrbestands."""

    __slots__ = (
        "schluessel",
        "name",
        "bereich",
        "owner",
        "eingang",
        "ergebnis",
        "kunde",
        "ausfallfolge",
        "laender",
        "ziele",
        "vorgelagert",
        "eigner",
    )

    def __init__(
        self,
        schluessel: str,
        name: str,
        bereich: str,
        owner: str,
        *,
        eingang: tuple[str, ...] = (),
        ergebnis: tuple[str, ...] = (),
        kunde: str = Kundenkreis.BEREICH,
        ausfallfolge: str = Ausfallfolge.GERING,
        laender: tuple[str, ...] = (),
        ziele: tuple[str, ...] = (),
        vorgelagert: tuple[str, ...] = (),
        eigner: str | None = None,
    ) -> None:
        self.schluessel = schluessel
        self.name = name
        self.bereich = bereich
        self.owner = owner
        self.eingang = eingang
        self.ergebnis = ergebnis
        self.kunde = kunde
        self.ausfallfolge = ausfallfolge
        self.laender = laender
        self.ziele = ziele
        self.vorgelagert = vorgelagert
        #: Wer als Eigner eingetragen ist — nicht zwingend der Anlegende.
        self.eigner = eigner or owner


PROZESSE: tuple[Eintrag, ...] = (
    # --- Die Kette: Kritikalität fließt von hinten nach vorn (A.4.2) -------
    Eintrag(
        "kette1",
        "Kette 1 — harmlos, wird durch die Kette kritisch",
        "logistik",
        "prozessowner",
        eingang=("intern",),
        kunde=Kundenkreis.TEAM,
        ausfallfolge=Ausfallfolge.GERING,
    ),
    Eintrag(
        "kette2",
        "Kette 2 — Mittelglied",
        "logistik",
        "prozessowner",
        eingang=("intern",),
        ergebnis=("vertraulich",),
        ausfallfolge=Ausfallfolge.GERING,
        vorgelagert=("kette1",),
    ),
    Eintrag(
        "kette3",
        "Kette 3 — kritisch, Quelle der Kritikalität",
        "logistik",
        "prozessowner",
        eingang=("vertraulich",),
        kunde=Kundenkreis.UNTERNEHMEN,
        ausfallfolge=Ausfallfolge.KRITISCH,
        vorgelagert=("kette2",),
    ),
    # --- Tier 3 mit allem, was dazugehört ----------------------------------
    Eintrag(
        "tier3",
        "Tier 3 — mit Gate 1, Selbstverpflichtung und zwei Ländern",
        "logistik",
        "prozessowner",
        eingang=("personenbezogen", "besondere"),
        ergebnis=("besondere",),
        kunde=Kundenkreis.BEREICH,
        ausfallfolge=Ausfallfolge.SPUERBAR,
        # Zwei Umsetzungen: erst ab der zweiten hebt sich die Reichweite.
        laender=("logistik-de", "logistik-fr"),
        ziele=("https://partner.beispiel-ag.de/avise",),
    ),
    # --- Tier 2: läuft, ohne Gate ------------------------------------------
    # Angelegt vom Fachbereichs-Owner, nicht vom bereichsowner: der ist auf ein
    # **Land** gescoped, und der Prozessgeber ist immer eine INT-Einheit. Ein
    # Prozess-Owner mit Landes-Scope kann deshalb keinen Prozess anlegen — er
    # sieht die Prozesse, die in seinem Land umgesetzt werden, und pflegt deren
    # lokale Abweichung. Das ist keine Luecke, sondern die Regel.
    Eintrag(
        "tier2",
        "Tier 2 — läuft ohne Gate, umgesetzt in DE",
        "logistik",
        "prozessowner",
        eingang=("intern",),
        ausfallfolge=Ausfallfolge.SPUERBAR,
        laender=("logistik-de",),
    ),
    # --- Ohne Bewertung: der Ausgangszustand jeder Neuanlage ---------------
    Eintrag(
        "unbewertet",
        "Ohne Bewertung — Entwurf, wie er entsteht",
        "logistik",
        "prozessowner",
        eingang=("ohne_kategorie",),
    ),
    # --- Das Gegenüber im fremden Fachbereich ------------------------------
    Eintrag(
        "fremd",
        "Fremder Bereich — für niemanden aus der Logistik sichtbar",
        "personal",
        "fremdowner",
        eingang=("fremd",),
        kunde=Kundenkreis.EXTERN,
        ausfallfolge=Ausfallfolge.SPUERBAR,
    ),
    # --- Tier 1: das untere Ende der Skala ---------------------------------
    # Ohne Kette, ohne Ausfallfolge: Kritikalitaet 0, jede Dimension 0, damit
    # Tier 1 und die Kurzform der Selbstverpflichtung (A.10.5) vorkommen.
    Eintrag(
        "tier1",
        "Tier 1 — geringes Risiko, nur Grundpflichten",
        "logistik",
        "prozessowner",
        eingang=("oeffentlich", "ohne_kategorie"),
        kunde=Kundenkreis.PERSOENLICH,
        ausfallfolge=Ausfallfolge.KEINE,
        # Der Eigner scheidet spaeter aus. Danach traegt dieses Prozessobjekt
        # niemand mehr — die erste Zeile des Cockpits, und im Betrieb der
        # haeufigste Grund dafuer.
        eigner="ausgeschieden",
    ),
)

#: Zielprofile je Prozess: (ki, ds, mb, it, rg). Die sechste Dimension UR
#: schlägt die Anwendung aus der Kritikalität vor — sie wird hier nie gesetzt,
#: damit der Vorschlagsdienst genau das tut, wofür er da ist.
PROFILE: dict[str, tuple[int, int, int, int, int]] = {
    "kette1": (0, 0, 0, 1, 0),
    "kette2": (0, 1, 0, 1, 0),
    "kette3": (0, 0, 0, 1, 0),
    "tier3": (0, 3, 2, 1, 2),
    "tier2": (0, 0, 0, 2, 0),
    "fremd": (0, 1, 0, 1, 0),
    "tier1": (0, 0, 0, 0, 0),
}


def baue(kontext: Kontext) -> None:
    """Legt die sieben Prozessobjekte an, danach die Ketten-Kanten."""
    for nummer, eintrag in enumerate(PROZESSE):
        with kontext.aktion(vor_tagen=360 - nummer * 2):
            objekt = prozess_service.anlegen(
                kontext.db,
                kontext.wer(eintrag.owner),
                ProzessAnlegen(
                    name=eintrag.name,
                    owner_user_id=kontext.person(eintrag.eigner).id,
                    stellvertretung_user_id=kontext.person("governance").id,
                    prozessgeber_org_id=kontext.einheit(eintrag.bereich).id,
                    supplier="Vorsystem",
                    input_datenobjekt_ids=[kontext.datenobjekt(s).id for s in eintrag.eingang],
                    process_steps="Erfassen\nPrüfen\nFreigeben",
                    output="Ergebnis des Prozesses",
                    output_datenobjekt_ids=[kontext.datenobjekt(s).id for s in eintrag.ergebnis],
                    customer=eintrag.kunde,
                    ausfallfolge=eintrag.ausfallfolge,
                    umsetzung_land_org_ids=[kontext.einheit(s).id for s in eintrag.laender],
                    erlaubte_externe_ziele=list(eintrag.ziele),
                ),
            )
        kontext.prozesse[eintrag.schluessel] = objekt

    # Die Kanten erst danach: beim Anlegen gibt es das Gegenstück noch nicht.
    for nummer, eintrag in enumerate(PROZESSE):
        if not eintrag.vorgelagert:
            continue
        with kontext.aktion(vor_tagen=344 - nummer):
            prozess_service.aendern(
                kontext.db,
                kontext.wer(eintrag.owner),
                kontext.prozess(eintrag.schluessel),
                _aenderung(vorgelagert_ids=[kontext.prozess(s).id for s in eintrag.vorgelagert]),
            )


def _aenderung(**werte):
    from app.schemas.prozess import ProzessAendern

    return ProzessAendern(**werte)


def bewerte(kontext: Kontext) -> None:
    """Bewertet sechs der sieben — einer bleibt bewusst ohne.

    Die Antworten entstehen aus dem Zielprofil ueber ``antworten_aus_profil``:
    denselben Weg geht der grosse Bestand, und der Baum ist zu verzweigt, um
    ihn ein zweites Mal nachzubauen (der KI-Block hat vier Fragen, nicht drei).

    Die sechste Dimension UR wird nicht gesetzt, sondern aus der **Kritikalitaet**
    uebernommen — genau so, wie es die Anwendung vorschlaegt. Damit steht die
    Kette aus A.4.2 auch in den Bewertungen.
    """
    from app.bestand.bewertungen import antworten_aus_profil
    from app.services import ableitung

    for nummer, eintrag in enumerate(PROZESSE):
        vorgabe = PROFILE.get(eintrag.schluessel)
        if vorgabe is None:
            continue
        prozess = kontext.prozess(eintrag.schluessel)
        profil = {
            "ki": vorgabe[0],
            "ds": vorgabe[1],
            "mb": vorgabe[2],
            "it": vorgabe[3],
            "rg": vorgabe[4],
            "ur": ableitung.leite_kritikalitaet_ab(prozess),
        }
        antworten = antworten_aus_profil(profil)
        with kontext.aktion(vor_tagen=330 - nummer * 2, stunde=10):
            ergebnis = bewertung_service.speichere(
                kontext.db,
                kontext.wer(eintrag.owner),
                prozess,
                antworten,
                modus=bewertung_service.Modus.VOLLSTAENDIG,
                begruendungen=dict.fromkeys(
                    antworten, "Im Lehrbestand bewusst so gesetzt, um diesen Fall zu zeigen."
                ),
            )
        kontext.bewertungen[eintrag.schluessel] = ergebnis
