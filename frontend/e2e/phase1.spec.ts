/**
 * Abnahme von Phase 1 durch die Oberflaeche, gefahren in einem headless
 * Browser gegen ein laufendes Backend.
 *
 * Geprueft werden die Kriterien 1.1 (Anmeldung), 1.3 (zehn Felder,
 * Stellvertretung als Pflichtfeld), 1.5 (n:m-Umsetzung in zwei Laender) und
 * 1.7 (Sprachwechsel aendert die Anzeige, nicht die Daten).
 */

import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const API = 'http://127.0.0.1:8100';
const ADMIN = 'e2e-admin';

async function token(anfrage: APIRequestContext, subject: string, name: string): Promise<string> {
  const antwort = await anfrage.post(`${API}/api/v1/auth/dev-token`, {
    data: { subject, email: `${subject}@beispiel-ag.de`, name },
  });
  expect(antwort.ok()).toBeTruthy();
  return (await antwort.json()).access_token;
}

/** Legt ueber die API einen Fachbereich mit INT- und zwei LAND-Einheiten an. */
async function stammdaten(anfrage: APIRequestContext) {
  const admin = await token(anfrage, ADMIN, 'E2E Administrator');
  const kopf = { Authorization: `Bearer ${admin}` };
  const code = `fb-${Date.now().toString(36)}`;

  const fachbereich = await (
    await anfrage.post(`${API}/api/v1/fachbereiche`, {
      headers: kopf,
      data: { name: `Finance ${code}`, code },
    })
  ).json();

  const einheit = async (ebene: string, land_code?: string) =>
    (
      await anfrage.post(`${API}/api/v1/organisationseinheiten`, {
        headers: kopf,
        data: { fachbereich_id: fachbereich.id, ebene, land_code },
      })
    ).json();

  return {
    admin,
    int: await einheit('INT'),
    de: await einheit('LAND', 'DE'),
    fr: await einheit('LAND', 'FR'),
  };
}

async function anmelden(seite: Page, subject: string, name: string) {
  await seite.goto('/de/anmeldung');
  await seite.getByLabel('Kennung').fill(subject);
  await seite.getByLabel('Name').fill(name);
  await seite.getByRole('button', { name: 'Anmelden' }).click();
  await expect(seite.getByRole('heading', { name: 'Prozessobjekte' })).toBeVisible();
}

test.describe('Phase 1 in der Oberflaeche', () => {
  test('ohne Anmeldung fuehrt jeder Weg zur Anmeldemaske', async ({ page }) => {
    await page.goto('/de/prozesse');
    await expect(page.getByRole('heading', { name: 'Anmeldung' })).toBeVisible();
  });

  test('Prozess anlegen, in zwei Laendern umsetzen, Sprache wechseln', async ({
    page,
    request,
  }) => {
    const daten = await stammdaten(request);
    await anmelden(page, ADMIN, 'E2E Administrator');

    await page.getByRole('link', { name: 'Prozessobjekt anlegen' }).click();

    // Ohne Stellvertretung laesst sich nicht absenden (Abnahmekriterium 1.3).
    await page.getByLabel('Name').fill('Rechnungspruefung');
    await page.getByRole('button', { name: 'Speichern' }).click();
    await expect(page.getByLabel('Stellvertretung')).toBeFocused();

    await page.getByLabel('Prozess-Owner').selectOption({ label: 'E2E Administrator' });
    await page.getByLabel('Stellvertretung').selectOption({ label: 'E2E Administrator' });
    await page.getByLabel('Prozessgeber (INT)').selectOption(daten.int.id.slice(0, 8));
    await page.getByLabel('Lieferant').fill('Kreditorenbuchhaltung');
    await page.getByLabel('Prozessschritte').fill('Pruefen, freigeben, buchen');
    await page.getByLabel('Ergebnis').fill('Freigegebene Rechnung');
    await page.getByLabel('Kundenkreis').selectOption('bereich');
    await page.getByLabel('Ausfallfolge').selectOption('spuerbar');
    await page.getByLabel('LAND-DE').check();
    await page.getByLabel('LAND-FR').check();
    await page.getByRole('button', { name: 'Speichern' }).click();

    await expect(page.getByRole('heading', { name: 'Rechnungspruefung' })).toBeVisible();

    // Abgeleitet und schreibgeschuetzt: zwei Umsetzungen heben die Reichweite an.
    await expect(page.getByTestId('reichweite')).toHaveText('unternehmen');
    await expect(page.getByTestId('kritikalitaet')).toHaveText('2');
    await expect(page.getByText('LAND-DE')).toBeVisible();
    await expect(page.getByText('LAND-FR')).toBeVisible();

    // Sprachwechsel: andere Anzeige, dieselben Daten (Abnahmekriterium 1.7).
    const vorherigeUmsetzungen = await page.locator('li').allTextContents();
    await page.getByLabel('Sprache').selectOption('fr');
    await expect(page).toHaveURL(/\/fr\/prozesse\//);
    await expect(page.getByText('Dérivé — non saisissable')).toBeVisible();
    await expect(page.getByTestId('reichweite')).toHaveText('unternehmen');
    expect(await page.locator('li').allTextContents()).toEqual(vorherigeUmsetzungen);

    await page.getByRole('link', { name: 'Retour' }).click();
    await expect(page.getByRole('heading', { name: 'Objets de processus' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Rechnungspruefung' })).toBeVisible();
  });

  test('ein Nutzer ohne Rolle sieht keine fremden Prozessobjekte', async ({ page, request }) => {
    await stammdaten(request);
    const fremd = `e2e-fremd-${Date.now()}`;
    await page.goto('/de/anmeldung');
    await page.getByLabel('Kennung').fill(fremd);
    await page.getByLabel('Name').fill('Ohne Rolle');
    await page.getByRole('button', { name: 'Anmelden' }).click();
    await expect(
      page.getByText('In Ihrem Bereich ist noch kein Prozessobjekt erfasst.'),
    ).toBeVisible();
  });
});
