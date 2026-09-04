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
| `docs/` | Phasenstand, Entwurfsentscheidungen und die Vorstellung des Konzepts (die Architekturvorgabe selbst liegt intern) |
| `beispieldaten/` | Beispielexport im Import-Vertragsformat (Architektur 7.2) |

`backend/app/bestand/` baut einen vollständigen Datenbestand einer
Einzelhandelsgruppe auf — siehe [Beispielbestand](#beispielbestand).

Drei getrennte Images, wie in Architektur 6.2 festgelegt: Backend, Frontend,
Sync-Worker. Das Registry-Ziel ist über `GP_IMAGE_REGISTRY` konfigurierbar und
nirgends im Code verankert; `./pruefen.sh --images` baut alle drei gegen zwei
verschiedene Ziele, ohne dass sich am Code etwas ändert.

Dasselbe gilt für die **Herkunft der Basisimages**. Ohne Zutun kommen sie aus
Docker Hub und ghcr.io; wo der Zugang dorthin gesperrt ist, zeigen zwei
Variablen auf den internen Spiegel — der abschließende Schrägstrich gehört zum
Wert, damit die Vorgabe leer bleiben kann:

```bash
cp .env.beispiel .env        # und darin eintragen:
GP_BASIS_PRAEFIX=artifactory.beispiel-ag.de/docker-remote/   # python, node, nginx, postgres
GP_GHCR_PRAEFIX=artifactory.beispiel-ag.de/ghcr-remote/      # astral-sh/uv
```

Zwei Variablen, weil Docker Hub und ghcr.io in Artifactory üblicherweise
getrennte Remote-Repositories sind; bündelt ein virtuelles Repository beide,
bekommen sie denselben Wert. `docker compose` liest die `.env` von selbst,
`./pruefen.sh --images` reicht beide an jeden Build weiter.

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

## Konzeptvorstellung

[`docs/praesentation.md`](docs/praesentation.md) erklärt Konzept und Vorgehen
für Fachbereiche, Betriebsrat, zentrale IT und Prozess-Owner — mit
Bildschirmfotos aus dem Beispielbestand. Der Vortrag bittet um keine Erlaubnis;
er beschreibt den Weg, den diese Anwendung durchsetzt.

Die Datei hat **eine** Quelle und drei Wege, sie zu lesen:

* in der Anwendung unter **Konzept** — als Vortrag mit Pfeiltasten und Vollbild
  oder als durchlaufendes Dokument,
* im Repository als Markdown,
* als Foliensatz:

```bash
npx @marp-team/marp-cli@latest docs/praesentation.md -o praesentation.pdf
```

Deshalb baut das Frontend-Image über dem Wurzelverzeichnis: es liest den
Vortrag und seine Bilder aus `docs/` ein, statt eine Kopie zu pflegen
(`docs/entscheidungen.md`, E-52).

Alle Zahlen darin stammen aus dem Beispielbestand und sind in der laufenden
Anwendung nachzählbar.

## Beispielbestand

Die Anwendung lässt sich mit drei Prozessobjekten bedienen, aber nicht
beurteilen. `app.bestand` füllt sie mit dem, wofür sie gebaut ist: zehn
Fachbereiche einer Einzelhandelsgruppe mit ihren Landesgesellschaften, den
Menschen darin, ihren Datenobjekten, Prozessen und Werkzeugen — und den
Vorgängen daran.

```bash
docker compose exec backend python -m app.bestand --leeren
```

`--leeren` verwirft den vorhandenen Inhalt; ohne die Option läuft der Aufbau
nur auf einer leeren Datenbank. Er dauert wenige Sekunden.

| Was | Anzahl |
|---|---|
| Fachbereiche, Organisationseinheiten, Teams | 10 · 41 · 17 |
| Menschen und Rollenzuweisungen | 70 · 72 |
| Datenobjekte (alle fünf Kategorien aus A.7, dazu die ohne) | 93 |
| Prozessobjekte (Entwurf, aktiv, stillgelegt; Tier 1 bis 3) | 55 |
| Tool-Objekte (vier Technologien, dazu eine ohne) | 72 |
| Bewertungen, Selbstverpflichtungen, Gate-Vorgänge | 76 · 120 · 34 |
| Compliance-Zustände, Lenkungsvorgänge, Kompensationen | 28 · 10 · 30 |
| Protokolleinträge über gut zwei Jahre | ~1100 |

Jeder Datensatz entsteht über dieselbe Geschäftslogik wie im Betrieb, unter der
Kennung des Menschen, der die Handlung täte — mit Berechtigungsprüfung,
Torwächtern und Vorschlagsabgleich. Der Bestand enthält absichtlich jeden
Zustand, den die Anwendung kennt: jede Cockpit-Zeile hat Inhalt, jedes
Rahmenelement wird irgendwo verletzt, alle sechs Verbote aus A.13.2 Schicht 2
kommen vor, und alle drei Eskalationsstufen sind belegt. `tests/test_bestand.py`
hält das fest.

Er legt zugleich **zehn Zugänge für Vorführung und Entwicklung** an — einen je
Rolle, dazu dieselbe Rolle mit zwei Geltungsbereichen und einen ganz ohne
Rolle. Kennung und Name sind jeweils dasselbe eine Wort
(`governance`, `auditor`, `prozessowner`, …); die Tabelle steht in
[`docs/demo-zugaenge.md`](docs/demo-zugaenge.md). Sie funktionieren
ausschließlich im Entwicklungsmodus und haben keine Sonderrechte.

Die Begründung der Entwurfsentscheidungen steht in
[`docs/entscheidungen.md`](docs/entscheidungen.md), E-49.

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

Alles auf einmal — Stil, Migrationen, beide Testsuiten und die
Oberflächentests:

```bash
./pruefen.sh              # ohne Images
./pruefen.sh --images     # zusätzlich die drei Images gegen zwei Registry-Ziele
```

Es gibt bewusst keine Pipeline: geprüft wird lokal, mit genau diesem Skript.

Einzeln ausgeführt brauchen alle Tests eine laufende PostgreSQL:

```bash
docker compose up -d datenbank
```

| Was | Befehl | Mindestabdeckung |
|---|---|---|
| Backend | `cd backend && uv run pytest --cov` | 90 % (erzwungen) |
| Frontend | `cd frontend && npm run coverage` | 90 % (erzwungen) |
| Oberfläche, headless | `cd frontend && npm run e2e` | — |
| Anwendervorgänge | `cd frontend && npm run vorgaenge` | — |

Die Oberflächentests laufen ausschließlich gegen einen **headless** Chromium
(Playwright); es wird kein realer, vom Entwickler bedienter Browser
angesteuert. Playwright startet dafür selbst ein Backend und die gebaute
Single-Page-Application.

**Zwei Durchläufe, zwei Fragen.** `npm run e2e` fährt die Abnahmekriterien je
Phase: *funktioniert es*. `npm run vorgaenge` fährt den Vorgangskatalog aus
[`docs/vorgaenge.md`](docs/vorgaenge.md): *ist es vollständig* — jeder Handgriff,
den ein Anwender später tut, mit seinem erwarteten Ergebnis. Noch nicht
umgesetzte Vorgänge erscheinen als übersprungen mit ihrem Arbeitspaket, statt zu
fehlen; eine Prüfung im Durchlauf hält Katalog und Umsetzungsplan gegeneinander.

Die Testsuite läuft gegen **dieselbe PostgreSQL** wie Entwicklung und
Produktion — es gibt keine abweichende Testdatenbank (Architektur 6.5). Jede
Ebene benutzt eine eigene Datenbank auf demselben Server: `governance` für die
Entwicklung, `governance_test` für die Backend-Tests, `governance_e2e` für die
Oberflächentests und `governance_vorgaenge` für die Anwendervorgänge.
Übersteuerbar über `GP_TEST_DATABASE_URL`, `GP_E2E_DATABASE_URL` beziehungsweise
`GP_VORGAENGE_DATABASE_URL`.

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
| `GP_IMAGE_REGISTRY` | Registry-Ziel der selbst gebauten Images |
| `GP_BASIS_PRAEFIX`, `GP_GHCR_PRAEFIX` | Herkunft der Basisimages (mit Schrägstrich am Ende) |

## Geplante Läufe

Zwei idempotente Läufe, produktiv als Kubernetes-`CronJob` (Architektur 6.2):

```bash
python -m app.jobs erinnerungen   # erinnert an ablaufende Selbstverpflichtungen
python -m app.jobs eskalationen   # rückt fällige Lenkungsvorgänge weiter
```

Dazu ein Wartungslauf, der nicht nach Kalender läuft, sondern nach einem
Release, das eine Ableitungsregel ändert (siehe `docs/entscheidungen.md`, E-19):

```bash
python -m app.jobs ableitungen    # rechnet Reichweite, Kritikalität und Mitbestimmung neu
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
