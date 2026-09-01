/**
 * Zugriff auf die Backend-API.
 *
 * Das Frontend kennt ausschliesslich diesen Vertrag — kein Datenbankschema,
 * keine internen Geschaeftsregeln (Architektur 6.4).
 */

import type {
  Bewertung,
  BewertungAbschluss,
  BewertungsModus,
  DatenObjekt,
  Datenkategorie,
  Aufloesungsart,
  AussageEingabe,
  ComplianceFarbe,
  ComplianceZustand,
  Fachbereich,
  GateStatus,
  GateTyp,
  GateVorgang,
  Katalog,
  Nutzer,
  Organisationseinheit,
  Profil,
  Prozess,
  ProzessEingabe,
  Lenkungsvorgang,
  Meldung,
  Selbstverpflichtung,
  ToolObjekt,
  Umsetzung,
  WizardSchritt,
} from './typen';

export const API_BASIS: string =
  (import.meta.env?.VITE_API_BASIS as string | undefined) ?? '';

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
  fachbereiche: (token: string) => anfrage<Fachbereich[]>('/api/v1/fachbereiche', { token }),
  organisationseinheiten: (token: string) =>
    anfrage<Organisationseinheit[]>('/api/v1/organisationseinheiten', { token }),
  nutzer: (token: string) => anfrage<Nutzer[]>('/api/v1/admin/users', { token }),
  prozesse: (token: string) => anfrage<Prozess[]>('/api/v1/prozesse', { token }),
  prozess: (token: string, id: string) => anfrage<Prozess>(`/api/v1/prozesse/${id}`, { token }),
  prozessAnlegen: (token: string, daten: ProzessEingabe) =>
    anfrage<Prozess>('/api/v1/prozesse', { methode: 'POST', koerper: daten, token }),
  prozessAendern: (token: string, id: string, daten: Partial<ProzessEingabe>) =>
    anfrage<Prozess>(`/api/v1/prozesse/${id}`, { methode: 'PATCH', koerper: daten, token }),
  wizardSchritt: (
    token: string,
    prozessId: string,
    modus: BewertungsModus,
    antworten: Record<string, boolean>,
  ) =>
    anfrage<WizardSchritt>(`/api/v1/prozesse/${prozessId}/bewertung/wizard`, {
      methode: 'POST',
      koerper: { modus, antworten },
      token,
    }),
  bewertungAbschliessen: (
    token: string,
    prozessId: string,
    modus: BewertungsModus,
    antworten: Record<string, boolean>,
  ) =>
    anfrage<BewertungAbschluss>(`/api/v1/prozesse/${prozessId}/bewertungen`, {
      methode: 'POST',
      koerper: { modus, antworten },
      token,
    }),
  bewertungen: (token: string, prozessId: string) =>
    anfrage<Bewertung[]>(`/api/v1/prozesse/${prozessId}/bewertungen`, { token }),
  tools: (token: string, abfrage = '') =>
    anfrage<ToolObjekt[]>(`/api/v1/tools${abfrage}`, { token }),
  tool: (token: string, id: string) => anfrage<ToolObjekt>(`/api/v1/tools/${id}`, { token }),
  toolAnlegen: (token: string, daten: { name: string; beschreibung?: string }) =>
    anfrage<ToolObjekt>('/api/v1/tools', { methode: 'POST', koerper: daten, token }),
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
  datenobjekte: (token: string, abfrage = '') =>
    anfrage<DatenObjekt[]>(`/api/v1/datenobjekte${abfrage}`, { token }),
  datenobjektAnlegen: (token: string, daten: { name: string; beschreibung?: string }) =>
    anfrage<DatenObjekt>('/api/v1/datenobjekte', { methode: 'POST', koerper: daten, token }),
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
    anfrage<ComplianceZustand[]>(`/api/v1/tools/${toolId}/compliance`, { token }),
  complianceMelden: (
    token: string,
    toolId: string,
    daten: { farbe: ComplianceFarbe; begruendung?: string; abweichung_art?: string | null },
  ) =>
    anfrage<Meldung>(`/api/v1/tools/${toolId}/compliance`, {
      methode: 'POST',
      koerper: daten,
      token,
    }),
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
  umsetzungAnlegen: (token: string, prozessId: string, landOrgId: string) =>
    anfrage<Umsetzung>(`/api/v1/prozesse/${prozessId}/umsetzungen`, {
      methode: 'POST',
      koerper: { land_org_id: landOrgId },
      token,
    }),
};
