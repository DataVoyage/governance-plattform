/**
 * Cockpit in der Oberflaeche (Architektur 8.7).
 */

import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { CockpitEintrag, CockpitZeile, CockpitZeilenkopf } from '@/api/typen';
import { zielPfad } from '@/seiten/Cockpit';
import { EINHEITEN, PROFIL, fetchAttrappe, prozess, zeichne, type Route } from './hilfen';

const FACHBEREICHE = [
  { id: 'fb-1', name: 'Finance', code: 'fb-fin' },
  { id: 'fb-2', name: 'HR', code: 'fb-hr' },
];

function kopf(ueberschreibungen: Partial<CockpitZeilenkopf> = {}): CockpitZeilenkopf {
  return {
    schluessel: 'prozesse_ohne_owner',
    titel: 'Prozesse ohne tragenden Owner',
    beschreibung: 'Der eingetragene Owner traegt nicht.',
    anzahl: 0,
    aggregat: null,
    ...ueberschreibungen,
  };
}

function eintrag(ueberschreibungen: Partial<CockpitEintrag> = {}): CockpitEintrag {
  return {
    id: 'p-1',
    titel: 'Rechnungspruefung',
    hinweis: 'Owner ohne Rolle',
    ziel_modul: 'prozesse',
    ziel_filter: { id: 'p-1' },
    ...ueberschreibungen,
  };
}

function zeile(ueberschreibungen: Partial<CockpitZeile> = {}): CockpitZeile {
  return { ...kopf(), eintraege: [], ...ueberschreibungen };
}

function grundrouten(): Route[] {
  return [
    { pfad: '/api/v1/auth/me', koerper: PROFIL },
    { pfad: '/api/v1/fachbereiche', koerper: FACHBEREICHE },
    { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    { pfad: /\/bewertungen$/, koerper: [] },
    { pfad: /\/compliance$/, koerper: [] },
    { pfad: /\/selbstverpflichtungen$/, koerper: [] },
    { pfad: /\/gates$/, koerper: [] },
    { pfad: '/api/v1/gates/ausloeser', koerper: [] },
    { pfad: '/api/v1/tools', koerper: [] },
  ];
}

describe('zielPfad', () => {
  const pfad = (rest: string) => `/de${rest}`;

  it('verlinkt ein Prozessobjekt direkt', () => {
    expect(zielPfad(eintrag(), pfad)).toBe('/de/prozesse/p-1');
  });

  it('verlinkt ein Tool-Objekt direkt', () => {
    expect(zielPfad(eintrag({ ziel_modul: 'tools', ziel_filter: { id: 't-1' } }), pfad)).toBe(
      '/de/tools/t-1',
    );
  });

  it('haengt einen Listenfilter als Query-Parameter an', () => {
    expect(
      zielPfad(
        eintrag({ ziel_modul: 'datenobjekte', ziel_filter: { ohne_kategorie: 'true' } }),
        pfad,
      ),
    ).toBe('/de/datenobjekte?ohne_kategorie=true');
  });

  it('kommt ohne Filter aus', () => {
    expect(zielPfad(eintrag({ ziel_modul: 'lenkung', ziel_filter: {} }), pfad)).toBe(
      '/de/lenkung',
    );
  });
});

describe('Cockpit-Uebersicht', () => {
  it('listet jede Zeile mit ihrer Trefferzahl', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/api/v1/cockpit',
        koerper: [
          kopf({ anzahl: 2 }),
          kopf({ schluessel: 'widersprueche', titel: 'Widersprueche', anzahl: 0 }),
        ],
      },
    ]);
    zeichne('/de/cockpit');
    expect(await screen.findByRole('heading', { name: 'Cockpit' })).toBeInTheDocument();
    expect(screen.getByTestId('anzahl-prozesse_ohne_owner')).toHaveTextContent('2');
    expect(screen.getByTestId('anzahl-widersprueche')).toHaveTextContent('0');
  });

  it('filtert nach Fachbereich und haelt den Filter in der URL', async () => {
    const { aufrufe } = fetchAttrappe([
      ...grundrouten(),
      { pfad: /\/api\/v1\/cockpit/, koerper: [kopf()] },
    ]);
    zeichne('/de/cockpit');
    await userEvent.selectOptions(await screen.findByLabelText('Fachbereich'), 'fb-2');
    expect(
      aufrufe.some((a) => a.url.includes('/api/v1/cockpit?fachbereich_id=fb-2')),
    ).toBe(true);

    // Der Link in die Zeile traegt den Filter weiter.
    const link = screen.getByRole('link', { name: 'Ansehen' });
    expect(link).toHaveAttribute(
      'href',
      '/de/cockpit/prozesse_ohne_owner?fachbereich=fb-2',
    );
  });

  it('meldet einen Ladefehler', async () => {
    fetchAttrappe([...grundrouten(), { pfad: '/api/v1/cockpit', status: 500, koerper: {} }]);
    zeichne('/de/cockpit');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});

describe('Cockpit-Zeile', () => {
  it('meldet eine leere Zeile', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/cockpit/prozesse_ohne_owner', koerper: zeile() },
    ]);
    zeichne('/de/cockpit/prozesse_ohne_owner');
    expect(
      await screen.findByText('In Ihrem Bereich ist zu dieser Zeile nichts offen.'),
    ).toBeInTheDocument();
  });

  it('fuehrt jeden Eintrag in sein vorgefiltertes Zielmodul', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/api/v1/cockpit/datenobjekte_ohne_kategorie',
        koerper: zeile({
          schluessel: 'datenobjekte_ohne_kategorie',
          titel: 'Datenobjekte ohne Kategorie',
          anzahl: 1,
          eintraege: [
            eintrag({
              id: 'do-1',
              titel: 'Kreditorenstamm',
              hinweis: 'Kategorie fehlt',
              ziel_modul: 'datenobjekte',
              ziel_filter: { ohne_kategorie: 'true' },
            }),
          ],
        }),
      },
      { pfad: '/api/v1/datenobjekte', koerper: [] },
    ]);
    zeichne('/de/cockpit/datenobjekte_ohne_kategorie');
    const zieleLink = await screen.findByRole('link', { name: 'datenobjekte' });
    expect(zieleLink).toHaveAttribute('href', '/de/datenobjekte?ohne_kategorie=true');

    await userEvent.click(zieleLink);
    expect(
      await screen.findByRole('heading', { name: 'Datenobjekte' }),
    ).toBeInTheDocument();
  });

  it('springt aus dem Cockpit in ein Prozessobjekt', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/cockpit/prozesse_ohne_owner', koerper: zeile({ eintraege: [eintrag()] }) },
      { pfad: '/api/v1/prozesse/p-1', koerper: prozess() },
    ]);
    zeichne('/de/cockpit/prozesse_ohne_owner');
    await userEvent.click(await screen.findByRole('link', { name: 'prozesse' }));
    expect(
      await screen.findByRole('heading', { name: 'Rechnungspruefung', level: 1 }),
    ).toBeInTheDocument();
  });

  it('zeigt ein Aggregat, wo die Zeile eines liefert', async () => {
    fetchAttrappe([
      ...grundrouten(),
      {
        pfad: '/api/v1/cockpit/tier_verteilung',
        koerper: zeile({
          schluessel: 'tier_verteilung',
          titel: 'Tier-Verteilung',
          aggregat: {
            je_technologie: { 'apps-script': { '3': 2 } },
            je_monat: { '2026-09': { '3': 2 } },
          },
        }),
      },
    ]);
    zeichne('/de/cockpit/tier_verteilung');
    const aggregat = await screen.findByTestId('aggregat');
    expect(within(aggregat).getByText('je_technologie')).toBeInTheDocument();
    expect(within(aggregat).getByText('apps-script: Tier 3 × 2')).toBeInTheDocument();
    expect(within(aggregat).getByText('2026-09: Tier 3 × 2')).toBeInTheDocument();
  });

  it('kehrt zur Uebersicht zurueck', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/cockpit/prozesse_ohne_owner', koerper: zeile() },
      { pfad: '/api/v1/cockpit', koerper: [kopf()] },
    ]);
    zeichne('/de/cockpit/prozesse_ohne_owner');
    await userEvent.click(await screen.findByRole('link', { name: 'Zurück zur Übersicht' }));
    expect(await screen.findByRole('heading', { name: 'Cockpit' })).toBeInTheDocument();
  });

  it('meldet einen Ladefehler', async () => {
    fetchAttrappe([
      ...grundrouten(),
      { pfad: '/api/v1/cockpit/prozesse_ohne_owner', status: 404, koerper: {} },
    ]);
    zeichne('/de/cockpit/prozesse_ohne_owner');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
