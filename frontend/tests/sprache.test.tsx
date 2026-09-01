/**
 * Abnahmekriterium Phase 1.7 — der Sprachpfad aendert die Anzeige,
 * nicht die sichtbaren Daten (Architektur 9.2).
 */

import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { KATALOG, SPRACHEN, istSprache, uebersetze } from '@/i18n';
import { pfadMitSprache } from '@/komponenten/Layout';
import { EINHEITEN, PROFIL, fetchAttrappe, prozess, zeichne } from './hilfen';

function routen() {
  return [
    { pfad: '/api/v1/auth/me', koerper: PROFIL },
    { pfad: '/api/v1/prozesse', koerper: [prozess(), prozess({ id: 'p-2', name: 'Zahlungslauf' })] },
    { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    { pfad: /\/bewertungen$/, koerper: [] },
  ];
}

describe('Textkatalog', () => {
  it('kennt fuer jede Sprache dieselben Schluessel', () => {
    const deutsch = Object.keys(KATALOG.de).sort();
    for (const sprache of SPRACHEN) {
      expect(Object.keys(KATALOG[sprache]).sort()).toEqual(deutsch);
    }
  });

  it('erkennt gueltige und ungueltige Sprachkuerzel', () => {
    expect(istSprache('de')).toBe(true);
    expect(istSprache('fr')).toBe(true);
    expect(istSprache('xx')).toBe(false);
    expect(istSprache(undefined)).toBe(false);
  });

  it('uebersetzt je Sprache', () => {
    expect(uebersetze('de', 'nav.prozesse')).toBe('Prozesse');
    expect(uebersetze('fr', 'nav.prozesse')).toBe('Processus');
  });
});

describe('pfadMitSprache', () => {
  it('tauscht nur das erste Segment', () => {
    expect(pfadMitSprache('/de/prozesse/abc', 'fr')).toBe('/fr/prozesse/abc');
    expect(pfadMitSprache('/', 'fr')).toBe('/fr');
  });
});

describe('Sprachpfad', () => {
  it('zeigt die Oberflaeche auf Deutsch unter /de', async () => {
    fetchAttrappe(routen());
    zeichne('/de/prozesse');
    expect(await screen.findByRole('heading', { name: 'Prozessobjekte' })).toBeInTheDocument();
  });

  it('zeigt dieselbe Ansicht auf Franzoesisch unter /fr', async () => {
    fetchAttrappe(routen());
    zeichne('/fr/prozesse');
    expect(
      await screen.findByRole('heading', { name: 'Objets de processus' }),
    ).toBeInTheDocument();
  });

  it('aendert beim Sprachwechsel die Anzeige, aber nicht die Datensaetze', async () => {
    const { aufrufe } = fetchAttrappe(routen());
    zeichne('/de/prozesse');
    await screen.findByRole('heading', { name: 'Prozessobjekte' });
    const vorher = await screen.findAllByRole('row');

    await userEvent.selectOptions(screen.getByLabelText('Sprache'), 'fr');

    await screen.findByRole('heading', { name: 'Objets de processus' });
    const nachher = await screen.findAllByRole('row');
    expect(nachher.length).toBe(vorher.length);
    expect(screen.getByText('Rechnungspruefung')).toBeInTheDocument();
    expect(screen.getByText('Zahlungslauf')).toBeInTheDocument();

    // Der Sprachwechsel schickt keine andere Abfrage an den Server.
    const prozessAufrufe = aufrufe.filter((a) => a.url.endsWith('/api/v1/prozesse'));
    expect(new Set(prozessAufrufe.map((a) => a.url)).size).toBe(1);
  });

  it('faellt bei unbekanntem Sprachkuerzel auf Deutsch zurueck', async () => {
    fetchAttrappe(routen());
    zeichne('/xx/prozesse');
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Prozessobjekte' })).toBeInTheDocument(),
    );
  });
});
