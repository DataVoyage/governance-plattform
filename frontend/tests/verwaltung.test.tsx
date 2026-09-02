/**
 * Verwaltung und Nachweis (AP-9).
 *
 * Zwei Dinge macht die Oberfläche, die eine API nicht mitliefert: sie erklärt
 * jede Rolle, und sie zeigt die Wirkung einer Zuweisung, **bevor** sie gilt.
 */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type {
  Nachweiseintrag,
  Nutzer,
  Profil,
  RolleErklaert,
  Rollenzuweisung,
} from '@/api/typen';
import { EINHEITEN, FACHBEREICHE, PROFIL, fetchAttrappe, zeichne, type Route } from './hilfen';

const ADMIN: Profil = {
  ...PROFIL,
  rollen: [
    {
      id: 'rz-a',
      user_id: 'user-1',
      rolle: 'app_administrator' as const,
      scope_typ: 'global' as const,
      scope_id: null,
    },
  ],
};

const NUTZER: Nutzer[] = [
  {
    id: 'user-1',
    email: 'admin@beispiel-ag.de',
    name: 'Alice Admin',
    ist_aktiv: true,
    fuehrungskraft_user_id: null,
  },
  {
    id: 'user-2',
    email: 'neu@beispiel-ag.de',
    name: 'Nina Neu',
    ist_aktiv: true,
    fuehrungskraft_user_id: 'user-1',
  },
  {
    id: 'user-3',
    email: 'alt@beispiel-ag.de',
    name: 'Otto Ohne',
    ist_aktiv: false,
    fuehrungskraft_user_id: null,
  },
];

const ROLLEN: RolleErklaert[] = [
  {
    schluessel: 'prozess_owner',
    erklaerung: 'Legt Prozessobjekte im eigenen Bereich an und hält sie aktuell.',
  },
  {
    schluessel: 'governance',
    erklaerung: 'Entscheidet Gates und pflegt die Einstellungen. Sieht bereichsübergreifend.',
  },
];

const ZUWEISUNGEN: Rollenzuweisung[] = [
  {
    id: 'rz-1',
    user_id: 'user-2',
    rolle: 'prozess_owner',
    scope_typ: 'organisationseinheit',
    scope_id: 'org-int',
  },
];

function routen(profil: Profil = ADMIN, zusatz: Route[] = []): Route[] {
  return [
    ...zusatz,
    { pfad: '/api/v1/auth/me', koerper: profil },
    { pfad: '/api/v1/admin/users', koerper: NUTZER },
    // Die Vorschau trägt ihre Auswahl in der Abfrage — deshalb ein Muster.
    { pfad: /\/rollenzuweisungen\/wirkung\?/, koerper: {
      rolle: 'prozess_owner',
      scope_typ: 'organisationseinheit',
      scope_name: 'Finance · INT',
      prozessobjekte: 24,
      tool_objekte: 3,
      beispiele: ['Rechnungsprüfung', 'Mahnlauf'],
    } },
    { pfad: '/api/v1/admin/rollenzuweisungen', koerper: ZUWEISUNGEN },
    { pfad: '/api/v1/admin/rollen', koerper: ROLLEN },
    { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    { pfad: '/api/v1/fachbereiche', koerper: FACHBEREICHE },
  ];
}

describe('Nutzerliste', () => {
  it('zeigt Name, Aktivstatus, Führungskraft und Rollen', async () => {
    fetchAttrappe(routen());
    zeichne('/de/verwaltung');
    const zeile = await screen.findByTestId('nutzer-user-2');
    expect(zeile).toHaveTextContent('Nina Neu');
    expect(zeile).toHaveTextContent('neu@beispiel-ag.de');
    expect(zeile).toHaveTextContent('Führungskraft: Alice Admin');
    expect(zeile).toHaveTextContent('Prozess-Owner');
    expect(zeile).toHaveTextContent('Aktiv');
    expect(screen.getByTestId('nutzer-user-3')).toHaveTextContent('Inaktiv');
  });

  it('durchsucht die Liste nach Name und E-Mail', async () => {
    fetchAttrappe(routen());
    zeichne('/de/verwaltung');
    await userEvent.type(await screen.findByLabelText('Nutzer suchen'), 'nina');
    expect(screen.getByTestId('nutzer-user-2')).toBeInTheDocument();
    expect(screen.queryByTestId('nutzer-user-3')).not.toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText('Nutzer suchen'));
    await userEvent.type(screen.getByLabelText('Nutzer suchen'), 'alt@');
    expect(screen.getByTestId('nutzer-user-3')).toBeInTheDocument();
    expect(screen.queryByTestId('nutzer-user-2')).not.toBeInTheDocument();
  });

  it('sagt, wenn nichts passt', async () => {
    fetchAttrappe(routen());
    zeichne('/de/verwaltung');
    await userEvent.type(await screen.findByLabelText('Nutzer suchen'), 'niemand');
    expect(screen.getByText('Kein Nutzer passt zu dieser Suche.')).toBeInTheDocument();
  });

  it('sperrt die Verwaltung ohne Administratorrolle', async () => {
    fetchAttrappe(routen(PROFIL));
    zeichne('/de/verwaltung');
    expect(
      await screen.findByText(
        'Ansicht ohne Änderungsrecht: Nutzer und Rollen verwaltet der App-Administrator.',
      ),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByTestId('nutzer-user-2'));
    expect(screen.getByTestId('rolle-zuweisen')).toBeDisabled();
  });

  it('meldet einen Ladefehler', async () => {
    fetchAttrappe([
      { pfad: '/api/v1/auth/me', koerper: ADMIN },
      { pfad: '/api/v1/admin/users', status: 403, koerper: { detail: 'Nur der Administrator' } },
    ]);
    zeichne('/de/verwaltung');
    expect(await screen.findByRole('alert')).toHaveTextContent('Nur der Administrator');
  });
});

describe('Rollenzuweisung', () => {
  async function blattOeffnen(zusatz: Route[] = []) {
    fetchAttrappe(routen(ADMIN, zusatz));
    zeichne('/de/verwaltung');
    await userEvent.click(await screen.findByTestId('nutzer-user-2'));
  }

  it('erklärt jede Rolle und zeigt die Wirkung vor der Entscheidung', async () => {
    await blattOeffnen();
    // Die Erklärung aus A.15 hängt an der gewählten Rolle.
    expect(
      screen.getByText('Legt Prozessobjekte im eigenen Bereich an und hält sie aktuell.'),
    ).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText('Organisationseinheit'), 'org-int');
    await waitFor(() =>
      expect(screen.getByTestId('wirkung')).toHaveTextContent(
        'Diese Zuweisung gibt zusätzlich Zugriff auf 24 Prozessobjekte und 3 Tool-Objekte (Finance · INT).',
      ),
    );
    expect(screen.getByText(/Rechnungsprüfung, Mahnlauf/)).toBeInTheDocument();
  });

  it('weist eine Rolle mit Scope zu', async () => {
    const { aufrufe } = fetchAttrappe(
      routen(ADMIN, [
        { pfad: '/api/v1/admin/rollenzuweisungen', methode: 'POST', koerper: ZUWEISUNGEN[0] },
      ]),
    );
    zeichne('/de/verwaltung');
    await userEvent.click(await screen.findByTestId('nutzer-user-2'));
    await userEvent.selectOptions(screen.getByLabelText('Rolle'), 'governance');
    await userEvent.selectOptions(screen.getByLabelText('Geltungsbereich'), 'global');
    // Ein globaler Scope hat kein Ziel — das Feld verschwindet.
    expect(screen.queryByLabelText('Organisationseinheit')).not.toBeInTheDocument();

    await userEvent.click(screen.getByTestId('rolle-zuweisen'));
    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
        user_id: 'user-2',
        rolle: 'governance',
        scope_typ: 'global',
        scope_id: null,
      }),
    );
  });

  it('entzieht eine Rolle', async () => {
    const { aufrufe } = fetchAttrappe(
      routen(ADMIN, [
        { pfad: '/api/v1/admin/rollenzuweisungen/rz-1', methode: 'DELETE', status: 204, koerper: {} },
      ]),
    );
    zeichne('/de/verwaltung');
    await userEvent.click(await screen.findByTestId('nutzer-user-2'));
    expect(screen.getByTestId('zuweisung-rz-1')).toHaveTextContent('Prozess-Owner');

    await userEvent.click(screen.getByTestId('entziehen-rz-1'));
    await waitFor(() =>
      expect(aufrufe.some((a) => a.methode === 'DELETE' && a.url.endsWith('/rz-1'))).toBe(true),
    );
  });

  it('setzt die Führungskraft', async () => {
    const { aufrufe } = fetchAttrappe(
      routen(ADMIN, [
        {
          pfad: '/api/v1/admin/users/user-3',
          methode: 'PATCH',
          koerper: { ...NUTZER[2], fuehrungskraft_user_id: 'user-1' },
        },
      ]),
    );
    zeichne('/de/verwaltung');
    await userEvent.click(await screen.findByTestId('nutzer-user-3'));
    await userEvent.selectOptions(screen.getByLabelText('Führungskraft'), 'user-1');
    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'PATCH')?.koerper).toEqual({
        fuehrungskraft_user_id: 'user-1',
      }),
    );
  });

  it('meldet eine abgelehnte Zuweisung', async () => {
    await blattOeffnen([
      {
        pfad: '/api/v1/admin/rollenzuweisungen',
        methode: 'POST',
        status: 403,
        koerper: { detail: 'Rollen vergibt nur der App-Administrator' },
      },
    ]);
    await userEvent.selectOptions(screen.getByLabelText('Geltungsbereich'), 'global');
    await userEvent.click(screen.getByTestId('rolle-zuweisen'));
    expect(await screen.findByRole('alert')).toHaveTextContent('App-Administrator');
  });
});

describe('Nachweis', () => {
  const EINTRAEGE: Nachweiseintrag[] = [
    {
      cursor: 42,
      entity_type: 'prozessobjekte',
      entity_id: 'p-1',
      aktion: 'geaendert',
      zeitpunkt: '2026-09-02T14:30:00+00:00',
      akteur: 'Nina Neu',
      gegenstand: 'Rechnungsprüfung',
      aenderungen: [{ feld: 'name', vorher: 'Alt', nachher: 'Rechnungsprüfung' }],
    },
    {
      cursor: 41,
      entity_type: 'prozessobjekte',
      entity_id: 'p-1',
      aktion: 'erstellt',
      zeitpunkt: '2026-09-01T09:00:00+00:00',
      akteur: 'Nina Neu',
      gegenstand: 'Rechnungsprüfung',
      aenderungen: [],
    },
  ];

  function nachweisrouten(eintraege: unknown = EINTRAEGE, zusatz: Route[] = []): Route[] {
    return [
      ...zusatz,
      { pfad: '/api/v1/auth/me', koerper: ADMIN },
      { pfad: '/api/v1/nachweis', koerper: eintraege },
    ];
  }

  it('nennt Person, Zeitpunkt und was sich geändert hat', async () => {
    fetchAttrappe(nachweisrouten());
    zeichne('/de/nachweis');
    const zeile = await screen.findByTestId('nachweis-42');
    expect(zeile).toHaveTextContent('Rechnungsprüfung');
    expect(zeile).toHaveTextContent('Nina Neu');
    expect(zeile).toHaveTextContent('2026-09-02 14:30');
    expect(zeile).toHaveTextContent('name: Alt → Rechnungsprüfung');
    expect(zeile).toHaveTextContent('Geändert');
    expect(screen.getByTestId('nachweis-41')).toHaveTextContent('Erstellt');
  });

  it('filtert nach Objektart und hält den Filter in der URL', async () => {
    const { aufrufe } = fetchAttrappe(nachweisrouten());
    zeichne('/de/nachweis');
    await userEvent.selectOptions(await screen.findByLabelText('Objektart'), 'bewertungen');
    await waitFor(() =>
      expect(aufrufe.some((a) => a.url.includes('entity_type=bewertungen'))).toBe(true),
    );
  });

  it('sagt, wenn es nichts zu zeigen gibt', async () => {
    fetchAttrappe(nachweisrouten([]));
    zeichne('/de/nachweis');
    expect(
      await screen.findByText('Zu diesem Ausschnitt gibt es keinen Eintrag.'),
    ).toBeInTheDocument();
  });

  it('meldet den abgelehnten Zugriff mit seinem Grund', async () => {
    fetchAttrappe(
      nachweisrouten(undefined, [
        {
          pfad: '/api/v1/nachweis',
          status: 403,
          koerper: { detail: 'Den Nachweis lesen die Auditor- und Governance-Rolle' },
        },
      ]),
    );
    zeichne('/de/nachweis');
    expect(await screen.findByRole('alert')).toHaveTextContent('Auditor');
  });
});

describe('Navigation', () => {
  it('zeigt Verwaltung und Nachweis nur, wo sie etwas nützen', async () => {
    fetchAttrappe(routen(ADMIN));
    zeichne('/de/verwaltung');
    await screen.findByTestId('nutzer-user-2');
    const navigation = screen.getByRole('navigation');
    expect(within(navigation).getByRole('link', { name: /Verwaltung/ })).toBeInTheDocument();
    expect(within(navigation).getByRole('link', { name: /Nachweis/ })).toBeInTheDocument();
  });

  it('blendet sie ohne die Rolle aus', async () => {
    fetchAttrappe(routen(PROFIL));
    zeichne('/de/verwaltung');
    await screen.findByTestId('nutzer-user-2');
    const navigation = screen.getByRole('navigation');
    expect(within(navigation).queryByRole('link', { name: /Verwaltung/ })).toBeNull();
    expect(within(navigation).queryByRole('link', { name: /Nachweis/ })).toBeNull();
  });
});
