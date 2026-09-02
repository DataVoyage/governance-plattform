/**
 * Selbstverpflichtung und Gates in der Oberflaeche (Architektur 8.4, 8.5).
 */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { Deckung, GateVorgang, Selbstverpflichtung } from '@/api/typen';
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
    version: 2,
    aussagen: [
      { id: 'PE1', text: 'Der Zweck ist vollstaendig beschrieben.', ab_tier: 1 },
      { id: 'PE2', text: 'Die Datenobjekte decken alle Daten ab.', ab_tier: 1 },
      { id: 'PE3', text: 'Der Empfaengerkreis ist vollstaendig angegeben.', ab_tier: 2 },
    ],
  },
  {
    typ: 'technischer_owner',
    version: 2,
    aussagen: [{ id: 'TO1', text: 'Die Anforderungsklassen sind umgesetzt.', ab_tier: 1 }],
  },
];

function deckung(ueberschreibungen: Partial<Deckung> = {}): Deckung {
  return {
    gedeckt: false,
    grund: 'keine',
    grundtext: 'Für dieses Objekt liegt noch keine Selbstverpflichtung vor.',
    verlangte_aussagen: ['PE1', 'PE2', 'PE3'],
    tier: 3,
    aktuelle: null,
    ...ueberschreibungen,
  };
}

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
    katalog_version: 2,
    bewertung_id: 'b-1',
    tier_bei_abgabe: 3,
    abgegeben_von: 'user-1',
    abgegeben_am: '2026-09-01T10:00:00Z',
    gueltig_bis: '2027-09-01T10:00:00Z',
    erinnerung_gesendet_am: null,
    ...ueberschreibungen,
  };
}

function detailrouten(gates: GateVorgang[] = [], stand: Deckung = deckung()): Route[] {
  return [
    { pfad: '/api/v1/auth/me', koerper: PROFIL },
    { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    { pfad: '/api/v1/prozesse/p-1', koerper: prozess() },
    { pfad: '/api/v1/prozesse/p-1/bewertungen', koerper: [] },
    { pfad: '/api/v1/prozesse/p-1/selbstverpflichtung', koerper: stand },
    { pfad: '/api/v1/prozesse/p-1/gates', koerper: gates },
    { pfad: '/api/v1/gates/ausloeser', koerper: AUSLOESER },
    { pfad: '/api/v1/tools', koerper: [] },
  ];
}

describe('Selbstverpflichtung', () => {
  it('zeigt jede verlangte Aussage einzeln mit einklappbarem Kommentar', async () => {
    fetchAttrappe([
      ...detailrouten(),
      { pfad: '/api/v1/selbstverpflichtungen/katalog', koerper: KATALOG },
    ]);
    zeichne('/de/prozesse/p-1/selbstverpflichtung');
    expect(await screen.findByLabelText('Der Zweck ist vollstaendig beschrieben.')).toBeInTheDocument();
    expect(screen.getByLabelText('Die Datenobjekte decken alle Daten ab.')).toBeInTheDocument();
    expect(screen.getByLabelText('Der Empfaengerkreis ist vollstaendig angegeben.')).toBeInTheDocument();

    // Kein Freitextfeld statt der Checkliste. Der Kommentar ist eingeklappt,
    // weil er die Ausnahme ist — je Aussage einer.
    expect(screen.queryByLabelText(/^Kommentar/)).toBeNull();
    await userEvent.click(screen.getByTestId('kommentar-oeffnen-PE2'));
    expect(await screen.findByLabelText('Kommentar — PE2')).toBeInTheDocument();
  });

  it('verlangt bei Tier 1 nur die Kurzform', async () => {
    // Welche Aussagen verlangt sind, entscheidet der Server (A.10.5).
    fetchAttrappe([
      ...detailrouten([], deckung({ tier: 1, verlangte_aussagen: ['PE1', 'PE2'] })),
      { pfad: '/api/v1/selbstverpflichtungen/katalog', koerper: KATALOG },
    ]);
    zeichne('/de/prozesse/p-1/selbstverpflichtung');
    expect(await screen.findByLabelText('Der Zweck ist vollstaendig beschrieben.')).toBeInTheDocument();
    expect(screen.queryByLabelText('Der Empfaengerkreis ist vollstaendig angegeben.')).toBeNull();
    expect(screen.getByText(/Kurzform/)).toBeInTheDocument();
  });

  it('nennt den Grund, wenn die Erklaerung nicht mehr traegt', async () => {
    fetchAttrappe([
      ...detailrouten(
        [],
        deckung({
          grund: 'profil_veraltet',
          grundtext: 'Die Erklärung hängt an einer überholten Bewertung.',
          aktuelle: selbstverpflichtung(),
        }),
      ),
      { pfad: '/api/v1/selbstverpflichtungen/katalog', koerper: KATALOG },
    ]);
    zeichne('/de/prozesse/p-1/selbstverpflichtung');
    expect(await screen.findByText(/überholten Bewertung/)).toBeInTheDocument();
    expect(screen.getAllByText('Verfallen').length).toBeGreaterThan(0);
    // Die bestehende Erklaerung ist der Ausgangspunkt, nicht ein leeres Blatt.
    expect(screen.getByText('2026-09-01')).toBeInTheDocument();
  });

  it('verlaengert eine abgelaufene Erklaerung mit einem Klick', async () => {
    const { aufrufe } = fetchAttrappe([
      ...detailrouten(
        [],
        deckung({
          grund: 'frist_abgelaufen',
          grundtext: 'Die Jahresfrist ist verstrichen; eine Bestätigung genügt.',
          aktuelle: selbstverpflichtung(),
        }),
      ),
      { pfad: '/api/v1/selbstverpflichtungen/katalog', koerper: KATALOG },
      {
        pfad: '/api/v1/selbstverpflichtungen/sv-1/bestaetigung',
        methode: 'POST',
        koerper: selbstverpflichtung({ id: 'sv-2' }),
      },
    ]);
    zeichne('/de/prozesse/p-1/selbstverpflichtung');
    await userEvent.click(await screen.findByTestId('sv-bestaetigen'));
    await screen.findByRole('heading', { name: 'Rechnungspruefung', level: 1 });
    expect(
      aufrufe.some((a) => a.methode === 'POST' && a.url.endsWith('/sv-1/bestaetigung')),
    ).toBe(true);
  });

  it('bietet die Jahresbestaetigung nur an, wo sie genuegt', async () => {
    fetchAttrappe([
      ...detailrouten(
        [],
        deckung({ grund: 'profil_veraltet', grundtext: 'Verfallen.', aktuelle: selbstverpflichtung() }),
      ),
      { pfad: '/api/v1/selbstverpflichtungen/katalog', koerper: KATALOG },
    ]);
    zeichne('/de/prozesse/p-1/selbstverpflichtung');
    await screen.findByText('Verfallen.');
    expect(screen.queryByTestId('sv-bestaetigen')).toBeNull();
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
    await userEvent.click(await screen.findByLabelText('Der Zweck ist vollstaendig beschrieben.'));
    await userEvent.click(screen.getByTestId('kommentar-oeffnen-PE2'));
    await userEvent.type(await screen.findByLabelText('Kommentar — PE2'), 'Noch offen');
    await userEvent.click(screen.getByTestId('sv-abgeben'));

    await screen.findByRole('heading', { name: 'Rechnungspruefung', level: 1 });
    expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
      typ: 'prozesseigner',
      prozessobjekt_id: 'p-1',
      aussagen: {
        PE1: { bestaetigt: true, kommentar: '' },
        PE2: { bestaetigt: false, kommentar: 'Noch offen' },
      },
    });
  });

  it('gibt die Erklaerung des technischen Owners am Tool-Objekt ab', async () => {
    const { aufrufe } = fetchAttrappe([
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
      { pfad: '/api/v1/selbstverpflichtungen/katalog', koerper: KATALOG },
      {
        pfad: '/api/v1/tools/t-1/selbstverpflichtung/deckung',
        koerper: deckung({ verlangte_aussagen: ['TO1'], tier: 1 }),
      },
      {
        pfad: '/api/v1/selbstverpflichtungen',
        methode: 'POST',
        status: 201,
        koerper: selbstverpflichtung({ typ: 'technischer_owner' }),
      },
    ]);
    zeichne('/de/tools/t-1/selbstverpflichtung');
    await userEvent.click(await screen.findByLabelText('Die Anforderungsklassen sind umgesetzt.'));
    await userEvent.click(screen.getByTestId('sv-abgeben'));
    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
        typ: 'technischer_owner',
        tool_objekt_id: 't-1',
        aussagen: { TO1: { bestaetigt: true, kommentar: '' } },
      }),
    );
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
    await userEvent.click(await screen.findByTestId('sv-abgeben'));
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
    fetchAttrappe(
      detailrouten(
        [],
        deckung({ gedeckt: true, grund: '', grundtext: 'Die Erklärung liegt vor und trägt.', aktuelle: selbstverpflichtung() }),
      ),
    );
    zeichne('/de/prozesse/p-1');
    expect(await screen.findByText('Die Erklärung liegt vor und trägt.')).toBeInTheDocument();
    expect(screen.getByText('2027-09-01')).toBeInTheDocument();
  });

  it('meldet eine fehlende Selbstverpflichtung mit ihrem Grund', async () => {
    fetchAttrappe(detailrouten());
    zeichne('/de/prozesse/p-1');
    expect(
      await screen.findByText('Für dieses Objekt liegt noch keine Selbstverpflichtung vor.'),
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
    // Ohne Ausloeser ist Gate 2 nicht einreichbar.
    expect(screen.getByTestId('gate-einreichen')).toBeDisabled();
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
    await userEvent.click(screen.getByTestId('gate-einreichen'));

    await waitFor(() => expect(screen.getByTestId('gate-g-1')).toBeInTheDocument());
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
    expect(screen.getByTestId('gate-g-1')).toHaveTextContent('Zu riskant');
    expect(screen.getByTestId('gate-g-2')).toHaveTextContent('Neues externes Ziel');
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
      rolle: 'governance' as const,
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
      await screen.findByLabelText('Entscheidungskommentar'),
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

  it('verlangt fuer eine Ablehnung eine Begruendung', async () => {
    const { aufrufe } = fetchAttrappe([
      ...vorratrouten([gate()], GOVERNANCE),
      {
        pfad: '/api/v1/gates/g-1/entscheidung',
        methode: 'POST',
        koerper: gate({ status: 'abgelehnt' }),
      },
    ]);
    zeichne('/de/gates');
    // Ohne Grund keine Ablehnung: wer abgelehnt wird, erfaehrt sonst nur,
    // dass es nicht weitergeht.
    expect(await screen.findByTestId('ablehnen-g-1')).toBeDisabled();
    expect(screen.getByTestId('freigeben-g-1')).toBeEnabled();

    await userEvent.type(
      screen.getByLabelText('Entscheidungskommentar'),
      'Reichweite unklar',
    );
    await userEvent.click(screen.getByTestId('ablehnen-g-1'));
    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
        status: 'abgelehnt',
        kommentar: 'Reichweite unklar',
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
    await userEvent.click(await screen.findByTestId('freigeben-g-1'));
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
