"""Startskript fuer Oberflaechentests und lokale Versuche.

Die Tests laufen gegen dieselbe PostgreSQL wie die uebrige Suite; sie legen
sich dafuer eine eigene, wegwerfbare Datenbank an, damit das Zuruecksetzen des
Schemas nichts trifft, was andere Tests brauchen.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect, text

from app import devserver


@pytest.fixture
def wegwerf_url(datenbank_url: str) -> str:
    """Eine eigene Datenbank je Lauf, am Ende wieder entfernt."""
    basis, _, name = datenbank_url.rpartition("/")
    ziel = f"{basis}/{name}_devserver"
    verwaltung = create_engine(f"{basis}/postgres", isolation_level="AUTOCOMMIT")
    with verwaltung.connect() as verbindung:
        verbindung.execute(text(f'DROP DATABASE IF EXISTS "{name}_devserver"'))
    yield ziel
    with verwaltung.connect() as verbindung:
        verbindung.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :name AND pid <> pg_backend_pid()"
            ),
            {"name": f"{name}_devserver"},
        )
        verbindung.execute(text(f'DROP DATABASE IF EXISTS "{name}_devserver"'))
    verwaltung.dispose()


def test_verwaltungs_url_zerlegt_die_verbindung() -> None:
    verwaltung, name = devserver.verwaltungs_url(
        "postgresql+psycopg://a:b@host:5432/governance_test"
    )
    assert verwaltung == "postgresql+psycopg://a:b@host:5432/postgres"
    assert name == "governance_test"


def test_datenbank_wird_nur_einmal_angelegt(wegwerf_url: str) -> None:
    assert devserver.lege_datenbank_an(wegwerf_url) is True
    assert devserver.lege_datenbank_an(wegwerf_url) is False


def test_zuruecksetzen_leert_das_schema(wegwerf_url: str) -> None:
    devserver.lege_datenbank_an(wegwerf_url)
    motor = create_engine(wegwerf_url, isolation_level="AUTOCOMMIT")
    with motor.connect() as verbindung:
        verbindung.execute(text("CREATE TABLE altlast (id integer)"))
    assert "altlast" in inspect(motor).get_table_names()

    devserver.zuruecksetzen(wegwerf_url)
    assert inspect(motor).get_table_names() == []
    motor.dispose()


def test_main_migriert_und_startet(wegwerf_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ohne --frisch wird nur migriert; mit --frisch vorher zurueckgesetzt."""
    from app.config import get_settings
    from app.db import reset_engine

    monkeypatch.setenv("GP_DATABASE_URL", wegwerf_url)
    get_settings.cache_clear()
    reset_engine()

    gestartet: dict = {}
    monkeypatch.setattr(
        devserver.uvicorn,
        "run",
        lambda ziel, **kwargs: gestartet.update({"ziel": ziel, **kwargs}),
    )

    assert devserver.main(["--frisch", "--port", "8123"]) == 0
    assert gestartet["ziel"] == "app.main:app"
    assert gestartet["port"] == 8123

    motor = create_engine(wegwerf_url)
    tabellen = inspect(motor).get_table_names()
    assert "prozessobjekte" in tabellen
    assert "alembic_version" in tabellen

    # Ein zweiter Lauf ohne --frisch laesst bestehende Daten stehen.
    with motor.connect() as verbindung:
        verbindung.execute(text("CREATE TABLE merker (id integer)"))
        verbindung.commit()
    assert devserver.main(["--port", "8124"]) == 0
    assert "merker" in inspect(motor).get_table_names()

    # Mit --frisch ist der Merker weg.
    assert devserver.main(["--frisch", "--port", "8125"]) == 0
    assert "merker" not in inspect(motor).get_table_names()
    motor.dispose()

    get_settings.cache_clear()
    reset_engine()
