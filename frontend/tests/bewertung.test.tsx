/**
 * Bewertungs-Wizard in der Oberflaeche (Architektur 8.2, 9.1, Leitdokument A.8).
 *
 * Der Schwerpunkt liegt auf dem, was AP-4 hinzugefuegt hat: der Vorschlag
 * neben der Frage, die Begruendungspflicht bei Abweichung, der Weg zurueck und
 * die Ergebnisseite mit Klassennamen und Auflagen.
 */

import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { Beleg, Bewertung, Ergebnis, Frage } from '@/api/typen';
import { EINHEITEN, PROFIL, fetchAttrappe, prozess, zeichne, type Route } from './hilfen';

function frage(
  id: string,
  nummer: number,
  block: string,
  titel: string,
  text: string,
  vorschlag: boolean | null = null,
  belege: Beleg[] = [],
): Frage {
  return { id, text, block, block_titel: titel, nummer, anzahl_bloecke: 6, vorschlag, belege };
}

const KI_FRAGE = frage('1a', 1, 'ki', 'Künstliche Intelligenz', 'Setzt der Prozess KI ein?');
const DS_FRAGE = frage('2a', 2, 'ds', 'Datenschutz', 'Besondere Kategorien?');
const DS_MIT_VORSCHLAG = frage('2a', 2, 'ds', 'Datenschutz', 'Besondere Kategorien?', true, [
  {
    text: 'Datenobjekt „Entgeltdaten“ trägt die Kategorie besondere Kategorie.',
    quelle: 'datenobjekt',
  },
]);

const ERGEBNIS: Ergebnis = {
  tier: 3,
  profil: { ki: 0, ds: 3, mb: 1, it: 1, rg: 2, ur: 2 },
  ausgeloeste_k_klassen: ['K1', 'K4'],
  klassen: [
    {
      kennung: 'K1',
      name: 'Dokumentationspflicht des Prozessobjekts',
      erklaerung: 'Im Verzeichnis fuehren.',
    },
    { kennung: 'K4', name: 'Datenschutz-Folgenabschätzung', erklaerung: 'Nach Art. 35 DSGVO.' },
  ],
  auflagen: [
    'Registrierung im Verzeichnis der Prozessobjekte.',
    'Freigabe durch die Governance-Rolle.',
  ],
};

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
    ausgeloeste_k_klassen: ['K1', 'K2', 'K3', 'K4', 'K5', 'K7', 'K8', 'K9'],
    antworten: {},
    vorschlaege: {},
    abweichungen: {},
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
    { pfad: '/api/v1/tools', koerper: [] },
    { pfad: '/api/v1/prozesse/p-1', koerper: prozess() },
  ];
}

/** Der Wizard beginnt ohne Vorschaltbildschirm — seit E-64 gibt es nichts zu wählen. */
async function starte() {
  zeichne('/de/prozesse/p-1/bewertung');
}

describe('Wizard', () => {
  it('beginnt ohne Vorschaltbildschirm bei der ersten Frage', async () => {
    // E-64: es gibt nur einen Durchlauf. Ein Bildschirm, auf dem nichts zu
    // waehlen ist, waere ein Klick ohne Entscheidung.
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: {
          naechste_frage: KI_FRAGE,
          abgeschlossen: false,
          verboten: false,
          vorschau: null,
        },
      },
    ]);
    zeichne('/de/prozesse/p-1/bewertung');
    expect(await screen.findByTestId('frage')).toBeInTheDocument();
  });

  it('zeigt eine Frage pro Bildschirm mit zwei Antwortflaechen und keinen Zwischenstand', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: {
          naechste_frage: KI_FRAGE,
          abgeschlossen: false,
          verboten: false,
          vorschau: null,
        },
      },
    ]);
    await starte();

    expect(await screen.findByTestId('frage')).toHaveTextContent('Setzt der Prozess KI ein?');
    expect(screen.getByText('Schritt 1 von 6 — Künstliche Intelligenz')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Ja' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Nein' })).toBeInTheDocument();
    // Kein Tier, kein Profil, solange der Durchlauf laeuft.
    expect(screen.queryByTestId('tier')).toBeNull();
    expect(screen.queryByTestId('profil')).toBeNull();

    const erster = aufrufe.find((a) => a.url.includes('/bewertung/wizard'));
    expect(erster?.koerper).toEqual({
      antworten: {},
      begruendungen: {},
    });
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
          vorschau: null,
        }),
      },
    ]);
    await starte();
    await screen.findByTestId('frage');
    await userEvent.click(screen.getByRole('button', { name: 'Nein' }));

    await waitFor(() =>
      expect(screen.getByTestId('frage')).toHaveTextContent('Besondere Kategorien?'),
    );
    const letzter = aufrufe.filter((a) => a.url.includes('/bewertung/wizard')).at(-1);
    expect(letzter?.koerper).toEqual({
      antworten: { '1a': false },
      begruendungen: {},
    });
  });

  // --- Vorschlag und Abweichung (Leitdokument A.8.4) ---------------------

  it('zeigt den Vorschlag mit seinem Beleg und der Quelle', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: {
          naechste_frage: DS_MIT_VORSCHLAG,
          abgeschlossen: false,
          verboten: false,
          vorschau: null,
        },
      },
    ]);
    await starte();

    const vorschlag = await screen.findByTestId('vorschlag');
    expect(vorschlag).toHaveAttribute('data-wert', 'true');
    expect(vorschlag).toHaveTextContent('Vorschlag aus Ihren Daten:');
    expect(vorschlag).toHaveTextContent('Entgeltdaten');
    expect(vorschlag).toHaveTextContent('Datenobjekt');
  });

  it('nennt es offen, wo die Daten nichts hergeben', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: {
          naechste_frage: frage('2a', 2, 'ds', 'Datenschutz', 'Besondere Kategorien?', null, [
            { text: 'Kein Datenobjekt traegt eine besondere Kategorie.', quelle: 'datenobjekt' },
          ]),
          abgeschlossen: false,
          verboten: false,
          vorschau: null,
        },
      },
    ]);
    await starte();

    const vorschlag = await screen.findByTestId('vorschlag');
    expect(vorschlag).toHaveAttribute('data-wert', 'offen');
    expect(vorschlag).toHaveTextContent('geben die vorhandenen Daten nichts her');
  });

  it('geht ohne Nachfrage weiter, wenn die Antwort dem Vorschlag folgt', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: (nummer: number) => ({
          naechste_frage: nummer === 1 ? DS_MIT_VORSCHLAG : KI_FRAGE,
          abgeschlossen: false,
          verboten: false,
          vorschau: null,
        }),
      },
    ]);
    await starte();
    await screen.findByTestId('vorschlag');
    await userEvent.click(screen.getByRole('button', { name: 'Ja' }));

    await waitFor(() =>
      expect(screen.getByTestId('frage')).toHaveTextContent('Setzt der Prozess KI ein?'),
    );
    expect(screen.queryByTestId('begruendung')).toBeNull();
    const letzter = aufrufe.filter((a) => a.url.includes('/bewertung/wizard')).at(-1);
    expect(letzter?.koerper).toMatchObject({ antworten: { '2a': true }, begruendungen: {} });
  });

  it('haelt bei einer abweichenden Antwort an und verlangt eine Begruendung', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: (nummer: number) => ({
          naechste_frage: nummer === 1 ? DS_MIT_VORSCHLAG : KI_FRAGE,
          abgeschlossen: false,
          verboten: false,
          vorschau: null,
        }),
      },
    ]);
    await starte();
    await screen.findByTestId('vorschlag');
    await userEvent.click(screen.getByRole('button', { name: 'Nein' }));

    const feld = await screen.findByTestId('begruendung');
    expect(feld).toHaveTextContent('Ihre Antwort widerspricht');
    const weiter = screen.getByRole('button', { name: 'Weiter' });
    expect(weiter).toBeDisabled();
    // Ohne Begruendung ist nichts abgeschickt worden.
    expect(aufrufe.filter((a) => a.url.includes('/bewertung/wizard'))).toHaveLength(1);

    await userEvent.type(
      screen.getByLabelText('Begründung der Abweichung'),
      'Nur als Aggregat eingebunden.',
    );
    expect(weiter).toBeEnabled();
    await userEvent.click(weiter);

    await waitFor(() =>
      expect(screen.getByTestId('frage')).toHaveTextContent('Setzt der Prozess KI ein?'),
    );
    const letzter = aufrufe.filter((a) => a.url.includes('/bewertung/wizard')).at(-1);
    expect(letzter?.koerper).toMatchObject({
      antworten: { '2a': false },
      begruendungen: { '2a': 'Nur als Aggregat eingebunden.' },
    });
  });

  it('laesst die Abweichung zuruecknehmen', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: {
          naechste_frage: DS_MIT_VORSCHLAG,
          abgeschlossen: false,
          verboten: false,
          vorschau: null,
        },
      },
    ]);
    await starte();
    await screen.findByTestId('vorschlag');
    await userEvent.click(screen.getByRole('button', { name: 'Nein' }));
    await screen.findByTestId('begruendung');

    await userEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));
    expect(screen.queryByTestId('begruendung')).toBeNull();
    expect(screen.getByTestId('frage')).toHaveTextContent('Besondere Kategorien?');
  });

  // --- Zurueck und Abbruch ----------------------------------------------

  it('geht einen Schritt zurueck und nimmt die letzte Antwort mit', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: (nummer: number) => ({
          naechste_frage: nummer === 1 || nummer === 3 ? KI_FRAGE : DS_FRAGE,
          abgeschlossen: false,
          verboten: false,
          vorschau: null,
        }),
      },
    ]);
    await starte();
    await screen.findByTestId('frage');
    await userEvent.click(screen.getByRole('button', { name: 'Nein' }));
    await waitFor(() =>
      expect(screen.getByTestId('frage')).toHaveTextContent('Besondere Kategorien?'),
    );

    await userEvent.click(screen.getByTestId('bewertung-zurueck'));
    await waitFor(() =>
      expect(screen.getByTestId('frage')).toHaveTextContent('Setzt der Prozess KI ein?'),
    );
    const letzter = aufrufe.filter((a) => a.url.includes('/bewertung/wizard')).at(-1);
    expect(letzter?.koerper).toMatchObject({ antworten: {} });
  });

  it('fuehrt vom ersten Schritt zurueck zum Prozessobjekt', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: {
          naechste_frage: KI_FRAGE,
          abgeschlossen: false,
          verboten: false,
          vorschau: null,
        },
      },
    ]);
    await starte();
    await screen.findByTestId('frage');
    await userEvent.click(screen.getByTestId('bewertung-zurueck'));
    // Vor der ersten Frage gibt es kein Zurueck mehr — nur den Weg hinaus.
    expect(
      await screen.findByRole('heading', { name: 'Rechnungspruefung', level: 1 }),
    ).toBeInTheDocument();
  });

  it('fragt vor dem Verwerfen zurueck', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: {
          naechste_frage: KI_FRAGE,
          abgeschlossen: false,
          verboten: false,
          vorschau: null,
        },
      },
    ]);
    await starte();
    await screen.findByTestId('frage');
    await userEvent.click(screen.getByRole('button', { name: 'Bewertung abbrechen' }));

    const blatt = await screen.findByRole('dialog');
    expect(blatt).toHaveTextContent('Bewertung verwerfen?');
    await userEvent.click(screen.getByRole('button', { name: 'Weiterbewerten' }));
    expect(screen.queryByRole('dialog')).toBeNull();

    await userEvent.click(screen.getByRole('button', { name: 'Bewertung abbrechen' }));
    await userEvent.click(await screen.findByTestId('abbruch-verwerfen'));
    await screen.findByRole('heading', { name: 'Rechnungspruefung', level: 1 });
  });

  // --- Ergebnis ----------------------------------------------------------

  it('zeigt Tier, Profil, Klassennamen und Auflagen erst am Ende und speichert', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: {
          naechste_frage: null,
          abgeschlossen: true,
          verboten: false,
          vorschau: ERGEBNIS,
        },
      },
      {
        pfad: '/api/v1/prozesse/p-1/bewertungen',
        methode: 'POST',
        status: 201,
        koerper: { bewertung: bewertung(), alarm: null },
      },
    ]);
    await starte();

    expect(await screen.findByTestId('tier')).toHaveTextContent('3');
    expect(screen.getByTestId('profil')).toHaveTextContent('KI0-DS3-MB1-IT1-RG2-UR2');
    const klassen = screen.getByTestId('k-klassen');
    expect(klassen).toHaveTextContent('Datenschutz-Folgenabschätzung');
    expect(klassen).toHaveTextContent('Nach Art. 35 DSGVO.');
    expect(screen.getByTestId('auflagen')).toHaveTextContent('Registrierung im Verzeichnis');

    await userEvent.click(screen.getByTestId('bewertung-speichern'));
    await screen.findByRole('heading', { name: 'Rechnungspruefung', level: 1 });
    expect(aufrufe.some((a) => a.methode === 'POST' && a.url.endsWith('/bewertungen'))).toBe(true);
  });

  it('zeigt die begruendeten Abweichungen am Ergebnis', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: (nummer: number) =>
          nummer === 1
            ? {
                naechste_frage: DS_MIT_VORSCHLAG,
                abgeschlossen: false,
                verboten: false,
                vorschau: null,
              }
            : {
                naechste_frage: null,
                abgeschlossen: true,
                verboten: false,
                vorschau: ERGEBNIS,
              },
      },
    ]);
    await starte();
    await screen.findByTestId('vorschlag');
    await userEvent.click(screen.getByRole('button', { name: 'Nein' }));
    await userEvent.type(
      await screen.findByLabelText('Begründung der Abweichung'),
      'Nur als Aggregat eingebunden.',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Weiter' }));

    await screen.findByTestId('tier');
    expect(screen.getByRole('heading', { name: 'Begründete Abweichungen' })).toBeInTheDocument();
    expect(screen.getByText('Nur als Aggregat eingebunden.')).toBeInTheDocument();
  });

  // --- Verbotstatbestand -------------------------------------------------

  it('meldet den Verbotstatbestand als eigenen Ausgang und zeigt kein Ergebnis', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/bewertung/wizard',
        methode: 'POST',
        koerper: {
          naechste_frage: null,
          abgeschlossen: true,
          verboten: true,
          vorschau: null,
        },
      },
    ]);
    await starte();
    expect(await screen.findByRole('heading', { name: 'Verbotene KI-Praxis' })).toBeInTheDocument();
    expect(screen.getByTestId('verbotstatbestand')).toHaveTextContent('Governance und Recht');
    expect(screen.getByRole('alert')).toHaveTextContent('EU AI Act');
    expect(screen.queryByTestId('tier')).toBeNull();
    expect(screen.queryByTestId('bewertung-speichern')).toBeNull();
    expect(screen.getByTestId('alarm-ausloesen')).toBeInTheDocument();
  });

  // --- Fehler ------------------------------------------------------------

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
    await starte();
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
          vorschau: { ...ERGEBNIS, tier: 1 },
        },
      },
      {
        pfad: '/api/v1/prozesse/p-1/bewertungen',
        methode: 'POST',
        status: 422,
        koerper: { detail: 'Durchlauf unvollstaendig' },
      },
    ]);
    await starte();
    await userEvent.click(await screen.findByTestId('bewertung-speichern'));
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
});
