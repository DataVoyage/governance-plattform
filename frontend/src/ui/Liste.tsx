/**
 * Design-System „Klar" — gruppierte Listen.
 *
 * Das Muster ersetzt die rohen Tabellen der ersten Fassung: Beschriftung
 * links, Wert oder Steuerelement rechts, Haarlinie dazwischen, die Gruppe mit
 * einem Etikett darueber.
 */

import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

export function Gruppe({
  etikett,
  hinweis,
  children,
}: {
  etikett?: string;
  hinweis?: string;
  children: ReactNode;
}) {
  return (
    <section className="k-gruppe">
      {etikett !== undefined && <span className="etikett">{etikett}</span>}
      <div className="k-liste">{children}</div>
      {hinweis !== undefined && <span className="hinweis">{hinweis}</span>}
    </section>
  );
}

interface ZeileInhalt {
  /** Feste Beschriftung links — fuer Wertzeilen in Formularen und Details. */
  beschriftung?: string;
  /** Hauptinhalt, waechst; bei Listen der Name des Objekts. */
  haupt?: ReactNode;
  zweitzeile?: ReactNode;
  wert?: ReactNode;
  pruefkennung?: string;
}

function Inhalt({ beschriftung, haupt, zweitzeile, wert, pfeil }: ZeileInhalt & { pfeil: boolean }) {
  return (
    <>
      {beschriftung !== undefined && <span className="beschriftung">{beschriftung}</span>}
      {(haupt !== undefined || zweitzeile !== undefined) && (
        <span className="haupt">
          {haupt}
          {zweitzeile !== undefined && <span className="zweitzeile">{zweitzeile}</span>}
        </span>
      )}
      {wert !== undefined && <span className="wert">{wert}</span>}
      {pfeil && (
        <span className="pfeil" aria-hidden="true">
          ›
        </span>
      )}
    </>
  );
}

export function Zeile({ pruefkennung, ...inhalt }: ZeileInhalt) {
  return (
    <div className="k-zeile" data-testid={pruefkennung}>
      <Inhalt {...inhalt} pfeil={false} />
    </div>
  );
}

export function ZeileVerweis({
  ziel,
  pruefkennung,
  ...inhalt
}: ZeileInhalt & { ziel: string }) {
  return (
    <Link className="k-zeile" to={ziel} data-testid={pruefkennung}>
      <Inhalt {...inhalt} pfeil />
    </Link>
  );
}

export function ZeileKnopf({
  handeln,
  pruefkennung,
  ...inhalt
}: ZeileInhalt & { handeln: () => void }) {
  return (
    <button type="button" className="k-zeile" onClick={handeln} data-testid={pruefkennung}>
      <Inhalt {...inhalt} pfeil />
    </button>
  );
}
