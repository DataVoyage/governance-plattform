/**
 * V-ANM — Zugang, Sprache, Darstellung.
 *
 * Die Vorgänge, die jeder Anwender in jeder Sitzung durchläuft, bevor er
 * überhaupt zu einem Fachgegenstand kommt.
 */

import { expect } from '@playwright/test';

import {
  ADMIN,
  anmelden,
  anwenderMitRolle,
  kennzeichen,
  organisation,
  prozessAnlegen,
  vorgang,
  type Organisation,
} from './hilfen';

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

vorgang('V-ANM-07', async ({ page }) => {
  // Der Fall, den jeder geteilte Link ausloest: die Adresse traegt Ansicht und
  // Filter, der Empfaenger ist noch nicht angemeldet. Landete er danach auf der
  // Prozessliste, waere die Zusage aus Architektur 9.3 gebrochen, genau in dem
  // Moment, in dem sie zaehlt.
  await page.context().clearCookies();
  await page.goto('/de/cockpit/datenobjekte_ohne_kategorie');
  await expect(page).toHaveURL(/\/de\/anmeldung/);

  await page.getByLabel('Kennung').fill(ADMIN);
  await page.getByLabel('Name').fill('Vorgangs-Administrator');
  await page.getByRole('button', { name: 'Anmelden' }).click();

  await expect(page).toHaveURL(/\/de\/cockpit\/datenobjekte_ohne_kategorie/);
  await expect(page.getByRole('heading', { name: 'Datenobjekte ohne Kategorie' })).toBeVisible();
});

vorgang('V-ANM-08', async ({ page }) => {
  // Das Vorgehen erklaert sich dort, wo damit gearbeitet wird — und nicht nur
  // in einer Datei daneben. Geprueft wird beides: dass der Vortrag traegt und
  // dass eine einzelne Folie eine teilbare Adresse hat.
  await anmelden(page);
  await page.getByRole('link', { name: 'Konzept' }).click();
  await expect(page.getByRole('heading', { name: 'Konzept und Vorgehen' })).toBeVisible();
  await expect(page.getByTestId('folie-1')).toBeVisible();

  await page.getByRole('button', { name: 'Weiter' }).click();
  await expect(page.getByTestId('folie-2')).toBeVisible();
  await expect(page).toHaveURL(/folie=2/);

  // Dieselbe Adresse, frisch aufgerufen, zeigt dieselbe Folie.
  await page.goto('/de/konzept?folie=12');
  await expect(page.getByTestId('folie-12')).toBeVisible();

  // Und die Dokumentansicht setzt alles untereinander.
  await page.getByRole('button', { name: 'Dokument' }).click();
  await expect(page.getByRole('heading', { name: 'Zusammengefasst' })).toBeVisible();
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
  await page
    .getByRole('group', { name: 'Darstellung' })
    .getByRole('button', { name: 'Hell' })
    .click();

  // Der Browser malt seine eigenen Flächen — sie müssen der Wahl folgen (E-27).
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).colorScheme)).toBe(
    'light',
  );

  await page.goto('/de/stilprobe');
  const waehler = page.getByTestId('waehler-stilprobe');
  await waehler.getByRole('combobox').click();
  const farben = await page.evaluate(() => {
    const flaeche = getComputedStyle(
      document.querySelector('.k-referenz .treffer')!,
    ).backgroundColor;
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

vorgang('V-ANM-09', async ({ page }) => {
  // Eine Folie, die unten abgeschnitten ist, merkt niemand beim Schreiben —
  // sie fällt erst vor Publikum auf. Deshalb wird jede einzelne vermessen:
  // passt ihr Inhalt in die Fläche, in der sie gezeigt wird?
  await anmelden(page);
  await page.goto('/de/konzept');
  await expect(page.getByTestId('folie-1')).toBeVisible();
  const zaehler = (await page.locator('.zaehler').textContent()) ?? '';
  const anzahl = Number(zaehler.split('/')[1].trim());
  expect(anzahl).toBeGreaterThan(30);

  const zuLang: string[] = [];
  for (let nummer = 1; nummer <= anzahl; nummer += 1) {
    await page.goto(`/de/konzept?folie=${nummer}`);
    const folie = page.getByTestId(`folie-${nummer}`);
    await expect(folie).toBeVisible();
    const masse = await folie.evaluate((element) => {
      const rahmen = element.parentElement as HTMLElement;
      return { inhalt: element.scrollHeight, flaeche: rahmen.clientHeight };
    });
    if (masse.inhalt > masse.flaeche) {
      const titel = (await folie.getByRole('heading').first().textContent()) ?? '';
      zuLang.push(`${nummer}: ${titel.trim()} (${masse.inhalt} > ${masse.flaeche})`);
    }
  }
  expect(zuLang, `Diese Folien laufen über:\n${zuLang.join('\n')}`).toEqual([]);
});

vorgang('V-ANM-10', async ({ page, request }) => {
  // Zwei Zusagen in einem Durchlauf. Erstens: die Anmeldung ist ein Wort in
  // einem Feld — das Namensfeld darf frei bleiben, dann gilt die Kennung auch
  // als Name. Das ist keine Bequemlichkeit: die Anwendung übernimmt den Namen
  // aus der Identität (Architektur 10.1), und ein abweichender Name im Bestand
  // würde beim ersten Anmelden überschrieben (E-62). Zweitens: wer die Sicht
  // wechselt, sieht dasselbe Objekt mit den Rechten des neuen Zugangs.
  const marke = kennzeichen();
  const org: Organisation = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, {
    name: `Zwei Sichten ${marke}`,
    umsetzung_land_org_ids: [org.deId],
  });

  const eigner = `eigner-${marke}`;
  const umsetzer = `umsetzer-${marke}`;
  await anwenderMitRolle(
    request,
    eigner,
    eigner,
    'prozess_owner',
    'fachbereich',
    org.fachbereichId,
  );
  await anwenderMitRolle(
    request,
    umsetzer,
    umsetzer,
    'prozess_umsetzer',
    'organisationseinheit',
    org.deId,
  );

  await page.goto('/de/anmeldung');
  await page.getByLabel('Kennung').fill(eigner);
  await page.getByRole('button', { name: 'Anmelden' }).click();
  await expect(page.getByRole('heading', { name: 'Prozessobjekte' })).toBeVisible();
  // Der Zugang heisst, wie er sich anmeldet — nicht anders.
  await expect(page.getByText(eigner)).toBeVisible();

  await page.goto(`/de/prozesse/${prozess.id}`);
  await expect(page.getByRole('link', { name: 'Bearbeiten' })).toBeVisible();

  await page.getByRole('button', { name: 'Abmelden' }).click();
  await expect(page).toHaveURL(/\/de\/anmeldung/);
  await page.getByLabel('Kennung').fill(umsetzer);
  await page.getByRole('button', { name: 'Anmelden' }).click();
  await expect(page.getByText(umsetzer)).toBeVisible();

  // Dasselbe Objekt, andere Rechte: sichtbar, aber nicht zu bearbeiten.
  await page.goto(`/de/prozesse/${prozess.id}`);
  await expect(page.getByRole('heading', { name: `Zwei Sichten ${marke}` })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Bearbeiten' })).toHaveCount(0);
});
