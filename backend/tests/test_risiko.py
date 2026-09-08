"""Unternehmerisches Risiko als komposite Ebene (Leitdokument A.8.4, AP-19).

Geprueft wird, was an die Stelle der drei UR-Fragen getreten ist: eine
Rechnung aus zwei erklaerten Erwartungen, hinterlegt in einer gepflegten
Tabelle — und die Trennung zwischen eigenem Betriebsrisiko und dem, was die
Prozesskette beitraegt.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.permissions import Principal, Verboten, Zuweisung
from app.models.enums import Ausfallfolge, Reichweite, Rolle, ScopeTyp
from app.models.governance import Prozessobjekt
from app.services import risiko as risiko_service
from app.services.prozess import Ungueltig


def _principal(*rollen: Rolle, user_id: uuid.UUID | None = None) -> Principal:
    """Ein Principal fuer den direkten Dienstaufruf, ohne den Umweg ueber HTTP.

    Wo eine Aenderung tatsaechlich geschrieben wird, muss ``user_id`` auf einen
    **vorhandenen** Nutzer zeigen: ``geaendert_von`` traegt einen Fremdschluessel
    auf ``users``, und ein erfundener Akteur waere ohnehin kein Nachweis.
    """
    return Principal(
        user_id=user_id or uuid.uuid4(),
        email="pruefung@beispiel-ag.de",
        name="Pruefung",
        zuweisungen=[Zuweisung(r, ScopeTyp.GLOBAL) for r in rollen],
    )


@pytest.fixture
def owner(anmelden, rolle_geben, organisation):
    nutzer = anmelden("Prozess-Owner", subject="sub-owner-risiko")
    rolle_geben(nutzer.user_id, "prozess_owner", "organisationseinheit", organisation["fin_int"])
    return nutzer


@pytest.fixture
def prozess_orm(client: TestClient, owner, anmelden, prozess_daten, db):
    """Legt ein Prozessobjekt ueber die API an und liefert die ORM-Sicht darauf."""
    vertretung = anmelden("Stellvertretung", subject="sub-vertretung-risiko")

    def _anlegen(name: str = "Fall", **felder) -> Prozessobjekt:
        antwort = client.post(
            "/api/v1/prozesse",
            json=prozess_daten(owner.user_id, vertretung.user_id, name=name, **felder),
            headers=owner.kopf,
        )
        assert antwort.status_code == 201, antwort.text
        kennung = uuid.UUID(antwort.json()["id"])
        return db.execute(select(Prozessobjekt).where(Prozessobjekt.id == kennung)).scalar_one()

    return _anlegen


# --- Die Tabelle ----------------------------------------------------------


def test_die_tabelle_deckt_jede_paarung_ab() -> None:
    """Vier Ausfallfolgen mal fuenf Reichweiten — keine Luecke, kein Zufall."""
    erwartet = {(a, r) for a in Ausfallfolge for r in Reichweite}
    assert set(risiko_service.STANDARDTABELLE) == erwartet
    assert len(risiko_service.STANDARDTABELLE) == 20
    assert all(0 <= s <= 3 for s in risiko_service.STANDARDTABELLE.values())


def test_die_tabelle_steigt_in_beiden_richtungen_monoton() -> None:
    """Mehr Schaden darf nie weniger Risiko ergeben — mehr Reichweite auch nicht.

    Das ist keine Formel, sondern eine Plausibilitaetsschranke: Die Belegung
    ist eine fachliche Setzung und darf frei gewaehlt werden, aber ein
    Ruecksprung waere ein Fehler und kein Ermessen.
    """
    folgen = list(Ausfallfolge)
    weiten = list(Reichweite)
    for i, folge in enumerate(folgen):
        for j, weite in enumerate(weiten):
            hier = risiko_service.STANDARDTABELLE[(folge, weite)]
            if i + 1 < len(folgen):
                assert risiko_service.STANDARDTABELLE[(folgen[i + 1], weite)] >= hier
            if j + 1 < len(weiten):
                assert risiko_service.STANDARDTABELLE[(folge, weiten[j + 1])] >= hier


def test_initialisieren_ist_idempotent(db) -> None:
    assert risiko_service.initialisiere(db) == 20
    assert risiko_service.initialisiere(db) == 0
    assert len(risiko_service.tabelle(db)) == 20


def test_die_stufe_gilt_auch_vor_dem_ersten_zugriff(db) -> None:
    """Eine frische Datenbank rechnet nicht anders als eine befuellte."""
    ohne = risiko_service.stufe_fuer(db, Ausfallfolge.KRITISCH, Reichweite.UNTERNEHMEN)
    risiko_service.initialisiere(db)
    mit = risiko_service.stufe_fuer(db, Ausfallfolge.KRITISCH, Reichweite.UNTERNEHMEN)
    assert ohne == mit == 3


def test_die_tabelle_kommt_geordnet(db) -> None:
    """Erst nach Ausfallfolge, dann nach Reichweite — wie im Dokument."""
    reihenfolge = [(e.ausfallfolge, e.reichweite) for e in risiko_service.tabelle(db)]
    assert reihenfolge[0] == (Ausfallfolge.KEINE, Reichweite.PERSOENLICH)
    assert reihenfolge[-1] == (Ausfallfolge.KRITISCH, Reichweite.EXTERN)


# --- Die Rechnung ---------------------------------------------------------


def test_ur_kommt_aus_der_tabelle_und_nicht_aus_dem_code(db, prozess_orm) -> None:
    """Die Tabelle ist die Quelle: wird sie geaendert, aendert sich die Stufe."""
    prozess = prozess_orm(customer="bereich", ausfallfolge="spuerbar")
    assert risiko_service.ur_stufe(db, prozess).stufe == 2

    eintrag = next(
        e
        for e in risiko_service.tabelle(db)
        if e.ausfallfolge == Ausfallfolge.SPUERBAR and e.reichweite == Reichweite.BEREICH
    )
    eintrag.stufe = 0
    db.flush()
    assert risiko_service.ur_stufe(db, prozess).stufe == 0


def test_der_ur_stand_nennt_beide_anteile(db, prozess_orm) -> None:
    """Eine gerechnete Stufe ohne ihren Rechenweg waere eine Behauptung."""
    prozess = prozess_orm(customer="unternehmen", ausfallfolge="kritisch")
    stand = risiko_service.ur_stufe(db, prozess)
    assert stand.stufe == 3
    assert stand.reichweite == Reichweite.UNTERNEHMEN
    assert stand.ausfallfolge == Ausfallfolge.KRITISCH


def test_dieselbe_ausfallfolge_wiegt_bei_kleinerer_reichweite_leichter(db, prozess_orm) -> None:
    """Ein kritischer Ausfall, der eine Person trifft, ist kein Unternehmensrisiko."""
    eng = prozess_orm(name="Eng", customer="persoenlich", ausfallfolge="kritisch")
    weit = prozess_orm(name="Weit", customer="unternehmen", ausfallfolge="kritisch")
    assert risiko_service.ur_stufe(db, eng).stufe == 1
    assert risiko_service.ur_stufe(db, weit).stufe == 3


# --- Die Kette ------------------------------------------------------------


def test_die_kette_enthaelt_den_eigenen_wert_nicht(db, prozess_orm) -> None:
    """Sonst waere die Kappung des eigenen Risikos wirkungslos."""
    allein = prozess_orm(customer="unternehmen", ausfallfolge="kritisch")
    assert risiko_service.ur_der_kette(db, allein) == (0, None)


def test_die_kette_wirkt_transitiv_und_nennt_ihre_quelle(db, prozess_orm) -> None:
    """A.4.2: auch der Vorgaenger des Vorgaengers wird gehoben."""
    kritisch = prozess_orm(name="Zahlungslauf", customer="unternehmen", ausfallfolge="kritisch")
    mitte = prozess_orm(
        name="Mitte",
        customer="persoenlich",
        ausfallfolge="keine",
        nachgelagert_ids=[str(kritisch.id)],
    )
    anfang = prozess_orm(
        name="Anfang",
        customer="persoenlich",
        ausfallfolge="keine",
        nachgelagert_ids=[str(mitte.id)],
    )

    stufe, quelle = risiko_service.ur_der_kette(db, anfang)
    assert stufe == 3
    assert quelle is not None and quelle.name == "Zahlungslauf"


def test_ein_enger_nachfolger_reisst_niemanden_mit(db, prozess_orm) -> None:
    """Der Unterschied zur blossen Kritikalitaet: die Reichweite zaehlt mit."""
    eng = prozess_orm(name="Eng", customer="persoenlich", ausfallfolge="kritisch")
    speist = prozess_orm(
        name="Speist",
        customer="persoenlich",
        ausfallfolge="keine",
        nachgelagert_ids=[str(eng.id)],
    )
    stufe, _ = risiko_service.ur_der_kette(db, speist)
    assert stufe == 1


def test_ein_zyklus_in_der_kette_terminiert(db, prozess_orm) -> None:
    """Die Kette ist fachlich azyklisch gemeint, technisch aber n:m."""
    erster = prozess_orm(name="Erster", customer="unternehmen", ausfallfolge="spuerbar")
    zweiter = prozess_orm(
        name="Zweiter", customer="team", ausfallfolge="gering", nachgelagert_ids=[str(erster.id)]
    )
    erster.nachgelagert.append(zweiter)
    db.flush()

    stufe, _ = risiko_service.ur_der_kette(db, erster)
    assert stufe == 1


# --- Pflege der Tabelle ---------------------------------------------------


def test_nur_die_governance_rolle_pflegt_die_tabelle(db) -> None:
    with pytest.raises(Verboten):
        risiko_service.setze_feld(
            db,
            _principal(Rolle.PROZESS_OWNER),
            Ausfallfolge.GERING,
            Reichweite.TEAM,
            stufe=3,
            begruendung="Weil ich es kann.",
        )


def test_ein_feld_ohne_begruendung_wird_abgewiesen(db) -> None:
    with pytest.raises(Ungueltig):
        risiko_service.setze_feld(
            db,
            _principal(Rolle.GOVERNANCE),
            Ausfallfolge.GERING,
            Reichweite.TEAM,
            stufe=3,
            begruendung="   ",
        )


def test_eine_stufe_ausserhalb_der_skala_wird_abgewiesen(db) -> None:
    with pytest.raises(Ungueltig):
        risiko_service.setze_feld(
            db,
            _principal(Rolle.GOVERNANCE),
            Ausfallfolge.GERING,
            Reichweite.TEAM,
            stufe=4,
            begruendung="Vier gibt es nicht.",
        )


def test_eine_aenderung_steht_im_nachweis(db, anmelden) -> None:
    from app.models.audit import ChangeLog

    # Ein echter Nutzer, nicht irgendeine Kennung: Der Nachweis soll auf eine
    # Person zeigen koennen, und der Fremdschluessel erzwingt genau das.
    akteur = uuid.UUID(anmelden("Governance", subject="sub-gov-nachweis").user_id)
    eintrag = risiko_service.setze_feld(
        db,
        _principal(Rolle.GOVERNANCE, user_id=akteur),
        Ausfallfolge.GERING,
        Reichweite.TEAM,
        stufe=2,
        begruendung="Teamausfaelle wiegen in dieser Organisation schwerer.",
    )
    assert eintrag.stufe == 2

    protokoll = list(
        db.execute(select(ChangeLog).where(ChangeLog.entity_type == "ur_komposition")).scalars()
    )
    assert len(protokoll) == 1
    assert protokoll[0].akteur_user_id is not None


# --- Die Tabelle ueber HTTP ----------------------------------------------
#
# Ohne Endpunkt waere die Kompositionstabelle zwar in der Datenbank, aber nur
# mit einer Auslieferung aenderbar — also faktisch weiter eine Konstante. Genau
# das schliesst E-66 aus.


@pytest.fixture
def governance_nutzer(anmelden, rolle_geben):
    nutzer = anmelden("Governance", subject="sub-gov-komposition")
    rolle_geben(nutzer.user_id, "governance", "global")
    return nutzer


def test_die_tabelle_kommt_ueber_die_api(client: TestClient, anmelden) -> None:
    """Der erste Aufruf legt die Standardbelegung an — zwanzig Felder."""
    wer = anmelden("Leserin", subject="sub-leserin-komposition")
    antwort = client.get("/api/v1/ur-komposition", headers=wer.kopf)
    assert antwort.status_code == 200, antwort.text
    felder = antwort.json()
    assert len(felder) == 20

    feld = {(f["ausfallfolge"], f["reichweite"]): f["stufe"] for f in felder}
    # Die beiden Enden der Aussage aus A.8.4.
    assert feld[("kritisch", "persoenlich")] == 1
    assert feld[("kritisch", "unternehmen")] == 3
    assert feld[("gering", "unternehmen")] == 2


def test_governance_aendert_ein_feld_und_die_rechnung_folgt(
    client: TestClient, governance_nutzer, prozess_orm
) -> None:
    """Die Aenderung wirkt in der naechsten Bewertung, nicht nur in der Tabelle."""
    prozess = prozess_orm(customer="bereich", ausfallfolge="spuerbar")
    assert (
        client.post(
            f"/api/v1/prozesse/{prozess.id}/bewertung/wizard",
            json={"antworten": {}},
            headers=governance_nutzer.kopf,
        ).json()["ausgangslage"]["ur_stufe"]
        == 2
    )

    antwort = client.put(
        "/api/v1/ur-komposition/spuerbar/bereich",
        json={"stufe": 3, "begruendung": "Der Bereich traegt inzwischen die halbe Gruppe."},
        headers=governance_nutzer.kopf,
    )
    assert antwort.status_code == 200, antwort.text
    assert antwort.json()["stufe"] == 3

    lage = client.post(
        f"/api/v1/prozesse/{prozess.id}/bewertung/wizard",
        json={"antworten": {}},
        headers=governance_nutzer.kopf,
    ).json()["ausgangslage"]
    assert lage["ur_stufe"] == 3


def test_ohne_governance_rolle_bleibt_die_tabelle_zu(client: TestClient, anmelden) -> None:
    wer = anmelden("Ohne Rolle", subject="sub-ohne-rolle-komposition")
    antwort = client.put(
        "/api/v1/ur-komposition/spuerbar/bereich",
        json={"stufe": 0, "begruendung": "Weil ich es kann."},
        headers=wer.kopf,
    )
    assert antwort.status_code == 403, antwort.text


def test_eine_aenderung_ohne_begruendung_wird_abgewiesen(
    client: TestClient, governance_nutzer
) -> None:
    """Pflichtfeld — ein Feld hier entscheidet ueber ganze Prozessgruppen."""
    antwort = client.put(
        "/api/v1/ur-komposition/spuerbar/bereich",
        json={"stufe": 3, "begruendung": "   "},
        headers=governance_nutzer.kopf,
    )
    assert antwort.status_code in (400, 422), antwort.text


def test_eine_unbekannte_paarung_gibt_es_nicht(client: TestClient, governance_nutzer) -> None:
    antwort = client.put(
        "/api/v1/ur-komposition/gibtesnicht/bereich",
        json={"stufe": 1, "begruendung": "Egal."},
        headers=governance_nutzer.kopf,
    )
    assert antwort.status_code == 404, antwort.text
