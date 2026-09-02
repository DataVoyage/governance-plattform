/**
 * Der Katalog prüft sich selbst.
 *
 * Ohne diese Prüfung wäre `docs/vorgaenge.md` ein Wunschzettel: Vorgänge, die
 * niemand hinterlegt hat, und Durchläufe, die niemand spezifiziert hat, würden
 * still nebeneinander herlaufen. Hier werden beide Seiten gegeneinander
 * gehalten — und der Katalog gegen den Umsetzungsplan.
 */

import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

import { expect, test } from '@playwright/test';

import { VORGAENGE } from './katalog';

const HIER = dirname(fileURLToPath(import.meta.url));
const PLAN = join(HIER, '..', '..', 'docs', 'umsetzungsplan.md');
const PHASEN = join(HIER, '..', '..', 'docs', 'phasen.md');

/** Alle Kennungen, die irgendein Durchlauf registriert. */
function hinterlegteKennungen(): string[] {
  const kennungen: string[] = [];
  for (const datei of readdirSync(HIER)) {
    if (!datei.endsWith('.vorgang.ts') || datei === 'katalog.vorgang.ts') continue;
    const text = readFileSync(join(HIER, datei), 'utf8');
    for (const treffer of text.matchAll(/vorgang\(\s*'(V-[A-Z]{3}-\d{2})'/g)) {
      kennungen.push(treffer[1]);
    }
  }
  return kennungen;
}

/** Arbeitspakete des Plans mit der Zahl offener und erledigter Punkte. */
function arbeitspakete(): Map<string, { offen: number; erledigt: number }> {
  const pakete = new Map<string, { offen: number; erledigt: number }>();
  let aktuell: string | null = null;
  for (const zeile of readFileSync(PLAN, 'utf8').split('\n')) {
    const ueberschrift = /^###\s+(AP-\d+)\s/.exec(zeile);
    if (ueberschrift !== null) {
      aktuell = ueberschrift[1];
      pakete.set(aktuell, { offen: 0, erledigt: 0 });
      continue;
    }
    if (aktuell === null) continue;
    if (/^##\s/.test(zeile)) aktuell = null;
    else if (/^-\s\[x\]/.test(zeile)) pakete.get(aktuell)!.erledigt += 1;
    else if (/^-\s\[ \]/.test(zeile)) pakete.get(aktuell)!.offen += 1;
  }
  return pakete;
}

test.describe('Vorgangskatalog', () => {
  test('jeder Vorgang hat genau einen Durchlauf', () => {
    const hinterlegt = hinterlegteKennungen();
    const doppelt = hinterlegt.filter((k, i) => hinterlegt.indexOf(k) !== i);
    expect(doppelt, 'mehrfach hinterlegte Vorgänge').toEqual([]);

    const spezifiziert = VORGAENGE.map((v) => v.kennung);
    const ohneDurchlauf = spezifiziert.filter((k) => !hinterlegt.includes(k));
    expect(
      ohneDurchlauf,
      'Im Katalog spezifiziert, aber nirgends hinterlegt — mit vorgang(...) ergänzen',
    ).toEqual([]);
  });

  test('die Kennungen sind eindeutig und fortlaufend', () => {
    const kennungen = VORGAENGE.map((v) => v.kennung);
    expect(new Set(kennungen).size, 'doppelte Kennung im Katalog').toBe(kennungen.length);

    const je: Record<string, number[]> = {};
    for (const kennung of kennungen) {
      const [, bereich, nummer] = /^V-([A-Z]{3})-(\d{2})$/.exec(kennung)!;
      (je[bereich] ??= []).push(Number(nummer));
    }
    for (const [bereich, nummern] of Object.entries(je)) {
      const erwartet = nummern.map((_, i) => i + 1);
      expect([...nummern].sort((a, b) => a - b), `Lücke in V-${bereich}`).toEqual(erwartet);
    }
  });

  test('jeder Vorgang nennt ein Arbeitspaket, das es gibt', () => {
    const pakete = arbeitspakete();
    expect(pakete.size, 'keine Arbeitspakete im Umsetzungsplan gefunden').toBeGreaterThan(0);
    for (const eintrag of VORGAENGE) {
      expect(pakete.has(eintrag.ap), `${eintrag.kennung} nennt unbekanntes ${eintrag.ap}`).toBe(
        true,
      );
    }
  });

  test('ein abgeschlossenes Arbeitspaket hat keine offenen Vorgänge mehr', () => {
    const pakete = arbeitspakete();
    const widerspruch = VORGAENGE.filter(
      (v) => v.stand === 'offen' && pakete.get(v.ap)?.offen === 0,
    ).map((v) => `${v.kennung} (${v.ap})`);
    expect(
      widerspruch,
      'Das Arbeitspaket gilt als fertig, der Vorgang ist aber offen — eins von beidem stimmt nicht',
    ).toEqual([]);
  });

  test('jedes Abnahmekriterium nennt seinen Weg über die Oberfläche', () => {
    // Seit AP-10 ist der Katalog die Abnahmegrundlage (Befund B15). Ein
    // Kriterium ohne Vorgangsspalte wäre wieder eine Aussage über die API.
    const zeilen = readFileSync(PHASEN, 'utf8')
      .split('\n')
      .filter((zeile) => /^\|\s*\d+\s*\|/.test(zeile) && zeile.split('|').length >= 5);
    expect(zeilen.length, 'keine Kriterienzeilen in phasen.md gefunden').toBeGreaterThan(20);

    const ohneWeg = zeilen
      .map((zeile) => zeile.split('|').map((s) => s.trim()))
      .filter((spalten) => spalten[3] === '')
      .map((spalten) => spalten[2].slice(0, 60));
    expect(ohneWeg, 'Kriterium ohne Vorgang und ohne die Angabe „kein Nutzerweg"').toEqual([]);
  });

  test('jeder in phasen.md zitierte Vorgang läuft auch', () => {
    const zitiert = new Set(
      [...readFileSync(PHASEN, 'utf8').matchAll(/V-[A-Z]{3}-\d{2}/g)].map((t) => t[0]),
    );
    expect(zitiert.size, 'phasen.md zitiert keinen Vorgang').toBeGreaterThan(30);

    const bekannt = new Map(VORGAENGE.map((v) => [v.kennung, v.stand]));
    const unbekannt = [...zitiert].filter((k) => !bekannt.has(k));
    expect(unbekannt, 'in phasen.md zitiert, im Katalog nicht vorhanden').toEqual([]);

    const offen = [...zitiert].filter((k) => bekannt.get(k) === 'offen');
    expect(offen, 'als Nachweis zitiert, aber noch nicht umgesetzt').toEqual([]);
  });

  test('jeder Vorgang nennt ein erwartetes Ergebnis', () => {
    const ohne = VORGAENGE.filter(
      (v) => v.erwartet.length < 20 || v.titel.length < 5 || v.rolle.length === 0,
    ).map((v) => v.kennung);
    expect(ohne, 'Vorgang ohne belastbares erwartetes Ergebnis, Titel oder Rolle').toEqual([]);
  });

  test('Stand des Katalogs', () => {
    const je = new Map<string, { erfuellt: number; offen: number }>();
    for (const eintrag of VORGAENGE) {
      const zaehler = je.get(eintrag.ap) ?? { erfuellt: 0, offen: 0 };
      if (eintrag.stand === 'erfüllt') zaehler.erfuellt += 1;
      else zaehler.offen += 1;
      je.set(eintrag.ap, zaehler);
    }
    const zeilen = [...je.entries()]
      .sort()
      .map(([ap, z]) => `${ap}: ${z.erfuellt} erfüllt, ${z.offen} offen`);
    const erfuellt = VORGAENGE.filter((v) => v.stand === 'erfüllt').length;
    test.info().annotations.push({
      type: 'Abdeckung',
      description: `${erfuellt} von ${VORGAENGE.length} Vorgängen laufen. ${zeilen.join(' · ')}`,
    });
    // Kein Schwellwert: die Zahl soll berichten, nicht bewerten.
    expect(VORGAENGE.length).toBeGreaterThan(0);
  });
});
