"""Der kleine Bestand — die Zusage lautet: alles einmal, nichts zweimal.

Diese Datei prüft genau das. Sie ist nicht dazu da, den Aufbau abzusichern —
das tut er selbst, indem er ausschließlich über die Dienstschicht schreibt und
bei jeder verletzten Regel laut scheitert. Sie prüft die **Vollständigkeit**:
dass jede Aufzählung, jeder Zustand und jede Cockpit-Zeile tatsächlich belegt
ist.

Ohne diese Prüfung wäre der Bestand nach der dritten Änderung wieder lückenhaft,
ohne dass es jemandem auffiele — und ein Bestand, der Vollständigkeit
behauptet und sie nicht hat, ist schlechter als einer, der nichts behauptet.
"""

from __future__ import annotations

from collections import Counter

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import lade_principal
from app.models.enums import (
    AssetStatus,
    Ausfallfolge,
    Datenkategorie,
    GateStatus,
    GateTyp,
    LenkungStatus,
    ProzessStatus,
    Reichweite,
    Rolle,
    ScopeTyp,
    SelbstverpflichtungTyp,
)
from app.models.governance import (
    Bewertung,
    ComplianceZustand,
    Datenobjekt,
    GateVorgang,
    Kompensation,
    Lenkungsvorgang,
    Prozessobjekt,
    Selbstverpflichtung,
    ToolObjekt,
)
from app.models.organisation import Rollenzuweisung, User
from app.services import cockpit, klassen
from app.services import lenkung as lenkung_service
from app.services import prozess as prozess_service
from app.services import rahmen as rahmen_service
from app.services.asset import erbe_klassifikation


@pytest.fixture(scope="module")
def lehrbestand(datenbank_url: str, schema: str, leer_anweisung: str):
    """Baut den kleinen Bestand einmal je Testlauf."""
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from app.lehrbestand.aufbau import baue

    engine = create_engine(datenbank_url, future=True)
    with engine.begin() as verbindung:
        verbindung.execute(text(leer_anweisung))
    fabrik = sessionmaker(bind=engine, future=True)
    with fabrik() as sitzung:
        baue(sitzung)
        yield sitzung


def _neueste(prozess: Prozessobjekt) -> Bewertung | None:
    return prozess_service.neueste_bewertung(prozess)


# --- Umfang: klein genug, um ihn zu überblicken ---------------------------


def test_der_bestand_bleibt_klein(lehrbestand: Session) -> None:
    """Die halbe Zusage ist „nichts zweimal" — sie ist eine Obergrenze.

    Wächst der Bestand über diese Zahlen, ist er kein Lehrbestand mehr. Dann
    gehört der neue Fall entweder in den grossen Bestand, oder ein alter muss
    weichen.
    """
    grenzen = {
        Prozessobjekt: 10,
        ToolObjekt: 8,
        Datenobjekt: 10,
        User: 14,
    }
    for modell, grenze in grenzen.items():
        anzahl = len(lehrbestand.execute(select(modell)).scalars().all())
        assert anzahl <= grenze, f"{modell.__name__}: {anzahl} > {grenze}"


# --- Vollständigkeit: jede Aufzählung einmal ------------------------------


def test_jeder_prozessstatus_kommt_vor(lehrbestand: Session) -> None:
    vorhanden = {p.status for p in lehrbestand.execute(select(Prozessobjekt)).scalars()}
    assert vorhanden == set(ProzessStatus)


def test_jede_tier_stufe_kommt_vor(lehrbestand: Session) -> None:
    tiers = {
        b.tier
        for p in lehrbestand.execute(select(Prozessobjekt)).scalars()
        if (b := _neueste(p)) is not None
    }
    assert tiers == {1, 2, 3}


def test_jede_reichweite_kommt_vor(lehrbestand: Session) -> None:
    """Alle fünf Stufen — die Ableitung aus dem Kundenkreis ist damit belegt."""
    vorhanden = {p.reichweite for p in lehrbestand.execute(select(Prozessobjekt)).scalars()}
    assert vorhanden == set(Reichweite)


def test_die_kritikalitaet_reicht_von_null_bis_drei(lehrbestand: Session) -> None:
    vorhanden = {p.kritikalitaet for p in lehrbestand.execute(select(Prozessobjekt)).scalars()}
    assert vorhanden == {0, 1, 2, 3}


def test_die_kette_hebt_das_vorderglied(lehrbestand: Session) -> None:
    """A.4.2, transitiv über zwei Kanten — der Fall, für den es die Kette gibt."""
    prozesse = {p.name: p for p in lehrbestand.execute(select(Prozessobjekt)).scalars()}
    vorn = next(p for name, p in prozesse.items() if name.startswith("Kette 1"))
    hinten = next(p for name, p in prozesse.items() if name.startswith("Kette 3"))
    assert hinten.ausfallfolge == Ausfallfolge.KRITISCH
    assert vorn.ausfallfolge == Ausfallfolge.GERING
    assert vorn.kritikalitaet == 3, "die Kritikalität muss über zwei Kanten durchschlagen"


def test_jede_datenkategorie_kommt_vor(lehrbestand: Session) -> None:
    """Die fünf aus A.7, dazu die Quelle ohne Einordnung."""
    vorhanden = {d.kategorie for d in lehrbestand.execute(select(Datenobjekt)).scalars()}
    assert set(Datenkategorie) <= vorhanden
    assert None in vorhanden, "eine Quelle ohne Kategorie gehört dazu"


def test_beide_asset_zustaende_kommen_vor(lehrbestand: Session) -> None:
    for modell in (Datenobjekt, ToolObjekt):
        vorhanden = {x.status for x in lehrbestand.execute(select(modell)).scalars()}
        assert AssetStatus.BESTAETIGT in vorhanden
        assert AssetStatus.IMPORTIERT_UNBESTAETIGT in vorhanden, modell.__name__


def test_jede_technologie_kommt_vor(lehrbestand: Session) -> None:
    vorhanden = {t.technologie for t in lehrbestand.execute(select(ToolObjekt)).scalars()}
    bekannt = {f.technologie for f in klassen.matrix(lehrbestand)}
    assert bekannt <= vorhanden, f"nicht belegt: {bekannt - vorhanden}"
    assert None in vorhanden, "ein Werkzeug ohne Technologie gehört dazu"


def test_jede_rolle_ist_einmal_vergeben(lehrbestand: Session) -> None:
    """Alle acht Rollen aus A.15, und beide Scope-Arten neben global."""
    zuweisungen = list(lehrbestand.execute(select(Rollenzuweisung)).scalars())
    assert {z.rolle for z in zuweisungen} == set(Rolle)
    assert {z.scope_typ for z in zuweisungen} == set(ScopeTyp)


def test_dieselbe_rolle_in_zwei_bereichen(lehrbestand: Session) -> None:
    """Der Fall, an dem sich P-App-3 zeigt — ohne ihn wäre die Regel unbelegt."""
    owner = [
        z
        for z in lehrbestand.execute(select(Rollenzuweisung)).scalars()
        if z.rolle == Rolle.PROZESS_OWNER
    ]
    arten = {z.scope_typ for z in owner}
    assert arten == {ScopeTyp.FACHBEREICH, ScopeTyp.ORGANISATIONSEINHEIT}


def test_beide_selbstverpflichtungen_kommen_vor(lehrbestand: Session) -> None:
    """A.10.2 und A.10.3 — die Erklärung des Eigners und die des Entwicklers."""
    vorhanden = {s.typ for s in lehrbestand.execute(select(Selbstverpflichtung)).scalars()}
    assert vorhanden == set(SelbstverpflichtungTyp)


def test_beide_gate_arten_und_beide_ausgaenge(lehrbestand: Session) -> None:
    vorgaenge = list(lehrbestand.execute(select(GateVorgang)).scalars())
    assert {v.gate_typ for v in vorgaenge} == set(GateTyp)
    ausgaenge = {v.status for v in vorgaenge}
    for erwartet in (GateStatus.EINGEREICHT, GateStatus.FREIGEGEBEN, GateStatus.ABGELEHNT):
        assert erwartet in ausgaenge, f"{erwartet} fehlt: {ausgaenge}"


def test_lenkung_offen_und_aufgeloest(lehrbestand: Session) -> None:
    """Beide Zustände — ein Vorgang ohne Ausgang sagt nichts über den Ausweg."""
    vorgaenge = list(lehrbestand.execute(select(Lenkungsvorgang)).scalars())
    assert {v.status for v in vorgaenge} >= {LenkungStatus.OFFEN, LenkungStatus.AUFGELOEST}


def test_compliance_gruen_und_rot(lehrbestand: Session) -> None:
    farben = {z.farbe for z in lehrbestand.execute(select(ComplianceZustand)).scalars()}
    assert {"gruen", "rot"} <= {str(f) for f in farben}


def test_eine_kompensation_ist_dokumentiert(lehrbestand: Session) -> None:
    """A.9.3: ein kompensierbarer Befund ohne Maßnahme bliebe offen."""
    assert lehrbestand.execute(select(Kompensation)).scalars().all()


# --- Der Erlaubnisrahmen: beide Seiten, beide Ausgänge --------------------


def test_rahmen_eingehalten_und_verletzt(lehrbestand: Session) -> None:
    """Ohne beide Fälle sagt der Abgleich nichts."""
    stände = {
        t.name: rahmen_service.erlaubnisrahmen(lehrbestand, t).eingehalten
        for t in lehrbestand.execute(select(ToolObjekt)).scalars()
        if t.prozessobjekte
    }
    assert True in stände.values(), "kein Werkzeug hält den Rahmen ein"
    assert False in stände.values(), "kein Werkzeug verletzt den Rahmen"


def test_ein_schicht_zwei_verstoss_ist_erfasst(lehrbestand: Session) -> None:
    """Vier der sechs Verbote erkennt die Anwendung selbst — eines muss vorkommen."""
    befunde = [
        rahmen_service.pruefe_schicht2(t) for t in lehrbestand.execute(select(ToolObjekt)).scalars()
    ]
    assert any(befunde), "kein Schicht-2-Verstoß im Bestand"


def test_ein_werkzeug_erbt_aus_zwei_prozessen(lehrbestand: Session) -> None:
    """Nur daran wird sichtbar, dass die Einstufung das Maximum ist (A.4.4)."""
    mehrfach = [
        t for t in lehrbestand.execute(select(ToolObjekt)).scalars() if len(t.prozessobjekte) > 1
    ]
    assert mehrfach, "kein Werkzeug an mehreren Prozessen"
    geerbt = erbe_klassifikation(mehrfach[0])
    assert any(b.massgeblich for b in geerbt.beitraege), "die maßgebliche Kante wird nicht benannt"


def test_ein_werkzeug_haengt_an_keinem_prozess(lehrbestand: Session) -> None:
    """Der gelbe Zustand aus A.13.3 — unbewertet, nicht regelwidrig."""
    ohne = [t for t in lehrbestand.execute(select(ToolObjekt)).scalars() if not t.prozessobjekte]
    assert ohne


# --- Das Cockpit: jede Zeile hat etwas zu zeigen --------------------------


def test_jede_cockpit_zeile_ist_belegt(lehrbestand: Session) -> None:
    """Die vierzehn Zeilen aus A.14 sind der Katalog der Governance-Zustände.

    Eine leere Zeile heißt: dieser Fall kommt im Bestand nicht vor, und wer
    ihn prüfen will, muss ihn sich von Hand bauen. Genau das soll dieser
    Bestand ersparen.
    """
    governance = lade_principal(
        lehrbestand,
        lehrbestand.execute(select(User).where(User.subject == "governance")).scalar_one(),
    )
    leer = []
    for schluessel, funktion in cockpit.ZEILEN.items():
        zeile = funktion(lehrbestand, governance)
        if not zeile.eintraege and not getattr(zeile, "aggregat", None):
            leer.append(schluessel)
    assert not leer, f"Cockpit-Zeilen ohne Inhalt: {leer}"


# --- Die Zugänge: der eigentliche Zweck ------------------------------------


def test_die_bereichsgebundenen_zugaenge_liegen_im_selben_fachbereich(
    lehrbestand: Session,
) -> None:
    """Sonst ließe sich nicht unterscheiden, woher ein Unterschied kommt.

    Verteilt man die Zugänge über mehrere Bereiche, sieht jeder etwas anderes —
    und ob das an der Rolle oder am Bereich liegt, ist nicht mehr zu sagen.
    """
    from app.lehrbestand.organisation import ZUGAENGE

    bereiche = {
        angabe.partition("@")[2]
        for _kennung, _name, rollen in ZUGAENGE
        for angabe in rollen
        if not angabe.endswith("@global") and not angabe.endswith("personal")
    }
    assert bereiche == {"fb:logistik", "oe:logistik-de"}, bereiche


def test_ein_prozess_traegt_keinen_aktiven_owner(lehrbestand: Session) -> None:
    """Der ausgeschiedene Eigner — die erste Zeile des Cockpits."""
    inaktive = {u.id for u in lehrbestand.execute(select(User)).scalars() if not u.ist_aktiv}
    assert inaktive, "niemand ist ausgeschieden"
    betroffen = [
        p
        for p in lehrbestand.execute(select(Prozessobjekt)).scalars()
        if p.owner_user_id in inaktive
    ]
    assert betroffen, "kein Prozessobjekt mit ausgeschiedenem Eigner"


def test_die_namen_sagen_wofuer_sie_da_sind(lehrbestand: Session) -> None:
    """Die bewusste Gegenentscheidung zum grossen Bestand.

    Dort heißt eine Quelle „Kassenjournal" und kein Datensatz verrät, dass er
    erfunden ist. Hier sagt jeder Name, welchen Fall er zeigt — sonst sucht man
    beim Prüfen erst, welches Objekt das interessante ist.
    """
    namen = [p.name for p in lehrbestand.execute(select(Prozessobjekt)).scalars()]
    sprechend = [n for n in namen if "—" in n]
    assert len(sprechend) == len(namen), f"ohne erklärenden Teil: {set(namen) - set(sprechend)}"


def test_die_verteilung_bleibt_ausgewogen(lehrbestand: Session) -> None:
    """Kein Fall doppelt: keine Kategorie stellt mehr als die Hälfte."""
    kategorien = Counter(d.kategorie for d in lehrbestand.execute(select(Datenobjekt)).scalars())
    haeufigste = max(kategorien.values())
    assert haeufigste <= len(list(kategorien.elements())) // 2, dict(kategorien)


# --- Jede Aufzählung, die einen Zustand trägt -----------------------------


def test_jede_aufzaehlung_ist_belegt(lehrbestand: Session) -> None:
    """Die eigentliche Zusage, in einer Tabelle.

    Was hier fehlt, kann in der Anwendung nicht angesehen werden, ohne dass
    man es sich von Hand baut — und genau das soll dieser Bestand ersparen.
    """
    from app.models import enums as e
    from app.models.governance import ToolDatenobjekt

    def werte(modell, spalte: str) -> set:
        return {getattr(x, spalte) for x in lehrbestand.execute(select(modell)).scalars()}

    pruefungen: list[tuple[str, type, set]] = [
        ("ProzessStatus", e.ProzessStatus, werte(Prozessobjekt, "status")),
        ("Ausfallfolge", e.Ausfallfolge, werte(Prozessobjekt, "ausfallfolge")),
        ("Kundenkreis", e.Kundenkreis, werte(Prozessobjekt, "customer")),
        ("Reichweite", e.Reichweite, werte(Prozessobjekt, "reichweite")),
        ("Datenkategorie", e.Datenkategorie, werte(Datenobjekt, "kategorie")),
        (
            "AssetStatus",
            e.AssetStatus,
            werte(ToolObjekt, "status") | werte(Datenobjekt, "status"),
        ),
        ("Lauftyp", e.Lauftyp, werte(ToolObjekt, "lauftyp")),
        (
            "Ausfuehrungsidentitaet",
            e.Ausfuehrungsidentitaet,
            werte(ToolObjekt, "ausfuehrungsidentitaet"),
        ),
        ("Zugriffsart", e.Zugriffsart, werte(ToolDatenobjekt, "zugriffsart")),
        ("Rolle", e.Rolle, werte(Rollenzuweisung, "rolle")),
        ("ScopeTyp", e.ScopeTyp, werte(Rollenzuweisung, "scope_typ")),
        (
            "SelbstverpflichtungTyp",
            e.SelbstverpflichtungTyp,
            werte(Selbstverpflichtung, "typ"),
        ),
        ("GateTyp", e.GateTyp, werte(GateVorgang, "gate_typ")),
        ("GateStatus", e.GateStatus, werte(GateVorgang, "status")),
        # Die Farbe wird gerechnet, nicht gespeichert (E-64): geprueft wird,
        # was die Anwendung ueber die Werkzeuge sagt, nicht was in der
        # Zeitreihe steht — dort kommt Gelb naturgemaess nie vor.
        (
            "ComplianceFarbe",
            e.ComplianceFarbe,
            [
                lenkung_service.gemessene_farbe(lehrbestand, werkzeug)
                for werkzeug in lehrbestand.execute(select(ToolObjekt)).scalars()
            ],
        ),
        ("LenkungStatus", e.LenkungStatus, werte(Lenkungsvorgang, "status")),
        ("Aufloesungsart", e.Aufloesungsart, werte(Lenkungsvorgang, "aufloesungsart")),
        ("Herkunft", e.Herkunft, werte(ToolObjekt, "herkunft")),
    ]
    luecken = {
        name: sorted({str(v) for v in aufzaehlung} - {str(v) for v in belegt if v is not None})
        for name, aufzaehlung, belegt in pruefungen
        if {str(v) for v in aufzaehlung} - {str(v) for v in belegt if v is not None}
    }
    assert not luecken, f"unbelegte Werte: {luecken}"


def test_alle_sechs_schicht_zwei_verbote_kommen_vor(lehrbestand: Session) -> None:
    """Alle sechs stehen in den Daten der Werkzeuge (A.13.2, E-64).

    Vier misst die Anwendung, zwei erklärt der technische Owner am Werkzeug —
    aber prüfen kann sie danach alle sechs gleich. Vorher war die eine Hälfte
    eine Eigenschaft des Werkzeugs und die andere eine Behauptung in einem
    Vorgang; nur die erste ließ sich nachrechnen.
    """
    from app.models.enums import Schicht2Verbot

    erkannt = {
        str(v)
        for werkzeug in lehrbestand.execute(select(ToolObjekt)).scalars()
        for v in rahmen_service.pruefe_schicht2(werkzeug)
    }
    fehlt = {str(v) for v in Schicht2Verbot} - erkannt
    assert not fehlt, f"nicht belegt: {sorted(fehlt)}"


def test_ein_verbotstatbestand_erzeugt_einen_alarm(lehrbestand: Session) -> None:
    """A.8.5, Schritt 1b: die Bewertung bricht ab und liefert keine Einstufung.

    Der einzige Weg, auf dem eine Bewertung ohne Ergebnis endet.
    """
    from app.models.governance import Alarm

    assert lehrbestand.execute(select(Alarm)).scalars().all()


def test_kennung_und_name_sind_dasselbe_wort(lehrbestand: Session) -> None:
    """Sonst überschreibt die erste Anmeldung den Namen (Architektur 10.1).

    Die Anwendung führt keine eigene Nutzerverwaltung; sie übernimmt den Namen
    aus der Identität. Wer sich mit „prozessowner" in beiden Feldern anmeldet,
    ändert damit einen abweichenden Namen im Bestand — und derselbe Mensch
    erscheint je nach Ansicht unter zwei Namen. Was ihn beschreibt, gehört in
    die Dokumentation, nicht in den Datensatz.
    """
    abweichend = {
        u.subject: u.name
        for u in lehrbestand.execute(select(User)).scalars()
        if u.subject != u.name
    }
    assert not abweichend, f"Kennung und Name unterscheiden sich: {abweichend}"


def test_beide_bestaende_bieten_dieselben_zugaenge(lehrbestand: Session) -> None:
    """Wer den Bestand wechselt, soll sich nicht umgewoehnen muessen."""
    from app.bestand.organisation import DEMOZUGAENGE
    from app.lehrbestand.organisation import ZUGAENGE

    grosser = {person.schluessel for person in DEMOZUGAENGE}
    kleiner = {kennung for kennung, _erlaeuterung, _rollen in ZUGAENGE} - {"ausgeschieden"}
    assert kleiner == grosser
