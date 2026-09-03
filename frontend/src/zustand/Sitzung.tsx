/**
 * Sitzung des angemeldeten Nutzers.
 *
 * Das Frontend blendet nicht erlaubte Aktionen aus, verlaesst sich aber nicht
 * darauf: jede Route prueft serverseitig unabhaengig (Architektur 10.2).
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { api } from '@/api/client';
import type { Profil } from '@/api/typen';

const SPEICHER_SCHLUESSEL = 'governance.token';

export interface SitzungsWert {
  token: string | null;
  profil: Profil | null;
  laedt: boolean;
  /**
   * Wahr, seit sich in diesem Browserfenster jemand aktiv abgemeldet hat.
   *
   * Der Unterschied zaehlt an genau einer Stelle: wer ohne Anmeldung eine
   * Adresse aufruft, soll nach dem Anmelden dort ankommen. Wer sich abmeldet,
   * hinterlaesst dem Naechsten kein Ziel — eine Abmeldung ist ein
   * Schlussstrich, und der Naechste gehoert nicht auf die letzte Seite seines
   * Vorgaengers.
   */
  abgemeldet: boolean;
  anmelden: (subject: string, name: string) => Promise<void>;
  abmelden: () => void;
  hatRolle: (rolle: string) => boolean;
}

export const SitzungsKontext = createContext<SitzungsWert | null>(null);

export function leseToken(): string | null {
  try {
    return window.localStorage.getItem(SPEICHER_SCHLUESSEL);
  } catch {
    return null;
  }
}

function schreibeToken(token: string | null): void {
  try {
    if (token === null) window.localStorage.removeItem(SPEICHER_SCHLUESSEL);
    else window.localStorage.setItem(SPEICHER_SCHLUESSEL, token);
  } catch {
    /* Ohne Speicher bleibt die Sitzung auf diesen Tab beschraenkt. */
  }
}

export function SitzungsAnbieter({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => leseToken());
  const [profil, setProfil] = useState<Profil | null>(null);
  const [laedt, setLaedt] = useState<boolean>(token !== null);
  const [abgemeldet, setAbgemeldet] = useState(false);

  useEffect(() => {
    let abgebrochen = false;
    if (token === null) {
      setProfil(null);
      setLaedt(false);
      return;
    }
    setLaedt(true);
    api
      .profil(token)
      .then((geladen) => {
        if (!abgebrochen) setProfil(geladen);
      })
      .catch(() => {
        if (!abgebrochen) {
          schreibeToken(null);
          setToken(null);
          setProfil(null);
        }
      })
      .finally(() => {
        if (!abgebrochen) setLaedt(false);
      });
    return () => {
      abgebrochen = true;
    };
  }, [token]);

  const anmelden = useCallback(async (subject: string, name: string) => {
    const antwort = await api.devToken(subject, `${subject}@beispiel-ag.de`, name);
    schreibeToken(antwort.access_token);
    setToken(antwort.access_token);
    setAbgemeldet(false);
  }, []);

  const abmelden = useCallback(() => {
    schreibeToken(null);
    setToken(null);
    setProfil(null);
    setAbgemeldet(true);
  }, []);

  const hatRolle = useCallback(
    (rolle: string) => (profil?.rollen ?? []).some((z) => z.rolle === rolle),
    [profil],
  );

  const wert = useMemo<SitzungsWert>(
    () => ({ token, profil, laedt, abgemeldet, anmelden, abmelden, hatRolle }),
    [token, profil, laedt, abgemeldet, anmelden, abmelden, hatRolle],
  );

  return <SitzungsKontext.Provider value={wert}>{children}</SitzungsKontext.Provider>;
}

export function useSitzung(): SitzungsWert {
  const wert = useContext(SitzungsKontext);
  if (wert === null) throw new Error('useSitzung ausserhalb von SitzungsAnbieter benutzt');
  return wert;
}
