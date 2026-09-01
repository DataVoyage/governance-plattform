"""Geplante Laeufe als Kubernetes-``CronJob`` (Architektur 6.2).

Kein zusaetzliches Job-Queue-System: dieselbe geplante Ausfuehrung wie fuer den
Sync-Worker, nur mit einem anderen Einstiegspunkt. Jeder Lauf ist idempotent —
ein doppelt gestarteter CronJob darf nichts doppelt tun.
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.db import get_sessionmaker

logger = logging.getLogger("jobs")

LAEUFE = ("erinnerungen", "eskalationen")


def erinnerungen() -> int:
    """Erinnert an ablaufende und markiert ueberfaellige Selbstverpflichtungen."""
    from app.services import erinnerung

    with get_sessionmaker()() as session:
        ergebnis = erinnerung.lauf(session)
        session.commit()
    logger.info(
        "Erinnerungen: %s erinnert, %s ueberfaellig",
        len(ergebnis.erinnert),
        len(ergebnis.ueberfaellig),
    )
    return 0


def eskalationen() -> int:
    """Rueckt faellige Lenkungsvorgaenge in die naechste Eskalationsstufe."""
    from app.services import lenkung

    with get_sessionmaker()() as session:
        gerueckt = lenkung.eskaliere_faellige(session)
        session.commit()
    logger.info("Eskalationen: %s Vorgaenge weitergerueckt", len(gerueckt))
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Geplante Laeufe der Governance-Plattform")
    parser.add_argument("lauf", choices=LAEUFE)
    args = parser.parse_args(argv)
    return {"erinnerungen": erinnerungen, "eskalationen": eskalationen}[args.lauf]()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
