import { defineConfig, devices } from '@playwright/test';

/**
 * Oberflaechentests laufen ausschliesslich gegen einen headless Browser —
 * kein realer, vom Entwickler bedienter Browser wird angesteuert.
 *
 * Playwright startet dazu selbst zwei Prozesse: das Backend mit einer
 * temporaeren SQLite-Datenbank und Entwicklungsanmeldung sowie die gebaute
 * Single-Page-Application. Damit prueft der Test dieselbe Container-Topologie
 * wie in Produktion, nur ohne Docker-Umweg in der Pipeline.
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
        GP_DATABASE_URL: 'sqlite:///./e2e.db',
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
