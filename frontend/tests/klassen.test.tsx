/**
 * Anforderungsklassen, Technologiematrix und Befundkarte (AP-7).
 *
 * Geprüft wird die zweite Übersetzungsstufe aus A.9.1 auf dem Bildschirm:
 * dass jede Klasse einen Namen und eine Auslöserbedingung trägt, dass die
 * Matrix beide Achsen zeigt und dass ein Befund sagt, was zu tun ist — nicht
 * nur, was der Fall ist.
 */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { Befund, Matrixfeld } from '@/api/typen';
import {
  ANFORDERUNGSKLASSEN,
  EINHEITEN,
  PROFIL,
  TECHNOLOGIEN,
  fetchAttrappe,
  klassenbefund,
  prozess,
  tool,
  zeichne,
  type Route,
} from './hilfen';

const GOVERNANCE = {
  ...PROFIL,
  rollen: [
    {
      id: 'rz-2',
      user_id: 'user-1',
      rolle: 'governance' as const,
      scope_typ: 'global' as const,
      scope_id: null,
    },
  ],
};

function matrixfeld(ueberschreibungen: Partial<Matrixfeld> = {}): Matrixfeld {
  return {
    technologie: 'apps-script',
    k_klasse: 'K1',
    bewertung: 'erfuellt',
    begruendung: 'Organisatorische Anforderung — sie hängt nicht an der Technologie.',
    geaendert_am: null,
    ...ueberschreibungen,
  };
}

/** Die volle Matrix: jede Technologie mal jede Klasse. */
const MATRIX: Matrixfeld[] = TECHNOLOGIEN.flatMap((technologie) =>
  ANFORDERUNGSKLASSEN.map((klasse) =>
    matrixfeld({
      technologie: technologie.schluessel,
      k_klasse: klasse.schluessel,
      bewertung:
        technologie.schluessel === 'appsheet' && klasse.schluessel === 'K5'
          ? 'nicht_erfuellbar'
          : technologie.schluessel === 'apps-script' && klasse.schluessel === 'K5'
            ? 'kompensierbar'
            : 'erfuellt',
      begruendung:
        klasse.schluessel === 'K5'
          ? 'Die Plattform kennt nur ihr eigenes Freigabemodell.'
          : 'Organisatorische Anforderung — sie hängt nicht an der Technologie.',
    }),
  ),
);

function klassenrouten(profil = PROFIL, zusatz: Route[] = []): Route[] {
  return [
    ...zusatz,
    { pfad: '/api/v1/auth/me', koerper: profil },
    { pfad: '/api/v1/technologiematrix', koerper: MATRIX },
  ];
}

function befund(ueberschreibungen: Partial<Befund> = {}): Befund {
  return {
    tool_id: 'tool-1',
    tool_name: 'Rechnungs-Skript',
    technologie: 'apps-script',
    k_klasse: 'K5',
    art: 'kompensation_fehlt',
    begruendung: 'Ein Skript hat kein eigenes Rechtekonzept.',
    massnahme: '',
    offen: true,
    ...ueberschreibungen,
  };
}

function toolrouten(zusatz: Route[] = []): Route[] {
  return [
    ...zusatz,
    { pfad: '/api/v1/auth/me', koerper: PROFIL },
    { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    { pfad: '/api/v1/prozesse', koerper: [prozess()] },
    { pfad: '/api/v1/tools/tool-1/compliance', koerper: [] },
    { pfad: '/api/v1/tools/tool-1', koerper: tool() },
  ];
}

describe('Anforderungsklassen (A.9.2)', () => {
  it('nennt jede Klasse mit Name, Zweck und Auslöserbedingung', async () => {
    fetchAttrappe(klassenrouten());
    zeichne('/de/klassen');
    const zeile = await screen.findByTestId('klasse-K5');
    expect(zeile).toHaveTextContent('K5 — Anforderungsklasse 5');
    expect(zeile).toHaveTextContent('Was bei K5 zu tun ist');
    expect(zeile).toHaveTextContent('Ausgelöst: Bedingung für K5.');
    expect(screen.getAllByTestId(/^klasse-K/)).toHaveLength(10);
  });

  it('meldet einen Ladefehler', async () => {
    fetchAttrappe([
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      { pfad: '/api/v1/anforderungsklassen', status: 500, koerper: {} },
    ]);
    zeichne('/de/klassen');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});

describe('Technologiematrix (Teil C.1)', () => {
  async function zurMatrix(routen: Route[]) {
    fetchAttrappe(routen);
    zeichne('/de/klassen');
    await screen.findByTestId('klasse-K1');
    await userEvent.click(screen.getByRole('button', { name: 'Matrix' }));
  }

  it('zeigt beide Achsen mit Symbol und Wort', async () => {
    await zurMatrix(klassenrouten());
    // Spalten: die Technologien mit ihrem Namen, nicht mit ihrem Schlüssel.
    expect(screen.getByRole('columnheader', { name: 'AppSheet' })).toBeInTheDocument();
    expect(screen.getByRole('rowheader', { name: /K5/ })).toBeInTheDocument();

    const zelle = screen.getByTestId('matrix-appsheet-K5');
    expect(zelle).toHaveTextContent('Nicht erfüllbar');
    expect(screen.getByTestId('matrix-apps-script-K5')).toHaveTextContent('Kompensierbar');
    expect(screen.getByTestId('matrix-apps-script-K1')).toHaveTextContent('Erfüllt');
  });

  it('sperrt die Pflege ohne Governance-Rolle', async () => {
    await zurMatrix(klassenrouten());
    expect(
      screen.getByText('Ansicht ohne Änderungsrecht: die Matrix pflegt die Governance-Rolle.'),
    ).toBeInTheDocument();
    expect(within(screen.getByTestId('matrix-appsheet-K5')).queryByRole('button')).toBeNull();
  });

  it('pflegt ein Feld mit Pflichtbegründung', async () => {
    const { aufrufe } = fetchAttrappe(
      klassenrouten(GOVERNANCE, [
        {
          pfad: '/api/v1/technologiematrix/apps-script/K5',
          methode: 'PUT',
          koerper: matrixfeld({
            k_klasse: 'K5',
            bewertung: 'nicht_erfuellbar',
            begruendung: 'Neu bewertet.',
          }),
        },
      ]),
    );
    zeichne('/de/klassen');
    await screen.findByTestId('klasse-K1');
    await userEvent.click(screen.getByRole('button', { name: 'Matrix' }));
    await userEvent.click(within(screen.getByTestId('matrix-apps-script-K5')).getByRole('button'));

    // Ohne Begründung geht nichts: das Feld entscheidet über einen Betrieb.
    await userEvent.clear(screen.getByLabelText('Begründung'));
    expect(screen.getByTestId('matrix-sichern')).toBeDisabled();

    await userEvent.selectOptions(screen.getByLabelText('Bewertung'), 'nicht_erfuellbar');
    await userEvent.type(screen.getByLabelText('Begründung'), 'Neu bewertet.');
    await userEvent.click(screen.getByTestId('matrix-sichern'));

    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'PUT')?.koerper).toEqual({
        bewertung: 'nicht_erfuellbar',
        begruendung: 'Neu bewertet.',
      }),
    );
    expect(screen.getByTestId('matrix-apps-script-K5')).toHaveTextContent('Nicht erfüllbar');
  });

  it('meldet eine abgelehnte Änderung', async () => {
    fetchAttrappe(
      klassenrouten(GOVERNANCE, [
        {
          pfad: '/api/v1/technologiematrix/apps-script/K5',
          methode: 'PUT',
          status: 403,
          koerper: { detail: 'Die Technologiematrix pflegt die Governance-Rolle' },
        },
      ]),
    );
    zeichne('/de/klassen');
    await screen.findByTestId('klasse-K1');
    await userEvent.click(screen.getByRole('button', { name: 'Matrix' }));
    await userEvent.click(within(screen.getByTestId('matrix-apps-script-K5')).getByRole('button'));
    await userEvent.click(screen.getByTestId('matrix-sichern'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Governance-Rolle');
  });
});

describe('Befundkarte am Tool (A.9.3)', () => {
  it('sagt bei einem Ausschluss, was zu entscheiden ist', async () => {
    fetchAttrappe(
      toolrouten([
        {
          pfad: /\/klassenbefund$/,
          koerper: klassenbefund({
            technologie: 'appsheet',
            k_klassen: ['K5'],
            befunde: [befund({ art: 'ausschluss', technologie: 'appsheet' })],
            ausschluss: true,
            offen: 1,
          }),
        },
      ]),
    );
    zeichne('/de/tools/tool-1');
    const zeile = await screen.findByTestId('befund-K5');
    expect(zeile).toHaveTextContent('K5 — Anforderungsklasse 5');
    expect(zeile).toHaveTextContent('Ausschluss');
    expect(zeile).toHaveTextContent('diese Technologie kann die Klasse nicht tragen');
    expect(zeile).toHaveTextContent('Ein Skript hat kein eigenes Rechtekonzept.');
    // Ein Ausschluss ist nicht kompensierbar — es gibt keinen Knopf dafür.
    expect(screen.queryByTestId('kompensieren-K5')).not.toBeInTheDocument();
  });

  it('verlangt bei einem kompensierbaren Fall eine Maßnahme', async () => {
    const { aufrufe } = fetchAttrappe(
      toolrouten([
        {
          pfad: /\/klassenbefund$/,
          koerper: (aufruf: number) =>
            klassenbefund({
              k_klassen: ['K5'],
              befunde: [
                aufruf === 1
                  ? befund()
                  : befund({
                      art: 'kompensiert',
                      massnahme: 'Ablagerechte geregelt.',
                      offen: false,
                    }),
              ],
              offen: aufruf === 1 ? 1 : 0,
            }),
        },
        {
          pfad: '/api/v1/tools/tool-1/kompensationen/K5',
          methode: 'PUT',
          koerper: { id: 'kp-1' },
        },
      ]),
    );
    zeichne('/de/tools/tool-1');
    expect(await screen.findByTestId('befund-K5')).toHaveTextContent('Maßnahme fehlt');
    expect(screen.getByText('Eine offen')).toBeInTheDocument();

    await userEvent.click(screen.getByTestId('kompensieren-K5'));
    expect(screen.getByTestId('kompensation-sichern')).toBeDisabled();
    await userEvent.type(
      screen.getByLabelText(/Kompensierende Maßnahme/),
      'Ablagerechte geregelt.',
    );
    await userEvent.click(screen.getByTestId('kompensation-sichern'));

    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'PUT')?.koerper).toEqual({
        massnahme: 'Ablagerechte geregelt.',
      }),
    );
    await waitFor(() =>
      expect(screen.getByTestId('befund-K5')).toHaveTextContent('Kompensiert'),
    );
    expect(screen.getByTestId('befund-K5')).toHaveTextContent('Maßnahme: Ablagerechte geregelt.');
  });

  it('nennt eine fehlende Technologie als ungeprüft', async () => {
    fetchAttrappe(
      toolrouten([
        {
          pfad: /\/klassenbefund$/,
          koerper: klassenbefund({
            technologie: null,
            k_klassen: ['K1'],
            befunde: [
              befund({ k_klasse: 'K1', art: 'ungeprueft', technologie: null, begruendung: '' }),
            ],
            offen: 1,
          }),
        },
      ]),
    );
    zeichne('/de/tools/tool-1');
    const zeile = await screen.findByTestId('befund-K1');
    expect(zeile).toHaveTextContent('Ungeprüft');
    expect(zeile).toHaveTextContent('die Technologie hinterlegen');
  });

  it('sagt, wenn das Tool noch keine Klassen erbt', async () => {
    fetchAttrappe(toolrouten());
    zeichne('/de/tools/tool-1');
    expect(
      await screen.findByText(
        'Dieses Tool-Objekt erbt noch keine Klassen — dafür braucht es eine Prozesskante mit Bewertung.',
      ),
    ).toBeInTheDocument();
  });

  it('meldet einen abgelehnten Kompensationsversuch', async () => {
    fetchAttrappe(
      toolrouten([
        {
          pfad: /\/klassenbefund$/,
          koerper: klassenbefund({ k_klassen: ['K5'], befunde: [befund()], offen: 1 }),
        },
        {
          pfad: '/api/v1/tools/tool-1/kompensationen/K5',
          methode: 'PUT',
          status: 422,
          koerper: { detail: 'Eine Kompensation ohne Beschreibung ist keine' },
        },
      ]),
    );
    zeichne('/de/tools/tool-1');
    await userEvent.click(await screen.findByTestId('kompensieren-K5'));
    await userEvent.type(screen.getByLabelText(/Kompensierende Maßnahme/), 'Naja.');
    await userEvent.click(screen.getByTestId('kompensation-sichern'));
    expect(await screen.findByRole('alert')).toHaveTextContent('ohne Beschreibung');
  });
});

describe('Befunde am Prozessobjekt (V-KLA-04)', () => {
  function prozessrouten(befunde: unknown, zusatz: Route[] = []): Route[] {
    return [
      ...zusatz,
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      { pfad: /\/prozesse\/p-1\/klassenbefund$/, koerper: befunde },
      { pfad: '/api/v1/prozesse/p-1/bewertungen', koerper: [] },
      { pfad: '/api/v1/prozesse/p-1', koerper: prozess({ tool_objekt_ids: ['tool-1'] }) },
      { pfad: '/api/v1/prozesse', koerper: [] },
      { pfad: '/api/v1/tools', koerper: [tool()] },
    ];
  }

  it('führt einen Ausschluss vom Prozess zum Tool', async () => {
    fetchAttrappe(
      prozessrouten([
        klassenbefund({
          k_klassen: ['K5'],
          befunde: [befund({ art: 'ausschluss' })],
          ausschluss: true,
          offen: 1,
        }),
      ]),
    );
    zeichne('/de/prozesse/p-1');
    const zeile = await screen.findByTestId('prozessbefund-tool-1');
    expect(zeile).toHaveTextContent('Rechnungs-Skript');
    expect(zeile).toHaveTextContent('K5: Ausschluss');
    expect(zeile).toHaveAttribute('href', '/de/tools/tool-1');
  });

  it('sagt, wenn alle Klassen getragen sind', async () => {
    fetchAttrappe(prozessrouten([klassenbefund({ k_klassen: ['K1'] })]));
    zeichne('/de/prozesse/p-1');
    expect(
      await screen.findByText('Alle ausgelösten Klassen sind getragen.'),
    ).toBeInTheDocument();
  });

  it('zählt offene Fälle über alle Werkzeuge', async () => {
    fetchAttrappe(
      prozessrouten([
        klassenbefund({ k_klassen: ['K5'], befunde: [befund()], offen: 1 }),
        klassenbefund({
          tool_id: 'tool-2',
          tool_name: 'Zweitwerkzeug',
          k_klassen: ['K8'],
          befunde: [befund({ k_klasse: 'K8' })],
          offen: 1,
        }),
      ]),
    );
    zeichne('/de/prozesse/p-1');
    expect(await screen.findByText('2 offen')).toBeInTheDocument();
  });

  it('sagt, wenn noch kein Tool am Prozess hängt', async () => {
    fetchAttrappe(prozessrouten([]));
    zeichne('/de/prozesse/p-1');
    expect(
      await screen.findByText('An diesem Prozessobjekt hängt noch kein Tool-Objekt.'),
    ).toBeInTheDocument();
  });

  it('meldet einen Ladefehler', async () => {
    fetchAttrappe(prozessrouten(undefined, [
      { pfad: /\/prozesse\/p-1\/klassenbefund$/, status: 500, koerper: {} },
    ]));
    zeichne('/de/prozesse/p-1');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
