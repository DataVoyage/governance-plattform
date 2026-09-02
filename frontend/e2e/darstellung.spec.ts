/**
 * Die Darstellung trägt, auch wenn Gerät und Anwendung sich widersprechen.
 *
 * Anlass war ein Befund aus dem Betrieb: im Referenz-Wähler blieb nur der
 * hervorgehobene Treffer lesbar, der Name der übrigen stand weiß auf weiß. Die
 * Ursache war eine Regel aus der Zeit vor dem Design-System, die **jeden**
 * ``button`` akzentblau mit weißer Schrift einfärbte; Bausteine mit eigener
 * Fläche, aber ohne eigene Schriftfarbe, erbten daraus die weiße Schrift.
 *
 * Geprüft wird auf der Stilprobe, weil sie alle Bausteine mit festem Bestand
 * zeigt — dieser Test legt damit keine Daten an, die anderen Abnahmen im Weg
 * stünden.
 */

import { expect, test, type Page } from '@playwright/test';

const ADMIN = 'e2e-admin';

async function anmelden(seite: Page) {
  await seite.goto('/de/anmeldung');
  await seite.getByLabel('Kennung').fill(ADMIN);
  await seite.getByLabel('Name').fill('E2E Administrator');
  await seite.getByRole('button', { name: 'Anmelden' }).click();
  await expect(seite.getByRole('heading', { name: 'Prozessobjekte' })).toBeVisible();
}

/** Grobe Helligkeit einer ``rgb(...)``-Angabe, 0 (schwarz) bis 255 (weiss). */
function helligkeit(farbe: string): number {
  const [r, g, b] = (farbe.match(/\d+/g) ?? ['0', '0', '0']).map(Number);
  return 0.299 * r + 0.587 * g + 0.114 * b;
}

/** Schrift und die Flaeche, auf der sie tatsaechlich steht, je Trefferzeile. */
async function trefferfarben(seite: Page) {
  return seite.evaluate(() => {
    const durchsichtig = (farbe: string) =>
      farbe === 'transparent' || farbe.startsWith('rgba(0, 0, 0, 0');
    return [...document.querySelectorAll('.k-referenz .treffer li button')].map((knopf) => {
      const eigene = getComputedStyle(knopf).backgroundColor;
      const flaeche = getComputedStyle(knopf.closest('.treffer') as Element).backgroundColor;
      return {
        name: knopf.querySelector('.haupt')?.firstChild?.textContent ?? '',
        schrift: getComputedStyle(knopf).color,
        grund: durchsichtig(eigene) ? flaeche : eigene,
      };
    });
  });
}

test.describe('Darstellung', () => {
  test('color-scheme folgt der gewaehlten Darstellung, nicht dem Geraet', async ({ browser }) => {
    const kontext = await browser.newContext({ colorScheme: 'dark' });
    const seite = await kontext.newPage();
    await anmelden(seite);

    const gewaehlt = () =>
      seite.evaluate(() => getComputedStyle(document.documentElement).colorScheme);
    const schalter = seite.getByRole('group', { name: 'Darstellung' });

    await schalter.getByRole('button', { name: 'Hell' }).click();
    expect(await gewaehlt()).toBe('light');

    await schalter.getByRole('button', { name: 'Dunkel' }).click();
    expect(await gewaehlt()).toBe('dark');

    // „Auto" ueberlaesst die Wahl wieder dem Geraet.
    await schalter.getByRole('button', { name: 'Auto' }).click();
    expect(await gewaehlt()).toBe('light dark');

    await kontext.close();
  });

  for (const [darstellung, geraet] of [
    ['Hell', 'dark'],
    ['Hell', 'light'],
    ['Dunkel', 'light'],
    ['Dunkel', 'dark'],
    ['Auto', 'dark'],
    ['Auto', 'light'],
  ] as const) {
    test(`Treffer bleiben lesbar: Anwendung „${darstellung}" auf ${geraet}em Geraet`, async ({
      browser,
    }) => {
      const kontext = await browser.newContext({ colorScheme: geraet });
      const seite = await kontext.newPage();
      await anmelden(seite);
      await seite
        .getByRole('group', { name: 'Darstellung' })
        .getByRole('button', { name: darstellung })
        .click();

      await seite.goto('/de/stilprobe');
      const waehler = seite.getByTestId('waehler-stilprobe');
      await waehler.getByRole('combobox').click();
      await expect(waehler.getByRole('option').first()).toBeVisible();

      // Nicht nur vorhanden, sondern sichtbar. Der hervorgehobene Treffer traegt
      // eine eigene Flaeche; verglichen wird je Zeile gegen die, auf der ihre
      // Schrift tatsaechlich steht.
      const zeilen = await trefferfarben(seite);
      expect(zeilen.length).toBeGreaterThan(1);
      for (const zeile of zeilen) {
        expect(zeile.name).not.toBe('');
        expect(
          Math.abs(helligkeit(zeile.schrift) - helligkeit(zeile.grund)),
          `Treffer „${zeile.name}": ${zeile.schrift} auf ${zeile.grund}`,
        ).toBeGreaterThan(60);
      }

      await kontext.close();
    });
  }
});
