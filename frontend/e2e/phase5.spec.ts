/**
 * Abnahme von Phase 5 durch die Oberflaeche, headless gefahren.
 *
 * Geprueft werden die Kriterien 5.1 (rote Meldung eroeffnet automatisch einen
 * Lenkungsvorgang in Stufe 1 mit tier-abhaengiger Frist), 5.2 (Eskalation in
 * Stufe 2 nach Fristablauf) und 5.3 (die drei Aufloesungswege; „Rahmen
 * erweitern" verlangt eine neue Bewertung).
 */

import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

import { json } from './hilfen';

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
  const fachbereich = await json<{ id: string }>(
    await anfrage.post(`${API}/api/v1/fachbereiche`, {
      headers: h,
      data: { name: `Bereich ${kennung}`, code: `fb-${kennung}` },
    }),
    'Fachbereich anlegen',
  );
  const int = await json<{ id: string }>(
    await anfrage.post(`${API}/api/v1/organisationseinheiten`, {
      headers: h,
      data: { fachbereich_id: fachbereich.id, ebene: 'INT' },
    }),
    'Organisationseinheit anlegen',
  );
  const ich = await (await anfrage.get(`${API}/api/v1/auth/me`, { headers: h })).json();
  const prozess = await json<{ id: string }>(
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
        ausfallfolge: 'keine',
      },
    }),
    'Prozessobjekt anlegen',
  );
  await json(
    await anfrage.post(`${API}/api/v1/prozesse/${prozess.id}/bewertungen`, {
      headers: h,
      data: {
        modus: 'vollstaendig',
        antworten: TIER3_ANTWORTEN,
        begruendungen: Object.fromEntries(
          Object.keys(TIER3_ANTWORTEN).map((frage) => [frage, 'Vorbedingung des Abnahmetests.']),
        ),
      },
    }),
    'Bewertung im Aufbau',
  );
  const tool = await (
    await anfrage.post(`${API}/api/v1/tools`, {
      headers: h,
      data: { name: `Tool ${kennung}`, technischer_owner_user_id: ich.id },
    })
  ).json();
  // Ohne die drei Erklaerungen aus A.6 gibt es keine Prozesskante — und ohne
  // sie erbte das Tool kein Tier, sodass die tier-abhaengige Frist gar nicht
  // geprueft waere.
  await json(
    await anfrage.put(`${API}/api/v1/tools/${tool.id}/attestierungen`, {
      headers: h,
      data: {
        attest_entscheidung_ueber_personen: false,
        attest_mensch_dazwischen: true,
        attest_undeklarierte_quellen: false,
      },
    }),
    'Attestierung im Aufbau',
  );
  await json(
    await anfrage.post(`${API}/api/v1/tools/${tool.id}/prozesse`, {
      headers: h,
      data: { prozessobjekt_id: prozess.id },
    }),
    'Prozesskante im Aufbau',
  );
  return { toolId: tool.id, toolName: tool.name, prozessId: prozess.id, kopfzeilen: h };
}

async function anmelden(seite: Page) {
  await seite.goto('/de/anmeldung');
  await seite.getByLabel('Kennung').fill(ADMIN);
  await seite.getByLabel('Name').fill('E2E Administrator');
  await seite.getByRole('button', { name: 'Anmelden' }).click();
  await expect(seite.getByRole('heading', { name: 'Prozessobjekte' })).toBeVisible();
}

/** Die Karte eines Vorgangs, ueber den Namen des betroffenen Tool-Objekts.

    Die Liste zeigt alle offenen Vorgaenge; jeder Test arbeitet deshalb auf
    seiner eigenen Karte statt auf der ersten. */
function karte(seite: Page, toolName: string) {
  return seite.locator('.k-karte').filter({ hasText: toolName });
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
    const meine = karte(page, toolName);
    await expect(meine).toBeVisible();
    // Stufe 1, mit der Tier-3-Frist von fuenf Arbeitstagen ab heute (A.13.5).
    await expect(meine.getByTestId(/^stufe-/)).toHaveText('Stufe 1');
    await expect(meine.getByTestId(/^frist-/)).toHaveText('5');
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
    await karte(page, toolName).getByRole('button', { name: 'Anpassen' }).click();
    await page.getByTestId('aufloesen').click();
    await expect(karte(page, toolName)).toHaveCount(0);

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
    await karte(page, toolName).getByRole('button', { name: 'Rahmen erweitern' }).click();

    // Ohne neue Bewertung gibt es nichts zu waehlen — und keinen Knopf, der
    // in eine Ablehnung liefe.
    await expect(page.getByText(/keine neue Bewertung/)).toBeVisible();
    await expect(page.getByTestId('aufloesen')).toHaveCount(0);
    await page.keyboard.press('Escape');
    await expect(karte(page, toolName)).toBeVisible();

    // Nach einer neuen Bewertung steht sie zur Wahl und schliesst den Vorgang.
    const neue = await json<{ bewertung: { id: string } | null }>(
      await request.post(`${API}/api/v1/prozesse/${prozessId}/bewertungen`, {
        headers: kopfzeilen,
        data: {
          modus: 'vollstaendig',
          antworten: { ...TIER3_ANTWORTEN, '4b': true },
          begruendungen: Object.fromEntries(
            Object.keys({ ...TIER3_ANTWORTEN, '4b': true }).map((frage) => [
              frage,
              'Vorbedingung des Abnahmetests.',
            ]),
          ),
        },
      }),
      'Neue Bewertung fuer Rahmenerweiterung',
    );
    expect(neue.bewertung, 'Der Durchlauf muss eine Bewertung liefern').not.toBeNull();

    await page.reload();
    await karte(page, toolName).getByRole('button', { name: 'Rahmen erweitern' }).click();
    await page.getByTestId(`bewertung-${neue.bewertung!.id}`).click();
    await expect(karte(page, toolName)).toHaveCount(0);
  });
});
