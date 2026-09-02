/**
 * V-PRO — Prozessobjekt.
 *
 * Der Prozess ist der Anker des Modells (Leitdokument A.4): alles andere hängt
 * an ihm. Entsprechend viele Handgriffe.
 */

import { expect, type Page } from '@playwright/test';

import {
  anmelden,
  bewerten,
  datenobjektAnlegen,
  kennzeichen,
  organisation,
  prozessAnlegen,
  vorgang,
  suchen,
  waehle,
} from './hilfen';

/** Das Formular mit den Pflichtangaben füllen — der gemeinsame Anfang. */
async function pflichtangaben(seite: Page, name: string, fachbereich: string) {
  await seite.getByLabel('Name').fill(name);
  await seite.getByLabel('Prozess-Owner').selectOption({ label: 'Vorgangs-Administrator' });
  await seite.getByLabel('Stellvertretung').selectOption({ label: 'Vorgangs-Administrator' });
  await seite
    .getByLabel('Prozessgeber (INT)')
    .selectOption({ label: `${fachbereich} — INT` });
}

async function neuerProzess(seite: Page) {
  await seite.goto('/de/prozesse');
  await seite.getByRole('link', { name: 'Prozessobjekt anlegen' }).first().click();
  await expect(seite.getByRole('heading', { name: 'Prozessobjekt anlegen' })).toBeVisible();
}

vorgang('V-PRO-01', async ({ page, request }) => {
  const org = await organisation(request);
  const name = `Rechnungspruefung ${kennzeichen()}`;
  await anmelden(page);
  await neuerProzess(page);
  await pflichtangaben(page, name, org.fachbereichName);
  await page.getByRole('button', { name: 'Speichern' }).click();

  await expect(page.getByRole('heading', { name })).toBeVisible();
  await expect(page.getByText('Entwurf').first()).toBeVisible();

  await page.goto('/de/prozesse');
  await expect(page.getByRole('link', { name: new RegExp(name) })).toBeVisible();
});

vorgang('V-PRO-02', async ({ page, request }) => {
  await organisation(request);
  await anmelden(page);
  await neuerProzess(page);
  await page.getByLabel('Name').fill(`Ohne Vertretung ${kennzeichen()}`);
  await page.getByRole('button', { name: 'Speichern' }).click();

  // Das Formular bleibt stehen und zeigt, woran es liegt.
  await expect(page.getByRole('heading', { name: 'Prozessobjekt anlegen' })).toBeVisible();
  await expect(page.getByLabel('Stellvertretung')).toBeFocused();
  await expect(page.getByText('Ohne Stellvertretung kann nicht gespeichert werden.')).toBeVisible();
});

vorgang('V-PRO-03', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const objekt = await datenobjektAnlegen(request, {
    name: `Kreditorenstamm ${marke}`,
    kategorie: 'besondere_kategorie',
    fachbereich_id: org.fachbereichId,
  });
  await anmelden(page);
  await neuerProzess(page);
  await pflichtangaben(page, `Mit Input ${marke}`, org.fachbereichName);

  // Der Treffer zeigt seine Einstufung, bevor gewählt wird (Leitdokument P5).
  const waehler = await suchen(page, 'waehler-input', objekt.name);
  await expect(
    waehler.getByRole('option').filter({ hasText: objekt.name }),
  ).toContainText('Personenbezogen — besonders');
  await waehler.getByRole('button', { name: new RegExp(objekt.name) }).click();
  await expect(waehler.locator('.k-chip')).toContainText(objekt.name);

  await page.getByRole('button', { name: 'Speichern' }).click();
  await expect(page.getByText(objekt.name)).toBeVisible();
});

vorgang('V-PRO-04', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const ein = await datenobjektAnlegen(request, {
    name: `Rohdaten ${marke}`,
    kategorie: 'intern',
    fachbereich_id: org.fachbereichId,
  });
  const aus = await datenobjektAnlegen(request, {
    name: `Bericht ${marke}`,
    kategorie: 'intern',
    fachbereich_id: org.fachbereichId,
  });
  await anmelden(page);
  await neuerProzess(page);
  await pflichtangaben(page, `Mit Output ${marke}`, org.fachbereichName);
  await waehle(page, 'waehler-input', ein.name);
  await waehle(page, 'waehler-output', aus.name);
  await page.getByRole('button', { name: 'Speichern' }).click();

  // Input und Output stehen getrennt — sonst wäre die Richtung verloren.
  const eingang = page.locator('.k-zeile', { hasText: 'Input — Datenobjekte' });
  const ausgang = page.locator('.k-zeile', { hasText: 'Output — Datenobjekte' });
  await expect(eingang).toContainText(ein.name);
  await expect(eingang).not.toContainText(aus.name);
  await expect(ausgang).toContainText(aus.name);
});

vorgang('V-PRO-05', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const zuliefer = await prozessAnlegen(request, org, { name: `Zulieferer ${marke}` });
  await anmelden(page);
  await neuerProzess(page);
  await pflichtangaben(page, `Empfaenger ${marke}`, org.fachbereichName);
  await waehle(page, 'waehler-vorgelagert', zuliefer.name);
  await page.getByRole('button', { name: 'Speichern' }).click();
  await expect(page.getByText(zuliefer.name).first()).toBeVisible();

  // Dieselbe Kante, von der anderen Seite gelesen — einmal erfasst.
  await page.goto(`/de/prozesse/${zuliefer.id}`);
  await expect(page.getByTestId('wirkung-abwaerts')).toContainText(`Empfaenger ${marke}`);
});

vorgang('V-PRO-06', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  await anmelden(page);
  await neuerProzess(page);
  await pflichtangaben(page, `Externer Zulauf ${marke}`, org.fachbereichName);
  await page.getByLabel('Lieferant').fill('Externes Rechenzentrum');
  await page.getByRole('button', { name: 'Speichern' }).click();

  await expect(
    page.locator('.k-zeile', { hasText: 'Lieferant' }),
  ).toContainText('Externes Rechenzentrum');
});

vorgang('V-PRO-07', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const folge = await prozessAnlegen(request, org, { name: `Nachfolger ${marke}` });
  await anmelden(page);
  await neuerProzess(page);
  await pflichtangaben(page, `Vorgaenger ${marke}`, org.fachbereichName);
  await waehle(page, 'waehler-nachgelagert', folge.name);
  await page.getByRole('button', { name: 'Speichern' }).click();

  await expect(page.getByTestId('wirkung-abwaerts')).toContainText(folge.name);
});

vorgang('V-PRO-08', async ({ page, request }) => {
  const org = await organisation(request);
  await anmelden(page);
  await neuerProzess(page);
  await pflichtangaben(page, `Zu tief ${kennzeichen()}`, org.fachbereichName);
  await page
    .getByLabel('Prozessschritte')
    .fill(['eins', 'zwei', 'drei', 'vier', 'fuenf', 'sechs', 'sieben', 'acht'].join('\n'));

  await expect(page.getByText(/Mehr als sieben Schritte/)).toBeVisible();
  // Die Warnung führt, sie verbietet nicht.
  await page.getByRole('button', { name: 'Speichern' }).click();
  await expect(page.getByRole('heading', { name: /Zu tief/ })).toBeVisible();
});

vorgang('V-PRO-09', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const a = await prozessAnlegen(request, org, { name: `Kreis A ${marke}` });
  const b = await prozessAnlegen(request, org, {
    name: `Kreis B ${marke}`,
    vorgelagert_ids: [a.id],
  });
  await anmelden(page);

  // A soll B nachgelagert werden — damit schlösse sich der Kreis.
  await page.goto(`/de/prozesse/${a.id}/bearbeiten`);
  await waehle(page, 'waehler-vorgelagert', b.name);
  await page.getByRole('button', { name: 'Speichern' }).click();

  await expect(page.getByRole('alert')).toContainText(/Kreis in der Prozesskette/);
});

vorgang('V-PRO-10', async ({ page, request }) => {
  const org = await organisation(request);
  await anmelden(page);
  await neuerProzess(page);
  await pflichtangaben(page, `Reichweite ${kennzeichen()}`, org.fachbereichName);
  await page.getByLabel('Kundenkreis').selectOption('unternehmen');
  await page.getByRole('button', { name: 'Speichern' }).click();

  const reichweite = page.getByTestId('reichweite');
  await expect(reichweite).toContainText('Unternehmen');
  await expect(reichweite).toContainText('Aus dem Kundenkreis');
  // Abgeleitet heißt: nicht eingebbar (Leitdokument P1).
  await expect(page.getByLabel('Reichweite')).toHaveCount(0);
});

vorgang('V-PRO-11', async ({ page, request }) => {
  const org = await organisation(request);
  await anmelden(page);
  await neuerProzess(page);
  await pflichtangaben(page, `Kritikalitaet ${kennzeichen()}`, org.fachbereichName);
  await page.getByLabel('Ausfallfolge').selectOption('kritisch');
  await page.getByRole('button', { name: 'Speichern' }).click();

  const kritikalitaet = page.getByTestId('kritikalitaet');
  await expect(kritikalitaet).toContainText('3');
  await expect(kritikalitaet).toContainText('Aus der eigenen Ausfallfolge');
});

vorgang('V-PRO-12', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const kritisch = await prozessAnlegen(request, org, {
    name: `Kritischer Nachfolger ${marke}`,
    ausfallfolge: 'kritisch',
  });
  const eigener = await prozessAnlegen(request, org, {
    name: `Harmlos ${marke}`,
    ausfallfolge: 'keine',
  });
  await anmelden(page);
  await page.goto(`/de/prozesse/${eigener.id}`);
  await expect(page.getByTestId('kritikalitaet')).toContainText('0');

  await page.goto(`/de/prozesse/${eigener.id}/bearbeiten`);
  await waehle(page, 'waehler-nachgelagert', kritisch.name);
  await page.getByRole('button', { name: 'Speichern' }).click();

  // Wer einen kritischen Nachfolger speist, ist selbst so kritisch (A.4.2).
  const kritikalitaet = page.getByTestId('kritikalitaet');
  await expect(kritikalitaet).toContainText('3');
  await expect(kritikalitaet).toContainText('Aus der Prozesskette geerbt');
});

vorgang('V-PRO-13', async ({ page, request }) => {
  const org = await organisation(request);
  await anmelden(page);
  await neuerProzess(page);
  await pflichtangaben(page, `Zwei Laender ${kennzeichen()}`, org.fachbereichName);
  await page.getByLabel('Kundenkreis').selectOption('bereich');
  await page.getByLabel(`${org.fachbereichName} — Land DE`, { exact: true }).check();
  await page.getByLabel(`${org.fachbereichName} — Land FR`, { exact: true }).check();
  await page.getByRole('button', { name: 'Speichern' }).click();

  await expect(page.getByTestId('reichweite')).toContainText('Unternehmen');
  await expect(page.getByText(`${org.fachbereichName} — Land DE`)).toBeVisible();
  await expect(page.getByText(`${org.fachbereichName} — Land FR`)).toBeVisible();
});

vorgang('V-PRO-14', async ({ page, request }) => {
  const org = await organisation(request);
  await anmelden(page);
  await neuerProzess(page);
  await pflichtangaben(page, `Mit Abweichung ${kennzeichen()}`, org.fachbereichName);
  await page.getByLabel(`${org.fachbereichName} — Land FR`, { exact: true }).check();
  await page
    .getByLabel(`Lokale Abweichung — ${org.fachbereichName} — Land FR`)
    .fill('Freigabe durch zwei Personen');
  await page.getByRole('button', { name: 'Speichern' }).click();

  // Die Abweichung steht an der Umsetzung, nicht am Prozess.
  await expect(
    page.locator('.k-zeile', { hasText: `${org.fachbereichName} — Land FR` }),
  ).toContainText('Freigabe durch zwei Personen');
});

vorgang('V-PRO-15', async ({ page, request }) => {
  const org = await organisation(request);
  const prozess = await prozessAnlegen(request, org, {
    name: `Rueckbau ${kennzeichen()}`,
    customer: 'bereich',
    umsetzung_land_org_ids: [org.deId, org.frId],
  });
  await anmelden(page);
  await page.goto(`/de/prozesse/${prozess.id}`);
  await expect(page.getByTestId('reichweite')).toContainText('Unternehmen');

  await page.goto(`/de/prozesse/${prozess.id}/bearbeiten`);
  await page.getByLabel(`${org.fachbereichName} — Land FR`, { exact: true }).uncheck();
  await page.getByRole('button', { name: 'Speichern' }).click();

  // Eine Umsetzung weniger: die Reichweite fällt auf den Kundenkreis zurück.
  await expect(page.getByTestId('reichweite')).toContainText('Fachbereich');
});

vorgang('V-PRO-16', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const objekt = await datenobjektAnlegen(request, {
    name: `Stammdaten ${marke}`,
    kategorie: 'intern',
    fachbereich_id: org.fachbereichId,
  });
  const prozess = await prozessAnlegen(request, org, {
    name: `Zu bearbeiten ${marke}`,
    input_datenobjekt_ids: [objekt.id],
  });
  await anmelden(page);
  await page.goto(`/de/prozesse/${prozess.id}/bearbeiten`);

  // Alles ist vorbelegt — auch die Referenzen.
  await expect(page.getByLabel('Name')).toHaveValue(prozess.name);
  await expect(page.getByTestId('waehler-input').locator('.k-chip')).toContainText(objekt.name);

  await page.getByLabel('Ergebnis').fill('Geprüfte Rechnung');
  await page.getByRole('button', { name: 'Speichern' }).click();

  await expect(page.locator('.k-zeile', { hasText: 'Ergebnis' })).toContainText(
    'Geprüfte Rechnung',
  );
  // Was nicht angefasst wurde, bleibt stehen.
  await expect(page.getByText(objekt.name).first()).toBeVisible();
});

vorgang('V-PRO-17', async ({ page, request }) => {
  const org = await organisation(request);
  const prozess = await prozessAnlegen(request, org, { name: `Ohne Bewertung ${kennzeichen()}` });
  await anmelden(page);
  await page.goto(`/de/prozesse/${prozess.id}`);
  await page.getByRole('button', { name: 'Aktivieren' }).click();

  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.getByText('Entwurf').first()).toBeVisible();
});

vorgang('V-PRO-18', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const prozess = await prozessAnlegen(request, org, { name: `Stilllegen ${marke}` });
  // Vorbedingung: ohne Bewertung gibt es keine Aktivierung (V-PRO-17).
  await bewerten(request, prozess.id);
  await anmelden(page);
  await page.goto(`/de/prozesse/${prozess.id}`);
  await page.getByRole('button', { name: 'Aktivieren' }).click();
  await expect(page.getByText('Aktiv').first()).toBeVisible();

  await page.getByRole('button', { name: 'Stilllegen' }).click();
  await expect(page.getByText('Stillgelegt').first()).toBeVisible();
});

vorgang('V-PRO-19', async ({ page, request }) => {
  const org = await organisation(request);
  const prozess = await prozessAnlegen(request, org, { name: `Wiederaufnahme ${kennzeichen()}` });
  await bewerten(request, prozess.id);
  await anmelden(page);
  await page.goto(`/de/prozesse/${prozess.id}`);
  await page.getByRole('button', { name: 'Aktivieren' }).click();
  await page.getByRole('button', { name: 'Stilllegen' }).click();
  await expect(page.getByText('Stillgelegt').first()).toBeVisible();

  // Die Bewertung gilt weiter, also führt derselbe Weg zurück in den Betrieb.
  await page.getByRole('button', { name: 'Aktivieren' }).click();
  await expect(page.getByText('Aktiv').first()).toBeVisible();
});

vorgang('V-PRO-20', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const vor = await prozessAnlegen(request, org, { name: `Zulauf ${marke}` });
  const nach = await prozessAnlegen(request, org, { name: `Ablauf ${marke}` });
  const mitte = await prozessAnlegen(request, org, {
    name: `Mitte ${marke}`,
    vorgelagert_ids: [vor.id],
    nachgelagert_ids: [nach.id],
  });
  await anmelden(page);
  await page.goto(`/de/prozesse/${mitte.id}`);

  await expect(page.getByTestId('wirkung-abwaerts')).toContainText(nach.name);
  await expect(page.getByTestId('wirkung-aufwaerts')).toContainText(vor.name);
});

vorgang('V-PRO-21', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  await prozessAnlegen(request, org, { name: `Suchbar ${marke}` });
  await prozessAnlegen(request, org, { name: `Unsichtbar ${marke}` });
  await anmelden(page);
  await page.goto('/de/prozesse');

  await page.getByRole('searchbox', { name: 'Name' }).fill(`Suchbar ${marke}`);
  await expect(page.getByRole('link', { name: new RegExp(`Suchbar ${marke}`) })).toBeVisible();
  await expect(page.getByRole('link', { name: new RegExp(`Unsichtbar ${marke}`) })).toHaveCount(0);
});

vorgang('V-PRO-22', async ({ page, request }) => {
  const org = await organisation(request);
  const fremd = await prozessAnlegen(request, org, { name: `Fremd ${kennzeichen()}` });

  // Ein Anwender ohne jede Rolle: er darf ihn weder finden noch aufrufen.
  await anmelden(page, `gast-${kennzeichen()}`, 'Gast ohne Rolle');
  await expect(page.getByRole('link', { name: new RegExp(fremd.name) })).toHaveCount(0);

  await page.goto(`/de/prozesse/${fremd.id}`);
  await expect(page.getByRole('heading', { name: fremd.name })).toHaveCount(0);
  await expect(page.getByRole('alert')).toBeVisible();
});

vorgang('V-PRO-23', async ({ page, request }) => {
  const org = await organisation(request);
  const marke = kennzeichen();
  const prozess = await prozessAnlegen(request, org, { name: `Mit Zielen ${marke}` });
  await bewerten(request, prozess.id);
  await anmelden(page);

  // Der Prozess ist aktiv — erst dann gibt es einen Rahmen, den ein neues
  // Ziel verlassen könnte (Leitdokument A.11).
  await page.goto(`/de/prozesse/${prozess.id}`);
  await page.getByRole('button', { name: 'Aktivieren' }).click();
  await expect(page.locator('.k-seitenkopf .k-abzeichen').first()).toHaveText('Aktiv');

  await page.goto(`/de/prozesse/${prozess.id}/bearbeiten`);
  await expect(page.getByText('Für diesen Prozess ist kein externes Ziel erklärt.')).toBeVisible();
  await expect(page.getByText(/löst ein neues Ziel Gate 2 aus/)).toBeVisible();
  await page.getByLabel('Ziel ergänzen').fill('sftp.partner.example');
  await page.getByTestId('ziel-hinzufuegen').click();
  await page.getByRole('button', { name: 'Speichern' }).click();

  // Das Ziel steht als Rahmen am Prozess …
  await expect(page.getByRole('heading', { name: prozess.name })).toBeVisible();
  await page.goto(`/de/prozesse/${prozess.id}/bearbeiten`);
  await expect(page.getByTestId('ziel-sftp.partner.example')).toBeVisible();

  // … und Gate 2 ist von selbst entstanden, mit seinem Auslöser im Klartext.
  await page.goto(`/de/prozesse/${prozess.id}`);
  const zeile = page.locator('.k-zeile[data-testid^="gate-"]');
  await expect(zeile).toContainText('Gate 2');
  await expect(zeile).toContainText('Neues externes Ziel');
  await expect(zeile).toContainText('sftp.partner.example');
});
