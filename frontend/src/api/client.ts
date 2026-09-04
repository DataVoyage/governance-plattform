/**
 * Zugriff auf die Backend-API.
 *
 * Das Frontend kennt ausschliesslich diesen Vertrag — kein Datenbankschema,
 * keine internen Geschaeftsregeln (Architektur 6.4).
 */

import type {
  Anforderungsklasse,
  Attestierung,
  Bewertung,
  BewertungAbschluss,
  DatenObjekt,
  DatenobjektKatalog,
  Datennutzung,
  Datenkategorie,
  Aufloesungsart,
  AussageEingabe,
  Compliance,
  CockpitZeile,
  CockpitZeilenkopf,
  Deckung,
  Fachbereich,
  GateStatus,
  GateTyp,
  GateVorgang,
  Katalog,
  Nutzer,
  Organisationseinheit,
  Person,
  Profil,
  Prozess,
  ProzessEingabe,
  Einstellung,
  Klassenbewertung,
  Lenkungsvorgang,
  Matrixfeld,
  Nachweiseintrag,
  Meldung,
  Rahmen,
  Rolle,
  RolleErklaert,
  Rollenzuweisung,
  ScopeTyp,
  Schicht2VerbotEintrag,
  Rollenwirkung,
  Technologie,
  Toolbefund,
  Selbstverpflichtung,
  ToolEingabe,
  ToolObjekt,
  Umsetzung,
  Wirkung,
  WizardSchritt,
  Zugriffsart,
} from './typen';

export const API_BASIS: string = (import.meta.env?.VITE_API_BASIS as string | undefined) ?? '';

export class ApiFehler extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiFehler';
  }
}

async function fehlertext(antwort: Response): Promise<string> {
  try {
    const koerper = await antwort.json();
    const detail = (koerper as { detail?: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const erster = detail[0] as { msg?: string };
      if (erster?.msg) return erster.msg;
    }
  } catch {
    /* Antwort ohne JSON-Körper — der Status trägt die Aussage. */
  }
  return `HTTP ${antwort.status}`;
}

export async function anfrage<T>(
  pfad: string,
  optionen: { methode?: string; koerper?: unknown; token?: string | null } = {},
): Promise<T> {
  const { methode = 'GET', koerper, token } = optionen;
  const kopf: Record<string, string> = {};
  if (koerper !== undefined) kopf['Content-Type'] = 'application/json';
  if (token) kopf.Authorization = `Bearer ${token}`;

  const antwort = await fetch(`${API_BASIS}${pfad}`, {
    method: methode,
    headers: kopf,
    body: koerper === undefined ? undefined : JSON.stringify(koerper),
  });

  if (!antwort.ok) throw new ApiFehler(antwort.status, await fehlertext(antwort));
  if (antwort.status === 204) return undefined as T;
  return (await antwort.json()) as T;
}

export const api = {
  devToken: (subject: string, email: string, name: string) =>
    anfrage<{ access_token: string }>('/api/v1/auth/dev-token', {
      methode: 'POST',
      koerper: { subject, email, name },
    }),
  profil: (token: string) => anfrage<Profil>('/api/v1/auth/me', { token }),
  /** Ohne `fuerRolle` die ganze Gliederung (Kontext), mit ihr die eigene Auswahl. */
  fachbereiche: (token: string, fuerRolle?: Rolle) =>
    anfrage<Fachbereich[]>(
      `/api/v1/fachbereiche${fuerRolle === undefined ? '' : `?fuer_rolle=${fuerRolle}`}`,
      { token },
    ),
  organisationseinheiten: (token: string, fuerRolle?: Rolle) =>
    anfrage<Organisationseinheit[]>(
      `/api/v1/organisationseinheiten${fuerRolle === undefined ? '' : `?fuer_rolle=${fuerRolle}`}`,
      { token },
    ),
  /**
   * Wer diese Rolle in diesem Bereich trägt — für Owner- und Vertretungsfelder.
   * Nicht `nutzer`: das ist die Nutzerverwaltung und bleibt global.
   */
  personen: (
    token: string,
    rolle: Rolle,
    bereich: { fachbereichId?: string; organisationseinheitId?: string },
  ) => {
    const abfrage = new URLSearchParams({ rolle });
    if (bereich.fachbereichId !== undefined) abfrage.set('fachbereich_id', bereich.fachbereichId);
    if (bereich.organisationseinheitId !== undefined) {
      abfrage.set('organisationseinheit_id', bereich.organisationseinheitId);
    }
    return anfrage<Person[]>(`/api/v1/personen?${abfrage}`, { token });
  },
  nutzer: (token: string) => anfrage<Nutzer[]>('/api/v1/admin/users', { token }),
  prozesse: (token: string) => anfrage<Prozess[]>('/api/v1/prozesse', { token }),
  prozess: (token: string, id: string) => anfrage<Prozess>(`/api/v1/prozesse/${id}`, { token }),
  prozessAnlegen: (token: string, daten: ProzessEingabe) =>
    anfrage<Prozess>('/api/v1/prozesse', { methode: 'POST', koerper: daten, token }),
  prozessAendern: (
    token: string,
    id: string,
    daten: Partial<ProzessEingabe> & {
      status?: Prozess['status'];
      erlaubte_externe_ziele?: string[];
    },
  ) => anfrage<Prozess>(`/api/v1/prozesse/${id}`, { methode: 'PATCH', koerper: daten, token }),
  wizardSchritt: (
    token: string,
    prozessId: string,
    antworten: Record<string, boolean>,
    begruendungen: Record<string, string> = {},
  ) =>
    anfrage<WizardSchritt>(`/api/v1/prozesse/${prozessId}/bewertung/wizard`, {
      methode: 'POST',
      koerper: { antworten, begruendungen },
      token,
    }),
  bewertungAbschliessen: (
    token: string,
    prozessId: string,
    antworten: Record<string, boolean>,
    begruendungen: Record<string, string> = {},
  ) =>
    anfrage<BewertungAbschluss>(`/api/v1/prozesse/${prozessId}/bewertungen`, {
      methode: 'POST',
      koerper: { antworten, begruendungen },
      token,
    }),
  bewertungen: (token: string, prozessId: string) =>
    anfrage<Bewertung[]>(`/api/v1/prozesse/${prozessId}/bewertungen`, { token }),
  tools: (token: string, abfrage = '') =>
    anfrage<ToolObjekt[]>(`/api/v1/tools${abfrage}`, { token }),
  tool: (token: string, id: string) => anfrage<ToolObjekt>(`/api/v1/tools/${id}`, { token }),
  toolAnlegen: (token: string, daten: ToolEingabe) =>
    anfrage<ToolObjekt>('/api/v1/tools', { methode: 'POST', koerper: daten, token }),
  toolAendern: (token: string, id: string, daten: Partial<ToolEingabe>) =>
    anfrage<ToolObjekt>(`/api/v1/tools/${id}`, { methode: 'PATCH', koerper: daten, token }),
  toolAttestieren: (token: string, id: string, daten: Attestierung) =>
    anfrage<ToolObjekt>(`/api/v1/tools/${id}/attestierungen`, {
      methode: 'PUT',
      koerper: daten,
      token,
    }),
  toolBestaetigen: (token: string, id: string) =>
    anfrage<ToolObjekt>(`/api/v1/tools/${id}/bestaetigung`, { methode: 'POST', token }),
  toolMitProzessVerknuepfen: (token: string, id: string, prozessId: string) =>
    anfrage<ToolObjekt>(`/api/v1/tools/${id}/prozesse`, {
      methode: 'POST',
      koerper: { prozessobjekt_id: prozessId },
      token,
    }),
  toolVonProzessLoesen: (token: string, id: string, prozessId: string) =>
    anfrage<ToolObjekt>(`/api/v1/tools/${id}/prozesse/${prozessId}`, {
      methode: 'DELETE',
      token,
    }),
  anforderungsklassen: (token: string) =>
    anfrage<Anforderungsklasse[]>('/api/v1/anforderungsklassen', { token }),
  technologien: (token: string) => anfrage<Technologie[]>('/api/v1/technologien', { token }),
  technologiematrix: (token: string) =>
    anfrage<Matrixfeld[]>('/api/v1/technologiematrix', { token }),
  matrixfeldSetzen: (
    token: string,
    technologie: string,
    klasse: string,
    daten: { bewertung: Klassenbewertung; begruendung: string },
  ) =>
    anfrage<Matrixfeld>(`/api/v1/technologiematrix/${technologie}/${klasse}`, {
      methode: 'PUT',
      koerper: daten,
      token,
    }),
  toolKlassenbefund: (token: string, id: string) =>
    anfrage<Toolbefund>(`/api/v1/tools/${id}/klassenbefund`, { token }),
  prozessKlassenbefund: (token: string, id: string) =>
    anfrage<Toolbefund[]>(`/api/v1/prozesse/${id}/klassenbefund`, { token }),
  kompensationSetzen: (token: string, toolId: string, klasse: string, massnahme: string) =>
    anfrage<{ id: string }>(`/api/v1/tools/${toolId}/kompensationen/${klasse}`, {
      methode: 'PUT',
      koerper: { massnahme },
      token,
    }),
  toolErlaubnisrahmen: (token: string, id: string) =>
    anfrage<Rahmen>(`/api/v1/tools/${id}/erlaubnisrahmen`, { token }),
  toolDatennutzung: (token: string, id: string) =>
    anfrage<Datennutzung[]>(`/api/v1/tools/${id}/datenobjekte`, { token }),
  toolMitDatenobjektVerknuepfen: (
    token: string,
    id: string,
    datenobjektId: string,
    zugriffsart: Zugriffsart,
  ) =>
    anfrage<void>(`/api/v1/tools/${id}/datenobjekte`, {
      methode: 'POST',
      koerper: { datenobjekt_id: datenobjektId, zugriffsart },
      token,
    }),
  toolZugriffsartAendern: (
    token: string,
    id: string,
    datenobjektId: string,
    zugriffsart: Zugriffsart,
  ) =>
    anfrage<void>(`/api/v1/tools/${id}/datenobjekte/${datenobjektId}`, {
      methode: 'PATCH',
      koerper: { zugriffsart },
      token,
    }),
  toolVonDatenobjektLoesen: (token: string, id: string, datenobjektId: string) =>
    anfrage<void>(`/api/v1/tools/${id}/datenobjekte/${datenobjektId}`, {
      methode: 'DELETE',
      token,
    }),
  datenobjekte: (token: string, abfrage = '') =>
    anfrage<DatenObjekt[]>(`/api/v1/datenobjekte${abfrage}`, { token }),
  datenobjektKatalog: (token: string) =>
    anfrage<DatenobjektKatalog[]>('/api/v1/datenobjekte/katalog', { token }),
  datenobjektAnlegen: (
    token: string,
    daten: {
      name: string;
      beschreibung?: string;
      kategorie?: Datenkategorie | null;
      fachbereich_id?: string | null;
      prozessobjekt_id?: string | null;
      quellsystem?: string | null;
    },
  ) => anfrage<DatenObjekt>('/api/v1/datenobjekte', { methode: 'POST', koerper: daten, token }),
  datenobjekt: (token: string, id: string) =>
    anfrage<DatenObjekt>(`/api/v1/datenobjekte/${id}`, { token }),
  datenobjektAendern: (
    token: string,
    id: string,
    daten: Partial<{
      name: string;
      beschreibung: string;
      kategorie: Datenkategorie | null;
      fachbereich_id: string | null;
      quellsystem: string | null;
    }>,
  ) =>
    anfrage<DatenObjekt>(`/api/v1/datenobjekte/${id}`, { methode: 'PATCH', koerper: daten, token }),
  datenobjektWirkung: (token: string, id: string, kategorie?: Datenkategorie | null) =>
    anfrage<Wirkung>(
      `/api/v1/datenobjekte/${id}/wirkung${kategorie ? `?kategorie=${kategorie}` : ''}`,
      { token },
    ),
  datenobjektKategorisieren: (token: string, id: string, kategorie: Datenkategorie | null) =>
    anfrage<DatenObjekt>(`/api/v1/datenobjekte/${id}`, {
      methode: 'PATCH',
      koerper: { kategorie },
      token,
    }),
  katalog: (token: string) =>
    anfrage<Katalog[]>('/api/v1/selbstverpflichtungen/katalog', { token }),
  selbstverpflichtungen: (token: string, prozessId: string) =>
    anfrage<Selbstverpflichtung[]>(`/api/v1/prozesse/${prozessId}/selbstverpflichtungen`, {
      token,
    }),
  selbstverpflichtungAbgeben: (
    token: string,
    prozessId: string,
    aussagen: Record<string, AussageEingabe>,
  ) =>
    anfrage<Selbstverpflichtung>('/api/v1/selbstverpflichtungen', {
      methode: 'POST',
      koerper: { typ: 'prozesseigner', prozessobjekt_id: prozessId, aussagen },
      token,
    }),
  toolVerpflichtungAbgeben: (
    token: string,
    toolId: string,
    aussagen: Record<string, AussageEingabe>,
  ) =>
    anfrage<Selbstverpflichtung>('/api/v1/selbstverpflichtungen', {
      methode: 'POST',
      koerper: { typ: 'technischer_owner', tool_objekt_id: toolId, aussagen },
      token,
    }),
  prozessDeckung: (token: string, prozessId: string) =>
    anfrage<Deckung>(`/api/v1/prozesse/${prozessId}/selbstverpflichtung`, { token }),
  toolDeckung: (token: string, toolId: string) =>
    anfrage<Deckung>(`/api/v1/tools/${toolId}/selbstverpflichtung/deckung`, { token }),
  verpflichtungBestaetigen: (token: string, eintragId: string) =>
    anfrage<Selbstverpflichtung>(`/api/v1/selbstverpflichtungen/${eintragId}/bestaetigung`, {
      methode: 'POST',
      token,
    }),
  gates: (token: string, prozessId: string) =>
    anfrage<GateVorgang[]>(`/api/v1/prozesse/${prozessId}/gates`, { token }),
  offeneGates: (token: string) => anfrage<GateVorgang[]>('/api/v1/gates', { token }),
  gateAusloeser: (token: string) => anfrage<string[]>('/api/v1/gates/ausloeser', { token }),
  gateEinreichen: (
    token: string,
    prozessId: string,
    daten: { gate_typ: GateTyp; ausloeser?: string | null; begruendung?: string },
  ) =>
    anfrage<GateVorgang>(`/api/v1/prozesse/${prozessId}/gates`, {
      methode: 'POST',
      koerper: daten,
      token,
    }),
  gateEntscheiden: (token: string, gateId: string, status: GateStatus, kommentar = '') =>
    anfrage<GateVorgang>(`/api/v1/gates/${gateId}/entscheidung`, {
      methode: 'POST',
      koerper: { status, kommentar },
      token,
    }),
  compliance: (token: string, toolId: string) =>
    anfrage<Compliance>(`/api/v1/tools/${toolId}/compliance`, { token }),
  /** Der eine Knopf. Ein Feld — die Beobachtung; alles Übrige misst der Server. */
  abweichungMelden: (token: string, toolId: string, begruendung: string) =>
    anfrage<Meldung>(`/api/v1/tools/${toolId}/compliance`, {
      methode: 'POST',
      koerper: { begruendung },
      token,
    }),
  schicht2Verbote: (token: string) =>
    anfrage<Schicht2VerbotEintrag[]>('/api/v1/schicht2-verbote', { token }),
  lenkungsvorgaenge: (token: string, abfrage = '') =>
    anfrage<Lenkungsvorgang[]>(`/api/v1/lenkungsvorgaenge${abfrage}`, { token }),
  lenkungAufloesen: (
    token: string,
    vorgangId: string,
    daten: { art: Aufloesungsart; bewertung_id?: string | null; kommentar?: string },
  ) =>
    anfrage<Lenkungsvorgang>(`/api/v1/lenkungsvorgaenge/${vorgangId}/aufloesung`, {
      methode: 'POST',
      koerper: daten,
      token,
    }),
  rollen: (token: string) => anfrage<RolleErklaert[]>('/api/v1/admin/rollen', { token }),
  rollenzuweisungen: (token: string, userId?: string) =>
    anfrage<Rollenzuweisung[]>(
      `/api/v1/admin/rollenzuweisungen${userId ? `?user_id=${userId}` : ''}`,
      { token },
    ),
  rolleZuweisen: (
    token: string,
    daten: { user_id: string; rolle: Rolle; scope_typ: ScopeTyp; scope_id: string | null },
  ) =>
    anfrage<Rollenzuweisung>('/api/v1/admin/rollenzuweisungen', {
      methode: 'POST',
      koerper: daten,
      token,
    }),
  rolleEntziehen: (token: string, zuweisungId: string) =>
    anfrage<void>(`/api/v1/admin/rollenzuweisungen/${zuweisungId}`, {
      methode: 'DELETE',
      token,
    }),
  rollenwirkung: (
    token: string,
    daten: { user_id: string; rolle: Rolle; scope_typ: ScopeTyp; scope_id: string | null },
  ) => {
    const abfrage = new URLSearchParams({
      user_id: daten.user_id,
      rolle: daten.rolle,
      scope_typ: daten.scope_typ,
      ...(daten.scope_id === null ? {} : { scope_id: daten.scope_id }),
    });
    return anfrage<Rollenwirkung>(`/api/v1/admin/rollenzuweisungen/wirkung?${abfrage}`, {
      token,
    });
  },
  nutzerAendern: (
    token: string,
    id: string,
    daten: { ist_aktiv?: boolean; fuehrungskraft_user_id?: string | null },
  ) => anfrage<Nutzer>(`/api/v1/admin/users/${id}`, { methode: 'PATCH', koerper: daten, token }),
  nachweis: (token: string, abfrage = '') =>
    anfrage<Nachweiseintrag[]>(`/api/v1/nachweis${abfrage}`, { token }),
  konfiguration: (token: string) => anfrage<Einstellung[]>('/api/v1/konfiguration', { token }),
  konfigurationSetzen: (token: string, schluessel: string, wert: string) =>
    anfrage<Einstellung>(`/api/v1/konfiguration/${schluessel}`, {
      methode: 'PUT',
      koerper: { wert },
      token,
    }),
  cockpit: (token: string, abfrage = '') =>
    anfrage<CockpitZeilenkopf[]>(`/api/v1/cockpit${abfrage}`, { token }),
  cockpitZeile: (token: string, schluessel: string, abfrage = '') =>
    anfrage<CockpitZeile>(`/api/v1/cockpit/${schluessel}${abfrage}`, { token }),
  umsetzungAnlegen: (token: string, prozessId: string, landOrgId: string) =>
    anfrage<Umsetzung>(`/api/v1/prozesse/${prozessId}/umsetzungen`, {
      methode: 'POST',
      koerper: { land_org_id: landOrgId },
      token,
    }),
  umsetzungAendern: (
    token: string,
    prozessId: string,
    umsetzungId: string,
    lokaleAbweichung: string | null,
  ) =>
    anfrage<Umsetzung>(`/api/v1/prozesse/${prozessId}/umsetzungen/${umsetzungId}`, {
      methode: 'PATCH',
      koerper: { lokale_abweichung: lokaleAbweichung },
      token,
    }),
  umsetzungEntfernen: (token: string, prozessId: string, umsetzungId: string) =>
    anfrage<void>(`/api/v1/prozesse/${prozessId}/umsetzungen/${umsetzungId}`, {
      methode: 'DELETE',
      token,
    }),
};
