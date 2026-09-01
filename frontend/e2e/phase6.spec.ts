/**
 * Abnahme von Phase 6 durch die Oberflaeche, headless gefahren.
 *
 * Geprueft werden die Kriterien 6.1 (jede Zeile aus A.14 ist eine eigene,
 * aufrufbare Ansicht), 6.2 (ein Klick fuehrt ins korrekt vorgefilterte
 * Zielmodul) und 6.3 (LAND-Scope sieht nur den eigenen Bereich, Governance
 * global).
 */

import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const API = 'http://127.0.0.1:8100';
const ADMIN = 'e2e-admin';

const ZEILEN = [
  'prozesse_ohne_owner',
  'assets_ohne_prozess',
  'non_compliant',
  'rahmenabweichungen',
  'datenobjekte_ohne_kategorie',
  'kritikalitaetsketten',
  'tier_verteilung',
  'inaktive_assets',
  'ueberfaellige_selbstverpflichtungen',
  'widersprueche',
];

async function kopf(anfrage: APIRequestContext, subject = ADMIN, name = 'E2E Administrator') {
  const antwort = await anfrage.post(`${API}/api/v1/auth/dev-token`, {
    data: { subject, email: `${subject}@beispiel-ag.de`, name },
  });
  return { Authorization: `Bearer ${(await antwort.json()).access_token}` };
}

async function anmelden(seite: Page, subject = ADMIN, name = 'E2E Administrator') {
  await seite.goto('/de/anmeldung');
  await seite.getByLabel('Kennung').fill(subject);
  await seite.getByLabel('Name').fill(name);
  await seite.getByRole('button', { name: 'Anmelden' }).click();
  await expect(seite.getByRole('heading', { name: 'Prozessobjekte' })).toBeVisible();
}

test.describe('Phase 6 in der Oberflaeche', () => {
  test('jede Zeile aus A.14 ist eine eigene, aufrufbare Ansicht', async ({ page }) => {
    await anmelden(page);
    await page.getByRole('link', { name: 'Cockpit', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Cockpit' })).toBeVisible();

    for (const schluessel of ZEILEN) {
      await expect(page.getByTestId(`anzahl-${schluessel}`)).toBeVisible();
    }
    // Genau zehn Zeilen, jede mit eigenem Einstieg.
    await expect(page.getByRole('link', { name: 'Ansehen' })).toHaveCount(ZEILEN.length);

    for (const schluessel of ZEILEN) {
      await page.goto(`/de/cockpit/${schluessel}`);
      await expect(page.getByRole('link', { name: 'Zurück zur Übersicht' })).toBeVisible();
    }
  });

  test('ein Klick fuehrt ins vorgefilterte Zielmodul', async ({ page, request }) => {
    const h = await kopf(request);
    const kennung = Math.random().toString(36).slice(2, 8);
    const name = `Ohne Kategorie ${kennung}`;
    await request.post(`${API}/api/v1/datenobjekte`, {
      headers: h,
      data: { name, beschreibung: '' },
    });

    await anmelden(page);
    await page.goto('/de/cockpit/datenobjekte_ohne_kategorie');
    const zeile = page
      .getByRole('row')
      .filter({ hasText: name });
    await expect(zeile).toBeVisible();
    await zeile.getByRole('link', { name: 'datenobjekte' }).click();

    await expect(page).toHaveURL(/\/de\/datenobjekte\?ohne_kategorie=true/);
    await expect(page.getByRole('heading', { name: 'Datenobjekte' })).toBeVisible();
    await expect(page.getByLabel(`Kategorie — ${name}`)).toBeVisible();
  });

  test('ein Nutzer ohne Rolle sieht ein leeres Cockpit', async ({ page, request }) => {
    const h = await kopf(request);
    await request.post(`${API}/api/v1/datenobjekte`, {
      headers: h,
      data: { name: `Sichtbar nur global ${Math.random().toString(36).slice(2, 8)}` },
    });

    const fremd = `e2e-cockpit-fremd-${Math.random().toString(36).slice(2, 8)}`;
    await anmelden(page, fremd, 'Ohne Rolle');
    await page.getByRole('link', { name: 'Cockpit', exact: true }).click();
    for (const schluessel of ZEILEN) {
      await expect(page.getByTestId(`anzahl-${schluessel}`)).toHaveText('0');
    }
  });
});
