/**
 * V-SEL — Selbstverpflichtung.
 *
 * Die Erklärungen nach A.10.2 und A.10.3, wortgetreu und an die Profilversion
 * gebunden. Der springende Punkt ist nicht das Abhaken, sondern die Bindung:
 * eine Erklärung, die eine Neubewertung überlebt, bezieht sich auf einen
 * Sachverhalt, den es nicht mehr gibt (A.10.4).
 */

import { expect, type APIRequestContext, type Page } from '@playwright/test';

import {
  API,
  anmelden,
  bewerten,
  kennzeichen,
  kopf,
  organisation,
  prozessAnlegen,
  toolAnlegen,
  toolMitProzess,
  vorgang,
  type Organisation,
} from './hilfen';

/** Die Erklärung eines Prozessobjekts über die Oberfläche abgeben. */
async function erklaere(seite: Page, prozessId: string, auslassen: string[] = []) {
  await seite.goto(`/de/prozesse/${prozessId}/selbstverpflichtung`);
  const schalter = seite.getByRole('checkbox');
  await schalter.first().waitFor();
  const anzahl = await schalter.count();
  for (let i = 0; i < anzahl; i += 1) {
    const block = seite.locator('.k-aussage').nth(i);
    const kennung = (await block.getAttribute('data-testid'))?.replace('aussage-', '') ?? '';
    if (auslassen.includes(kennung)) continue;
    await schalter.nth(i).check();
  }
  // Der Klick stößt einen POST an. Wer danach sofort die API fragt, liest an
  // ihm vorbei — deshalb auf die Antwort warten und nicht auf einen Text: der
  // fällt je nach Vollständigkeit der Erklärung anders aus.
  const gespeichert = seite.waitForResponse(
    (antwort) =>
      antwort.url().includes('selbstverpflichtung') && antwort.request().method() === 'POST',
  );
  await seite.getByTestId('sv-abgeben').click();
  await gespeichert;
}

/** Ein Tier-3-Prozess: erst ab Tier 3 ist die Erklärung Aktivierungsbedingung. */
async function tier3(anfrage: APIRequestContext, org: Organisation, marke: string) {
  const prozess = await prozessAnlegen(anfrage, org, { name: `Erklärt ${marke}` });
  await bewerten(anfrage, prozess.id, true);
  return prozess;
}

vorgang('V-SEL-01', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await tier3(request, org, marke);
  await anmelden(page);
  await page.goto(`/de/prozesse/${prozess.id}/selbstverpflichtung`);

  // Die sechs Aussagen aus A.10.2, wortgetreu und einzeln zu bestätigen.
  await expect(page.locator('.k-aussage')).toHaveCount(6);
  for (const kennung of ['PE1', 'PE2', 'PE3', 'PE4', 'PE5', 'PE6']) {
    await expect(page.getByTestId(`aussage-${kennung}`)).toBeVisible();
  }
  await expect(page.getByTestId('aussage-PE3')).toContainText('Empfängerkreis');
  await expect(page.getByTestId('aussage-PE4')).toContainText('Kontrolle einzelner Beschäftigter');
  await expect(page.getByTestId('aussage-PE5')).toContainText('Aufbewahrungspflichten');
  // Keine pauschale Formel — A.10.4 schließt sie aus.
  await expect(page.getByRole('main')).not.toContainText('nach bestem Wissen');

  await erklaere(page, prozess.id);
  await expect(page.getByText('Die Erklärung liegt vor und trägt.')).toBeVisible();
});

vorgang('V-SEL-02', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await tier3(request, org, marke);
  await anmelden(page);

  // Nur fünf der sechs Aussagen bestätigen.
  await erklaere(page, prozess.id, ['PE4']);
  await expect(page.getByText('Nicht alle verlangten Aussagen sind bestätigt.')).toBeVisible();

  // Die Aktivierung wird verweigert und nennt die fehlende Erklärung.
  const antwort = await request.patch(`${API}/api/v1/prozesse/${prozess.id}`, {
    headers: await kopf(request),
    data: { status: 'aktiv' },
  });
  expect(antwort.status()).toBe(422);
  expect(await antwort.text()).toContain('Selbstverpflichtung');
});

vorgang('V-SEL-03', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await tier3(request, org, marke);
  const tool = await toolAnlegen(request, {
    name: `Auswertung ${marke}`,
    technischer_owner_user_id: org.ichId,
  });
  await toolMitProzess(request, tool.id, prozess.id);
  await anmelden(page);

  // Der Weg beginnt am Tool-Objekt — bis AP-5 gab es ihn dort gar nicht.
  await page.goto(`/de/tools/${tool.id}`);
  await page.getByTestId('tool-sv-oeffnen').click();

  await expect(page.locator('.k-aussage')).toHaveCount(6);
  for (const kennung of ['TO1', 'TO2', 'TO3', 'TO4', 'TO5', 'TO6']) {
    await expect(page.getByTestId(`aussage-${kennung}`)).toBeVisible();
  }
  await expect(page.getByTestId('aussage-TO1')).toContainText('Anforderungsklassen');
  await expect(page.getByTestId('aussage-TO2')).toContainText('undeklarierten Datenquellen');
  await expect(page.getByTestId('aussage-TO6')).toContainText('Stellvertretung');

  const schalter = page.getByRole('checkbox');
  for (let i = 0; i < (await schalter.count()); i += 1) await schalter.nth(i).check();
  await page.getByTestId('sv-abgeben').click();
  await expect(page.getByRole('heading', { name: `Auswertung ${marke}` })).toBeVisible();
  await expect(page.getByText('Die Erklärung liegt vor und trägt.')).toBeVisible();
});

vorgang('V-SEL-04', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, { name: `Klein ${marke}` });
  await bewerten(request, prozess.id); // alles verneint -> Tier 1
  await anmelden(page);
  await page.goto(`/de/prozesse/${prozess.id}/selbstverpflichtung`);

  // Kurzform nach A.10.5: nur der Kern, nicht der ganze Katalog.
  await expect(page.locator('.k-aussage')).toHaveCount(3);
  await expect(page.getByTestId('aussage-PE1')).toBeVisible();
  await expect(page.getByTestId('aussage-PE2')).toBeVisible();
  await expect(page.getByTestId('aussage-PE6')).toBeVisible();
  await expect(page.getByTestId('aussage-PE3')).toHaveCount(0);
  await expect(page.getByText(/Kurzform/)).toBeVisible();

  await erklaere(page, prozess.id);
  await expect(page.getByText('Die Erklärung liegt vor und trägt.')).toBeVisible();
});

vorgang('V-SEL-05', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await tier3(request, org, marke);
  await anmelden(page);
  await page.goto(`/de/prozesse/${prozess.id}/selbstverpflichtung`);

  // Ab Tier 2 wird der ganze Katalog verlangt.
  await expect(page.locator('.k-aussage')).toHaveCount(6);
  await expect(page.getByText(/alle Aussagen zu bestätigen/)).toBeVisible();

  // Die Kurzform genügt jetzt nicht mehr.
  await erklaere(page, prozess.id, ['PE3', 'PE4', 'PE5']);
  await expect(page.getByText('Nicht alle verlangten Aussagen sind bestätigt.')).toBeVisible();
});

vorgang('V-SEL-06', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await tier3(request, org, marke);
  await anmelden(page);
  await erklaere(page, prozess.id);
  await expect(page.getByText('Die Erklärung liegt vor und trägt.')).toBeVisible();

  // Neu bewerten — die Erklärung war an die alte Bewertung gebunden.
  const h = await kopf(request);
  const antworten: Record<string, boolean> = Object.fromEntries(
    [
      '1a',
      '1b',
      '1c',
      '2a',
      '2b',
      '2c',
      '3a',
      '3b',
      '3c',
      '4a',
      '4b',
      '4c',
      '5a',
      '5b',
      '5c',
      '6a',
      '6b',
      '6c',
    ].map((frage) => [frage, frage === '2a' || frage === '3a']),
  );
  const neu = await request.post(`${API}/api/v1/prozesse/${prozess.id}/bewertungen`, {
    headers: h,
    data: {
      modus: 'vollstaendig',
      antworten,
      begruendungen: Object.fromEntries(Object.keys(antworten).map((f) => [f, 'Neubewertung.'])),
    },
  });
  expect(neu.status()).toBe(201);

  await page.goto(`/de/prozesse/${prozess.id}`);
  await expect(page.getByText(/überholten Bewertung/)).toBeVisible();
  await expect(page.getByText('Verfallen').first()).toBeVisible();
});

vorgang('V-SEL-07', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await tier3(request, org, marke);
  await anmelden(page);
  await erklaere(page, prozess.id);

  const h = await kopf(request);
  const historie = await (
    await request.get(`${API}/api/v1/prozesse/${prozess.id}/selbstverpflichtungen`, { headers: h })
  ).json();
  // Ab Tier 3 ist die Erklärung befristet.
  expect(historie[0].gueltig_bis).not.toBeNull();

  // Damit der Vorgang die Bestätigung zeigen kann, wird die Gültigkeitsdauer
  // auf null Tage gesetzt — das ist eine echte Governance-Handlung (A.6.6,
  // Vorgang V-RAH-10) und kein Eingriff in die Datenbank. Danach ist die
  // Erklärung mit ihrer Abgabe sofort fällig.
  await request.put(`${API}/api/v1/konfiguration/selbstverpflichtung_gueltigkeit_tage`, {
    headers: h,
    data: { wert: '0' },
  });
  await erklaere(page, prozess.id);
  // Die Frist sofort wieder auf den Regelwert stellen: die eben abgegebene
  // Erklärung trägt ihr Ablaufdatum bereits bei sich, und der Durchlauf soll
  // keine Nullfrist für die folgenden Vorgänge hinterlassen.
  await request.put(`${API}/api/v1/konfiguration/selbstverpflichtung_gueltigkeit_tage`, {
    headers: h,
    data: { wert: '365' },
  });

  await page.goto(`/de/prozesse/${prozess.id}/selbstverpflichtung`);
  await expect(page.getByText(/Jahresfrist ist verstrichen/)).toBeVisible();
  // Ein Klick genügt.
  await page.getByTestId('sv-bestaetigen').click();
  await expect(page.getByText('Die Erklärung liegt vor und trägt.')).toBeVisible();

  // Das Datum wird festgehalten: die alte Erklärung bleibt daneben stehen.
  const danach = await (
    await request.get(`${API}/api/v1/prozesse/${prozess.id}/selbstverpflichtungen`, { headers: h })
  ).json();
  expect(danach.length).toBeGreaterThan(historie.length);
  expect(danach[0].aussagen).toEqual(danach[1].aussagen);
  expect(danach[0].abgegeben_am).not.toBe(danach[1].abgegeben_am);
  // Die Bestätigung gilt wieder ein Jahr.
  expect(danach[0].gueltig_bis).not.toBe(danach[1].gueltig_bis);
});

vorgang('V-SEL-08', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await tier3(request, org, marke);
  await anmelden(page);
  await page.goto(`/de/prozesse/${prozess.id}/selbstverpflichtung`);
  await page.getByTestId('aussage-PE3').waitFor();

  // Der Kommentar ist eingeklappt: er ist die Ausnahme, nicht die Regel.
  await expect(page.getByLabel(/^Kommentar/)).toHaveCount(0);
  await page.getByTestId('kommentar-oeffnen-PE3').click();
  await page.getByLabel('Kommentar — PE3').fill('Empfänger: nur die Konzernrevision.');

  const schalter = page.getByRole('checkbox');
  for (let i = 0; i < (await schalter.count()); i += 1) await schalter.nth(i).check();
  await page.getByTestId('sv-abgeben').click();
  await expect(page.getByText('Die Erklärung liegt vor und trägt.')).toBeVisible();

  // Der Kommentar hängt an der Aussage, nicht an der Erklärung als Ganzes.
  const historie = await (
    await request.get(`${API}/api/v1/prozesse/${prozess.id}/selbstverpflichtungen`, {
      headers: await kopf(request),
    })
  ).json();
  expect(historie[0].aussagen.PE3.kommentar).toContain('Konzernrevision');
  expect(historie[0].aussagen.PE1.kommentar).toBe('');
});
