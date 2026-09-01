"""Sync-Worker (Architektur 6.1) — eigener Container, eigener Lebenszyklus.

Der Worker laeuft als Kubernetes-``CronJob``/``Job`` je Adapter. Er holt
Datensaetze bei einer Quelle ab und uebergibt sie an die Import-API. Er
enthaelt bewusst keine Governance-Logik: die Abgleichsregeln (Architektur 7.2)
liegen im Backend, damit es nur eine Stelle gibt, an der sie gelten.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("sync-worker")


def lade_aus_datei(pfad: Path) -> dict[str, Any]:
    """Quelle: eine JSON-Datei im Import-Vertragsformat (Architektur 7.2).

    Der erste Adapter der zentralen Entwicklungsplattform liefert einen
    Export; Format und Frequenz sind dort offen (Architektur 12, Punkt 3).
    Die Datei-Quelle haelt diesen Anschluss offen, ohne ihn vorwegzunehmen.
    """
    return json.loads(pfad.read_text(encoding="utf-8"))


def lade_aus_http(url: str, token: str | None, ca_bundle: str | None) -> dict[str, Any]:
    kopf = {"Authorization": f"Bearer {token}"} if token else {}
    verify: str | bool = ca_bundle if ca_bundle else True
    antwort = httpx.get(url, headers=kopf, timeout=60.0, verify=verify)
    antwort.raise_for_status()
    return antwort.json()


def sende(
    api_basis: str, nutzlast: dict[str, Any], token: str, ca_bundle: str | None
) -> dict[str, Any]:
    verify: str | bool = ca_bundle if ca_bundle else True
    antwort = httpx.post(
        f"{api_basis.rstrip('/')}/api/v1/import/assets",
        json=nutzlast,
        headers={"Authorization": f"Bearer {token}"},
        timeout=120.0,
        verify=verify,
    )
    antwort.raise_for_status()
    return antwort.json()


def baue_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Governance-Plattform Sync-Worker")
    parser.add_argument("--api", required=True, help="Basis-URL der Backend-API")
    parser.add_argument("--token", required=True, help="Zugangstoken der Plattform-Rolle")
    parser.add_argument("--datei", help="JSON-Datei im Import-Vertragsformat")
    parser.add_argument("--url", help="HTTP-Quelle im Import-Vertragsformat")
    parser.add_argument("--quell-token", help="Token fuer die Quelle, falls noetig")
    parser.add_argument("--ca-bundle", help="Pfad zu einem zusaetzlichen CA-Bundle")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = baue_parser().parse_args(argv)
    if not args.datei and not args.url:
        logger.error("Entweder --datei oder --url angeben")
        return 2
    nutzlast = (
        lade_aus_datei(Path(args.datei))
        if args.datei
        else lade_aus_http(args.url, args.quell_token, args.ca_bundle)
    )
    ergebnis = sende(args.api, nutzlast, args.token, args.ca_bundle)
    logger.info(
        "Import abgeschlossen: %s angelegt, %s aktualisiert, %s unveraendert, "
        "%s Vorschlaege, %s Fehler",
        ergebnis.get("angelegt"),
        ergebnis.get("aktualisiert"),
        ergebnis.get("unveraendert"),
        len(ergebnis.get("vorschlaege", [])),
        len(ergebnis.get("fehler", [])),
    )
    return 1 if ergebnis.get("fehler") else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
