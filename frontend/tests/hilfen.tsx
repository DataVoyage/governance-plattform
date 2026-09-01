import { render, type RenderResult } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';

import { App } from '@/App';
import type { Prozess } from '@/api/typen';
import { SitzungsAnbieter } from '@/zustand/Sitzung';

export const PROFIL = {
  id: 'user-1',
  email: 'owner@beispiel-ag.de',
  name: 'Olivia Owner',
  rollen: [
    {
      id: 'rz-1',
      user_id: 'user-1',
      rolle: 'prozess_owner',
      scope_typ: 'organisationseinheit' as const,
      scope_id: 'org-int',
    },
  ],
};

export const EINHEITEN = [
  { id: 'org-int', fachbereich_id: 'fb-1', ebene: 'INT' as const, land_code: null },
  { id: 'org-de', fachbereich_id: 'fb-1', ebene: 'LAND' as const, land_code: 'DE' },
  { id: 'org-fr', fachbereich_id: 'fb-1', ebene: 'LAND' as const, land_code: 'FR' },
];

export function prozess(ueberschreibungen: Partial<Prozess> = {}): Prozess {
  return {
    id: 'p-1',
    name: 'Rechnungspruefung',
    owner_user_id: 'user-1',
    stellvertretung_user_id: 'user-2',
    prozessgeber_org_id: 'org-int',
    supplier: 'Kreditorenbuchhaltung',
    process_steps: 'Pruefen, freigeben, buchen',
    output: 'Freigegebene Rechnung',
    customer: 'bereich',
    ausfallfolge: 'spuerbar',
    status: 'entwurf',
    reichweite: 'bereich',
    kritikalitaet: 2,
    mitbestimmung_flag: false,
    input_datenobjekt_ids: [],
    output_datenobjekt_ids: [],
    vorgelagert_ids: [],
    nachgelagert_ids: [],
    umsetzungen: [],
    tool_objekt_ids: [],
    ...ueberschreibungen,
  };
}

export interface Route {
  pfad: string | RegExp;
  methode?: string;
  status?: number;
  koerper: unknown;
}

/** Ersetzt fetch durch eine Tabelle aus Pfadmustern und Antworten. */
export function fetchAttrappe(routen: Route[]) {
  const aufrufe: { url: string; methode: string; koerper: unknown }[] = [];
  const attrappe = vi.fn(async (eingabe: RequestInfo | URL, init?: RequestInit) => {
    const url = String(eingabe);
    const methode = init?.method ?? 'GET';
    aufrufe.push({
      url,
      methode,
      koerper: init?.body ? JSON.parse(String(init.body)) : undefined,
    });
    const treffer = routen.find(
      (r) =>
        (r.methode ?? 'GET') === methode &&
        (typeof r.pfad === 'string' ? url.endsWith(r.pfad) : r.pfad.test(url)),
    );
    const status = treffer?.status ?? (treffer ? 200 : 404);
    return {
      ok: status < 400,
      status,
      json: async () => treffer?.koerper ?? { detail: `Keine Attrappe fuer ${methode} ${url}` },
    } as Response;
  });
  vi.stubGlobal('fetch', attrappe);
  return { attrappe, aufrufe };
}

export function zeichne(pfad: string, angemeldet = true): RenderResult {
  if (angemeldet) window.localStorage.setItem('governance.token', 'test-token');
  return render(
    <MemoryRouter
      initialEntries={[pfad]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <SitzungsAnbieter>
        <App />
      </SitzungsAnbieter>
    </MemoryRouter>,
  );
}
