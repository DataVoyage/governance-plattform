/**
 * Bewertungs-Wizard in der Oberflaeche (Architektur 8.2, 9.1).
 */

import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { Bewertung, Frage } from '@/api/typen';
import { EINHEITEN, PROFIL, fetchAttrappe, prozess, zeichne, type Route } from './hilfen';

function frage(id: string, nummer: number, block: string, titel: string, text: string): Frage {
  return { id, text, block, block_titel: titel, nummer, anzahl_bloecke: 6 };
}

const KI_FRAGE = frage('1a', 1, 'ki', 'Kuenstliche Intelligenz', 'Setzt der Prozess KI ein?');
const DS_FRAGE = frage('2a', 2, 'ds', 'Datenschutz', 'Besondere Kategorien?');

function bewertung(ueberschreibungen: Partial<Bewertung> = {}): Bewertung {
  return {
    id: 'b-1',
    prozessobjekt_id: 'p-1',
    ki_stufe: 0,
    ds_stufe: 3,
    mb_stufe: 1,
    it_stufe: 1,
    rg_stufe: 2,
    ur_stufe: 2,
    tier: 3,
    gesperrt: false,
    vollstaendig: true,
    ausgeloeste_k_klassen: ['K1', 'K2', 'K3', 'K4', 'K5', 'K7', 'K8', 'K9'],
    antworten: {},
    bewertet_von: 'user-1',
    bewertet_am: '2026-09-01T10:00:00Z',
    gueltig_bis: '2027-09-01T10:00:00Z',
    ...ueberschreibungen,
  };
}

function grundrouten(bewertungen: Bewertung[] = []): Route[] {
  return [
    { pfad: '/api/v1/auth/me', koerper: PROFIL },
    { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    { pfad: '/api/v1/prozesse/p-1/bewertungen', koerper: bewertungen },
    { pfad: '/api/v1/prozesse/p-1', koerper: prozess() },
  ];
}

describe('Wizard', () => {
  it('verlangt zu Beginn die Wahl zwischen schnell und vollstaendig', async () => {
    fetchAttrappe(grundrouten());
    zeichne('/de/prozesse/p-1/bewertung');
    expect(await screen.findByText('Wie möchten Sie den Baum durchlaufen?')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Schnell — endet beim ersten Tier-3-Treffer' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Vollständig — alle sechs Schritte, mit K-Klassen' }),
    ).toBeInTheDocument();
  });

  it('zeigt eine Frage pro Bildschirm mit zwei Antwortknoepfen und keinen Zwischenstand', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: {
          naechste_frage: KI_FRAGE,
          abgeschlossen: false,
          verboten: false,
          vollstaendig: true,
          vorschau: null,
        },
      },
    ]);
    zeichne('/de/prozesse/p-1/bewertung');
    await userEvent.click(
      await screen.findByRole('button', { name: 'Vollständig — alle sechs Schritte, mit K-Klassen' }),
    );

    expect(await screen.findByTestId('frage')).toHaveTextContent('Setzt der Prozess KI ein?');
    expect(screen.getByText('Schritt 1 von 6 — Kuenstliche Intelligenz')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Ja' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Nein' })).toBeInTheDocument();
    // Kein Tier, kein Profil, solange der Durchlauf laeuft.
    expect(screen.queryByTestId('tier')).toBeNull();
    expect(screen.queryByTestId('profil')).toBeNull();

    const erster = aufrufe.find((a) => a.url.includes('/bewertung/wizard'));
    expect(erster?.koerper).toEqual({ modus: 'vollstaendig', antworten: {} });
  });

  it('schickt die Antwort mit und holt die naechste Frage', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: (nummer: number) => ({
          naechste_frage: nummer === 1 ? KI_FRAGE : DS_FRAGE,
          abgeschlossen: false,
          verboten: false,
          vollstaendig: true,
          vorschau: null,
        }),
      },
    ]);

    zeichne('/de/prozesse/p-1/bewertung');
    await userEvent.click(
      await screen.findByRole('button', { name: 'Vollständig — alle sechs Schritte, mit K-Klassen' }),
    );
    await screen.findByTestId('frage');
    await userEvent.click(screen.getByRole('button', { name: 'Nein' }));

    await waitFor(() =>
      expect(screen.getByTestId('frage')).toHaveTextContent('Besondere Kategorien?'),
    );
    const letzter = aufrufe.filter((a) => a.url.includes('/bewertung/wizard')).at(-1);
    expect(letzter?.koerper).toEqual({ modus: 'vollstaendig', antworten: { '1a': false } });
  });

  it('zeigt Tier, Profil und K-Klassen erst am Ende und speichert', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: {
          naechste_frage: null,
          abgeschlossen: true,
          verboten: false,
          vollstaendig: true,
          vorschau: {
            tier: 3,
            profil: { ki: 0, ds: 3, mb: 1, it: 1, rg: 2, ur: 2 },
            ausgeloeste_k_klassen: ['K1', 'K2', 'K3', 'K4', 'K5', 'K7', 'K8', 'K9'],
            vollstaendig: true,
          },
        },
      },
      {
        pfad: '/api/v1/prozesse/p-1/bewertungen',
        methode: 'POST',
        status: 201,
        koerper: { bewertung: bewertung(), alarm: null },
      },
    ]);
    zeichne('/de/prozesse/p-1/bewertung');
    await userEvent.click(
      await screen.findByRole('button', { name: 'Vollständig — alle sechs Schritte, mit K-Klassen' }),
    );

    expect(await screen.findByTestId('tier')).toHaveTextContent('3');
    expect(screen.getByTestId('profil')).toHaveTextContent('KI0-DS3-MB1-IT1-RG2-UR2');
    const klassen = screen.getByTestId('k-klassen');
    expect(klassen).toHaveTextContent('K4');
    expect(klassen).not.toHaveTextContent('K6');
    expect(klassen).not.toHaveTextContent('K10');

    await userEvent.click(screen.getByRole('button', { name: 'Bewertung speichern' }));
    await screen.findByRole('heading', { name: 'Rechnungspruefung', level: 1 });
    expect(aufrufe.some((a) => a.methode === 'POST' && a.url.endsWith('/bewertungen'))).toBe(true);
  });

  it('erklaert, warum der schnelle Durchlauf keine K-Klassen liefert', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: {
          naechste_frage: null,
          abgeschlossen: true,
          verboten: false,
          vollstaendig: false,
          vorschau: {
            tier: 3,
            profil: { ki: 0, ds: 3, mb: 0, it: 0, rg: 0, ur: 0 },
            ausgeloeste_k_klassen: [],
            vollstaendig: false,
          },
        },
      },
    ]);
    zeichne('/de/prozesse/p-1/bewertung');
    await userEvent.click(
      await screen.findByRole('button', { name: 'Schnell — endet beim ersten Tier-3-Treffer' }),
    );
    expect(await screen.findByTestId('tier')).toHaveTextContent('3');
    expect(
      screen.getByText('Der schnelle Durchlauf endet vorzeitig und liefert deshalb keine K-Klassen.'),
    ).toBeInTheDocument();
    expect(screen.queryByTestId('k-klassen')).toBeNull();
  });

  it('meldet den Verbotstatbestand und zeigt kein Ergebnis', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: {
          naechste_frage: null,
          abgeschlossen: true,
          verboten: true,
          vollstaendig: false,
          vorschau: null,
        },
      },
    ]);
    zeichne('/de/prozesse/p-1/bewertung');
    await userEvent.click(
      await screen.findByRole('button', { name: 'Schnell — endet beim ersten Tier-3-Treffer' }),
    );
    expect(
      await screen.findByRole('heading', { name: 'Verbotene KI-Praxis' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('EU AI Act');
    expect(screen.queryByTestId('tier')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Bewertung speichern' })).toBeNull();
  });

  it('erlaubt einen Neustart des Durchlaufs', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: {
          naechste_frage: KI_FRAGE,
          abgeschlossen: false,
          verboten: false,
          vollstaendig: true,
          vorschau: null,
        },
      },
    ]);
    zeichne('/de/prozesse/p-1/bewertung');
    await userEvent.click(
      await screen.findByRole('button', { name: 'Schnell — endet beim ersten Tier-3-Treffer' }),
    );
    await screen.findByTestId('frage');
    await userEvent.click(screen.getByRole('button', { name: 'Von vorn beginnen' }));
    expect(await screen.findByText('Wie möchten Sie den Baum durchlaufen?')).toBeInTheDocument();
  });

  it('meldet einen Serverfehler', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        status: 403,
        koerper: { detail: 'Bewerten darf nur der Prozess-Owner' },
      },
    ]);
    zeichne('/de/prozesse/p-1/bewertung');
    await userEvent.click(
      await screen.findByRole('button', { name: 'Schnell — endet beim ersten Tier-3-Treffer' }),
    );
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Bewerten darf nur der Prozess-Owner',
    );
  });

  it('meldet einen Fehler beim Speichern', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: {
          naechste_frage: null,
          abgeschlossen: true,
          verboten: false,
          vollstaendig: true,
          vorschau: { tier: 1, profil: {}, ausgeloeste_k_klassen: ['K1'], vollstaendig: true },
        },
      },
      {
        pfad: '/api/v1/prozesse/p-1/bewertungen',
        methode: 'POST',
        status: 422,
        koerper: { detail: 'Durchlauf unvollstaendig' },
      },
    ]);
    zeichne('/de/prozesse/p-1/bewertung');
    await userEvent.click(
      await screen.findByRole('button', { name: 'Vollständig — alle sechs Schritte, mit K-Klassen' }),
    );
    await userEvent.click(await screen.findByRole('button', { name: 'Bewertung speichern' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Durchlauf unvollstaendig');
  });
});

describe('Bewertungshistorie im Prozessdetail', () => {
  it('zeigt einen Hinweis, solange keine Bewertung vorliegt', async () => {
    fetchAttrappe(grundrouten());
    zeichne('/de/prozesse/p-1');
    expect(
      await screen.findByText('Für diesen Prozess liegt noch keine Bewertung vor.'),
    ).toBeInTheDocument();
  });

  it('listet alle Bewertungen, neueste zuerst', async () => {
    fetchAttrappe(
      grundrouten([
        bewertung(),
        bewertung({
          id: 'b-0',
          ds_stufe: 1,
          mb_stufe: 0,
          it_stufe: 0,
          rg_stufe: 0,
          ur_stufe: 0,
          tier: 1,
          ausgeloeste_k_klassen: ['K1', 'K2'],
          gueltig_bis: null,
          bewertet_am: '2026-01-01T10:00:00Z',
        }),
      ]),
    );
    zeichne('/de/prozesse/p-1');
    await screen.findByRole('heading', { name: 'Bewertungshistorie' });
    expect(screen.getByText('KI0-DS3-MB1-IT1-RG2-UR2')).toBeInTheDocument();
    expect(screen.getByText('KI0-DS1-MB0-IT0-RG0-UR0')).toBeInTheDocument();
    expect(screen.getByText('2027-09-01')).toBeInTheDocument();
  });

  it('kennzeichnet einen schnellen Durchlauf', async () => {
    fetchAttrappe(
      grundrouten([bewertung({ vollstaendig: false, ausgeloeste_k_klassen: [] })]),
    );
    zeichne('/de/prozesse/p-1');
    await screen.findByRole('heading', { name: 'Bewertungshistorie' });
    expect(screen.getByText(/\(schnell\)/)).toBeInTheDocument();
  });
});
