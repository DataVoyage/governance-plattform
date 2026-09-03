/**
 * Der Vortrag, gelesen aus `docs/praesentation.md`.
 *
 * Die Präsentation hat **eine** Quelle. Sie liegt als Markdown im Repository,
 * ist dort lesbar, lässt sich mit Marp zu einem PDF machen — und dieselbe
 * Datei trägt die Ansicht in der Anwendung. Eine zweite, gepflegte Fassung im
 * Frontend wäre genau die Doppelpflege, die dieses Vorhaben an jeder anderen
 * Stelle vermeidet (Grundsatz P5).
 *
 * Deshalb kein allgemeiner Markdown-Übersetzer, sondern einer, der **genau
 * die Auszeichnungen kennt, die im Dokument vorkommen**. Alles andere meldet
 * er als Fehler, statt es stillschweigend als Fließtext auszugeben. Wer eine
 * neue Auszeichnung benutzt, bekommt einen roten Test — und nicht eine Folie,
 * auf der Sternchen stehen.
 */

/** Ein Stück Text mit seiner Auszeichnung. */
export interface Teil {
  art: 'text' | 'stark' | 'betont' | 'code';
  text: string;
}

export type Block =
  | { art: 'ueberschrift'; ebene: 1 | 2; inhalt: Teil[] }
  | { art: 'absatz'; inhalt: Teil[] }
  | { art: 'liste'; geordnet: boolean; punkte: Teil[][] }
  | { art: 'zitat'; absaetze: Teil[][] }
  | { art: 'tabelle'; kopf: Teil[][]; zeilen: Teil[][][] }
  | { art: 'bild'; quelle: string; breite: number | null }
  | { art: 'code'; text: string };

export interface Folie {
  /** Eins-basiert — dieselbe Zählung, die der Foliensatz anzeigt. */
  nummer: number;
  /** Die Überschrift der Folie, für Gliederung und Sprungmarken. */
  titel: string;
  /** Auszeichnung aus `<!-- _class: … -->`, etwa `eng` für dichte Folien. */
  klasse: string | null;
  bloecke: Block[];
}

export class Unbekannt extends Error {}

const VORSPANN = /^---\r?\n[\s\S]*?\r?\n---\r?\n/;
const STILBLOCK = /<style>[\s\S]*?<\/style>/g;
const KOMMENTAR = /<!--[\s\S]*?-->/g;
const KLASSE = /<!--\s*_class:\s*([a-z-]+)\s*-->/;
const TRENNER = /\r?\n---\r?\n/;

const UEBERSCHRIFT = /^(#{1,2})\s+(.*)$/;
const PUNKT = /^\*\s+(.*)$/;
const NUMMER = /^\d+\.\s+(.*)$/;
const ZITAT = /^>\s?(.*)$/;
const TABELLE = /^\|(.*)\|\s*$/;
const TRENNZEILE = /^\|[\s|:-]+\|\s*$/;
const BILD = /^!\[([^\]]*)\]\(([^)]+)\)\s*$/;
const CODEZAUN = /^```/;
const EINRUECKUNG = /^\s+/;

/** Fett, kursiv und Festbreite — mehr Auszeichnung kennt der Vortrag nicht. */
const AUSZEICHNUNG = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\*[^*\s][^*]*\*)/g;

export function zerlege(zeile: string): Teil[] {
  const teile: Teil[] = [];
  let gelesen = 0;
  for (const treffer of zeile.matchAll(AUSZEICHNUNG)) {
    const stelle = treffer.index ?? 0;
    if (stelle > gelesen) teile.push({ art: 'text', text: zeile.slice(gelesen, stelle) });
    const [gefunden] = treffer;
    if (gefunden.startsWith('`')) {
      teile.push({ art: 'code', text: gefunden.slice(1, -1) });
    } else if (gefunden.startsWith('**')) {
      teile.push({ art: 'stark', text: gefunden.slice(2, -2) });
    } else {
      teile.push({ art: 'betont', text: gefunden.slice(1, -1) });
    }
    gelesen = stelle + gefunden.length;
  }
  if (gelesen < zeile.length) teile.push({ art: 'text', text: zeile.slice(gelesen) });
  return teile.length > 0 ? teile : [{ art: 'text', text: zeile }];
}

function zellen(zeile: string): Teil[][] {
  const roh = TABELLE.exec(zeile)?.[1] ?? '';
  return roh.split('|').map((z) => zerlege(z.trim()));
}

/**
 * Die Blöcke einer einzelnen Folie.
 *
 * Der Durchlauf ist bewusst zeilenweise und ohne Rückgriff: eine Folie ist
 * kurz, und ein Zustandsautomat über wenige Zeilen bleibt lesbar.
 */
function bloecke(text: string, nummer: number): Block[] {
  const zeilen = text.split(/\r?\n/);
  const ergebnis: Block[] = [];
  let absatz: string[] = [];

  const absatzAbschliessen = () => {
    if (absatz.length === 0) return;
    ergebnis.push({ art: 'absatz', inhalt: zerlege(absatz.join(' ')) });
    absatz = [];
  };

  for (let i = 0; i < zeilen.length; i += 1) {
    const zeile = zeilen[i];
    const blank = zeile.trim() === '';

    if (blank) {
      absatzAbschliessen();
      continue;
    }

    const ueberschrift = UEBERSCHRIFT.exec(zeile);
    if (ueberschrift) {
      absatzAbschliessen();
      ergebnis.push({
        art: 'ueberschrift',
        ebene: ueberschrift[1].length as 1 | 2,
        inhalt: zerlege(ueberschrift[2]),
      });
      continue;
    }

    const bild = BILD.exec(zeile);
    if (bild) {
      absatzAbschliessen();
      const breite = /w:(\d+)/.exec(bild[1]);
      ergebnis.push({
        art: 'bild',
        quelle: bild[2],
        breite: breite ? Number(breite[1]) : null,
      });
      continue;
    }

    if (CODEZAUN.test(zeile)) {
      absatzAbschliessen();
      const gesammelt: string[] = [];
      i += 1;
      while (i < zeilen.length && !CODEZAUN.test(zeilen[i])) {
        gesammelt.push(zeilen[i]);
        i += 1;
      }
      ergebnis.push({ art: 'code', text: gesammelt.join('\n') });
      continue;
    }

    if (PUNKT.test(zeile) || NUMMER.test(zeile)) {
      absatzAbschliessen();
      const geordnet = NUMMER.test(zeile);
      const punkte: string[] = [];
      while (i < zeilen.length) {
        const treffer = geordnet ? NUMMER.exec(zeilen[i]) : PUNKT.exec(zeilen[i]);
        if (treffer) {
          punkte.push(treffer[1]);
        } else if (EINRUECKUNG.test(zeilen[i]) && zeilen[i].trim() !== '' && punkte.length > 0) {
          // Fortsetzungszeile eines Punktes — sie gehört zum vorigen.
          punkte[punkte.length - 1] += ` ${zeilen[i].trim()}`;
        } else {
          break;
        }
        i += 1;
      }
      i -= 1;
      ergebnis.push({ art: 'liste', geordnet, punkte: punkte.map(zerlege) });
      continue;
    }

    if (ZITAT.test(zeile)) {
      absatzAbschliessen();
      const gesammelt: string[] = [];
      while (i < zeilen.length && ZITAT.test(zeilen[i])) {
        gesammelt.push(ZITAT.exec(zeilen[i])![1]);
        i += 1;
      }
      i -= 1;
      const absaetze = gesammelt
        .join('\n')
        .split(/\n\s*\n/)
        .map((teil) => zerlege(teil.replace(/\n/g, ' ').trim()));
      ergebnis.push({ art: 'zitat', absaetze });
      continue;
    }

    if (TABELLE.test(zeile)) {
      absatzAbschliessen();
      const kopf = zellen(zeile);
      i += 1;
      if (i >= zeilen.length || !TRENNZEILE.test(zeilen[i])) {
        throw new Unbekannt(`Folie ${nummer}: Tabelle ohne Trennzeile unter dem Kopf`);
      }
      const reihen: Teil[][][] = [];
      i += 1;
      while (i < zeilen.length && TABELLE.test(zeilen[i])) {
        reihen.push(zellen(zeilen[i]));
        i += 1;
      }
      i -= 1;
      ergebnis.push({ art: 'tabelle', kopf, zeilen: reihen });
      continue;
    }

    if (zeile.trimStart().startsWith('<')) {
      throw new Unbekannt(`Folie ${nummer}: unbekannte Auszeichnung „${zeile.trim()}"`);
    }

    absatz.push(zeile.trim());
  }

  absatzAbschliessen();
  return ergebnis;
}

/**
 * Zerlegt das ganze Dokument in Folien.
 *
 * Vorspann und Massband (`<style>`) gehören zum Foliensatz für Marp und nicht
 * in die Anwendung — sie werden vorher entfernt.
 */
export function liesVortrag(quelle: string): Folie[] {
  const ohneVorspann = quelle.replace(VORSPANN, '').replace(STILBLOCK, '');
  const abschnitte = ohneVorspann.split(TRENNER);
  const folien: Folie[] = [];

  abschnitte.forEach((abschnitt, stelle) => {
    const klasse = KLASSE.exec(abschnitt)?.[1] ?? null;
    const text = abschnitt.replace(KOMMENTAR, '').trim();
    if (text === '') return;
    const nummer = stelle + 1;
    const inhalt = bloecke(text, nummer);
    const ueberschrift = inhalt.find((b) => b.art === 'ueberschrift');
    folien.push({
      nummer,
      titel:
        ueberschrift && ueberschrift.art === 'ueberschrift'
          ? ueberschrift.inhalt.map((teil) => teil.text).join('')
          : `Folie ${nummer}`,
      klasse,
      bloecke: inhalt,
    });
  });

  if (folien.length === 0) throw new Unbekannt('Der Vortrag enthält keine Folie');
  return folien;
}
