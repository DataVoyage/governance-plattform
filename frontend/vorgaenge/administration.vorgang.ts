/**
 * V-ADM — Administration und Rollen.
 *
 * Nutzer, Rollen und Konfiguration — die Anwendung wird selbsttragend. Bis
 * AP-9 waren Rollen nur über die API zu vergeben; wer die Anwendung in Betrieb
 * nehmen wollte, brauchte einen Token und ein Terminal.
 */

import { expect, type APIRequestContext, type Page } from '@playwright/test';

import {
  API,
  anmelden,
  anwenderMitRolle,
  bewerten,
  datenobjektAnlegen,
  kennzeichen,
  kopf,
  organisation,
  prozessAnlegen,
  toolAnlegen,
  vorgang,
  type Organisation,
} from './hilfen';

/** Einen Anwender ohne Rolle anlegen; liefert seine Kennung. */
async function anwender(
  anfrage: APIRequestContext,
  subject: string,
  name: string,
): Promise<string> {
  const h = await kopf(anfrage, subject, name);
  const ich = await (await anfrage.get(`${API}/api/v1/auth/me`, { headers: h })).json();
  return ich.id;
}

/** Die Zeile eines Nutzers in der Verwaltung öffnen. */
async function nutzerOeffnen(seite: Page, userId: string) {
  await seite.goto('/de/verwaltung');
  await seite.getByTestId(`nutzer-${userId}`).click();
}

vorgang('V-ADM-01', async ({ page, request }) => {
  const marke = kennzeichen();
  const suchbar = await anwender(request, `suchbar-${marke}`, `Suchbar ${marke}`);
  await anwender(request, `versteckt-${marke}`, `Versteckt ${marke}`);
  await anmelden(page);

  await page.goto('/de/verwaltung');
  const zeile = page.getByTestId(`nutzer-${suchbar}`);
  await expect(zeile).toContainText(`Suchbar ${marke}`);
  await expect(zeile).toContainText(`suchbar-${marke}@beispiel-ag.de`);
  await expect(zeile).toContainText('Aktiv');
  await expect(zeile).toContainText('Führungskraft: nicht hinterlegt');

  await page.getByLabel('Nutzer suchen').fill(`Suchbar ${marke}`);
  await expect(page.getByTestId(`nutzer-${suchbar}`)).toBeVisible();
  await expect(page.getByText(`Versteckt ${marke}`)).toHaveCount(0);
});

vorgang('V-ADM-02', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const neuer = await anwender(request, `neu-${marke}`, `Neu ${marke}`);
  await anmelden(page);

  await nutzerOeffnen(page, neuer);
  await expect(page.getByText('Diesem Nutzer ist noch keine Rolle zugewiesen.')).toBeVisible();

  // Die Rolle trägt ihre Erklärung aus A.15 mit — wer zuweist, soll nicht
  // raten, was der Name bedeutet.
  await page.getByLabel('Rolle').selectOption('prozess_owner');
  await expect(page.getByText(/Legt Prozessobjekte im eigenen Bereich an/)).toBeVisible();

  await page.getByLabel('Geltungsbereich').selectOption('organisationseinheit');
  await page.getByLabel('Organisationseinheit').selectOption(org.intId);
  await page.getByTestId('rolle-zuweisen').click();

  // Die Zuweisung steht am Nutzer, mit Rolle und Bereich im Klartext.
  await page.goto('/de/verwaltung');
  const zeile = page.getByTestId(`nutzer-${neuer}`);
  await expect(zeile).toContainText('Prozess-Owner');
  await expect(zeile).toContainText('INT');
});

vorgang('V-ADM-03', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  for (const name of ['Erster', 'Zweiter']) {
    await prozessAnlegen(request, org, { name: `${name} ${marke}` });
  }
  const neuer = await anwender(request, `vorschau-${marke}`, `Vorschau ${marke}`);
  await anmelden(page);

  await nutzerOeffnen(page, neuer);
  await page.getByLabel('Rolle').selectOption('prozess_owner');
  await page.getByLabel('Geltungsbereich').selectOption('organisationseinheit');
  await page.getByLabel('Organisationseinheit').selectOption(org.intId);

  // Die Zahl steht vor der Entscheidung, nicht danach.
  await expect(page.getByTestId('wirkung')).toContainText('2 Prozessobjekte');
  await expect(page.getByText(/Zum Beispiel/)).toContainText(`Erster ${marke}`);
});

vorgang('V-ADM-04', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, { name: `Entzogen ${marke}` });
  const nutzerId = await anwenderMitRolle(
    request,
    `entzug-${marke}`,
    `Entzug ${marke}`,
    'prozess_owner',
    'organisationseinheit',
    org.intId,
  );

  // Vorher sieht er den Prozess.
  await anmelden(page, `entzug-${marke}`, `Entzug ${marke}`);
  await expect(page.getByRole('link', { name: new RegExp(`Entzogen ${marke}`) })).toBeVisible();
  await page.getByRole('button', { name: 'Abmelden' }).click();

  await anmelden(page);
  await nutzerOeffnen(page, nutzerId);
  const zuweisung = page.locator('[data-testid^="zuweisung-"]').first();
  await expect(zuweisung).toContainText('Prozess-Owner');
  await zuweisung.getByRole('button', { name: 'Entziehen' }).click();
  await expect(page.locator('[data-testid^="zuweisung-"]')).toHaveCount(0);
  await page.getByRole('button', { name: 'Abmelden' }).click();

  // Danach nicht mehr — sofort, ohne Zwischenschritt.
  await anmelden(page, `entzug-${marke}`, `Entzug ${marke}`);
  await expect(page.getByRole('link', { name: new RegExp(`Entzogen ${marke}`) })).toHaveCount(0);
  await page.goto(`/de/prozesse/${prozess.id}`);
  await expect(page.getByRole('alert')).toBeVisible();
});

vorgang('V-ADM-05', async ({ page, request }) => {
  const marke = kennzeichen();
  const meiner: Organisation = await organisation(request, marke);
  const fremder = await organisation(request, kennzeichen());
  const meinProzess = await prozessAnlegen(request, meiner, { name: `Meiner ${marke}` });
  const fremdProzess = await prozessAnlegen(request, fremder, { name: `Fremder ${marke}` });

  // Der Administrator vergibt die Rolle über die Oberfläche — das ist die
  // Abnahme dieses Pakets.
  const neuer = await anwender(request, `frisch-${marke}`, `Frisch ${marke}`);
  await anmelden(page);
  await nutzerOeffnen(page, neuer);
  await page.getByLabel('Rolle').selectOption('prozess_owner');
  await page.getByLabel('Geltungsbereich').selectOption('organisationseinheit');
  await page.getByLabel('Organisationseinheit').selectOption(meiner.intId);
  await page.getByTestId('rolle-zuweisen').click();
  await expect(page.locator('[data-testid^="zuweisung-"]')).toHaveCount(1);
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Abmelden' }).click();

  // Genau die Objekte des zugewiesenen Scopes — keine anderen.
  await anmelden(page, `frisch-${marke}`, `Frisch ${marke}`);
  await expect(page.getByRole('link', { name: new RegExp(`Meiner ${marke}`) })).toBeVisible();
  await expect(page.getByRole('link', { name: new RegExp(`Fremder ${marke}`) })).toHaveCount(0);
  await page.goto(`/de/prozesse/${fremdProzess.id}`);
  await expect(page.getByRole('alert')).toBeVisible();
  expect(meinProzess.id).toBeTruthy();
});

vorgang('V-ADM-06', async ({ page, request }) => {
  const marke = kennzeichen();
  await anwender(request, `ohne-${marke}`, `Ohne Rolle ${marke}`);
  await anmelden(page, `ohne-${marke}`, `Ohne Rolle ${marke}`);

  // Nicht verlinkt …
  await expect(page.getByRole('navigation').getByRole('link', { name: 'Verwaltung' })).toHaveCount(
    0,
  );

  // … und über die Adresse ohne Inhalt: der Server weist ab, die Seite sagt
  // warum (Architektur 10.2).
  await page.goto('/de/verwaltung');
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.locator('[data-testid^="nutzer-"]')).toHaveCount(0);
});

vorgang('V-ADM-08', async ({ page, request }) => {
  // Der Auditor liest bereichsübergreifend und schreibt nie. Bis AP-9 sah er
  // trotzdem jedes Bearbeitungsfeld und erfuhr erst beim Speichern, dass es
  // nicht geht. Geprüft wird jetzt beides: er sieht alles, und er findet
  // nichts, was etwas ändert — mit dem Satz, warum.
  const marke = kennzeichen();
  const org: Organisation = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, { name: `Geprüft ${marke}` });

  await anwenderMitRolle(request, `pruefer-${marke}`, `Prüfer ${marke}`, 'auditor', 'global');
  await anmelden(page, `pruefer-${marke}`, `Prüfer ${marke}`);

  // Sichtbar ist alles — auch ein Prozessobjekt aus einem fremden Bereich.
  await page.goto(`/de/prozesse/${prozess.id}`);
  await expect(page.getByRole('heading', { name: `Geprüft ${marke}` })).toBeVisible();

  // Änderbar ist nichts, und die Anwendung sagt es.
  await expect(page.getByText(/dürfen es aber nicht ändern/).first()).toBeVisible();
  await expect(page.getByRole('link', { name: 'Bearbeiten' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Aktivieren' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Bewertung durchführen' })).toHaveCount(0);
  await expect(page.getByTestId('sv-oeffnen')).toHaveCount(0);
  await expect(page.getByTestId('gate-einreichen')).toHaveCount(0);

  // Auch die Liste bietet nichts zum Anlegen an.
  await page.goto('/de/prozesse');
  await expect(page.getByRole('link', { name: 'Prozessobjekt anlegen' })).toHaveCount(0);
});

vorgang('V-ADM-09', async ({ page, request }) => {
  // Der Prozess-Umsetzer darf genau eine Sache: die lokale Abweichung seiner
  // Landesorganisation. Alles Übrige ist gesperrt — und erklärt.
  const marke = kennzeichen();
  const org: Organisation = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, {
    name: `Umgesetzt ${marke}`,
    umsetzung_land_org_ids: [org.deId],
  });

  await anwenderMitRolle(
    request,
    `umsetzer-${marke}`,
    `Umsetzer ${marke}`,
    'prozess_umsetzer',
    'organisationseinheit',
    org.deId,
  );
  await anmelden(page, `umsetzer-${marke}`, `Umsetzer ${marke}`);

  await page.goto(`/de/prozesse/${prozess.id}`);
  await expect(page.getByRole('heading', { name: `Umgesetzt ${marke}` })).toBeVisible();

  // Der eine Weg wird benannt, die übrigen fehlen.
  await expect(page.getByText(/lokale Abweichung Ihrer Landesorganisation/)).toBeVisible();
  await expect(page.getByRole('link', { name: 'Bearbeiten' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Bewertung durchführen' })).toHaveCount(0);
});

vorgang('V-ADM-07', async ({ page, request }) => {
  const marke = kennzeichen();
  await anwenderMitRolle(request, `konf-${marke}`, `Governance ${marke}`, 'governance', 'global');
  await anmelden(page, `konf-${marke}`, `Governance ${marke}`);

  await page.goto('/de/konfiguration');
  await expect(page.getByRole('heading', { name: 'Einstellungen' })).toBeVisible();

  // Fristen, Schwellen und Vorlauf — je eine aus jeder Gruppe.
  await expect(page.getByTestId('einstellung-lenkung_frist_tage_tier1')).toBeVisible();
  await expect(page.getByTestId('einstellung-asset_inaktiv_tage')).toBeVisible();
  await expect(
    page.getByTestId('einstellung-selbstverpflichtung_erinnerung_vorlauf_tage'),
  ).toBeVisible();

  // Ohne Neustart änderbar: der neue Wert steht nach dem Neuladen da.
  const zeile = page.getByTestId('einstellung-asset_inaktiv_tage');
  await zeile.getByLabel('Ab wann ein Tool als inaktiv gilt').fill('200');
  await page.getByTestId('sichern-asset_inaktiv_tage').click();
  await expect(page.getByTestId('sichern-asset_inaktiv_tage')).toHaveText('Gesichert');

  await page.reload();
  await expect(page.getByTestId('einstellung-asset_inaktiv_tage').getByRole('textbox')).toHaveValue(
    '200',
  );

  // Zurückstellen: die Einstellung wirkt global, und der nächste Vorgang soll
  // sie so vorfinden, wie sie gemeint ist (siehe E-35).
  await zeile.getByLabel('Ab wann ein Tool als inaktiv gilt').fill('180');
  await page.getByTestId('sichern-asset_inaktiv_tage').click();
  await expect(page.getByTestId('sichern-asset_inaktiv_tage')).toHaveText('Gesichert');
});

vorgang('V-ADM-10', async ({ request }) => {
  // Ein Vorgang ohne Oberfläche, mit Absicht: die Frage ist, ob die Daten
  // fehlen oder nur nicht angezeigt werden. Das lässt sich nur an der API
  // beantworten — hier wird an der Liste vorbei direkt nach der Kennung
  // gefragt.
  const marke = kennzeichen();
  const org: Organisation = await organisation(request, marke);
  const datenobjekt = await datenobjektAnlegen(request, {
    name: `Fremde Daten ${marke}`,
    fachbereich_id: org.fachbereichId,
  });

  // Der Fremde ist kein Rechtloser: er trägt dieselbe Rolle, nur in einem
  // anderen Fachbereich. Genau daran hängt die Regel — nicht an der Rolle.
  const anderer: Organisation = await organisation(request, `${marke}b`);
  await anwenderMitRolle(
    request,
    `fremd-${marke}`,
    `Anderer Bereich ${marke}`,
    'datenobjekt_owner',
    'fachbereich',
    anderer.fachbereichId,
  );
  const fremd = await kopf(request, `fremd-${marke}`, `Anderer Bereich ${marke}`);

  // Vier Wege zum selben Objekt, vier gleiche Antworten.
  const liste = await (await request.get(`${API}/api/v1/datenobjekte`, { headers: fremd })).json();
  expect(liste.map((eintrag: { id: string }) => eintrag.id)).not.toContain(datenobjekt.id);
  expect(
    (
      await request.get(`${API}/api/v1/datenobjekte/${datenobjekt.id}`, { headers: fremd })
    ).status(),
  ).toBe(403);
  expect(
    (
      await request.get(`${API}/api/v1/datenobjekte/${datenobjekt.id}/wirkung`, { headers: fremd })
    ).status(),
  ).toBe(403);
  expect(
    (
      await request.patch(`${API}/api/v1/datenobjekte/${datenobjekt.id}`, {
        headers: fremd,
        data: { kategorie: 'vertraulich' },
      })
    ).status(),
  ).toBe(403);

  // Die Gegenprobe: im eigenen Bereich steht dasselbe Objekt offen.
  await anwenderMitRolle(
    request,
    `eigen-${marke}`,
    `Im Bereich ${marke}`,
    'datenobjekt_owner',
    'fachbereich',
    org.fachbereichId,
  );
  const eigen = await kopf(request, `eigen-${marke}`, `Im Bereich ${marke}`);
  expect(
    (
      await request.get(`${API}/api/v1/datenobjekte/${datenobjekt.id}`, { headers: eigen })
    ).status(),
  ).toBe(200);
});

vorgang('V-ADM-11', async ({ page, request }) => {
  // Ein Bereich gehört einer Rolle, nicht der Person (P-App-3). Wer als
  // Prozess-Umsetzer in einer Einheit steht, sieht dort deshalb *nicht*, was
  // einem technischen Owner zusteht — bis AP-12 tat er genau das, weil die
  // Anwendung die Bereiche aller Rollen zusammenwarf (R-7).
  const marke = kennzeichen();
  const org: Organisation = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, {
    name: `Fremd gefuehrt ${marke}`,
    umsetzung_land_org_ids: [org.deId],
  });
  const tool = await toolAnlegen(request, {
    name: `Nur fuer Technik ${marke}`,
    organisationseinheit_id: org.deId,
  });
  const quelle = await datenobjektAnlegen(request, {
    name: `Nur fuer Daten ${marke}`,
    fachbereich_id: org.fachbereichId,
  });

  // Derselbe Bereich, eine andere Rolle: der Umsetzer der Einheit DE.
  await anwenderMitRolle(
    request,
    `umsetzer-${marke}`,
    `Umsetzer ${marke}`,
    'prozess_umsetzer',
    'organisationseinheit',
    org.deId,
  );
  await anmelden(page, `umsetzer-${marke}`, `Umsetzer ${marke}`);

  // Seinen Prozess sieht er — dafür ist er da.
  await page.goto(`/de/prozesse/${prozess.id}`);
  await expect(page.getByRole('heading', { name: prozess.name })).toBeVisible();

  // Das Datenobjekt des Fachbereichs geht ihn nichts an: es hängt an keinem
  // seiner Objekte, und die Rolle dafür hat er nicht.
  await page.goto('/de/datenobjekte');
  await expect(page.getByRole('link', { name: new RegExp(quelle.name) })).toHaveCount(0);
  await page.goto(`/de/datenobjekte/${quelle.id}`);
  await expect(page.getByRole('alert')).toBeVisible();

  // Das Tool-Objekt steht in *seiner* Einheit DE — und hängt an keinem seiner
  // Prozesse. Gleiche Einheit, andere Rolle: er sieht es nicht. Genau hier
  // hätte eine rollenblind gesammelte Bereichsliste ihn durchgelassen.
  await page.goto('/de/tools');
  await expect(page.getByRole('link', { name: new RegExp(tool.name) })).toHaveCount(0);
  await page.goto(`/de/tools/${tool.id}`);
  await expect(page.getByRole('alert')).toBeVisible();

  // Und anlegen darf er nichts — auch nicht im eigenen Bereich.
  await page.goto('/de/datenobjekte');
  await expect(page.getByRole('button', { name: 'Datenobjekt anlegen' })).toHaveCount(0);
});
