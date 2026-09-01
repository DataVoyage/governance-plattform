# Governance-Plattform

Verwaltungsschicht der Governance: das System, in dem Prozessobjekte,
Tool-Objekte und Datenobjekte geführt, bewertet, verknüpft und in ihrem
Compliance-Zustand nachverfolgt werden.

Die verbindliche Vorgabe ist das interne Architekturdokument
„Governance-Plattform — Technische Architektur"; es liegt **nicht** in diesem
Repository. Code, Tests und Dokumentation verweisen darauf über
Abschnittsnummern (`Architektur 8.2`) und auf das übergeordnete Leitdokument
„Governance by Design für Citizen Development und Custom Code" (`Leitdokument
A.13.5`).

Dieses Repository setzt die Vorgabe in sieben einzeln abnehmbaren Phasen um;
Stand und Abnahmenachweis je Phase stehen in [`docs/phasen.md`](docs/phasen.md),
Abweichungen und Auslegungen in [`docs/entscheidungen.md`](docs/entscheidungen.md).

**Was diese Anwendung nicht ist:** Sie provisioniert keine Infrastruktur — keine
GCP-Projekte, keine Kubernetes-Namespaces, keine Apps-Script-Deployments. Solche
Systeme docken über die Adapter- und Integrationsschicht an (Architektur 7).

## Aufbau

| Verzeichnis | Inhalt |
|---|---|
| `backend/` | FastAPI-API, Geschäftslogik, Datenmodell, Alembic-Migrationen, Sync-Worker |
| `frontend/` | React-Single-Page-Application (TypeScript, Vite), Sprachpfad-Routing |
| `docs/` | Phasenstand und Entwurfsentscheidungen (die Architekturvorgabe selbst liegt intern) |
| `beispieldaten/` | Beispielexport im Import-Vertragsformat (Architektur 7.2) |

Drei getrennte Images, wie in Architektur 6.2 festgelegt: Backend, Frontend,
Sync-Worker. Das Registry-Ziel ist über `GP_IMAGE_REGISTRY` konfigurierbar und
nirgends im Code verankert.

## Schnellstart mit Docker Compose

```bash
docker compose up --build
```

- Oberfläche: <http://localhost:5173/de/prozesse>
- API-Dokumentation (OpenAPI): <http://localhost:8000/api/v1/docs>

Für den Erstzugang eine Kennung in `GP_BOOTSTRAP_ADMIN_SUBJECTS` eintragen;
dieses Subject erhält bei seiner ersten Anmeldung global die Rollen
App-Administrator und Governance. Ohne diesen Startpunkt könnte niemand die
erste Rollenzuweisung vornehmen, weil Rollen nur ein App-Administrator vergibt.

Beispieldaten einspielen (Sync-Worker als eigener Container):

```bash
docker compose run --rm sync-worker \
  --api http://backend:8000 --token "<Token der Plattform-Rolle>" \
  --datei /daten/zentrale-entwicklungsplattform.json
```

## Entwicklung ohne Container

```bash
# Datenbank
docker compose up -d datenbank

# Backend
cd backend
uv sync --all-groups
uv run python -m app.devserver

# Frontend
cd frontend
npm ci
VITE_API_BASIS=http://127.0.0.1:8100 npm run dev
```

## Tests

Alle Tests brauchen eine laufende PostgreSQL:

```bash
docker compose up -d datenbank
```

| Was | Befehl | Mindestabdeckung |
|---|---|---|
| Backend | `cd backend && uv run pytest --cov` | 90 % (erzwungen) |
| Frontend | `cd frontend && npm run coverage` | 90 % (erzwungen) |
| Oberfläche, headless | `cd frontend && npm run e2e` | — |

Die Oberflächentests laufen ausschließlich gegen einen **headless** Chromium
(Playwright); es wird kein realer, vom Entwickler bedienter Browser
angesteuert. Playwright startet dafür selbst ein Backend mit temporärer
SQLite-Datenbank und die gebaute Single-Page-Application.

Die Testsuite läuft gegen **dieselbe PostgreSQL** wie Entwicklung und
Produktion — es gibt keine abweichende Testdatenbank (Architektur 6.5). Jede
Ebene benutzt eine eigene Datenbank auf demselben Server: `governance` für die
Entwicklung, `governance_test` für die Backend-Tests, `governance_e2e` für die
Oberflächentests. Übersteuerbar über `GP_TEST_DATABASE_URL` beziehungsweise
`GP_E2E_DATABASE_URL`.

Das Schema entsteht einmal je Testlauf aus denselben Alembic-Migrationen wie in
Produktion; zwischen den Tests werden die Tabellen geleert.

## Konfiguration

Zwei getrennte Mechanismen für zwei Arten von Einstellungen (Architektur 6.6):

- **ENV** (`GP_*`) — wie die Anwendung läuft: Datenbankverbindung, OIDC,
  Registry, CA-Bundle, Log-Level. Ändert sich beim Deployment.
- **`konfiguration`-Tabelle** — was die Anwendung an Governance-Regeln
  durchsetzt: Fristen, Erinnerungsvorlauf, Schwellen. Ändert die
  Governance-Rolle im laufenden Betrieb, ohne Deployment; jede Änderung läuft
  wie jede andere schreibende Aktion über den `change_log`.

| ENV-Variable | Bedeutung |
|---|---|
| `GP_DATABASE_URL` | Verbindungszeichenfolge zur PostgreSQL |
| `GP_TEST_DATABASE_URL` | Datenbank der Backend-Tests |
| `GP_E2E_DATABASE_URL` | Datenbank der Oberflächentests |
| `GP_OIDC_ISSUER`, `GP_OIDC_JWKS_URL`, `GP_OIDC_AUDIENCE` | Zentrale Unternehmensidentität |
| `GP_AUTH_DEV_MODE` | Nur Entwicklung: lokal ausgestellte Token statt OIDC |
| `GP_BOOTSTRAP_ADMIN_SUBJECTS` | Subjects, die beim Erstzugang die Startrollen erhalten |
| `GP_QUERY_API_SERVICE_TOKENS` | `name:token`-Paare andockender Anwendungen |
| `GP_CORS_ORIGINS` | Erlaubte Herkünfte der Single-Page-Application |
| `GP_CA_BUNDLE_PATH` | Zusätzliches CA-Bundle für ausgehende Verbindungen |
| `GP_IMAGE_REGISTRY` | Registry-Ziel der Images |

## Geplante Läufe

Zwei idempotente Läufe, produktiv als Kubernetes-`CronJob` (Architektur 6.2):

```bash
python -m app.jobs erinnerungen   # erinnert an ablaufende Selbstverpflichtungen
python -m app.jobs eskalationen   # rückt fällige Lenkungsvorgänge weiter
```

## Governance-Query-API

Der Anschlusspunkt für die später andockende Infrastruktur-Provisionierung
(Architektur 7.3). Vier Endpunkte, ausschließlich lesend, authentifiziert über
ein Service-Token aus `GP_QUERY_API_SERVICE_TOKENS`:

```
GET /api/v1/query/prozess/{id}/tier
GET /api/v1/query/prozess/{id}/k-klassen
GET /api/v1/query/tool/{id}/erlaubnisrahmen
GET /api/v1/query/changes?since={cursor}&entity_type=bewertung
```

Sie liefern nur Auskünfte und provisionieren nichts; jede
Provisionierungsentscheidung bleibt bei der andockenden Anwendung. Der Cursor
der Delta-Abfrage ist eine Sequenznummer und wird einschließend gelesen: der
gelieferte `naechster_cursor` geht beim nächsten Lauf unverändert als `since`
wieder hinein.
