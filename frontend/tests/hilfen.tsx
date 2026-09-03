import { render, type RenderResult } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';

import { App } from '@/App';
import type {
  Anforderungsklasse,
  Geerbt,
  Prozess,
  Rahmen,
  RahmenElement,
  Rollenzuweisung,
  Schicht2VerbotEintrag,
  Technologie,
  Toolbefund,
  ToolObjekt,
} from '@/api/typen';
import { SitzungsAnbieter } from '@/zustand/Sitzung';

export const PROFIL: {
  id: string;
  email: string;
  name: string;
  rollen: Rollenzuweisung[];
} = {
  id: 'user-1',
  email: 'owner@beispiel-ag.de',
  name: 'Olivia Owner',
  rollen: [
    {
      id: 'rz-1',
      user_id: 'user-1',
      rolle: 'prozess_owner',
      scope_typ: 'organisationseinheit',
      scope_id: 'org-int',
    },
  ],
};

export const FACHBEREICHE = [{ id: 'fb-1', name: 'Finance', code: 'fin' }];

/** Wer eine Rolle in einem Bereich trägt — die Antwort von `/personen`. */
export const PERSONEN = [
  { id: 'user-1', name: 'Olivia Owner' },
  { id: 'user-2', name: 'Viktor Vertretung' },
  { id: 'user-9', name: 'Tamara Technik' },
];

export const EINHEITEN = [
  { id: 'org-int', fachbereich_id: 'fb-1', ebene: 'INT' as const, land_code: null },
  { id: 'org-de', fachbereich_id: 'fb-1', ebene: 'LAND' as const, land_code: 'DE' },
  { id: 'org-fr', fachbereich_id: 'fb-1', ebene: 'LAND' as const, land_code: 'FR' },
];

/** Alles erlaubt — die Rechte übersteuert, wer sie prüfen will. */
export const ALLE_PROZESSRECHTE = {
  bearbeiten: true,
  bewerten: true,
  selbstverpflichten: true,
  gate_einreichen: true,
  umsetzung_pflegen: true,
};

export const ALLE_TOOLRECHTE = {
  bearbeiten: true,
  attestieren: true,
  verknuepfen: true,
  zustand_melden: true,
  kompensieren: true,
  selbstverpflichten: true,
  bestaetigen: true,
};

export const ALLE_DATENOBJEKTRECHTE = {
  bearbeiten: true,
  kategorisieren: true,
  anker_aendern: true,
  bestaetigen: true,
};

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
    schritt_anzahl: 3,
    schritte_zu_viele: false,
    input_datenobjekt_ids: [],
    output_datenobjekt_ids: [],
    vorgelagert_ids: [],
    nachgelagert_ids: [],
    erlaubte_externe_ziele: [],
    umsetzungen: [],
    tool_objekt_ids: [],
    tier: null,
    ausgeloeste_k_klassen: [],
    bewertung_gueltig_bis: null,
    rechte: ALLE_PROZESSRECHTE,
    ...ueberschreibungen,
  };
}

export function geerbt(ueberschreibungen: Partial<Geerbt> = {}): Geerbt {
  return {
    kritikalitaet: 0,
    reichweite: null,
    tier: null,
    mitbestimmung_flag: false,
    k_klassen: [],
    quelle_prozess_ids: [],
    beitraege: [],
    ...ueberschreibungen,
  };
}

/**
 * Ein attestiertes Tool-Objekt als Ausgangslage.
 *
 * Die Vorbelegung beschreibt den unauffaelligen Fall aus A.6 — ein Mensch
 * steht zwischen Output und Wirkung. Tests, die den offenen Zustand brauchen,
 * setzen die drei Felder ausdruecklich auf ``null``.
 */
export function tool(ueberschreibungen: Partial<ToolObjekt> = {}): ToolObjekt {
  return {
    id: 'tool-1',
    name: 'Rechnungs-Skript',
    beschreibung: '',
    technologie: 'apps-script',
    kategorie: null,
    technischer_owner_user_id: null,
    stellvertretung_user_id: null,
    organisationseinheit_id: 'org-de',
    lauftyp: null,
    ausfuehrungsidentitaet: null,
    statische_zugangsdaten: null,
    externe_ziele: [],
    herkunft: 'manuell',
    quelle: null,
    externe_id: null,
    status: 'bestaetigt',
    metadaten: {},
    letzte_aktivitaet_am: null,
    prozessobjekt_ids: [],
    geerbt: geerbt(),
    attest_entscheidung_ueber_personen: false,
    attest_mensch_dazwischen: true,
    attest_undeklarierte_quellen: false,
    attestiert_am: '2026-08-01T10:00:00+00:00',
    attestiert_von_user_id: 'user-1',
    attestiert_von_name: 'Olivia Owner',
    attestierung_vollstaendig: true,
    wirkungsart: 'gestaltend',
    wirkungsart_grund: 'nur_lesend',
    schreibgeschuetzte_felder: [],
    rechte: ALLE_TOOLRECHTE,
    ...ueberschreibungen,
  };
}

/** Ein Rahmenelement ohne Abweichung — der unauffällige Fall. */
export function rahmenElement(
  schluessel: string,
  ueberschreibungen: Partial<RahmenElement> = {},
): RahmenElement {
  return {
    schluessel,
    erlaubt: [],
    gemessen: [],
    abweichung: [],
    messbar: schluessel !== 'reichweite',
    eingehalten: true,
    ...ueberschreibungen,
  };
}

/** Ein eingehaltener Erlaubnisrahmen mit allen sieben Elementen (A.13.2). */
export function rahmen(ueberschreibungen: Partial<Rahmen> = {}): Rahmen {
  return {
    elemente: [
      'datenobjekte',
      'datenkategorie',
      'reichweite',
      'externe_ziele',
      'zugriffsart',
      'ausfuehrungsart',
      'ausfuehrungsidentitaet',
    ].map((schluessel) => rahmenElement(schluessel)),
    tier: null,
    quelle_prozess_ids: [],
    eingehalten: true,
    schicht2_befunde: [],
    ...ueberschreibungen,
  };
}

export const SCHICHT2_VERBOTE: Schicht2VerbotEintrag[] = [
  { schluessel: 'identitaet_umgangen', automatisch_erkennbar: true },
  { schluessel: 'statische_zugangsdaten', automatisch_erkennbar: true },
  { schluessel: 'undeklarierte_quellen', automatisch_erkennbar: true },
  { schluessel: 'entscheidung_ohne_mensch', automatisch_erkennbar: true },
  { schluessel: 'daten_ins_offene_netz', automatisch_erkennbar: false },
  { schluessel: 'protokollierung_umgangen', automatisch_erkennbar: false },
];

export const TECHNOLOGIEN: Technologie[] = [
  { schluessel: 'apps-script', name: 'Apps Script' },
  { schluessel: 'python-kubernetes', name: 'Python / Kubernetes' },
  { schluessel: 'bigquery-gcs', name: 'BigQuery / Cloud Storage' },
  { schluessel: 'appsheet', name: 'AppSheet' },
];

export const ANFORDERUNGSKLASSEN: Anforderungsklasse[] = Array.from({ length: 10 }, (_, i) => ({
  schluessel: `K${i + 1}`,
  name: `Anforderungsklasse ${i + 1}`,
  zweck: `Was bei K${i + 1} zu tun ist, in einem Satz für die Ergebnisseite.`,
  ausloeser: `Bedingung für K${i + 1}.`,
}));

/** Ein Tool ohne ausgelöste Klassen — der unauffällige Fall. */
export function klassenbefund(ueberschreibungen: Partial<Toolbefund> = {}): Toolbefund {
  return {
    tool_id: 'tool-1',
    tool_name: 'Rechnungs-Skript',
    technologie: 'apps-script',
    k_klassen: [],
    befunde: [],
    ausschluss: false,
    offen: 0,
    ...ueberschreibungen,
  };
}

export interface Route {
  pfad: string | RegExp;
  methode?: string;
  status?: number;
  /** Fester Koerper, oder eine Funktion fuer wechselnde Antworten je Aufruf. */
  koerper: unknown | ((aufrufNummer: number) => unknown);
}

/**
 * Antworten, die fast jede Seite braucht und die kein Test einzeln setzen soll.
 * Eine ausdrueckliche Route im Test gewinnt, weil sie zuerst geprueft wird.
 */
const STANDARDROUTEN: Route[] = [
  { pfad: '/api/v1/fachbereiche', koerper: FACHBEREICHE },
  { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
  // Auswahllisten der Formulare: nur der eigene Scope, nur passende Personen
  // (docs/rollen-und-scopes.md, 6). Das Testprofil trägt prozess_owner an
  // org-int und sonst nichts — deshalb Einheiten ja, Fachbereiche nein.
  { pfad: /\/organisationseinheiten\?fuer_rolle=/, koerper: EINHEITEN },
  { pfad: /\/fachbereiche\?fuer_rolle=/, koerper: [] },
  { pfad: /\/personen\?/, koerper: PERSONEN },
  { pfad: '/api/v1/datenobjekte/katalog', koerper: [] },
  { pfad: '/api/v1/datenobjekte', koerper: [] },
  { pfad: '/api/v1/admin/users', koerper: [] },
  { pfad: /\/erlaubnisrahmen$/, koerper: rahmen() },
  // Der Prozessbefund ist eine Liste, der Toolbefund ein einzelner —
  // deshalb zwei Muster und nicht eines.
  { pfad: /\/prozesse\/[^/]+\/klassenbefund$/, koerper: [] },
  { pfad: /\/klassenbefund$/, koerper: klassenbefund() },
  { pfad: '/api/v1/anforderungsklassen', koerper: ANFORDERUNGSKLASSEN },
  { pfad: '/api/v1/technologien', koerper: TECHNOLOGIEN },
  { pfad: '/api/v1/schicht2-verbote', koerper: SCHICHT2_VERBOTE },
];

/** Ersetzt fetch durch eine Tabelle aus Pfadmustern und Antworten. */
export function fetchAttrappe(eigene: Route[]) {
  const routen = [...eigene, ...STANDARDROUTEN];
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
    const treffernummer = aufrufe.filter((a) => a.url === url && a.methode === methode).length;
    const koerper =
      typeof treffer?.koerper === 'function'
        ? (treffer.koerper as (n: number) => unknown)(treffernummer)
        : treffer?.koerper;
    return {
      ok: status < 400,
      status,
      json: async () => koerper ?? { detail: `Keine Attrappe fuer ${methode} ${url}` },
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
