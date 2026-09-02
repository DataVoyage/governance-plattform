"""Erlaubnisrahmen nach Leitdokument A.13.2 — Schicht 1 und Schicht 2.

Der Rahmen sagt, was ein Tool-Objekt darf. Er wird **abgeleitet**, nicht
eingegeben: jedes seiner sieben Elemente stammt aus den Prozessobjekten, an
denen das Tool haengt, oder aus den Attestierungen nach A.6. Es gilt das
Positivlistenprinzip — was nicht ausdruecklich erlaubt ist, ist nicht erlaubt.

Neben jedes erlaubte Element stellt dieses Modul das **gemessene**: was am Tool
tatsaechlich erfasst ist. Erst beide nebeneinander machen aus einer Behauptung
eine pruefbare Aussage. Sechs der sieben Elemente haben ein solches Gegenstueck;
die Reichweite hat keines, weil sie in dieser Anwendung abgeleitet und nirgends
beobachtet wird. Das steht so in der Antwort, statt eine Messung vorzutaeuschen.

**Schicht 2** ist etwas anderes als eine Rahmenueberschreitung. Es sind sechs
organisationsweite Verbote, die durch keine Prozessbewertung freischaltbar
sind. Deshalb entfaellt bei ihnen die erste Eskalationsstufe (A.13.5) — es gibt
nichts zu klaeren, nur abzustellen.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.enums import (
    DATENKATEGORIE_ORDNUNG,
    SCHREIBENDE_ZUGRIFFSARTEN,
    Ausfuehrungsidentitaet,
    Lauftyp,
    Schicht2Verbot,
    Zugriffsart,
)
from app.models.governance import Datenobjekt, ToolObjekt
from app.services.asset import datenobjekte_eines_tools, erbe_klassifikation

#: Die sieben Elemente aus A.13.2 Schicht 1, in der Reihenfolge des Dokuments.
ELEMENTE: tuple[str, ...] = (
    "datenobjekte",
    "datenkategorie",
    "reichweite",
    "externe_ziele",
    "zugriffsart",
    "ausfuehrungsart",
    "ausfuehrungsidentitaet",
)


@dataclass(frozen=True)
class Element:
    """Ein Rahmenelement: was erlaubt ist, was gemessen wurde, was abweicht.

    ``erlaubt`` und ``gemessen`` sind bewusst Listen von Zeichenketten, auch wo
    fachlich ein einzelner Wert steht: die Oberflaeche stellt sie
    nebeneinander, und ein einheitlicher Aufbau erspart ihr sieben Sonderfaelle.
    ``abweichung`` nennt genau das, was gemessen wurde und nicht erlaubt ist.
    """

    schluessel: str
    erlaubt: tuple[str, ...] = ()
    gemessen: tuple[str, ...] = ()
    abweichung: tuple[str, ...] = ()
    #: Falsch, wo es zu diesem Element keine Messung gibt (Reichweite).
    messbar: bool = True

    @property
    def eingehalten(self) -> bool:
        return not self.abweichung


@dataclass
class Rahmen:
    """Der vollstaendige Rahmen eines Tool-Objekts."""

    elemente: list[Element] = field(default_factory=list)
    tier: int | None = None
    quelle_prozess_ids: list[uuid.UUID] = field(default_factory=list)

    def element(self, schluessel: str) -> Element:
        for eintrag in self.elemente:
            if eintrag.schluessel == schluessel:
                return eintrag
        raise KeyError(f"Unbekanntes Rahmenelement: {schluessel}")

    @property
    def eingehalten(self) -> bool:
        return all(eintrag.eingehalten for eintrag in self.elemente)

    @property
    def verletzte_elemente(self) -> list[str]:
        return [e.schluessel for e in self.elemente if not e.eingehalten]


def _hoechste_kategorie(kategorien: set[str]) -> str | None:
    bekannt = [k for k in kategorien if k in DATENKATEGORIE_ORDNUNG]
    if not bekannt:
        return None
    return max(bekannt, key=lambda k: DATENKATEGORIE_ORDNUNG[k])


def _erlaubte_lauftypen(tool: ToolObjekt) -> tuple[str, ...]:
    """Element 6: die erlaubte Ausfuehrungsart, zurueckgefuehrt auf A.6.

    Steht ein Mensch zwischen Output und Wirkung, ist jede Ausfuehrungsart im
    Rahmen — jemand sieht das Ergebnis, bevor es wirkt. Steht keiner dazwischen,
    bleibt nur die interaktive Ausfuehrung: ein Lauf ohne Anwesenden waere ein
    Tool, das allein handelt. Ohne Attestierung 2 ist ueberhaupt nichts gedeckt,
    weil nichts erklaert wurde.
    """
    if tool.attest_mensch_dazwischen is True:
        return (Lauftyp.INTERAKTIV, Lauftyp.GETRIGGERT, Lauftyp.GEPLANT)
    if tool.attest_mensch_dazwischen is False:
        return (Lauftyp.INTERAKTIV,)
    return ()


def _erlaubte_identitaeten(tool: ToolObjekt) -> tuple[str, ...]:
    """Element 7: unter welcher Identitaet das Tool laufen darf.

    Interaktiv heisst: ein Mensch bedient, also laeuft es unter dessen
    Identitaet. Getriggert oder geplant heisst: niemand ist da, der eine
    Identitaet leihen koennte — dann ist eine benannte Dienstidentitaet die
    einzige Moeglichkeit, die spaeter noch jemandem zuzuordnen ist. Ein
    geteiltes Konto ist in keinem Fall erlaubt; das verbietet Schicht 2.
    """
    if tool.lauftyp == Lauftyp.INTERAKTIV:
        return (Ausfuehrungsidentitaet.PERSOENLICH,)
    if tool.lauftyp in (Lauftyp.GETRIGGERT, Lauftyp.GEPLANT):
        return (Ausfuehrungsidentitaet.BENANNTER_DIENST,)
    return (Ausfuehrungsidentitaet.PERSOENLICH, Ausfuehrungsidentitaet.BENANNTER_DIENST)


def erlaubnisrahmen(db: Session, tool: ToolObjekt) -> Rahmen:
    """Die sieben Elemente aus A.13.2 Schicht 1, je mit ihrer Messung."""
    erlaubte_objekte: dict[uuid.UUID, str] = {}
    schreibbare: set[uuid.UUID] = set()
    erlaubte_kategorien: set[str] = set()
    erlaubte_ziele: list[str] = []
    for prozess in tool.prozessobjekte:
        for datenobjekt in [*prozess.input_datenobjekte, *prozess.output_datenobjekte]:
            erlaubte_objekte[datenobjekt.id] = datenobjekt.name
            if datenobjekt.kategorie is not None:
                erlaubte_kategorien.add(datenobjekt.kategorie)
        # A.4.1: die Output-Kante ist die Schreibkante. Schreiben darf ein Tool
        # nur dort, wo der Prozess das Datenobjekt als Ergebnis fuehrt.
        for datenobjekt in prozess.output_datenobjekte:
            schreibbare.add(datenobjekt.id)
        for ziel in prozess.erlaubte_externe_ziele or []:
            if ziel not in erlaubte_ziele:
                erlaubte_ziele.append(ziel)

    kanten = datenobjekte_eines_tools(db, tool.id)
    genutzte: dict[uuid.UUID, Zugriffsart] = {k.datenobjekt_id: k.zugriffsart for k in kanten}
    namen = dict(erlaubte_objekte)
    gemessene_kategorien: set[str] = set()
    for kennung in genutzte:
        # Ausdruecklich aus der Datenbank, nicht aus den Prozesskanten: die
        # Objekte ausserhalb des Rahmens sind gerade die interessanten.
        objekt = db.get(Datenobjekt, kennung)
        if objekt is None:
            continue
        namen.setdefault(objekt.id, objekt.name)
        if objekt.kategorie is not None:
            gemessene_kategorien.add(objekt.kategorie)

    geerbt = erbe_klassifikation(tool)
    obergrenze = _hoechste_kategorie(erlaubte_kategorien)
    gemessene_grenze = _hoechste_kategorie(gemessene_kategorien)
    gemessene_ziele = tuple(sorted(tool.externe_ziele or []))
    erlaubte_lauftypen = _erlaubte_lauftypen(tool)
    erlaubte_identitaeten = _erlaubte_identitaeten(tool)

    schreibend_erlaubt = bool(schreibbare)
    schreibend_gemessen = any(art in SCHREIBENDE_ZUGRIFFSARTEN for art in genutzte.values())
    unerlaubt_schreibend = sorted(
        namen.get(kennung, str(kennung))
        for kennung, art in genutzte.items()
        if art in SCHREIBENDE_ZUGRIFFSARTEN and kennung not in schreibbare
    )

    elemente = [
        Element(
            schluessel="datenobjekte",
            erlaubt=tuple(sorted(erlaubte_objekte.values())),
            gemessen=tuple(sorted(namen.get(k, str(k)) for k in genutzte)),
            abweichung=tuple(
                sorted(namen.get(k, str(k)) for k in genutzte if k not in erlaubte_objekte)
            ),
        ),
        Element(
            schluessel="datenkategorie",
            erlaubt=() if obergrenze is None else (obergrenze,),
            gemessen=() if gemessene_grenze is None else (gemessene_grenze,),
            abweichung=(
                (gemessene_grenze,)
                if gemessene_grenze is not None
                and (
                    obergrenze is None
                    or DATENKATEGORIE_ORDNUNG[gemessene_grenze] > DATENKATEGORIE_ORDNUNG[obergrenze]
                )
                else ()
            ),
        ),
        # Die Reichweite ist nach A.4.4 geerbt und nach P1 nie eingegeben — es
        # gibt am Tool nichts, wogegen sie zu pruefen waere.
        Element(
            schluessel="reichweite",
            erlaubt=() if geerbt.reichweite is None else (geerbt.reichweite,),
            messbar=False,
        ),
        Element(
            schluessel="externe_ziele",
            erlaubt=tuple(sorted(erlaubte_ziele)),
            gemessen=gemessene_ziele,
            abweichung=tuple(ziel for ziel in gemessene_ziele if ziel not in erlaubte_ziele),
        ),
        Element(
            schluessel="zugriffsart",
            erlaubt=(
                (Zugriffsart.LESEN_SCHREIBEN,) if schreibend_erlaubt else (Zugriffsart.LESEN,)
            ),
            gemessen=(
                (Zugriffsart.LESEN_SCHREIBEN,)
                if schreibend_gemessen
                else ((Zugriffsart.LESEN,) if genutzte else ())
            ),
            abweichung=tuple(unerlaubt_schreibend),
        ),
        Element(
            schluessel="ausfuehrungsart",
            erlaubt=erlaubte_lauftypen,
            gemessen=() if tool.lauftyp is None else (tool.lauftyp,),
            abweichung=(
                (tool.lauftyp,)
                if tool.lauftyp is not None and tool.lauftyp not in erlaubte_lauftypen
                else ()
            ),
        ),
        Element(
            schluessel="ausfuehrungsidentitaet",
            erlaubt=erlaubte_identitaeten,
            gemessen=(
                () if tool.ausfuehrungsidentitaet is None else (tool.ausfuehrungsidentitaet,)
            ),
            abweichung=(
                (tool.ausfuehrungsidentitaet,)
                if tool.ausfuehrungsidentitaet is not None
                and tool.ausfuehrungsidentitaet not in erlaubte_identitaeten
                else ()
            ),
        ),
    ]
    return Rahmen(
        elemente=elemente,
        tier=geerbt.tier,
        quelle_prozess_ids=list(geerbt.quelle_prozess_ids),
    )


# --- Schicht 2 (Leitdokument A.13.2) -------------------------------------

#: Die Verbote, die diese Anwendung aus vorhandenen Daten selbst erkennt. Die
#: uebrigen beiden sind zu melden — sie betreffen Vorgaenge in der Zielplattform,
#: von denen die Governance-Plattform nichts sieht.
AUTOMATISCH_ERKENNBAR: frozenset[str] = frozenset(
    {
        Schicht2Verbot.IDENTITAET_UMGANGEN,
        Schicht2Verbot.STATISCHE_ZUGANGSDATEN,
        Schicht2Verbot.UNDEKLARIERTE_QUELLEN,
        Schicht2Verbot.ENTSCHEIDUNG_OHNE_MENSCH,
    }
)


def pruefe_schicht2(tool: ToolObjekt) -> list[Schicht2Verbot]:
    """Welche der sechs Verbote die erfassten Daten selbst belegen.

    Die Liste ist nicht die Wahrheit ueber das Tool, sondern das, was ohne
    Meldung erkennbar ist. Wer eine Umgehung der Protokollierung sucht, findet
    sie hier nicht — dafuer gibt es die Meldung. Was die Anwendung aber sieht,
    soll sie auch sagen, statt auf jemanden zu warten.
    """
    verstoesse: list[Schicht2Verbot] = []
    if tool.ausfuehrungsidentitaet == Ausfuehrungsidentitaet.GETEILTES_KONTO:
        verstoesse.append(Schicht2Verbot.IDENTITAET_UMGANGEN)
    if tool.statische_zugangsdaten is True:
        verstoesse.append(Schicht2Verbot.STATISCHE_ZUGANGSDATEN)
    if tool.attest_undeklarierte_quellen is True:
        verstoesse.append(Schicht2Verbot.UNDEKLARIERTE_QUELLEN)
    if tool.attest_entscheidung_ueber_personen is True and tool.attest_mensch_dazwischen is False:
        verstoesse.append(Schicht2Verbot.ENTSCHEIDUNG_OHNE_MENSCH)
    return verstoesse
