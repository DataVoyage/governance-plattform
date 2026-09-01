"""Abnahmekriterium Phase 1.1 — Anmeldung ausschliesslich ueber zentrale Identitaet."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

GESCHUETZTE_ROUTEN = [
    ("get", "/api/v1/auth/me"),
    ("get", "/api/v1/prozesse"),
    ("post", "/api/v1/prozesse"),
    ("get", "/api/v1/fachbereiche"),
    ("get", "/api/v1/organisationseinheiten"),
    ("get", "/api/v1/admin/users"),
    ("get", "/api/v1/admin/rollenzuweisungen"),
    ("post", "/api/v1/import/assets"),
    ("get", "/api/v1/konfiguration"),
]


@pytest.mark.parametrize(("methode", "pfad"), GESCHUETZTE_ROUTEN)
def test_ohne_session_liefert_jede_route_401(client: TestClient, methode: str, pfad: str) -> None:
    kwargs = {"json": {}} if methode == "post" else {}
    antwort = getattr(client, methode)(pfad, **kwargs)
    assert antwort.status_code == 401
    assert antwort.headers["www-authenticate"] == "Bearer"


def test_kaputtes_token_liefert_401(client: TestClient) -> None:
    antwort = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer nicht-echt"})
    assert antwort.status_code == 401


def test_falsches_schema_liefert_401(client: TestClient, anmelden) -> None:
    anmeldung = anmelden()
    antwort = client.get("/api/v1/auth/me", headers={"Authorization": f"Basic {anmeldung.token}"})
    assert antwort.status_code == 401


def test_anmeldung_legt_nutzer_an_und_liefert_profil(client: TestClient, anmelden) -> None:
    anmeldung = anmelden("Erika Musterfrau")
    antwort = client.get("/api/v1/auth/me", headers=anmeldung.kopf)
    assert antwort.status_code == 200
    profil = antwort.json()
    assert profil["name"] == "Erika Musterfrau"
    assert profil["rollen"] == []


def test_zweite_anmeldung_erzeugt_keinen_zweiten_nutzer(client: TestClient, anmelden) -> None:
    erste = anmelden("Gleiche Person", subject="sub-stabil")
    zweite = anmelden("Gleiche Person", subject="sub-stabil")
    assert erste.user_id == zweite.user_id


def test_namensaenderung_im_token_wird_uebernommen(client: TestClient, anmelden, db) -> None:
    from app.models.organisation import User

    anmelden("Alter Name", subject="sub-umbenannt")
    anmelden("Neuer Name", subject="sub-umbenannt")
    db.expire_all()
    user = db.query(User).filter(User.subject == "sub-umbenannt").one()
    assert user.name == "Neuer Name"


def test_deaktivierter_nutzer_wird_abgewiesen(client: TestClient, anmelden, db) -> None:
    from app.models.organisation import User

    anmeldung = anmelden(subject="sub-gesperrt")
    user = db.query(User).filter(User.subject == "sub-gesperrt").one()
    user.ist_aktiv = False
    db.commit()
    antwort = client.get("/api/v1/auth/me", headers=anmeldung.kopf)
    assert antwort.status_code == 403


def test_dev_token_route_fehlt_ohne_entwicklungsmodus(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In Produktion darf es keinen zweiten Anmeldeweg geben (Architektur 10.1)."""
    from app.config import get_settings

    monkeypatch.setenv("GP_AUTH_DEV_MODE", "false")
    get_settings.cache_clear()
    antwort = client.post(
        "/api/v1/auth/dev-token",
        json={"subject": "s", "email": "s@beispiel-ag.de", "name": "S"},
    )
    assert antwort.status_code == 404


def test_health_ist_offen(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_erstzugang_vergibt_startrollen(
    client: TestClient, anmelden, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ohne diesen Startpunkt koennte niemand die erste Rolle vergeben."""
    from app.config import get_settings

    monkeypatch.setenv("GP_BOOTSTRAP_ADMIN_SUBJECTS", "sub-erst, sub-zweit")
    get_settings.cache_clear()
    anmeldung = anmelden("Erster Admin", subject="sub-erst")
    profil = client.get("/api/v1/auth/me", headers=anmeldung.kopf).json()
    assert {r["rolle"] for r in profil["rollen"]} == {"app_administrator", "governance"}
    assert all(r["scope_typ"] == "global" for r in profil["rollen"])

    # Erneute Anmeldung verdoppelt die Zuweisungen nicht.
    nochmal = client.get("/api/v1/auth/me", headers=anmeldung.kopf).json()
    assert len(nochmal["rollen"]) == 2


def test_erstzugang_gilt_nur_fuer_konfigurierte_subjects(
    client: TestClient, anmelden, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.config import get_settings

    monkeypatch.setenv("GP_BOOTSTRAP_ADMIN_SUBJECTS", "sub-erst")
    get_settings.cache_clear()
    anmeldung = anmelden("Jemand anderes", subject="sub-anders")
    assert client.get("/api/v1/auth/me", headers=anmeldung.kopf).json()["rollen"] == []
