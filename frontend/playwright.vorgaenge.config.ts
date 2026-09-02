import { defineConfig, devices } from '@playwright/test';

/**
 * Anwendervorgänge — der inhaltliche Ablauftest, neben den technischen Tests.
 *
 * Getrennt von `playwright.config.ts`, weil beide verschiedene Fragen stellen:
 * die Abnahmetests je Phase prüfen, ob ein Kriterium erfüllt ist; dieser
 * Durchlauf prüft, ob **jeder** Handgriff, den ein Anwender später tun wird,
 * spezifiziert ist und funktioniert. Der Katalog dazu steht in
 * `docs/vorgaenge.md`.
 *
 * Eigene Datenbank und eigene Ports, damit beide Durchläufe nebeneinander
 * laufen können und keiner dem anderen Daten in den Weg legt.
 */
export default defineConfig({
  testDir: './vorgaenge',
  testMatch: '**/*.vorgang.ts',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : [['list']],
  use: {
    baseURL: 'http://127.0.0.1:4174',
    headless: true,
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium-headless', use: { ...devices['Desktop Chrome'], headless: true } }],
  webServer: [
    {
      command:
        'uv run --directory ../backend python -m app.devserver --frisch --host 127.0.0.1 --port 8101',
      url: 'http://127.0.0.1:8101/health',
      reuseExistingServer: false,
      timeout: 180_000,
      env: {
        GP_DATABASE_URL:
          process.env.GP_VORGAENGE_DATABASE_URL ??
          'postgresql+psycopg://governance:governance@localhost:5432/governance_vorgaenge',
        GP_AUTH_DEV_MODE: 'true',
        GP_AUTH_DEV_SECRET: 'vorgaenge-geheimnis',
        GP_CORS_ORIGINS: 'http://127.0.0.1:4174,http://localhost:4174',
        GP_BOOTSTRAP_ADMIN_SUBJECTS: 'vorgang-admin',
        GP_QUERY_API_SERVICE_TOKENS: 'self-service-frontend:vorgang-service-token',
      },
    },
    {
      command: 'npm run build && npm run preview -- --port 4174 --host 127.0.0.1',
      url: 'http://127.0.0.1:4174',
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
      env: { VITE_API_BASIS: 'http://127.0.0.1:8101' },
    },
  ],
});
