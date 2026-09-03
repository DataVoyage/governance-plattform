"""``python -m app.bestand`` — den Datenbestand aufbauen.

Der Aufbau schreibt in die Datenbank aus ``GP_DATABASE_URL``. Er laeuft nur auf
einer leeren Datenbank; ``--leeren`` verwirft vorher den Inhalt. Das ist
destruktiv und deshalb ausdruecklich anzufordern — es gibt keinen Schalter, der
das aus Versehen tut.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime

from sqlalchemy import text

from app.bestand.aufbau import baue, ist_leer
from app.db import get_engine, get_sessionmaker

logger = logging.getLogger("bestand")


def leere(schweigend: bool = False) -> None:
    """Leert alle Tabellen ausser der Alembic-Version."""
    with get_engine().begin() as verbindung:
        namen = [
            zeile[0]
            for zeile in verbindung.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
                )
            )
        ]
        if not namen:
            return
        tabellen = ", ".join(f'"{name}"' for name in namen)
        verbindung.execute(text(f"TRUNCATE TABLE {tabellen} RESTART IDENTITY CASCADE"))
    if not schweigend:
        logger.info("Bestand geleert: %s Tabellen", len(namen))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Datenbestand einer Einzelhandelsgruppe aufbauen")
    parser.add_argument(
        "--leeren",
        action="store_true",
        help="vorhandenen Inhalt vorher verwerfen (destruktiv)",
    )
    parser.add_argument(
        "--stichtag",
        help="Bezugstag im Format JJJJ-MM-TT; alle Zeitangaben zaehlen von hier zurueck",
    )
    parser.add_argument("--still", action="store_true", help="keine Fortschrittsmeldungen")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    heute = (
        datetime.fromisoformat(args.stichtag).replace(tzinfo=UTC)
        if args.stichtag
        else datetime.now(UTC)
    )

    if args.leeren:
        leere(args.still)

    with get_sessionmaker()() as sitzung:
        if not ist_leer(sitzung):
            logger.error(
                "Die Datenbank ist nicht leer. Der Aufbau wuerde einen Mischbestand "
                "erzeugen, in dem niemand mehr unterscheiden kann, was woher stammt.\n"
                "Mit --leeren laeuft er nach dem Verwerfen des Inhalts."
            )
            return 2
        melde = None if args.still else (lambda name: logger.info("  fertig: %s", name))
        bericht = baue(sitzung, heute=heute, melde=melde)
        sitzung.commit()

    if not args.still:
        logger.info(
            "\nBestand aufgebaut in %.0f Sekunden:\n%s",
            bericht.sekunden,
            bericht.als_text(),
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
