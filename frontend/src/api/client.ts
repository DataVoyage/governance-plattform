/**
 * Zugriff auf die Backend-API.
 *
 * Das Frontend kennt ausschliesslich diesen Vertrag — kein Datenbankschema,
 * keine internen Geschaeftsregeln (Architektur 6.4).
 */

import type {
  Fachbereich,
  Nutzer,
  Organisationseinheit,
  Profil,
  Prozess,
  ProzessEingabe,
  Umsetzung,
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
  umsetzungAnlegen: (token: string, prozessId: string, landOrgId: string) =>
    anfrage<Umsetzung>(`/api/v1/prozesse/${prozessId}/umsetzungen`, {
      methode: 'POST',
      koerper: { land_org_id: landOrgId },
      token,
    }),
};
