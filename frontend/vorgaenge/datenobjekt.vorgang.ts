/**
 * V-DAT — Datenobjekt.
 *
 * Nicht Tools klassifizieren, sondern Quellen (Leitdokument A.7). Diese
 * Vorgänge prüfen, dass das in dreißig Sekunden gelingt und dass die Wirkung
 * einer Umklassifizierung vor der Entscheidung sichtbar ist.
 */

import { expect, type Page } from '@playwright/test';

import {
  API,
  anmelden,
  datenobjektAnlegen,
  kennzeichen,
  kopf,
  organisation,
  prozessAnlegen,
  toolAnlegen,
  toolMitProzess,
  vorgang,
} from './hilfen';

async function anlageOeffnen(seite: Page) {
  await seite.goto('/de/datenobjekte');
  await seite.getByRole('button', { name: 'Datenobjekt anlegen' }).first().click();
  return seite.getByRole('dialog');
}

vorgang('V-DAT-01', async ({ page, request }) => {
  const org = await organisation(request);
  const name = `Entgeltdaten ${kennzeichen()}`;
  await anmelden(page);
  const blatt = await anlageOeffnen(page);

  // Reifegrad 1 aus A.7: Name, Kategorie, Owner, Quellsystem — mehr nicht.
  await blatt.getByLabel('Name').fill(name);
  await blatt.getByLabel('Kategorie').selectOption('besondere_kategorie');
  await blatt.getByLabel('Owner').selectOption({ label: 'Vorgangs-Administrator' });
  await blatt.getByLabel('Fachbereich').selectOption({ label: org.fachbereichName });
  await blatt.getByLabel('Quellsystem').fill('SAP HCM');
  await blatt.getByRole('button', { name: 'Speichern' }).click();

  const zeile = page.getByRole('link', { name: new RegExp(name) });
  await expect(zeile).toBeVisible();
  await expect(zeile).toContainText('SAP HCM');
  await expect(zeile).toContainText('Personenbezogen — besonders');
});

vorgang('V-DAT-02', async ({ page, request }) => {
  await organisation(request);
  const name = `Unklassifiziert ${kennzeichen()}`;
  await anmelden(page);
  const blatt = await anlageOeffnen(page);
  await blatt.getByLabel('Name').fill(name);
  await blatt.getByRole('button', { name: 'Speichern' }).click();

  const zeile = page.getByRole('link', { name: new RegExp(name) });
  await expect(zeile).toContainText('Ohne Kategorie');

  // Der Befund ist im Cockpit adressiert, nicht nur in der Liste sichtbar.
  await page.goto('/de/cockpit/datenobjekte_ohne_kategorie');
  await expect(page.getByRole('link').filter({ hasText: name })).toBeVisible();
});

vorgang('V-DAT-03', async ({ page, request }) => {
  await organisation(request);
  await anmelden(page);
  const blatt = await anlageOeffnen(page);

  // Jede Kategorie nennt ihre Beispiele — die Wahl gelingt ohne Rückfrage.
  const optionen = await blatt.getByLabel('Kategorie').locator('option').allTextContents();
  expect(optionen).toContain('Öffentlich — frei zugänglich');
  expect(optionen).toContain('Personenbezogen — besonders — Entgelt, Gesundheit, Leistungsbewertung');
  // Genau fünf Kategorien aus A.7, dazu der Leereintrag.
  expect(optionen).toHaveLength(6);
});

vorgang('V-DAT-04', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const objekt = await datenobjektAnlegen(request, {
    name: `Kontaktdaten ${marke}`,
    kategorie: 'personenbezogen',
    fachbereich_id: org.fachbereichId,
  });
  await prozessAnlegen(request, org, {
    name: `Nutzt als Input ${marke}`,
    input_datenobjekt_ids: [objekt.id],
  });
  await prozessAnlegen(request, org, {
    name: `Erzeugt als Output ${marke}`,
    output_datenobjekt_ids: [objekt.id],
  });
  await anmelden(page);
  await page.goto(`/de/datenobjekte/${objekt.id}`);

  const eingang = page.getByRole('link', { name: new RegExp(`Nutzt als Input ${marke}`) });
  const ausgang = page.getByRole('link', { name: new RegExp(`Erzeugt als Output ${marke}`) });
  await expect(eingang).toContainText('Input');
  await expect(ausgang).toContainText('Output');
});

vorgang('V-DAT-05', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const objekt = await datenobjektAnlegen(request, {
    name: `Buchungen ${marke}`,
    kategorie: 'intern',
    fachbereich_id: org.fachbereichId,
  });
  const tool = await toolAnlegen(request, { name: `Buchungsskript ${marke}` });
  const h = await kopf(request);
  await request.post(`${API}/api/v1/tools/${tool.id}/datenobjekte`, {
    headers: h,
    data: { datenobjekt_id: objekt.id, zugriffsart: 'lesen_schreiben' },
  });
  await anmelden(page);
  await page.goto(`/de/datenobjekte/${objekt.id}`);

  await expect(page.getByRole('link', { name: new RegExp(tool.name) })).toContainText(
    'Liest und schreibt',
  );
});

vorgang('V-DAT-06', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const objekt = await datenobjektAnlegen(request, {
    name: `Leistungsdaten ${marke}`,
    kategorie: 'personenbezogen',
    fachbereich_id: org.fachbereichId,
  });
  await prozessAnlegen(request, org, {
    name: `Auswertung ${marke}`,
    input_datenobjekt_ids: [objekt.id],
  });
  await anmelden(page);
  await page.goto(`/de/datenobjekte/${objekt.id}`);
  await page.getByLabel('Kategorie').selectOption('besondere_kategorie');

  // Die Vorschau steht vor der Entscheidung, nicht danach (A.4.5).
  const blatt = page.getByRole('dialog');
  await expect(blatt).toBeVisible();
  await expect(blatt.getByTestId('wirkung-prozesse')).toContainText('1');
  await expect(blatt.getByTestId('wirkung-mitbestimmung')).toContainText('1');
  await expect(
    blatt.getByText('Diese Änderung macht Prozesse mitbestimmungsrelevant.', { exact: false }),
  ).toBeVisible();
});

vorgang('V-DAT-07', async ({ page, request }) => {
  const org = await organisation(request);
  const objekt = await datenobjektAnlegen(request, {
    name: `Unangetastet ${kennzeichen()}`,
    kategorie: 'intern',
    fachbereich_id: org.fachbereichId,
  });
  await anmelden(page);
  await page.goto(`/de/datenobjekte/${objekt.id}`);
  await page.getByLabel('Kategorie').selectOption('besondere_kategorie');
  await page.getByRole('dialog').getByRole('button', { name: 'Abbrechen' }).click();

  await page.reload();
  await expect(page.getByLabel('Kategorie')).toHaveValue('intern');
});

vorgang('V-DAT-08', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const objekt = await datenobjektAnlegen(request, {
    name: `Umstufung ${marke}`,
    kategorie: 'personenbezogen',
    fachbereich_id: org.fachbereichId,
  });
  const prozess = await prozessAnlegen(request, org, {
    name: `Betroffen ${marke}`,
    input_datenobjekt_ids: [objekt.id],
  });
  await anmelden(page);
  await page.goto(`/de/prozesse/${prozess.id}`);
  await expect(page.getByTestId('mitbestimmung')).toContainText('Nein');

  await page.goto(`/de/datenobjekte/${objekt.id}`);
  await page.getByLabel('Kategorie').selectOption('besondere_kategorie');
  await page.getByRole('button', { name: 'Kategorie übernehmen' }).click();

  // Der Prozess liest die Kategorie, statt sie erneut zu führen (P5).
  await page.goto(`/de/prozesse/${prozess.id}`);
  await expect(page.getByTestId('mitbestimmung')).toContainText('Ja');
});

vorgang('V-DAT-09', async ({ page, request }) => {
  const org = await organisation(request);
  const objekt = await datenobjektAnlegen(request, {
    name: `Zu pflegen ${kennzeichen()}`,
    kategorie: 'intern',
  });
  await anmelden(page);
  await page.goto(`/de/datenobjekte/${objekt.id}`);

  await page.getByLabel('Owner').selectOption({ label: 'Vorgangs-Administrator' });
  await page.getByLabel('Fachbereich').selectOption({ label: org.fachbereichName });
  await page.getByLabel('Quellsystem').fill('SAP FI');
  await page.getByRole('button', { name: 'Speichern' }).click();

  await page.reload();
  await expect(page.getByLabel('Quellsystem')).toHaveValue('SAP FI');
  await expect(page.getByLabel('Owner')).not.toHaveValue('');
});

vorgang('V-DAT-10', async ({ page, request }) => {
  const marke = kennzeichen();
  const h = await kopf(request);
  await request.post(`${API}/api/v1/import/assets`, {
    headers: h,
    data: {
      quelle: 'zentrale-entwicklungsplattform',
      datensaetze: [
        { typ: 'datenobjekt', externe_id: `DO-${marke}`, name: `Importiert ${marke}` },
      ],
    },
  });
  const liste = await (await request.get(`${API}/api/v1/datenobjekte`, { headers: h })).json();
  const objekt = liste.find((d: { name: string }) => d.name === `Importiert ${marke}`);

  await anmelden(page);
  await page.goto(`/de/datenobjekte/${objekt.id}`);
  await expect(page.getByText(/Ursprungssystem|importiert/i).first()).toBeVisible();

  // Die Kategorie bleibt pflegbar — sie ist governance-relevant, kein Stammdatum.
  await page.getByLabel('Kategorie').selectOption('vertraulich');
  await page.getByRole('button', { name: 'Kategorie übernehmen' }).click();
  await page.reload();
  await expect(page.getByLabel('Kategorie')).toHaveValue('vertraulich');
});

vorgang('V-DAT-11', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  await datenobjektAnlegen(request, {
    name: `Findbar ${marke}`,
    quellsystem: 'SAP HCM',
    fachbereich_id: org.fachbereichId,
  });
  await datenobjektAnlegen(request, {
    name: `Daneben ${marke}`,
    quellsystem: 'Confluence',
    fachbereich_id: org.fachbereichId,
  });
  await anmelden(page);
  await page.goto('/de/datenobjekte');

  // Auch das Quellsystem ist ein Suchbegriff — man sucht, woran man sich erinnert.
  await page.getByRole('searchbox', { name: 'Name' }).fill('Confluence');
  await expect(page.getByRole('link', { name: new RegExp(`Daneben ${marke}`) })).toBeVisible();
  await expect(page.getByRole('link', { name: new RegExp(`Findbar ${marke}`) })).toHaveCount(0);
});

vorgang('V-DAT-12', async ({ page, request }) => {
  const marke = kennzeichen();
  const objekt = await datenobjektAnlegen(request, { name: `Ohne Fachbereich ${marke}` });

  // Ein Datenobjekt ohne Fachbereich ist niemandem zugeordnet (Architektur 4.3).
  await anmelden(page, `gast-${marke}`, 'Gast ohne Rolle');
  await page.goto('/de/datenobjekte');
  await expect(page.getByRole('link', { name: new RegExp(objekt.name) })).toHaveCount(0);
});
