"""Gemeinsame Testeinrichtung.

Die Tests laufen gegen eine SQLite-Datei je Test. Produktiv ist PostgreSQL
gesetzt (Architektur 6.3); alles Dialektspezifische ist auf den Typ-Adapter
``app.db.GUID`` beschraenkt, sodass die Fachlogik in beiden Faellen dieselbe
ist. Das Schema entsteht in den Tests aus denselben Alembic-Migrationen wie in
Produktion — ein ``create_all`` wuerde sonst Schemafehler verdecken.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def datenbank_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'test.db').as_posix()}"


@pytest.fixture
def umgebung(datenbank_url: str, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("GP_DATABASE_URL", datenbank_url)
    monkeypatch.setenv("GP_AUTH_DEV_MODE", "true")
    monkeypatch.setenv("GP_AUTH_DEV_SECRET", "test-secret")
    monkeypatch.setenv("GP_QUERY_API_SERVICE_TOKENS", "self-service-frontend:service-token-1")
    from app.config import get_settings
    from app.db import reset_engine

    get_settings.cache_clear()
    reset_engine()
    yield
    get_settings.cache_clear()
    reset_engine()


@pytest.fixture
def migriert(umgebung: None, datenbank_url: str) -> None:
    del umgebung
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    alt = os.environ.get("GP_DATABASE_URL")
    os.environ["GP_DATABASE_URL"] = datenbank_url
    try:
        command.upgrade(config, "head")
    finally:
        if alt is not None:
            os.environ["GP_DATABASE_URL"] = alt


@pytest.fixture
def db(migriert: None) -> Iterator[Session]:
    del migriert
    from app.db import get_sessionmaker

    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    finally:
        session.close()


@pytest.fixture
def client(migriert: None) -> Iterator[TestClient]:
    del migriert
    from app.main import erstelle_app

    with TestClient(erstelle_app()) as testclient:
        yield testclient


# --- Hilfen fuer Nutzer, Rollen und Stammdaten ---------------------------


class Anmeldung:
    """Ein angemeldeter Testnutzer samt Authorization-Kopfzeile."""

    def __init__(self, client: TestClient, subject: str, email: str, name: str) -> None:
        antwort = client.post(
            "/api/v1/auth/dev-token",
            json={"subject": subject, "email": email, "name": name},
        )
        assert antwort.status_code == 200, antwort.text
        self.token: str = antwort.json()["access_token"]
        self.client = client
        self.email = email

    @property
    def kopf(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    @property
    def user_id(self) -> str:
        antwort = self.client.get("/api/v1/auth/me", headers=self.kopf)
        assert antwort.status_code == 200, antwort.text
        return antwort.json()["id"]


@pytest.fixture
def anmelden(client: TestClient):
    def _anmelden(name: str = "Test Nutzer", subject: str | None = None) -> Anmeldung:
        kennung = subject or f"sub-{uuid.uuid4().hex[:8]}"
        return Anmeldung(client, kennung, f"{kennung}@beispiel-ag.de", name)

    return _anmelden


@pytest.fixture
def administrator(client: TestClient, anmelden, db: Session) -> Anmeldung:
    """Erster Administrator — im Betrieb per Seed, im Test direkt gesetzt."""
    from app.models.enums import Rolle, ScopeTyp
    from app.models.organisation import Rollenzuweisung, User

    anmeldung = anmelden("App-Administrator", subject="sub-admin")
    user = db.query(User).filter(User.subject == "sub-admin").one()
    db.add(
        Rollenzuweisung(user_id=user.id, rolle=Rolle.APP_ADMINISTRATOR, scope_typ=ScopeTyp.GLOBAL)
    )
    db.commit()
    return anmeldung


@pytest.fixture
def rolle_geben(db: Session):
    def _geben(user_id: str, rolle: str, scope_typ: str = "global", scope_id: str | None = None):
        from app.models.organisation import Rollenzuweisung

        db.add(
            Rollenzuweisung(
                user_id=uuid.UUID(user_id),
                rolle=rolle,
                scope_typ=scope_typ,
                scope_id=uuid.UUID(scope_id) if scope_id else None,
            )
        )
        db.commit()

    return _geben


@pytest.fixture
def organisation(db: Session) -> dict[str, str]:
    """Ein Fachbereich mit INT-Einheit und zwei LAND-Ausprägungen."""
    from app.models.enums import Ebene
    from app.models.organisation import Fachbereich, Organisationseinheit

    finance = Fachbereich(name="Finance", code="fb-fin")
    hr = Fachbereich(name="HR", code="fb-hr")
    db.add_all([finance, hr])
    db.flush()
    fin_int = Organisationseinheit(fachbereich_id=finance.id, ebene=Ebene.INT)
    fin_de = Organisationseinheit(fachbereich_id=finance.id, ebene=Ebene.LAND, land_code="DE")
    fin_fr = Organisationseinheit(fachbereich_id=finance.id, ebene=Ebene.LAND, land_code="FR")
    hr_int = Organisationseinheit(fachbereich_id=hr.id, ebene=Ebene.INT)
    db.add_all([fin_int, fin_de, fin_fr, hr_int])
    db.commit()
    return {
        "fachbereich_finance": str(finance.id),
        "fachbereich_hr": str(hr.id),
        "fin_int": str(fin_int.id),
        "fin_de": str(fin_de.id),
        "fin_fr": str(fin_fr.id),
        "hr_int": str(hr_int.id),
    }


@pytest.fixture
def prozess_daten(anmelden, organisation):
    """Minimal gueltige Nutzlast fuer das Anlegen eines Prozessobjekts."""

    def _daten(owner_id: str, vertretung_id: str, **overrides) -> dict:
        basis = {
            "name": "Rechnungspruefung",
            "owner_user_id": owner_id,
            "stellvertretung_user_id": vertretung_id,
            "prozessgeber_org_id": organisation["fin_int"],
            "supplier": "Kreditorenbuchhaltung",
            "input_datenobjekt_ids": [],
            "process_steps": "Pruefen, freigeben, buchen",
            "output": "Freigegebene Rechnung",
            "customer": "bereich",
            "ausfallfolge": "spuerbar",
        }
        basis.update(overrides)
        return basis

    return _daten
