/**
 * V-RAH — Erlaubnisrahmen und Lenkung.
 *
 * Der Rahmen nach A.13.2 und der Lenkungsvorgang nach A.13.5 mit
 * Arbeitstagfristen und den drei gleichrangigen Auflösungswegen.
 *
 * Zwei Vorgänge greifen auf Zeit zu, die nicht vergeht: eine abgelaufene Frist
 * (V-RAH-05) und ein Tier-1-Fall über sechs Wochen (V-RAH-04). Beide arbeiten
 * deshalb über die **echte** Konfiguration, nicht über einen Testeinstieg — und
 * stellen sie unmittelbar nach der Beobachtung zurück, damit ein
 * fehlgeschlagener Lauf dem nächsten keine Nullfrist hinterlässt.
 */

import { expect, type APIRequestContext, type Page } from '@playwright/test';

import {
  API,
  anmelden,
  anwenderMitRolle,
  bewerten,
  geplanterLauf,
  kennzeichen,
  kopf,
  organisation,
  prozessAnlegen,
  toolAnlegen,
  toolMitProzess,
  vorgang,
} from './hilfen';

/** Eine Governance-Einstellung setzen und den vorherigen Wert zurückgeben. */
async function einstellen(
  anfrage: APIRequestContext,
  schluessel: string,
  wert: string,
): Promise<string> {
  const h = await kopf(anfrage);
  const liste = await (await anfrage.get(`${API}/api/v1/konfiguration`, { headers: h })).json();
  const vorher = (liste as { schluessel: string; wert: string }[]).find(
    (e) => e.schluessel === schluessel,
  );
  const antwort = await anfrage.put(`${API}/api/v1/konfiguration/${schluessel}`, {
    headers: h,
    data: { wert },
  });
  if (antwort.status() >= 400) throw new Error(`Konfiguration: ${await antwort.text()}`);
  return vorher?.wert ?? '';
}

/** Ein bewertetes Tool-Objekt an einem Prozess — die Ausgangslage jedes Vorgangs. */
async function aufbau(
  anfrage: APIRequestContext,
  marke: string,
  { hoch = true }: { hoch?: boolean } = {},
) {
  const org = await organisation(anfrage, marke);
  const prozess = await prozessAnlegen(anfrage, org, { name: `Rahmen ${marke}` });
  await bewerten(anfrage, prozess.id, hoch);
  const tool = await toolAnlegen(anfrage, {
    name: `Werkzeug ${marke}`,
    organisationseinheit_id: org.deId,
  });
  await toolMitProzess(anfrage, tool.id, prozess.id);
  return { org, prozess, tool };
}

/** Einen roten Zustand über die Oberfläche melden. */
async function melden(seite: Page, toolId: string, begruendung: string, verbot?: string) {
  await seite.goto(`/de/tools/${toolId}`);
  await seite.getByLabel('Zustand melden').selectOption('rot');
  if (verbot !== undefined) await seite.getByLabel('Verstoß gegen Schicht 2').selectOption(verbot);
  await seite.getByLabel('Begründung').fill(begruendung);
  await seite.getByRole('button', { name: 'Zustand melden' }).click();
  await expect(seite.getByTestId('aktueller-zustand')).toContainText(begruendung);
}

vorgang('V-RAH-01', async ({ page, request }) => {
  const marke = kennzeichen();
  const { tool } = await aufbau(request, marke);
  await anmelden(page);

  await page.goto(`/de/tools/${tool.id}`);
  // Alle sieben Elemente aus Schicht 1 — vorher waren es drei.
  for (const element of [
    'datenobjekte',
    'datenkategorie',
    'reichweite',
    'externe_ziele',
    'zugriffsart',
    'ausfuehrungsart',
    'ausfuehrungsidentitaet',
  ]) {
    await expect(page.getByTestId(`rahmen-${element}`)).toBeVisible();
  }
  // Erlaubt und gemessen stehen nebeneinander, mit Namen statt Schlüsseln.
  await expect(page.getByTestId('erlaubt-reichweite')).toHaveText('Fachbereich');
  await expect(page.getByTestId('gemessen-reichweite')).toHaveText('Nicht gemessen — abgeleitet');
});

vorgang('V-RAH-02', async ({ page, request }) => {
  const marke = kennzeichen();
  const { tool } = await aufbau(request, marke);
  await anmelden(page);

  await melden(page, tool.id, 'Schreibt in ein nicht freigegebenes Datenobjekt');

  await page.goto('/de/lenkung');
  const karte = page.locator('.k-karte').filter({ hasText: `Werkzeug ${marke}` });
  await expect(karte.getByText('Stufe 1')).toBeVisible();
  await expect(karte.locator('.k-countdown')).toBeVisible();
});

vorgang('V-RAH-03', async ({ page, request }) => {
  const marke = kennzeichen();
  const { tool } = await aufbau(request, marke);
  await anmelden(page);

  // Vor der Meldung steht auf dem Bildschirm, was folgt.
  await page.goto(`/de/tools/${tool.id}`);
  await page.getByLabel('Zustand melden').selectOption('rot');
  await page.getByLabel('Verstoß gegen Schicht 2').selectOption('identitaet_umgangen');
  await expect(page.getByText(/unmittelbar in Eskalationsstufe 2/)).toBeVisible();
  await page.getByLabel('Begründung').fill('Läuft unter einem geteilten Konto');
  await page.getByRole('button', { name: 'Zustand melden' }).click();

  await page.goto('/de/lenkung');
  const karte = page.locator('.k-karte').filter({ hasText: `Werkzeug ${marke}` });
  await expect(karte.getByText('Stufe 2')).toBeVisible();
  await expect(karte).toContainText('Ausführung unter umgangener Unternehmensidentität');
  await expect(karte).toContainText('ohne erste Stufe');
});

vorgang('V-RAH-04', async ({ page, request }) => {
  const marke = kennzeichen();
  // Tier 1 statt Tier 3: 30 Arbeitstage statt 5 (Leitdokument A.13.5).
  const { tool } = await aufbau(request, marke, { hoch: false });
  await anmelden(page);

  await melden(page, tool.id, 'Rahmen verlassen');

  await page.goto('/de/lenkung');
  const karte = page.locator('.k-karte').filter({ hasText: `Werkzeug ${marke}` });
  await expect(karte.locator('.k-countdown .zahl')).toHaveText('30');
  await expect(karte.locator('.k-countdown .einheit')).toHaveText('Arbeitstage verbleiben');

  // Das Fristdatum liegt echte sechs Wochen entfernt: 30 Arbeitstage sind
  // sechs Wochen, weil die Wochenenden übersprungen werden.
  const datum = await karte.locator('.k-countdown .datum').innerText();
  const frist = new Date(datum.replace('Frist ', ''));
  expect(frist.getDay()).toBeGreaterThan(0);
  expect(frist.getDay()).toBeLessThan(6);
  expect(Math.round((frist.getTime() - Date.now()) / 86_400_000)).toBeGreaterThanOrEqual(39);
});

vorgang('V-RAH-05', async ({ page, request }) => {
  const marke = kennzeichen();
  const { tool } = await aufbau(request, marke);
  await anmelden(page);

  // Eine Frist, die schon abgelaufen ist, gibt es nur über eine Frist von
  // null Tagen. Sie wird sofort nach dem Melden zurückgesetzt.
  const vorher = await einstellen(request, 'lenkung_frist_tage_tier3', '0');
  try {
    await melden(page, tool.id, 'Frist läuft sofort ab');
  } finally {
    await einstellen(request, 'lenkung_frist_tage_tier3', vorher);
  }

  await page.goto('/de/lenkung');
  const karte = page.locator('.k-karte').filter({ hasText: `Werkzeug ${marke}` });
  await expect(karte.locator('.k-countdown .zahl')).toHaveText('Abgelaufen');

  // Der geplante Lauf rückt den Vorgang in die nächste Stufe — derselbe
  // Befehl, den im Betrieb der Zeitplan ausführt.
  geplanterLauf('eskalationen');

  await page.reload();
  await expect(
    page
      .locator('.k-karte')
      .filter({ hasText: `Werkzeug ${marke}` })
      .getByText('Stufe 2'),
  ).toBeVisible();
});

vorgang('V-RAH-06', async ({ page, request }) => {
  const marke = kennzeichen();
  const { tool } = await aufbau(request, marke);
  await anmelden(page);
  await melden(page, tool.id, 'Rahmen verlassen');

  await page.goto('/de/lenkung');
  const karte = page.locator('.k-karte').filter({ hasText: `Werkzeug ${marke}` });
  await karte.getByRole('button', { name: 'Anpassen' }).click();
  await page.getByLabel('Kommentar').fill('Schreibzugriff entfernt');
  await page.getByTestId('aufloesen').click();

  // Der Vorgang ist aus dem Vorrat verschwunden und das Tool wieder grün.
  await expect(page.locator('.k-karte').filter({ hasText: `Werkzeug ${marke}` })).toHaveCount(0);
  await page.goto(`/de/tools/${tool.id}`);
  await expect(page.getByTestId('aktueller-zustand')).toContainText('Grün');
});

vorgang('V-RAH-07', async ({ page, request }) => {
  const marke = kennzeichen();
  const { prozess, tool } = await aufbau(request, marke);
  await anmelden(page);
  await melden(page, tool.id, 'Rahmen zu eng');

  await page.goto('/de/lenkung');
  const karte = page.locator('.k-karte').filter({ hasText: `Werkzeug ${marke}` });
  await karte.getByRole('button', { name: 'Rahmen erweitern' }).click();

  // Ohne neue Bewertung schließt der Vorgang nicht — und die Oberfläche
  // bietet gar nichts an, statt eine Ablehnung abzuwarten.
  await expect(page.getByText(/keine neue Bewertung/)).toBeVisible();
  await expect(page.getByTestId('aufloesen')).toHaveCount(0);
  await page.keyboard.press('Escape');

  // Neu bewerten, dann steht die Bewertung zur Wahl.
  await bewerten(request, prozess.id, true);
  await page.reload();
  await page
    .locator('.k-karte')
    .filter({ hasText: `Werkzeug ${marke}` })
    .getByRole('button', { name: 'Rahmen erweitern' })
    .click();
  await page.locator('[data-testid^="bewertung-"]').first().click();
  await expect(page.locator('.k-karte').filter({ hasText: `Werkzeug ${marke}` })).toHaveCount(0);
});

vorgang('V-RAH-08', async ({ page, request }) => {
  const marke = kennzeichen();
  const { tool } = await aufbau(request, marke);
  await anmelden(page);
  await melden(page, tool.id, 'Nicht mehr im Rahmen zu betreiben');

  await page.goto('/de/lenkung');
  const karte = page.locator('.k-karte').filter({ hasText: `Werkzeug ${marke}` });
  await karte.getByRole('button', { name: 'Stilllegen' }).click();
  // Stilllegen ist keine Rückkehr in den Rahmen — das steht vor dem Klick da.
  await expect(page.getByText(/Das ist keine Rückkehr in den Rahmen/)).toBeVisible();
  await page.getByTestId('aufloesen').click();

  await page.goto(`/de/tools/${tool.id}`);
  await expect(page.getByTestId('status')).toContainText('Inaktiv');
  // Der Zustand bleibt rot: ein stillgelegtes Tool ist nicht „wieder konform".
  await expect(page.getByTestId('aktueller-zustand')).toContainText('Rot');
});

vorgang('V-RAH-09', async ({ page, request }) => {
  const marke = kennzeichen();
  const { tool } = await aufbau(request, marke);
  await anmelden(page);
  await melden(page, tool.id, 'Rahmen verlassen');

  await page.goto('/de/lenkung');
  const countdown = page
    .locator('.k-karte')
    .filter({ hasText: `Werkzeug ${marke}` })
    .locator('.k-countdown');
  // Tier 3: fünf Arbeitstage, ohne Rechnen ablesbar — Zahl, Einheit, Datum.
  await expect(countdown.locator('.zahl')).toHaveText('5');
  await expect(countdown.locator('.einheit')).toHaveText('Arbeitstage verbleiben');
  await expect(countdown.locator('.datum')).toContainText('Frist ');
});

vorgang('V-RAH-10', async ({ page, request }) => {
  const marke = kennzeichen();
  const { tool } = await aufbau(request, marke);
  const govId = await anwenderMitRolle(
    request,
    `gov-${marke}`,
    `Governance ${marke}`,
    'governance',
    'global',
  );
  expect(govId).toBeTruthy();
  await anmelden(page, `gov-${marke}`, `Governance ${marke}`);

  // Ein Vorgang mit der geltenden Frist, bevor die Einstellung sich ändert.
  await melden(page, tool.id, 'Vor der Änderung eröffnet');
  await page.goto('/de/lenkung');
  const vorher = await page
    .locator('.k-karte')
    .filter({ hasText: `Werkzeug ${marke}` })
    .locator('.k-countdown .datum')
    .innerText();

  await page.goto('/de/konfiguration');
  await expect(
    page.getByText(/Eine Änderung wirkt auf neue Vorgänge, nicht rückwirkend/),
  ).toBeVisible();
  const zeile = page.getByTestId('einstellung-lenkung_frist_tage_tier3');
  await zeile.getByLabel('Stufe 1 bei Tier 3').fill('12');
  await page.getByTestId('sichern-lenkung_frist_tage_tier3').click();
  await expect(page.getByTestId('sichern-lenkung_frist_tage_tier3')).toHaveText('Gesichert');

  try {
    // Der laufende Vorgang behält seine Frist — sie wurde bei der Eröffnung
    // gerechnet und gespeichert.
    await page.goto('/de/lenkung');
    await expect(
      page
        .locator('.k-karte')
        .filter({ hasText: `Werkzeug ${marke}` })
        .locator('.k-countdown .datum'),
    ).toHaveText(vorher);

    // Ein neuer Vorgang bekommt die neue Frist.
    const zweite = kennzeichen();
    const spaeter = await aufbau(request, zweite);
    await melden(page, spaeter.tool.id, 'Nach der Änderung eröffnet');
    await page.goto('/de/lenkung');
    await expect(
      page
        .locator('.k-karte')
        .filter({ hasText: `Werkzeug ${zweite}` })
        .locator('.k-countdown .zahl'),
    ).toHaveText('12');
  } finally {
    await einstellen(request, 'lenkung_frist_tage_tier3', '5');
  }
});
