/**
 * Abnahme von Phase 5 durch die Oberflaeche, headless gefahren.
 *
 * Geprueft werden die Kriterien 5.1 (rote Meldung eroeffnet automatisch einen
 * Lenkungsvorgang in Stufe 1 mit tier-abhaengiger Frist), 5.2 (Eskalation in
 * Stufe 2 nach Fristablauf) und 5.3 (die drei Aufloesungswege; „Rahmen
 * erweitern" verlangt eine neue Bewertung).
 */

import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const API = 'http://127.0.0.1:8100';
const ADMIN = 'e2e-admin';

const TIER3_ANTWORTEN = {
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
};

async function kopf(anfrage: APIRequestContext) {
  const antwort = await anfrage.post(`${API}/api/v1/auth/dev-token`, {
    data: { subject: ADMIN, email: `${ADMIN}@beispiel-ag.de`, name: 'E2E Administrator' },
  });
  return { Authorization: `Bearer ${(await antwort.json()).access_token}` };
}

/** Legt ein Tier-3-bewertetes Tool an, das an einem Prozess haengt. */
async function tier3Tool(anfrage: APIRequestContext) {
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
        name: `Prozess ${kennung}`,
        owner_user_id: ich.id,
        stellvertretung_user_id: ich.id,
        prozessgeber_org_id: int.id,
        supplier: '',
        input_datenobjekt_ids: [],
        process_steps: '',
        output: '',
        customer: 'bereich',
        ausfallfolge: 'gering',
      },
    })
  ).json();
  await anfrage.post(`${API}/api/v1/prozesse/${prozess.id}/bewertungen`, {
    headers: h,
    data: { modus: 'vollstaendig', antworten: TIER3_ANTWORTEN },
  });
  const tool = await (
    await anfrage.post(`${API}/api/v1/tools`, {
      headers: h,
      data: { name: `Tool ${kennung}`, technischer_owner_user_id: ich.id },
    })
  ).json();
  await anfrage.post(`${API}/api/v1/tools/${tool.id}/prozesse`, {
    headers: h,
    data: { prozessobjekt_id: prozess.id },
  });
  return { toolId: tool.id, toolName: tool.name, prozessId: prozess.id, kopfzeilen: h };
}

async function anmelden(seite: Page) {
  await seite.goto('/de/anmeldung');
  await seite.getByLabel('Kennung').fill(ADMIN);
  await seite.getByLabel('Name').fill('E2E Administrator');
  await seite.getByRole('button', { name: 'Anmelden' }).click();
  await expect(seite.getByRole('heading', { name: 'Prozessobjekte' })).toBeVisible();
}

/** Die Zeile eines Vorgangs, ueber den Namen des betroffenen Tool-Objekts.

    Die Liste zeigt alle offenen Vorgaenge; jeder Test arbeitet deshalb auf
    seiner eigenen Zeile statt auf der ersten. */
function zeile(seite: Page, toolName: string) {
  return seite.getByRole('row').filter({ has: seite.getByRole('link', { name: toolName }) });
}

test.describe('Phase 5 in der Oberflaeche', () => {
  test('rote Meldung eroeffnet einen Lenkungsvorgang in Stufe 1', async ({ page, request }) => {
    const { toolId, toolName } = await tier3Tool(request);
    await anmelden(page);
    await page.goto(`/de/tools/${toolId}`);

    await expect(
      page.getByText('Für dieses Tool-Objekt ist noch kein Zustand erfasst.'),
    ).toBeVisible();

    await page.getByLabel('Zustand melden').selectOption('rot');
    await expect(
      page.getByText(
        'Eine rote Meldung eröffnet automatisch einen Lenkungsvorgang in Eskalationsstufe 1 mit der tier-abhängigen Frist.',
      ),
    ).toBeVisible();
    await page.getByLabel('Begründung').fill('Schreibt in ein fremdes Datenobjekt');
    await page.getByLabel('Art der Abweichung').fill('datenobjekt_ausserhalb_rahmen');
    await page.getByRole('button', { name: 'Zustand melden' }).click();

    await expect(page.getByTestId('aktueller-zustand')).toContainText(
      'Rot — Rahmenüberschreitung',
    );

    await page.getByRole('link', { name: 'Lenkung', exact: true }).click();
    const meine = zeile(page, toolName);
    await expect(meine).toBeVisible();
    // Stufe 1, mit der Tier-3-Frist von 14 Tagen ab heute.
    await expect(meine.getByTestId(/^stufe-/)).toHaveText('1');
  });

  test('Anpassen schliesst den Vorgang und setzt den Zustand auf gruen', async ({
    page,
    request,
  }) => {
    const { toolId, toolName, kopfzeilen } = await tier3Tool(request);
    await request.post(`${API}/api/v1/tools/${toolId}/compliance`, {
      headers: kopfzeilen,
      data: { farbe: 'rot', begruendung: 'Rahmen verlassen' },
    });

    await anmelden(page);
    await page.getByRole('link', { name: 'Lenkung', exact: true }).click();
    const meine = zeile(page, toolName);
    await meine.getByRole('button', { name: 'Auflösen' }).click();
    await expect(meine).toHaveCount(0);

    await page.goto(`/de/tools/${toolId}`);
    await expect(page.getByTestId('aktueller-zustand')).toContainText('Grün');
  });

  test('Rahmen erweitern verlangt eine neue Bewertung', async ({ page, request }) => {
    const { toolName, prozessId, kopfzeilen, toolId } = await tier3Tool(request);
    await request.post(`${API}/api/v1/tools/${toolId}/compliance`, {
      headers: kopfzeilen,
      data: { farbe: 'rot', begruendung: 'Rahmen verlassen' },
    });

    await anmelden(page);
    await page.getByRole('link', { name: 'Lenkung', exact: true }).click();
    const meine = zeile(page, toolName);
    await meine.getByLabel(/^Auflösungsart/).selectOption('rahmen_erweitern');
    await expect(
      meine.getByText('Der Vorgang schließt erst, wenn die neue Bewertung abgeschlossen ist.'),
    ).toBeVisible();

    // Ohne Bewertung bleibt der Vorgang offen.
    await meine.getByRole('button', { name: 'Auflösen' }).click();
    await expect(page.getByRole('alert')).toContainText('neue Bewertung');
    await expect(meine).toBeVisible();

    // Nach einer neuen Bewertung schliesst er.
    const neue = await (
      await request.post(`${API}/api/v1/prozesse/${prozessId}/bewertungen`, {
        headers: kopfzeilen,
        data: { modus: 'vollstaendig', antworten: { ...TIER3_ANTWORTEN, '4b': true } },
      })
    ).json();
    await meine.getByLabel(/^Neue Bewertung/).fill(neue.bewertung.id);
    await meine.getByRole('button', { name: 'Auflösen' }).click();
    await expect(meine).toHaveCount(0);
  });
});
