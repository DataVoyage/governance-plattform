/**
 * V-INT — Integration und Nachweis.
 *
 * Der einzige Bereich, in dem der „Anwender" ein anderes System ist: die
 * Provisionierungsplattform, die importiert, und der andockende Dienst, der
 * die Governance-Query-API befragt (Architektur 7.2, 7.3).
 */

import { expect } from '@playwright/test';

import {
  API,
  SERVICE_TOKEN,
  anmelden,
  bewerten,
  kennzeichen,
  kopf,
  organisation,
  plattformKopf,
  prozessAnlegen,
  toolAnlegen,
  toolMitProzess,
  vorgang,
} from './hilfen';

const dienst = { 'X-Service-Token': SERVICE_TOKEN };

vorgang('V-INT-01', async ({ request }) => {
  const marke = kennzeichen();
  const h = await plattformKopf(request); // Adapter betreibt nur die Plattform
  const antwort = await request.post(`${API}/api/v1/import/assets`, {
    headers: h,
    data: {
      quelle: 'zentrale-entwicklungsplattform',
      datensaetze: [
        { typ: 'tool', externe_id: `T-${marke}`, name: `Import ${marke}` },
        { typ: 'datenobjekt', externe_id: `D-${marke}`, name: `Datenimport ${marke}` },
      ],
    },
  });
  expect(antwort.status()).toBe(200);

  const tools = await (await request.get(`${API}/api/v1/tools`, { headers: h })).json();
  const tool = tools.find((t: { name: string }) => t.name === `Import ${marke}`);
  expect(tool.status).toBe('importiert_unbestaetigt');
  expect(tool.herkunft).toBe('importiert');

  // Ein unbestätigtes Tool ist nicht verknüpfbar — es würde sonst erben,
  // bevor jemand geprüft hat, ob es das gemeinte Objekt ist.
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, { name: `Ziel ${marke}` });
  // Verknüpfen ist keine Sache der Plattform: sie importiert und bestätigt,
  // mehr nicht (E-57). Deshalb hier der Zugang, der es dürfte — und der
  // trotzdem abgewiesen wird, weil das Objekt unbestätigt ist.
  const kante = await request.post(`${API}/api/v1/tools/${tool.id}/prozesse`, {
    headers: await kopf(request),
    data: { prozessobjekt_id: prozess.id },
  });
  expect(kante.status()).toBe(422);
});

vorgang('V-INT-02', async ({ request }) => {
  const marke = kennzeichen();
  const h = await plattformKopf(request); // Adapter betreibt nur die Plattform
  const importieren = (name: string, umgebung: string) =>
    request.post(`${API}/api/v1/import/assets`, {
      headers: h,
      data: {
        quelle: 'zentrale-entwicklungsplattform',
        datensaetze: [
          {
            typ: 'tool',
            externe_id: `T-${marke}`,
            name,
            metadaten: { technologie: 'python', umgebung },
          },
        ],
      },
    });
  await importieren(`Alter Name ${marke}`, 'alt');
  const tools = await (await request.get(`${API}/api/v1/tools`, { headers: h })).json();
  const tool = tools.find((t: { name: string }) => t.name === `Alter Name ${marke}`);
  // Die Kategorie ist ein Governance-Feld — die Plattform setzt sie nie (E-57).
  const gesetzt = await request.patch(`${API}/api/v1/tools/${tool.id}`, {
    headers: await kopf(request),
    data: { kategorie: 'kernanwendung' },
  });
  expect(gesetzt.status()).toBe(200);

  await importieren(`Neuer Name ${marke}`, 'neu');
  const danach = await (await request.get(`${API}/api/v1/tools/${tool.id}`, { headers: h })).json();
  expect(danach.name).toBe(`Neuer Name ${marke}`);
  expect(danach.metadaten.umgebung).toBe('neu');
  // Das Governance-Feld überlebt den Sync (Architektur 8.3).
  expect(danach.kategorie).toBe('kernanwendung');
});

vorgang('V-INT-03', async ({ request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, { name: `Abfragbar ${marke}` });
  // Tier 3 als Vorbedingung; das Antwortmuster liegt in `bewerten`.
  await bewerten(request, prozess.id, true);
  const tool = await toolAnlegen(request, { name: `Andocker ${marke}` });
  await toolMitProzess(request, tool.id, prozess.id);

  const tier = await (
    await request.get(`${API}/api/v1/query/prozess/${prozess.id}/tier`, { headers: dienst })
  ).json();
  expect(tier.tier).toBe(3);
  expect(tier.profil.ds).toBe(3);

  const rahmen = await (
    await request.get(`${API}/api/v1/query/tool/${tool.id}/erlaubnisrahmen`, { headers: dienst })
  ).json();
  expect(rahmen.tier).toBe(3);
});

vorgang('V-INT-04', async ({ request }) => {
  const org = await organisation(request);
  const prozess = await prozessAnlegen(request, org, { name: `Geschuetzt ${kennzeichen()}` });

  const ohne = await request.get(`${API}/api/v1/query/prozess/${prozess.id}/tier`);
  expect(ohne.status()).toBe(401);

  // Auch ein gültiges Nutzertoken öffnet die Query-API nicht.
  const mitNutzer = await request.get(`${API}/api/v1/query/prozess/${prozess.id}/tier`, {
    headers: await kopf(request),
  });
  expect(mitNutzer.status()).toBe(401);
});

vorgang('V-INT-05', async ({ request }) => {
  const erste = await (
    await request.get(`${API}/api/v1/query/changes?since=0`, { headers: dienst })
  ).json();
  const cursor = erste.naechster_cursor;

  const org = await organisation(request);
  await prozessAnlegen(request, org, { name: `Nach dem Cursor ${kennzeichen()}` });

  const zweite = await (
    await request.get(`${API}/api/v1/query/changes?since=${cursor}`, { headers: dienst })
  ).json();
  expect(zweite.changes.length).toBeGreaterThan(0);

  // Derselbe Cursor liefert keine Dopplungen.
  const dritte = await (
    await request.get(`${API}/api/v1/query/changes?since=${zweite.naechster_cursor}`, {
      headers: dienst,
    })
  ).json();
  const ids = new Set(zweite.changes.map((c: { id: string }) => c.id));
  for (const eintrag of dritte.changes) expect(ids.has(eintrag.id)).toBe(false);
});

vorgang('V-INT-06', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, { name: `Nachweisbar ${marke}` });
  await bewerten(request, prozess.id, true);

  // Eine schreibende Aktion über die Oberfläche, die sich wiederfinden lassen
  // muss.
  await anmelden(page);
  await page.goto(`/de/prozesse/${prozess.id}/bearbeiten`);
  await page.getByLabel('Name').fill(`Umbenannt ${marke}`);
  await page.getByRole('button', { name: 'Speichern' }).click();
  await expect(page.getByRole('heading', { name: `Umbenannt ${marke}` })).toBeVisible();

  await page.goto('/de/nachweis?art=prozessobjekte');
  const zeile = page
    .locator('.k-zeile')
    .filter({ hasText: `Umbenannt ${marke}` })
    .first();
  await expect(zeile).toContainText('Geändert');
  await expect(zeile).toContainText('Vorgangs-Administrator');
  await expect(zeile).toContainText(`name: Nachweisbar ${marke} → Umbenannt ${marke}`);
});
