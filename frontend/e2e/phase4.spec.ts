/**
 * Abnahme von Phase 4 durch die Oberflaeche, headless gefahren.
 *
 * Geprueft werden die Kriterien 4.1 (Tier 3 wird ohne vollstaendige
 * Selbstverpflichtung nicht aktiv), 4.2 (Gate 2 ohne Ausloeser wird vom
 * Formular abgelehnt) und 4.3 (nur die Governance-Rolle entscheidet).
 */

import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const API = 'http://127.0.0.1:8100';
const ADMIN = 'e2e-admin';

async function kopf(anfrage: APIRequestContext, subject = ADMIN, name = 'E2E Administrator') {
  const antwort = await anfrage.post(`${API}/api/v1/auth/dev-token`, {
    data: { subject, email: `${subject}@beispiel-ag.de`, name },
  });
  return { Authorization: `Bearer ${(await antwort.json()).access_token}` };
}

/** Legt einen mit Tier 3 bewerteten Prozess an und liefert ID und Name. */
async function tier3Prozess(anfrage: APIRequestContext) {
  const h = await kopf(anfrage);
  const kennung = Math.random().toString(36).slice(2, 8);
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
  const prozess = await (
    await anfrage.post(`${API}/api/v1/prozesse`, {
      headers: h,
      data: {
        name: `Tier-3-Prozess ${kennung}`,
        owner_user_id: ich.id,
        stellvertretung_user_id: ich.id,
        prozessgeber_org_id: int.id,
        supplier: '',
        input_datenobjekt_ids: [],
        process_steps: '',
        output: '',
        customer: 'bereich',
        ausfallfolge: 'keine',
      },
    })
  ).json();
  // Profil DS3 ergibt Tier 3.
  await anfrage.post(`${API}/api/v1/prozesse/${prozess.id}/bewertungen`, {
    headers: h,
    data: {
      modus: 'vollstaendig',
      antworten: {
        '1a': false,
        '2a': true,
        '3a': false,
        '3b': false,
        '3c': false,
        '4a': false,
        '4b': false,
        '4c': false,
        '5a': false,
        '5b': false,
        '5c': false,
        '6a': false,
        '6b': false,
        '6c': false,
      },
    },
  });
  return { id: prozess.id, name: prozess.name };
}

async function anmelden(seite: Page, subject = ADMIN, name = 'E2E Administrator') {
  await seite.goto('/de/anmeldung');
  await seite.getByLabel('Kennung').fill(subject);
  await seite.getByLabel('Name').fill(name);
  await seite.getByRole('button', { name: 'Anmelden' }).click();
  await expect(seite.getByRole('heading', { name: 'Prozessobjekte' })).toBeVisible();
}

test.describe('Phase 4 in der Oberflaeche', () => {
  test('Tier 3 wird erst nach Selbstverpflichtung und Gate 1 aktiv', async ({
    page,
    request,
  }) => {
    const prozess = await tier3Prozess(request);
    await anmelden(page);
    await page.goto(`/de/prozesse/${prozess.id}`);

    await expect(
      page.getByText('Für dieses Objekt liegt noch keine Selbstverpflichtung vor.'),
    ).toBeVisible();

    // Eine unvollstaendige Selbstverpflichtung genuegt nicht.
    await page.getByTestId('sv-oeffnen').click();
    await page.getByRole('checkbox').first().waitFor();
    await page.getByRole('checkbox').first().check();
    await page.getByTestId('sv-abgeben').click();
    await expect(page.getByText('Nicht alle verlangten Aussagen sind bestätigt.')).toBeVisible();

    // Vollstaendig abgeben.
    await page.getByTestId('sv-oeffnen').click();
    await page.getByRole('checkbox').first().waitFor();
    const anzahl = await page.getByRole('checkbox').count();
    for (let i = 0; i < anzahl; i += 1) {
      await page.getByRole('checkbox').nth(i).check();
    }
    await page.getByTestId('sv-abgeben').click();
    await expect(page.getByText('Die Erklärung liegt vor und trägt.')).toBeVisible();

    // Gate 1 einreichen und als Governance freigeben.
    await page.getByLabel('Gate').selectOption('1');
    await page.getByLabel('Begründung').fill('Erstfreigabe');
    await page.getByTestId('gate-einreichen').click();
    await expect(page.getByText('Eingereicht')).toBeVisible();

    await page.getByRole('link', { name: 'Gates', exact: true }).click();
    await page
      .getByLabel(/^Entscheidungskommentar/)
      .first()
      .fill('Geprüft');
    await page.getByRole('button', { name: 'Freigeben' }).first().click();
    await expect(page.getByText('Es ist kein Gate-Vorgang offen.')).toBeVisible();
  });

  test('Gate 2 ohne Ausloeser laesst sich nicht einreichen', async ({ page, request }) => {
    const prozess = await tier3Prozess(request);
    await anmelden(page);
    await page.goto(`/de/prozesse/${prozess.id}`);

    await page.getByLabel('Gate').selectOption('2');
    const ausloeser = page.getByLabel('Auslöser');
    await expect(ausloeser).toBeVisible();
    // Genau fuenf Gruende plus Leerauswahl — kein sechster, freier Grund.
    await expect(ausloeser.getByRole('option')).toHaveCount(6);

    // Ohne Ausloeser ist das Einreichen gesperrt — die Liste in A.11 ist
    // abschliessend, ein Gate 2 ohne Grund gibt es nicht.
    await expect(page.getByTestId('gate-einreichen')).toBeDisabled();
    await expect(page.getByText('Für diesen Prozess gibt es noch keinen Gate-Vorgang.')).toBeVisible();

    await ausloeser.selectOption('reichweitenerweiterung');
    await page.getByTestId('gate-einreichen').click();
    // Der Vorgang steht in der Liste, mit dem Namen des Auslösers.
    await expect(page.locator('.k-zeile[data-testid^="gate-"]')).toContainText(
      'Reichweitenerweiterung',
    );
  });

  test('ohne Governance-Rolle erscheint keine Entscheidung', async ({ page, request }) => {
    const prozess = await tier3Prozess(request);
    const h = await kopf(request);
    await request.post(`${API}/api/v1/prozesse/${prozess.id}/gates`, {
      headers: h,
      data: { gate_typ: '1', begruendung: 'Erstfreigabe' },
    });

    const fremd = `e2e-ohne-rolle-${Math.random().toString(36).slice(2, 8)}`;
    await anmelden(page, fremd, 'Ohne Rolle');
    await page.getByRole('link', { name: 'Gates', exact: true }).click();
    await expect(page.getByText('Es ist kein Gate-Vorgang offen.')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Freigeben' })).toHaveCount(0);
  });
});
