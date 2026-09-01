import { Link, Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom';

import { SPRACHEN, type Sprache } from '@/i18n';
import { useSprache } from '@/i18n/SprachKontext';
import { useSitzung } from '@/zustand/Sitzung';

/** Ersetzt das Sprachsegment im Pfad, ohne die Ansicht zu verlassen. */
export function pfadMitSprache(pfad: string, sprache: Sprache): string {
  const segmente = pfad.split('/').filter(Boolean);
  if (segmente.length === 0) return `/${sprache}`;
  segmente[0] = sprache;
  return `/${segmente.join('/')}`;
}

export function Kopfzeile() {
  const { sprache, t, pfad } = useSprache();
  const { profil, abmelden } = useSitzung();
  const ort = useLocation();
  const navigiere = useNavigate();

  return (
    <header className="kopfzeile">
      <Link className="marke" to={pfad('/prozesse')}>
        {t('app.titel')}
      </Link>
      <nav aria-label={t('app.titel')}>
        <Link to={pfad('/prozesse')}>{t('nav.prozesse')}</Link>{' '}
        <Link to={pfad('/tools')}>{t('nav.tools')}</Link>{' '}
        <Link to={pfad('/datenobjekte')}>{t('nav.datenobjekte')}</Link>{' '}
        <Link to={pfad('/gates')}>{t('nav.gates')}</Link>{' '}
        <Link to={pfad('/lenkung')}>{t('nav.lenkung')}</Link>
      </nav>
      <div className="kopfzeile-rechts">
        <label htmlFor="sprachwahl">{t('app.sprache')}</label>
        <select
          id="sprachwahl"
          value={sprache}
          onChange={(e) => navigiere(pfadMitSprache(ort.pathname, e.target.value as Sprache))}
        >
          {SPRACHEN.map((s) => (
            <option key={s} value={s}>
              {s.toUpperCase()}
            </option>
          ))}
        </select>
        {profil !== null && (
          <>
            <span className="nutzer">{profil.name}</span>
            <button type="button" onClick={abmelden}>
              {t('app.abmelden')}
            </button>
          </>
        )}
      </div>
    </header>
  );
}

export function Layout() {
  const { t, pfad } = useSprache();
  const { token, laedt } = useSitzung();

  if (token === null) return <Navigate to={pfad('/anmeldung')} replace />;
  return (
    <div className="huelle">
      <Kopfzeile />
      <main>{laedt ? <p>{t('app.laden')}</p> : <Outlet />}</main>
    </div>
  );
}
