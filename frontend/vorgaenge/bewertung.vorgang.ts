/**
 * V-BEW — Bewertung.
 *
 * Der Bewertungs-Wizard nach A.8: ableiten statt abfragen. Was die Datenlage
 * hergibt, steht als Vorschlag neben der Frage; wer anders antwortet, schreibt
 * einen Satz dazu. Die Vorgänge hier laufen deshalb über echte Datenobjekte
 * und echte Ausfallfolgen — ein Prozess ohne Daten hätte nichts, woraus sich
 * ein Vorschlag ableiten ließe, und die halbe Zusage von AP-4 bliebe ungeprüft.
 */

import { expect, type APIRequestContext, type Page } from '@playwright/test';

import {
  API,
  anmelden,
  datenobjektAnlegen,
  kennzeichen,
  organisation,
  prozessAnlegen,
  vorgang,
  type Organisation,
} from './hilfen';

/** Ein Prozess mit Entgeltdaten am Eingang — die Datenlage, die DS und MB trägt. */
async function mitEntgeltdaten(
  anfrage: APIRequestContext,
  org: Organisation,
  marke: string,
  felder: Record<string, unknown> = {},
) {
  const entgelt = await datenobjektAnlegen(anfrage, {
    name: `Entgeltdaten ${marke}`,
    kategorie: 'besondere_kategorie',
    fachbereich_id: org.fachbereichId,
  });
  const prozess = await prozessAnlegen(anfrage, org, {
    name: `Entgeltlauf ${marke}`,
    input_datenobjekt_ids: [entgelt.id],
    ...felder,
  });
  return { entgelt, prozess };
}

/**
 * Öffnet den Wizard auf der Bewertungsseite eines Prozesses.
 *
 * Kein Vorschaltbildschirm mehr: seit E-64 gibt es nur den vollständigen
 * Durchlauf, und ein Klick ohne Alternative ist keine Entscheidung.
 */
async function starte(seite: Page, prozessId: string) {
  await seite.goto(`/de/prozesse/${prozessId}/bewertung`);
  await expect(seite.getByTestId('frage')).toBeVisible();
}

/**
 * Beantwortet die aktuelle Frage und wartet, bis der Wizard weitergerückt ist.
 *
 * Gewartet wird auf den Netzaufruf, nicht auf eine DOM-Änderung: bei einem
 * Fehlschlag steht so der Statuscode des Servers in der Meldung.
 */
async function antworte(seite: Page, antwort: 'Ja' | 'Nein') {
  const vorher = await seite.getByTestId('frage').getAttribute('data-frage-id');
  const [ruf] = await Promise.all([
    seite.waitForResponse(
      (r) => r.url().includes('/bewertung/wizard') && r.request().method() === 'POST',
    ),
    seite.getByRole('button', { name: antwort, exact: true }).click(),
  ]);
  expect(ruf.ok(), `Wizard-Schritt: ${ruf.status()} ${await ruf.text()}`).toBeTruthy();
  await expect
    .poll(async () => {
      if ((await seite.getByTestId('frage').count()) === 0) return '__ende__';
      return seite.getByTestId('frage').getAttribute('data-frage-id');
    })
    .not.toBe(vorher);
}

/** Antwortet abweichend und begründet die Abweichung. */
async function antworteAbweichend(seite: Page, antwort: 'Ja' | 'Nein', begruendung: string) {
  await seite.getByRole('button', { name: antwort, exact: true }).click();
  await expect(seite.getByTestId('begruendung')).toBeVisible();
  await seite.getByLabel('Begründung der Abweichung').fill(begruendung);
  await seite.getByRole('button', { name: 'Weiter' }).click();
}

/**
 * Beantwortet die restlichen Fragen so, wie die Datenlage sie vorschlägt.
 *
 * Seit E-64 gibt es nur den vollständigen Durchlauf; ein Vorgang, der nur eine
 * Dimension prüfen will, muss die übrigen trotzdem zu Ende bringen. Der
 * Vorschlag ist dafür die richtige Antwort — er braucht keine Begründung.
 */
async function beendeDurchlauf(seite: Page) {
  for (let i = 0; i < 16; i += 1) {
    if ((await seite.getByTestId('frage').count()) === 0) break;
    const vorschlag = seite.getByTestId('vorschlag');
    const wert = (await vorschlag.count()) > 0 ? await vorschlag.getAttribute('data-wert') : null;
    await antworte(seite, wert === 'true' ? 'Ja' : 'Nein');
  }
}

vorgang('V-BEW-01', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  // Ausfallfolge „spuerbar" ergibt UR 2 — das durchgerechnete Beispiel aus A.9.
  const { prozess } = await mitEntgeltdaten(request, org, marke, { ausfallfolge: 'spuerbar' });
  await anmelden(page);
  await starte(page, prozess.id);

  // Alle sechs Blöcke in der festgelegten Reihenfolge (A.8.5).
  await expect(page.getByText('Schritt 1 von 6 — Künstliche Intelligenz')).toBeVisible();
  await antworte(page, 'Nein'); // 1a
  await expect(page.getByText('Schritt 2 von 6 — Datenschutz')).toBeVisible();
  // Solange der Durchlauf läuft, gibt es keinen Zwischenstand.
  await expect(page.getByTestId('tier')).toHaveCount(0);
  await antworte(page, 'Ja'); // 2a -> DS 3
  await expect(page.getByText('Schritt 3 von 6 — Mitbestimmung')).toBeVisible();
  await antworte(page, 'Ja'); // 3a -> MB 3
  await expect(page.getByText('Schritt 4 von 6 — IT-Sicherheit')).toBeVisible();
  await antworte(page, 'Nein');
  await antworte(page, 'Nein');
  await antworte(page, 'Ja'); // 4c -> IT 1
  await expect(page.getByText('Schritt 5 von 6 — Regulatorik')).toBeVisible();
  await antworte(page, 'Nein');
  await antworte(page, 'Ja'); // 5b -> RG 2
  await expect(page.getByText('Schritt 6 von 6 — Unternehmerisches Risiko')).toBeVisible();
  await antworte(page, 'Nein'); // 6a
  await antworte(page, 'Ja'); // 6b -> UR 2

  await expect(page.getByTestId('tier')).toHaveText('3');
  await expect(page.getByTestId('profil')).toHaveText('KI0-DS3-MB3-IT1-RG2-UR2');
  await expect(page.getByTestId('k-klassen')).toContainText('Mitbestimmungsverfahren einleiten');

  await page.getByTestId('bewertung-speichern').click();
  await expect(page.getByRole('heading', { name: 'Bewertungshistorie' })).toBeVisible();
  await expect(page.getByText('KI0-DS3-MB3-IT1-RG2-UR2')).toBeVisible();
});

vorgang('V-BEW-02', async ({ page, request }) => {
  // E-64: es gibt keine unvollständige Bewertung mehr. Der Wizard beginnt bei
  // der ersten Frage, und ein Tier-3-Treffer beendet ihn nicht — sonst
  // stünden am Ende Nullen in Dimensionen, die niemand gefragt hat, und keine
  // einzige Maßnahmenklasse.
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const { prozess } = await mitEntgeltdaten(request, org, marke);
  await anmelden(page);
  await starte(page, prozess.id);

  await antworte(page, 'Nein'); // 1a
  await antworte(page, 'Ja'); // 2a -> DS 3 …
  // … und es geht weiter: die Mitbestimmungsdimension kommt noch.
  await expect(page.getByTestId('frage')).toBeVisible();
  await expect(page.getByTestId('tier')).toHaveCount(0);
});

vorgang('V-BEW-03', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const { prozess } = await mitEntgeltdaten(request, org, marke, { ausfallfolge: 'kritisch' });
  await anmelden(page);
  await starte(page, prozess.id);

  // KI ist nach A.8.4 vollständig zu erklären — kein Vorschlag, keine Belege.
  await expect(page.getByTestId('frage')).toHaveAttribute('data-frage-id', '1a');
  await expect(page.getByTestId('vorschlag')).toHaveCount(0);
  await antworte(page, 'Nein');

  // Datenschutz: der Vorschlag nennt das Objekt, aus dem er stammt.
  const ds = page.getByTestId('vorschlag');
  await expect(ds).toHaveAttribute('data-wert', 'true');
  await expect(ds).toContainText(`Entgeltdaten ${marke}`);
  await expect(ds).toContainText('besondere Kategorie');
  await expect(ds).toContainText('Datenobjekt');
  await antworte(page, 'Ja');

  // Mitbestimmung: dieselbe Quelle, aber die Begründung aus A.5/A.7.
  await expect(page.getByTestId('vorschlag')).toContainText('Leistungsbewertung');
  await antworte(page, 'Ja');

  // IT-Sicherheit: ohne Telemetrie kein Vorschlag.
  await expect(page.getByTestId('frage')).toHaveAttribute('data-frage-id', '4a');
  await expect(page.getByTestId('vorschlag')).toHaveCount(0);
  await antworte(page, 'Nein');
  await antworte(page, 'Nein');
  await antworte(page, 'Nein');
  await antworte(page, 'Nein'); // 5a
  await antworte(page, 'Nein'); // 5b
  await antworte(page, 'Nein'); // 5c

  // Unternehmerisches Risiko: aus der eigenen Ausfallfolge, im Klartext.
  const ur = page.getByTestId('vorschlag');
  await expect(ur).toHaveAttribute('data-wert', 'true');
  await expect(ur).toContainText('Ausfallfolge');
  await expect(ur).toContainText('kritisch');
});

vorgang('V-BEW-04', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const { prozess } = await mitEntgeltdaten(request, org, marke);
  await anmelden(page);
  await starte(page, prozess.id);
  await antworte(page, 'Nein'); // 1a

  await expect(page.getByTestId('vorschlag')).toHaveAttribute('data-wert', 'true');
  await antworteAbweichend(page, 'Nein', 'Nur ein Aggregat ohne Einzelwerte eingebunden.');

  // Der Wizard rückt weiter — die Abweichung ist angenommen.
  await expect(page.getByTestId('frage')).toHaveAttribute('data-frage-id', '2b');

  // Den Rest im Einklang mit der Datenlage beantworten, damit nur die eine
  // Abweichung im Ergebnis steht.
  await antworte(page, 'Ja'); // 2b: Personenbezug, wie vorgeschlagen
  await antworte(page, 'Ja'); // 3a: Mitbestimmung, wie vorgeschlagen
  await antworte(page, 'Nein'); // 4a
  await antworte(page, 'Nein'); // 4b
  await antworte(page, 'Nein'); // 4c
  await antworte(page, 'Nein'); // 5a
  await antworte(page, 'Nein'); // 5b
  await antworte(page, 'Nein'); // 5c
  await antworte(page, 'Nein'); // 6a, Ausfallfolge „gering"
  await antworte(page, 'Nein'); // 6b
  await antworte(page, 'Ja'); // 6c, wie vorgeschlagen

  // Vorschlag und Antwort werden beide festgehalten.
  const [ruf] = await Promise.all([
    page.waitForResponse(
      (r) => r.url().endsWith('/bewertungen') && r.request().method() === 'POST',
    ),
    page.getByTestId('bewertung-speichern').click(),
  ]);
  const gespeichert = (await ruf.json()).bewertung;
  expect(gespeichert.vorschlaege['2a']).toBe(true);
  expect(gespeichert.antworten['2a']).toBe(false);
  expect(gespeichert.abweichungen['2a']).toContain('Aggregat');
});

vorgang('V-BEW-05', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const { prozess } = await mitEntgeltdaten(request, org, marke);
  await anmelden(page);
  await starte(page, prozess.id);
  await antworte(page, 'Nein'); // 1a

  await expect(page.getByTestId('vorschlag')).toHaveAttribute('data-wert', 'true');
  await page.getByRole('button', { name: 'Nein', exact: true }).click();

  // Der Schritt wird nicht angenommen: das Begründungsfeld hält an, „Weiter"
  // bleibt gesperrt, und die Frage steht unverändert da.
  await expect(page.getByTestId('begruendung')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Weiter' })).toBeDisabled();
  await expect(page.getByTestId('frage')).toHaveAttribute('data-frage-id', '2a');

  // Leerzeichen zählen nicht als Begründung.
  await page.getByLabel('Begründung der Abweichung').fill('   ');
  await expect(page.getByRole('button', { name: 'Weiter' })).toBeDisabled();

  // Auch die API weist den Schritt ab — die Sperre liegt nicht nur im Browser.
  const direkt = await request.post(`${API}/api/v1/prozesse/${prozess.id}/bewertung/wizard`, {
    headers: org.kopfzeilen,
    data: { modus: 'vollstaendig', antworten: { '1a': false, '2a': false }, begruendungen: {} },
  });
  expect(direkt.status()).toBe(422);
  expect(await direkt.text()).toContain('2a');
});

vorgang('V-BEW-06', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const { prozess } = await mitEntgeltdaten(request, org, marke);
  await anmelden(page);
  await starte(page, prozess.id);
  await antworte(page, 'Nein'); // 1a
  await antworte(page, 'Ja'); // 2a -> DS 3
  await antworte(page, 'Ja'); // 3a -> MB 3
  await antworte(page, 'Nein');
  await antworte(page, 'Nein');
  await antworte(page, 'Nein'); // IT 0
  await antworte(page, 'Nein');
  await antworte(page, 'Nein');
  await antworte(page, 'Nein'); // RG 0
  await antworte(page, 'Nein');
  await antworte(page, 'Nein');
  await antworte(page, 'Ja'); // 6c -> UR 1

  const klassen = page.getByTestId('k-klassen');
  // Namen und Erklärungssatz, nicht nur das Kürzel.
  await expect(klassen).toContainText('Datenschutz-Folgenabschätzung');
  await expect(klassen).toContainText('Art. 35');
  await expect(klassen).toContainText('Mitbestimmungsverfahren einleiten');
  await expect(klassen).toContainText('Betriebsrat');
  // Das Kürzel bleibt daneben stehen, damit die Auskunft anschlussfähig ist.
  await expect(klassen.getByRole('listitem').filter({ hasText: 'K4' })).toHaveCount(1);
});

vorgang('V-BEW-07', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const { prozess } = await mitEntgeltdaten(request, org, marke);
  await anmelden(page);
  await starte(page, prozess.id);
  await antworte(page, 'Nein'); // 1a
  await antworte(page, 'Ja'); // 2a -> DS 3 -> Tier 3
  await antworte(page, 'Ja'); // 3a
  await antworte(page, 'Nein');
  await antworte(page, 'Nein');
  await antworte(page, 'Nein');
  await antworte(page, 'Nein');
  await antworte(page, 'Nein');
  await antworte(page, 'Nein');
  await antworte(page, 'Nein');
  await antworte(page, 'Nein');
  await antworte(page, 'Ja'); // 6c

  const auflagen = page.getByTestId('auflagen');
  await expect(auflagen).toBeVisible();
  // Kumulativ: Tier 3 trägt auch die Auflagen von Tier 1 und 2.
  await expect(auflagen).toContainText('Registrierung im Verzeichnis der Prozessobjekte.');
  await expect(auflagen).toContainText('Zugriffs- und Rechtekonzept');
  await expect(auflagen).toContainText('Die Bewertung verfällt nach einem Jahr');
});

vorgang('V-BEW-08', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, { name: `KI-Vorhaben ${marke}` });
  await anmelden(page);
  await starte(page, prozess.id);

  await antworte(page, 'Ja'); // 1a: KI im Einsatz
  await page.getByRole('button', { name: 'Ja', exact: true }).click(); // 1b: verbotene Praxis

  // Eigener roter Ausgang, kein Ergebnis.
  const ausgang = page.getByTestId('verbotstatbestand');
  await expect(ausgang).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Verbotene KI-Praxis' })).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('EU AI Act');
  await expect(ausgang).toContainText('Governance und Recht');
  await expect(page.getByTestId('tier')).toHaveCount(0);
  await expect(page.getByTestId('bewertung-speichern')).toHaveCount(0);

  await page.getByTestId('alarm-ausloesen').click();
  // Keine gespeicherte Bewertung — das Prozessobjekt bleibt unbewertet.
  await expect(page.getByRole('heading', { name: 'Bewertungshistorie' })).toBeVisible();
  await expect(page.getByText('Für diesen Prozess liegt noch keine Bewertung vor.')).toBeVisible();
});

vorgang('V-BEW-09', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, { name: `Abbruch ${marke}` });
  await anmelden(page);
  await starte(page, prozess.id);
  await antworte(page, 'Nein'); // 1a

  await page.getByRole('button', { name: 'Bewertung abbrechen' }).click();
  // Vor dem Verwerfen wird zurückgefragt.
  const blatt = page.getByRole('dialog');
  await expect(blatt).toContainText('Bewertung verwerfen?');
  await expect(blatt).toContainText('Eine Antwort geht verloren.');

  // Weiterbewerten führt zurück in den Durchlauf, ohne etwas zu verlieren.
  await page.getByRole('button', { name: 'Weiterbewerten' }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByTestId('frage')).toBeVisible();

  await page.getByRole('button', { name: 'Bewertung abbrechen' }).click();
  await page.getByTestId('abbruch-verwerfen').click();
  await expect(page.getByRole('heading', { name: 'Bewertungshistorie' })).toBeVisible();
  await expect(page.getByText('Für diesen Prozess liegt noch keine Bewertung vor.')).toBeVisible();
});

vorgang('V-BEW-10', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const { prozess } = await mitEntgeltdaten(request, org, marke);
  await anmelden(page);
  await starte(page, prozess.id);
  await antworte(page, 'Nein'); // 1a
  await expect(page.getByTestId('frage')).toHaveAttribute('data-frage-id', '2a');

  await page.getByTestId('bewertung-zurueck').click();
  await expect(page.getByTestId('frage')).toHaveAttribute('data-frage-id', '1a');
  // Die vorige Antwort steht noch da.
  await expect(page.getByRole('button', { name: 'Nein', exact: true })).toHaveAttribute(
    'aria-pressed',
    'true',
  );

  // Und lässt sich ändern: jetzt doch KI im Einsatz.
  await antworte(page, 'Ja');
  await expect(page.getByTestId('frage')).toHaveAttribute('data-frage-id', '1b');
});

vorgang('V-BEW-11', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const { prozess } = await mitEntgeltdaten(request, org, marke);
  await anmelden(page);

  // Erste Bewertung: DS 3, und der Durchlauf geht bis zum Ende (E-64).
  await starte(page, prozess.id);
  await antworte(page, 'Nein');
  await antworte(page, 'Ja');
  await beendeDurchlauf(page);
  await page.getByTestId('bewertung-speichern').click();
  await expect(page.getByRole('heading', { name: 'Bewertungshistorie' })).toBeVisible();
  await expect(page.getByRole('row')).toHaveCount(2); // Kopf plus eine Bewertung

  // Neubewertung, diesmal vollständig und mit MB 3.
  await starte(page, prozess.id);
  await antworte(page, 'Nein');
  await antworte(page, 'Ja');
  await antworte(page, 'Ja'); // 3a -> MB 3
  await beendeDurchlauf(page);
  await page.getByTestId('bewertung-speichern').click();

  // Die alte Bewertung bleibt erhalten, die neue steht oben und ist maßgeblich.
  await expect(page.getByRole('heading', { name: 'Bewertungshistorie' })).toBeVisible();
  await expect(page.getByRole('row')).toHaveCount(3);
  const massgeblich = page.getByTestId('bewertung-massgeblich');
  await expect(massgeblich).toContainText('Maßgeblich');
  await expect(massgeblich).toContainText('MB3');
});

vorgang('V-BEW-12', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const { prozess } = await mitEntgeltdaten(request, org, marke);
  await anmelden(page);

  await starte(page, prozess.id);
  await antworte(page, 'Nein');
  await antworte(page, 'Ja');
  await beendeDurchlauf(page);
  await page.getByTestId('bewertung-speichern').click();

  await expect(page.getByRole('heading', { name: 'Bewertungshistorie' })).toBeVisible();
  const zeile = page.getByTestId('bewertung-massgeblich');
  // Jede Version ist mit Datum und vollständigem Profil nachvollziehbar.
  await expect(zeile).toContainText(new Date().toISOString().slice(0, 10));
  await expect(zeile).toContainText('KI0-DS3');
  await expect(zeile).toContainText('Tier 3');
});
