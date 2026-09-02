"""Vorschlagsdienst der Bewertung (Leitdokument A.8.4, Grundsatz P1).

P1 lautet: „Was aus vorhandenen Daten berechenbar ist, wird nie erfragt." Der
Bewertungsbaum stellt trotzdem Fragen — er muss, denn nicht alles ist
berechenbar. Dieses Modul schliesst die Luecke dazwischen: es rechnet vor, was
die vorhandenen Daten zu einer Frage hergeben, und legt das Ergebnis als
**Vorschlag mit Belegen** neben die Frage.

A.8.4 nennt die Herkunft je Dimension:

* **DS** aus den Kategorien der referenzierten Datenobjekte und dem Kundenkreis,
* **MB** aus denselben Kategorien und den Attestierungen 1 und 2 nach A.6,
* **UR** aus der eigenen Ausfallfolge und der Kritikalitaet der Prozesskette.

**KI** und **RG** bleiben vollstaendig zu erklaeren; **IT** waere nach A.8.4 aus
Telemetrie abzuleiten, die diese Plattform nicht hat. Fuer diese drei Bloecke
gibt es hier bewusst keinen Vorschlag — ein geratener Vorschlag waere schlimmer
als keiner, weil die Abweichung von ihm begruendungspflichtig ist.

Zwei Regeln durchziehen alle Ableitungen:

1. **Ein „ja" braucht einen Beleg, ein „nein" braucht Vollstaendigkeit.**
   Positiv wird nur vorgeschlagen, was ein konkretes Objekt hergibt. Negativ
   nur, wenn die Datenlage geschlossen ist — ein Datenobjekt ohne Kategorie
   kann alles sein und verbietet jedes „nein".
2. **Was die Daten nicht entscheiden, bleibt offen.** Kein Vorschlag ist ein
   gueltiger Zustand (vgl. E-24 zur Wirkungsart). Offen heisst: frei
   beantwortbar, ohne Begruendungspflicht.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import (
    AUSFALLFOLGE_STUFE,
    PERSONENBEZOGENE_KATEGORIEN,
    Datenkategorie,
    Kundenkreis,
)
from app.models.governance import Prozessobjekt
from app.services import ableitung
from app.services.bewertungsbaum import FRAGE_JE_ID

#: Lesbare Namen der Datenkategorien fuer die Belegtexte.
KATEGORIE_NAME: dict[str, str] = {
    Datenkategorie.OEFFENTLICH: "öffentlich",
    Datenkategorie.INTERN: "intern",
    Datenkategorie.VERTRAULICH: "vertraulich",
    Datenkategorie.PERSONENBEZOGEN: "personenbezogen",
    Datenkategorie.BESONDERE_KATEGORIE: "besondere Kategorie",
}

#: Lesbare Namen der Ausfallfolgen fuer die Belegtexte.
AUSFALLFOLGE_NAME: dict[str, str] = {
    "keine": "keine",
    "gering": "gering",
    "spuerbar": "spürbar",
    "kritisch": "kritisch",
}


@dataclass(frozen=True)
class Beleg:
    """Ein einzelner Grund, in der Sprache des Objekts, aus dem er stammt.

    ``quelle`` sagt, welches Modul den Beleg getragen hat; die Oberflaeche
    verlinkt darueber zurueck auf das Objekt, damit ein Vorschlag nicht nur
    behauptet, sondern nachschlagbar ist.
    """

    text: str
    quelle: str


@dataclass(frozen=True)
class Vorschlag:
    """Was die Daten zu einer Frage sagen — oder dass sie nichts sagen."""

    frage_id: str
    wert: bool | None
    belege: tuple[Beleg, ...] = ()

    @property
    def ableitbar(self) -> bool:
        return self.wert is not None


def _offen(frage_id: str, *belege: Beleg) -> Vorschlag:
    """Kein Vorschlag — mit dem Hinweis, warum die Daten nicht reichen."""
    return Vorschlag(frage_id, None, belege)


# --- DS: Datenschutz ------------------------------------------------------


def _ds(prozess: Prozessobjekt, lage: ableitung.Datenlage) -> dict[str, Vorschlag]:
    """A.8.4: Kategorien der referenzierten Datenobjekte und Kundenkreis.

    Der Kundenkreis wirkt hier **nur negativ**: ein externer Kundenkreis
    verhindert das „nein", statt ein „ja" zu behaupten. Ein Prozess mit
    externem Kundenkreis kann eine Preisliste veroeffentlichen und dabei keine
    einzige personenbezogene Angabe verarbeiten — daraus ein „ja" abzuleiten,
    waere geraten. Dass die Datenlage moeglicherweise unvollstaendig ist, ist
    dagegen eine belastbare Aussage.
    """
    besondere = [o for o in lage.objekte if o.kategorie == Datenkategorie.BESONDERE_KATEGORIE]
    personenbezogene = [o for o in lage.objekte if o.kategorie in PERSONENBEZOGENE_KATEGORIEN]
    extern = prozess.customer == Kundenkreis.EXTERN

    def kategorie_beleg(objekt) -> Beleg:
        name = KATEGORIE_NAME.get(objekt.kategorie, str(objekt.kategorie))
        return Beleg(f"Datenobjekt „{objekt.name}“ trägt die Kategorie {name}.", "datenobjekt")

    unvollstaendig = Beleg(
        "Nicht alle referenzierten Datenobjekte sind eingeordnet: "
        + ", ".join(f"„{o.name}“" for o in lage.ohne_kategorie)
        + ". Solange bleibt die Frage offen.",
        "datenobjekt",
    )
    ohne_objekte = Beleg(
        "Der Prozess referenziert kein Datenobjekt. Ohne Datenlage gibt es nichts abzuleiten.",
        "prozess",
    )
    externer_kreis = Beleg(
        "Der Kundenkreis ist extern. Ob dabei personenbezogene Daten fließen, "
        "steht in keinem Stammdatum — deshalb kein Vorschlag.",
        "kundenkreis",
    )

    vorschlaege: dict[str, Vorschlag] = {}

    # 2a fragt nach besonderen Kategorien **oder** Profilbildung. Die erste
    # Haelfte steht in den Daten, die zweite nicht: ein „nein" wuerde behaupten,
    # dass keine Profilbildung stattfindet, und das weiss nur der Prozesseigner.
    if besondere:
        vorschlaege["2a"] = Vorschlag("2a", True, tuple(kategorie_beleg(o) for o in besondere))
    else:
        vorschlaege["2a"] = _offen(
            "2a",
            Beleg(
                "Kein referenziertes Datenobjekt trägt eine besondere Kategorie. "
                "Ob Profilbildung stattfindet, ist aus den Daten nicht ableitbar.",
                "datenobjekt",
            ),
        )

    # 2b ist die Frage, die A.7 abschliessend beantwortet: die fuenf Kategorien
    # decken alle Faelle ab, „keine davon ist personenbezogen" ist deshalb eine
    # echte Antwort und kein Schweigen.
    if personenbezogene:
        vorschlaege["2b"] = Vorschlag(
            "2b", True, tuple(kategorie_beleg(o) for o in personenbezogene)
        )
    elif not lage.objekte:
        vorschlaege["2b"] = _offen("2b", ohne_objekte)
    elif lage.ohne_kategorie:
        vorschlaege["2b"] = _offen("2b", unvollstaendig)
    elif extern:
        vorschlaege["2b"] = _offen("2b", externer_kreis)
    else:
        vorschlaege["2b"] = Vorschlag(
            "2b",
            False,
            (
                Beleg(
                    f"Alle {len(lage.objekte)} referenzierten Datenobjekte sind eingeordnet, "
                    "keines personenbezogen.",
                    "datenobjekt",
                ),
            ),
        )

    # 2c fragt nach pseudonymisierten oder personenbeziehbaren Daten. Nur wenn
    # ausnahmslos alles oeffentlich ist, ist das sicher ausgeschlossen —
    # „intern" oder „vertraulich" kann sehr wohl personenbeziehbar sein.
    nur_oeffentlich = lage.vollstaendig and lage.kategorien == {Datenkategorie.OEFFENTLICH}
    if nur_oeffentlich and not extern:
        vorschlaege["2c"] = Vorschlag(
            "2c",
            False,
            (
                Beleg(
                    "Alle referenzierten Datenobjekte sind öffentlich; ein Personenbezug "
                    "ist damit ausgeschlossen.",
                    "datenobjekt",
                ),
            ),
        )
    return vorschlaege


# --- MB: Mitbestimmung ----------------------------------------------------


def _mb(prozess: Prozessobjekt, lage: ableitung.Datenlage) -> dict[str, Vorschlag]:
    """A.8.4: dieselben Kategorien plus die Attestierungen 1 und 2 aus A.6.

    Die Konjunktion aus A.5 steht in ``ableitung.mitbestimmung_aus_daten``. Sie
    wird hier nicht nachgebaut, sondern aufgerufen — eine zweite Fassung
    derselben Regel waere genau die Doppelpflege, die P5 verbietet.
    """
    vorschlaege: dict[str, Vorschlag] = {}
    aus_daten = ableitung.mitbestimmung_aus_daten(prozess)
    kein_personenbezug = lage.vollstaendig and not (lage.kategorien & PERSONENBEZOGENE_KATEGORIEN)

    if aus_daten is True:
        belege: list[Beleg] = []
        for objekt in lage.objekte:
            if objekt.kategorie == Datenkategorie.BESONDERE_KATEGORIE:
                belege.append(
                    Beleg(
                        f"Datenobjekt „{objekt.name}“ trägt die besondere Kategorie; A.7 zählt "
                        "dazu Entgelt, Gesundheit und Leistungsbewertung.",
                        "datenobjekt",
                    )
                )
        for tool in prozess.tool_objekte:
            if tool.attest_entscheidung_ueber_personen:
                belege.append(
                    Beleg(
                        f"Tool-Objekt „{tool.name}“ hat attestiert, dass sein Ergebnis in eine "
                        "Entscheidung über einzelne Personen einfließt.",
                        "tool",
                    )
                )
        vorschlaege["3a"] = Vorschlag("3a", True, tuple(belege))
    elif kein_personenbezug:
        # Ohne Personenbezug faellt die Konjunktion aus A.5 in sich zusammen —
        # eine Verhaltens- oder Leistungskontrolle setzt Daten ueber Personen
        # voraus. Das gilt fuer 3a und 3b gleichermassen.
        ohne = Beleg(
            "Kein referenziertes Datenobjekt hat Personenbezug; die Konjunktion aus A.5 "
            "greift damit nicht.",
            "datenobjekt",
        )
        vorschlaege["3a"] = Vorschlag("3a", False, (ohne,))
        vorschlaege["3b"] = Vorschlag("3b", False, (ohne,))
    else:
        vorschlaege["3a"] = _offen(
            "3a",
            Beleg(
                "Personenbezug liegt vor, aber weder eine besondere Kategorie noch eine "
                "Attestierung nach A.6. Ob eine Kontrolle möglich ist, weiß nur der "
                "Prozesseigner.",
                "datenobjekt",
            ),
        )

    # Attestierung 2: kein Mensch zwischen Ergebnis und Wirkung. Ein solches
    # Tool greift unmittelbar in den Ablauf ein — das ist die Frage nach 3c.
    ohne_mensch = [t for t in prozess.tool_objekte if t.attest_mensch_dazwischen is False]
    if ohne_mensch:
        vorschlaege["3c"] = Vorschlag(
            "3c",
            True,
            tuple(
                Beleg(
                    f"Tool-Objekt „{tool.name}“ hat attestiert, dass zwischen Ergebnis und "
                    "Wirkung kein Mensch steht.",
                    "tool",
                )
                for tool in ohne_mensch
            ),
        )
    return vorschlaege


# --- UR: Unternehmerisches Risiko -----------------------------------------


def _ur(prozess: Prozessobjekt) -> dict[str, Vorschlag]:
    """A.8.4: eigene Ausfallfolge, angehoben durch die Kette (A.4.2).

    Als einzige Dimension ist diese vollstaendig ableitbar: die Ausfallfolge
    ist ein Pflichtfeld, und die Vererbung entlang der Kette ist gerechnet.
    Alle drei Fragen bekommen deshalb einen Vorschlag in beide Richtungen.
    """
    stufe, quelle = ableitung.kritikalitaetsquelle(prozess)
    eigene = AUSFALLFOLGE_STUFE[prozess.ausfallfolge]
    name = AUSFALLFOLGE_NAME.get(prozess.ausfallfolge, str(prozess.ausfallfolge))

    belege = [Beleg(f"Die Ausfallfolge des Prozesses ist „{name}“ (Stufe {eigene}).", "prozess")]
    if quelle is not None:
        belege.append(
            Beleg(
                f"Der nachgelagerte Prozess „{quelle.name}“ trägt Stufe {stufe}; nach A.4.2 "
                "ist dieser Prozess mindestens so kritisch.",
                "kette",
            )
        )
    fest = tuple(belege)
    return {
        "6a": Vorschlag("6a", stufe >= 3, fest),
        "6b": Vorschlag("6b", stufe >= 2, fest),
        "6c": Vorschlag("6c", stufe >= 1, fest),
    }


# --- Zusammenfuehrung -----------------------------------------------------


def fuer_prozess(prozess: Prozessobjekt) -> dict[str, Vorschlag]:
    """Alle Vorschlaege zu einem Prozessobjekt, nach Frage-ID.

    Enthaelt nur Eintraege fuer Fragen, zu denen es etwas zu sagen gibt —
    entweder einen Vorschlag oder wenigstens den Grund, warum keiner moeglich
    ist. Fragen der Bloecke KI, IT und RG kommen nicht vor.
    """
    lage = ableitung.datenlage(prozess)
    alle: dict[str, Vorschlag] = {**_ds(prozess, lage), **_mb(prozess, lage), **_ur(prozess)}
    return {frage_id: v for frage_id, v in alle.items() if frage_id in FRAGE_JE_ID}


def werte(vorschlaege: dict[str, Vorschlag]) -> dict[str, bool]:
    """Nur die entschiedenen Vorschlaege — die Form, in der sie gespeichert werden."""
    return {f: v.wert for f, v in vorschlaege.items() if v.wert is not None}


@dataclass(frozen=True)
class Abweichung:
    """Eine Antwort, die dem Vorschlag widerspricht."""

    frage_id: str
    vorschlag: bool
    antwort: bool
    belege: tuple[Beleg, ...] = field(default_factory=tuple)


def abweichungen(vorschlaege: dict[str, Vorschlag], antworten: dict[str, bool]) -> list[Abweichung]:
    """Alle Stellen, an denen die Antwort dem abgeleiteten Vorschlag widerspricht."""
    return [
        Abweichung(frage_id, vorschlag.wert, antworten[frage_id], vorschlag.belege)
        for frage_id, vorschlag in sorted(vorschlaege.items())
        if vorschlag.wert is not None
        and frage_id in antworten
        and antworten[frage_id] is not vorschlag.wert
    ]
