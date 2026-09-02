"""Verwaltung: Nutzer, Rollen, Wirkungsvorschau und Nachweis (AP-9).

Die Anwendung wird selbsttragend — Rollen wurden bisher nur ueber die API
vergeben, der Nachweis war nur ueber die Datenbank zu lesen.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.services.verwaltung import ROLLENERKLAERUNG
from tests.test_bewertung import nutzlast, profil_von


@pytest.fixture
def owner(anmelden, rolle_geben, organisation):
    nutzer = anmelden("Prozess-Owner", subject="sub-owner")
    rolle_geben(nutzer.user_id, "prozess_owner", "organisationseinheit", organisation["fin_int"])
    return nutzer


@pytest.fixture
def governance(anmelden, rolle_geben):
    nutzer = anmelden("Governance", subject="sub-gov")
    rolle_geben(nutzer.user_id, "governance", "global")
    return nutzer


@pytest.fixture
def auditor(anmelden, rolle_geben):
    nutzer = anmelden("Auditor", subject="sub-audit")
    rolle_geben(nutzer.user_id, "auditor", "global")
    return nutzer


@pytest.fixture
def kandidat(anmelden):
    return anmelden("Neue Kollegin", subject="sub-neu")


# --- Rollen mit Erklaerung (Leitdokument A.15) ---------------------------


def test_jede_rolle_nennt_ihre_erklaerung(client: TestClient, administrator) -> None:
    liste = client.get("/api/v1/admin/rollen", headers=administrator.kopf).json()
    assert len(liste) == 8
    for eintrag in liste:
        assert eintrag["schluessel"] in ROLLENERKLAERUNG
        assert len(eintrag["erklaerung"]) > 40


# --- Wirkungsvorschau -----------------------------------------------------


def test_wirkung_zaehlt_was_die_zuweisung_eroeffnet(
    client: TestClient, administrator, owner, kandidat, organisation, prozess_daten, anmelden
) -> None:
    """V-ADM-03: die Zahl steht vor der Entscheidung."""
    vertretung = anmelden("Vertretung", subject="sub-vert")
    for name in ("Erster", "Zweiter"):
        client.post(
            "/api/v1/prozesse",
            json=prozess_daten(owner.user_id, vertretung.user_id, name=name),
            headers=owner.kopf,
        )

    antwort = client.get(
        "/api/v1/admin/rollenzuweisungen/wirkung",
        params={
            "user_id": kandidat.user_id,
            "rolle": "prozess_owner",
            "scope_typ": "organisationseinheit",
            "scope_id": organisation["fin_int"],
        },
        headers=administrator.kopf,
    )
    assert antwort.status_code == 200, antwort.text
    wirkung = antwort.json()
    assert wirkung["prozessobjekte"] == 2
    assert set(wirkung["beispiele"]) == {"Erster", "Zweiter"}
    assert "INT" in wirkung["scope_name"]


def test_wirkung_rechnet_die_zuweisung_allein(
    client: TestClient, administrator, owner, organisation, prozess_daten, anmelden
) -> None:
    """Nicht, was der Nutzer insgesamt sieht — was diese eine Zuweisung eröffnet."""
    vertretung = anmelden("Vertretung", subject="sub-vert")
    client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id),
        headers=owner.kopf,
    )
    # Der Owner sieht seinen Prozess schon; ein Scope auf HR eröffnet nichts.
    wirkung = client.get(
        "/api/v1/admin/rollenzuweisungen/wirkung",
        params={
            "user_id": owner.user_id,
            "rolle": "prozess_owner",
            "scope_typ": "organisationseinheit",
            "scope_id": organisation["hr_int"],
        },
        headers=administrator.kopf,
    ).json()
    assert wirkung["prozessobjekte"] == 0


def test_globale_zuweisung_nennt_ihren_umfang(client: TestClient, administrator, kandidat) -> None:
    wirkung = client.get(
        "/api/v1/admin/rollenzuweisungen/wirkung",
        params={"user_id": kandidat.user_id, "rolle": "governance", "scope_typ": "global"},
        headers=administrator.kopf,
    ).json()
    assert wirkung["scope_name"] == "unternehmensweit"


def test_wirkung_nur_fuer_den_administrator(client: TestClient, owner, kandidat) -> None:
    antwort = client.get(
        "/api/v1/admin/rollenzuweisungen/wirkung",
        params={"user_id": kandidat.user_id, "rolle": "governance", "scope_typ": "global"},
        headers=owner.kopf,
    )
    assert antwort.status_code == 403


def test_wirkung_fuer_unbekannten_nutzer(client: TestClient, administrator) -> None:
    antwort = client.get(
        "/api/v1/admin/rollenzuweisungen/wirkung",
        params={
            "user_id": "00000000-0000-0000-0000-000000000000",
            "rolle": "governance",
            "scope_typ": "global",
        },
        headers=administrator.kopf,
    )
    assert antwort.status_code == 404


# --- Nutzerpflege ---------------------------------------------------------


def test_administrator_setzt_die_fuehrungskraft(
    client: TestClient, administrator, kandidat, owner
) -> None:
    antwort = client.patch(
        f"/api/v1/admin/users/{kandidat.user_id}",
        json={"fuehrungskraft_user_id": owner.user_id},
        headers=administrator.kopf,
    )
    assert antwort.status_code == 200
    assert antwort.json()["fuehrungskraft_user_id"] == owner.user_id


def test_niemand_ist_seine_eigene_fuehrungskraft(
    client: TestClient, administrator, kandidat
) -> None:
    antwort = client.patch(
        f"/api/v1/admin/users/{kandidat.user_id}",
        json={"fuehrungskraft_user_id": kandidat.user_id},
        headers=administrator.kopf,
    )
    assert antwort.status_code == 422
    assert "Kreis" in antwort.json()["detail"]


def test_unbekannte_fuehrungskraft_wird_abgewiesen(
    client: TestClient, administrator, kandidat
) -> None:
    antwort = client.patch(
        f"/api/v1/admin/users/{kandidat.user_id}",
        json={"fuehrungskraft_user_id": "00000000-0000-0000-0000-000000000000"},
        headers=administrator.kopf,
    )
    assert antwort.status_code == 404


def test_administrator_deaktiviert_einen_nutzer(
    client: TestClient, administrator, kandidat
) -> None:
    antwort = client.patch(
        f"/api/v1/admin/users/{kandidat.user_id}",
        json={"ist_aktiv": False},
        headers=administrator.kopf,
    )
    assert antwort.json()["ist_aktiv"] is False


def test_nutzerpflege_nur_fuer_den_administrator(client: TestClient, owner, kandidat) -> None:
    antwort = client.patch(
        f"/api/v1/admin/users/{kandidat.user_id}",
        json={"ist_aktiv": False},
        headers=owner.kopf,
    )
    assert antwort.status_code == 403


def test_unbekannter_nutzer(client: TestClient, administrator) -> None:
    antwort = client.patch(
        "/api/v1/admin/users/00000000-0000-0000-0000-000000000000",
        json={"ist_aktiv": False},
        headers=administrator.kopf,
    )
    assert antwort.status_code == 404


# --- Nachweis (Leitdokument A.13.7) --------------------------------------


def test_nachweis_nennt_zeitpunkt_person_und_aenderung(
    client: TestClient, auditor, owner, anmelden, prozess_daten
) -> None:
    """V-INT-06: jede Änderung mit Zeitpunkt, Person und Vorher/Nachher."""
    vertretung = anmelden("Vertretung", subject="sub-vert")
    prozess = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id),
        headers=owner.kopf,
    ).json()
    client.patch(
        f"/api/v1/prozesse/{prozess['id']}",
        json={"name": "Anders benannt"},
        headers=owner.kopf,
    )

    eintraege = client.get(
        "/api/v1/nachweis",
        params={"entity_type": "prozessobjekte", "entity_id": prozess["id"]},
        headers=auditor.kopf,
    ).json()
    assert [e["aktion"] for e in eintraege] == ["geaendert", "erstellt"]

    aenderung = eintraege[0]
    assert aenderung["akteur"] == "Prozess-Owner"
    assert aenderung["zeitpunkt"]
    assert aenderung["gegenstand"] == "Anders benannt"
    namensfeld = next(a for a in aenderung["aenderungen"] if a["feld"] == "name")
    assert namensfeld["vorher"] == "Rechnungspruefung"
    assert namensfeld["nachher"] == "Anders benannt"


def test_nachweis_laesst_belanglose_felder_weg(
    client: TestClient, auditor, owner, anmelden, prozess_daten
) -> None:
    """Ein Zeitstempel, der sich bei jeder Änderung ändert, erklärt nichts."""
    vertretung = anmelden("Vertretung", subject="sub-vert")
    prozess = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id),
        headers=owner.kopf,
    ).json()
    client.patch(f"/api/v1/prozesse/{prozess['id']}", json={"name": "Neu"}, headers=owner.kopf)
    eintraege = client.get(
        "/api/v1/nachweis",
        params={"entity_type": "prozessobjekte", "entity_id": prozess["id"]},
        headers=auditor.kopf,
    ).json()
    felder = {a["feld"] for a in eintraege[0]["aenderungen"]}
    assert felder == {"name"}


def test_nachweis_zeigt_auch_bewertungen(
    client: TestClient, auditor, owner, anmelden, prozess_daten
) -> None:
    vertretung = anmelden("Vertretung", subject="sub-vert")
    prozess = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id),
        headers=owner.kopf,
    ).json()
    client.post(
        f"/api/v1/prozesse/{prozess['id']}/bewertungen",
        json=nutzlast(profil_von(ds=3)),
        headers=owner.kopf,
    )
    eintraege = client.get(
        "/api/v1/nachweis", params={"entity_type": "bewertungen"}, headers=auditor.kopf
    ).json()
    assert eintraege
    assert eintraege[0]["akteur"] == "Prozess-Owner"


def test_nachweis_ist_nichts_fuer_jeden(client: TestClient, owner) -> None:
    assert client.get("/api/v1/nachweis", headers=owner.kopf).status_code == 403


def test_administrator_liest_den_nachweis(client: TestClient, administrator) -> None:
    assert client.get("/api/v1/nachweis", headers=administrator.kopf).status_code == 200


def test_nachweis_begrenzt_die_menge(client: TestClient, auditor) -> None:
    antwort = client.get("/api/v1/nachweis", params={"limit": 5}, headers=auditor.kopf)
    assert antwort.status_code == 200
    assert len(antwort.json()) <= 5


def test_nachweis_nennt_personen_mit_namen(
    client: TestClient, auditor, owner, anmelden, prozess_daten
) -> None:
    """Eine UUID beantwortet die Frage „wer" nicht."""
    vertretung = anmelden("Vertretung", subject="sub-vert")
    prozess = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id),
        headers=owner.kopf,
    ).json()
    eintraege = client.get(
        "/api/v1/nachweis",
        params={"entity_type": "prozessobjekte", "entity_id": prozess["id"]},
        headers=auditor.kopf,
    ).json()
    owner_feld = next(a for a in eintraege[0]["aenderungen"] if a["feld"] == "owner_user_id")
    assert owner_feld["nachher"] == "Prozess-Owner"


def test_nachweis_zeigt_keine_fremdschluessel(
    client: TestClient, auditor, owner, anmelden, prozess_daten
) -> None:
    """Den Gegenstand nennt die Überschrift — seine Beziehungs-IDs sagen nichts."""
    vertretung = anmelden("Vertretung", subject="sub-vert")
    prozess = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id),
        headers=owner.kopf,
    ).json()
    eintraege = client.get(
        "/api/v1/nachweis",
        params={"entity_type": "prozessobjekte", "entity_id": prozess["id"]},
        headers=auditor.kopf,
    ).json()
    felder = {a["feld"] for a in eintraege[0]["aenderungen"]}
    assert "prozessgeber_org_id" not in felder
    # Personenfelder bleiben — sie lassen sich zu einem Namen auflösen.
    assert "owner_user_id" in felder


def test_nachweis_kuerzt_zeitstempel_auf_die_minute(
    client: TestClient, auditor, governance, owner, anmelden, prozess_daten
) -> None:
    from app.models.enums import GateTyp

    vertretung = anmelden("Vertretung", subject="sub-vert")
    prozess = client.post(
        "/api/v1/prozesse",
        json=prozess_daten(owner.user_id, vertretung.user_id),
        headers=owner.kopf,
    ).json()
    gate = client.post(
        f"/api/v1/prozesse/{prozess['id']}/gates",
        json={"gate_typ": GateTyp.GATE_1.value, "begruendung": "Erstfreigabe"},
        headers=owner.kopf,
    ).json()
    client.post(
        f"/api/v1/gates/{gate['id']}/entscheidung",
        json={"status": "freigegeben", "kommentar": "In Ordnung"},
        headers=governance.kopf,
    )
    eintraege = client.get(
        "/api/v1/nachweis", params={"entity_type": "gate_vorgaenge"}, headers=auditor.kopf
    ).json()
    zeitfeld = next(a for a in eintraege[0]["aenderungen"] if a["feld"] == "entschieden_am")
    # „2026-09-02 18:13" statt „2026-09-02T18:13:52.392292+00:00".
    assert len(zeitfeld["nachher"]) == 16
    assert "T" not in zeitfeld["nachher"]
    # Und die entscheidende Person mit Namen.
    personenfeld = next(a for a in eintraege[0]["aenderungen"] if a["feld"] == "entschieden_von")
    assert personenfeld["nachher"] == "Governance"
