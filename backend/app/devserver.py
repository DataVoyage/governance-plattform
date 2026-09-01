"""Start eines frischen Backends fuer Oberflaechentests und lokale Versuche.

Laeuft gegen dieselbe PostgreSQL wie Entwicklung und Produktion (Architektur
6.5); es gibt keine abweichende Testdatenbank. Fehlt die Zieldatenbank, wird
sie angelegt; danach werden die Migrationen eingespielt und die API gestartet.

``--frisch`` verwirft zuvor das Schema samt Inhalt und baut es neu auf. Das ist
destruktiv und deshalb bewusst nur auf ausdrueckliche Anforderung — ohne die
Option wird ausschliesslich migriert. Welche Datenbank betroffen ist, bestimmt
allein ``GP_DATABASE_URL``: die Oberflaechentests zeigen auf eine eigene
Testdatenbank, nicht auf die der Entwicklung.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn
from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command
from app.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parent.parent


def verwaltungs_url(database_url: str) -> tuple[str, str]:
    """Zerlegt die URL in eine Verbindung zur ``postgres``-Datenbank und den Namen."""
    basis, _, name = database_url.rpartition("/")
    return f"{basis}/postgres", name


def lege_datenbank_an(database_url: str) -> bool:
    """Legt die Zieldatenbank an, falls sie fehlt. Liefert True, wenn neu."""
    verwaltung, name = verwaltungs_url(database_url)
    motor = create_engine(verwaltung, isolation_level="AUTOCOMMIT")
    try:
        with motor.connect() as verbindung:
            vorhanden = verbindung.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
            ).scalar_one_or_none()
            if vorhanden is not None:
                return False
            verbindung.execute(text(f'CREATE DATABASE "{name}"'))
            return True
    finally:
        motor.dispose()


def zuruecksetzen(database_url: str) -> None:
    """Verwirft das Schema samt Inhalt und legt es leer wieder an."""
    motor = create_engine(database_url, isolation_level="AUTOCOMMIT")
    try:
        with motor.connect() as verbindung:
            verbindung.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    finally:
        motor.dispose()


def migrieren() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backend fuer Tests starten")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8100)
    parser.add_argument(
        "--frisch",
        action="store_true",
        help="Schema vorher verwerfen und neu aufbauen (destruktiv)",
    )
    args = parser.parse_args(argv)

    url = get_settings().database_url
    lege_datenbank_an(url)
    if args.frisch:
        zuruecksetzen(url)
    migrieren()
    uvicorn.run("app.main:app", host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
