/**
 * V-ADM — Administration und Rollen.
 *
 * Nutzer, Rollen und Konfiguration — die Anwendung wird selbsttragend. Bis
 * AP-9 waren Rollen nur über die API zu vergeben; wer die Anwendung in Betrieb
 * nehmen wollte, brauchte einen Token und ein Terminal.
 */

import { expect, type APIRequestContext, type Page } from '@playwright/test';

import {
  API,
  anmelden,
  anwenderMitRolle,
  kennzeichen,
  kopf,
  organisation,
  prozessAnlegen,
  vorgang,
  type Organisation,
} from './hilfen';

/** Einen Anwender ohne Rolle anlegen; liefert seine Kennung. */
async function anwender(anfrage: APIRequestContext, subject: string, name: string): Promise<string> {
  const h = await kopf(anfrage, subject, name);
  const ich = await (await anfrage.get(`${API}/api/v1/auth/me`, { headers: h })).json();
  return ich.id;
}

/** Die Zeile eines Nutzers in der Verwaltung öffnen. */
async function nutzerOeffnen(seite: Page, userId: string) {
  await seite.goto('/de/verwaltung');
  await seite.getByTestId(`nutzer-${userId}`).click();
}

vorgang('V-ADM-01', async ({ page, request }) => {
  const marke = kennzeichen();
  const suchbar = await anwender(request, `suchbar-${marke}`, `Suchbar ${marke}`);
  await anwender(request, `versteckt-${marke}`, `Versteckt ${marke}`);
  await anmelden(page);

  await page.goto('/de/verwaltung');
  const zeile = page.getByTestId(`nutzer-${suchbar}`);
  await expect(zeile).toContainText(`Suchbar ${marke}`);
  await expect(zeile).toContainText(`suchbar-${marke}@beispiel-ag.de`);
  await expect(zeile).toContainText('Aktiv');
  await expect(zeile).toContainText('Führungskraft: nicht hinterlegt');

  await page.getByLabel('Nutzer suchen').fill(`Suchbar ${marke}`);
  await expect(page.getByTestId(`nutzer-${suchbar}`)).toBeVisible();
  await expect(page.getByText(`Versteckt ${marke}`)).toHaveCount(0);
});

vorgang('V-ADM-02', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const neuer = await anwender(request, `neu-${marke}`, `Neu ${marke}`);
  await anmelden(page);

  await nutzerOeffnen(page, neuer);
  await expect(page.getByText('Diesem Nutzer ist noch keine Rolle zugewiesen.')).toBeVisible();

  // Die Rolle trägt ihre Erklärung aus A.15 mit — wer zuweist, soll nicht
  // raten, was der Name bedeutet.
  await page.getByLabel('Rolle').selectOption('prozess_owner');
  await expect(page.getByText(/Legt Prozessobjekte im eigenen Bereich an/)).toBeVisible();

  await page.getByLabel('Geltungsbereich').selectOption('organisationseinheit');
  await page.getByLabel('Organisationseinheit').selectOption(org.intId);
  await page.getByTestId('rolle-zuweisen').click();

  // Die Zuweisung steht am Nutzer, mit Rolle und Bereich im Klartext.
  await page.goto('/de/verwaltung');
  const zeile = page.getByTestId(`nutzer-${neuer}`);
  await expect(zeile).toContainText('Prozess-Owner');
  await expect(zeile).toContainText('INT');
});

vorgang('V-ADM-03', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  for (const name of ['Erster', 'Zweiter']) {
    await prozessAnlegen(request, org, { name: `${name} ${marke}` });
  }
  const neuer = await anwender(request, `vorschau-${marke}`, `Vorschau ${marke}`);
  await anmelden(page);

  await nutzerOeffnen(page, neuer);
  await page.getByLabel('Rolle').selectOption('prozess_owner');
  await page.getByLabel('Geltungsbereich').selectOption('organisationseinheit');
  await page.getByLabel('Organisationseinheit').selectOption(org.intId);

  // Die Zahl steht vor der Entscheidung, nicht danach.
  await expect(page.getByTestId('wirkung')).toContainText('2 Prozessobjekte');
  await expect(page.getByText(/Zum Beispiel/)).toContainText(`Erster ${marke}`);
});

vorgang('V-ADM-04', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, { name: `Entzogen ${marke}` });
  const nutzerId = await anwenderMitRolle(
    request,
    `entzug-${marke}`,
    `Entzug ${marke}`,
    'prozess_owner',
    'organisationseinheit',
    org.intId,
  );

  // Vorher sieht er den Prozess.
  await anmelden(page, `entzug-${marke}`, `Entzug ${marke}`);
  await expect(page.getByRole('link', { name: new RegExp(`Entzogen ${marke}`) })).toBeVisible();
  await page.getByRole('button', { name: 'Abmelden' }).click();

  await anmelden(page);
  await nutzerOeffnen(page, nutzerId);
  const zuweisung = page.locator('[data-testid^="zuweisung-"]').first();
  await expect(zuweisung).toContainText('Prozess-Owner');
  await zuweisung.getByRole('button', { name: 'Entziehen' }).click();
  await expect(page.locator('[data-testid^="zuweisung-"]')).toHaveCount(0);
  await page.getByRole('button', { name: 'Abmelden' }).click();

  // Danach nicht mehr — sofort, ohne Zwischenschritt.
  await anmelden(page, `entzug-${marke}`, `Entzug ${marke}`);
  await expect(page.getByRole('link', { name: new RegExp(`Entzogen ${marke}`) })).toHaveCount(0);
  await page.goto(`/de/prozesse/${prozess.id}`);
  await expect(page.getByRole('alert')).toBeVisible();
});

vorgang('V-ADM-05', async ({ page, request }) => {
  const marke = kennzeichen();
  const meiner: Organisation = await organisation(request, marke);
  const fremder = await organisation(request, kennzeichen());
  const meinProzess = await prozessAnlegen(request, meiner, { name: `Meiner ${marke}` });
  const fremdProzess = await prozessAnlegen(request, fremder, { name: `Fremder ${marke}` });

  // Der Administrator vergibt die Rolle über die Oberfläche — das ist die
  // Abnahme dieses Pakets.
  const neuer = await anwender(request, `frisch-${marke}`, `Frisch ${marke}`);
  await anmelden(page);
  await nutzerOeffnen(page, neuer);
  await page.getByLabel('Rolle').selectOption('prozess_owner');
  await page.getByLabel('Geltungsbereich').selectOption('organisationseinheit');
  await page.getByLabel('Organisationseinheit').selectOption(meiner.intId);
  await page.getByTestId('rolle-zuweisen').click();
  await expect(page.locator('[data-testid^="zuweisung-"]')).toHaveCount(1);
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Abmelden' }).click();

  // Genau die Objekte des zugewiesenen Scopes — keine anderen.
  await anmelden(page, `frisch-${marke}`, `Frisch ${marke}`);
  await expect(page.getByRole('link', { name: new RegExp(`Meiner ${marke}`) })).toBeVisible();
  await expect(page.getByRole('link', { name: new RegExp(`Fremder ${marke}`) })).toHaveCount(0);
  await page.goto(`/de/prozesse/${fremdProzess.id}`);
  await expect(page.getByRole('alert')).toBeVisible();
  expect(meinProzess.id).toBeTruthy();
});

vorgang('V-ADM-06', async ({ page, request }) => {
  const marke = kennzeichen();
  await anwender(request, `ohne-${marke}`, `Ohne Rolle ${marke}`);
  await anmelden(page, `ohne-${marke}`, `Ohne Rolle ${marke}`);

  // Nicht verlinkt …
  await expect(
    page.getByRole('navigation').getByRole('link', { name: 'Verwaltung' }),
  ).toHaveCount(0);

  // … und über die Adresse ohne Inhalt: der Server weist ab, die Seite sagt
  // warum (Architektur 10.2).
  await page.goto('/de/verwaltung');
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.locator('[data-testid^="nutzer-"]')).toHaveCount(0);
});

vorgang('V-ADM-07', async ({ page, request }) => {
  const marke = kennzeichen();
  await anwenderMitRolle(
    request,
    `konf-${marke}`,
    `Governance ${marke}`,
    'governance',
    'global',
  );
  await anmelden(page, `konf-${marke}`, `Governance ${marke}`);

  await page.goto('/de/konfiguration');
  await expect(page.getByRole('heading', { name: 'Einstellungen' })).toBeVisible();

  // Fristen, Schwellen und Vorlauf — je eine aus jeder Gruppe.
  await expect(page.getByTestId('einstellung-lenkung_frist_tage_tier1')).toBeVisible();
  await expect(page.getByTestId('einstellung-asset_inaktiv_tage')).toBeVisible();
  await expect(
    page.getByTestId('einstellung-selbstverpflichtung_erinnerung_vorlauf_tage'),
  ).toBeVisible();

  // Ohne Neustart änderbar: der neue Wert steht nach dem Neuladen da.
  const zeile = page.getByTestId('einstellung-asset_inaktiv_tage');
  await zeile.getByLabel('Ab wann ein Tool als inaktiv gilt').fill('200');
  await page.getByTestId('sichern-asset_inaktiv_tage').click();
  await expect(page.getByTestId('sichern-asset_inaktiv_tage')).toHaveText('Gesichert');

  await page.reload();
  await expect(
    page.getByTestId('einstellung-asset_inaktiv_tage').getByRole('textbox'),
  ).toHaveValue('200');

  // Zurückstellen: die Einstellung wirkt global, und der nächste Vorgang soll
  // sie so vorfinden, wie sie gemeint ist (siehe E-35).
  await zeile.getByLabel('Ab wann ein Tool als inaktiv gilt').fill('180');
  await page.getByTestId('sichern-asset_inaktiv_tage').click();
  await expect(page.getByTestId('sichern-asset_inaktiv_tage')).toHaveText('Gesichert');
});
