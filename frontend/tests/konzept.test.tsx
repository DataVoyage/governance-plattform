/**
 * Der Vortrag in der Anwendung.
 *
 * Zwei Zusicherungen tragen diese Datei. Die erste gilt dem Zerleger: er
 * kennt genau die Auszeichnungen des Dokuments und meldet jede andere, statt
 * sie stillschweigend als Fließtext auszugeben. Die zweite gilt dem
 * Dokument selbst — es wird hier vollständig durchgelesen. Wer eine neue
 * Auszeichnung benutzt, bekommt einen roten Test und keine Folie mit
 * Sternchen darauf.
 */

import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { Unbekannt, liesVortrag, zerlege } from '@/nutzen/folien';
import { EINHEITEN, PROFIL, fetchAttrappe, zeichne } from './hilfen';

// Dieselbe Quelle, die auch die Seite einliest.
import quelle from '../../docs/praesentation.md?raw';

describe('Zerleger', () => {
  it('erkennt fett, kursiv und Festbreite nebeneinander', () => {
    expect(zerlege('Ein **starker** und ein *betonter* Teil mit `code`.')).toEqual([
      { art: 'text', text: 'Ein ' },
      { art: 'stark', text: 'starker' },
      { art: 'text', text: ' und ein ' },
      { art: 'betont', text: 'betonter' },
      { art: 'text', text: ' Teil mit ' },
      { art: 'code', text: 'code' },
      { art: 'text', text: '.' },
    ]);
  });

  it('lässt gewöhnlichen Text unangetastet', () => {
    expect(zerlege('Nichts ausgezeichnet')).toEqual([
      { art: 'text', text: 'Nichts ausgezeichnet' },
    ]);
  });

  it('meldet eine unbekannte Auszeichnung, statt sie zu verschlucken', () => {
    expect(() => liesVortrag('# Titel\n\n<figure>Etwas Fremdes</figure>')).toThrow(Unbekannt);
  });

  it('meldet eine Tabelle ohne Trennzeile', () => {
    expect(() => liesVortrag('# Titel\n\n| a | b |\n| 1 | 2 |')).toThrow(Unbekannt);
  });

  it('meldet einen Vortrag ohne Folie', () => {
    expect(() => liesVortrag('')).toThrow(Unbekannt);
  });

  it('liest Überschrift, Liste, Tabelle, Zitat, Bild und Code', () => {
    const [folie] = liesVortrag(
      [
        '## Eine Folie',
        '',
        'Ein Absatz, der',
        'über zwei Zeilen geht.',
        '',
        '* Erster Punkt',
        '* Zweiter Punkt',
        '  mit Fortsetzung',
        '',
        '1. Ein Schritt',
        '',
        '> Ein Zitat',
        '',
        '| Kopf | Wert |',
        '|---|---|',
        '| a | 1 |',
        '',
        '![w:900](bilder/cockpit.png)',
        '',
        '```bash',
        'docker compose up',
        '```',
      ].join('\n'),
    );
    expect(folie.titel).toBe('Eine Folie');
    expect(folie.bloecke.map((b) => b.art)).toEqual([
      'ueberschrift',
      'absatz',
      'liste',
      'liste',
      'zitat',
      'tabelle',
      'bild',
      'code',
    ]);
    const absatz = folie.bloecke[1];
    expect(absatz.art === 'absatz' && absatz.inhalt[0].text).toBe(
      'Ein Absatz, der über zwei Zeilen geht.',
    );
    const liste = folie.bloecke[2];
    expect(liste.art === 'liste' && liste.punkte[1][0].text).toBe('Zweiter Punkt mit Fortsetzung');
    const bild = folie.bloecke[6];
    expect(bild.art === 'bild' && bild.breite).toBe(900);
  });

  it('nimmt die Auszeichnung dichter Folien mit', () => {
    const [folie] = liesVortrag('<!-- _class: eng -->\n\n## Dicht\n\nText.');
    expect(folie.klasse).toBe('eng');
  });
});

describe('Der Vortrag selbst', () => {
  const folien = liesVortrag(quelle);

  it('lässt sich vollständig lesen', () => {
    expect(folien.length).toBeGreaterThan(30);
    for (const folie of folien) {
      expect(folie.bloecke.length, `Folie ${folie.nummer} ist leer`).toBeGreaterThan(0);
      expect(folie.titel, `Folie ${folie.nummer} ohne Titel`).not.toBe('');
    }
  });

  it('trägt weder Vorspann noch Massband in die Anwendung', () => {
    const alleTexte = folien
      .flatMap((f) => f.bloecke)
      .flatMap((b) => ('inhalt' in b ? b.inhalt.map((teil) => teil.text) : []))
      .join(' ');
    expect(alleTexte).not.toContain('marp:');
    expect(alleTexte).not.toContain('paginate');
    expect(alleTexte).not.toContain('font-size');
  });

  it('verweist nur auf Bilder, die es gibt', () => {
    const bilder = folien
      .flatMap((f) => f.bloecke)
      .filter((b) => b.art === 'bild')
      .map((b) => (b.art === 'bild' ? b.quelle : ''));
    expect(bilder.length).toBeGreaterThan(0);
    for (const bild of bilder) expect(bild).toMatch(/^bilder\/[a-z-]+\.png$/);
  });
});

describe('Konzeptseite', () => {
  function attrappe() {
    fetchAttrappe([
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    ]);
  }

  // Aus der Quelle gelesen statt fest eingetragen: der Vortrag wächst, und
  // eine Zahl im Test würde bei jeder neuen Folie brechen, ohne etwas zu sagen.
  const ANZAHL = liesVortrag(quelle).length;

  it('zeigt die erste Folie und blättert vorwärts', async () => {
    attrappe();
    zeichne('/de/konzept');
    expect(await screen.findByTestId('folie-1')).toBeInTheDocument();
    expect(screen.getByText(`1 / ${ANZAHL}`)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Weiter' }));
    expect(await screen.findByTestId('folie-2')).toBeInTheDocument();
  });

  it('nimmt die Foliennummer aus der Adresse', async () => {
    attrappe();
    zeichne('/de/konzept?folie=3');
    const folie = await screen.findByTestId('folie-3');
    expect(within(folie).getByRole('heading')).toBeInTheDocument();
  });

  it('begrenzt eine Nummer außerhalb des Vortrags', async () => {
    attrappe();
    zeichne('/de/konzept?folie=999');
    expect(await screen.findByTestId(`folie-${ANZAHL}`)).toBeInTheDocument();
  });

  it('blättert mit den Pfeiltasten', async () => {
    attrappe();
    zeichne('/de/konzept');
    await screen.findByTestId('folie-1');
    await userEvent.keyboard('{ArrowRight}');
    expect(await screen.findByTestId('folie-2')).toBeInTheDocument();
    await userEvent.keyboard('{ArrowLeft}');
    expect(await screen.findByTestId('folie-1')).toBeInTheDocument();
    await userEvent.keyboard('{End}');
    expect(await screen.findByTestId(`folie-${ANZAHL}`)).toBeInTheDocument();
    await userEvent.keyboard('{Home}');
    expect(await screen.findByTestId('folie-1')).toBeInTheDocument();
  });

  it('zeigt in der Dokumentansicht alle Folien untereinander', async () => {
    attrappe();
    zeichne('/de/konzept');
    await screen.findByTestId('folie-1');
    await userEvent.click(screen.getByRole('button', { name: 'Dokument' }));
    expect(await screen.findByRole('heading', { name: 'Worum es hier geht' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Zusammengefasst' })).toBeInTheDocument();
  });

  it('weist auf Französisch darauf hin, dass der Vortrag deutsch ist', async () => {
    attrappe();
    zeichne('/fr/konzept');
    expect(await screen.findByText(/allemand/)).toBeInTheDocument();
  });
});
