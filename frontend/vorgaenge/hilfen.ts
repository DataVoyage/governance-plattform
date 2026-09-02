/**
 * Werkzeug für den Vorgangsdurchlauf.
 *
 * Grundsatz: Der Vorgang selbst läuft **über die Oberfläche**. Die API dient
 * ausschließlich dazu, Vorbedingungen herzustellen, die der geprüfte Anwender
 * selbst nicht herstellen darf — etwa eine Rolle, die ihm erst der
 * App-Administrator gibt. Jede solche Abkürzung steht als Kommentar am Ort.
 */

import { execFileSync } from 'node:child_process';

import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

import { hole } from './katalog';

export const API = 'http://127.0.0.1:8101';
export const ADMIN = 'vorgang-admin';
export const SERVICE_TOKEN = 'vorgang-service-token';

/** Eindeutiger Namensteil, damit Vorgänge einander nicht in die Quere kommen. */
export function kennzeichen(): string {
  return Math.random().toString(36).slice(2, 8);
}

/**
 * Registriert einen Vorgang aus dem Katalog als Testlauf.
 *
 * Der Titel kommt aus `docs/vorgaenge.md`, damit der Bericht dieselbe Sprache
 * spricht wie die Spezifikation. Offene Vorgänge bleiben in der Liste und
 * erscheinen als übersprungen mit ihrem Arbeitspaket als Grund — sie sollen
 * sichtbar bleiben, nicht verschwinden.
 */
export function vorgang(
  kennung: string,
  lauf?: (args: { page: Page; request: APIRequestContext }) => Promise<void>,
): void {
  const eintrag = hole(kennung);
  if (eintrag.stand === 'erfüllt' && lauf === undefined) {
    throw new Error(
      `${kennung} steht im Katalog als „erfüllt", hat aber keinen Durchlauf. ` +
        'Entweder den Durchlauf hinterlegen oder den Stand auf „offen" setzen.',
    );
  }
  test(`${kennung} — ${eintrag.titel}`, async ({ page, request }) => {
    test.skip(
      eintrag.stand === 'offen',
      `Noch offen, vorgesehen in ${eintrag.ap}. Erwartet: ${eintrag.erwartet}`,
    );
    test.info().annotations.push(
      { type: 'Rolle', description: eintrag.rolle },
      { type: 'Arbeitspaket', description: eintrag.ap },
      { type: 'Erwartetes Ergebnis', description: eintrag.erwartet },
    );
    await lauf!({ page, request });
  });
}

// --- Vorbedingungen über die API ----------------------------------------

export async function kopf(
  anfrage: APIRequestContext,
  subject = ADMIN,
  name = 'Vorgangs-Administrator',
): Promise<Record<string, string>> {
  const antwort = await anfrage.post(`${API}/api/v1/auth/dev-token`, {
    data: { subject, email: `${subject}@beispiel-ag.de`, name },
  });
  return { Authorization: `Bearer ${(await antwort.json()).access_token}` };
}

async function json<T = Record<string, string>>(antwort: {
  status: () => number;
  text: () => Promise<string>;
  json: () => Promise<unknown>;
}): Promise<T> {
  if (antwort.status() >= 400) throw new Error(`API ${antwort.status()}: ${await antwort.text()}`);
  return (await antwort.json()) as T;
}

export interface Organisation {
  fachbereichId: string;
  fachbereichName: string;
  intId: string;
  deId: string;
  frId: string;
  ichId: string;
  kopfzeilen: Record<string, string>;
}

/** Ein frischer Fachbereich mit INT- und zwei LAND-Einheiten. */
export async function organisation(
  anfrage: APIRequestContext,
  marke = kennzeichen(),
): Promise<Organisation> {
  const h = await kopf(anfrage);
  const fachbereich = await json(
    await anfrage.post(`${API}/api/v1/fachbereiche`, {
      headers: h,
      data: { name: `Finance ${marke}`, code: `fb-${marke}` },
    }),
  );
  const einheit = async (ebene: 'INT' | 'LAND', land?: string) =>
    json(
      await anfrage.post(`${API}/api/v1/organisationseinheiten`, {
        headers: h,
        data: { fachbereich_id: fachbereich.id, ebene, land_code: land ?? null },
      }),
    );
  const [int, de, fr] = [await einheit('INT'), await einheit('LAND', 'DE'), await einheit('LAND', 'FR')];
  const ich = await json(await anfrage.get(`${API}/api/v1/auth/me`, { headers: h }));
  return {
    fachbereichId: fachbereich.id,
    fachbereichName: fachbereich.name,
    intId: int.id,
    deId: de.id,
    frId: fr.id,
    ichId: ich.id,
    kopfzeilen: h,
  };
}

export async function datenobjektAnlegen(
  anfrage: APIRequestContext,
  daten: Record<string, unknown>,
): Promise<{ id: string; name: string }> {
  const h = await kopf(anfrage);
  return json(await anfrage.post(`${API}/api/v1/datenobjekte`, { headers: h, data: daten }));
}

export async function prozessAnlegen(
  anfrage: APIRequestContext,
  org: Organisation,
  daten: Record<string, unknown>,
): Promise<{ id: string; name: string }> {
  const h = await kopf(anfrage);
  return json(
    await anfrage.post(`${API}/api/v1/prozesse`, {
      headers: h,
      data: {
        owner_user_id: org.ichId,
        stellvertretung_user_id: org.ichId,
        prozessgeber_org_id: org.intId,
        supplier: '',
        input_datenobjekt_ids: [],
        process_steps: 'Pruefen, freigeben, buchen',
        output: 'Freigegebene Rechnung',
        customer: 'bereich',
        ausfallfolge: 'gering',
        ...daten,
      },
    }),
  );
}

export async function toolAnlegen(
  anfrage: APIRequestContext,
  daten: Record<string, unknown>,
  attestieren = true,
): Promise<{ id: string; name: string }> {
  const h = await kopf(anfrage);
  const tool = await json<{ id: string; name: string }>(
    await anfrage.post(`${API}/api/v1/tools`, { headers: h, data: daten }),
  );
  if (attestieren) {
    // Vorbedingung nach A.6 — ohne Erklärung gibt es keine Prozesskante.
    await anfrage.put(`${API}/api/v1/tools/${tool.id}/attestierungen`, {
      headers: h,
      data: {
        attest_entscheidung_ueber_personen: false,
        attest_mensch_dazwischen: true,
        attest_undeklarierte_quellen: false,
      },
    });
  }
  return tool;
}

/**
 * Eine Bewertung als Vorbedingung setzen.
 *
 * Das Antwortmuster ist das aus den Abnahmetests: alles verneint ergibt Tier 1,
 * `2a` bejaht ergibt DS 3 und damit Tier 3. Der Vorgang, der die Bewertung
 * selbst prüft, steht in V-BEW und geht über die Oberfläche.
 */
export async function bewerten(
  anfrage: APIRequestContext,
  prozessId: string,
  hoch = false,
): Promise<void> {
  const h = await kopf(anfrage);
  // Jede Frage jedes Blocks wird beantwortet; nur so gilt der Durchlauf als
  // abgeschlossen. `2a` bejaht kürzt den DS-Block ab und ergibt Tier 3.
  const antworten: Record<string, boolean> = Object.fromEntries(
    ['1a', '1b', '1c', '2a', '2b', '2c', '3a', '3b', '3c', '4a', '4b', '4c', '5a', '5b', '5c', '6a', '6b', '6c'].map(
      (frage) => [frage, frage === '2a' ? hoch : false],
    ),
  );
  const antwort = await anfrage.post(`${API}/api/v1/prozesse/${prozessId}/bewertungen`, {
    headers: h,
    data: {
      modus: 'vollstaendig',
      antworten,
      // Ein gesetztes Zielprofil widerspricht der Datenlage fast immer — die
      // Ausfallfolge ist ein Pflichtfeld, und A.8.4 leitet UR vollständig
      // daraus ab. Der Server behält nur die Begründungen, zu denen es
      // wirklich eine Abweichung gibt. Der Vorgang, der die Begründungspflicht
      // selbst prüft, ist V-BEW-04 und geht über die Oberfläche.
      begruendungen: Object.fromEntries(
        Object.keys(antworten).map((frage) => [frage, 'Vorbedingung des Vorgangs.']),
      ),
    },
  });
  if (antwort.status() >= 400) throw new Error(`Bewertung: ${await antwort.text()}`);
}

export async function toolMitProzess(
  anfrage: APIRequestContext,
  toolId: string,
  prozessId: string,
): Promise<void> {
  const h = await kopf(anfrage);
  const antwort = await anfrage.post(`${API}/api/v1/tools/${toolId}/prozesse`, {
    headers: h,
    data: { prozessobjekt_id: prozessId },
  });
  if (antwort.status() !== 201) throw new Error(`Kante: ${await antwort.text()}`);
}

/** Vorbedingung, die nur der App-Administrator herstellen darf (A.15). */
export async function rolleGeben(
  anfrage: APIRequestContext,
  userId: string,
  rolle: string,
  scopeTyp: 'global' | 'fachbereich' | 'organisationseinheit',
  scopeId: string | null = null,
): Promise<void> {
  const h = await kopf(anfrage);
  const antwort = await anfrage.post(`${API}/api/v1/admin/rollenzuweisungen`, {
    headers: h,
    data: { user_id: userId, rolle, scope_typ: scopeTyp, scope_id: scopeId },
  });
  if (antwort.status() >= 400) throw new Error(`Rolle: ${await antwort.text()}`);
}

/** Legt einen Anwender an und gibt ihm eine Rolle; liefert seine Kennung. */
export async function anwenderMitRolle(
  anfrage: APIRequestContext,
  subject: string,
  name: string,
  rolle: string,
  scopeTyp: 'global' | 'fachbereich' | 'organisationseinheit',
  scopeId: string | null = null,
): Promise<string> {
  const h = await kopf(anfrage, subject, name);
  const ich = await json(await anfrage.get(`${API}/api/v1/auth/me`, { headers: h }));
  await rolleGeben(anfrage, ich.id, rolle, scopeTyp, scopeId);
  return ich.id;
}

/**
 * Einen der geplanten Läufe anstoßen — denselben Befehl, den im Betrieb der
 * Zeitplan ausführt (`app.jobs`).
 *
 * Bewusst kein eigener Endpunkt: eine Route, die es nur für den Vorgang gibt,
 * stünde als Produktionscode in der API und hübe genau die Aussage auf, für
 * die es den Katalog gibt. Die Eskalation läuft nicht in einer Anfrage,
 * sondern in einem Lauf — und genau der wird hier gestartet.
 */
export function geplanterLauf(name: 'erinnerungen' | 'eskalationen' | 'ableitungen'): void {
  execFileSync('uv', ['run', '--directory', '../backend', 'python', '-m', 'app.jobs', name], {
    env: {
      ...process.env,
      GP_DATABASE_URL:
        process.env.GP_VORGAENGE_DATABASE_URL ??
        'postgresql+psycopg://governance:governance@localhost:5432/governance_vorgaenge',
    },
    stdio: 'pipe',
  });
}

// --- Bedienung der Oberfläche -------------------------------------------

export async function anmelden(
  seite: Page,
  subject = ADMIN,
  name = 'Vorgangs-Administrator',
): Promise<void> {
  await seite.goto('/de/anmeldung');
  await seite.getByLabel('Kennung').fill(subject);
  await seite.getByLabel('Name').fill(name);
  await seite.getByRole('button', { name: 'Anmelden' }).click();
  await expect(seite.getByRole('heading', { name: 'Prozessobjekte' })).toBeVisible();
}

/**
 * Eine Referenz über den Wähler auswählen — der Weg, den auch ein Mensch geht:
 * tippen, bis der Treffer oben steht, dann übernehmen.
 *
 * Die Trefferliste zeigt bewusst nur die ersten acht Einträge. Ohne Suchbegriff
 * findet man in einem gewachsenen Bestand nichts — und genau deshalb tippt der
 * Durchlauf, statt blind in eine ungefilterte Liste zu greifen.
 */
export async function waehle(seite: Page, waehler: string, name: string): Promise<void> {
  const feld = seite.getByTestId(waehler);
  await feld.getByRole('combobox').fill(name);
  await feld.getByRole('button', { name: new RegExp(name) }).click();
}

/** Die Trefferliste zu einem Suchbegriff öffnen, ohne schon zu wählen. */
export async function suchen(seite: Page, waehler: string, begriff: string) {
  const feld = seite.getByTestId(waehler);
  await feld.getByRole('combobox').fill(begriff);
  return feld;
}

/** Die Chips eines Wählers als Namen. */
export async function gewaehlt(seite: Page, waehler: string): Promise<string[]> {
  return seite
    .getByTestId(waehler)
    .locator('.k-chip')
    .allTextContents()
    .then((texte) => texte.map((t) => t.replace(/×$/, '').trim()));
}
