"""Serverseitige Ableitungen am Prozessobjekt (Leitdokument P1, Architektur 8.1).

Reichweite, Kritikalitaet und Mitbestimmungsflag werden nicht abgefragt,
sondern aus vorhandenen Daten berechnet. Die Regeln liegen hier in der
Geschaeftslogik und nicht in der Oberflaeche, damit sie nicht versehentlich
durch eine UI-Aenderung verschoben werden koennen.
"""

from __future__ import annotations

from app.models.enums import (
    AUSFALLFOLGE_STUFE,
    KUNDENKREIS_ZU_REICHWEITE,
    MITBESTIMMUNGSRELEVANTE_KATEGORIEN,
    REICHWEITE_ORDNUNG,
    Reichweite,
)
from app.models.governance import Prozessobjekt


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


def leite_mitbestimmung_ab(prozess: Prozessobjekt) -> bool:
    """Mitbestimmung greift, sobald mitarbeiterbezogene Daten beteiligt sind.

    Ergaenzend setzt eine Bewertung mit Mitbestimmungsstufe > 0 das Flag —
    dieser Weg traegt ab Phase 2, der Datenobjektweg schon ab Phase 3.
    """
    for datenobjekt in [*prozess.input_datenobjekte, *prozess.output_datenobjekte]:
        if datenobjekt.kategorie in MITBESTIMMUNGSRELEVANTE_KATEGORIEN:
            return True
    if prozess.bewertungen:
        neueste = max(prozess.bewertungen, key=lambda b: b.bewertet_am)
        if neueste.mb_stufe > 0:
            return True
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
