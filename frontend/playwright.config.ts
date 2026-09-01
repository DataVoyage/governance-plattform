import { defineConfig, devices } from '@playwright/test';

/**
 * Oberflaechentests laufen ausschliesslich gegen einen headless Browser —
 * kein realer, vom Entwickler bedienter Browser wird angesteuert.
 *
 * Playwright startet dazu selbst zwei Prozesse: das Backend gegen eine eigene
 * Datenbank in derselben PostgreSQL, die auch Entwicklung und Produktion
 * benutzen (Architektur 6.5), sowie die gebaute Single-Page-Application.
 *
 * Lokal genuegt `docker compose up -d datenbank`; in der Pipeline stellt ein
 * Service-Container dieselbe Datenbank bereit. Die Verbindung laesst sich ueber
 * GP_E2E_DATABASE_URL uebersteuern.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : [['list']],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    headless: true,
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium-headless', use: { ...devices['Desktop Chrome'], headless: true } }],
  webServer: [
    {
      command:
        'uv run --directory ../backend python -m app.devserver --frisch --host 127.0.0.1 --port 8100',
      url: 'http://127.0.0.1:8100/health',
      reuseExistingServer: false,
      timeout: 180_000,
      env: {
        GP_DATABASE_URL:
          process.env.GP_E2E_DATABASE_URL ??
          'postgresql+psycopg://governance:governance@localhost:5432/governance_e2e',
        GP_AUTH_DEV_MODE: 'true',
        GP_AUTH_DEV_SECRET: 'e2e-geheimnis',
        GP_CORS_ORIGINS: 'http://127.0.0.1:4173,http://localhost:4173',
        GP_BOOTSTRAP_ADMIN_SUBJECTS: 'e2e-admin',
        GP_QUERY_API_SERVICE_TOKENS: 'self-service-frontend:e2e-service-token',
      },
    },
    {
      command: 'npm run build && npm run preview -- --port 4173 --host 127.0.0.1',
      url: 'http://127.0.0.1:4173',
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
      env: { VITE_API_BASIS: 'http://127.0.0.1:8100' },
    },
  ],
});
