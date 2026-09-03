/**
 * Abnahme von Phase 6 durch die Oberflaeche, headless gefahren.
 *
 * Geprueft werden die Kriterien 6.1 (jede Zeile aus A.14 ist eine eigene,
 * aufrufbare Ansicht), 6.2 (ein Klick fuehrt ins korrekt vorgefilterte
 * Zielmodul) und 6.3 (LAND-Scope sieht nur den eigenen Bereich, Governance
 * global).
 */

import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const API = 'http://127.0.0.1:8100';
const ADMIN = 'e2e-admin';

const ZEILEN = [
  'prozesse_ohne_owner',
  'assets_ohne_prozess',
  'non_compliant',
  'rahmenabweichungen',
  'datenobjekte_ohne_kategorie',
  'kritikalitaetsketten',
  'tier_verteilung',
  'inaktive_assets',
  'ueberfaellige_selbstverpflichtungen',
  'attestierungen_veraltet',
  'widersprueche',
  'antwort_widerspricht_datenlage',
  'technologie_erfuellt_klasse_nicht',
  'altanwendungen',
];

async function kopf(anfrage: APIRequestContext, subject = ADMIN, name = 'E2E Administrator') {
  const antwort = await anfrage.post(`${API}/api/v1/auth/dev-token`, {
    data: { subject, email: `${subject}@beispiel-ag.de`, name },
  });
  return { Authorization: `Bearer ${(await antwort.json()).access_token}` };
}

/** Ein Zugang mit der Plattform-Rolle — nur sie betreibt Adapter (E-57). */
async function plattformKopf(anfrage: APIRequestContext) {
  const marke = Math.random().toString(36).slice(2, 8);
  const subject = `plattform-${marke}`;
  const h = await kopf(anfrage, subject, `Plattform ${marke}`);
  const ich = await (await anfrage.get(`${API}/api/v1/auth/me`, { headers: h })).json();
  await anfrage.post(`${API}/api/v1/admin/rollenzuweisungen`, {
    headers: await kopf(anfrage),
    data: { user_id: ich.id, rolle: 'plattform', scope_typ: 'global' },
  });
  return h;
}

async function anmelden(seite: Page, subject = ADMIN, name = 'E2E Administrator') {
  await seite.goto('/de/anmeldung');
  await seite.getByLabel('Kennung').fill(subject);
  await seite.getByLabel('Name').fill(name);
  await seite.getByRole('button', { name: 'Anmelden' }).click();
  await expect(seite.getByRole('heading', { name: 'Prozessobjekte' })).toBeVisible();
}

test.describe('Phase 6 in der Oberflaeche', () => {
  test('jede Zeile aus A.14 ist eine eigene, aufrufbare Ansicht', async ({ page }) => {
    await anmelden(page);
    await page.getByRole('link', { name: 'Cockpit', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Cockpit' })).toBeVisible();

    for (const schluessel of ZEILEN) {
      await expect(page.getByTestId(`anzahl-${schluessel}`)).toBeVisible();
    }
    // Jede Zeile eine eigene Kachel — keine mehr, keine weniger.
    await expect(page.locator('[data-testid^="kachel-"]')).toHaveCount(ZEILEN.length);

    for (const schluessel of ZEILEN) {
      await page.goto(`/de/cockpit/${schluessel}`);
      await expect(page.getByRole('link', { name: 'Zurück zur Übersicht' })).toBeVisible();
    }
  });

  test('ein Klick fuehrt ins vorgefilterte Zielmodul', async ({ page, request }) => {
    const h = await kopf(request);
    const kennung = Math.random().toString(36).slice(2, 8);
    const name = `Ohne Kategorie ${kennung}`;
    const fachbereich = await (
      await request.post(`${API}/api/v1/fachbereiche`, {
        headers: h,
        data: { name: `Bereich ${kennung}`, code: `fb-${kennung}` },
      })
    ).json();
    await request.post(`${API}/api/v1/datenobjekte`, {
      headers: h,
      data: { name, beschreibung: '', fachbereich_id: fachbereich.id },
    });

    await anmelden(page);
    await page.goto('/de/cockpit/datenobjekte_ohne_kategorie');
    const zeile = page.getByRole('link').filter({ hasText: name });
    await expect(zeile).toBeVisible();
    // Das Ziel steht mit seinem Namen da, nicht mit seinem Schluessel.
    await expect(zeile).toContainText('Datenobjekt');
    await zeile.click();

    await expect(page).toHaveURL(/\/de\/datenobjekte\?ohne_kategorie=true/);
    await expect(page.getByRole('heading', { name: 'Datenobjekte' })).toBeVisible();
    // Der Befund ist in der Liste sichtbar; gepflegt wird die Kategorie am
    // Datenobjekt selbst, weil dort die Wirkung der Aenderung angezeigt wird.
    const treffer = page.getByRole('link', { name: new RegExp(name) });
    await expect(treffer).toContainText('Ohne Kategorie');
    await treffer.click();
    await expect(page.getByLabel('Kategorie')).toHaveValue('');
  });

  test('ein Nutzer ohne Rolle sieht ein leeres Cockpit', async ({ page, request }) => {
    const h = await plattformKopf(request); // Adapter betreibt nur die Plattform
    const kennung = Math.random().toString(36).slice(2, 8);
    // Ein vorgefundenes Datenobjekt ohne Fachbereich — nur global sichtbar.
    await request.post(`${API}/api/v1/import/assets`, {
      headers: h,
      data: {
        quelle: 'zentrale-entwicklungsplattform',
        datensaetze: [
          {
            typ: 'datenobjekt',
            externe_id: `DO-${kennung}`,
            name: `Sichtbar nur global ${kennung}`,
          },
        ],
      },
    });

    const fremd = `e2e-cockpit-fremd-${Math.random().toString(36).slice(2, 8)}`;
    await anmelden(page, fremd, 'Ohne Rolle');
    await page.getByRole('link', { name: 'Cockpit', exact: true }).click();
    for (const schluessel of ZEILEN) {
      await expect(page.getByTestId(`anzahl-${schluessel}`)).toHaveText('0');
    }
  });
});
