#!/usr/bin/env bash
# Vollstaendige lokale Pruefung — dasselbe, was zuvor eine Pipeline getan hat.
#
# Reihenfolge ist Absicht: erst das Billige (Stil), dann Migrationen, dann die
# Tests, zuletzt die Images. So faellt der schnellste Fehler zuerst auf.
#
#   ./pruefen.sh            alles ausser den Images
#   ./pruefen.sh --images   zusaetzlich die drei Images gegen zwei Registry-Ziele
set -euo pipefail

WURZEL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIT_IMAGES="${1:-}"

schritt() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }

schritt "Datenbank starten"
docker compose -f "$WURZEL/docker-compose.yml" up -d datenbank
# Warten, bis PostgreSQL Verbindungen annimmt.
for _ in $(seq 1 30); do
  if docker compose -f "$WURZEL/docker-compose.yml" exec -T datenbank \
      pg_isready -U governance >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

schritt "Backend: Stil"
cd "$WURZEL/backend"
uv sync --all-groups --frozen
uv run ruff check .
uv run ruff format --check .

schritt "Backend: Migrationen vorwaerts und rueckwaerts"
GP_DATABASE_URL="postgresql+psycopg://governance:governance@localhost:5432/governance_migration" \
  uv run python - <<'PY'
from sqlalchemy import create_engine, text
motor = create_engine(
    "postgresql+psycopg://governance:governance@localhost:5432/postgres",
    isolation_level="AUTOCOMMIT",
)
with motor.connect() as v:
    v.execute(text("DROP DATABASE IF EXISTS governance_migration"))
    v.execute(text("CREATE DATABASE governance_migration"))
PY
GP_DATABASE_URL="postgresql+psycopg://governance:governance@localhost:5432/governance_migration" \
  uv run alembic upgrade head
GP_DATABASE_URL="postgresql+psycopg://governance:governance@localhost:5432/governance_migration" \
  uv run alembic downgrade base

schritt "Backend: Tests mit Mindestabdeckung 90 %"
uv run pytest --cov

schritt "Frontend: Typpruefung, Build und Tests mit Mindestabdeckung 90 %"
cd "$WURZEL/frontend"
npm ci
npm run build
npm run coverage

schritt "Oberflaeche: technische Laeufe je Phase (Playwright/Chromium)"
# Die aelteren Abnahmetests je Phase. Sie belegen die Fachlogik hinter einem
# Kriterium und bleiben als zweites Netz stehen.
npm run e2e

schritt "Abnahme: die Anwendervorgaenge aus docs/vorgaenge.md"
# Seit AP-10 die Abnahmegrundlage (Befund B15). Die Abnahmekriterien sind als
# Aussagen ueber eine Rolle formuliert — „ein Prozess-Owner kann" —, also als
# Aussagen ueber einen Menschen an einem Bildschirm. Dieser Durchlauf faehrt
# jeden dieser Handgriffe ueber die Oberflaeche, mit eigener Datenbank, und
# haelt Katalog, Umsetzungsplan und docs/phasen.md gegeneinander.
npm run vorgaenge

if [ "$MIT_IMAGES" = "--images" ]; then
  schritt "Images gegen zwei Registry-Ziele (Abnahmekriterium 1.6)"
  # Ohne Codeaenderung, nur ueber das Ziel: derselbe Build, zwei Adressen.
  for registry in "localhost:5000" "registry.intern.beispiel-ag.de/governance"; do
    docker build -t "$registry/governance-backend:pruefung" "$WURZEL/backend"
    docker build -f "$WURZEL/backend/Dockerfile.worker" \
      -t "$registry/governance-sync-worker:pruefung" "$WURZEL/backend"
    docker build -t "$registry/governance-frontend:pruefung" "$WURZEL/frontend"
  done
fi

printf '\n\033[1;32mAlles gruen.\033[0m\n'
