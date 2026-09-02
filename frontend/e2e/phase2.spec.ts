/**
 * Abnahme von Phase 2 durch die Oberflaeche, headless gefahren.
 *
 * Geprueft werden die Kriterien 2.1 (Reihenfolge der sechs Bloecke), 2.2
 * (Verbotstatbestand speichert keine Bewertung), 2.3 (schnelle und
 * vollstaendige Variante), 2.4 (Historie) und 2.5 (K-Klassen des
 * durchgerechneten Beispiels).
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

/** Legt ueber die API einen bewertbaren Prozess an und liefert seine ID. */
async function prozessAnlegen(anfrage: APIRequestContext, name: string): Promise<string> {
  const admin = await token(anfrage, ADMIN, 'E2E Administrator');
  const kopf = { Authorization: `Bearer ${admin}` };
  const code = `fb-${Math.random().toString(36).slice(2, 10)}`;

  const fachbereich = await (
    await anfrage.post(`${API}/api/v1/fachbereiche`, {
      headers: kopf,
      data: { name: `Bereich ${code}`, code },
    })
  ).json();
  const int = await (
    await anfrage.post(`${API}/api/v1/organisationseinheiten`, {
      headers: kopf,
      data: { fachbereich_id: fachbereich.id, ebene: 'INT' },
    })
  ).json();
  const ich = await (await anfrage.get(`${API}/api/v1/auth/me`, { headers: kopf })).json();

  const prozess = await (
    await anfrage.post(`${API}/api/v1/prozesse`, {
      headers: kopf,
      data: {
        name,
        owner_user_id: ich.id,
        stellvertretung_user_id: ich.id,
        prozessgeber_org_id: int.id,
        supplier: 'Vorsystem',
        input_datenobjekt_ids: [],
        process_steps: 'Schritte',
        output: 'Ergebnis',
        customer: 'bereich',
        ausfallfolge: 'spuerbar',
      },
    })
  ).json();
  return prozess.id;
}

async function anmelden(seite: Page) {
  await seite.goto('/de/anmeldung');
  await seite.getByLabel('Kennung').fill(ADMIN);
  await seite.getByLabel('Name').fill('E2E Administrator');
  await seite.getByRole('button', { name: 'Anmelden' }).click();
  await expect(seite.getByRole('heading', { name: 'Prozessobjekte' })).toBeVisible();
}

/** Beantwortet die aktuelle Frage und wartet auf die Antwort des Servers.

    Gewartet wird auf den Netzaufruf, nicht auf eine Aenderung im DOM: so
    steht bei einem Fehlschlag der Statuscode des Servers in der Meldung,
    statt dass nur eine Zusicherung ins Leere laeuft. Der anschliessende
    Abgleich der Frage-ID stellt sicher, dass der Wizard tatsaechlich
    weitergerueckt ist. */
async function antworte(seite: Page, antwort: 'Ja' | 'Nein') {
  const vorher = await seite.getByTestId('frage').getAttribute('data-frage-id');
  const [ruf] = await Promise.all([
    seite.waitForResponse(
      (r) => r.url().includes('/bewertung/wizard') && r.request().method() === 'POST',
    ),
    seite.getByRole('button', { name: antwort, exact: true }).click(),
  ]);
  expect(ruf.ok(), `Wizard-Schritt fehlgeschlagen: ${ruf.status()} ${await ruf.text()}`).toBeTruthy();

  await expect
    .poll(async () => {
      if ((await seite.getByTestId('frage').count()) === 0) return '__ende__';
      return seite.getByTestId('frage').getAttribute('data-frage-id');
    })
    .not.toBe(vorher);
}

test.describe('Phase 2 in der Oberflaeche', () => {
  test('vollstaendiger Durchlauf liefert Tier 3 und das erwartete K-Klassen-Bild', async ({
    page,
    request,
  }) => {
    const id = await prozessAnlegen(request, 'Bewertung vollstaendig');
    await anmelden(page);
    await page.goto(`/de/prozesse/${id}/bewertung`);

    await page.getByRole('button', { name: 'Vollständig' }).click();
    await page.getByRole('button', { name: 'Bewertung durchführen' }).click();

    // Profil KI0-DS3-MB1-IT1-RG2-UR2 aus dem durchgerechneten Beispiel.
    await expect(page.getByText('Schritt 1 von 6 — Künstliche Intelligenz')).toBeVisible();
    await antworte(page, 'Nein'); // 1a: kein KI-Einsatz
    await expect(page.getByText('Schritt 2 von 6 — Datenschutz')).toBeVisible();
    // Der Zwischenstand bleibt bis zum Ende unsichtbar.
    await expect(page.getByTestId('tier')).toHaveCount(0);
    await antworte(page, 'Ja'); // 2a: besondere Kategorien -> DS 3
    await expect(page.getByText('Schritt 3 von 6 — Mitbestimmung')).toBeVisible();
    await antworte(page, 'Nein'); // 3a
    await antworte(page, 'Nein'); // 3b
    await antworte(page, 'Ja'); // 3c -> MB 1
    await expect(page.getByText('Schritt 4 von 6 — IT-Sicherheit')).toBeVisible();
    await antworte(page, 'Nein'); // 4a
    await antworte(page, 'Nein'); // 4b
    await antworte(page, 'Ja'); // 4c -> IT 1
    await expect(page.getByText('Schritt 5 von 6 — Regulatorik')).toBeVisible();
    await antworte(page, 'Nein'); // 5a
    await antworte(page, 'Ja'); // 5b -> RG 2
    await expect(page.getByText('Schritt 6 von 6 — Unternehmerisches Risiko')).toBeVisible();
    await antworte(page, 'Nein'); // 6a
    await antworte(page, 'Ja'); // 6b -> UR 2

    await expect(page.getByTestId('tier')).toHaveText('3');
    await expect(page.getByTestId('profil')).toHaveText('KI0-DS3-MB1-IT1-RG2-UR2');
    // Die Klassen stehen mit Namen da; die Kennung bleibt als Abzeichen davor.
    const klassen = page.getByTestId('k-klassen');
    await expect(klassen.getByRole('listitem')).toHaveCount(8);
    for (const kennung of ['K1', 'K2', 'K3', 'K4', 'K5', 'K7', 'K8', 'K9']) {
      await expect(klassen.getByRole('listitem').filter({ hasText: kennung })).toHaveCount(1);
    }
    await expect(klassen).toContainText('Datenschutz-Folgenabschätzung');
    await expect(page.getByTestId('auflagen')).toContainText('Registrierung im Verzeichnis');

    await page.getByRole('button', { name: 'Bewertung speichern' }).click();
    await expect(page.getByRole('heading', { name: 'Bewertungshistorie' })).toBeVisible();
    await expect(page.getByText('KI0-DS3-MB1-IT1-RG2-UR2')).toBeVisible();
  });

  test('schnelle Variante endet beim ersten Tier-3-Treffer', async ({ page, request }) => {
    const id = await prozessAnlegen(request, 'Bewertung schnell');
    await anmelden(page);
    await page.goto(`/de/prozesse/${id}/bewertung`);

    await page.getByRole('button', { name: 'Schnell' }).click();
    await page.getByRole('button', { name: 'Bewertung durchführen' }).click();
    await antworte(page, 'Nein'); // 1a
    await antworte(page, 'Ja'); // 2a -> DS 3, Schluss

    await expect(page.getByTestId('tier')).toHaveText('3');
    await expect(
      page.getByText('Der schnelle Durchlauf endet vorzeitig und liefert deshalb keine K-Klassen.'),
    ).toBeVisible();
    await expect(page.getByTestId('k-klassen')).toHaveCount(0);
  });

  test('verbotene KI-Praxis speichert keine Bewertung', async ({ page, request }) => {
    const id = await prozessAnlegen(request, 'Bewertung verboten');
    await anmelden(page);
    await page.goto(`/de/prozesse/${id}/bewertung`);

    await page.getByRole('button', { name: 'Schnell' }).click();
    await page.getByRole('button', { name: 'Bewertung durchführen' }).click();
    await antworte(page, 'Ja'); // 1a: KI im Einsatz
    await page.getByRole('button', { name: 'Ja', exact: true }).click(); // 1b: verbotene Praxis

    await expect(page.getByRole('heading', { name: 'Verbotene KI-Praxis' })).toBeVisible();
    await expect(page.getByTestId('tier')).toHaveCount(0);

    await page.getByRole('button', { name: 'Alarm auslösen' }).click();
    await expect(page.getByRole('heading', { name: 'Bewertungshistorie' })).toBeVisible();
    await expect(
      page.getByText('Für diesen Prozess liegt noch keine Bewertung vor.'),
    ).toBeVisible();
  });
});
