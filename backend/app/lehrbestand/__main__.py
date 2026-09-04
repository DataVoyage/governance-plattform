"""``python -m app.lehrbestand`` — den kleinen Bestand aufbauen.

Wie ``app.bestand``, nur klein: jede Funktion einmal, kein Rauschen. Der
Aufbau schreibt in die Datenbank aus ``GP_DATABASE_URL`` und läuft nur auf
einer leeren; ``--leeren`` verwirft vorher den Inhalt. Das ist destruktiv und
deshalb ausdrücklich anzufordern.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime

from app.bestand.__main__ import leere
from app.bestand.aufbau import ist_leer
from app.db import get_sessionmaker
from app.lehrbestand.aufbau import baue

logger = logging.getLogger("lehrbestand")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Kleiner Bestand für Entwicklung und Prüfung — jede Funktion genau einmal"
    )
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
        datetime.now(UTC)
        if args.stichtag is None
        else datetime.fromisoformat(args.stichtag).replace(tzinfo=UTC)
    )

    if args.leeren:
        leere(schweigend=args.still)

    with get_sessionmaker()() as session:
        if not ist_leer(session):
            logger.error(
                "Die Datenbank ist nicht leer. Mit --leeren verwerfen oder eine leere benutzen."
            )
            return 1
        melde = None if args.still else (lambda name: logger.info("  %s", name))
        bericht = baue(session, heute=heute, melde=melde)

    if not args.still:
        logger.info("\nLehrbestand aufgebaut in %.1f s:\n%s", bericht.sekunden, bericht.als_text())
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
