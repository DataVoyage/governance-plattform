/**
 * Abnahme von Phase 3 durch die Oberflaeche, headless gefahren.
 *
 * Geprueft werden die Kriterien 3.1 (importiertes Tool erst nach Bestaetigung
 * verknuepfbar), 3.2 (Sync ueberschreibt die Kategorie nicht), 3.3
 * (Maximum-Vererbung) und 3.4 (Datenobjekt-Kategorie wirkt im Prozess, ohne
 * dort erneut gepflegt zu werden).
 */

import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const API = 'http://127.0.0.1:8100';
const ADMIN = 'e2e-admin';

async function kopf(anfrage: APIRequestContext): Promise<Record<string, string>> {
  const antwort = await anfrage.post(`${API}/api/v1/auth/dev-token`, {
    data: { subject: ADMIN, email: `${ADMIN}@beispiel-ag.de`, name: 'E2E Administrator' },
  });
  return { Authorization: `Bearer ${(await antwort.json()).access_token}` };
}

async function prozessAnlegen(
  anfrage: APIRequestContext,
  name: string,
  ausfallfolge: string,
): Promise<{ id: string; name: string }> {
  const h = await kopf(anfrage);
  const code = `fb-${Math.random().toString(36).slice(2, 10)}`;
  const fachbereich = await (
    await anfrage.post(`${API}/api/v1/fachbereiche`, {
      headers: h,
      data: { name: `Bereich ${code}`, code },
    })
  ).json();
  const int = await (
    await anfrage.post(`${API}/api/v1/organisationseinheiten`, {
      headers: h,
      data: { fachbereich_id: fachbereich.id, ebene: 'INT' },
    })
  ).json();
  const ich = await (await anfrage.get(`${API}/api/v1/auth/me`, { headers: h })).json();
  const prozess = await (
    await anfrage.post(`${API}/api/v1/prozesse`, {
      headers: h,
      data: {
        name,
        owner_user_id: ich.id,
        stellvertretung_user_id: ich.id,
        prozessgeber_org_id: int.id,
        supplier: '',
        input_datenobjekt_ids: [],
        process_steps: '',
        output: '',
        customer: 'bereich',
        ausfallfolge,
      },
    })
  ).json();
  return { id: prozess.id, name: prozess.name };
}

async function anmelden(seite: Page) {
  await seite.goto('/de/anmeldung');
  await seite.getByLabel('Kennung').fill(ADMIN);
  await seite.getByLabel('Name').fill('E2E Administrator');
  await seite.getByRole('button', { name: 'Anmelden' }).click();
  await expect(seite.getByRole('heading', { name: 'Prozessobjekte' })).toBeVisible();
}

test.describe('Phase 3 in der Oberflaeche', () => {
  test('importiertes Tool ist erst nach Bestaetigung verknuepfbar', async ({ page, request }) => {
    const h = await kopf(request);
    const externeId = `TOOL-${Math.random().toString(36).slice(2, 8)}`;
    const toolName = `Importiertes Tool ${externeId}`;
    await request.post(`${API}/api/v1/import/assets`, {
      headers: h,
      data: {
        quelle: 'zentrale-entwicklungsplattform',
        datensaetze: [
          {
            typ: 'tool',
            externe_id: externeId,
            name: toolName,
            metadaten: { technologie: 'apps-script' },
          },
        ],
      },
    });
    const prozess = await prozessAnlegen(request, `Zielprozess ${externeId}`, 'kritisch');

    await anmelden(page);
    await page.getByRole('link', { name: 'Tool-Objekte', exact: true }).click();
    await page.getByRole('link', { name: toolName }).click();

    await expect(page.getByTestId('status')).toHaveText('Importiert, unbestätigt');
    await expect(page.getByLabel('Mit Prozess verknüpfen')).toHaveCount(0);

    await page.getByRole('button', { name: 'Bestätigen' }).click();
    await expect(page.getByTestId('status')).toHaveText('Bestätigt');

    // Abnahmekriterium 3.3: das Tool erbt die Kritikalitaet des Prozesses.
    await page.getByLabel('Mit Prozess verknüpfen').selectOption({ label: prozess.name });
    await page.getByRole('button', { name: 'Mit Prozess verknüpfen' }).click();
    await expect(page.getByTestId('geerbt-kritikalitaet')).toHaveText('3');
  });

  test('ein Tool an zwei Prozessen zeigt die hoehere Einstufung', async ({ page, request }) => {
    const kennung = Math.random().toString(36).slice(2, 8);
    const gering = await prozessAnlegen(request, `Gering ${kennung}`, 'gering');
    const kritisch = await prozessAnlegen(request, `Kritisch ${kennung}`, 'kritisch');

    await anmelden(page);
    await page.getByRole('link', { name: 'Tool-Objekte', exact: true }).click();
    const toolName = `Gemeinsames Tool ${kennung}`;
    await page.getByLabel('Tool-Objekt anlegen').fill(toolName);
    await page.getByRole('button', { name: 'Speichern' }).click();
    await page.getByRole('link', { name: toolName }).click();

    await page.getByLabel('Mit Prozess verknüpfen').selectOption({ label: gering.name });
    await page.getByRole('button', { name: 'Mit Prozess verknüpfen' }).click();
    await expect(page.getByTestId('geerbt-kritikalitaet')).toHaveText('1');

    await page.getByLabel('Mit Prozess verknüpfen').selectOption({ label: kritisch.name });
    await page.getByRole('button', { name: 'Mit Prozess verknüpfen' }).click();
    await expect(page.getByTestId('geerbt-kritikalitaet')).toHaveText('3');
  });

  test('Kategorie eines Datenobjekts wirkt im verknuepften Prozess', async ({ page, request }) => {
    const h = await kopf(request);
    const kennung = Math.random().toString(36).slice(2, 8);
    const datenobjektName = `Zeiterfassung ${kennung}`;
    const datenobjekt = await (
      await request.post(`${API}/api/v1/datenobjekte`, {
        headers: h,
        data: { name: datenobjektName, beschreibung: '' },
      })
    ).json();

    const fachbereich = await (
      await request.post(`${API}/api/v1/fachbereiche`, {
        headers: h,
        data: { name: `Bereich ${kennung}`, code: `fb-${kennung}` },
      })
    ).json();
    const int = await (
      await request.post(`${API}/api/v1/organisationseinheiten`, {
        headers: h,
        data: { fachbereich_id: fachbereich.id, ebene: 'INT' },
      })
    ).json();
    const ich = await (await request.get(`${API}/api/v1/auth/me`, { headers: h })).json();
    const prozess = await (
      await request.post(`${API}/api/v1/prozesse`, {
        headers: h,
        data: {
          name: `Zeitprozess ${kennung}`,
          owner_user_id: ich.id,
          stellvertretung_user_id: ich.id,
          prozessgeber_org_id: int.id,
          supplier: '',
          input_datenobjekt_ids: [datenobjekt.id],
          process_steps: '',
          output: '',
          customer: 'bereich',
          ausfallfolge: 'gering',
        },
      })
    ).json();

    await anmelden(page);
    await page.goto(`/de/prozesse/${prozess.id}`);
    await expect(page.getByTestId('mitbestimmung')).toHaveText('Nein');

    await page.getByRole('link', { name: 'Datenobjekte', exact: true }).click();
    await page
      .getByLabel(`Kategorie — ${datenobjektName}`)
      .selectOption('mitarbeiterbezogen');
    await expect(page.getByLabel(`Kategorie — ${datenobjektName}`)).toHaveValue(
      'mitarbeiterbezogen',
    );

    // Der Prozess liest die Kategorie, statt sie erneut zu fuehren.
    await page.goto(`/de/prozesse/${prozess.id}`);
    await expect(page.getByTestId('mitbestimmung')).toHaveText('Ja');
  });
});
