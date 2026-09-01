/**
 * Sprachpfad-Routing (Architektur 9.2).
 *
 * Wichtige Abgrenzung: das Landeskuerzel im Pfad steuert ausschliesslich die
 * Anzeigesprache, nie die Sichtbarkeit von Daten. Welche Prozesse ein Nutzer
 * sieht, bestimmt allein die Rolle-x-Bereich-Zuweisung im Backend.
 */

import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { useParams } from 'react-router-dom';

import { STANDARDSPRACHE, istSprache, uebersetze, type Schluessel, type Sprache } from '.';

export interface SprachWert {
  sprache: Sprache;
  t: (schluessel: Schluessel) => string;
  pfad: (rest: string) => string;
}

export const SprachKontext = createContext<SprachWert | null>(null);

export function SprachAnbieter({ children }: { children: ReactNode }) {
  const { sprache: ausPfad } = useParams();
  const sprache: Sprache = istSprache(ausPfad) ? ausPfad : STANDARDSPRACHE;

  const wert = useMemo<SprachWert>(
    () => ({
      sprache,
      t: (schluessel: Schluessel) => uebersetze(sprache, schluessel),
      pfad: (rest: string) => `/${sprache}${rest.startsWith('/') ? rest : `/${rest}`}`,
    }),
    [sprache],
  );

  return <SprachKontext.Provider value={wert}>{children}</SprachKontext.Provider>;
}

export function useSprache(): SprachWert {
  const wert = useContext(SprachKontext);
  if (wert === null) throw new Error('useSprache ausserhalb von SprachAnbieter benutzt');
  return wert;
}
