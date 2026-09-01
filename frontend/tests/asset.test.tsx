/**
 * Asset-Management in der Oberflaeche (Architektur 8.3).
 */

import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { DatenObjekt, Geerbt, ToolObjekt } from '@/api/typen';
import { EINHEITEN, PROFIL, fetchAttrappe, prozess, zeichne, type Route } from './hilfen';

function geerbt(ueberschreibungen: Partial<Geerbt> = {}): Geerbt {
  return {
    kritikalitaet: 0,
    reichweite: null,
    tier: null,
    mitbestimmung_flag: false,
    k_klassen: [],
    quelle_prozess_ids: [],
    ...ueberschreibungen,
  };
}

function tool(ueberschreibungen: Partial<ToolObjekt> = {}): ToolObjekt {
  return {
    id: 'tool-1',
    name: 'Rechnungs-Skript',
    beschreibung: '',
    technologie: 'apps-script',
    kategorie: null,
    technischer_owner_user_id: null,
    organisationseinheit_id: 'org-de',
    herkunft: 'manuell',
    quelle: null,
    externe_id: null,
    status: 'bestaetigt',
    metadaten: {},
    letzte_aktivitaet_am: null,
    prozessobjekt_ids: [],
    geerbt: geerbt(),
    schreibgeschuetzte_felder: [],
    ...ueberschreibungen,
  };
}

function datenobjekt(ueberschreibungen: Partial<DatenObjekt> = {}): DatenObjekt {
  return {
    id: 'do-1',
    name: 'Kreditorenstamm',
    beschreibung: '',
    kategorie: null,
    owner_user_id: null,
    fachbereich_id: null,
    herkunft: 'manuell',
    quelle: null,
    externe_id: null,
    status: 'bestaetigt',
    metadaten: {},
    schreibgeschuetzte_felder: [],
    ...ueberschreibungen,
  };
}

function grundrouten(): Route[] {
  return [
    { pfad: '/api/v1/auth/me', koerper: PROFIL },
    { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    { pfad: /\/bewertungen$/, koerper: [] },
    { pfad: /\/compliance$/, koerper: [] },
  ];
}

describe('Tool-Liste', () => {
  it('zeigt einen Hinweis, wenn nichts erfasst ist', async () => {
    fetchAttrappe([...grundrouten(), { pfad: '/api/v1/tools', koerper: [] }]);
    zeichne('/de/tools');
    expect(
      await screen.findByText('In Ihrem Bereich ist noch kein Tool-Objekt erfasst.'),
    ).toBeInTheDocument();
  });

  it('listet Tools mit ihrer geerbten Einstufung', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/api/v1/tools',
        koerper: [tool({ geerbt: geerbt({ kritikalitaet: 3, tier: 3 }) })],
      },
    ]);
    zeichne('/de/tools');
    await screen.findByRole('heading', { name: 'Tool-Objekte' });
    const zeile = screen.getByRole('row', { name: /Rechnungs-Skript/ });
    expect(zeile).toHaveTextContent('Bestätigt');
    expect(zeile).toHaveTextContent('3');
  });

  it('legt ein Tool-Objekt an', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/tools', koerper: [] },
      {
        pfad: '/api/v1/tools',
        methode: 'POST',
        status: 201,
        koerper: tool({ name: 'Neues Tool' }),
      },
    ]);
    zeichne('/de/tools');
    await userEvent.type(await screen.findByLabelText('Tool-Objekt anlegen'), 'Neues Tool');
    await userEvent.click(screen.getByRole('button', { name: 'Speichern' }));
    await screen.findByRole('link', { name: 'Neues Tool' });
    expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({ name: 'Neues Tool' });
  });

  it('meldet einen Fehler beim Anlegen', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/tools', koerper: [] },
      {
        pfad: '/api/v1/tools',
        methode: 'POST',
        status: 403,
        koerper: { detail: 'Keine Berechtigung' },
      },
    ]);
    zeichne('/de/tools');
    await userEvent.type(await screen.findByLabelText('Tool-Objekt anlegen'), 'X');
    await userEvent.click(screen.getByRole('button', { name: 'Speichern' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Keine Berechtigung');
  });

  it('meldet einen Ladefehler', async () => {
    fetchAttrappe([...grundrouten(), { pfad: '/api/v1/tools', status: 500, koerper: {} }]);
    zeichne('/de/tools');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});

describe('Tool-Detail', () => {
  it('zeigt die geerbte Klassifikation als Maximum aller Kanten', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [prozess(), prozess({ id: 'p-2', name: 'Zweiter' })] },
      {
        pfad: '/api/v1/tools/tool-1',
        koerper: tool({
          prozessobjekt_ids: ['p-1', 'p-2'],
          geerbt: geerbt({
            kritikalitaet: 3,
            reichweite: 'extern',
            tier: 3,
            k_klassen: ['K1', 'K4'],
            quelle_prozess_ids: ['p-1', 'p-2'],
          }),
        }),
      },
    ]);
    zeichne('/de/tools/tool-1');
    expect(await screen.findByTestId('geerbt-kritikalitaet')).toHaveTextContent('3');
    expect(screen.getByTestId('geerbt-reichweite')).toHaveTextContent('extern');
    expect(screen.getByTestId('geerbt-tier')).toHaveTextContent('3');
    expect(screen.getByTestId('geerbt-k-klassen')).toHaveTextContent('K1, K4');
    expect(screen.getByRole('link', { name: 'Rechnungspruefung' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Zweiter' })).toBeInTheDocument();
  });

  it('verlangt bei einem importierten Tool erst die Bestaetigung', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      {
        pfad: '/api/v1/tools/tool-1',
        koerper: tool({
          herkunft: 'importiert',
          status: 'importiert_unbestaetigt',
          schreibgeschuetzte_felder: ['metadaten', 'name', 'technologie'],
        }),
      },
      {
        pfad: '/api/v1/tools/tool-1/bestaetigung',
        methode: 'POST',
        koerper: tool({ herkunft: 'importiert', status: 'bestaetigt' }),
      },
    ]);
    zeichne('/de/tools/tool-1');
    expect(await screen.findByTestId('status')).toHaveTextContent('Importiert, unbestätigt');
    expect(screen.getByText(/kann es nicht mit einem Prozess/)).toBeInTheDocument();
    // Vor der Bestaetigung gibt es keine Verknuepfungsmoeglichkeit.
    expect(screen.queryByLabelText('Mit Prozess verknüpfen')).toBeNull();

    await userEvent.click(screen.getByRole('button', { name: 'Bestätigen' }));
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('Bestätigt'));
    expect(await screen.findByLabelText('Mit Prozess verknüpfen')).toBeInTheDocument();
  });

  it('verknuepft und loest eine Prozesskante', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      { pfad: '/api/v1/tools/tool-1', koerper: tool() },
      {
        pfad: '/api/v1/tools/tool-1/prozesse',
        methode: 'POST',
        status: 201,
        koerper: tool({
          prozessobjekt_ids: ['p-1'],
          geerbt: geerbt({ kritikalitaet: 2, quelle_prozess_ids: ['p-1'] }),
        }),
      },
      {
        pfad: '/api/v1/tools/tool-1/prozesse/p-1',
        methode: 'DELETE',
        koerper: tool({ prozessobjekt_ids: [] }),
      },
    ]);
    zeichne('/de/tools/tool-1');
    await userEvent.selectOptions(await screen.findByLabelText('Mit Prozess verknüpfen'), 'p-1');
    await userEvent.click(screen.getByRole('button', { name: 'Mit Prozess verknüpfen' }));

    await waitFor(() => expect(screen.getByTestId('geerbt-kritikalitaet')).toHaveTextContent('2'));
    expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
      prozessobjekt_id: 'p-1',
    });

    await userEvent.click(screen.getByRole('button', { name: 'Lösen' }));
    await waitFor(() =>
      expect(screen.getByText('Dieses Tool-Objekt hängt an keinem Prozess.')).toBeInTheDocument(),
    );
  });

  it('meldet einen abgelehnten Verknuepfungsversuch', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      { pfad: '/api/v1/tools/tool-1', koerper: tool() },
      {
        pfad: '/api/v1/tools/tool-1/prozesse',
        methode: 'POST',
        status: 422,
        koerper: { detail: 'Diese Verknuepfung besteht bereits' },
      },
    ]);
    zeichne('/de/tools/tool-1');
    await userEvent.selectOptions(await screen.findByLabelText('Mit Prozess verknüpfen'), 'p-1');
    await userEvent.click(screen.getByRole('button', { name: 'Mit Prozess verknüpfen' }));
    expect(await screen.findByText(/besteht bereits/)).toBeInTheDocument();
  });

  it('meldet einen Ladefehler', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [] },
      { pfad: '/api/v1/tools/tool-1', status: 403, koerper: { detail: 'nein' } },
    ]);
    zeichne('/de/tools/tool-1');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});

describe('Datenobjekte', () => {
  it('zeigt einen Hinweis, wenn nichts erfasst ist', async () => {
    fetchAttrappe([...grundrouten(), { pfad: '/api/v1/datenobjekte', koerper: [] }]);
    zeichne('/de/datenobjekte');
    expect(
      await screen.findByText('In Ihrem Bereich ist noch kein Datenobjekt erfasst.'),
    ).toBeInTheDocument();
  });

  it('pflegt die Kategorie genau an einer Stelle', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/datenobjekte', koerper: [datenobjekt()] },
      {
        pfad: '/api/v1/datenobjekte/do-1',
        methode: 'PATCH',
        koerper: datenobjekt({ kategorie: 'mitarbeiterbezogen' }),
      },
    ]);
    zeichne('/de/datenobjekte');
    const wahl = await screen.findByLabelText('Kategorie — Kreditorenstamm');
    expect(wahl).toHaveValue('');
    await userEvent.selectOptions(wahl, 'mitarbeiterbezogen');
    await waitFor(() => expect(wahl).toHaveValue('mitarbeiterbezogen'));
    expect(aufrufe.find((a) => a.methode === 'PATCH')?.koerper).toEqual({
      kategorie: 'mitarbeiterbezogen',
    });
  });

  it('nimmt eine Kategorie wieder zurueck', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/api/v1/datenobjekte',
        koerper: [datenobjekt({ kategorie: 'intern' })],
      },
      { pfad: '/api/v1/datenobjekte/do-1', methode: 'PATCH', koerper: datenobjekt() },
    ]);
    zeichne('/de/datenobjekte');
    const wahl = await screen.findByLabelText('Kategorie — Kreditorenstamm');
    await userEvent.selectOptions(wahl, '');
    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'PATCH')?.koerper).toEqual({ kategorie: null }),
    );
  });

  it('legt ein Datenobjekt an', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/datenobjekte', koerper: [] },
      {
        pfad: '/api/v1/datenobjekte',
        methode: 'POST',
        status: 201,
        koerper: datenobjekt({ name: 'Neues Objekt' }),
      },
    ]);
    zeichne('/de/datenobjekte');
    await userEvent.type(await screen.findByLabelText('Datenobjekt anlegen'), 'Neues Objekt');
    await userEvent.click(screen.getByRole('button', { name: 'Speichern' }));
    expect(await screen.findByText('Neues Objekt')).toBeInTheDocument();
  });

  it('meldet einen abgelehnten Kategorisierungsversuch', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/datenobjekte', koerper: [datenobjekt()] },
      {
        pfad: '/api/v1/datenobjekte/do-1',
        methode: 'PATCH',
        status: 403,
        koerper: { detail: 'Keine Schreibberechtigung' },
      },
    ]);
    zeichne('/de/datenobjekte');
    await userEvent.selectOptions(
      await screen.findByLabelText('Kategorie — Kreditorenstamm'),
      'intern',
    );
    expect(await screen.findByRole('alert')).toHaveTextContent('Keine Schreibberechtigung');
  });

  it('meldet einen Ladefehler', async () => {
    fetchAttrappe([...grundrouten(), { pfad: '/api/v1/datenobjekte', status: 500, koerper: {} }]);
    zeichne('/de/datenobjekte');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('legt ein Datenobjekt trotz Fehler nicht doppelt an', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/datenobjekte', koerper: [] },
      {
        pfad: '/api/v1/datenobjekte',
        methode: 'POST',
        status: 403,
        koerper: { detail: 'Keine Berechtigung' },
      },
    ]);
    zeichne('/de/datenobjekte');
    await userEvent.type(await screen.findByLabelText('Datenobjekt anlegen'), 'X');
    await userEvent.click(screen.getByRole('button', { name: 'Speichern' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Keine Berechtigung');
  });
});

describe('Prozessdetail mit Assets', () => {
  it('zeigt die verknuepften Tool-Objekte', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse/p-1', koerper: prozess() },
      { pfad: '/api/v1/tools', koerper: [tool({ prozessobjekt_ids: ['p-1'] })] },
    ]);
    zeichne('/de/prozesse/p-1');
    await screen.findByRole('heading', { name: 'Verknüpfte Tool-Objekte' });
    expect(screen.getByRole('link', { name: 'Rechnungs-Skript' })).toBeInTheDocument();
  });

  it('zeigt einen Hinweis ohne Tool-Objekt', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse/p-1', koerper: prozess() },
      { pfad: '/api/v1/tools', koerper: [tool({ prozessobjekt_ids: ['p-9'] })] },
    ]);
    zeichne('/de/prozesse/p-1');
    expect(
      await screen.findByText('An diesem Prozess hängt noch kein Tool-Objekt.'),
    ).toBeInTheDocument();
  });
});
