/**
 * V-GAT — Gates.
 *
 * Die zwei Gates aus A.11: Gate 1 als Erstfreigabe ab Tier 3, Gate 2 bei einem
 * der fünf benannten Auslöser. Die Liste ist abschließend — ein sechster,
 * freier Grund ist bewusst nicht wählbar, weil er die Liste aushebeln würde.
 */

import { expect, type Page } from '@playwright/test';

import {
  API,
  anmelden,
  anwenderMitRolle,
  bewerten,
  kennzeichen,
  kopf,
  organisation,
  prozessAnlegen,
  vorgang,
} from './hilfen';

/**
 * Die Karte eines Vorgangs im Arbeitsvorrat, über den Prozessnamen gefunden.
 *
 * Der Arbeitsvorrat ist geteilt: er zeigt alles, was offen ist. Ein Zugriff
 * über `.first()` würde in einem gewachsenen Bestand den Vorgang eines anderen
 * treffen — so, wie es einem Menschen auch passieren würde, der nicht hinsieht.
 */
function vorratskarte(seite: Page, prozessName: string) {
  return seite.locator('.k-karte').filter({ hasText: prozessName });
}

/** Die vollständige Erklärung des Prozesseigners über die Oberfläche abgeben. */
async function erklaere(seite: Page, prozessId: string) {
  await seite.goto(`/de/prozesse/${prozessId}/selbstverpflichtung`);
  const schalter = seite.getByRole('checkbox');
  await schalter.first().waitFor();
  for (let i = 0; i < (await schalter.count()); i += 1) await schalter.nth(i).check();
  await seite.getByTestId('sv-abgeben').click();
}

/** Ein Gate über die Oberfläche einreichen. */
async function einreichen(seite: Page, prozessId: string, typ: '1' | '2', ausloeser?: string) {
  await seite.goto(`/de/prozesse/${prozessId}`);
  await seite.getByLabel('Gate').selectOption(typ);
  if (ausloeser !== undefined) await seite.getByLabel('Auslöser').selectOption(ausloeser);
  await seite.getByLabel('Begründung').fill('Erstfreigabe des Prozessobjekts.');
  await seite.getByTestId('gate-einreichen').click();
}

vorgang('V-GAT-01', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, { name: `Freizugeben ${marke}` });
  await bewerten(request, prozess.id, true);
  await anmelden(page);

  await page.goto(`/de/prozesse/${prozess.id}`);
  await expect(
    page.getByText('Für diesen Prozess gibt es noch keinen Gate-Vorgang.'),
  ).toBeVisible();

  await einreichen(page, prozess.id, '1');
  const zeile = page.locator('.k-zeile[data-testid^="gate-"]');
  await expect(zeile).toContainText('Eingereicht');
  await expect(zeile).toContainText('Gate 1');
});

vorgang('V-GAT-02', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, { name: `Aktivierbar ${marke}` });
  await bewerten(request, prozess.id, true);
  await anmelden(page);

  // Vorbedingung der Aktivierung neben dem Gate: die vollständige Erklärung.
  await erklaere(page, prozess.id);

  await einreichen(page, prozess.id, '1');
  await page.goto('/de/gates');
  const karte = vorratskarte(page, prozess.name);
  await karte.getByLabel(/^Entscheidungskommentar/).fill('Geprüft, in Ordnung.');
  await karte.getByRole('button', { name: 'Freigeben' }).click();
  await expect(vorratskarte(page, prozess.name)).toHaveCount(0);

  // Der Prozess ist danach aktivierbar.
  await page.goto(`/de/prozesse/${prozess.id}`);
  await page.getByRole('button', { name: 'Aktivieren' }).click();
  await expect(page.locator('.k-seitenkopf .k-abzeichen').first()).toHaveText('Aktiv');
});

vorgang('V-GAT-03', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, { name: `Abgelehnt ${marke}` });
  await bewerten(request, prozess.id, true);
  await anmelden(page);
  // Die Erklärung liegt vor: so ist die Ablehnung der einzige Grund, aus dem
  // die Aktivierung scheitert.
  await erklaere(page, prozess.id);
  await einreichen(page, prozess.id, '1');

  await page.goto('/de/gates');
  const karte = vorratskarte(page, prozess.name);
  // Ohne Grund keine Ablehnung: wer abgelehnt wird, erfährt sonst nur, dass es
  // nicht weitergeht, aber nicht, was zu ändern wäre.
  await expect(karte.getByRole('button', { name: 'Ablehnen' })).toBeDisabled();
  await karte.getByLabel(/^Entscheidungskommentar/).fill('Die Reichweite ist unklar.');
  await expect(karte.getByRole('button', { name: 'Ablehnen' })).toBeEnabled();
  await karte.getByRole('button', { name: 'Ablehnen' }).click();
  await expect(vorratskarte(page, prozess.name)).toHaveCount(0);

  // Die Ablehnung blockiert die Aktivierung und steht mit ihrem Grund da.
  await page.goto(`/de/prozesse/${prozess.id}`);
  const zeile = page.locator('.k-zeile[data-testid^="gate-"]');
  await expect(zeile).toContainText('Abgelehnt');
  await expect(zeile).toContainText('Die Reichweite ist unklar.');
  await page.getByRole('button', { name: 'Aktivieren' }).click();
  await expect(page.getByRole('alert')).toContainText('Gate 1');
});

vorgang('V-GAT-04', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, { name: `Ohne Auslöser ${marke}` });
  await bewerten(request, prozess.id, true);
  await anmelden(page);

  await page.goto(`/de/prozesse/${prozess.id}`);
  await page.getByLabel('Gate').selectOption('2');
  await page.getByLabel('Begründung').fill('Ohne Angabe des Auslösers.');

  // Das Einreichen ist nicht möglich.
  await expect(page.getByTestId('gate-einreichen')).toBeDisabled();
  await expect(
    page.getByText('Für diesen Prozess gibt es noch keinen Gate-Vorgang.'),
  ).toBeVisible();
});

vorgang('V-GAT-05', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, { name: `Rahmenwechsel ${marke}` });
  await bewerten(request, prozess.id, true);
  await anmelden(page);

  await page.goto(`/de/prozesse/${prozess.id}`);
  await page.getByLabel('Gate').selectOption('2');
  const auswahl = page.getByLabel('Auslöser');
  // Genau die fünf aus A.11 plus Leereintrag — kein freier sechster Grund.
  await expect(auswahl.getByRole('option')).toHaveCount(6);
  const texte = await auswahl.getByRole('option').allTextContents();
  expect(texte).toContain('Reichweitenerweiterung');
  expect(texte).toContain('Neue Datenkategorie');
  expect(texte).toContain('Neues externes Ziel');
  expect(texte).toContain('KI-Komponente ergänzt');
  expect(texte).toContain('Kritikalität gestiegen');

  await einreichen(page, prozess.id, '2', 'neues_externes_ziel');
  await expect(page.locator('.k-zeile[data-testid^="gate-"]')).toContainText('Neues externes Ziel');
});

vorgang('V-GAT-06', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, { name: `Fremdes Gate ${marke}` });
  await bewerten(request, prozess.id, true);
  await anmelden(page);
  await einreichen(page, prozess.id, '1');

  // Ein Prozess-Owner ohne Governance-Rolle sieht seinen Vorgang, aber keine
  // Entscheidung. Die Route prüft unabhängig nach (Architektur 10.2).
  await anwenderMitRolle(
    request,
    `owner-${marke}`,
    `Owner ${marke}`,
    'prozess_owner',
    'organisationseinheit',
    org.intId,
  );
  await page.getByRole('button', { name: 'Abmelden' }).click();
  await anmelden(page, `owner-${marke}`, `Owner ${marke}`);
  await page.goto('/de/gates');
  await expect(page.getByRole('heading', { name: 'Offene Gate-Vorgänge' })).toBeVisible();
  const karte = vorratskarte(page, prozess.name);
  await expect(karte).toBeVisible();
  await expect(karte.getByRole('button', { name: 'Freigeben' })).toHaveCount(0);
  await expect(karte.getByRole('button', { name: 'Ablehnen' })).toHaveCount(0);
  await expect(karte.getByLabel(/^Entscheidungskommentar/)).toHaveCount(0);
});

vorgang('V-GAT-07', async ({ page, request }) => {
  // Ein laufender Prozess steigt auf Tier 3. Bis E-60 lief er unverändert
  // weiter: die Prüfung hing am Statuswechsel, und den hatte er hinter sich.
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, { name: `Aufstieg ${marke}` });

  // Erst harmlos, aktiviert — der reguläre Weg für Tier 1.
  await bewerten(request, prozess.id);
  const aktiviert = await request.patch(`${API}/api/v1/prozesse/${prozess.id}`, {
    headers: await kopf(request),
    data: { status: 'aktiv' },
  });
  expect(aktiviert.status()).toBe(200);

  await anmelden(page);
  await page.goto(`/de/prozesse/${prozess.id}`);
  await expect(page.getByText('Aktiv')).toBeVisible();

  // Neubewertung hebt ihn auf Tier 3.
  await bewerten(request, prozess.id, true);
  await page.reload();

  // Er läuft — aber er ist nicht mehr freigegeben, und die Seite sagt warum.
  await expect(page.getByText('Freigabe ausstehend')).toBeVisible();
  await expect(page.getByText(/nicht freigegeben/)).toBeVisible();

  // Der Gate-1-Vorgang liegt schon vor; niemand musste ihn einreichen.
  await page.goto('/de/gates');
  await expect(vorratskarte(page, prozess.name)).toHaveCount(1);
});
