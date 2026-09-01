"""Der Entscheidungsbaum aus Leitdokument A.8.5 als Datenstruktur.

Die Reihenfolge der sechs Themenbloecke — KI, Datenschutz, Mitbestimmung,
IT-Sicherheit, Regulatorik, unternehmerisches Risiko — ist **keine
UI-Entscheidung**. Sie liegt hier in der Geschaeftslogik, damit sie nicht
versehentlich in der Oberflaeche verschoben werden kann (Architektur 8.2).

Innerhalb eines Blocks stehen die Fragen absteigend nach Schwere: die erste mit
``ja`` beantwortete Frage bestimmt die Stufe des Blocks. Wird keine bejaht,
ist die Stufe 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

#: Stufe, die einen nach EU AI Act verbotenen Tatbestand kennzeichnet.
KI_VERBOTEN = -1


class Block(StrEnum):
    KI = "ki"
    DS = "ds"
    MB = "mb"
    IT = "it"
    RG = "rg"
    UR = "ur"


@dataclass(frozen=True)
class Frage:
    id: str
    text: str
    stufe_bei_ja: int
    #: Bei ``ja`` endet der Block sofort mit ``stufe_bei_ja``; bei ``nein``
    #: geht es zur naechsten Frage. ``abbruch_bei_nein`` kehrt das um: dann
    #: endet der Block bei ``nein`` mit Stufe 0 (Einstiegsfrage des KI-Blocks).
    abbruch_bei_nein: bool = False
    #: Ein ``ja`` bricht die gesamte Bewertung ab (Verbotstatbestand).
    verbot_bei_ja: bool = False


@dataclass(frozen=True)
class Themenblock:
    block: Block
    titel: str
    fragen: tuple[Frage, ...] = field(default_factory=tuple)


#: Die sechs Bloecke in der im Leitdokument festgelegten Reihenfolge.
BAUM: tuple[Themenblock, ...] = (
    Themenblock(
        Block.KI,
        "Kuenstliche Intelligenz",
        (
            Frage(
                "1a",
                "Setzt der Prozess ein KI-System oder ein KI-Modell ein?",
                stufe_bei_ja=1,
                abbruch_bei_nein=True,
            ),
            Frage(
                "1b",
                "Faellt der Einsatz unter eine nach EU AI Act verbotene Praxis "
                "(etwa Social Scoring, Emotionserkennung am Arbeitsplatz, "
                "biometrische Kategorisierung)?",
                stufe_bei_ja=KI_VERBOTEN,
                verbot_bei_ja=True,
            ),
            Frage(
                "1c",
                "Handelt es sich um einen Hochrisiko-Anwendungsfall nach Anhang III "
                "des EU AI Act (etwa Personalauswahl, Kreditwuerdigkeit, kritische "
                "Infrastruktur)?",
                stufe_bei_ja=3,
            ),
            Frage(
                "1d",
                "Interagiert das System unmittelbar mit natuerlichen Personen oder "
                "erzeugt es Inhalte, die als menschlich erscheinen koennen?",
                stufe_bei_ja=2,
            ),
        ),
    ),
    Themenblock(
        Block.DS,
        "Datenschutz",
        (
            Frage(
                "2a",
                "Werden besondere Kategorien personenbezogener Daten (Art. 9 DSGVO) "
                "verarbeitet oder findet Profilbildung statt?",
                stufe_bei_ja=3,
            ),
            Frage("2b", "Werden personenbezogene Daten verarbeitet?", stufe_bei_ja=2),
            Frage(
                "2c",
                "Werden pseudonymisierte oder personenbeziehbare Daten verarbeitet?",
                stufe_bei_ja=1,
            ),
        ),
    ),
    Themenblock(
        Block.MB,
        "Mitbestimmung",
        (
            Frage(
                "3a",
                "Ist eine Verhaltens- oder Leistungskontrolle von Beschaeftigten moeglich?",
                stufe_bei_ja=3,
            ),
            Frage("3b", "Werden mitarbeiterbezogene Daten verarbeitet?", stufe_bei_ja=2),
            Frage(
                "3c",
                "Veraendert der Prozess den Arbeitsablauf von Beschaeftigten spuerbar?",
                stufe_bei_ja=1,
            ),
        ),
    ),
    Themenblock(
        Block.IT,
        "IT-Sicherheit",
        (
            Frage(
                "4a",
                "Greift der Prozess schreibend auf produktive Kernsysteme oder auf "
                "Unternehmensdaten zu?",
                stufe_bei_ja=3,
            ),
            Frage(
                "4b",
                "Werden vertrauliche Daten verarbeitet oder besteht eine "
                "Schnittstelle nach ausserhalb des Unternehmens?",
                stufe_bei_ja=2,
            ),
            Frage(
                "4c",
                "Werden ausschliesslich interne, nicht vertrauliche Daten verarbeitet?",
                stufe_bei_ja=1,
            ),
        ),
    ),
    Themenblock(
        Block.RG,
        "Regulatorik",
        (
            Frage(
                "5a",
                "Ist der Prozess rechnungslegungs-, steuer- oder aufsichtsrelevant?",
                stufe_bei_ja=3,
            ),
            Frage(
                "5b",
                "Entstehen dokumentations- oder aufbewahrungspflichtige Ergebnisse?",
                stufe_bei_ja=2,
            ),
            Frage(
                "5c",
                "Besteht eine sonstige regulatorische Beruehrung?",
                stufe_bei_ja=1,
            ),
        ),
    ),
    Themenblock(
        Block.UR,
        "Unternehmerisches Risiko",
        (
            Frage(
                "6a",
                "Gefaehrdet ein Ausfall den Geschaeftsbetrieb oder wesentliche Umsaetze?",
                stufe_bei_ja=3,
            ),
            Frage(
                "6b",
                "Fuehrt ein Ausfall zu einer spuerbaren Beeintraechtigung?",
                stufe_bei_ja=2,
            ),
            Frage("6c", "Fuehrt ein Ausfall zu einer geringen Beeintraechtigung?", stufe_bei_ja=1),
        ),
    ),
)

BLOCK_REIHENFOLGE: tuple[Block, ...] = tuple(b.block for b in BAUM)
FRAGE_JE_ID: dict[str, Frage] = {f.id: f for b in BAUM for f in b.fragen}
BLOCK_JE_FRAGE: dict[str, Block] = {f.id: b.block for b in BAUM for f in b.fragen}
