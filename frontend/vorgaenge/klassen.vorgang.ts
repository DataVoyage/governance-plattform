/**
 * V-KLA — Anforderungsklassen und Technologiematrix.
 *
 * Die zweite Übersetzungsstufe aus A.9.1: vom ausgelösten K-Code zu einer
 * Entscheidung über die eingesetzte Technologie.
 *
 * V-KLA-03 ändert die Matrix, und die gilt organisationsweit. Der Vorgang
 * stellt das Feld unmittelbar nach der Beobachtung zurück — ein Durchlauf, der
 * auf halbem Weg scheitert, darf den folgenden keinen Ausschluss hinterlassen
 * (siehe `docs/entscheidungen.md`, E-35).
 */

import { expect, type APIRequestContext, type Page } from '@playwright/test';

import {
  API,
  anmelden,
  anwenderMitRolle,
  bewerten,
  kennzeichen,
  kopf,
  organisation,
  prozessAnlegen,
  toolAnlegen,
  toolMitProzess,
  vorgang,
} from './hilfen';

/** Ein Tier-3-Prozess mit einem Tool bestimmter Technologie. */
async function aufbau(anfrage: APIRequestContext, marke: string, technologie: string | null) {
  const org = await organisation(anfrage, marke);
  const prozess = await prozessAnlegen(anfrage, org, { name: `Klassenprozess ${marke}` });
  // `2a` bejaht ergibt DS 3 — und damit K4 und K5.
  await bewerten(anfrage, prozess.id, true);
  const tool = await toolAnlegen(anfrage, {
    name: `Werkzeug ${marke}`,
    technologie,
    organisationseinheit_id: org.deId,
  });
  await toolMitProzess(anfrage, tool.id, prozess.id);
  return { org, prozess, tool };
}

/** Ein Matrixfeld über die API setzen; liefert den vorherigen Wert zurück. */
async function matrixfeld(
  anfrage: APIRequestContext,
  technologie: string,
  klasse: string,
  bewertung: string,
  begruendung: string,
): Promise<{ bewertung: string; begruendung: string }> {
  const h = await kopf(anfrage);
  const matrix = await (await anfrage.get(`${API}/api/v1/technologiematrix`, { headers: h })).json();
  const vorher = (matrix as { technologie: string; k_klasse: string; bewertung: string; begruendung: string }[]).find(
    (e) => e.technologie === technologie && e.k_klasse === klasse,
  );
  const antwort = await anfrage.put(`${API}/api/v1/technologiematrix/${technologie}/${klasse}`, {
    headers: h,
    data: { bewertung, begruendung },
  });
  if (antwort.status() >= 400) throw new Error(`Matrix: ${await antwort.text()}`);
  return { bewertung: vorher!.bewertung, begruendung: vorher!.begruendung };
}

/** Zur Matrixansicht wechseln. */
async function zurMatrix(seite: Page) {
  await seite.goto('/de/klassen');
  await seite.getByRole('button', { name: 'Matrix' }).click();
  await expect(seite.getByRole('columnheader', { name: 'AppSheet' })).toBeVisible();
}

vorgang('V-KLA-01', async ({ page }) => {
  await anmelden(page);
  await page.goto('/de/klassen');

  // Alle zehn, jede mit Name, Zweck und Auslöserbedingung (A.9.2).
  await expect(page.locator('[data-testid^="klasse-K"]')).toHaveCount(10);
  const k5 = page.getByTestId('klasse-K5');
  await expect(k5).toContainText('Zugriffs- und Rechtekonzept');
  await expect(k5).toContainText('schriftlich festzulegen');
  await expect(k5).toContainText('Ausgelöst: Datenschutz-Stufe 2');
});

vorgang('V-KLA-02', async ({ page }) => {
  await anmelden(page);
  await zurMatrix(page);

  // Beide Achsen: die vier Technologien als Spalten, die zehn Klassen als
  // Zeilen — und jede Zelle mit Wort, nicht nur mit Farbe.
  await expect(page.getByRole('columnheader')).toHaveCount(5);
  await expect(page.getByRole('rowheader')).toHaveCount(10);
  await expect(page.getByTestId('matrix-appsheet-K5')).toContainText('Nicht erfüllbar');
  await expect(page.getByTestId('matrix-apps-script-K5')).toContainText('Kompensierbar');
  await expect(page.getByTestId('matrix-python-kubernetes-K5')).toContainText('Erfüllt');
});

vorgang('V-KLA-03', async ({ page, request }) => {
  const marke = kennzeichen();
  const { tool } = await aufbau(request, marke, 'python-kubernetes');
  await anwenderMitRolle(request, `gov-${marke}`, `Governance ${marke}`, 'governance', 'global');
  await anmelden(page, `gov-${marke}`, `Governance ${marke}`);

  // Vor der Änderung trägt die Technologie K5.
  await page.goto(`/de/tools/${tool.id}`);
  await expect(page.getByTestId('befund-K5')).toContainText('Erfüllt');

  await zurMatrix(page);
  await page.getByTestId('matrix-python-kubernetes-K5').getByRole('button').click();
  await page.getByLabel('Bewertung').selectOption('nicht_erfuellbar');
  await page.getByLabel('Begründung').fill('Für diesen Durchlauf bewusst abgestuft.');
  await page.getByTestId('matrix-sichern').click();
  await expect(page.getByTestId('matrix-python-kubernetes-K5')).toContainText('Nicht erfüllbar');

  try {
    // Sofort wirksam: derselbe Befund sieht jetzt anders aus.
    await page.goto(`/de/tools/${tool.id}`);
    await expect(page.getByTestId('befund-K5')).toContainText('Ausschluss');
  } finally {
    await matrixfeld(
      request,
      'python-kubernetes',
      'K5',
      'erfuellt',
      'Organisatorische Anforderung — sie hängt an der Organisation, nicht an der Technologie.',
    );
  }
});

vorgang('V-KLA-04', async ({ page, request }) => {
  const marke = kennzeichen();
  const { prozess, tool } = await aufbau(request, marke, 'appsheet');
  await anmelden(page);

  // Am Prozess: der Verweis auf das Werkzeug, das den Fall trägt.
  await page.goto(`/de/prozesse/${prozess.id}`);
  const zeile = page.getByTestId(`prozessbefund-${tool.id}`);
  await expect(zeile).toContainText(`Werkzeug ${marke}`);
  await expect(zeile).toContainText('K5: Ausschluss');

  // Am Tool: der Befund mit dem, was zu entscheiden ist.
  await zeile.click();
  await expect(page.getByTestId('befund-K5')).toContainText('Ausschluss');

  // Im Cockpit: derselbe Fall als Handlungsaufforderung, mit dem Werkzeug
  // und dem Grund in einer Zeile.
  await page.goto('/de/cockpit/technologie_erfuellt_klasse_nicht');
  const cockpitzeile = page.getByTestId(`eintrag-${tool.id}`);
  await expect(cockpitzeile).toContainText('K5 Zugriffs- und Rechtekonzept');
  await expect(cockpitzeile).toContainText('Ausschluss');
});

vorgang('V-KLA-05', async ({ page, request }) => {
  const marke = kennzeichen();
  const { tool } = await aufbau(request, marke, 'apps-script');
  await anmelden(page);

  await page.goto(`/de/tools/${tool.id}`);
  // Ohne Vermerk bleibt der Befund offen.
  await expect(page.getByTestId('befund-K5')).toContainText('Maßnahme fehlt');

  await page.getByTestId('kompensieren-K5').click();
  // Eine leere Maßnahme ist keine.
  await expect(page.getByTestId('kompensation-sichern')).toBeDisabled();
  await page
    .getByLabel('Kompensierende Maßnahme')
    .fill('Zugriff über die Rechte der angesprochenen Ablage geregelt und jährlich geprüft.');
  await page.getByTestId('kompensation-sichern').click();

  await expect(page.getByTestId('befund-K5')).toContainText('Kompensiert');
  await expect(page.getByTestId('befund-K5')).toContainText('Maßnahme: Zugriff über die Rechte');
});

vorgang('V-KLA-06', async ({ page, request }) => {
  const marke = kennzeichen();
  const { tool } = await aufbau(request, marke, 'apps-script');
  await anmelden(page);

  await page.goto(`/de/tools/${tool.id}`);
  const karte = page.locator('.k-karte').filter({ hasText: 'Anforderungsklassen und Technologie' });

  // Klasse mit Namen, nicht nur als Kürzel …
  await expect(karte.getByTestId('befund-K5')).toContainText('K5 — Zugriffs- und Rechtekonzept');
  // … die Aussage der Technologie …
  await expect(karte.getByTestId('befund-K5')).toContainText(
    'ein eigenes Rechtekonzept hat es nicht',
  );
  // … und der nötige Schritt.
  await expect(karte.getByTestId('befund-K5')).toContainText(
    'Zu tun: die kompensierende Maßnahme beschreiben',
  );
  // Eine erfüllte Klasse sagt, dass nichts zu tun ist.
  await expect(karte.getByTestId('befund-K1')).toContainText('Nichts zu tun');
});
