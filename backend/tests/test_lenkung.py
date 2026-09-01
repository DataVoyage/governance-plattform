"""Compliance und Lenkung — Abnahmekriterien Phase 5 (Architektur 8.6)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from tests.test_bewertung import antworten_fuer, profil_von


@pytest.fixture
def governance(anmelden, rolle_geben):
    nutzer = anmelden("Governance", subject="sub-gov")
    rolle_geben(nutzer.user_id, "governance", "global")
    return nutzer


@pytest.fixture
def owner(anmelden, rolle_geben, organisation):
    nutzer = anmelden("Prozess-Owner", subject="sub-owner")
    rolle_geben(nutzer.user_id, "prozess_owner", "organisationseinheit", organisation["fin_int"])
    return nutzer


@pytest.fixture
def vertretung(anmelden):
    return anmelden("Stellvertretung", subject="sub-vertretung")


@pytest.fixture
def techniker(anmelden, rolle_geben, organisation):
    nutzer = anmelden("Technischer Owner", subject="sub-technik")
    rolle_geben(nutzer.user_id, "technischer_owner", "organisationseinheit", organisation["fin_de"])
    return nutzer


@pytest.fixture
def prozess(client: TestClient, owner, vertretung, prozess_daten):
    return client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id),
        headers=owner.kopf,
    ).json()


def bewerte(client: TestClient, anmeldung, prozess_id: str, **profil):
    antwort = client.post(
        f"/api/v1/prozesse/{prozess_id}/bewertungen",
        json={"modus": "vollstaendig", "antworten": antworten_fuer(profil_von(**profil))},
        headers=anmeldung.kopf,
    )
    assert antwort.status_code == 201, antwort.text
    return antwort.json()["bewertung"]


@pytest.fixture
def tool(client: TestClient, governance, techniker, organisation, prozess, owner):
    """Ein Tier-3-Tool mit technischem Owner, an einem bewerteten Prozess."""
    bewerte(client, owner, prozess["id"], ds=3)
    angelegt = client.post(
        "/api/v1/tools",
        json={
            "name": "Rechnungs-Skript",
            "organisationseinheit_id": organisation["fin_de"],
            "technischer_owner_user_id": techniker.user_id,
        },
        headers=governance.kopf,
    ).json()
    client.post(
        f"/api/v1/tools/{angelegt['id']}/prozesse",
        json={"prozessobjekt_id": prozess["id"]},
        headers=governance.kopf,
    )
    return client.get(f"/api/v1/tools/{angelegt['id']}", headers=governance.kopf).json()


def melde(client: TestClient, anmeldung, tool_id: str, farbe: str, **daten):
    return client.post(
        f"/api/v1/tools/{tool_id}/compliance",
        json={"farbe": farbe, **daten},
        headers=anmeldung.kopf,
    )


# --- Zeitreihe ------------------------------------------------------------


def test_zustand_ist_eine_zeitreihe(client: TestClient, governance, tool) -> None:
    melde(client, governance, tool["id"], "gruen", begruendung="Erstpruefung")
    melde(client, governance, tool["id"], "gelb", begruendung="Beobachtung")
    verlauf = client.get(
        f"/api/v1/tools/{tool['id']}/compliance", headers=governance.kopf
    ).json()
    assert [z["farbe"] for z in verlauf] == ["gelb", "gruen"]
    assert verlauf[0]["begruendung"] == "Beobachtung"


def test_gruene_meldung_erzeugt_keinen_vorgang(client: TestClient, governance, tool) -> None:
    antwort = melde(client, governance, tool["id"], "gruen")
    assert antwort.status_code == 201
    assert antwort.json()["lenkungsvorgang"] is None


def test_meldung_braucht_schreibrecht(client: TestClient, tool, anmelden) -> None:
    fremder = anmelden("Ohne Rolle")
    assert melde(client, fremder, tool["id"], "rot").status_code == 403


# --- Automatischer Lenkungsvorgang (Abnahmekriterium 5.1) ----------------


def test_rahmenueberschreitung_erzeugt_stufe_1_mit_tier_frist(
    client: TestClient, governance, techniker, tool, db
) -> None:
    """Abnahmekriterium 5.1: Stufe 1 mit der tier-abhaengigen Frist."""
    antwort = melde(
        client,
        governance,
        tool["id"],
        "rot",
        begruendung="Schreibt in ein nicht freigegebenes Datenobjekt",
        abweichung_art="datenobjekt_ausserhalb_rahmen",
    )
    assert antwort.status_code == 201
    vorgang = antwort.json()["lenkungsvorgang"]
    assert vorgang is not None
    assert vorgang["eskalationsstufe"] == 1
    assert vorgang["status"] == "offen"
    assert vorgang["zugewiesen_an"] == techniker.user_id

    # Tier 3 -> 14 Tage (Standardwert der Konfiguration).
    frist = datetime.fromisoformat(vorgang["frist"])
    erstellt = datetime.fromisoformat(vorgang["erstellt_am"])
    assert 13 <= (frist - erstellt).days <= 14

    # Der betroffene Owner wird benachrichtigt.
    nachrichten = client.get("/api/v1/benachrichtigungen", headers=techniker.kopf).json()
    assert [n["anlass"] for n in nachrichten] == ["lenkungsvorgang_eroeffnet"]
    del db


def test_frist_haengt_am_tier(
    client: TestClient, governance, owner, vertretung, prozess_daten, organisation
) -> None:
    niedrig = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id, name="Niedrig"),
        headers=owner.kopf,
    ).json()
    bewerte(client, owner, niedrig["id"], ur=1)
    tool = client.post(
        "/api/v1/tools",
        json={"name": "Tier-1-Tool", "organisationseinheit_id": organisation["fin_de"]},
        headers=governance.kopf,
    ).json()
    client.post(
        f"/api/v1/tools/{tool['id']}/prozesse",
        json={"prozessobjekt_id": niedrig["id"]},
        headers=governance.kopf,
    )
    vorgang = melde(client, governance, tool["id"], "rot").json()["lenkungsvorgang"]
    frist = datetime.fromisoformat(vorgang["frist"])
    erstellt = datetime.fromisoformat(vorgang["erstellt_am"])
    assert 89 <= (frist - erstellt).days <= 90


def test_zweite_meldung_verdoppelt_den_vorgang_nicht(
    client: TestClient, governance, tool
) -> None:
    erste = melde(client, governance, tool["id"], "rot").json()["lenkungsvorgang"]
    zweite = melde(client, governance, tool["id"], "rot").json()["lenkungsvorgang"]
    assert erste["id"] == zweite["id"]
    offen = client.get("/api/v1/lenkungsvorgaenge", headers=governance.kopf).json()
    assert len(offen) == 1


def test_vorgang_ohne_owner_bleibt_unzugewiesen(client: TestClient, governance) -> None:
    tool = client.post(
        "/api/v1/tools", json={"name": "Ohne Owner"}, headers=governance.kopf
    ).json()
    vorgang = melde(client, governance, tool["id"], "rot").json()["lenkungsvorgang"]
    assert vorgang["zugewiesen_an"] is None


# --- Eskalation (Abnahmekriterium 5.2) -----------------------------------


def test_fristablauf_rueckt_in_stufe_2_und_informiert_die_fuehrungskraft(
    client: TestClient, governance, techniker, tool, db, anmelden
) -> None:
    """Abnahmekriterium 5.2."""
    from app.models.governance import Benachrichtigung, Lenkungsvorgang
    from app.models.organisation import User
    from app.services import lenkung

    fuehrungskraft = anmelden("Fuehrungskraft", subject="sub-chef")
    db.expire_all()
    owner_datensatz = db.query(User).filter(User.subject == "sub-technik").one()
    owner_datensatz.fuehrungskraft_user_id = __import__("uuid").UUID(fuehrungskraft.user_id)
    db.commit()

    melde(client, governance, tool["id"], "rot")
    db.expire_all()
    vorgang = db.query(Lenkungsvorgang).one()

    # Vor Fristablauf passiert nichts.
    assert lenkung.eskaliere_faellige(db, vorgang.frist - timedelta(days=1)) == []

    gerueckt = lenkung.eskaliere_faellige(db, vorgang.frist + timedelta(days=1))
    db.commit()
    assert len(gerueckt) == 1
    assert gerueckt[0].eskalationsstufe == 2

    nachricht = (
        db.query(Benachrichtigung)
        .filter(Benachrichtigung.anlass == lenkung.ANLASS_ESKALATION)
        .one()
    )
    assert str(nachricht.empfaenger_user_id) == fuehrungskraft.user_id


def test_eskalation_endet_bei_stufe_3(client: TestClient, governance, tool, db) -> None:
    from app.models.governance import Lenkungsvorgang
    from app.services import lenkung

    melde(client, governance, tool["id"], "rot")
    db.expire_all()
    vorgang = db.query(Lenkungsvorgang).one()

    for erwartet in (2, 3):
        gerueckt = lenkung.eskaliere_faellige(db, vorgang.frist + timedelta(days=1))
        assert gerueckt[0].eskalationsstufe == erwartet
        db.refresh(vorgang)

    # In Stufe 3 wird nicht weiter gerueckt.
    assert lenkung.eskaliere_faellige(db, vorgang.frist + timedelta(days=365)) == []
    assert vorgang.eskalationsstufe == 3


def test_ohne_fuehrungskraft_bleibt_der_owner_empfaenger(
    client: TestClient, governance, techniker, tool, db
) -> None:
    from app.models.governance import Benachrichtigung, Lenkungsvorgang
    from app.services import lenkung

    melde(client, governance, tool["id"], "rot")
    db.expire_all()
    vorgang = db.query(Lenkungsvorgang).one()
    lenkung.eskaliere_faellige(db, vorgang.frist + timedelta(days=1))
    db.commit()
    nachricht = (
        db.query(Benachrichtigung)
        .filter(Benachrichtigung.anlass == lenkung.ANLASS_ESKALATION)
        .one()
    )
    assert str(nachricht.empfaenger_user_id) == techniker.user_id


def test_eskalationsjob_laeuft(client: TestClient, governance, tool, db) -> None:
    from app import jobs

    melde(client, governance, tool["id"], "rot")
    db.commit()
    assert jobs.main(["eskalationen"]) == 0


# --- Aufloesung (Abnahmekriterium 5.3) -----------------------------------


def loese_auf(client: TestClient, anmeldung, vorgang_id: str, art: str, **daten):
    return client.post(
        f"/api/v1/lenkungsvorgaenge/{vorgang_id}/aufloesung",
        json={"art": art, **daten},
        headers=anmeldung.kopf,
    )


def test_anpassen_schliesst_und_setzt_gruen(client: TestClient, governance, tool) -> None:
    vorgang = melde(client, governance, tool["id"], "rot").json()["lenkungsvorgang"]
    antwort = loese_auf(
        client, governance, vorgang["id"], "anpassen", kommentar="Schreibzugriff entfernt"
    )
    assert antwort.status_code == 200
    assert antwort.json()["status"] == "aufgeloest"
    assert antwort.json()["aufloesungsart"] == "anpassen"

    verlauf = client.get(
        f"/api/v1/tools/{tool['id']}/compliance", headers=governance.kopf
    ).json()
    assert verlauf[0]["farbe"] == "gruen"


def test_rahmen_erweitern_verlangt_eine_neue_bewertung(
    client: TestClient, governance, owner, prozess, tool
) -> None:
    """Abnahmekriterium 5.3: schliesst erst nach Abschluss der neuen Bewertung."""
    alte_bewertung = client.get(
        f"/api/v1/prozesse/{prozess['id']}/bewertungen", headers=owner.kopf
    ).json()[0]
    vorgang = melde(client, governance, tool["id"], "rot").json()["lenkungsvorgang"]

    ohne = loese_auf(client, governance, vorgang["id"], "rahmen_erweitern")
    assert ohne.status_code == 422
    assert "neue Bewertung" in ohne.json()["detail"]

    zu_alt = loese_auf(
        client, governance, vorgang["id"], "rahmen_erweitern", bewertung_id=alte_bewertung["id"]
    )
    assert zu_alt.status_code == 422
    assert "vor der Eroeffnung" in zu_alt.json()["detail"]

    neue = bewerte(client, owner, prozess["id"], ds=3, it=2)
    antwort = loese_auf(
        client, governance, vorgang["id"], "rahmen_erweitern", bewertung_id=neue["id"]
    )
    assert antwort.status_code == 200
    assert antwort.json()["aufloesung_bewertung_id"] == neue["id"]
    assert antwort.json()["status"] == "aufgeloest"


def test_rahmen_erweitern_mit_unbekannter_bewertung(
    client: TestClient, governance, tool
) -> None:
    vorgang = melde(client, governance, tool["id"], "rot").json()["lenkungsvorgang"]
    antwort = loese_auf(
        client,
        governance,
        vorgang["id"],
        "rahmen_erweitern",
        bewertung_id="00000000-0000-0000-0000-000000000000",
    )
    assert antwort.status_code == 422


def test_stilllegen_setzt_das_tool_inaktiv(client: TestClient, governance, tool) -> None:
    vorgang = melde(client, governance, tool["id"], "rot").json()["lenkungsvorgang"]
    antwort = loese_auf(client, governance, vorgang["id"], "stilllegen")
    assert antwort.status_code == 200

    aktuell = client.get(f"/api/v1/tools/{tool['id']}", headers=governance.kopf).json()
    assert aktuell["status"] == "inaktiv"
    # Stilllegen bedeutet nicht "wieder konform": kein gruener Eintrag.
    verlauf = client.get(
        f"/api/v1/tools/{tool['id']}/compliance", headers=governance.kopf
    ).json()
    assert verlauf[0]["farbe"] == "rot"


def test_jede_aufloesung_ist_eine_eigene_aktion(client: TestClient, governance, tool) -> None:
    from app.models.enums import Aufloesungsart

    assert {a.value for a in Aufloesungsart} == {"anpassen", "rahmen_erweitern", "stilllegen"}
    vorgang = melde(client, governance, tool["id"], "rot").json()["lenkungsvorgang"]
    ungueltig = loese_auf(client, governance, vorgang["id"], "irgendwie_anders")
    assert ungueltig.status_code == 422


def test_zweite_aufloesung_wird_abgelehnt(client: TestClient, governance, tool) -> None:
    vorgang = melde(client, governance, tool["id"], "rot").json()["lenkungsvorgang"]
    loese_auf(client, governance, vorgang["id"], "anpassen")
    nochmal = loese_auf(client, governance, vorgang["id"], "anpassen")
    assert nochmal.status_code == 422


def test_betroffener_darf_selbst_aufloesen(client: TestClient, governance, techniker, tool) -> None:
    vorgang = melde(client, governance, tool["id"], "rot").json()["lenkungsvorgang"]
    assert loese_auf(client, techniker, vorgang["id"], "anpassen").status_code == 200


def test_fremder_darf_nicht_aufloesen(client: TestClient, governance, tool, anmelden) -> None:
    vorgang = melde(client, governance, tool["id"], "rot").json()["lenkungsvorgang"]
    fremder = anmelden("Ohne Rolle")
    assert loese_auf(client, fremder, vorgang["id"], "anpassen").status_code == 403


# --- Abbruch, Liste, Sichtbarkeit ----------------------------------------


def test_governance_bricht_eine_fehlmeldung_ab(client: TestClient, governance, tool) -> None:
    vorgang = melde(client, governance, tool["id"], "rot").json()["lenkungsvorgang"]
    antwort = client.post(
        f"/api/v1/lenkungsvorgaenge/{vorgang['id']}/abbruch",
        json={"kommentar": "Fehlmeldung"},
        headers=governance.kopf,
    )
    assert antwort.status_code == 200
    assert antwort.json()["status"] == "abgebrochen"


def test_nur_governance_bricht_ab(client: TestClient, governance, techniker, tool) -> None:
    vorgang = melde(client, governance, tool["id"], "rot").json()["lenkungsvorgang"]
    antwort = client.post(
        f"/api/v1/lenkungsvorgaenge/{vorgang['id']}/abbruch",
        json={},
        headers=techniker.kopf,
    )
    assert antwort.status_code == 403


def test_abgeschlossener_vorgang_wird_nicht_abgebrochen(
    client: TestClient, governance, tool
) -> None:
    vorgang = melde(client, governance, tool["id"], "rot").json()["lenkungsvorgang"]
    loese_auf(client, governance, vorgang["id"], "anpassen")
    antwort = client.post(
        f"/api/v1/lenkungsvorgaenge/{vorgang['id']}/abbruch",
        json={},
        headers=governance.kopf,
    )
    assert antwort.status_code == 422


def test_liste_filtert_nach_stufe_und_status(
    client: TestClient, governance, tool, db
) -> None:
    from app.models.governance import Lenkungsvorgang
    from app.services import lenkung

    melde(client, governance, tool["id"], "rot")
    db.expire_all()
    vorgang = db.query(Lenkungsvorgang).one()
    lenkung.eskaliere_faellige(db, vorgang.frist + timedelta(days=1))
    db.commit()

    stufe_2 = client.get(
        "/api/v1/lenkungsvorgaenge?eskalationsstufe=2", headers=governance.kopf
    ).json()
    assert len(stufe_2) == 1
    stufe_1 = client.get(
        "/api/v1/lenkungsvorgaenge?eskalationsstufe=1", headers=governance.kopf
    ).json()
    assert stufe_1 == []

    loese_auf(client, governance, str(vorgang.id), "anpassen")
    assert client.get("/api/v1/lenkungsvorgaenge", headers=governance.kopf).json() == []
    alle = client.get(
        "/api/v1/lenkungsvorgaenge?nur_offen=false", headers=governance.kopf
    ).json()
    assert len(alle) == 1


def test_fremder_sieht_keine_vorgaenge(client: TestClient, governance, tool, anmelden) -> None:
    vorgang = melde(client, governance, tool["id"], "rot").json()["lenkungsvorgang"]
    fremder = anmelden("Ohne Rolle")
    assert client.get("/api/v1/lenkungsvorgaenge", headers=fremder.kopf).json() == []
    assert (
        client.get(
            f"/api/v1/lenkungsvorgaenge/{vorgang['id']}", headers=fremder.kopf
        ).status_code
        == 403
    )


def test_betroffener_sieht_seinen_vorgang(client: TestClient, governance, techniker, tool) -> None:
    melde(client, governance, tool["id"], "rot")
    assert len(client.get("/api/v1/lenkungsvorgaenge", headers=techniker.kopf).json()) == 1


def test_unbekannter_vorgang(client: TestClient, governance) -> None:
    antwort = client.get(
        "/api/v1/lenkungsvorgaenge/00000000-0000-0000-0000-000000000000",
        headers=governance.kopf,
    )
    assert antwort.status_code == 404


def test_lenkung_landet_im_nachweis(client: TestClient, governance, tool, db) -> None:
    from app.models.audit import ChangeLog

    vorgang = melde(client, governance, tool["id"], "rot").json()["lenkungsvorgang"]
    loese_auf(client, governance, vorgang["id"], "anpassen")
    db.expire_all()
    aktionen = [
        e.aktion
        for e in db.query(ChangeLog)
        .filter(ChangeLog.entity_type == "lenkungsvorgaenge")
        .order_by(ChangeLog.cursor)
        .all()
    ]
    assert aktionen == ["erstellt", "geaendert"]


def test_zeitzonenlose_frist_wird_als_utc_gelesen(db) -> None:
    from app.services import lenkung

    naiv = datetime(2026, 1, 1, 12, 0)
    assert lenkung._als_utc(naiv) == naiv.replace(tzinfo=UTC)
    assert lenkung._als_utc(None) is None
