/**
 * Prozess-Modul in der Oberflaeche (Architektur 8.1, 9.1).
 */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { DatenobjektKatalog } from '@/api/typen';

import { EINHEITEN, PROFIL, fetchAttrappe, prozess, zeichne, type Route } from './hilfen';

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
    { pfad: '/api/v1/tools', koerper: [] },
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

  it('faerbt das Tier-Abzeichen nach seiner Stufe', async () => {
    // Tier 3 rot, Tier 2 gelb, Tier 1 neutral: die Liste soll die Schwere auf
    // einen Blick zeigen, ohne dass man die Zahl lesen muss.
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/api/v1/prozesse',
        koerper: [
          prozess({ id: 'p-1', name: 'Hoch', tier: 3, mitbestimmung_flag: true }),
          prozess({ id: 'p-2', name: 'Mittel', tier: 2 }),
          prozess({ id: 'p-3', name: 'Niedrig', tier: 1 }),
        ],
      },
    ]);
    zeichne('/de/prozesse');
    expect(await screen.findByText('Tier 3')).toBeInTheDocument();
    expect(screen.getByText('Tier 2')).toBeInTheDocument();
    expect(screen.getByText('Tier 1')).toBeInTheDocument();
    expect(screen.getByText('MB')).toBeInTheDocument();
  });

  it('verlinkt in die Detailansicht', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      { pfad: '/api/v1/prozesse/p-1', koerper: prozess() },
    ]);
    zeichne('/de/prozesse');
    await userEvent.click(await screen.findByRole('link', { name: /Rechnungspruefung/ }));
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
    expect(await screen.findByTestId('reichweite')).toHaveTextContent('Unternehmen');
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
    expect(await screen.findByText('Finance — Land DE')).toBeInTheDocument();
    expect(screen.getByText('Freigabegrenze 5.000 EUR')).toBeInTheDocument();
    expect(screen.getByText('Finance — Land FR')).toBeInTheDocument();
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
    await userEvent.click(screen.getByRole('checkbox', { name: 'Finance — Land DE' }));
    await userEvent.click(screen.getByRole('checkbox', { name: 'Finance — Land FR' }));
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
    await userEvent.click(screen.getByRole('checkbox', { name: 'Finance — Land DE' }));
    await userEvent.click(screen.getByRole('checkbox', { name: 'Finance — Land DE' }));
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
    await waitFor(() => expect(within(owner).getByText('Olivia Owner')).toBeInTheDocument());
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

// --- Umsetzungsplan AP-1: Kanten, Bearbeiten, Status ---------------------

const DATENOBJEKTE: DatenobjektKatalog[] = [
  {
    id: 'do-1',
    name: 'Entgeltdaten',
    fachbereich_id: 'fb-1',
    kategorie: 'besondere_kategorie',
    quellsystem: 'SAP HCM',
  },
  {
    id: 'do-2',
    name: 'Buchungsjournal',
    fachbereich_id: 'fb-1',
    kategorie: null,
    quellsystem: null,
  },
];

function mitBestand(weitere: Route[] = []) {
  return [
    ...grundrouten(),
    ...weitere,
    { pfad: '/api/v1/datenobjekte/katalog', koerper: DATENOBJEKTE },
    { pfad: '/api/v1/datenobjekte', koerper: DATENOBJEKTE },
  ];
}

describe('Prozessformular — Referenzen statt Freitext', () => {
  it('bietet alle vier SIPOC-Kanten als Referenz-Waehler an', async () => {
    fetchAttrappe(mitBestand([{ pfad: '/api/v1/prozesse', koerper: [prozess({ id: 'p-9' })] }]));
    zeichne('/de/prozesse/neu');
    for (const feld of [
      'Vorgelagerte Prozesse',
      'Input — Datenobjekte',
      'Output — Datenobjekte',
      'Nachgelagerte Prozesse',
    ]) {
      expect(await screen.findByLabelText(feld)).toBeInTheDocument();
    }
  });

  it('schickt die gewaehlten Datenobjekte und Kettenglieder mit', async () => {
    const { aufrufe } = fetchAttrappe(
      mitBestand([
        { pfad: '/api/v1/prozesse', koerper: [prozess({ id: 'p-9', name: 'Zahlungslauf' })] },
        { pfad: '/api/v1/prozesse', methode: 'POST', status: 201, koerper: prozess() },
        { pfad: '/api/v1/prozesse/p-1', koerper: prozess() },
      ]),
    );
    zeichne('/de/prozesse/neu');

    await userEvent.type(await screen.findByLabelText('Name'), 'Rechnungspruefung');
    await userEvent.selectOptions(screen.getByLabelText('Prozess-Owner'), 'user-1');
    await userEvent.selectOptions(screen.getByLabelText('Stellvertretung'), 'user-2');
    await userEvent.selectOptions(screen.getByLabelText('Prozessgeber (INT)'), 'org-int');

    await userEvent.type(screen.getByLabelText('Input — Datenobjekte'), 'Entgelt');
    await userEvent.click(await screen.findByText('Entgeltdaten'));
    await userEvent.type(screen.getByLabelText('Output — Datenobjekte'), 'Buchung');
    await userEvent.click(await screen.findByText('Buchungsjournal'));
    await userEvent.type(screen.getByLabelText('Nachgelagerte Prozesse'), 'Zahlung');
    await userEvent.click(await screen.findByText('Zahlungslauf'));

    await userEvent.click(screen.getByRole('button', { name: 'Speichern' }));
    await waitFor(() => expect(aufrufe.some((a) => a.methode === 'POST')).toBe(true));

    expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toMatchObject({
      input_datenobjekt_ids: ['do-1'],
      output_datenobjekt_ids: ['do-2'],
      nachgelagert_ids: ['p-9'],
    });
  });

  it('zeigt die Kategorie eines Datenobjekts schon bei der Auswahl', async () => {
    fetchAttrappe(mitBestand([{ pfad: '/api/v1/prozesse', koerper: [] }]));
    zeichne('/de/prozesse/neu');
    await userEvent.type(await screen.findByLabelText('Input — Datenobjekte'), 'Entgelt');
    const liste = screen.getByRole('listbox', { name: 'Input — Datenobjekte' });
    expect(within(liste).getByText('Personenbezogen — besonders')).toBeInTheDocument();
    expect(within(liste).getByText(/SAP HCM/)).toBeInTheDocument();
  });

  it('warnt ab dem achten Prozessschritt', async () => {
    fetchAttrappe(mitBestand([{ pfad: '/api/v1/prozesse', koerper: [] }]));
    zeichne('/de/prozesse/neu');
    const schritte = await screen.findByLabelText('Prozessschritte');
    await userEvent.type(schritte, 'a;b;c;d;e;f;g');
    expect(screen.queryByText(/falsche Flughöhe/)).toBeNull();
    await userEvent.type(schritte, ';h');
    expect(screen.getByText(/falsche Flughöhe/)).toBeInTheDocument();
  });

  it('fuellt beim Bearbeiten vor und schickt eine Aenderung', async () => {
    const { aufrufe } = fetchAttrappe(
      mitBestand([
        { pfad: '/api/v1/prozesse', koerper: [] },
        {
          pfad: '/api/v1/prozesse/p-1',
          koerper: prozess({ input_datenobjekt_ids: ['do-1'] }),
        },
        { pfad: '/api/v1/prozesse/p-1', methode: 'PATCH', koerper: prozess() },
      ]),
    );
    zeichne('/de/prozesse/p-1/bearbeiten');

    expect(await screen.findByLabelText('Name')).toHaveValue('Rechnungspruefung');
    expect(screen.getByRole('button', { name: 'Entgeltdaten entfernen' })).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Entgeltdaten entfernen' }));
    await userEvent.click(screen.getByRole('button', { name: 'Speichern' }));
    await waitFor(() => expect(aufrufe.some((a) => a.methode === 'PATCH')).toBe(true));
    expect(aufrufe.find((a) => a.methode === 'PATCH')?.koerper).toMatchObject({
      input_datenobjekt_ids: [],
    });
  });
});

describe('Prozessdetail — Kanten, Wirkung und Status', () => {
  it('zeigt Datenobjekte und Kette als Verweise und die Wirkung transitiv', async () => {
    fetchAttrappe(
      mitBestand([
        {
          pfad: '/api/v1/prozesse/p-1',
          koerper: prozess({
            input_datenobjekt_ids: ['do-1'],
            output_datenobjekt_ids: ['do-2'],
            nachgelagert_ids: ['p-2'],
          }),
        },
        {
          pfad: '/api/v1/prozesse',
          koerper: [
            prozess({ input_datenobjekt_ids: ['do-1'], nachgelagert_ids: ['p-2'] }),
            prozess({ id: 'p-2', name: 'KPI-Report', nachgelagert_ids: ['p-3'] }),
            prozess({ id: 'p-3', name: 'Produktionsfreigabe' }),
          ],
        },
      ]),
    );
    zeichne('/de/prozesse/p-1');

    expect(await screen.findByText('Entgeltdaten')).toBeInTheDocument();
    expect(screen.getByText('Buchungsjournal')).toBeInTheDocument();

    // Abwaerts zaehlt die ganze Kette, nicht nur die direkte Kante (A.4.3).
    const abwaerts = screen.getByTestId('wirkung-abwaerts');
    expect(within(abwaerts).getByText('KPI-Report')).toBeInTheDocument();
    expect(within(abwaerts).getByText('Produktionsfreigabe')).toBeInTheDocument();
  });

  it('nennt den Grund, wenn die Aktivierung abgelehnt wird', async () => {
    fetchAttrappe(
      mitBestand([
        { pfad: '/api/v1/prozesse/p-1', koerper: prozess() },
        { pfad: '/api/v1/prozesse', koerper: [prozess()] },
        {
          pfad: '/api/v1/prozesse/p-1',
          methode: 'PATCH',
          status: 422,
          koerper: { detail: 'Ein Prozessobjekt wird erst nach einer Bewertung aktiv' },
        },
      ]),
    );
    zeichne('/de/prozesse/p-1');
    await userEvent.click(await screen.findByRole('button', { name: 'Aktivieren' }));
    expect(
      await screen.findByText('Ein Prozessobjekt wird erst nach einer Bewertung aktiv'),
    ).toBeInTheDocument();
  });

  it('bietet den Weg ins Bearbeiten-Formular an', async () => {
    fetchAttrappe(
      mitBestand([
        { pfad: '/api/v1/prozesse/p-1', koerper: prozess() },
        { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      ]),
    );
    zeichne('/de/prozesse/p-1');
    expect(await screen.findByRole('link', { name: 'Bearbeiten' })).toHaveAttribute(
      'href',
      '/de/prozesse/p-1/bearbeiten',
    );
  });
});
