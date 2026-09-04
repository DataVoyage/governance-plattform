"""Der Datenbestand als Integrationstest.

``app.bestand`` baut den Bestand ausschliesslich ueber die Fachlogik auf — mit
Berechtigungspruefung, Torwaechtern und Vorschlagsabgleich. Damit ist ein
gelungener Aufbau die schaerfste Aussage, die diese Testsuite ueber das
Zusammenspiel der Module treffen kann: er faehrt den vollstaendigen
Lebenszyklus von der Organisation bis zum Lenkungsvorgang, siebzig Mal.

Geprueft wird deshalb nicht nur, **dass** er laeuft, sondern dass er die
Zustaende erzeugt, um derentwillen es ihn gibt: jede Cockpit-Zeile mit Inhalt,
jede Aufzaehlung des Modells belegt, und eine Zeitachse, die diesen Namen
verdient.
"""

from __future__ import annotations

import os
from collections import Counter
from collections.abc import Iterator
from datetime import datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.deps import lade_principal
from app.bestand.aufbau import baue, ist_leer
from app.models.audit import ChangeLog
from app.models.enums import (
    Ausfuehrungsidentitaet,
    ComplianceFarbe,
    Gate2Ausloeser,
    GateStatus,
    Herkunft,
    Kundenkreis,
    Lauftyp,
    ProzessStatus,
    Reichweite,
    Rolle,
    Schicht2Verbot,
    Zugriffsart,
)
from app.models.governance import (
    Alarm,
    Benachrichtigung,
    Bewertung,
    Datenobjekt,
    GateVorgang,
    Lenkungsvorgang,
    Prozessobjekt,
    ToolDatenobjekt,
    ToolObjekt,
)
from app.models.organisation import Rollenzuweisung, User
from app.services import cockpit, erinnerung, klassen, lenkung, rahmen
from app.services import prozess as prozess_service

#: Die Zeile liefert ausschliesslich ein Aggregat und nie einzelne Eintraege.
NUR_AGGREGAT = {"tier_verteilung"}


@pytest.fixture(scope="module")
def bestand(schema: str, leer_anweisung: str) -> Iterator[Session]:
    """Baut den Bestand einmal je Modul auf und gibt die Sitzung zurueck.

    Eigene Einrichtung statt der ueblichen ``db``-Fixture: die raeumt je Test
    auf, und dieser Aufbau dauert Sekunden. Alle Zusicherungen lesen denselben
    Stand, keine schreibt.
    """
    from app.config import get_settings
    from app.db import get_engine, get_sessionmaker, reset_engine

    vorher = os.environ.get("GP_DATABASE_URL")
    os.environ["GP_DATABASE_URL"] = schema
    get_settings.cache_clear()
    reset_engine()
    with get_engine().begin() as verbindung:
        verbindung.execute(text(leer_anweisung))

    sitzung = get_sessionmaker()()
    baue(sitzung, heute=datetime.fromisoformat("2026-06-15T00:00:00+00:00"))
    sitzung.commit()
    try:
        yield sitzung
    finally:
        sitzung.close()
        if vorher is None:
            os.environ.pop("GP_DATABASE_URL", None)
        else:
            os.environ["GP_DATABASE_URL"] = vorher
        get_settings.cache_clear()
        reset_engine()


def test_aufbau_faehrt_durch(bestand: Session) -> None:
    """Der Aufbau laeuft ohne Verstoss gegen eine einzige Regel durch."""
    assert not ist_leer(bestand)
    assert bestand.execute(select(Prozessobjekt)).scalars().all()


def test_jede_cockpit_zeile_hat_inhalt(bestand: Session) -> None:
    """Ein Cockpit mit leeren Zeilen sagt ueber die Anwendung nichts aus."""
    governance = _governance(bestand)
    leer = [
        zeile.schluessel
        for zeile in cockpit.uebersicht(bestand, governance)
        if zeile.anzahl == 0 and zeile.schluessel not in NUR_AGGREGAT
    ]
    assert leer == [], f"Cockpit-Zeilen ohne Inhalt: {leer}"


def test_tier_verteilung_traegt_ihr_aggregat(bestand: Session) -> None:
    zeile = cockpit.hole_zeile(bestand, _governance(bestand), "tier_verteilung")
    assert zeile.aggregat is not None
    assert len(zeile.aggregat["je_technologie"]) >= 4
    # Eine Zeitreihe, die diesen Namen verdient: mehr als ein Jahr in Monaten.
    assert len(zeile.aggregat["je_monat"]) >= 12


def test_alle_prozessstatus_kommen_vor(bestand: Session) -> None:
    vorhanden = {p.status for p in bestand.execute(select(Prozessobjekt)).scalars()}
    assert vorhanden == set(ProzessStatus)


def test_alle_tier_stufen_kommen_vor(bestand: Session) -> None:
    stufen = Counter(
        bewertung.tier
        for p in bestand.execute(select(Prozessobjekt)).scalars()
        if (bewertung := prozess_service.neueste_bewertung(p)) is not None
    )
    assert set(stufen) == {1, 2, 3}
    assert min(stufen.values()) >= 5, f"zu einseitig verteilt: {dict(stufen)}"


def test_alle_datenkategorien_und_die_luecke(bestand: Session) -> None:
    kategorien = Counter(d.kategorie for d in bestand.execute(select(Datenobjekt)).scalars())
    assert len(kategorien) == 6, "fuenf Kategorien aus A.7 plus die ohne Einordnung"
    assert kategorien[None] >= 5


def test_alle_gate_status_und_alle_ausloeser(bestand: Session) -> None:
    vorgaenge = list(bestand.execute(select(GateVorgang)).scalars())
    assert {v.status for v in vorgaenge} == set(GateStatus)
    assert {v.ausloeser for v in vorgaenge if v.ausloeser} == set(Gate2Ausloeser)


def test_alle_compliance_farben_und_eskalationsstufen(bestand: Session) -> None:
    """Die Farbe wird gerechnet, nicht gemeldet (E-64).

    Geprueft wird deshalb, was die Anwendung ueber ihre Werkzeuge sagt. In der
    Zeitreihe kaeme Gelb nie vor: sie haelt fest, was gemeldet und wie
    geschlossen wurde, und „nicht zugeordnet" ist beides nicht.
    """
    from app.services import lenkung as lenkung_service

    farben = {
        lenkung_service.gemessene_farbe(bestand, werkzeug)
        for werkzeug in bestand.execute(select(ToolObjekt)).scalars()
    }
    assert farben == set(ComplianceFarbe)
    offen = {
        v.eskalationsstufe
        for v in bestand.execute(select(Lenkungsvorgang)).scalars()
        if v.status == "offen"
    }
    assert offen == {1, 2, 3}


def test_alle_sechs_verbote_der_schicht_zwei(bestand: Session) -> None:
    """Alle sechs stehen in den Daten der Werkzeuge (A.13.2, E-64).

    Vier misst die Anwendung, zwei erklaert der technische Owner am Werkzeug.
    Frueher war die zweite Haelfte nur eine Angabe in einer Meldung — und damit
    das einzige am Compliance-Modell, das sich nicht nachrechnen liess.
    """
    erkannt: set[str] = set()
    for tool in bestand.execute(select(ToolObjekt)).scalars():
        erkannt.update(rahmen.pruefe_schicht2(tool))
    assert erkannt == set(Schicht2Verbot)
    assert erkannt == set(rahmen.AUTOMATISCH_ERKENNBAR)

    # Und jedes davon steht auch an einem Vorgang: die Meldung uebernimmt es
    # aus der Messung, statt es erfragen zu muessen.
    an_vorgaengen = {
        v.schicht2_verbot
        for v in bestand.execute(select(Lenkungsvorgang)).scalars()
        if v.schicht2_verbot
    }
    assert an_vorgaengen


def test_jedes_rahmenelement_wird_irgendwo_verletzt(bestand: Session) -> None:
    """Sechs der sieben Elemente sind messbar — und jedes hat seinen Fall."""
    verletzt: set[str] = set()
    for tool in bestand.execute(select(ToolObjekt)).scalars():
        verletzt.update(rahmen.erlaubnisrahmen(bestand, tool).verletzte_elemente)
    messbar = {
        element.schluessel
        for element in rahmen.erlaubnisrahmen(
            bestand, bestand.execute(select(ToolObjekt)).scalars().first()
        ).elemente
        if element.messbar
    }
    assert verletzt == messbar, f"nie verletzt: {sorted(messbar - verletzt)}"


def test_jede_befundart_der_technologiematrix(bestand: Session) -> None:
    arten = Counter()
    for tool in bestand.execute(select(ToolObjekt)).scalars():
        for befund in klassen.pruefe_tool(bestand, tool).befunde:
            arten[befund.art] += 1
    assert set(arten) == set(klassen.Befundart)


def test_alle_lauftypen_und_identitaeten(bestand: Session) -> None:
    tools = list(bestand.execute(select(ToolObjekt)).scalars())
    assert {t.lauftyp for t in tools if t.lauftyp} == set(Lauftyp)
    assert {t.ausfuehrungsidentitaet for t in tools if t.ausfuehrungsidentitaet} == set(
        Ausfuehrungsidentitaet
    )
    assert {t.herkunft for t in tools} == set(Herkunft)


def test_alle_kundenkreise_reichweiten_und_zugriffsarten(bestand: Session) -> None:
    """Auch die Randfaelle: der persoenliche Kundenkreis, der reine Schreibzugriff."""
    prozesse = list(bestand.execute(select(Prozessobjekt)).scalars())
    assert {p.customer for p in prozesse} == set(Kundenkreis)
    assert {p.reichweite for p in prozesse} == set(Reichweite)
    kanten = bestand.execute(select(ToolDatenobjekt)).scalars()
    assert {k.zugriffsart for k in kanten} == set(Zugriffsart)


def test_jeder_benachrichtigungsanlass_kommt_vor(bestand: Session) -> None:
    """Erinnerung, Ueberfaelligkeit, Eroeffnung und Eskalation — alle vier."""
    anlaesse = {n.anlass for n in bestand.execute(select(Benachrichtigung)).scalars()}
    assert anlaesse == {
        erinnerung.ANLASS_ERINNERUNG,
        erinnerung.ANLASS_UEBERFAELLIG,
        lenkung.ANLASS_LENKUNG_NEU,
        lenkung.ANLASS_ESKALATION,
    }


def test_alle_acht_rollen_sind_vergeben(bestand: Session) -> None:
    vergeben = {z.rolle for z in bestand.execute(select(Rollenzuweisung)).scalars()}
    assert vergeben == set(Rolle)


def test_der_verbotstatbestand_hat_einen_alarm_und_keine_bewertung(bestand: Session) -> None:
    alarm = bestand.execute(select(Alarm)).scalars().one()
    prozess = bestand.get(Prozessobjekt, alarm.prozessobjekt_id)
    assert prozess is not None
    assert prozess_service.neueste_bewertung(prozess) is None
    assert prozess.status == ProzessStatus.ENTWURF


def test_das_protokoll_ist_chronologisch(bestand: Session) -> None:
    """Der Cursor steigt mit der Zeit — sonst waere der Nachweis unlesbar."""
    eintraege = list(bestand.execute(select(ChangeLog).order_by(ChangeLog.cursor)).scalars())
    assert len(eintraege) > 800
    rueckspruenge = [
        (a.cursor, b.cursor)
        for a, b in zip(eintraege, eintraege[1:], strict=False)
        if a.zeitpunkt > b.zeitpunkt
    ]
    assert rueckspruenge == []
    spanne = eintraege[-1].zeitpunkt - eintraege[0].zeitpunkt
    assert spanne.days > 600, "die Zeitachse ist zu kurz fuer eine Historie"


def test_jede_bewertung_haengt_an_einer_person(bestand: Session) -> None:
    """Kein Datensatz ohne Akteur — sonst ist der Nachweis wertlos."""
    for bewertung in bestand.execute(select(Bewertung)).scalars():
        assert bestand.get(User, bewertung.bewertet_von) is not None
    # Ohne Person geht nur, was kein Mensch getan hat: der geplante Lauf. Er
    # muss sich dann aber benennen, sonst steht im Nachweis nur „System".
    namenlos = [
        eintrag.entity_type
        for eintrag in bestand.execute(select(ChangeLog)).scalars()
        if eintrag.akteur_user_id is None and not eintrag.akteur_beschreibung
    ]
    assert namenlos == []


def _governance(db: Session):
    nutzer = db.execute(select(User).where(User.subject == "andrea.wilms")).scalar_one()
    return lade_principal(db, nutzer)
