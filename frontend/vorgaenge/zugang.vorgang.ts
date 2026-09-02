/**
 * V-ANM — Zugang, Sprache, Darstellung.
 *
 * Die Vorgänge, die jeder Anwender in jeder Sitzung durchläuft, bevor er
 * überhaupt zu einem Fachgegenstand kommt.
 */

import { expect } from '@playwright/test';

import { ADMIN, anmelden, vorgang } from './hilfen';

vorgang('V-ANM-01', async ({ page }) => {
  await page.goto('/de/anmeldung');
  await page.getByLabel('Kennung').fill(ADMIN);
  await page.getByLabel('Name').fill('Vorgangs-Administrator');
  await page.getByRole('button', { name: 'Anmelden' }).click();

  await expect(page.getByRole('heading', { name: 'Prozessobjekte' })).toBeVisible();
  await expect(page.getByText('Vorgangs-Administrator')).toBeVisible();
});

vorgang('V-ANM-02', async ({ page }) => {
  await page.context().clearCookies();
  await page.goto('/de/prozesse');
  await expect(page).toHaveURL(/\/de\/anmeldung/);
  await expect(page.getByRole('heading', { name: 'Prozessobjekte' })).toHaveCount(0);
});

vorgang('V-ANM-03', async ({ page }) => {
  await anmelden(page);
  await page.getByRole('button', { name: 'Abmelden' }).click();
  await expect(page).toHaveURL(/\/de\/anmeldung/);

  // Der Rückweg führt nicht zurück in die Anwendung.
  await page.goto('/de/prozesse');
  await expect(page).toHaveURL(/\/de\/anmeldung/);
});

vorgang('V-ANM-04', async ({ page }) => {
  await anmelden(page);
  await page.getByRole('group', { name: 'Sprache' }).getByRole('button', { name: 'FR' }).click();

  await expect(page).toHaveURL(/\/fr\/prozesse/);
  await expect(page.getByRole('heading', { name: 'Objets de processus' })).toBeVisible();

  // Zurück ins Deutsche, ohne dass sich am Gegenstand etwas ändert.
  await page.getByRole('group', { name: 'Langue' }).getByRole('button', { name: 'DE' }).click();
  await expect(page.getByRole('heading', { name: 'Prozessobjekte' })).toBeVisible();
});

vorgang('V-ANM-05', async ({ page }) => {
  await anmelden(page);
  const schalter = page.getByRole('group', { name: 'Darstellung' });
  await schalter.getByRole('button', { name: 'Dunkel' }).click();

  const schema = () => page.evaluate(() => document.documentElement.dataset.farbschema);
  expect(await schema()).toBe('dunkel');

  // Die Wahl gehört dem Anwender, nicht der Sitzung.
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Prozessobjekte' })).toBeVisible();
  expect(await schema()).toBe('dunkel');
});

vorgang('V-ANM-06', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'dark' });
  await anmelden(page);
  await page.getByRole('group', { name: 'Darstellung' }).getByRole('button', { name: 'Hell' }).click();

  // Der Browser malt seine eigenen Flächen — sie müssen der Wahl folgen (E-27).
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).colorScheme)).toBe(
    'light',
  );

  await page.goto('/de/stilprobe');
  const waehler = page.getByTestId('waehler-stilprobe');
  await waehler.getByRole('combobox').click();
  const farben = await page.evaluate(() => {
    const flaeche = getComputedStyle(document.querySelector('.k-referenz .treffer')!).backgroundColor;
    return [...document.querySelectorAll('.k-referenz .treffer li button')].map((knopf) => ({
      name: knopf.querySelector('.haupt')?.firstChild?.textContent ?? '',
      schrift: getComputedStyle(knopf).color,
      eigene: getComputedStyle(knopf).backgroundColor,
      flaeche,
    }));
  });
  const helligkeit = (farbe: string) => {
    const [r, g, b] = (farbe.match(/\d+/g) ?? ['0', '0', '0']).map(Number);
    return 0.299 * r + 0.587 * g + 0.114 * b;
  };
  expect(farben.length).toBeGreaterThan(1);
  for (const zeile of farben) {
    const grund = zeile.eigene.startsWith('rgba(0, 0, 0, 0') ? zeile.flaeche : zeile.eigene;
    expect(zeile.name, 'Treffer ohne sichtbaren Namen').not.toBe('');
    expect(
      Math.abs(helligkeit(zeile.schrift) - helligkeit(grund)),
      `„${zeile.name}": ${zeile.schrift} auf ${grund}`,
    ).toBeGreaterThan(60);
  }
});
