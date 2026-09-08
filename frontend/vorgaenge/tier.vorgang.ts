/**
 * V-TIE — Tier, komposites Risiko und Prozesskette.
 *
 * Spezifiziert in `docs/tier-als-lenkungsobjekt.md`, umgesetzt in AP-19.
 *
 * Die Vorgänge belegen, dass es keine Ebene neben der Bewertung mehr gibt: Die
 * erklärten Erwartungen wirken über die UR-Achse, die Prozesskette über das
 * Tier, und beides ist über die Oberfläche nachvollziehbar. Der tragende
 * Vorgang ist V-TIE-03 — von einer Rechnung gibt es keine Abweichung.
 */

import { expect, type Page } from '@playwright/test';

import {
  anmelden,
  bewerten,
  kennzeichen,
  organisation,
  prozessAnlegen,
  toolAnlegen,
  toolMitProzess,
  vorgang,
  waehle,
} from './hilfen';

/** Öffnet den Wizard und wartet, bis die erste Frage steht. */
async function starte(seite: Page, prozessId: string) {
  await seite.goto(`/de/prozesse/${prozessId}/bewertung`);
  await expect(seite.getByTestId('frage')).toBeVisible();
}

/**
 * Beantwortet die aktuelle Frage so, wie die Datenlage sie vorschlägt, bis der
 * Baum durch ist. Der Vorschlag ist die begründungsfreie Antwort.
 */
async function beendeDurchlauf(seite: Page): Promise<string[]> {
  const gesehen: string[] = [];
  for (let i = 0; i < 20; i += 1) {
    if ((await seite.getByTestId('frage').count()) === 0) break;
    const kennung = await seite.getByTestId('frage').getAttribute('data-frage-id');
    if (kennung !== null) gesehen.push(kennung);
    const vorschlag = seite.getByTestId('vorschlag');
    const wert = (await vorschlag.count()) > 0 ? await vorschlag.getAttribute('data-wert') : null;
    const [ruf] = await Promise.all([
      seite.waitForResponse(
        (r) => r.url().includes('/bewertung/wizard') && r.request().method() === 'POST',
      ),
      seite
        .getByRole('button', { name: wert === 'true' ? 'Ja' : 'Nein', exact: true })
        .click(),
    ]);
    expect(ruf.ok(), `Wizard-Schritt: ${ruf.status()} ${await ruf.text()}`).toBeTruthy();
    await expect
      .poll(async () => {
        if ((await seite.getByTestId('frage').count()) === 0) return '__ende__';
        return seite.getByTestId('frage').getAttribute('data-frage-id');
      })
      .not.toBe(kennung);
  }
  return gesehen;
}

/** Speichert das Ergebnis und kehrt auf die Prozessseite zurück. */
async function speichere(seite: Page) {
  await expect(seite.getByTestId('tier')).toBeVisible();
  await Promise.all([
    seite.waitForResponse(
      (r) => r.url().includes('/bewertungen') && r.request().method() === 'POST',
    ),
    seite.getByTestId('bewertung-speichern').click(),
  ]);
}

vorgang('V-TIE-01', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  // Zwei erklärte Erwartungen — genau die beiden Anteile aus E-66.
  const prozess = await prozessAnlegen(request, org, {
    name: `Erwartung ${marke}`,
    customer: 'bereich',
    ausfallfolge: 'spuerbar',
  });
  await anmelden(page);

  // Sie stehen am Prozessobjekt, dort wo der Owner sie erklärt hat — die
  // Ausfallfolge als Erklärung, die Reichweite als ihre unmittelbare Folge.
  // Eine dritte, abgeleitete Größe steht hier seit AP-19 nicht mehr: Was die
  // Kette bewirkt, sagt das Tier und sonst nichts (E-72).
  await page.goto(`/de/prozesse/${prozess.id}`);
  await expect(page.getByTestId('reichweite')).toContainText('Fachbereich');
  await expect(page.getByTestId('ausfallfolge')).toContainText('Spürbar');
  await expect(page.getByTestId('kritikalitaet')).toHaveCount(0);

  // Und die Bewertung übernimmt sie unverändert als Ausgangslage.
  await starte(page, prozess.id);
  const lage = page.getByTestId('ausgangslage');
  await expect(lage).toContainText('Fachbereich');
  await expect(lage).toContainText('Spürbar');
});

vorgang('V-TIE-02', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, {
    name: `Ausgangslage ${marke}`,
    customer: 'bereich',
    ausfallfolge: 'spuerbar',
  });
  await anmelden(page);
  await starte(page, prozess.id);

  // Fachbereich x spürbar ergibt nach der Kompositionstabelle Stufe 2.
  await expect(page.getByTestId('ur-stufe')).toHaveText('2');
  // Der Rechenweg steht dabei, sonst wäre die Zahl eine Behauptung.
  await expect(page.getByTestId('ausgangslage')).toContainText('Fachbereich');
  await expect(page.getByTestId('ausgangslage')).toContainText('Spürbar');
});

vorgang('V-TIE-03', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, {
    name: `Ohne Frage ${marke}`,
    customer: 'unternehmen',
    ausfallfolge: 'kritisch',
  });
  await anmelden(page);
  await starte(page, prozess.id);

  const gesehen = await beendeDurchlauf(page);

  // Der tragende Punkt: Es gibt keinen Weg, die gerechnete Stufe zu ändern.
  // Nach dem fünften Block ist der Baum durch — eine Frage 6a existiert nicht.
  expect(gesehen.filter((k) => k.startsWith('6'))).toEqual([]);
  expect(gesehen[0]).toBe('1a');
  await expect(page.getByTestId('tier')).toBeVisible();

  // Die Stufe steht da, aber nicht als Eingabe.
  const lage = page.getByTestId('ausgangslage');
  await expect(lage).toBeVisible();
  await expect(lage.getByRole('textbox')).toHaveCount(0);
  await expect(lage.getByRole('button')).toHaveCount(0);
});

vorgang('V-TIE-04', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  // Unauffälliges Profil, aber ein eigenes Betriebsrisiko auf Stufe 3.
  const prozess = await prozessAnlegen(request, org, {
    name: `Eigenes Risiko ${marke}`,
    customer: 'unternehmen',
    ausfallfolge: 'kritisch',
  });
  await anmelden(page);
  await starte(page, prozess.id);
  await beendeDurchlauf(page);

  // Gekappt: reines Betriebsrisiko hebt allein nicht auf Tier 3 (A.8.5, 6a).
  await expect(page.getByTestId('tier')).toHaveText('2');
  await expect(page.getByTestId('tier-herkunft')).toContainText('eigenen Betriebsrisiko');
});

vorgang('V-TIE-05', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  // Der Nachfolger trägt UR 3; seine Bewertung ist Vorbedingung und läuft
  // deshalb über die API (E-35).
  const kritisch = await prozessAnlegen(request, org, {
    name: `Zahlungslauf ${marke}`,
    customer: 'unternehmen',
    ausfallfolge: 'kritisch',
  });
  await bewerten(request, kritisch.id);
  // Der speisende Prozess ist für sich harmlos.
  const speist = await prozessAnlegen(request, org, {
    name: `Vorbereitung ${marke}`,
    customer: 'persoenlich',
    ausfallfolge: 'keine',
    nachgelagert_ids: [kritisch.id],
  });

  await anmelden(page);
  await starte(page, speist.id);
  await beendeDurchlauf(page);

  // Abhängigkeit ist kein eigenes Betriebsrisiko und wird nicht gekappt.
  await expect(page.getByTestId('tier')).toHaveText('3');
  await expect(page.getByTestId('tier-herkunft')).toContainText('Prozesskette');
});

vorgang('V-TIE-06', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const kritisch = await prozessAnlegen(request, org, {
    name: `Kritischer Lauf ${marke}`,
    customer: 'unternehmen',
    ausfallfolge: 'kritisch',
  });
  await bewerten(request, kritisch.id);
  const speist = await prozessAnlegen(request, org, {
    name: `Speisend ${marke}`,
    customer: 'persoenlich',
    ausfallfolge: 'keine',
  });

  await anmelden(page);
  // Erst bewerten — ohne Kette, also Tier 1.
  await starte(page, speist.id);
  await beendeDurchlauf(page);
  await expect(page.getByTestId('tier')).toHaveText('1');
  await speichere(page);

  // Dann die Kette über die Oberfläche anlegen.
  await page.goto(`/de/prozesse/${speist.id}/bearbeiten`);
  await waehle(page, 'waehler-nachgelagert', `Kritischer Lauf ${marke}`);
  await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes(`/prozesse/${speist.id}`) && r.request().method() === 'PATCH',
    ),
    page.getByRole('button', { name: 'Speichern' }).click(),
  ]);

  // Die Bewertung ist überholt und sagt, warum.
  await page.goto(`/de/prozesse/${speist.id}`);
  await expect(page.getByText(/Diese Bewertung ist überholt/)).toBeVisible();
});

vorgang('V-TIE-07', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  // Ein Nachfolger, dessen Risiko das Tier des Vorgängers nicht bewegt.
  const harmlos = await prozessAnlegen(request, org, {
    name: `Harmlos ${marke}`,
    customer: 'persoenlich',
    ausfallfolge: 'keine',
  });
  await bewerten(request, harmlos.id);
  const speist = await prozessAnlegen(request, org, {
    name: `Unberuehrt ${marke}`,
    customer: 'bereich',
    ausfallfolge: 'spuerbar',
  });

  await anmelden(page);
  await starte(page, speist.id);
  await beendeDurchlauf(page);
  await speichere(page);

  await page.goto(`/de/prozesse/${speist.id}/bearbeiten`);
  await waehle(page, 'waehler-nachgelagert', `Harmlos ${marke}`);
  await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes(`/prozesse/${speist.id}`) && r.request().method() === 'PATCH',
    ),
    page.getByRole('button', { name: 'Speichern' }).click(),
  ]);

  // Kein Tier-Sprung, also keine Entwertung — sonst stürbe Agilität an
  // Wartezeiten (P4, E-69).
  await page.goto(`/de/prozesse/${speist.id}`);
  await expect(page.getByText(/Diese Bewertung ist überholt/)).toHaveCount(0);
});

vorgang('V-TIE-08', async ({ page, request }) => {
  const marke = kennzeichen();
  const org = await organisation(request, marke);
  const prozess = await prozessAnlegen(request, org, {
    name: `Rahmen ${marke}`,
    customer: 'bereich',
    ausfallfolge: 'gering',
  });
  await bewerten(request, prozess.id);
  const tool = await toolAnlegen(request, {
    name: `Rahmenwerkzeug ${marke}`,
    organisationseinheit_id: org.deId,
  });
  await toolMitProzess(request, tool.id, prozess.id);

  await anmelden(page);
  await page.goto(`/de/tools/${tool.id}`);
  await expect(page.getByTestId('erlaubt-reichweite')).toContainText('Fachbereich');

  // Der Kundenkreis wird geweitet — die abgeleitete Reichweite steigt damit
  // auf „Unternehmen".
  await page.goto(`/de/prozesse/${prozess.id}/bearbeiten`);
  await page.getByLabel('Kundenkreis').selectOption('unternehmen');
  await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes(`/prozesse/${prozess.id}`) && r.request().method() === 'PATCH',
    ),
    page.getByRole('button', { name: 'Speichern' }).click(),
  ]);

  // Der Rahmen des Tools bleibt trotzdem stehen: Sein Soll kommt aus der
  // Bewertung, nicht aus dem lebenden Feld (A.13.1, E-70).
  await page.goto(`/de/tools/${tool.id}`);
  await expect(page.getByTestId('erlaubt-reichweite')).toContainText('Fachbereich');
});
