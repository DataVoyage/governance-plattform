/**
 * V-COC — Cockpit.
 *
 * Die zwölf Zeilen aus A.14, jede als eigene, aufrufbare Ansicht mit Sprung
 * ins vorgefilterte Zielmodul. A.14 nennt die Abweichung den „eigentlichen
 * Steuerungshebel" — geprüft wird deshalb nicht, dass Zahlen erscheinen,
 * sondern dass jede Zahl zu einem Fall und jeder Fall zu einer Handlung führt.
 */

import { expect, type APIRequestContext, type Page } from '@playwright/test';

import {
  API,
  anmelden,
  anwenderMitRolle,
  bewerten,
  kennzeichen,
  kopf,
  organisation,
  plattformKopf,
  prozessAnlegen,
  toolAnlegen,
  toolMitProzess,
  vorgang,
  type Organisation,
} from './hilfen';

/** Die zwölf Zeilen aus A.14, in der Reihenfolge des Leitdokuments. */
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
  'attestierungen_veraltet',
  'widersprueche',
  'antwort_widerspricht_datenlage',
  'technologie_erfuellt_klasse_nicht',
  'altanwendungen',
];

/** Ein bewerteter Prozess mit Tool — Futter für mehrere Zeilen. */
async function aufbau(anfrage: APIRequestContext, marke: string, org?: Organisation) {
  const bereich = org ?? (await organisation(anfrage, marke));
  const prozess = await prozessAnlegen(anfrage, bereich, { name: `Cockpitprozess ${marke}` });
  await bewerten(anfrage, prozess.id, true);
  const tool = await toolAnlegen(anfrage, {
    name: `Cockpitwerkzeug ${marke}`,
    technologie: 'appsheet',
    organisationseinheit_id: bereich.deId,
  });
  await toolMitProzess(anfrage, tool.id, prozess.id);
  return { org: bereich, prozess, tool };
}

/** Eine Kachel der Übersicht. */
function kachel(seite: Page, schluessel: string) {
  return seite.getByTestId(`kachel-${schluessel}`);
}

vorgang('V-COC-01', async ({ page, request }) => {
  const marke = kennzeichen();
  await aufbau(request, marke);
  await anmelden(page);
  await page.goto('/de/cockpit');

  // Jede Zeile eine Kachel — keine mehr, keine weniger.
  await expect(page.locator('[data-testid^="kachel-"]')).toHaveCount(ZEILEN.length);
  for (const schluessel of ZEILEN) {
    const eine = kachel(page, schluessel);
    await expect(eine).toBeVisible();
    // Zahl, Zustandszeichen und der Satz, was zu tun ist.
    await expect(eine.locator('.zahl')).toHaveText(/^\d+$/);
    await expect(eine.locator('.punkt')).toHaveText(/[✓!]/);
    await expect(eine.locator('.satz')).not.toBeEmpty();
  }
});

vorgang('V-COC-02', async ({ page, request }) => {
  const marke = kennzeichen();
  const { tool } = await aufbau(request, marke);
  await anmelden(page);

  await page.goto('/de/cockpit');
  await kachel(page, 'technologie_erfuellt_klasse_nicht').click();

  // Die Detailliste nennt jeden Einzelfall mit seinem Hinweis.
  const zeile = page.getByTestId(`eintrag-${tool.id}`);
  await expect(zeile).toContainText(`Cockpitwerkzeug ${marke}`);
  await expect(zeile).toContainText('K5 Zugriffs- und Rechtekonzept');
});

vorgang('V-COC-03', async ({ page, request }) => {
  const marke = kennzeichen();
  const { tool } = await aufbau(request, marke);
  await anmelden(page);

  await page.goto('/de/cockpit/technologie_erfuellt_klasse_nicht');
  await page.getByTestId(`eintrag-${tool.id}`).click();

  // Das Zielmodul öffnet auf genau diesem Fall.
  await expect(page.getByRole('heading', { name: `Cockpitwerkzeug ${marke}` })).toBeVisible();
  expect(page.url()).toContain(`/tools/${tool.id}`);
});

vorgang('V-COC-04', async ({ page, request }) => {
  const marke = kennzeichen();
  const { org, tool } = await aufbau(request, marke);
  await anmelden(page);

  await page.goto('/de/cockpit');
  await page.getByLabel('Fachbereich').selectOption(org.fachbereichId);

  // Der Filter steht in der Adresse und ist damit teilbar.
  expect(page.url()).toContain(`fachbereich=${org.fachbereichId}`);

  // Er trägt in die Zeile weiter — und dort steht nur der eigene Bereich.
  await kachel(page, 'technologie_erfuellt_klasse_nicht').click();
  expect(page.url()).toContain(`fachbereich=${org.fachbereichId}`);
  await expect(page.getByTestId(`eintrag-${tool.id}`)).toBeVisible();

  // Ein fremder Fachbereich zeigt diesen Fall nicht.
  const fremd = await organisation(request, kennzeichen());
  await page.goto(
    `/de/cockpit/technologie_erfuellt_klasse_nicht?fachbereich=${fremd.fachbereichId}`,
  );
  await expect(page.getByTestId(`eintrag-${tool.id}`)).toHaveCount(0);
});

vorgang('V-COC-05', async ({ page, request }) => {
  const marke = kennzeichen();
  const meiner = await aufbau(request, marke);
  const fremder = await aufbau(request, kennzeichen());

  // Ein Owner mit Scope auf genau eine Organisationseinheit.
  await anwenderMitRolle(
    request,
    `land-${marke}`,
    `Land-Owner ${marke}`,
    'prozess_owner',
    'organisationseinheit',
    meiner.org.intId,
  );
  await anmelden(page, `land-${marke}`, `Land-Owner ${marke}`);

  await page.goto('/de/cockpit/technologie_erfuellt_klasse_nicht');
  await expect(page.getByTestId(`eintrag-${meiner.tool.id}`)).toBeVisible();
  // Der fremde Fall ist nicht sichtbar — und zwar serverseitig, nicht durch
  // einen Filter in der Adresse (Architektur 4.3).
  await expect(page.getByTestId(`eintrag-${fremder.tool.id}`)).toHaveCount(0);
});

vorgang('V-COC-06', async ({ page, request }) => {
  const marke = kennzeichen();
  await aufbau(request, marke);

  // Ein Anwender ohne jede Rolle: leer, nicht fehlerhaft.
  await anmelden(page, `gast-${marke}`, `Gast ${marke}`);
  await page.goto('/de/cockpit');
  await expect(page.getByRole('heading', { name: 'Cockpit' })).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.locator('[data-testid^="kachel-"]')).toHaveCount(ZEILEN.length);
  for (const schluessel of ZEILEN) {
    await expect(kachel(page, schluessel).locator('.zahl')).toHaveText('0');
  }
});

vorgang('V-COC-07', async ({ page, request }) => {
  const marke = kennzeichen();
  await aufbau(request, marke);
  await anmelden(page);

  await page.goto('/de/cockpit/tier_verteilung');
  const technologie = page.getByTestId('verteilung-je_technologie');
  await expect(technologie).toBeVisible();

  // Achsen: die Kategorie links am Balken, die Menge als Zahl am Segment.
  await expect(technologie.getByText('AppSheet')).toBeVisible();
  await expect(technologie.locator('.segment').first()).toHaveText(/^\d+$/);

  // Zugänglichkeit: die Legende benennt jede Stufe, Farbe trägt nichts allein.
  const karte = page.locator('.k-karte').filter({ hasText: 'Tier-Verteilung je Technologie' });
  await expect(karte.locator('.k-legende .eintrag')).toHaveCount(3);
  await expect(karte.locator('.k-legende')).toContainText('Tier 3');

  // Auch die zweite Achse aus A.14: je Monat.
  await expect(page.getByTestId('verteilung-je_monat')).toBeVisible();
});

vorgang('V-COC-08', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  // Erst passend bewerten, dann die Datenlage ändern: genau der Fall, für den
  // es die Zeile gibt — die Antwort von damals steht neben einer neuen
  // Wirklichkeit (siehe E-30).
  const prozess = await prozessAnlegen(request, org, {
    name: `Widerspruch ${marke}`,
    ausfallfolge: 'keine',
  });
  await bewerten(request, prozess.id, true);
  const h = await kopf(request);
  const geaendert = await request.patch(`${API}/api/v1/prozesse/${prozess.id}`, {
    headers: h,
    data: { ausfallfolge: 'kritisch' },
  });
  expect(geaendert.status()).toBe(200);
  await anmelden(page);

  await page.goto('/de/cockpit/antwort_widerspricht_datenlage');
  // Eine geänderte Ausfallfolge berührt mehrere Fragen des Risikoblocks —
  // deshalb steht der Prozess hier mit je einem Eintrag pro Frage.
  const eintraege = page.getByTestId(`eintrag-${prozess.id}`);
  await expect(eintraege.first()).toContainText(`Widerspruch ${marke}`);
  // Antwort, Vorschlag und der Grund stehen nebeneinander.
  await expect(eintraege.first()).toContainText('geantwortet');
  await expect(eintraege.first()).toContainText('abgeleitet');
  await expect(eintraege.first()).toContainText('Datenlage seit der Bewertung geändert');
});

vorgang('V-COC-09', async ({ page, request }) => {
  const marke = kennzeichen();
  const { tool } = await aufbau(request, marke);
  await anmelden(page);

  await page.goto('/de/cockpit/technologie_erfuellt_klasse_nicht');
  const zeile = page.getByTestId(`eintrag-${tool.id}`);
  // Tool, Klasse und der Grund — mit Namen, nicht mit Kürzeln allein.
  await expect(zeile).toContainText(`Cockpitwerkzeug ${marke}`);
  await expect(zeile).toContainText('K5 Zugriffs- und Rechtekonzept');
  await expect(zeile).toContainText('Ausschluss');
  await expect(zeile).toContainText('Tool-Objekt');

  // Die Technologie steht am Ziel, wohin der Eintrag führt.
  await zeile.click();
  await expect(page.getByRole('heading', { name: `Cockpitwerkzeug ${marke}` })).toBeVisible();
  await expect(page.locator('.k-seitenkopf')).toContainText('AppSheet');
});

vorgang('V-COC-10', async ({ page, request }) => {
  const marke = kennzeichen();
  const h = await plattformKopf(request); // Adapter betreibt nur die Plattform
  const org = await organisation(request, marke);
  // Eine vorgefundene Anwendung, wie sie der Sync anlegt: importiert und
  // unbestätigt. Über die Oberfläche entsteht so etwas nicht — deshalb hier
  // über die Schnittstelle, die auch der Sync benutzt.
  const antwort = await request.post(`${API}/api/v1/import/assets`, {
    headers: h,
    data: {
      quelle: `sync-${marke}`,
      datensaetze: [{ typ: 'tool', externe_id: `alt-${marke}`, name: `Altanwendung ${marke}` }],
    },
  });
  expect(antwort.status()).toBe(200);
  expect(org.fachbereichId).toBeTruthy();

  await anmelden(page);
  await page.goto('/de/cockpit/altanwendungen');
  const zeile = page.getByRole('link').filter({ hasText: `Altanwendung ${marke}` });
  await expect(zeile).toContainText('Meldepfad');
  await expect(zeile).toContainText('noch nicht bestätigt');
});
