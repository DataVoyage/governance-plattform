/**
 * V-TOO — Tool-Objekt.
 *
 * „Was ein Tool tut, sagt die Telemetrie. Was es bewirkt, sagt sein Owner"
 * (Leitdokument A.6). Diese Vorgänge prüfen beide Hälften: die deklarierten
 * Stammdaten und die drei Erklärungen, die kein System liefern kann.
 */

import { expect, type Page } from '@playwright/test';

import {
  API,
  anmelden,
  anwenderMitRolle,
  datenobjektAnlegen,
  kennzeichen,
  kopf,
  organisation,
  prozessAnlegen,
  toolAnlegen,
  toolMitProzess,
  vorgang,
  waehle,
} from './hilfen';

/** Die drei Erklärungen über die Oberfläche abgeben. */
async function attestieren(seite: Page, antworten: [string, string][]) {
  for (const [feld, antwort] of antworten) {
    await seite.getByTestId(feld).getByRole('button', { name: antwort, exact: true }).click();
  }
  await seite.getByRole('button', { name: /Erklärung (abgeben|erneuern)/ }).click();
  await expect(seite.getByText('Vollständig abgegeben')).toBeVisible();
}

const UNAUFFAELLIG: [string, string][] = [
  ['attest_entscheidung_ueber_personen', 'Nein'],
  ['attest_mensch_dazwischen', 'Ja'],
  ['attest_undeklarierte_quellen', 'Nein'],
];

vorgang('V-TOO-01', async ({ page, request }) => {
  const org = await organisation(request);
  const name = `Rechnungs-Skript ${kennzeichen()}`;
  await anmelden(page);
  await page.goto('/de/tools');
  await page.getByRole('button', { name: 'Tool-Objekt anlegen' }).first().click();

  const blatt = page.getByRole('dialog');
  await blatt.getByLabel('Name').fill(name);
  // Erst die Einheit, dann die Personen: wählbar ist, wer dort technischer
  // Owner ist (docs/rollen-und-scopes.md, 6).
  await blatt
    .getByLabel('Organisationseinheit')
    .selectOption({ label: `${org.fachbereichName} — Land DE` });
  await blatt.getByLabel('Technischer Owner').selectOption({ label: 'Vorgangs-Administrator' });
  await blatt.getByLabel('Stellvertretung').selectOption({ label: 'Vorgangs-Administrator' });
  await blatt.getByLabel('Technologie').selectOption('apps-script');
  await blatt.getByLabel('Lauftyp').selectOption('geplant');
  await blatt.getByRole('button', { name: 'Speichern' }).click();

  const zeile = page.getByRole('link', { name: new RegExp(name) });
  await expect(zeile).toContainText('Apps Script');
  await expect(zeile).toContainText('Geplant');
});

vorgang('V-TOO-02', async ({ page, request }) => {
  const tool = await toolAnlegen(request, { name: `Zu erklaeren ${kennzeichen()}` }, false);
  await anmelden(page);
  await page.goto(`/de/tools/${tool.id}`);
  await expect(page.getByText('Noch nicht erklärt')).toBeVisible();

  await attestieren(page, UNAUFFAELLIG);

  // Mit Namen, nicht als Formularfeld (A.6).
  const karte = page
    .getByRole('heading', { name: 'Attestierungen' })
    .locator('xpath=ancestor::section[1]');
  await expect(karte).toContainText('Vorgangs-Administrator');
  await expect(karte.locator('.k-werte')).toContainText(new Date().getFullYear().toString());
});

vorgang('V-TOO-03', async ({ page, request }) => {
  const org = await organisation(request);
  const tool = await toolAnlegen(request, { name: `Ohne Erklaerung ${kennzeichen()}` }, false);
  await prozessAnlegen(request, org, { name: `Ziel ${kennzeichen()}` });
  await anmelden(page);
  await page.goto(`/de/tools/${tool.id}`);

  // Der Grund steht dort, wo die Verknüpfung erwartet wird — nicht im Protokoll.
  await expect(page.getByTestId('waehler-prozesse')).toHaveCount(0);
  await expect(
    page.getByText(/Ohne die drei Erklärungen ist keine Verknüpfung/).first(),
  ).toBeVisible();
});

vorgang('V-TOO-04', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const objekt = await datenobjektAnlegen(request, {
    name: `Kontaktdaten ${marke}`,
    kategorie: 'personenbezogen',
    fachbereich_id: org.fachbereichId,
  });
  const prozess = await prozessAnlegen(request, org, {
    name: `Auswertung ${marke}`,
    input_datenobjekt_ids: [objekt.id],
  });
  const tool = await toolAnlegen(request, { name: `Bewerter ${marke}` });
  await toolMitProzess(request, tool.id, prozess.id);

  await anmelden(page);
  await page.goto(`/de/prozesse/${prozess.id}`);
  await expect(page.getByTestId('mitbestimmung')).toContainText('Nein');

  // Die Erklärung wird korrigiert — und zieht die Ableitung nach (A.5, E-23).
  await page.goto(`/de/tools/${tool.id}`);
  await attestieren(page, [
    ['attest_entscheidung_ueber_personen', 'Ja'],
    ['attest_mensch_dazwischen', 'Ja'],
    ['attest_undeklarierte_quellen', 'Nein'],
  ]);
  await page.goto(`/de/prozesse/${prozess.id}`);
  await expect(page.getByTestId('mitbestimmung')).toContainText('Ja');
});

vorgang('V-TOO-05', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const prozess = await prozessAnlegen(request, org, {
    name: `Kritischer Prozess ${marke}`,
    ausfallfolge: 'kritisch',
  });
  const tool = await toolAnlegen(request, { name: `Erbe ${marke}` });
  await anmelden(page);
  await page.goto(`/de/tools/${tool.id}`);
  await waehle(page, 'waehler-prozesse', prozess.name);

  await expect(page.getByTestId('geerbt-kritikalitaet')).toContainText('3');
  // Das Erbe hat eine Adresse, keine anonyme Zahl (A.4.4).
  await expect(page.getByRole('link', { name: new RegExp(prozess.name) })).toContainText(
    'Bestimmt das Maximum',
  );
});

vorgang('V-TOO-06', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const gering = await prozessAnlegen(request, org, {
    name: `Gering ${marke}`,
    ausfallfolge: 'gering',
  });
  const kritisch = await prozessAnlegen(request, org, {
    name: `Kritisch ${marke}`,
    ausfallfolge: 'kritisch',
    customer: 'extern',
  });
  const tool = await toolAnlegen(request, { name: `Zwei Kanten ${marke}` });
  await anmelden(page);
  await page.goto(`/de/tools/${tool.id}`);

  await waehle(page, 'waehler-prozesse', gering.name);
  await expect(page.getByTestId('geerbt-kritikalitaet')).toContainText('1');

  await waehle(page, 'waehler-prozesse', kritisch.name);
  await expect(page.getByTestId('geerbt-kritikalitaet')).toContainText('3');
  await expect(page.getByTestId('geerbt-reichweite')).toContainText('Extern');

  // Die schwächere Kante wäre sonst eine stille Umgehung.
  await expect(page.getByRole('link', { name: new RegExp(kritisch.name) })).toContainText(
    'Bestimmt das Maximum',
  );
});

vorgang('V-TOO-07', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const prozess = await prozessAnlegen(request, org, {
    name: `Zu loesen ${marke}`,
    ausfallfolge: 'kritisch',
  });
  const tool = await toolAnlegen(request, { name: `Loeser ${marke}` });
  await toolMitProzess(request, tool.id, prozess.id);
  await anmelden(page);
  await page.goto(`/de/tools/${tool.id}`);
  await expect(page.getByTestId('geerbt-kritikalitaet')).toContainText('3');

  await page
    .getByTestId('waehler-prozesse')
    .getByRole('button', { name: `${prozess.name} entfernen` })
    .click();

  await expect(page.getByTestId('geerbt-kritikalitaet')).toContainText('0');
});

vorgang('V-TOO-08', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const objekt = await datenobjektAnlegen(request, {
    name: `Belege ${marke}`,
    kategorie: 'intern',
    fachbereich_id: org.fachbereichId,
  });
  const tool = await toolAnlegen(request, { name: `Nutzer ${marke}` });
  await anmelden(page);
  await page.goto(`/de/tools/${tool.id}`);

  await page.getByRole('button', { name: 'Liest und schreibt', exact: true }).click();
  await waehle(page, 'waehler-datenobjekte', objekt.name);

  const zeile = page.getByTestId(`nutzung-${objekt.id}`);
  await expect(zeile).toContainText(objekt.name);
  await expect(zeile.getByRole('combobox')).toHaveValue('lesen_schreiben');
});

vorgang('V-TOO-09', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const objekt = await datenobjektAnlegen(request, {
    name: `Journal ${marke}`,
    kategorie: 'intern',
    fachbereich_id: org.fachbereichId,
  });
  const tool = await toolAnlegen(request, { name: `Wechsler ${marke}` });
  const h = await kopf(request);
  await request.post(`${API}/api/v1/tools/${tool.id}/datenobjekte`, {
    headers: h,
    data: { datenobjekt_id: objekt.id, zugriffsart: 'lesen' },
  });
  await anmelden(page);
  await page.goto(`/de/tools/${tool.id}`);
  await expect(page.getByTestId('wirkungsart')).toContainText('Gestaltend');

  await page.getByTestId(`nutzung-${objekt.id}`).getByRole('combobox').selectOption('schreiben');

  // Schreibzugriff macht ein Tool verändernd — immer prüfpflichtig (A.6).
  await expect(page.getByTestId('wirkungsart')).toContainText('Verändernd');
  await expect(page.getByTestId('wirkungsart')).toContainText('Schreibt auf ein Datenobjekt');
});

vorgang('V-TOO-10', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const imRahmen = await datenobjektAnlegen(request, {
    name: `Kreditorenstamm ${marke}`,
    kategorie: 'intern',
    fachbereich_id: org.fachbereichId,
  });
  const daneben = await datenobjektAnlegen(request, {
    name: `Gesundheitsakte ${marke}`,
    kategorie: 'besondere_kategorie',
    fachbereich_id: org.fachbereichId,
  });
  const prozess = await prozessAnlegen(request, org, {
    name: `Rahmen ${marke}`,
    input_datenobjekt_ids: [imRahmen.id],
  });
  const tool = await toolAnlegen(request, { name: `Zweckbindung ${marke}` });
  await toolMitProzess(request, tool.id, prozess.id);
  await anmelden(page);
  await page.goto(`/de/tools/${tool.id}`);

  await waehle(page, 'waehler-datenobjekte', imRahmen.name);
  await expect(page.getByTestId(`nutzung-${imRahmen.id}`)).not.toContainText(
    'Außerhalb des Prozessrahmens',
  );

  await waehle(page, 'waehler-datenobjekte', daneben.name);
  await expect(page.getByTestId(`nutzung-${daneben.id}`)).toContainText(
    'Außerhalb des Prozessrahmens',
  );
  // Der Befund muss nicht gesucht werden (A.4.6).
  await expect(page.getByText(/Zweckbindung nicht belegt: 1 /)).toBeVisible();
});

vorgang('V-TOO-11', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const erklaert = await datenobjektAnlegen(request, {
    name: `Kreditoren ${marke}`,
    kategorie: 'intern',
    fachbereich_id: org.fachbereichId,
  });
  const weiteres = await datenobjektAnlegen(request, {
    name: `Debitoren ${marke}`,
    kategorie: 'intern',
    fachbereich_id: org.fachbereichId,
  });
  const prozess = await prozessAnlegen(request, org, {
    name: `Nur eine Quelle ${marke}`,
    input_datenobjekt_ids: [erklaert.id],
  });
  const tool = await toolAnlegen(request, { name: `Milder Befund ${marke}` });
  await toolMitProzess(request, tool.id, prozess.id);
  await anmelden(page);
  await page.goto(`/de/tools/${tool.id}`);
  await waehle(page, 'waehler-datenobjekte', weiteres.name);

  // Der schwächere Test aus A.4.6: Kategorie gedeckt, Objekt nicht erklärt.
  const zeile = page.getByTestId(`nutzung-${weiteres.id}`);
  await expect(zeile).toContainText('Nicht deklariert');
  await expect(zeile).not.toContainText('Außerhalb des Prozessrahmens');
});

vorgang('V-TOO-12', async ({ page, request }) => {
  const tool = await toolAnlegen(request, { name: `Unklar ${kennzeichen()}` }, false);
  await anmelden(page);
  await page.goto(`/de/tools/${tool.id}`);

  // Ohne Attestierung 2 darf niemand „gestaltend" behaupten (E-24).
  const feld = page.getByTestId('wirkungsart');
  await expect(feld).toContainText('Noch offen');
  await expect(feld).toContainText('Erst nach der zweiten Attestierung');
});

vorgang('V-TOO-13', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const objekt = await datenobjektAnlegen(request, {
    name: `Bewerbungen ${marke}`,
    kategorie: 'personenbezogen',
    fachbereich_id: org.fachbereichId,
  });
  const tool = await toolAnlegen(request, { name: `Autopilot ${marke}` }, false);
  const h = await kopf(request);
  await request.post(`${API}/api/v1/tools/${tool.id}/datenobjekte`, {
    headers: h,
    data: { datenobjekt_id: objekt.id, zugriffsart: 'lesen' },
  });
  await anmelden(page);
  await page.goto(`/de/tools/${tool.id}`);

  await attestieren(page, [
    ['attest_entscheidung_ueber_personen', 'Ja'],
    ['attest_mensch_dazwischen', 'Nein'],
    ['attest_undeklarierte_quellen', 'Nein'],
  ]);

  // Die Warnung aus A.6: das sieht man an keiner Berechtigung.
  const feld = page.getByTestId('wirkungsart');
  await expect(feld).toContainText('Verändernd');
  await expect(feld).toContainText('Kein Mensch zwischen Output und Wirkung');
});

vorgang('V-TOO-14', async ({ page, request }) => {
  const marke = kennzeichen();
  const h = await kopf(request);
  await request.post(`${API}/api/v1/import/assets`, {
    headers: h,
    data: {
      quelle: 'zentrale-entwicklungsplattform',
      datensaetze: [
        {
          typ: 'tool',
          externe_id: `TOOL-${marke}`,
          name: `Importiert ${marke}`,
          metadaten: { technologie: 'apps-script' },
        },
      ],
    },
  });
  await anmelden(page);
  await page.goto('/de/tools');
  await page.getByRole('link', { name: new RegExp(`Importiert ${marke}`) }).click();

  await expect(page.getByTestId('status')).toHaveText('Importiert, unbestätigt');
  await page.getByRole('button', { name: 'Bestätigen' }).click();
  await expect(page.getByTestId('status')).toHaveText('Bestätigt');

  // Erst danach ist die Attestierung und damit die Kante überhaupt möglich.
  await attestieren(page, UNAUFFAELLIG);
  await expect(page.getByTestId('waehler-prozesse')).toBeVisible();
});

vorgang('V-TOO-15', async ({ page, request }) => {
  const marke = kennzeichen();
  const h = await kopf(request);
  await request.post(`${API}/api/v1/import/assets`, {
    headers: h,
    data: {
      quelle: 'zentrale-entwicklungsplattform',
      datensaetze: [{ typ: 'tool', externe_id: `TOOL-${marke}`, name: `Unbestaetigt ${marke}` }],
    },
  });
  await anmelden(page);
  await page.goto('/de/tools');
  await page.getByRole('link', { name: new RegExp(`Unbestaetigt ${marke}`) }).click();

  // Ein unbestätigtes Tool würde erben, bevor jemand geprüft hat, ob es das
  // gemeinte Objekt ist (Architektur 7.2).
  await expect(page.getByTestId('waehler-prozesse')).toHaveCount(0);
  await expect(page.getByText(/kann es nicht mit einem Prozess/).first()).toBeVisible();
});

vorgang('V-TOO-16', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const prozess = await prozessAnlegen(request, org, {
    name: `Traeger ${marke}`,
    ausfallfolge: 'kritisch',
  });
  const erklaert = await toolAnlegen(request, {
    name: `Erklaert ${marke}`,
    technologie: 'appsheet',
  });
  await toolMitProzess(request, erklaert.id, prozess.id);
  const offen = await toolAnlegen(request, { name: `Offen ${marke}` }, false);

  await anmelden(page);
  await page.goto('/de/tools');
  await page.getByRole('searchbox', { name: 'Suchen' }).fill(marke);

  await expect(page.getByRole('link', { name: new RegExp(offen.name) })).toContainText(
    'Attestierung fehlt',
  );
  const zeile = page.getByRole('link', { name: new RegExp(erklaert.name) });
  await expect(zeile).toContainText('AppSheet');
  await expect(zeile).toContainText('Gestaltend');
});

vorgang('V-TOO-17', async ({ page, request }) => {
  const tool = await toolAnlegen(request, { name: `Zu melden ${kennzeichen()}` });
  await anmelden(page);
  await page.goto(`/de/tools/${tool.id}`);
  await expect(
    page.getByText('Für dieses Tool-Objekt ist noch kein Zustand erfasst.'),
  ).toBeVisible();

  await page.getByLabel('Zustand melden').selectOption('gelb');
  await page.getByLabel('Begründung').fill('Externes Ziel nicht im Rahmen');
  await page.getByRole('button', { name: 'Zustand melden' }).click();

  const aktuell = page.getByTestId('aktueller-zustand');
  await expect(aktuell).toContainText('Gelb');
  await expect(aktuell).toContainText('Externes Ziel nicht im Rahmen');
});

vorgang('V-TOO-18', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const objekt = await datenobjektAnlegen(request, {
    name: `Personalakte ${marke}`,
    kategorie: 'personenbezogen',
  });
  const prozess = await prozessAnlegen(request, org, { name: `Rahmenprozess ${marke}` });
  const tool = await toolAnlegen(request, { name: `Gerahmt ${marke}` });
  await toolMitProzess(request, tool.id, prozess.id);
  await anmelden(page);

  // Ein Datenobjekt, das der Prozess nicht führt: die Abweichung, die A.4.6
  // „der Compliance am meisten wert" nennt.
  await page.goto(`/de/tools/${tool.id}`);
  await waehle(page, 'waehler-datenobjekte', `Personalakte ${marke}`);

  // Erlaubt, gemessen und Abweichung stehen nebeneinander.
  const zeile = page.getByTestId('rahmen-datenobjekte');
  await expect(zeile.getByTestId('erlaubt-datenobjekte')).toHaveText('—');
  await expect(zeile.getByTestId('gemessen-datenobjekte')).toHaveText(`Personalakte ${marke}`);
  await expect(zeile.getByTestId('abweichung-datenobjekte')).toContainText(
    'Außerhalb des Rahmens genutzt',
  );
  await expect(page.getByTestId('gemessen-datenkategorie')).toContainText('Personenbezogen');
  await expect(page.getByTestId('erlaubt-datenkategorie')).toHaveText('—');
  await expect(page.getByTestId('abweichung-datenkategorie')).toContainText(
    'höhere Kategorie, als der Rahmen deckt',
  );
});

vorgang('V-TOO-19', async ({ page, request }) => {
  // Dieselbe Regel wie am Prozessobjekt: erst der Bereich, dann die Personen
  // (docs/rollen-und-scopes.md, 6).
  const marke = kennzeichen();
  const eigene = await organisation(request, marke);
  const fremde = await organisation(request, `${marke}f`);
  await anwenderMitRolle(
    request,
    `technik-${marke}`,
    `Technischer Owner ${marke}`,
    'technischer_owner',
    'fachbereich',
    eigene.fachbereichId,
  );
  await anmelden(page, `technik-${marke}`, `Technischer Owner ${marke}`);
  await page.goto('/de/tools');
  await page.getByRole('button', { name: 'Tool-Objekt anlegen' }).first().click();
  const blatt = page.getByRole('dialog');

  const einheiten = await blatt
    .getByLabel('Organisationseinheit')
    .locator('option')
    .allTextContents();
  expect(einheiten.join(' ')).toContain(eigene.fachbereichName);
  expect(einheiten.join(' ')).not.toContain(fremde.fachbereichName);

  await blatt
    .getByLabel('Organisationseinheit')
    .selectOption({ label: `${eigene.fachbereichName} — Land DE` });
  const personen = await blatt.getByLabel('Technischer Owner').locator('option').allTextContents();
  expect(personen).toContain(`Technischer Owner ${marke}`);
});
