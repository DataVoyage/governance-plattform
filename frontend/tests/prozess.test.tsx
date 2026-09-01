/**
 * Prozess-Modul in der Oberflaeche (Architektur 8.1, 9.1).
 */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { EINHEITEN, PROFIL, fetchAttrappe, prozess, zeichne } from './hilfen';

const NUTZER = [
  { id: 'user-1', email: 'owner@beispiel-ag.de', name: 'Olivia Owner', ist_aktiv: true },
  { id: 'user-2', email: 'vertretung@beispiel-ag.de', name: 'Viktor Vertretung', ist_aktiv: true },
];

function grundrouten() {
  return [
    { pfad: '/api/v1/auth/me', koerper: PROFIL },
    { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    { pfad: '/api/v1/admin/users', koerper: NUTZER },
    { pfad: /\/bewertungen$/, koerper: [] },
  ];
}

describe('Prozessliste', () => {
  it('zeigt einen Hinweis, wenn im eigenen Bereich nichts erfasst ist', async () => {
    fetchAttrappe([...grundrouten(), { pfad: '/api/v1/prozesse', koerper: [] }]);
    zeichne('/de/prozesse');
    expect(
      await screen.findByText('In Ihrem Bereich ist noch kein Prozessobjekt erfasst.'),
    ).toBeInTheDocument();
  });

  it('meldet einen Serverfehler sichtbar', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', status: 500, koerper: { detail: 'kaputt' } },
    ]);
    zeichne('/de/prozesse');
    expect(await screen.findByRole('alert')).toHaveTextContent('Es ist ein Fehler aufgetreten');
  });

  it('verlinkt in die Detailansicht', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      { pfad: '/api/v1/prozesse/p-1', koerper: prozess() },
    ]);
    zeichne('/de/prozesse');
    await userEvent.click(await screen.findByRole('link', { name: 'Rechnungspruefung' }));
    expect(
      await screen.findByRole('heading', { name: 'Rechnungspruefung', level: 1 }),
    ).toBeInTheDocument();
  });
});

describe('Prozessdetail', () => {
  it('zeigt die abgeleiteten Felder als schreibgeschuetzte Angaben', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/api/v1/prozesse/p-1',
        koerper: prozess({ reichweite: 'unternehmen', kritikalitaet: 3, mitbestimmung_flag: true }),
      },
    ]);
    zeichne('/de/prozesse/p-1');
    expect(await screen.findByTestId('reichweite')).toHaveTextContent('unternehmen');
    expect(screen.getByTestId('kritikalitaet')).toHaveTextContent('3');
    expect(screen.getByTestId('mitbestimmung')).toHaveTextContent('Ja');
    // Die abgeleiteten Werte sind Text, kein Eingabefeld.
    const bereich = screen.getByText('Abgeleitet — nicht eingebbar').closest('section');
    expect(within(bereich as HTMLElement).queryByRole('textbox')).toBeNull();
  });

  it('listet die umsetzenden Landesorganisationen', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/api/v1/prozesse/p-1',
        koerper: prozess({
          umsetzungen: [
            {
              id: 'u-1',
              prozessobjekt_id: 'p-1',
              land_org_id: 'org-de',
              lokale_abweichung: 'Freigabegrenze 5.000 EUR',
            },
            {
              id: 'u-2',
              prozessobjekt_id: 'p-1',
              land_org_id: 'org-fr',
              lokale_abweichung: null,
            },
          ],
        }),
      },
    ]);
    zeichne('/de/prozesse/p-1');
    expect(await screen.findByText(/LAND-DE — Freigabegrenze 5.000 EUR/)).toBeInTheDocument();
    expect(screen.getByText('LAND-FR')).toBeInTheDocument();
  });

  it('zeigt einen Hinweis ohne Umsetzung', async () => {
    fetchAttrappe([...grundrouten(), { pfad: '/api/v1/prozesse/p-1', koerper: prozess() }]);
    zeichne('/de/prozesse/p-1');
    expect(await screen.findByText('Noch keine Umsetzung erfasst.')).toBeInTheDocument();
  });

  it('meldet einen fehlgeschlagenen Abruf', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse/p-1', status: 403, koerper: { detail: 'ausserhalb' } },
    ]);
    zeichne('/de/prozesse/p-1');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});

describe('Prozessformular', () => {
  it('fragt genau die zehn Felder ab und keine abgeleiteten', async () => {
    fetchAttrappe(grundrouten());
    zeichne('/de/prozesse/neu');
    await screen.findByLabelText('Name');
    for (const feld of [
      'Name',
      'Prozess-Owner',
      'Stellvertretung',
      'Prozessgeber (INT)',
      'Lieferant',
      'Prozessschritte',
      'Ergebnis',
      'Kundenkreis',
      'Ausfallfolge',
    ]) {
      expect(screen.getByLabelText(feld)).toBeInTheDocument();
    }
    expect(screen.queryByLabelText('Reichweite')).toBeNull();
    expect(screen.queryByLabelText('Kritikalität')).toBeNull();
    expect(screen.queryByLabelText('Mitbestimmung berührt')).toBeNull();
  });

  it('legt einen Prozess mit zwei Umsetzungen an und springt in die Detailansicht', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', methode: 'POST', status: 201, koerper: prozess() },
      { pfad: '/api/v1/prozesse/p-1', koerper: prozess() },
    ]);
    zeichne('/de/prozesse/neu');

    await userEvent.type(await screen.findByLabelText('Name'), 'Rechnungspruefung');
    await userEvent.selectOptions(screen.getByLabelText('Prozess-Owner'), 'user-1');
    await userEvent.selectOptions(screen.getByLabelText('Stellvertretung'), 'user-2');
    await userEvent.selectOptions(screen.getByLabelText('Prozessgeber (INT)'), 'org-int');
    await userEvent.type(screen.getByLabelText('Lieferant'), 'Kreditoren');
    await userEvent.selectOptions(screen.getByLabelText('Kundenkreis'), 'bereich');
    await userEvent.selectOptions(screen.getByLabelText('Ausfallfolge'), 'spuerbar');
    await userEvent.click(screen.getByLabelText('LAND-DE'));
    await userEvent.click(screen.getByLabelText('LAND-FR'));
    await userEvent.click(screen.getByRole('button', { name: 'Speichern' }));

    await screen.findByRole('heading', { name: 'Rechnungspruefung', level: 1 });
    const angelegt = aufrufe.find((a) => a.methode === 'POST');
    expect(angelegt?.koerper).toMatchObject({
      name: 'Rechnungspruefung',
      owner_user_id: 'user-1',
      stellvertretung_user_id: 'user-2',
      prozessgeber_org_id: 'org-int',
      customer: 'bereich',
      ausfallfolge: 'spuerbar',
      umsetzung_land_org_ids: ['org-de', 'org-fr'],
    });
    // Abgeleitete Felder werden nicht mitgeschickt.
    expect(angelegt?.koerper).not.toHaveProperty('reichweite');
    expect(angelegt?.koerper).not.toHaveProperty('kritikalitaet');
  });

  it('nimmt eine Umsetzung wieder zurueck', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', methode: 'POST', status: 201, koerper: prozess() },
      { pfad: '/api/v1/prozesse/p-1', koerper: prozess() },
    ]);
    zeichne('/de/prozesse/neu');
    await userEvent.type(await screen.findByLabelText('Name'), 'X');
    await userEvent.selectOptions(screen.getByLabelText('Stellvertretung'), 'user-2');
    await userEvent.selectOptions(screen.getByLabelText('Prozessgeber (INT)'), 'org-int');
    await userEvent.click(screen.getByLabelText('LAND-DE'));
    await userEvent.click(screen.getByLabelText('LAND-DE'));
    await userEvent.click(screen.getByRole('button', { name: 'Speichern' }));
    await waitFor(() => expect(aufrufe.some((a) => a.methode === 'POST')).toBe(true));
    expect(
      (aufrufe.find((a) => a.methode === 'POST')?.koerper as { umsetzung_land_org_ids: string[] })
        .umsetzung_land_org_ids,
    ).toEqual([]);
  });

  it('zeigt die Fehlermeldung des Servers', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/api/v1/prozesse',
        methode: 'POST',
        status: 403,
        koerper: { detail: 'Prozessobjekte darf nur ein Prozess-Owner anlegen' },
      },
    ]);
    zeichne('/de/prozesse/neu');
    await userEvent.type(await screen.findByLabelText('Name'), 'X');
    await userEvent.selectOptions(screen.getByLabelText('Stellvertretung'), 'user-2');
    await userEvent.selectOptions(screen.getByLabelText('Prozessgeber (INT)'), 'org-int');
    await userEvent.click(screen.getByRole('button', { name: 'Speichern' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Prozessobjekte darf nur ein Prozess-Owner anlegen',
    );
  });

  it('kommt ohne Nutzerliste aus, wenn die Rolle sie nicht abrufen darf', async () => {
    fetchAttrappe([
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
      { pfad: '/api/v1/admin/users', status: 403, koerper: { detail: 'nein' } },
    ]);
    zeichne('/de/prozesse/neu');
    const owner = await screen.findByLabelText('Prozess-Owner');
    await waitFor(() =>
      expect(within(owner).getByText('Olivia Owner')).toBeInTheDocument(),
    );
  });

  it('meldet einen Fehler beim Laden der Organisationseinheiten', async () => {
    fetchAttrappe([
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      { pfad: '/api/v1/organisationseinheiten', status: 500, koerper: {} },
      { pfad: '/api/v1/admin/users', koerper: NUTZER },
    ]);
    zeichne('/de/prozesse/neu');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
