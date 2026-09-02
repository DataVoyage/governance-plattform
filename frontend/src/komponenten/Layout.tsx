import { useEffect, useState } from 'react';
import { Navigate, NavLink, Link, Outlet, useLocation, useNavigate } from 'react-router-dom';

import { SPRACHEN, type Sprache } from '@/i18n';
import { useSprache } from '@/i18n/SprachKontext';
import { Ladeschimmer } from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

/** Ersetzt das Sprachsegment im Pfad, ohne die Ansicht zu verlassen. */
export function pfadMitSprache(pfad: string, sprache: Sprache): string {
  const segmente = pfad.split('/').filter(Boolean);
  if (segmente.length === 0) return `/${sprache}`;
  segmente[0] = sprache;
  return `/${segmente.join('/')}`;
}

type Farbschema = 'system' | 'hell' | 'dunkel';

const SCHEMA_SCHLUESSEL = 'governance.farbschema';

function leseSchema(): Farbschema {
  try {
    const wert = window.localStorage.getItem(SCHEMA_SCHLUESSEL);
    return wert === 'hell' || wert === 'dunkel' ? wert : 'system';
  } catch {
    return 'system';
  }
}

/**
 * Navigationspunkte der Seitenleiste, in der Reihenfolge des Arbeitsflusses.
 *
 * ``rolle`` blendet einen Punkt aus, wo er ohnehin nichts zeigen würde. Das
 * ist Aufräumen, keine Sicherung — jede Route prüft serverseitig noch einmal
 * (Architektur 10.2).
 */
const PUNKTE: {
  ziel: string;
  schluessel: 'nav.cockpit' | 'nav.prozesse' | 'nav.tools' | 'nav.datenobjekte' | 'nav.gates' | 'nav.lenkung' | 'nav.klassen' | 'nav.konfiguration' | 'nav.verwaltung' | 'nav.nachweis';
  zeichen: string;
  rollen?: string[];
}[] = [
  { ziel: '/cockpit', schluessel: 'nav.cockpit', zeichen: '◧' },
  { ziel: '/prozesse', schluessel: 'nav.prozesse', zeichen: '▤' },
  { ziel: '/tools', schluessel: 'nav.tools', zeichen: '◆' },
  { ziel: '/datenobjekte', schluessel: 'nav.datenobjekte', zeichen: '◇' },
  { ziel: '/gates', schluessel: 'nav.gates', zeichen: '⛨' },
  { ziel: '/lenkung', schluessel: 'nav.lenkung', zeichen: '◎' },
  { ziel: '/klassen', schluessel: 'nav.klassen', zeichen: '▦' },
  { ziel: '/konfiguration', schluessel: 'nav.konfiguration', zeichen: '⚙' },
  {
    ziel: '/nachweis',
    schluessel: 'nav.nachweis',
    zeichen: '❒',
    rollen: ['auditor', 'governance', 'app_administrator'],
  },
  {
    ziel: '/verwaltung',
    schluessel: 'nav.verwaltung',
    zeichen: '☗',
    rollen: ['app_administrator'],
  },
];

export function Kopfzeile() {
  const { sprache, t, pfad } = useSprache();
  const { profil, abmelden } = useSitzung();
  const ort = useLocation();
  const navigiere = useNavigate();
  const [schema, setSchema] = useState<Farbschema>(leseSchema);

  useEffect(() => {
    const wurzel = document.documentElement;
    if (schema === 'system') wurzel.removeAttribute('data-farbschema');
    else wurzel.setAttribute('data-farbschema', schema);
    try {
      window.localStorage.setItem(SCHEMA_SCHLUESSEL, schema);
    } catch {
      /* Ohne Speicher gilt die Wahl nur fuer diese Sitzung. */
    }
  }, [schema]);

  const anfangsbuchstaben = (profil?.name ?? '')
    .split(' ')
    .map((teil) => teil.charAt(0))
    .slice(0, 2)
    .join('')
    .toUpperCase();

  return (
    <aside className="seitenleiste">
      <Link className="marke" to={pfad('/prozesse')}>
        <span className="zeichen" aria-hidden="true">
          G
        </span>
        {t('app.titel')}
      </Link>

      <nav aria-label={t('app.titel')}>
        {PUNKTE.filter(
          (punkt) =>
            punkt.rollen === undefined ||
            (profil?.rollen ?? []).some((z) => punkt.rollen!.includes(z.rolle)),
        ).map((punkt) => (
          <NavLink key={punkt.ziel} to={pfad(punkt.ziel)}>
            <span className="symbol" aria-hidden="true">
              {punkt.zeichen}
            </span>
            {t(punkt.schluessel)}
          </NavLink>
        ))}
      </nav>

      <div className="seitenleiste-fuss">
        {profil !== null && (
          <div className="nutzerzeile">
            <span className="kreis" aria-hidden="true">
              {anfangsbuchstaben}
            </span>
            <span className="name">{profil.name}</span>
          </div>
        )}
        <div className="k-segmente" role="group" aria-label={t('app.farbschema')}>
          {(['system', 'hell', 'dunkel'] as const).map((wahl) => (
            <button
              key={wahl}
              type="button"
              aria-pressed={schema === wahl}
              onClick={() => setSchema(wahl)}
            >
              {t(`app.farbschema.${wahl}`)}
            </button>
          ))}
        </div>
        <div className="k-segmente" role="group" aria-label={t('app.sprache')}>
          {SPRACHEN.map((s) => (
            <button
              key={s}
              type="button"
              aria-pressed={s === sprache}
              onClick={() => navigiere(pfadMitSprache(ort.pathname, s))}
            >
              {s.toUpperCase()}
            </button>
          ))}
        </div>
        {profil !== null && (
          <button type="button" className="k-knopf k-knopf--unauffaellig" onClick={abmelden}>
            {t('app.abmelden')}
          </button>
        )}
      </div>
    </aside>
  );
}

export function Layout() {
  const { t, pfad } = useSprache();
  const { token, laedt } = useSitzung();

  if (token === null) return <Navigate to={pfad('/anmeldung')} replace />;
  return (
    <div className="huelle">
      <Kopfzeile />
      <main className="inhalt">
        {laedt ? <Ladeschimmer beschriftung={t('app.laden')} /> : <Outlet />}
      </main>
    </div>
  );
}
