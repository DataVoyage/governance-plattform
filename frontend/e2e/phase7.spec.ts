/**
 * Abnahme von Phase 7 gegen den laufenden Server.
 *
 * Die Governance-Query-API hat keine Oberflaeche — sie ist der Anschlusspunkt
 * fuer andockende Anwendungen. Dieser Lauf spielt genau das durch: ein
 * Platzhalter-Client, der nur der OpenAPI-Dokumentation folgt, meldet sich mit
 * einem Service-Token an, holt Tier, K-Klassen und Erlaubnisrahmen und
 * verarbeitet danach Deltas ueber den Cursor.
 *
 * Geprueft werden die Kriterien 7.1 (dieselben Werte wie die Fachlogik), 7.2
 * (ohne Service-Authentifizierung keine Auskunft), 7.3 (die Dokumentation
 * traegt eine Probeintegration) und 7.4 (Delta lueckenlos und zustandslos).
 */

import { expect, test, type APIRequestContext } from '@playwright/test';

const API = 'http://127.0.0.1:8100';
const ADMIN = 'e2e-admin';
const SERVICE_TOKEN = 'e2e-service-token';

const TIER3_ANTWORTEN = {
  '1a': false,
  '2a': true,
  '3a': false,
  '3b': false,
  '3c': true,
  '4a': false,
  '4b': false,
  '4c': true,
  '5a': false,
  '5b': true,
  '6a': false,
  '6b': true,
};

async function kopf(anfrage: APIRequestContext) {
  const antwort = await anfrage.post(`${API}/api/v1/auth/dev-token`, {
    data: { subject: ADMIN, email: `${ADMIN}@beispiel-ag.de`, name: 'E2E Administrator' },
  });
  return { Authorization: `Bearer ${(await antwort.json()).access_token}` };
}

/** Prueft jede Aufbau-Antwort, damit ein Fehler dort sofort sichtbar wird. */
async function json(antwort: Awaited<ReturnType<APIRequestContext['post']>>) {
  const koerper = await antwort.json();
  expect(
    antwort.ok(),
    `Aufbau fehlgeschlagen (${antwort.status()}): ${JSON.stringify(koerper)}`,
  ).toBeTruthy();
  return koerper;
}

/** Legt ein bewertetes Prozessobjekt samt verknuepftem Tool an. */
async function landschaft(anfrage: APIRequestContext) {
  const h = await kopf(anfrage);
  const kennung = Math.random().toString(36).slice(2, 8);
  const fachbereich = await json(
    await anfrage.post(`${API}/api/v1/fachbereiche`, {
      headers: h,
      data: { name: `Bereich ${kennung}`, code: `fb-${kennung}` },
    }),
  );
  const int = await json(
    await anfrage.post(`${API}/api/v1/organisationseinheiten`, {
      headers: h,
      data: { fachbereich_id: fachbereich.id, ebene: 'INT' },
    }),
  );
  const ich = await (await anfrage.get(`${API}/api/v1/auth/me`, { headers: h })).json();
  const datenobjekt = await json(
    await anfrage.post(`${API}/api/v1/datenobjekte`, {
      headers: h,
      data: { name: `Kreditorenstamm ${kennung}`, fachbereich_id: fachbereich.id },
    }),
  );
  const prozess = await json(
    await anfrage.post(`${API}/api/v1/prozesse`, {
      headers: h,
      data: {
        name: `Prozess ${kennung}`,
        owner_user_id: ich.id,
        stellvertretung_user_id: ich.id,
        prozessgeber_org_id: int.id,
        supplier: '',
        input_datenobjekt_ids: [datenobjekt.id],
        process_steps: '',
        output: '',
        customer: 'bereich',
        ausfallfolge: 'spuerbar',
      },
    }),
  );
  await json(
    await anfrage.post(`${API}/api/v1/prozesse/${prozess.id}/bewertungen`, {
      headers: h,
      data: { modus: 'vollstaendig', antworten: TIER3_ANTWORTEN },
    }),
  );
  await anfrage.patch(`${API}/api/v1/prozesse/${prozess.id}`, {
    headers: h,
    data: { erlaubte_externe_ziele: ['sftp.partner.example'] },
  });
  const tool = await json(
    await anfrage.post(`${API}/api/v1/tools`, { headers: h, data: { name: `Tool ${kennung}` } }),
  );
  // Ohne die drei Erklaerungen aus A.6 gibt es keine Prozesskante.
  await anfrage.put(`${API}/api/v1/tools/${tool.id}/attestierungen`, {
    headers: h,
    data: {
      attest_entscheidung_ueber_personen: false,
      attest_mensch_dazwischen: true,
      attest_undeklarierte_quellen: false,
    },
  });
  const kante = await anfrage.post(`${API}/api/v1/tools/${tool.id}/prozesse`, {
    headers: h,
    data: { prozessobjekt_id: prozess.id },
  });
  if (kante.status() !== 201) throw new Error(`Kante nicht angelegt: ${await kante.text()}`);
  return {
    prozessId: prozess.id,
    toolId: tool.id,
    datenobjektName: datenobjekt.name,
    kopfzeilen: h,
  };
}

const service = { 'X-Service-Token': SERVICE_TOKEN };

test.describe('Phase 7 gegen den laufenden Server', () => {
  test('ohne Service-Token gibt es keine Auskunft', async ({ request }) => {
    const { prozessId } = await landschaft(request);
    const ohne = await request.get(`${API}/api/v1/query/prozess/${prozessId}/tier`);
    expect(ohne.status()).toBe(401);

    const falsch = await request.get(`${API}/api/v1/query/prozess/${prozessId}/tier`, {
      headers: { 'X-Service-Token': 'nicht-ausgestellt' },
    });
    expect(falsch.status()).toBe(401);
  });

  test('ein Nutzertoken oeffnet die Query-API nicht', async ({ request }) => {
    const { prozessId, kopfzeilen } = await landschaft(request);
    const antwort = await request.get(`${API}/api/v1/query/prozess/${prozessId}/tier`, {
      headers: kopfzeilen,
    });
    expect(antwort.status()).toBe(401);
  });

  test('die OpenAPI-Dokumentation beschreibt alle vier Endpunkte', async ({ request }) => {
    const spezifikation = await (await request.get(`${API}/api/v1/openapi.json`)).json();
    const pfade = Object.keys(spezifikation.paths).filter((p) => p.includes('/query/'));
    expect(pfade.sort()).toEqual([
      '/api/v1/query/changes',
      '/api/v1/query/prozess/{prozess_id}/k-klassen',
      '/api/v1/query/prozess/{prozess_id}/tier',
      '/api/v1/query/tool/{tool_id}/erlaubnisrahmen',
    ]);
    for (const pfad of pfade) {
      // Nur Auskunft: kein Endpunkt der Query-API veraendert etwas.
      expect(Object.keys(spezifikation.paths[pfad])).toEqual(['get']);
      expect(spezifikation.paths[pfad].get.summary).toBeTruthy();
      expect(spezifikation.paths[pfad].get.description).toBeTruthy();
    }
  });

  test('Probeintegration: Auskunft holen und Deltas verarbeiten', async ({ request }) => {
    const { prozessId, toolId, datenobjektName, kopfzeilen } = await landschaft(request);

    const tier = await (
      await request.get(`${API}/api/v1/query/prozess/${prozessId}/tier`, { headers: service })
    ).json();
    expect(tier.tier).toBe(3);
    expect(tier.profil).toEqual({ ki: 0, ds: 3, mb: 1, it: 1, rg: 2, ur: 2 });

    const klassen = await (
      await request.get(`${API}/api/v1/query/prozess/${prozessId}/k-klassen`, {
        headers: service,
      })
    ).json();
    expect(klassen.ausgeloest).toEqual(['K1', 'K2', 'K3', 'K4', 'K5', 'K7', 'K8', 'K9']);

    const rahmen = await (
      await request.get(`${API}/api/v1/query/tool/${toolId}/erlaubnisrahmen`, {
        headers: service,
      })
    ).json();
    expect(rahmen.erlaubte_datenobjekte.map((d: { name: string }) => d.name)).toEqual([
      datenobjektName,
    ]);
    expect(rahmen.erlaubte_reichweite).toBe('bereich');
    expect(rahmen.erlaubte_externe_ziele).toEqual(['sftp.partner.example']);
    expect(rahmen.tier).toBe(3);

    // Delta: der gelieferte Cursor geht unveraendert wieder hinein.
    const stand = await (
      await request.get(`${API}/api/v1/query/changes`, { headers: service })
    ).json();
    const cursor = stand.naechster_cursor;
    const leer = await (
      await request.get(`${API}/api/v1/query/changes?since=${cursor}`, { headers: service })
    ).json();
    expect(leer.changes).toEqual([]);

    await request.post(`${API}/api/v1/prozesse/${prozessId}/bewertungen`, {
      headers: kopfzeilen,
      data: { modus: 'vollstaendig', antworten: { ...TIER3_ANTWORTEN, '2a': false, '2b': true } },
    });

    const delta = await (
      await request.get(`${API}/api/v1/query/changes?since=${cursor}&entity_type=bewertung`, {
        headers: service,
      })
    ).json();
    expect(delta.changes.map((c: { entity_type: string }) => c.entity_type)).toEqual(['bewertung']);
    // Derselbe Cursor liefert erneut dasselbe Ergebnis.
    const wiederholt = await (
      await request.get(`${API}/api/v1/query/changes?since=${cursor}&entity_type=bewertung`, {
        headers: service,
      })
    ).json();
    expect(wiederholt).toEqual(delta);

    // Die Neubewertung schlaegt sofort in der Auskunft durch.
    const neu = await (
      await request.get(`${API}/api/v1/query/prozess/${prozessId}/tier`, { headers: service })
    ).json();
    expect(neu.profil.ds).toBe(2);
  });
});
