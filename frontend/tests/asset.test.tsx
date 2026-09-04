/**
 * Asset-Management in der Oberflaeche (Architektur 8.3).
 */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { DatenObjekt, ToolObjekt } from '@/api/typen';
import {
  EINHEITEN,
  FACHBEREICHE,
  PROFIL,
  fetchAttrappe,
  geerbt,
  prozess,
  tool,
  zeichne,
  type Route,
} from './hilfen';

function datenobjekt(ueberschreibungen: Partial<DatenObjekt> = {}): DatenObjekt {
  return {
    id: 'do-1',
    name: 'Kreditorenstamm',
    beschreibung: '',
    kategorie: null,
    fachbereich_id: 'fb-1',
    quellsystem: null,
    herkunft: 'manuell',
    quelle: null,
    externe_id: null,
    status: 'bestaetigt',
    metadaten: {},
    schreibgeschuetzte_felder: [],
    rechte: { bearbeiten: true, kategorisieren: true, anker_aendern: true, bestaetigen: true },
    ...ueberschreibungen,
  };
}

function grundrouten(): Route[] {
  return [
    { pfad: '/api/v1/auth/me', koerper: PROFIL },
    { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    { pfad: /\/bewertungen$/, koerper: [] },
    { pfad: /\/compliance$/, koerper: { farbe: 'gruen', offene_abweichungen: [], verlauf: [] } },
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

  it('nennt Technologie, Lauftyp und Einstufung je Zeile', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/api/v1/tools',
        koerper: [tool({ lauftyp: 'geplant', geerbt: geerbt({ kritikalitaet: 3, tier: 3 }) })],
      },
    ]);
    zeichne('/de/tools');
    const zeile = await screen.findByRole('link', { name: /Rechnungs-Skript/ });
    expect(zeile).toHaveTextContent('Apps Script');
    expect(zeile).toHaveTextContent('Geplant');
    expect(zeile).toHaveTextContent('Tier 3');
    expect(zeile).toHaveTextContent('Gestaltend');
  });

  it('markiert ein Tool ohne Attestierung', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/api/v1/tools',
        koerper: [
          tool({
            attest_entscheidung_ueber_personen: null,
            attest_mensch_dazwischen: null,
            attest_undeklarierte_quellen: null,
            attestiert_am: null,
            attestiert_von_user_id: null,
            attestierung_vollstaendig: false,
            wirkungsart: null,
            wirkungsart_grund: 'offen',
          }),
        ],
      },
    ]);
    zeichne('/de/tools');
    expect(await screen.findByText('Attestierung fehlt')).toBeInTheDocument();
  });

  it('filtert die Liste ueber die Suche', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/api/v1/tools',
        koerper: [tool(), tool({ id: 'tool-2', name: 'Nachtlauf', technologie: null })],
      },
    ]);
    zeichne('/de/tools');
    await screen.findByRole('link', { name: /Rechnungs-Skript/ });
    await userEvent.type(screen.getByLabelText('Suchen'), 'Nacht');
    expect(screen.queryByRole('link', { name: /Rechnungs-Skript/ })).toBeNull();
    expect(screen.getByRole('link', { name: /Nachtlauf/ })).toBeInTheDocument();
  });

  it('legt ein Tool mit Owner, Technologie und Lauftyp an', async () => {
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
    await userEvent.click(await screen.findByRole('button', { name: 'Tool-Objekt anlegen' }));
    const blatt = screen.getByRole('dialog');
    await userEvent.type(within(blatt).getByLabelText('Name'), 'Neues Tool');
    // Erst die Einheit, dann die Personen: wählbar ist, wer *dort* technischer
    // Owner ist (docs/rollen-und-scopes.md, 6). Vorher stand die Auswahl in der
    // Nutzerverwaltung — die jeder Fachrolle mit 403 antwortet.
    await userEvent.selectOptions(within(blatt).getByLabelText('Organisationseinheit'), 'org-de');
    await userEvent.selectOptions(within(blatt).getByLabelText('Technischer Owner'), 'user-9');
    await userEvent.selectOptions(within(blatt).getByLabelText('Stellvertretung'), 'user-9');
    await userEvent.selectOptions(within(blatt).getByLabelText('Technologie'), 'appsheet');
    await userEvent.selectOptions(within(blatt).getByLabelText('Lauftyp'), 'geplant');
    await userEvent.click(within(blatt).getByRole('button', { name: 'Speichern' }));

    await screen.findByRole('link', { name: /Neues Tool/ });
    expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
      name: 'Neues Tool',
      technischer_owner_user_id: 'user-9',
      stellvertretung_user_id: 'user-9',
      technologie: 'appsheet',
      organisationseinheit_id: 'org-de',
      lauftyp: 'geplant',
    });
  });

  it('bricht die Anlage ab, ohne zu speichern', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/tools', koerper: [tool()] },
    ]);
    zeichne('/de/tools');
    await userEvent.click(await screen.findByRole('button', { name: 'Tool-Objekt anlegen' }));
    await userEvent.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Abbrechen' }),
    );
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(aufrufe.some((a) => a.methode === 'POST')).toBe(false);
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
    await userEvent.click(await screen.findByRole('button', { name: 'Tool-Objekt anlegen' }));
    const blatt = screen.getByRole('dialog');
    await userEvent.type(within(blatt).getByLabelText('Name'), 'X');
    // Die Einheit ist Pflicht — ohne sie kommt das Formular gar nicht bis zum
    // Server, und geprüft werden soll die Antwort des Servers.
    await userEvent.selectOptions(within(blatt).getByLabelText('Organisationseinheit'), 'org-de');
    await userEvent.click(within(blatt).getByRole('button', { name: 'Speichern' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Keine Berechtigung');
  });

  it('meldet einen Ladefehler', async () => {
    fetchAttrappe([...grundrouten(), { pfad: '/api/v1/tools', status: 500, koerper: {} }]);
    zeichne('/de/tools');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});

function unattestiert(ueberschreibungen: Partial<ToolObjekt> = {}): ToolObjekt {
  return tool({
    attest_entscheidung_ueber_personen: null,
    attest_mensch_dazwischen: null,
    attest_undeklarierte_quellen: null,
    attestiert_am: null,
    attestiert_von_user_id: null,
    attestierung_vollstaendig: false,
    wirkungsart: null,
    wirkungsart_grund: 'offen',
    ...ueberschreibungen,
  });
}

describe('Tool-Detail', () => {
  it('zeigt die geerbte Klassifikation mit dem Beitrag jeder Kante', async () => {
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
            beitraege: [
              {
                prozess_id: 'p-1',
                name: 'Rechnungspruefung',
                kritikalitaet: 1,
                reichweite: 'bereich',
                tier: 1,
                mitbestimmung_flag: false,
                k_klassen: [],
                massgeblich: false,
              },
              {
                prozess_id: 'p-2',
                name: 'Zweiter',
                kritikalitaet: 3,
                reichweite: 'extern',
                tier: 3,
                mitbestimmung_flag: false,
                k_klassen: ['K1', 'K4'],
                massgeblich: true,
              },
            ],
          }),
        }),
      },
    ]);
    zeichne('/de/tools/tool-1');
    expect(await screen.findByTestId('geerbt-kritikalitaet')).toHaveTextContent('3');
    expect(screen.getByTestId('geerbt-reichweite')).toHaveTextContent('Extern');
    expect(screen.getByTestId('geerbt-tier')).toHaveTextContent('3');
    expect(screen.getByTestId('geerbt-k-klassen')).toHaveTextContent('K1, K4');
    // Das Maximum bleibt adressierbar: die massgebliche Kante ist benannt.
    expect(screen.getByTestId('geerbt-tier')).toHaveTextContent('Zweiter');
    const kante = screen.getByRole('link', { name: /Zweiter/ });
    expect(kante).toHaveTextContent('Bestimmt das Maximum');
    expect(screen.getByRole('link', { name: /Rechnungspruefung/ })).not.toHaveTextContent(
      'Bestimmt das Maximum',
    );
  });

  it('verlangt bei einem importierten Tool erst die Bestaetigung', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      {
        pfad: '/api/v1/tools/tool-1',
        koerper: (nummer: number) =>
          nummer === 1
            ? tool({
                herkunft: 'importiert',
                status: 'importiert_unbestaetigt',
                schreibgeschuetzte_felder: ['metadaten', 'name', 'technologie'],
              })
            : tool({ herkunft: 'importiert', status: 'bestaetigt' }),
      },
      {
        pfad: '/api/v1/tools/tool-1/bestaetigung',
        methode: 'POST',
        koerper: tool({ herkunft: 'importiert', status: 'bestaetigt' }),
      },
    ]);
    zeichne('/de/tools/tool-1');
    expect(await screen.findByTestId('status')).toHaveTextContent('Importiert, unbestätigt');
    expect(screen.getAllByText(/kann es nicht mit einem Prozess/)).toHaveLength(2);
    expect(screen.queryByTestId('waehler-prozesse')).toBeNull();

    await userEvent.click(screen.getByRole('button', { name: 'Bestätigen' }));
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('Bestätigt'));
    expect(screen.getByTestId('waehler-prozesse')).toBeInTheDocument();
  });

  it('sperrt die Prozessverknuepfung, solange nicht attestiert ist', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      { pfad: '/api/v1/tools/tool-1', koerper: unattestiert() },
    ]);
    zeichne('/de/tools/tool-1');
    await screen.findByRole('heading', { name: 'Attestierungen' });
    expect(screen.getAllByText(/Ohne die drei Erklärungen ist keine Verknüpfung/)).toHaveLength(2);
    expect(screen.queryByTestId('waehler-prozesse')).toBeNull();
    expect(screen.getByTestId('wirkungsart')).toHaveTextContent('Noch offen');
  });

  it('gibt die drei Erklaerungen nach A.6 ab', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      {
        pfad: '/api/v1/tools/tool-1',
        koerper: (nummer: number) => (nummer === 1 ? unattestiert() : tool()),
      },
      { pfad: '/api/v1/tools/tool-1/attestierungen', methode: 'PUT', koerper: tool() },
      {
        pfad: '/api/v1/admin/users',
        koerper: [{ id: 'user-1', name: 'Olivia Owner', email: 'o@x', ist_aktiv: true }],
      },
    ]);
    zeichne('/de/tools/tool-1');

    // Ohne vollstaendige Antworten bleibt der Knopf gesperrt.
    const abgeben = await screen.findByRole('button', { name: 'Erklärung abgeben' });
    expect(abgeben).toBeDisabled();

    for (const [kennung, antwort] of [
      ['attest_entscheidung_ueber_personen', 'Ja'],
      ['attest_mensch_dazwischen', 'Nein'],
      ['attest_undeklarierte_quellen', 'Nein'],
    ] as const) {
      await userEvent.click(
        within(screen.getByTestId(kennung)).getByRole('button', { name: antwort }),
      );
    }
    await userEvent.click(screen.getByRole('button', { name: 'Erklärung abgeben' }));

    expect(aufrufe.find((a) => a.methode === 'PUT')?.koerper).toEqual({
      attest_entscheidung_ueber_personen: true,
      attest_mensch_dazwischen: false,
      attest_undeklarierte_quellen: false,
    });
    const karte = (await screen.findByRole('heading', { name: 'Attestierungen' })).closest(
      'section',
    ) as HTMLElement;
    await waitFor(() => expect(within(karte).getByText('Olivia Owner')).toBeInTheDocument());
  });

  it('verknuepft und loest eine Prozesskante ueber den Referenzwaehler', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      {
        pfad: '/api/v1/tools/tool-1',
        koerper: (nummer: number) =>
          nummer === 1
            ? tool()
            : nummer === 2
              ? tool({
                  prozessobjekt_ids: ['p-1'],
                  geerbt: geerbt({ kritikalitaet: 2, quelle_prozess_ids: ['p-1'] }),
                })
              : tool(),
      },
      {
        pfad: '/api/v1/tools/tool-1/prozesse',
        methode: 'POST',
        status: 201,
        koerper: tool({ prozessobjekt_ids: ['p-1'] }),
      },
      {
        pfad: '/api/v1/tools/tool-1/prozesse/p-1',
        methode: 'DELETE',
        koerper: tool({ prozessobjekt_ids: [] }),
      },
    ]);
    zeichne('/de/tools/tool-1');
    const waehler = await screen.findByTestId('waehler-prozesse');
    await userEvent.click(within(waehler).getByRole('combobox'));
    await userEvent.click(within(waehler).getByRole('button', { name: /Rechnungspruefung/ }));

    await waitFor(() => expect(screen.getByTestId('geerbt-kritikalitaet')).toHaveTextContent('2'));
    expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
      prozessobjekt_id: 'p-1',
    });

    await userEvent.click(
      within(screen.getByTestId('waehler-prozesse')).getByRole('button', {
        name: 'Rechnungspruefung entfernen',
      }),
    );
    await waitFor(() => expect(aufrufe.some((a) => a.methode === 'DELETE')).toBe(true));
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
    const waehler = await screen.findByTestId('waehler-prozesse');
    await userEvent.click(within(waehler).getByRole('combobox'));
    await userEvent.click(within(waehler).getByRole('button', { name: /Rechnungspruefung/ }));
    expect(await screen.findByText(/besteht bereits/)).toBeInTheDocument();
  });

  it('verknuepft ein Datenobjekt mit der gewaehlten Zugriffsart', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      { pfad: '/api/v1/tools/tool-1', koerper: tool() },
      {
        pfad: '/api/v1/datenobjekte/katalog',
        koerper: [
          {
            id: 'do-1',
            name: 'Buchungen',
            beschreibung: '',
            kategorie: 'intern',
            fachbereich_id: 'fb-1',
            quellsystem: 'SAP',
            herkunft: 'manuell',
            quelle: null,
            externe_id: null,
            status: 'bestaetigt',
            metadaten: {},
            schreibgeschuetzte_felder: [],
          },
        ],
      },
      {
        pfad: '/api/v1/tools/tool-1/datenobjekte',
        koerper: (nummer: number) =>
          nummer === 1
            ? []
            : [
                {
                  datenobjekt_id: 'do-1',
                  name: 'Buchungen',
                  kategorie: 'intern',
                  zugriffsart: 'schreiben',
                  im_prozessrahmen: true,
                  kategorie_gedeckt: true,
                },
              ],
      },
      {
        pfad: '/api/v1/tools/tool-1/datenobjekte',
        methode: 'POST',
        status: 201,
        koerper: {},
      },
    ]);
    zeichne('/de/tools/tool-1');
    expect(
      await screen.findByText('Dieses Tool-Objekt greift auf kein Datenobjekt zu.'),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Schreibt' }));
    const waehler = screen.getByTestId('waehler-datenobjekte');
    await userEvent.click(within(waehler).getByRole('combobox'));
    await userEvent.click(within(waehler).getByRole('button', { name: /Buchungen/ }));

    await waitFor(() => expect(screen.getByTestId('nutzung-do-1')).toBeInTheDocument());
    expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
      datenobjekt_id: 'do-1',
      zugriffsart: 'schreiben',
    });
  });

  it('warnt, wenn ein genutztes Datenobjekt ausserhalb des Prozessrahmens liegt', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      { pfad: '/api/v1/tools/tool-1', koerper: tool({ prozessobjekt_ids: ['p-1'] }) },
      {
        pfad: '/api/v1/tools/tool-1/datenobjekte',
        koerper: [
          {
            datenobjekt_id: 'do-1',
            name: 'Gesundheitsakte',
            kategorie: 'besondere_kategorie',
            zugriffsart: 'lesen',
            im_prozessrahmen: false,
            kategorie_gedeckt: false,
          },
          {
            datenobjekt_id: 'do-2',
            name: 'Debitorenstamm',
            kategorie: 'intern',
            zugriffsart: 'lesen',
            im_prozessrahmen: false,
            kategorie_gedeckt: true,
          },
        ],
      },
    ]);
    zeichne('/de/tools/tool-1');
    expect(await screen.findByText(/1 genutzte Datenobjekte liegen außerhalb/)).toBeInTheDocument();
    expect(screen.getByTestId('nutzung-do-1')).toHaveTextContent('Außerhalb des Prozessrahmens');
    expect(screen.getByTestId('nutzung-do-2')).toHaveTextContent('Nicht deklariert');
  });

  it('aendert die Zugriffsart und entfernt eine Datenkante', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      { pfad: '/api/v1/tools/tool-1', koerper: tool() },
      {
        pfad: '/api/v1/tools/tool-1/datenobjekte',
        koerper: [
          {
            datenobjekt_id: 'do-1',
            name: 'Buchungen',
            kategorie: 'intern',
            zugriffsart: 'lesen',
            im_prozessrahmen: true,
            kategorie_gedeckt: true,
          },
        ],
      },
      { pfad: '/api/v1/tools/tool-1/datenobjekte/do-1', methode: 'PATCH', koerper: {} },
      {
        pfad: '/api/v1/tools/tool-1/datenobjekte/do-1',
        methode: 'DELETE',
        status: 204,
        koerper: {},
      },
    ]);
    zeichne('/de/tools/tool-1');
    await userEvent.selectOptions(
      await screen.findByLabelText('Zugriffsart — Buchungen'),
      'lesen_schreiben',
    );
    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'PATCH')?.koerper).toEqual({
        zugriffsart: 'lesen_schreiben',
      }),
    );

    await userEvent.click(
      screen.getByRole('button', { name: 'Buchungen — Verknüpfung entfernen' }),
    );
    await waitFor(() => expect(aufrufe.some((a) => a.methode === 'DELETE')).toBe(true));
  });

  it('nennt den Grund der Wirkungsart', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [] },
      {
        pfad: '/api/v1/tools/tool-1',
        koerper: tool({ wirkungsart: 'veraendernd', wirkungsart_grund: 'kein_mensch' }),
      },
    ]);
    zeichne('/de/tools/tool-1');
    const feld = await screen.findByTestId('wirkungsart');
    expect(feld).toHaveTextContent('Verändernd');
    expect(feld).toHaveTextContent('Kein Mensch zwischen Output und Wirkung');
  });

  it('aendert die Stammdaten einzeln', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [] },
      {
        pfad: '/api/v1/admin/users',
        koerper: [{ id: 'user-9', name: 'Tina Technik', email: 't@x', ist_aktiv: true }],
      },
      { pfad: '/api/v1/tools/tool-1', koerper: tool() },
      { pfad: '/api/v1/tools/tool-1', methode: 'PATCH', koerper: tool() },
    ]);
    zeichne('/de/tools/tool-1');
    await userEvent.selectOptions(await screen.findByLabelText('Lauftyp'), 'geplant');
    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'PATCH')?.koerper).toEqual({ lauftyp: 'geplant' }),
    );

    for (const [beschriftung, wert, feld] of [
      ['Technischer Owner', 'user-9', 'technischer_owner_user_id'],
      ['Stellvertretung', 'user-9', 'stellvertretung_user_id'],
      ['Technologie', 'appsheet', 'technologie'],
      ['Organisationseinheit', 'org-de', 'organisationseinheit_id'],
    ] as const) {
      await userEvent.selectOptions(screen.getByLabelText(beschriftung), wert);
      await waitFor(() =>
        expect(aufrufe.filter((a) => a.methode === 'PATCH').at(-1)?.koerper).toEqual({
          [feld]: wert,
        }),
      );
    }
  });

  it('behaelt eine importierte Technologie, die nicht in der Liste steht', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [] },
      { pfad: '/api/v1/tools/tool-1', koerper: tool({ technologie: 'powershell' }) },
    ]);
    zeichne('/de/tools/tool-1');
    // Der Bestandswert bleibt waehlbar, statt beim naechsten Speichern zu verschwinden.
    expect(await screen.findByRole('option', { name: 'powershell' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Rechnungs-Skript' }).nextSibling).toHaveTextContent(
      'powershell',
    );
  });

  it('zeigt ein Datenobjekt ohne Kategorie und ohne Quellsystem', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [] },
      { pfad: '/api/v1/tools/tool-1', koerper: tool() },
      {
        pfad: '/api/v1/datenobjekte/katalog',
        koerper: [
          {
            id: 'do-9',
            name: 'Unklassifiziert',
            beschreibung: '',
            kategorie: null,
            fachbereich_id: null,
            quellsystem: null,
            herkunft: 'manuell',
            quelle: null,
            externe_id: null,
            status: 'bestaetigt',
            metadaten: {},
            schreibgeschuetzte_felder: [],
          },
        ],
      },
    ]);
    zeichne('/de/tools/tool-1');
    const waehler = await screen.findByTestId('waehler-datenobjekte');
    await userEvent.click(within(waehler).getByRole('combobox'));
    expect(within(waehler).getByRole('button', { name: 'Unklassifiziert' })).toBeInTheDocument();
  });

  it('nennt bei einer Kante ohne Reichweite nur die Kritikalitaet', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      {
        pfad: '/api/v1/tools/tool-1',
        koerper: tool({
          prozessobjekt_ids: ['p-1'],
          geerbt: geerbt({
            quelle_prozess_ids: ['p-1'],
            beitraege: [
              {
                prozess_id: 'p-1',
                name: 'Rechnungspruefung',
                kritikalitaet: 0,
                reichweite: null,
                tier: null,
                mitbestimmung_flag: false,
                k_klassen: [],
                massgeblich: true,
              },
            ],
          }),
        }),
      },
    ]);
    zeichne('/de/tools/tool-1');
    const kante = await screen.findByRole('link', { name: /Rechnungspruefung/ });
    expect(kante).toHaveTextContent('Kritikalität 0');
    expect(screen.getByTestId('geerbt-tier')).toHaveTextContent('—');
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

  it('legt ein Datenobjekt als Output des eigenen Prozesses an', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/datenobjekte', koerper: [] },
      { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      {
        pfad: '/api/v1/datenobjekte',
        methode: 'POST',
        status: 201,
        koerper: datenobjekt({ name: 'Entgeltdaten', quellsystem: 'SAP HCM' }),
      },
    ]);
    zeichne('/de/datenobjekte');

    await userEvent.click(
      (await screen.findAllByRole('button', { name: 'Datenobjekt anlegen' }))[0],
    );
    const blatt = screen.getByRole('dialog', { name: 'Datenobjekt anlegen' });
    await userEvent.type(within(blatt).getByLabelText('Name'), 'Entgeltdaten');
    await userEvent.selectOptions(within(blatt).getByLabelText('Kategorie'), 'besondere_kategorie');
    // Ein Prozess-Owner ohne Datenobjekt-Owner-Rolle hat genau einen Weg: den
    // gebenden Prozess. Ein Fachbereichsfeld gibt es fuer ihn nicht.
    expect(within(blatt).queryByLabelText('Fachbereich')).not.toBeInTheDocument();
    await userEvent.selectOptions(within(blatt).getByLabelText('Gebender Prozess'), 'p-1');
    await userEvent.type(within(blatt).getByLabelText('Quellsystem'), 'SAP HCM');
    await userEvent.click(within(blatt).getByRole('button', { name: 'Speichern' }));

    await waitFor(() => expect(aufrufe.some((a) => a.methode === 'POST')).toBe(true));
    expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toMatchObject({
      name: 'Entgeltdaten',
      kategorie: 'besondere_kategorie',
      quellsystem: 'SAP HCM',
      prozessobjekt_id: 'p-1',
      fachbereich_id: null,
    });
    expect(await screen.findByText('Entgeltdaten')).toBeInTheDocument();
  });

  it('meldet einen abgelehnten Anlageversuch', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/datenobjekte', koerper: [] },
      { pfad: '/api/v1/prozesse', koerper: [prozess()] },
      {
        pfad: '/api/v1/datenobjekte',
        methode: 'POST',
        status: 403,
        koerper: { detail: 'Keine Berechtigung' },
      },
    ]);
    zeichne('/de/datenobjekte');
    await userEvent.click(
      (await screen.findAllByRole('button', { name: 'Datenobjekt anlegen' }))[0],
    );
    const blatt = screen.getByRole('dialog', { name: 'Datenobjekt anlegen' });
    await userEvent.type(within(blatt).getByLabelText('Name'), 'X');
    await userEvent.click(within(blatt).getByRole('button', { name: 'Speichern' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Keine Berechtigung');
  });

  it('meldet einen Ladefehler', async () => {
    fetchAttrappe([...grundrouten(), { pfad: '/api/v1/datenobjekte', status: 500, koerper: {} }]);
    zeichne('/de/datenobjekte');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('bietet ohne einen Weg kein Anlegen an und sagt warum', async () => {
    // Prozess-Owner ohne schreibbaren Prozess und ohne Datenobjekt-Owner-Rolle.
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/datenobjekte', koerper: [datenobjekt()] },
      { pfad: '/api/v1/prozesse', koerper: [] },
    ]);
    zeichne('/de/datenobjekte');
    expect(await screen.findByText('Kreditorenstamm')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Datenobjekt anlegen' })).not.toBeInTheDocument();
    expect(screen.getByText(/Rolle Datenobjekt-Owner/)).toBeInTheDocument();
  });

  it('belegt fuer den Datenobjekt-Owner den einen Fachbereich vor und sperrt ihn', async () => {
    const { aufrufe } = fetchAttrappe([
      // Welche Bereiche wählbar sind, sagt der Server — nicht das Profil.
      { pfad: /\/fachbereiche\?fuer_rolle=datenobjekt_owner/, koerper: FACHBEREICHE },
      ...grundrouten(),
      { pfad: '/api/v1/fachbereiche', koerper: FACHBEREICHE },
      { pfad: '/api/v1/datenobjekte', koerper: [] },
      { pfad: '/api/v1/prozesse', koerper: [] },
      {
        pfad: '/api/v1/datenobjekte',
        methode: 'POST',
        status: 201,
        koerper: datenobjekt({ name: 'Kassenbelege' }),
      },
    ]);
    zeichne('/de/datenobjekte');
    await userEvent.click(
      (await screen.findAllByRole('button', { name: 'Datenobjekt anlegen' }))[0],
    );
    const blatt = screen.getByRole('dialog', { name: 'Datenobjekt anlegen' });
    const fachbereich = within(blatt).getByLabelText('Fachbereich');
    expect(fachbereich).toHaveValue('fb-1');
    expect(fachbereich).toBeDisabled();
    expect(within(blatt).queryByLabelText('Gebender Prozess')).not.toBeInTheDocument();
    await userEvent.type(within(blatt).getByLabelText('Name'), 'Kassenbelege');
    await userEvent.click(within(blatt).getByRole('button', { name: 'Speichern' }));
    await waitFor(() => expect(aufrufe.some((a) => a.methode === 'POST')).toBe(true));
    expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toMatchObject({
      name: 'Kassenbelege',
      fachbereich_id: 'fb-1',
      prozessobjekt_id: null,
    });
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
    await screen.findByText('Verknüpfte Tool-Objekte');
    expect(screen.getByRole('link', { name: /Rechnungs-Skript/ })).toBeInTheDocument();
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

// --- Umsetzungsplan AP-2: Detailseite und Wirkungsvorschau ---------------

function wirkung(ueberschreibungen: Record<string, unknown> = {}) {
  return {
    kategorie_alt: null,
    kategorie_neu: null,
    prozesse: [],
    tools: [],
    mitbestimmung_neu: 0,
    ...ueberschreibungen,
  };
}

describe('Datenobjekt-Detail', () => {
  const STAND = wirkung({
    prozesse: [
      {
        id: 'p-1',
        name: 'Personalbericht',
        tier: 2,
        mitbestimmung_flag: false,
        mitbestimmung_flag_neu: false,
        als_input: true,
        als_output: false,
      },
    ],
    tools: [{ id: 'tool-1', name: 'Berichtsskript', zugriffsart: 'lesen', ueber_prozess: false }],
  });

  function routen(weitere: Route[] = []) {
    return [
      ...grundrouten(),
      { pfad: '/api/v1/datenobjekte/do-1/wirkung', koerper: STAND },
      { pfad: '/api/v1/datenobjekte/do-1', koerper: datenobjekt({ quellsystem: 'SAP HCM' }) },
      ...weitere,
    ];
  }

  it('zeigt beide Rueckwaertssichten', async () => {
    fetchAttrappe(routen());
    zeichne('/de/datenobjekte/do-1');

    expect(await screen.findByRole('heading', { name: 'Kreditorenstamm' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Personalbericht/ })).toHaveAttribute(
      'href',
      '/de/prozesse/p-1',
    );
    expect(screen.getByRole('link', { name: /Berichtsskript/ })).toHaveAttribute(
      'href',
      '/de/tools/tool-1',
    );
    expect(screen.getByText('Liest')).toBeInTheDocument();
    expect(screen.getByText('Input')).toBeInTheDocument();
  });

  it('zeigt die Wirkung vor der Umklassifizierung und uebernimmt erst danach', async () => {
    const { aufrufe } = fetchAttrappe(
      routen([
        {
          pfad: '/api/v1/datenobjekte/do-1/wirkung?kategorie=besondere_kategorie',
          koerper: wirkung({
            kategorie_neu: 'besondere_kategorie',
            prozesse: [
              {
                id: 'p-1',
                name: 'Personalbericht',
                tier: 2,
                mitbestimmung_flag: false,
                mitbestimmung_flag_neu: true,
                als_input: true,
                als_output: false,
              },
            ],
            tools: [
              { id: 'tool-1', name: 'Berichtsskript', zugriffsart: 'lesen', ueber_prozess: false },
            ],
            mitbestimmung_neu: 1,
          }),
        },
        {
          pfad: '/api/v1/datenobjekte/do-1',
          methode: 'PATCH',
          koerper: datenobjekt({ kategorie: 'besondere_kategorie' }),
        },
      ]),
    );
    zeichne('/de/datenobjekte/do-1');

    await userEvent.selectOptions(await screen.findByLabelText('Kategorie'), 'besondere_kategorie');

    const blatt = await screen.findByRole('dialog', { name: 'Wirkung der Umklassifizierung' });
    expect(within(blatt).getByTestId('wirkung-prozesse')).toHaveTextContent('1');
    expect(within(blatt).getByTestId('wirkung-mitbestimmung')).toHaveTextContent('1');
    expect(within(blatt).getByRole('status')).toHaveTextContent(
      'Diese Änderung macht Prozesse mitbestimmungsrelevant',
    );
    // Bis hierher ist nichts geschrieben worden.
    expect(aufrufe.some((a) => a.methode === 'PATCH')).toBe(false);

    await userEvent.click(within(blatt).getByRole('button', { name: 'Kategorie übernehmen' }));
    await waitFor(() => expect(aufrufe.some((a) => a.methode === 'PATCH')).toBe(true));
    expect(aufrufe.find((a) => a.methode === 'PATCH')?.koerper).toEqual({
      kategorie: 'besondere_kategorie',
    });
  });

  it('verwirft die Umklassifizierung beim Abbrechen', async () => {
    const { aufrufe } = fetchAttrappe(
      routen([
        {
          pfad: '/api/v1/datenobjekte/do-1/wirkung?kategorie=intern',
          koerper: wirkung({ kategorie_neu: 'intern' }),
        },
      ]),
    );
    zeichne('/de/datenobjekte/do-1');
    await userEvent.selectOptions(await screen.findByLabelText('Kategorie'), 'intern');
    const blatt = await screen.findByRole('dialog', { name: 'Wirkung der Umklassifizierung' });
    await userEvent.click(within(blatt).getByRole('button', { name: 'Abbrechen' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(aufrufe.some((a) => a.methode === 'PATCH')).toBe(false);
  });

  it('sperrt die Kategorie ohne Klassifizierungsrecht und zeigt den Fachbereich als Text', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/fachbereiche', koerper: FACHBEREICHE },
      { pfad: '/api/v1/datenobjekte/do-1/wirkung', koerper: STAND },
      {
        pfad: '/api/v1/datenobjekte/do-1',
        koerper: datenobjekt({
          rechte: {
            bearbeiten: true,
            kategorisieren: false,
            anker_aendern: false,
            bestaetigen: false,
          },
        }),
      },
    ]);
    zeichne('/de/datenobjekte/do-1');
    expect(await screen.findByLabelText('Kategorie')).toBeDisabled();
    // Der Owner des gebenden Prozesses pflegt Stammdaten — und erfaehrt, was nicht.
    expect(screen.getByLabelText('Quellsystem')).toBeEnabled();
    expect(screen.getByText(/Kategorie setzt der Datenobjekt-Owner/)).toBeInTheDocument();
    const fachbereich = screen.getByLabelText('Fachbereich');
    expect(fachbereich).toHaveValue('Finance');
    expect(fachbereich).toBeDisabled();
    expect(screen.getByTestId('gebender-prozess')).toHaveTextContent(
      'Kein Prozess erzeugt diese Quelle',
    );
  });

  it('nennt den gebenden Prozess als Verweis', async () => {
    fetchAttrappe([
      // Vor den Standardrouten, weil die erste Antwort auf einen Pfad gewinnt.

      {
        pfad: '/api/v1/datenobjekte/do-1/wirkung',
        koerper: wirkung({
          prozesse: [
            {
              id: 'p-7',
              name: 'Kassenabschluss',
              tier: 1,
              mitbestimmung_flag: false,
              mitbestimmung_flag_neu: false,
              als_input: false,
              als_output: true,
            },
          ],
        }),
      },
      ...routen(),
    ]);
    zeichne('/de/datenobjekte/do-1');
    const gebender = await screen.findByTestId('gebender-prozess');
    expect(within(gebender).getByRole('link', { name: 'Kassenabschluss' })).toHaveAttribute(
      'href',
      '/de/prozesse/p-7',
    );
  });

  it('pflegt das Quellsystem', async () => {
    const { aufrufe } = fetchAttrappe(
      routen([
        {
          pfad: '/api/v1/datenobjekte/do-1',
          methode: 'PATCH',
          koerper: datenobjekt({ quellsystem: 'SAP FI' }),
        },
      ]),
    );
    zeichne('/de/datenobjekte/do-1');
    const feld = await screen.findByLabelText('Quellsystem');
    await userEvent.clear(feld);
    await userEvent.type(feld, 'SAP FI');
    await userEvent.click(screen.getByRole('button', { name: 'Speichern' }));
    await waitFor(() => expect(aufrufe.some((a) => a.methode === 'PATCH')).toBe(true));
    expect(aufrufe.find((a) => a.methode === 'PATCH')?.koerper).toEqual({ quellsystem: 'SAP FI' });
  });

  it('meldet einen Ladefehler', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/datenobjekte/do-1', status: 500, koerper: {} },
    ]);
    zeichne('/de/datenobjekte/do-1');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});

describe('Datenobjekte — Filter und Randfaelle', () => {
  it('filtert die Liste nach Name und Quellsystem', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/api/v1/datenobjekte',
        koerper: [
          datenobjekt({ id: 'do-1', name: 'Kreditorenstamm', quellsystem: 'SAP FI' }),
          datenobjekt({ id: 'do-2', name: 'Entgeltdaten', quellsystem: 'SAP HCM' }),
        ],
      },
    ]);
    zeichne('/de/datenobjekte');
    await screen.findByRole('link', { name: /Kreditorenstamm/ });

    await userEvent.type(screen.getByLabelText('Name'), 'HCM');
    expect(screen.getByRole('link', { name: /Entgeltdaten/ })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Kreditorenstamm/ })).toBeNull();
  });

  it('kennzeichnet ein Datenobjekt ohne Kategorie und ohne Quellsystem', async () => {
    fetchAttrappe([...grundrouten(), { pfad: '/api/v1/datenobjekte', koerper: [datenobjekt()] }]);
    zeichne('/de/datenobjekte');
    const zeile = await screen.findByRole('link', { name: /Kreditorenstamm/ });
    expect(zeile).toHaveTextContent('Ohne Kategorie');
    expect(zeile).toHaveTextContent('Kein Quellsystem angegeben');
  });

  it('weist am importierten Datenobjekt auf das Ursprungssystem hin', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/api/v1/datenobjekte/do-1/wirkung',
        koerper: {
          kategorie_alt: null,
          kategorie_neu: null,
          prozesse: [],
          tools: [],
          mitbestimmung_neu: 0,
        },
      },
      {
        pfad: '/api/v1/datenobjekte/do-1',
        koerper: datenobjekt({ herkunft: 'importiert', schreibgeschuetzte_felder: ['name'] }),
      },
    ]);
    zeichne('/de/datenobjekte/do-1');
    expect(await screen.findByText(/Ursprungssystem/)).toBeInTheDocument();
    expect(
      screen.getByText('Kein Prozessobjekt referenziert dieses Datenobjekt.'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Kein Tool-Objekt greift auf dieses Datenobjekt zu.'),
    ).toBeInTheDocument();
  });

  it('meldet einen abgelehnten Pflegeversuch am Detail', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/api/v1/datenobjekte/do-1/wirkung',
        koerper: {
          kategorie_alt: null,
          kategorie_neu: null,
          prozesse: [],
          tools: [],
          mitbestimmung_neu: 0,
        },
      },
      { pfad: '/api/v1/datenobjekte/do-1', koerper: datenobjekt() },
      {
        pfad: '/api/v1/datenobjekte/do-1',
        methode: 'PATCH',
        status: 403,
        koerper: { detail: 'Keine Schreibberechtigung' },
      },
    ]);
    zeichne('/de/datenobjekte/do-1');
    await userEvent.type(await screen.findByLabelText('Quellsystem'), 'SAP');
    await userEvent.click(screen.getByRole('button', { name: 'Speichern' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Keine Schreibberechtigung');
  });
});
