/**
 * Gemeinsame Hilfen der Oberflaechentests.
 *
 * Wichtigster Punkt: jeder Aufbau-Aufruf wird auf seinen Statuscode geprueft.
 * Ein stillschweigend fehlgeschlagener Aufbau taucht sonst erst viel spaeter
 * als „undefined" in einer Zusicherung auf, und der eigentliche Grund — ein
 * 403, ein 409, ein 422 — geht verloren.
 */

import { expect, type APIRequestContext } from '@playwright/test';

export const API = 'http://127.0.0.1:8100';
export const ADMIN = 'e2e-admin';

type Antwort = Awaited<ReturnType<APIRequestContext['post']>>;

/** Liefert den JSON-Koerper und scheitert laut, wenn der Aufruf nicht glueckte. */
export async function json<T = never>(antwort: Antwort, was = 'Aufbau'): Promise<T> {
  const text = await antwort.text();
  expect(
    antwort.ok(),
    `${was} fehlgeschlagen: ${antwort.status()} ${antwort.url()}\n${text}`,
  ).toBeTruthy();
  return JSON.parse(text) as T;
}

/** Anmeldung als Erstzugangs-Administrator; liefert die Authorization-Kopfzeile. */
export async function kopf(
  anfrage: APIRequestContext,
  subject: string = ADMIN,
  name = 'E2E Administrator',
): Promise<Record<string, string>> {
  const antwort = await anfrage.post(`${API}/api/v1/auth/dev-token`, {
    data: { subject, email: `${subject}@beispiel-ag.de`, name },
  });
  const koerper = await json<{ access_token: string }>(antwort, 'Anmeldung');
  return { Authorization: `Bearer ${koerper.access_token}` };
}

/** Eine je Aufruf eindeutige Kennung fuer Namen und Codes. */
let zaehler = 0;
export function kennung(): string {
  zaehler += 1;
  return `${Date.now().toString(36)}${zaehler.toString(36)}`.slice(-8);
}
