"""Start eines frischen Backends fuer Oberflaechentests und lokale Versuche.

Setzt die konfigurierte SQLite-Datei zurueck, spielt die Migrationen ein und
startet die API. Bewusst nur fuer SQLite: gegen PostgreSQL waere ein
Zuruecksetzen der Datenbank durch die Anwendung selbst ein Fussangel.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn
from alembic.config import Config

from alembic import command
from app.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parent.parent


def sqlite_pfad(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite"):
        return None
    _, _, rest = database_url.partition("///")
    return Path(rest.lstrip("/")) if rest and rest != ":memory:" else None


def zuruecksetzen(database_url: str) -> None:
    pfad = sqlite_pfad(database_url)
    if pfad is not None and pfad.exists():
        pfad.unlink()


def migrieren() -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backend fuer Tests starten")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8100)
    parser.add_argument("--frisch", action="store_true", help="SQLite-Datei vorher loeschen")
    args = parser.parse_args(argv)

    url = get_settings().database_url
    if args.frisch:
        zuruecksetzen(url)
    migrieren()
    uvicorn.run("app.main:app", host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
