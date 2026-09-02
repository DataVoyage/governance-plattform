"""Serverseitige Ableitungen am Prozessobjekt (Leitdokument P1, Architektur 8.1).

Reichweite, Kritikalitaet und Mitbestimmungsflag werden nicht abgefragt,
sondern aus vorhandenen Daten berechnet. Die Regeln liegen hier in der
Geschaeftslogik und nicht in der Oberflaeche, damit sie nicht versehentlich
durch eine UI-Aenderung verschoben werden koennen.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import (
    AUSFALLFOLGE_STUFE,
    KUNDENKREIS_ZU_REICHWEITE,
    LEISTUNGSDATEN_KATEGORIEN,
    MB_STUFE_ZURECHENBAR,
    PERSONENBEZOGENE_KATEGORIEN,
    REICHWEITE_ORDNUNG,
    Reichweite,
)
from app.models.governance import Datenobjekt, Prozessobjekt


@dataclass(frozen=True)
class Datenlage:
    """Die Datenobjekte eines Prozesses aus Sicht der Ableitung."""

    objekte: list[Datenobjekt] = field(default_factory=list)
    ohne_kategorie: list[Datenobjekt] = field(default_factory=list)
    kategorien: set[str] = field(default_factory=set)

    @property
    def vollstaendig(self) -> bool:
        """Wahr, wenn ueberhaupt Objekte da sind und alle eingeordnet sind."""
        return bool(self.objekte) and not self.ohne_kategorie


def leite_reichweite_ab(prozess: Prozessobjekt) -> Reichweite:
    """Reichweite aus Kundenkreis, angehoben durch die Zahl der Umsetzungen.

    Ein Prozess, der in mehr als einer Landesorganisation umgesetzt wird,
    wirkt mindestens unternehmensweit — unabhaengig davon, wie eng der
    Kundenkreis lokal beschrieben ist.
    """
    basis = KUNDENKREIS_ZU_REICHWEITE[prozess.customer]
    if (
        len(prozess.umsetzungen) > 1
        and REICHWEITE_ORDNUNG[basis] < REICHWEITE_ORDNUNG[Reichweite.UNTERNEHMEN]
    ):
        return Reichweite.UNTERNEHMEN
    return basis


def leite_kritikalitaet_ab(prozess: Prozessobjekt, *, _besucht: set | None = None) -> int:
    """Eigene Ausfallfolge, angehoben auf das Maximum der Prozesskette (A.4.2).

    Wer einen kritischen Nachfolgeprozess speist, ist selbst mindestens so
    kritisch wie dieser. Die Rekursion ist gegen Zyklen abgesichert, weil die
    Kette fachlich zwar azyklisch gemeint, technisch aber n:m ist.
    """
    besucht = _besucht if _besucht is not None else set()
    if prozess.id in besucht:
        return AUSFALLFOLGE_STUFE[prozess.ausfallfolge]
    besucht.add(prozess.id)
    stufe = AUSFALLFOLGE_STUFE[prozess.ausfallfolge]
    for nachfolger in prozess.nachgelagert:
        stufe = max(stufe, leite_kritikalitaet_ab(nachfolger, _besucht=besucht))
    return stufe


def kritikalitaetsquelle(prozess: Prozessobjekt) -> tuple[int, Prozessobjekt | None]:
    """Die Kritikalitaet samt dem Prozess, aus dem sie stammt.

    Ist die zweite Stelle ``None``, traegt der Prozess seine Stufe selbst.
    Andernfalls ist es der nachgelagerte Prozess, der sie nach A.4.2 anhebt —
    genau die Angabe, die ein Vorschlag nennen muss, damit man ihn pruefen kann.
    """
    stufe = leite_kritikalitaet_ab(prozess)
    if stufe <= AUSFALLFOLGE_STUFE[prozess.ausfallfolge]:
        return stufe, None
    for nachfolger in prozess.nachgelagert:
        if leite_kritikalitaet_ab(nachfolger) >= stufe:
            return stufe, nachfolger
    return stufe, None


def datenlage(prozess: Prozessobjekt) -> Datenlage:
    """Die Datenkategorien am Prozess, samt der Frage, ob sie vollstaendig sind.

    Ein nicht kategorisiertes Datenobjekt macht die Lage unvollstaendig. Das
    ist fuer den Vorschlagsdienst der entscheidende Unterschied: aus einer
    vollstaendigen Lage darf ein „nein" abgeleitet werden, aus einer
    unvollstaendigen nicht — ein noch nicht eingeordnetes Objekt kann alles
    sein.
    """
    objekte = [*prozess.input_datenobjekte, *prozess.output_datenobjekte]
    return Datenlage(
        objekte=objekte,
        ohne_kategorie=[o for o in objekte if o.kategorie is None],
        kategorien={o.kategorie for o in objekte if o.kategorie is not None},
    )


def mitbestimmung_aus_daten(prozess: Prozessobjekt) -> bool | None:
    """Die Konjunktion aus A.5, soweit die vorhandenen Daten sie hergeben.

    Liefert ``True``/``False``, wenn die Datenlage entscheidet, und ``None``,
    wenn sie es nicht tut — etwa bei Personenbezug ohne Leistungsdaten und ohne
    Attestierung: dann kann eine Verhaltens- oder Leistungskontrolle vorliegen
    oder eben nicht, und nur der Prozesseigner weiss es.

    Diese Funktion kennt bewusst **keine** Bewertung. Sie ist die Grundlage des
    Vorschlagsdienstes, und ein Vorschlag, der die letzte Antwort auf dieselbe
    Frage zitiert, waere ein Zirkelschluss statt einer Ableitung.
    """
    lage = datenlage(prozess)
    if lage.kategorien & LEISTUNGSDATEN_KATEGORIEN:
        return True
    if not lage.kategorien & PERSONENBEZOGENE_KATEGORIEN:
        # Ohne Personenbezug greift die Konjunktion nicht — aber das gilt nur
        # bei geschlossener Datenlage. Ein Prozess ganz ohne Datenobjekt und
        # einer mit einem noch nicht eingeordneten sagen beide nichts aus.
        return False if lage.vollstaendig else None
    if any(tool.attest_entscheidung_ueber_personen for tool in prozess.tool_objekte):
        return True
    return None


def leite_mitbestimmung_ab(prozess: Prozessobjekt) -> bool:
    """Personenbezug **und** (Wirkung auf Einzelne oder Leistungsdaten).

    Die Regel steht so im Leitdokument A.5 und ist bewusst eine Konjunktion:
    Personenbezug allein macht einen Prozess nicht mitbestimmungspflichtig,
    und eine Wirkung auf Beschaeftigte ohne Personenbezug gibt es nicht.

    Die zweite Haelfte hat drei Quellen. Die besondere Datenkategorie schliesst
    nach A.7 Entgelt, Gesundheit und Leistungsbewertung ein — das sind
    Leistungs- und Verhaltensdaten. Ein verknuepftes Tool-Objekt kann nach A.6
    erklaert haben, dass sein Ergebnis in eine Entscheidung ueber einzelne
    Personen fliesst; das ist die Wirkung auf Einzelne, unmittelbar erklaert.
    Und unabhaengig davon erklaert die Bewertung in der Dimension MB ab Stufe 2,
    dass das Ergebnis einzelnen Beschaeftigten zurechenbar ist (A.8.3).
    """
    aus_daten = mitbestimmung_aus_daten(prozess)
    if aus_daten is not None:
        return aus_daten
    lage = datenlage(prozess)
    if not lage.kategorien & PERSONENBEZOGENE_KATEGORIEN:
        return False
    if prozess.bewertungen:
        neueste = max(prozess.bewertungen, key=lambda b: b.bewertet_am)
        return neueste.mb_stufe >= MB_STUFE_ZURECHENBAR
    return False


def aktualisiere_ableitungen(prozess: Prozessobjekt) -> None:
    """Setzt alle abgeleiteten Felder eines Prozessobjekts neu."""
    prozess.reichweite = leite_reichweite_ab(prozess)
    prozess.kritikalitaet = leite_kritikalitaet_ab(prozess)
    prozess.mitbestimmung_flag = leite_mitbestimmung_ab(prozess)


def aktualisiere_kette(prozess: Prozessobjekt) -> list[Prozessobjekt]:
    """Aktualisiert den Prozess und alle transitiven Vorgaenger.

    Eine geaenderte Ausfallfolge wirkt entlang der Kette nach oben; ohne diese
    Nachfuehrung waere die Kritikalitaet eines Vorgaengers nach einer Aenderung
    still veraltet.
    """
    betroffen: dict = {}
    stapel = [prozess]
    while stapel:
        aktuell = stapel.pop()
        if aktuell.id in betroffen:
            continue
        betroffen[aktuell.id] = aktuell
        stapel.extend(aktuell.vorgelagert)
    for objekt in betroffen.values():
        aktualisiere_ableitungen(objekt)
    return list(betroffen.values())
