/**
 * Abnahme von Phase 3 durch die Oberflaeche, headless gefahren.
 *
 * Geprueft werden die Kriterien 3.1 (importiertes Tool erst nach Bestaetigung
 * verknuepfbar), 3.3 (Maximum-Vererbung) und 3.4 (Datenobjekt-Kategorie wirkt
 * im Prozess, ohne dort erneut gepflegt zu werden) — dazu die Abnahme aus
 * Umsetzungsplan AP-3: Tool anlegen, attestieren, mit Prozessen und
 * Datenobjekten verknuepfen, geerbtes Maximum und Rahmenwarnung sehen.
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

async function organisation(anfrage: APIRequestContext, kennung: string) {
  const h = await kopf(anfrage);
  const fachbereich = await (
    await anfrage.post(`${API}/api/v1/fachbereiche`, {
      headers: h,
      data: { name: `Bereich ${kennung}`, code: `fb-${kennung}` },
    })
  ).json();
  const int = await (
    await anfrage.post(`${API}/api/v1/organisationseinheiten`, {
      headers: h,
      data: { fachbereich_id: fachbereich.id, ebene: 'INT' },
    })
  ).json();
  const ich = await (await anfrage.get(`${API}/api/v1/auth/me`, { headers: h })).json();
  return { h, int, ich, fachbereich };
}

async function prozessAnlegen(
  anfrage: APIRequestContext,
  name: string,
  ausfallfolge: string,
  zusatz: Record<string, unknown> = {},
): Promise<{ id: string; name: string }> {
  const { h, int, ich } = await organisation(anfrage, Math.random().toString(36).slice(2, 10));
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
        ...zusatz,
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

/** Die drei Erklaerungen aus A.6 abgeben — Vorbedingung jeder Prozesskante. */
async function attestieren(seite: Page, kein_mensch = false) {
  await seite
    .getByTestId('attest_entscheidung_ueber_personen')
    .getByRole('button', { name: 'Nein' })
    .click();
  await seite
    .getByTestId('attest_mensch_dazwischen')
    .getByRole('button', { name: kein_mensch ? 'Nein' : 'Ja' })
    .click();
  await seite
    .getByTestId('attest_undeklarierte_quellen')
    .getByRole('button', { name: 'Nein' })
    .click();
  await seite.getByRole('button', { name: /Erklärung (abgeben|erneuern)/ }).click();
  await expect(seite.getByText('Vollständig abgegeben')).toBeVisible();
}

/** Eine Referenz ueber den Waehler auswaehlen. */
async function waehle(seite: Page, waehler: string, name: string) {
  const feld = seite.getByTestId(waehler);
  await feld.getByRole('combobox').click();
  await feld.getByRole('button', { name: new RegExp(name) }).click();
}

async function toolAnlegen(seite: Page, name: string, technologie = 'Apps Script') {
  await seite.getByRole('link', { name: 'Tool-Objekte', exact: true }).click();
  await seite.getByRole('button', { name: 'Tool-Objekt anlegen' }).first().click();
  const blatt = seite.getByRole('dialog');
  await blatt.getByLabel('Name').fill(name);
  await blatt.getByLabel('Technologie').selectOption({ label: technologie });
  await blatt.getByLabel('Lauftyp').selectOption('geplant');
  await blatt.getByRole('button', { name: 'Speichern' }).click();
  await seite.getByRole('link', { name: new RegExp(name) }).click();
  await expect(seite.getByRole('heading', { name })).toBeVisible();
}

test.describe('Phase 3 in der Oberflaeche', () => {
  test('importiertes Tool ist erst nach Bestaetigung und Attestierung verknuepfbar', async ({
    page,
    request,
  }) => {
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
    await page.getByRole('link', { name: new RegExp(toolName) }).click();

    await expect(page.getByTestId('status')).toHaveText('Importiert, unbestätigt');
    await expect(page.getByTestId('waehler-prozesse')).toHaveCount(0);

    await page.getByRole('button', { name: 'Bestätigen' }).click();
    await expect(page.getByTestId('status')).toHaveText('Bestätigt');

    // Bestaetigt, aber noch nicht attestiert: die Kante bleibt gesperrt (A.6).
    await expect(page.getByTestId('waehler-prozesse')).toHaveCount(0);
    await expect(page.getByTestId('wirkungsart')).toContainText('Noch offen');

    await attestieren(page);

    // Abnahmekriterium 3.3: das Tool erbt die Kritikalitaet des Prozesses.
    await waehle(page, 'waehler-prozesse', prozess.name);
    await expect(page.getByTestId('geerbt-kritikalitaet')).toContainText('3');
  });

  test('ein Tool an zwei Prozessen zeigt die hoehere Einstufung mit ihrer Quelle', async ({
    page,
    request,
  }) => {
    const kennung = Math.random().toString(36).slice(2, 8);
    const gering = await prozessAnlegen(request, `Gering ${kennung}`, 'gering');
    const kritisch = await prozessAnlegen(request, `Kritisch ${kennung}`, 'kritisch');

    await anmelden(page);
    await toolAnlegen(page, `Gemeinsames Tool ${kennung}`);
    await attestieren(page);

    await waehle(page, 'waehler-prozesse', gering.name);
    await expect(page.getByTestId('geerbt-kritikalitaet')).toContainText('1');

    await waehle(page, 'waehler-prozesse', kritisch.name);
    await expect(page.getByTestId('geerbt-kritikalitaet')).toContainText('3');

    // Das Maximum bleibt adressierbar: die massgebliche Kante ist benannt.
    await expect(page.getByRole('link', { name: new RegExp(kritisch.name) })).toContainText(
      'Bestimmt das Maximum',
    );
  });

  test('genutzte Datenobjekte werden gegen den Prozessrahmen geprueft', async ({
    page,
    request,
  }) => {
    const kennung = Math.random().toString(36).slice(2, 8);
    const { h, fachbereich } = await organisation(request, `rahmen-${kennung}`);
    const imRahmen = await (
      await request.post(`${API}/api/v1/datenobjekte`, {
        headers: h,
        data: {
          name: `Kreditorenstamm ${kennung}`,
          kategorie: 'intern',
          fachbereich_id: fachbereich.id,
        },
      })
    ).json();
    const daneben = await (
      await request.post(`${API}/api/v1/datenobjekte`, {
        headers: h,
        data: {
          name: `Gesundheitsakte ${kennung}`,
          kategorie: 'besondere_kategorie',
          fachbereich_id: fachbereich.id,
        },
      })
    ).json();
    const prozess = await prozessAnlegen(request, `Rahmenprozess ${kennung}`, 'gering', {
      input_datenobjekt_ids: [imRahmen.id],
    });

    await anmelden(page);
    await toolAnlegen(page, `Zweckbindung ${kennung}`, 'Python / Kubernetes');
    await attestieren(page);
    await waehle(page, 'waehler-prozesse', prozess.name);

    // Innerhalb des Rahmens: keine Warnung.
    await waehle(page, 'waehler-datenobjekte', imRahmen.name);
    await expect(page.getByTestId(`nutzung-${imRahmen.id}`)).toBeVisible();
    await expect(page.getByTestId(`nutzung-${imRahmen.id}`)).not.toContainText(
      'Außerhalb des Prozessrahmens',
    );

    // Ausserhalb: die Abweichung wird sichtbar, statt entdeckt werden zu muessen.
    await page.getByRole('button', { name: 'Schreibt', exact: true }).click();
    await waehle(page, 'waehler-datenobjekte', daneben.name);
    await expect(page.getByTestId(`nutzung-${daneben.id}`)).toContainText(
      'Außerhalb des Prozessrahmens',
    );
    await expect(page.getByText(/Zweckbindung nicht belegt: 1 /)).toBeVisible();

    // Schreibzugriff macht das Tool veraendernd (A.6).
    await expect(page.getByTestId('wirkungsart')).toContainText('Verändernd');
  });

  test('Kategorie eines Datenobjekts wirkt im verknuepften Prozess', async ({ page, request }) => {
    const kennung = Math.random().toString(36).slice(2, 8);
    const { h, fachbereich } = await organisation(request, `kat-${kennung}`);
    const datenobjektName = `Zeiterfassung ${kennung}`;
    const datenobjekt = await (
      await request.post(`${API}/api/v1/datenobjekte`, {
        headers: h,
        data: { name: datenobjektName, beschreibung: '', fachbereich_id: fachbereich.id },
      })
    ).json();
    const prozess = await prozessAnlegen(request, `Zeitprozess ${kennung}`, 'gering', {
      input_datenobjekt_ids: [datenobjekt.id],
    });

    await anmelden(page);
    await page.goto(`/de/prozesse/${prozess.id}`);
    await expect(page.getByTestId('mitbestimmung')).toContainText('Nein');

    await page.goto(`/de/datenobjekte/${datenobjekt.id}`);
    await page.getByLabel('Kategorie').selectOption('besondere_kategorie');
    await expect(page.getByRole('dialog')).toBeVisible();
    await page.getByRole('button', { name: 'Kategorie übernehmen' }).click();

    // Der Prozess liest die Kategorie, statt sie erneut zu fuehren.
    await page.goto(`/de/prozesse/${prozess.id}`);
    await expect(page.getByTestId('mitbestimmung')).toContainText('Ja');
  });
});
