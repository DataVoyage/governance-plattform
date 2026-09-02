/**
 * Der Vorgangskatalog, gelesen aus `docs/vorgaenge.md`.
 *
 * Die Spezifikation ist das Dokument, nicht diese Datei. Sie wird hier
 * geparst, damit Katalog und Durchlauf nicht auseinanderlaufen können: jeder
 * Vorgang bekommt seinen Titel und sein erwartetes Ergebnis aus dem Dokument,
 * und `katalog.vorgang.ts` prüft, dass beide Seiten dieselbe Menge tragen.
 */

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export interface Vorgang {
  kennung: string;
  /** Was der Anwender tut. */
  titel: string;
  /** Wer ihn ausführt (Leitdokument A.15). */
  rolle: string;
  /** Woran der Anwender erkennt, dass es geklappt hat — die geprüfte Zusage. */
  erwartet: string;
  /** Arbeitspaket aus `umsetzungsplan.md`. */
  ap: string;
  stand: 'erfüllt' | 'offen';
}

const HIER = dirname(fileURLToPath(import.meta.url));
export const KATALOGPFAD = join(HIER, '..', '..', 'docs', 'vorgaenge.md');

/** Nur Zeilen einer Tabelle, deren erste Spalte eine Kennung trägt. */
const ZEILE = /^\|\s*(V-[A-Z]{3}-\d{2})\s*\|(.+)\|\s*$/;

function lies(): Vorgang[] {
  const text = readFileSync(KATALOGPFAD, 'utf8');
  const vorgaenge: Vorgang[] = [];
  for (const zeile of text.split('\n')) {
    const treffer = ZEILE.exec(zeile);
    if (treffer === null) continue;
    const spalten = treffer[2].split('|').map((s) => s.trim());
    const [titel, rolle, erwartet, ap, stand] = spalten;
    if (stand !== 'erfüllt' && stand !== 'offen') {
      throw new Error(`${treffer[1]}: unbekannter Stand „${stand}" — erlaubt sind erfüllt|offen`);
    }
    vorgaenge.push({ kennung: treffer[1], titel, rolle, erwartet, ap, stand });
  }
  if (vorgaenge.length === 0) throw new Error(`Kein Vorgang in ${KATALOGPFAD} gefunden`);
  return vorgaenge;
}

export const VORGAENGE: Vorgang[] = lies();

export const NACH_KENNUNG: ReadonlyMap<string, Vorgang> = new Map(
  VORGAENGE.map((v) => [v.kennung, v]),
);

export function hole(kennung: string): Vorgang {
  const eintrag = NACH_KENNUNG.get(kennung);
  if (eintrag === undefined) {
    throw new Error(
      `${kennung} steht nicht im Vorgangskatalog. Erst in docs/vorgaenge.md aufnehmen — ` +
        'ein Durchlauf ohne Spezifikation ist genau das, was dieser Katalog verhindern soll.',
    );
  }
  return eintrag;
}
