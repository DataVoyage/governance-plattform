/**
 * Design-System „Klar" — Grundbausteine.
 *
 * Alle Bausteine beziehen Farbe, Mass und Bewegung ausschliesslich aus den
 * Token (`src/stil/token.css`); kein Baustein setzt einen Rohwert.
 */

import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Link } from 'react-router-dom';

export type KnopfArt = 'gefuellt' | 'getoent' | 'unauffaellig' | 'zerstoerend' | 'schlicht';

interface KnopfEigenschaften extends ButtonHTMLAttributes<HTMLButtonElement> {
  art?: KnopfArt;
  gross?: boolean;
  breit?: boolean;
}

export function Knopf({
  art = 'schlicht',
  gross = false,
  breit = false,
  className = '',
  type = 'button',
  children,
  ...rest
}: KnopfEigenschaften) {
  const klassen = [
    'k-knopf',
    art === 'schlicht' ? '' : `k-knopf--${art}`,
    gross ? 'k-knopf--gross' : '',
    breit ? 'k-knopf--breit' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');
  // eslint-disable-next-line react/button-has-type -- type kommt typisiert aus den Props.
  return (
    <button type={type} className={klassen} {...rest}>
      {children}
    </button>
  );
}

export type Ton = 'neutral' | 'gruen' | 'gelb' | 'rot' | 'blau' | 'lila';

/**
 * Statuspille. Farbe ist nie der alleinige Bedeutungstraeger — jedes Abzeichen
 * traegt seinen Text, optional mit vorangestelltem Zeichen.
 */
export function Abzeichen({
  ton = 'neutral',
  zeichen,
  children,
}: {
  ton?: Ton;
  zeichen?: string;
  children: ReactNode;
}) {
  return (
    <span className={`k-abzeichen${ton === 'neutral' ? '' : ` k-abzeichen--${ton}`}`}>
      {zeichen !== undefined && (
        <span className="punkt" aria-hidden="true">
          {zeichen}
        </span>
      )}
      {children}
    </span>
  );
}

export function Karte({
  titel,
  beischrift,
  aktion,
  children,
}: {
  titel?: string;
  beischrift?: ReactNode;
  aktion?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="k-karte">
      {(titel !== undefined || aktion !== undefined) && (
        <header>
          <div>
            {titel !== undefined && <h2>{titel}</h2>}
            {beischrift !== undefined && <p className="beischrift">{beischrift}</p>}
          </div>
          {aktion}
        </header>
      )}
      {children}
    </section>
  );
}

export function Seitenkopf({
  titel,
  untertitel,
  rueckweg,
  aktionen,
}: {
  titel: string;
  untertitel?: ReactNode;
  rueckweg?: { ziel: string; text: string };
  aktionen?: ReactNode;
}) {
  return (
    <header className="k-seitenkopf">
      <div className="titelblock">
        {rueckweg !== undefined && (
          <Link className="rueckweg" to={rueckweg.ziel}>
            <span aria-hidden="true">‹</span>
            {rueckweg.text}
          </Link>
        )}
        <h1>{titel}</h1>
        {untertitel !== undefined && <p className="untertitel">{untertitel}</p>}
      </div>
      {aktionen !== undefined && <div className="aktionen">{aktionen}</div>}
    </header>
  );
}

export function Leerzustand({
  zeichen = '◍',
  titel,
  text,
  aktion,
}: {
  zeichen?: string;
  titel: string;
  text?: string;
  aktion?: ReactNode;
}) {
  return (
    <div className="k-leer">
      <span className="symbol" aria-hidden="true">
        {zeichen}
      </span>
      <h2>{titel}</h2>
      {text !== undefined && <p>{text}</p>}
      {aktion}
    </div>
  );
}

export type HinweisArt = 'information' | 'warnung' | 'fehler' | 'erfolg';

const HINWEIS_ZEICHEN: Record<HinweisArt, string> = {
  information: 'ℹ',
  warnung: '⚠',
  fehler: '⨯',
  erfolg: '✓',
};

export function Hinweis({ art = 'information', children }: { art?: HinweisArt; children: ReactNode }) {
  return (
    <p
      className={`k-hinweis${art === 'information' ? '' : ` k-hinweis--${art}`}`}
      role={art === 'fehler' ? 'alert' : 'status'}
    >
      <span className="symbol" aria-hidden="true">
        {HINWEIS_ZEICHEN[art]}
      </span>
      <span>{children}</span>
    </p>
  );
}

export function Ladeschimmer({ zeilen = 3, beschriftung }: { zeilen?: number; beschriftung: string }) {
  return (
    <div role="status" aria-live="polite" aria-busy="true">
      <span className="k-nur-vorlesen">{beschriftung}</span>
      {Array.from({ length: zeilen }, (_, nummer) => (
        <div
          key={nummer}
          className="k-schimmer"
          style={{ width: `${100 - nummer * 12}%` }}
          aria-hidden="true"
        />
      ))}
    </div>
  );
}

export interface Wertpaar {
  beschriftung: string;
  wert: ReactNode;
  /** Woher ein abgeleiteter Wert stammt — sichtbar, nicht erraten. */
  herkunft?: string;
  pruefkennung?: string;
}

export function Werteliste({ eintraege }: { eintraege: Wertpaar[] }) {
  return (
    <dl className="k-werte">
      {eintraege.map((eintrag) => (
        <div key={eintrag.beschriftung} style={{ display: 'contents' }}>
          <dt>{eintrag.beschriftung}</dt>
          <dd data-testid={eintrag.pruefkennung}>
            {eintrag.wert}
            {eintrag.herkunft !== undefined && <span className="herkunft">{eintrag.herkunft}</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}
