"""Rollenverwaltung und Organisationsmodell (Architektur 4 und 5)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_nur_administrator_darf_rollen_vergeben(
    client: TestClient, anmelden, administrator, organisation
) -> None:
    fremder = anmelden("Ohne Rolle")
    nutzlast = {
        "user_id": fremder.user_id,
        "rolle": "prozess_owner",
        "scope_typ": "organisationseinheit",
        "scope_id": organisation["fin_int"],
    }
    assert (
        client.post(
            "/api/v1/admin/rollenzuweisungen", json=nutzlast, headers=fremder.kopf
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/admin/rollenzuweisungen", json=nutzlast, headers=administrator.kopf
        ).status_code
        == 201
    )


def test_rollenvergabe_ist_idempotent(
    client: TestClient, anmelden, administrator, organisation
) -> None:
    nutzer = anmelden("Prozess-Owner")
    nutzlast = {
        "user_id": nutzer.user_id,
        "rolle": "prozess_owner",
        "scope_typ": "organisationseinheit",
        "scope_id": organisation["fin_int"],
    }
    erste = client.post(
        "/api/v1/admin/rollenzuweisungen", json=nutzlast, headers=administrator.kopf
    )
    zweite = client.post(
        "/api/v1/admin/rollenzuweisungen", json=nutzlast, headers=administrator.kopf
    )
    assert erste.json()["id"] == zweite.json()["id"]


def test_globaler_scope_ohne_scope_id(client: TestClient, anmelden, administrator) -> None:
    nutzer = anmelden("Governance")
    antwort = client.post(
        "/api/v1/admin/rollenzuweisungen",
        json={"user_id": nutzer.user_id, "rolle": "governance", "scope_typ": "global"},
        headers=administrator.kopf,
    )
    assert antwort.status_code == 201


def test_globaler_scope_mit_scope_id_wird_abgelehnt(
    client: TestClient, anmelden, administrator, organisation
) -> None:
    nutzer = anmelden("Governance")
    antwort = client.post(
        "/api/v1/admin/rollenzuweisungen",
        json={
            "user_id": nutzer.user_id,
            "rolle": "governance",
            "scope_typ": "global",
            "scope_id": organisation["fin_int"],
        },
        headers=administrator.kopf,
    )
    assert antwort.status_code == 422


def test_bereichsscope_ohne_scope_id_wird_abgelehnt(
    client: TestClient, anmelden, administrator
) -> None:
    nutzer = anmelden("Prozess-Owner")
    antwort = client.post(
        "/api/v1/admin/rollenzuweisungen",
        json={
            "user_id": nutzer.user_id,
            "rolle": "prozess_owner",
            "scope_typ": "organisationseinheit",
        },
        headers=administrator.kopf,
    )
    assert antwort.status_code == 422


def test_rolle_fuer_unbekannten_nutzer(client: TestClient, administrator) -> None:
    antwort = client.post(
        "/api/v1/admin/rollenzuweisungen",
        json={
            "user_id": "00000000-0000-0000-0000-000000000000",
            "rolle": "governance",
            "scope_typ": "global",
        },
        headers=administrator.kopf,
    )
    assert antwort.status_code == 404


def test_rolle_fuer_unbekannte_organisationseinheit(
    client: TestClient, anmelden, administrator
) -> None:
    nutzer = anmelden("Irgendwer")
    antwort = client.post(
        "/api/v1/admin/rollenzuweisungen",
        json={
            "user_id": nutzer.user_id,
            "rolle": "prozess_owner",
            "scope_typ": "organisationseinheit",
            "scope_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=administrator.kopf,
    )
    assert antwort.status_code == 404


def test_rolle_entziehen(client: TestClient, anmelden, administrator, organisation) -> None:
    nutzer = anmelden("Kurzzeit-Owner")
    angelegt = client.post(
        "/api/v1/admin/rollenzuweisungen",
        json={
            "user_id": nutzer.user_id,
            "rolle": "prozess_owner",
            "scope_typ": "fachbereich",
            "scope_id": organisation["fachbereich_finance"],
        },
        headers=administrator.kopf,
    ).json()
    assert (
        client.delete(
            f"/api/v1/admin/rollenzuweisungen/{angelegt['id']}", headers=administrator.kopf
        ).status_code
        == 204
    )
    assert (
        client.delete(
            f"/api/v1/admin/rollenzuweisungen/{angelegt['id']}", headers=administrator.kopf
        ).status_code
        == 404
    )
    assert client.get("/api/v1/auth/me", headers=nutzer.kopf).json()["rollen"] == []


def test_nutzer_vorablegen_und_doppelt_anlegen(client: TestClient, administrator) -> None:
    nutzlast = {"email": "neue.person@beispiel-ag.de", "name": "Neue Person"}
    erste = client.post("/api/v1/admin/users", json=nutzlast, headers=administrator.kopf)
    assert erste.status_code == 201
    zweite = client.post("/api/v1/admin/users", json=nutzlast, headers=administrator.kopf)
    assert zweite.status_code == 409


def test_nutzerliste_ist_nicht_fuer_jeden(client: TestClient, anmelden, administrator) -> None:
    fremder = anmelden("Ohne Rolle")
    assert client.get("/api/v1/admin/users", headers=fremder.kopf).status_code == 403
    assert client.get("/api/v1/admin/users", headers=administrator.kopf).status_code == 200
    assert client.get("/api/v1/admin/rollenzuweisungen", headers=fremder.kopf).status_code == 403


def test_rollenliste_nach_nutzer_gefiltert(
    client: TestClient, anmelden, administrator, organisation
) -> None:
    nutzer = anmelden("Gefiltert")
    client.post(
        "/api/v1/admin/rollenzuweisungen",
        json={
            "user_id": nutzer.user_id,
            "rolle": "prozess_owner",
            "scope_typ": "organisationseinheit",
            "scope_id": organisation["fin_int"],
        },
        headers=administrator.kopf,
    )
    treffer = client.get(
        f"/api/v1/admin/rollenzuweisungen?user_id={nutzer.user_id}", headers=administrator.kopf
    ).json()
    assert len(treffer) == 1
    assert treffer[0]["user_id"] == nutzer.user_id


# --- Organisationsmodell -------------------------------------------------


def test_fachbereich_anlegen_und_code_kollision(client: TestClient, administrator) -> None:
    erste = client.post(
        "/api/v1/fachbereiche", json={"name": "Sales", "code": "fb-sal"}, headers=administrator.kopf
    )
    assert erste.status_code == 201
    zweite = client.post(
        "/api/v1/fachbereiche",
        json={"name": "Sales International", "code": "fb-sal"},
        headers=administrator.kopf,
    )
    assert zweite.status_code == 409


def test_fachbereich_anlegen_braucht_rolle(client: TestClient, anmelden) -> None:
    fremder = anmelden("Ohne Rolle")
    antwort = client.post(
        "/api/v1/fachbereiche", json={"name": "Sales", "code": "fb-sal"}, headers=fremder.kopf
    )
    assert antwort.status_code == 403


def test_land_einheit_braucht_land_code(client: TestClient, administrator, organisation) -> None:
    antwort = client.post(
        "/api/v1/organisationseinheiten",
        json={"fachbereich_id": organisation["fachbereich_hr"], "ebene": "LAND"},
        headers=administrator.kopf,
    )
    assert antwort.status_code == 422


def test_int_einheit_darf_keinen_land_code_haben(
    client: TestClient, administrator, organisation
) -> None:
    antwort = client.post(
        "/api/v1/organisationseinheiten",
        json={
            "fachbereich_id": organisation["fachbereich_hr"],
            "ebene": "INT",
            "land_code": "DE",
        },
        headers=administrator.kopf,
    )
    assert antwort.status_code == 422


def test_organisationseinheit_anlegen_und_duplikat(
    client: TestClient, administrator, organisation
) -> None:
    nutzlast = {
        "fachbereich_id": organisation["fachbereich_hr"],
        "ebene": "LAND",
        "land_code": "AT",
    }
    assert (
        client.post(
            "/api/v1/organisationseinheiten", json=nutzlast, headers=administrator.kopf
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/organisationseinheiten", json=nutzlast, headers=administrator.kopf
        ).status_code
        == 409
    )


def test_organisationseinheit_fuer_unbekannten_fachbereich(
    client: TestClient, administrator
) -> None:
    antwort = client.post(
        "/api/v1/organisationseinheiten",
        json={
            "fachbereich_id": "00000000-0000-0000-0000-000000000000",
            "ebene": "INT",
        },
        headers=administrator.kopf,
    )
    assert antwort.status_code == 404


def test_organisationseinheiten_filtern(client: TestClient, anmelden, organisation) -> None:
    nutzer = anmelden("Leser")
    alle = client.get("/api/v1/organisationseinheiten", headers=nutzer.kopf).json()
    assert len(alle) == 4
    nur_land = client.get(
        f"/api/v1/organisationseinheiten?fachbereich_id={organisation['fachbereich_finance']}"
        "&ebene=LAND",
        headers=nutzer.kopf,
    ).json()
    assert {e["land_code"] for e in nur_land} == {"DE", "FR"}
    assert len(client.get("/api/v1/fachbereiche", headers=nutzer.kopf).json()) == 2


def test_datenobjekt_owner_wird_je_fachbereich_vergeben(
    client: TestClient, anmelden, administrator, organisation
) -> None:
    """R-11 aus docs/rollen-und-scopes.md: eine Quelle gehoert einer Stelle, keiner Einheit."""
    nutzer = anmelden("Datenobjekt-Owner")
    auf_einheit = {
        "user_id": nutzer.user_id,
        "rolle": "datenobjekt_owner",
        "scope_typ": "organisationseinheit",
        "scope_id": organisation["fin_int"],
    }
    antwort = client.post(
        "/api/v1/admin/rollenzuweisungen", json=auf_einheit, headers=administrator.kopf
    )
    assert antwort.status_code == 422
    auf_fachbereich = {
        **auf_einheit,
        "scope_typ": "fachbereich",
        "scope_id": organisation["fachbereich_finance"],
    }
    assert (
        client.post(
            "/api/v1/admin/rollenzuweisungen", json=auf_fachbereich, headers=administrator.kopf
        ).status_code
        == 201
    )
