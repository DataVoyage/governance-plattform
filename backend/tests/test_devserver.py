"""Startskript fuer Oberflaechentests und lokale Versuche."""

from __future__ import annotations

from pathlib import Path

import pytest

from app import devserver


def test_sqlite_pfad_erkennt_dateien() -> None:
    assert devserver.sqlite_pfad("sqlite:///./e2e.db") == Path("e2e.db")
    assert devserver.sqlite_pfad("sqlite:///:memory:") is None
    assert devserver.sqlite_pfad("postgresql+psycopg://a@b/c") is None


def test_zuruecksetzen_loescht_nur_vorhandene_dateien(tmp_path: Path) -> None:
    datei = tmp_path / "weg.db"
    datei.write_text("x", encoding="utf-8")
    devserver.zuruecksetzen(f"sqlite:///{datei.as_posix()}")
    assert not datei.exists()
    # Ein zweiter Aufruf und eine PostgreSQL-URL bleiben folgenlos.
    devserver.zuruecksetzen(f"sqlite:///{datei.as_posix()}")
    devserver.zuruecksetzen("postgresql+psycopg://a@b/c")


def test_main_setzt_zurueck_migriert_und_startet(
    umgebung: None, datenbank_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    del umgebung
    gestartet: dict = {}
    monkeypatch.setattr(
        devserver.uvicorn,
        "run",
        lambda ziel, **kwargs: gestartet.update({"ziel": ziel, **kwargs}),
    )
    assert devserver.main(["--frisch", "--port", "8123"]) == 0
    assert gestartet["ziel"] == "app.main:app"
    assert gestartet["port"] == 8123

    from sqlalchemy import inspect

    from app.db import get_engine

    assert "prozessobjekte" in inspect(get_engine()).get_table_names()
