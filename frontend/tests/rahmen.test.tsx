/**
 * Erlaubnisrahmen, Schicht 2 und die Governance-Einstellungen (AP-6).
 *
 * Der Rahmen ist der Ort, an dem „erlaubt" und „gemessen" nebeneinander
 * stehen. Die Tests prüfen genau das: dass beide Seiten sichtbar sind, dass
 * eine Abweichung als Satz erklärt wird und dass nirgends ein technischer
 * Schlüssel im Sichtfeld landet.
 */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { Einstellung } from '@/api/typen';
import {
  EINHEITEN,
  PROFIL,
  fetchAttrappe,
  prozess,
  rahmen,
  rahmenElement,
  tool,
  zeichne,
  type Route,
} from './hilfen';

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

describe('Erlaubnisrahmen', () => {
  it('zeigt alle sieben Elemente aus Schicht 1', async () => {
    fetchAttrappe(toolrouten());
    zeichne('/de/tools/tool-1');
    // Auf ein Element warten, nicht auf die Überschrift: die trägt auch die
    // Karte, solange sie noch lädt.
    await screen.findByTestId('rahmen-datenobjekte');
    for (const schluessel of [
      'datenobjekte',
      'datenkategorie',
      'reichweite',
      'externe_ziele',
      'zugriffsart',
      'ausfuehrungsart',
      'ausfuehrungsidentitaet',
    ]) {
      expect(screen.getByTestId(`rahmen-${schluessel}`)).toBeInTheDocument();
    }
  });

  it('stellt erlaubt und gemessen nebeneinander, mit Namen statt Schluesseln', async () => {
    fetchAttrappe(
      toolrouten([
        {
          pfad: /\/erlaubnisrahmen$/,
          koerper: rahmen({
            elemente: [
              rahmenElement('datenkategorie', {
                erlaubt: ['intern'],
                gemessen: ['personenbezogen'],
                abweichung: ['personenbezogen'],
                eingehalten: false,
              }),
            ],
            eingehalten: false,
          }),
        },
      ]),
    );
    zeichne('/de/tools/tool-1');
    expect(await screen.findByTestId('erlaubt-datenkategorie')).toHaveTextContent('Intern');
    expect(screen.getByTestId('gemessen-datenkategorie')).toHaveTextContent('Personenbezogen');
    expect(screen.getByTestId('abweichung-datenkategorie')).toHaveTextContent(
      'Das Tool verarbeitet eine höhere Kategorie, als der Rahmen deckt: Personenbezogen',
    );
    expect(screen.getByText('Eine Abweichung')).toBeInTheDocument();
  });

  it('nennt die Reichweite als abgeleitet statt als gemessen', async () => {
    fetchAttrappe(
      toolrouten([
        {
          pfad: /\/erlaubnisrahmen$/,
          koerper: rahmen({
            elemente: [rahmenElement('reichweite', { erlaubt: ['bereich'], messbar: false })],
          }),
        },
      ]),
    );
    zeichne('/de/tools/tool-1');
    expect(await screen.findByTestId('gemessen-reichweite')).toHaveTextContent(
      'Nicht gemessen — abgeleitet',
    );
  });

  it('nennt bei der Zugriffsabweichung das Datenobjekt, nicht die Zugriffsart', async () => {
    fetchAttrappe(
      toolrouten([
        {
          pfad: /\/erlaubnisrahmen$/,
          koerper: rahmen({
            elemente: [
              rahmenElement('zugriffsart', {
                erlaubt: ['lesen'],
                gemessen: ['lesen_schreiben'],
                abweichung: ['Buchungsliste'],
                eingehalten: false,
              }),
            ],
            eingehalten: false,
          }),
        },
      ]),
    );
    zeichne('/de/tools/tool-1');
    expect(await screen.findByTestId('abweichung-zugriffsart')).toHaveTextContent(
      'Schreibzugriff auf ein Datenobjekt, das kein Prozessergebnis ist: Buchungsliste',
    );
    expect(screen.getByTestId('erlaubt-zugriffsart')).toHaveTextContent('Liest');
  });

  it('meldet einen selbst erkannten Schicht-2-Verstoss', async () => {
    fetchAttrappe(
      toolrouten([
        {
          pfad: /\/erlaubnisrahmen$/,
          koerper: rahmen({ schicht2_befunde: ['statische_zugangsdaten'] }),
        },
      ]),
    );
    zeichne('/de/tools/tool-1');
    expect(
      await screen.findByText(/Dauerhaft gültige Zugangsdaten im Tool hinterlegt/),
    ).toBeInTheDocument();
  });

  it('sagt, wenn das Tool im Rahmen liegt', async () => {
    fetchAttrappe(toolrouten());
    zeichne('/de/tools/tool-1');
    expect(await screen.findByText('Im Rahmen')).toBeInTheDocument();
  });
});

describe('Schicht-2-Meldung', () => {
  it('bietet die sechs Verbote erst bei einer roten Meldung an', async () => {
    fetchAttrappe(toolrouten());
    zeichne('/de/tools/tool-1');
    await screen.findByLabelText('Zustand melden');
    expect(screen.queryByLabelText('Verstoß gegen Schicht 2')).not.toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText('Zustand melden'), 'rot');
    const wahl = screen.getByLabelText('Verstoß gegen Schicht 2');
    const optionen = Array.from(wahl.querySelectorAll('option')).map((o) => o.value);
    // Sechs Verbote plus „keiner" — kein siebter, freier Grund.
    expect(optionen).toEqual([
      '',
      'identitaet_umgangen',
      'statische_zugangsdaten',
      'undeklarierte_quellen',
      'entscheidung_ohne_mensch',
      'daten_ins_offene_netz',
      'protokollierung_umgangen',
    ]);
  });

  it('kuendigt die Folge an und schickt das Verbot mit', async () => {
    const { aufrufe } = fetchAttrappe([
      ...toolrouten(),
      {
        pfad: '/api/v1/tools/tool-1/compliance',
        methode: 'POST',
        status: 201,
        koerper: {
          zustand: {
            id: 'cz-9',
            tool_objekt_id: 'tool-1',
            farbe: 'rot',
            begruendung: 'Laeuft unter einem geteilten Konto',
            abweichung_art: null,
            schicht2_verbot: 'identitaet_umgangen',
            festgestellt_am: '2026-09-02T10:00:00Z',
            festgestellt_von: 'user-1',
          },
          lenkungsvorgang: null,
        },
      },
    ]);
    zeichne('/de/tools/tool-1');
    await userEvent.selectOptions(await screen.findByLabelText('Zustand melden'), 'rot');
    await userEvent.selectOptions(
      screen.getByLabelText('Verstoß gegen Schicht 2'),
      'identitaet_umgangen',
    );
    expect(screen.getByText(/unmittelbar in Eskalationsstufe 2/)).toBeInTheDocument();

    await userEvent.type(
      screen.getByLabelText('Begründung'),
      'Laeuft unter einem geteilten Konto',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Zustand melden' }));

    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
        farbe: 'rot',
        begruendung: 'Laeuft unter einem geteilten Konto',
        abweichung_art: null,
        schicht2_verbot: 'identitaet_umgangen',
      }),
    );
    // In der Zeitreihe steht der Name des Verbots, nicht sein Schlüssel.
    expect(await screen.findByTestId('aktueller-zustand')).toHaveTextContent(
      'Ausführung unter umgangener Unternehmensidentität',
    );
  });
});

describe('Governance-Einstellungen', () => {
  const EINSTELLUNGEN: Einstellung[] = [
    {
      schluessel: 'lenkung_frist_tage_tier1',
      wert: '30',
      beschreibung: 'Arbeitstage bis zur Eskalation in Stufe 2 bei Tier 1 (A.13.5)',
    },
    {
      schluessel: 'lenkung_nachfrist_tage_tier1',
      wert: '15',
      beschreibung: 'Zusätzliche Arbeitstage in Stufe 2 bei Tier 1, danach Stufe 3 (A.13.5)',
    },
    {
      schluessel: 'asset_inaktiv_tage',
      wert: '180',
      beschreibung: 'Ab wann ein Tool-Objekt im Cockpit als inaktiv gilt',
    },
  ];

  const governanceProfil = {
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

  it('zeigt die Fristen mit ihrer Begruendung und dem Hinweis auf die Wirkung', async () => {
    fetchAttrappe([
      { pfad: '/api/v1/auth/me', koerper: governanceProfil },
      { pfad: '/api/v1/konfiguration', koerper: EINSTELLUNGEN },
    ]);
    zeichne('/de/konfiguration');
    await screen.findByRole('heading', { name: 'Einstellungen' });
    expect(
      screen.getByText(/Eine Änderung wirkt auf neue Vorgänge, nicht rückwirkend/),
    ).toBeInTheDocument();
    expect(screen.getByTestId('einstellung-lenkung_frist_tage_tier1')).toHaveTextContent(
      'Stufe 1 bei Tier 1',
    );
    expect(screen.getByText('Lenkungsfristen (A.13.5)')).toBeInTheDocument();
  });

  it('sichert eine geaenderte Frist', async () => {
    const { aufrufe } = fetchAttrappe([
      { pfad: '/api/v1/auth/me', koerper: governanceProfil },
      { pfad: '/api/v1/konfiguration', koerper: EINSTELLUNGEN },
      {
        pfad: '/api/v1/konfiguration/lenkung_frist_tage_tier1',
        methode: 'PUT',
        koerper: { ...EINSTELLUNGEN[0], wert: '20' },
      },
    ]);
    zeichne('/de/konfiguration');
    const zeile = await screen.findByTestId('einstellung-lenkung_frist_tage_tier1');
    const feld = within(zeile).getByLabelText('Stufe 1 bei Tier 1');
    await userEvent.clear(feld);
    await userEvent.type(feld, '20');
    await userEvent.click(screen.getByTestId('sichern-lenkung_frist_tage_tier1'));

    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'PUT')?.koerper).toEqual({ wert: '20' }),
    );
    expect(await screen.findByText('Gesichert')).toBeInTheDocument();
  });

  it('sperrt die Aenderung ohne Governance-Rolle', async () => {
    fetchAttrappe([
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      { pfad: '/api/v1/konfiguration', koerper: EINSTELLUNGEN },
    ]);
    zeichne('/de/konfiguration');
    expect(
      await screen.findByText(
        'Ansicht ohne Änderungsrecht: Governance-Einstellungen ändert die Governance-Rolle.',
      ),
    ).toBeInTheDocument();
    expect(screen.getByTestId('sichern-asset_inaktiv_tage')).toBeDisabled();
  });

  it('meldet einen Ladefehler', async () => {
    fetchAttrappe([
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      { pfad: '/api/v1/konfiguration', status: 500, koerper: {} },
    ]);
    zeichne('/de/konfiguration');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});

describe('Erklärter Rahmen am Prozessobjekt (V-PRO-23)', () => {
  // Ohne Nutzerliste bleibt die Pflichtauswahl „Owner" leer, und das
  // Formular lässt sich gar nicht absenden — dieselbe Vorbedingung, die auch
  // ein Mensch braucht.
  const NUTZER = [
    { id: 'user-1', email: 'owner@beispiel-ag.de', name: 'Olivia Owner', aktiv: true },
    { id: 'user-2', email: 'v@beispiel-ag.de', name: 'Viktor Vertretung', aktiv: true },
  ];

  function formularrouten(zusatz: Route[] = []): Route[] {
    return [
      ...zusatz,
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      { pfad: '/api/v1/admin/users', koerper: NUTZER },
      { pfad: '/api/v1/prozesse/p-1', koerper: prozess({ erlaubte_externe_ziele: ['alt.example'] }) },
      { pfad: '/api/v1/prozesse', koerper: [] },
    ];
  }

  it('zeigt die erklaerten Ziele und die Folge einer Ergaenzung', async () => {
    fetchAttrappe(formularrouten());
    zeichne('/de/prozesse/p-1/bearbeiten');
    expect(await screen.findByTestId('ziel-alt.example')).toBeInTheDocument();
    expect(screen.getByText(/löst ein neues Ziel Gate 2 aus/)).toBeInTheDocument();
  });

  it('ergaenzt ein Ziel und schickt es beim Speichern mit', async () => {
    const { aufrufe } = fetchAttrappe(
      formularrouten([
        {
          pfad: '/api/v1/prozesse/p-1',
          methode: 'PATCH',
          koerper: prozess({ erlaubte_externe_ziele: ['alt.example', 'neu.example'] }),
        },
      ]),
    );
    zeichne('/de/prozesse/p-1/bearbeiten');
    await userEvent.type(await screen.findByLabelText('Ziel ergänzen'), 'neu.example');
    await userEvent.click(screen.getByTestId('ziel-hinzufuegen'));
    expect(screen.getByTestId('ziel-neu.example')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Speichern' }));
    await waitFor(() =>
      expect(
        (aufrufe.find((a) => a.methode === 'PATCH')?.koerper as { erlaubte_externe_ziele: string[] })
          .erlaubte_externe_ziele,
      ).toEqual(['alt.example', 'neu.example']),
    );
  });

  it('entfernt ein Ziel wieder', async () => {
    fetchAttrappe(formularrouten());
    zeichne('/de/prozesse/p-1/bearbeiten');
    await userEvent.click(
      await screen.findByRole('button', { name: 'alt.example — Entfernen' }),
    );
    expect(screen.queryByTestId('ziel-alt.example')).not.toBeInTheDocument();
    expect(screen.getByText('Für diesen Prozess ist kein externes Ziel erklärt.')).toBeInTheDocument();
  });
});

describe('Gemessene Seite am Tool-Objekt (V-TOO-18)', () => {
  it('erfasst ein externes Ziel und entfernt es wieder', async () => {
    const { aufrufe } = fetchAttrappe([
      { pfad: '/api/v1/tools/tool-1', methode: 'PATCH', koerper: tool() },
      ...toolrouten(),
    ]);
    zeichne('/de/tools/tool-1');
    await userEvent.type(await screen.findByLabelText('Ziel erfassen'), 'ziel.example');
    await userEvent.click(screen.getByTestId('tool-ziel-hinzufuegen'));
    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'PATCH')?.koerper).toEqual({
        externe_ziele: ['ziel.example'],
      }),
    );
  });

  it('erklaert die Ausfuehrungsidentitaet und die statischen Zugangsdaten', async () => {
    const { aufrufe } = fetchAttrappe([
      { pfad: '/api/v1/tools/tool-1', methode: 'PATCH', koerper: tool() },
      ...toolrouten(),
    ]);
    zeichne('/de/tools/tool-1');
    await userEvent.selectOptions(
      await screen.findByLabelText('Ausführungsidentität'),
      'benannter_dienst',
    );
    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'PATCH')?.koerper).toEqual({
        ausfuehrungsidentitaet: 'benannter_dienst',
      }),
    );

    await userEvent.click(screen.getByLabelText(/Dauerhaft gültige Zugangsdaten hinterlegt/));
    await waitFor(() =>
      expect(aufrufe.filter((a) => a.methode === 'PATCH').at(-1)?.koerper).toEqual({
        statische_zugangsdaten: true,
      }),
    );
  });

  it('zeigt ein erfasstes Ziel in der Liste', async () => {
    fetchAttrappe([
      { pfad: '/api/v1/tools/tool-1', koerper: tool({ externe_ziele: ['ziel.example'] }) },
      ...toolrouten(),
    ]);
    zeichne('/de/tools/tool-1');
    expect(await screen.findByTestId('tool-ziel-ziel.example')).toBeInTheDocument();
  });
});
