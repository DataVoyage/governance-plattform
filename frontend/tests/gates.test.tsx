/**
 * Selbstverpflichtung und Gates in der Oberflaeche (Architektur 8.4, 8.5).
 */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { GateVorgang, Selbstverpflichtung } from '@/api/typen';
import { EINHEITEN, PROFIL, fetchAttrappe, prozess, zeichne, type Route } from './hilfen';

const AUSLOESER = [
  'neue_datenkategorie',
  'reichweitenerweiterung',
  'neues_externes_ziel',
  'ki_komponente_ergaenzt',
  'kritikalitaet_gestiegen',
];

const KATALOG = [
  {
    typ: 'prozesseigner',
    aussagen: [
      { id: 'P1', text: 'Das Prozessobjekt ist vollstaendig beschrieben.' },
      { id: 'P2', text: 'Die Bewertung wurde vollstaendig durchgefuehrt.' },
    ],
  },
  { typ: 'technischer_owner', aussagen: [{ id: 'T1', text: 'Das Tool laeuft im Rahmen.' }] },
];

function gate(ueberschreibungen: Partial<GateVorgang> = {}): GateVorgang {
  return {
    id: 'g-1',
    prozessobjekt_id: 'p-1',
    gate_typ: '1',
    ausloeser: null,
    begruendung: '',
    status: 'eingereicht',
    eingereicht_von: 'user-1',
    entschieden_von: null,
    entscheidungskommentar: '',
    entschieden_am: null,
    erstellt_am: '2026-09-01T10:00:00Z',
    ...ueberschreibungen,
  };
}

function selbstverpflichtung(
  ueberschreibungen: Partial<Selbstverpflichtung> = {},
): Selbstverpflichtung {
  return {
    id: 'sv-1',
    typ: 'prozesseigner',
    prozessobjekt_id: 'p-1',
    tool_objekt_id: null,
    aussagen: {},
    vollstaendig: true,
    abgegeben_von: 'user-1',
    abgegeben_am: '2026-09-01T10:00:00Z',
    gueltig_bis: '2027-09-01T10:00:00Z',
    erinnerung_gesendet_am: null,
    ...ueberschreibungen,
  };
}

function detailrouten(
  gates: GateVorgang[] = [],
  sv: Selbstverpflichtung[] = [],
): Route[] {
  return [
    { pfad: '/api/v1/auth/me', koerper: PROFIL },
    { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    { pfad: '/api/v1/prozesse/p-1', koerper: prozess() },
    { pfad: '/api/v1/prozesse/p-1/bewertungen', koerper: [] },
    { pfad: '/api/v1/prozesse/p-1/selbstverpflichtungen', koerper: sv },
    { pfad: '/api/v1/prozesse/p-1/gates', koerper: gates },
    { pfad: '/api/v1/gates/ausloeser', koerper: AUSLOESER },
    { pfad: '/api/v1/tools', koerper: [] },
  ];
}

describe('Selbstverpflichtung', () => {
  it('zeigt jede Aussage als eigene Checkbox mit Kommentarfeld', async () => {
    fetchAttrappe([
      ...detailrouten(),
      { pfad: '/api/v1/selbstverpflichtungen/katalog', koerper: KATALOG },
    ]);
    zeichne('/de/prozesse/p-1/selbstverpflichtung');
    expect(
      await screen.findByLabelText('Das Prozessobjekt ist vollstaendig beschrieben.'),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText('Die Bewertung wurde vollstaendig durchgefuehrt.'),
    ).toBeInTheDocument();
    // Kein Freitextfeld statt der Checkliste, sondern Kommentar je Aussage.
    expect(screen.getAllByLabelText('Kommentar')).toHaveLength(2);
  });

  it('gibt die bestaetigten Aussagen samt Kommentar ab', async () => {
    const { aufrufe } = fetchAttrappe([
      ...detailrouten(),
      { pfad: '/api/v1/selbstverpflichtungen/katalog', koerper: KATALOG },
      {
        pfad: '/api/v1/selbstverpflichtungen',
        methode: 'POST',
        status: 201,
        koerper: selbstverpflichtung(),
      },
    ]);
    zeichne('/de/prozesse/p-1/selbstverpflichtung');
    await userEvent.click(
      await screen.findByLabelText('Das Prozessobjekt ist vollstaendig beschrieben.'),
    );
    await userEvent.type(screen.getAllByLabelText('Kommentar')[1], 'Noch offen');
    await userEvent.click(screen.getByRole('button', { name: 'Abgeben' }));

    await screen.findByRole('heading', { name: 'Rechnungspruefung', level: 1 });
    expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
      typ: 'prozesseigner',
      prozessobjekt_id: 'p-1',
      aussagen: {
        P1: { bestaetigt: true, kommentar: '' },
        P2: { bestaetigt: false, kommentar: 'Noch offen' },
      },
    });
  });

  it('meldet einen abgelehnten Versuch', async () => {
    fetchAttrappe([
      ...detailrouten(),
      { pfad: '/api/v1/selbstverpflichtungen/katalog', koerper: KATALOG },
      {
        pfad: '/api/v1/selbstverpflichtungen',
        methode: 'POST',
        status: 403,
        koerper: { detail: 'Die Selbstverpflichtung gibt der Prozesseigner ab' },
      },
    ]);
    zeichne('/de/prozesse/p-1/selbstverpflichtung');
    await userEvent.click(await screen.findByRole('button', { name: 'Abgeben' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Prozesseigner');
  });

  it('meldet einen Ladefehler', async () => {
    fetchAttrappe([
      ...detailrouten(),
      { pfad: '/api/v1/selbstverpflichtungen/katalog', status: 500, koerper: {} },
    ]);
    zeichne('/de/prozesse/p-1/selbstverpflichtung');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});

describe('Gate-Einreichung am Prozessobjekt', () => {
  it('zeigt den Stand der Selbstverpflichtung', async () => {
    fetchAttrappe(detailrouten([], [selbstverpflichtung()]));
    zeichne('/de/prozesse/p-1');
    expect(await screen.findByTestId('sv-status')).toHaveTextContent('Vollständig abgegeben');
    expect(screen.getByText('2027-09-01')).toBeInTheDocument();
  });

  it('meldet eine fehlende Selbstverpflichtung', async () => {
    fetchAttrappe(detailrouten());
    zeichne('/de/prozesse/p-1');
    expect(
      await screen.findByText('Für diesen Prozess liegt noch keine Selbstverpflichtung vor.'),
    ).toBeInTheDocument();
  });

  it('blendet die Ausloeserwahl nur fuer Gate 2 ein und verlangt sie dort', async () => {
    fetchAttrappe(detailrouten());
    zeichne('/de/prozesse/p-1');
    const typwahl = await screen.findByLabelText('Gate');
    expect(screen.queryByLabelText('Auslöser')).toBeNull();

    await userEvent.selectOptions(typwahl, '2');
    const ausloeserwahl = await screen.findByLabelText('Auslöser');
    // Genau die fuenf abschliessend aufgezaehlten Gruende, kein freier sechster.
    expect(within(ausloeserwahl).getAllByRole('option')).toHaveLength(AUSLOESER.length + 1);
    expect(ausloeserwahl).toBeRequired();
  });

  it('reicht ein Gate 2 mit Ausloeser ein', async () => {
    const { aufrufe } = fetchAttrappe([
      ...detailrouten(),
      {
        pfad: '/api/v1/prozesse/p-1/gates',
        methode: 'POST',
        status: 201,
        koerper: gate({ gate_typ: '2', ausloeser: 'reichweitenerweiterung' }),
      },
    ]);
    zeichne('/de/prozesse/p-1');
    await userEvent.selectOptions(await screen.findByLabelText('Gate'), '2');
    await userEvent.selectOptions(screen.getByLabelText('Auslöser'), 'reichweitenerweiterung');
    await userEvent.type(screen.getByLabelText('Begründung'), 'Neues Land');
    await userEvent.click(screen.getByRole('button', { name: 'Gate einreichen' }));

    await waitFor(() =>
      expect(screen.getByRole('cell', { name: 'reichweitenerweiterung' })).toBeInTheDocument(),
    );
    expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
      gate_typ: '2',
      ausloeser: 'reichweitenerweiterung',
      begruendung: 'Neues Land',
    });
  });

  it('reicht ein Gate 1 ohne Ausloeser ein', async () => {
    const { aufrufe } = fetchAttrappe([
      ...detailrouten(),
      { pfad: '/api/v1/prozesse/p-1/gates', methode: 'POST', status: 201, koerper: gate() },
    ]);
    zeichne('/de/prozesse/p-1');
    await userEvent.click(await screen.findByRole('button', { name: 'Gate einreichen' }));
    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
        gate_typ: '1',
        ausloeser: null,
        begruendung: '',
      }),
    );
  });

  it('meldet eine abgelehnte Einreichung', async () => {
    fetchAttrappe([
      ...detailrouten(),
      {
        pfad: '/api/v1/prozesse/p-1/gates',
        methode: 'POST',
        status: 422,
        koerper: { detail: 'Fuer diesen Prozess ist bereits ein Gate dieses Typs offen' },
      },
    ]);
    zeichne('/de/prozesse/p-1');
    await userEvent.click(await screen.findByRole('button', { name: 'Gate einreichen' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('bereits ein Gate');
  });

  it('listet die Gate-Historie', async () => {
    fetchAttrappe(
      detailrouten([
        gate({ status: 'abgelehnt', entscheidungskommentar: 'Zu riskant' }),
        gate({ id: 'g-2', gate_typ: '2', ausloeser: 'neues_externes_ziel' }),
      ]),
    );
    zeichne('/de/prozesse/p-1');
    await screen.findByRole('heading', { name: 'Gate-Vorgänge' });
    expect(screen.getByText('Abgelehnt')).toBeInTheDocument();
    expect(screen.getByText('Zu riskant')).toBeInTheDocument();
    expect(screen.getByText('neues_externes_ziel')).toBeInTheDocument();
  });

  it('meldet einen Ladefehler', async () => {
    // Die fehlschlagende Route steht vorn: die Attrappe nimmt den ersten Treffer.
    fetchAttrappe([
      { pfad: '/api/v1/prozesse/p-1/gates', status: 500, koerper: {} },
      ...detailrouten(),
    ]);
    zeichne('/de/prozesse/p-1');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});

describe('Arbeitsvorrat der Governance', () => {
  function vorratrouten(gates: GateVorgang[], rollen = PROFIL.rollen): Route[] {
    return [
      { pfad: '/api/v1/auth/me', koerper: { ...PROFIL, rollen } },
      { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
      { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      { pfad: '/api/v1/gates', koerper: gates },
    ];
  }

  const GOVERNANCE = [
    {
      id: 'rz-2',
      user_id: 'user-1',
      rolle: 'governance',
      scope_typ: 'global' as const,
      scope_id: null,
    },
  ];

  it('meldet einen leeren Arbeitsvorrat', async () => {
    fetchAttrappe(vorratrouten([]));
    zeichne('/de/gates');
    expect(await screen.findByText('Es ist kein Gate-Vorgang offen.')).toBeInTheDocument();
  });

  it('blendet die Entscheidung fuer Nicht-Governance aus', async () => {
    fetchAttrappe(vorratrouten([gate()]));
    zeichne('/de/gates');
    await screen.findByRole('heading', { name: 'Offene Gate-Vorgänge' });
    expect(screen.queryByRole('button', { name: 'Freigeben' })).toBeNull();
  });

  it('entscheidet einen Vorgang als Governance', async () => {
    const { aufrufe } = fetchAttrappe([
      ...vorratrouten([gate()], GOVERNANCE),
      {
        pfad: '/api/v1/gates/g-1/entscheidung',
        methode: 'POST',
        koerper: gate({ status: 'freigegeben' }),
      },
    ]);
    zeichne('/de/gates');
    await userEvent.type(
      await screen.findByLabelText('Entscheidungskommentar — g-1'),
      'Passt',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Freigeben' }));
    await waitFor(() =>
      expect(screen.getByText('Es ist kein Gate-Vorgang offen.')).toBeInTheDocument(),
    );
    expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
      status: 'freigegeben',
      kommentar: 'Passt',
    });
  });

  it('lehnt einen Vorgang ab', async () => {
    const { aufrufe } = fetchAttrappe([
      ...vorratrouten([gate()], GOVERNANCE),
      {
        pfad: '/api/v1/gates/g-1/entscheidung',
        methode: 'POST',
        koerper: gate({ status: 'abgelehnt' }),
      },
    ]);
    zeichne('/de/gates');
    await userEvent.click(await screen.findByRole('button', { name: 'Ablehnen' }));
    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
        status: 'abgelehnt',
        kommentar: '',
      }),
    );
  });

  it('meldet eine abgelehnte Entscheidung', async () => {
    fetchAttrappe([
      ...vorratrouten([gate()], GOVERNANCE),
      {
        pfad: '/api/v1/gates/g-1/entscheidung',
        methode: 'POST',
        status: 403,
        koerper: { detail: 'Nur die Governance-Rolle entscheidet' },
      },
    ]);
    zeichne('/de/gates');
    await userEvent.click(await screen.findByRole('button', { name: 'Freigeben' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Governance-Rolle');
  });

  it('meldet einen Ladefehler', async () => {
    fetchAttrappe([
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      { pfad: '/api/v1/gates', status: 500, koerper: {} },
    ]);
    zeichne('/de/gates');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
