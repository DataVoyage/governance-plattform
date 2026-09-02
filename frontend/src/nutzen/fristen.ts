/**
 * Fristrechnung in Arbeitstagen (Leitdokument A.13.5).
 *
 * Dieselbe Zählweise wie im Server — Samstag und Sonntag zählen nicht mit.
 * Der Server *setzt* die Frist, die Oberfläche *liest* sie; beide müssen
 * dasselbe meinen, sonst zeigt der Countdown eine andere Zahl an, als die
 * Eskalation verwendet.
 */

const TAG = 24 * 60 * 60 * 1000;

export interface Fristlage {
  /** Arbeitstage bis zum Stichtag, beziehungsweise seit ihm. Nie negativ. */
  tage: number;
  abgelaufen: boolean;
}

/**
 * Wie weit die Frist noch reicht.
 *
 * ``abgelaufen`` hängt am Zeitpunkt, nicht an der Tageszahl: eine Frist, die
 * heute um 14 Uhr endete, ist um 15 Uhr abgelaufen — auch wenn zwischen beiden
 * kein Arbeitstag liegt. Ein Vorzeichen allein könnte das nicht ausdrücken,
 * weil null kein Vorzeichen hat.
 */
export function fristlage(frist: string, jetzt = new Date()): Fristlage {
  const ziel = new Date(frist);
  const abgelaufen = ziel.getTime() < jetzt.getTime();
  const [von, bis] = abgelaufen ? [ziel, jetzt] : [jetzt, ziel];

  let zaehler = 0;
  const lauf = new Date(von.getFullYear(), von.getMonth(), von.getDate());
  const ende = new Date(bis.getFullYear(), bis.getMonth(), bis.getDate());
  while (lauf.getTime() < ende.getTime()) {
    lauf.setTime(lauf.getTime() + TAG);
    if (lauf.getDay() !== 0 && lauf.getDay() !== 6) zaehler += 1;
  }
  return { tage: zaehler, abgelaufen };
}
