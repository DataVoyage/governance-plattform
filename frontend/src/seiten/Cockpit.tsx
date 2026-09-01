import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import { api } from '@/api/client';
import type { CockpitEintrag, CockpitZeile, CockpitZeilenkopf, Fachbereich } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { useSitzung } from '@/zustand/Sitzung';

/** Baut aus Zielmodul und Filter den Deep-Link ins passende Modul (Architektur 9.3). */
export function zielPfad(eintrag: CockpitEintrag, pfad: (rest: string) => string): string {
  const { id, ...rest } = eintrag.ziel_filter;
  if (id !== undefined && (eintrag.ziel_modul === 'prozesse' || eintrag.ziel_modul === 'tools')) {
    return pfad(`/${eintrag.ziel_modul}/${id}`);
  }
  const abfrage = new URLSearchParams(rest).toString();
  return pfad(`/${eintrag.ziel_modul}${abfrage ? `?${abfrage}` : ''}`);
}

function useFachbereiche(): Fachbereich[] {
  const { token } = useSitzung();
  const [fachbereiche, setFachbereiche] = useState<Fachbereich[]>([]);
  useEffect(() => {
    if (token === null) return;
    api
      .fachbereiche(token)
      .then(setFachbereiche)
      .catch(() => setFachbereiche([]));
  }, [token]);
  return fachbereiche;
}

/**
 * Cockpit-Übersicht (Architektur 8.7).
 *
 * Kein überladenes Dashboard, sondern eine Liste gezielt aufrufbarer Zeilen.
 * Der Fachbereichsfilter steht in der URL, damit eine gefilterte Ansicht
 * teilbar ist (Architektur 9.3) — er verleiht dabei keine Rechte: was ein
 * Nutzer sieht, entscheidet weiterhin allein der Server.
 */
export function Cockpit() {
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const [suche, setSuche] = useSearchParams();
  const fachbereiche = useFachbereiche();
  const [zeilen, setZeilen] = useState<CockpitZeilenkopf[] | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);

  const fachbereich = suche.get('fachbereich') ?? '';

  useEffect(() => {
    if (token === null) return;
    api
      .cockpit(token, fachbereich ? `?fachbereich_id=${fachbereich}` : '')
      .then(setZeilen)
      .catch(() => setFehler(t('app.fehler')));
  }, [token, fachbereich, t]);

  if (fehler !== null) return <p role="alert">{fehler}</p>;
  if (zeilen === null) return <p>{t('app.laden')}</p>;

  return (
    <section>
      <h1>{t('cockpit.titel')}</h1>
      <p>{t('cockpit.hinweis')}</p>

      <label htmlFor="cockpit-fachbereich">{t('cockpit.fachbereich')}</label>
      <select
        id="cockpit-fachbereich"
        value={fachbereich}
        onChange={(e) =>
          setSuche(e.target.value === '' ? {} : { fachbereich: e.target.value })
        }
      >
        <option value="">{t('cockpit.alleFachbereiche')}</option>
        {fachbereiche.map((f) => (
          <option key={f.id} value={f.id}>
            {f.name}
          </option>
        ))}
      </select>

      <table>
        <thead>
          <tr>
            <th>{t('cockpit.titel')}</th>
            <th>{t('cockpit.anzahl')}</th>
            <th>{t('cockpit.oeffnen')}</th>
          </tr>
        </thead>
        <tbody>
          {zeilen.map((zeile) => (
            <tr key={zeile.schluessel}>
              <td>
                {zeile.titel}
                <br />
                <small>{zeile.beschreibung}</small>
              </td>
              <td data-testid={`anzahl-${zeile.schluessel}`}>{zeile.anzahl}</td>
              <td>
                <Link
                  to={pfad(
                    `/cockpit/${zeile.schluessel}${fachbereich ? `?fachbereich=${fachbereich}` : ''}`,
                  )}
                >
                  {t('cockpit.oeffnen')}
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

/** Eine einzelne Cockpit-Zeile mit ihren Einträgen und deren Zielen. */
export function CockpitZeileAnsicht() {
  const { schluessel } = useParams();
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const [suche] = useSearchParams();
  const [zeile, setZeile] = useState<CockpitZeile | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);

  const fachbereich = suche.get('fachbereich') ?? '';

  useEffect(() => {
    if (token === null || schluessel === undefined) return;
    api
      .cockpitZeile(token, schluessel, fachbereich ? `?fachbereich_id=${fachbereich}` : '')
      .then(setZeile)
      .catch(() => setFehler(t('app.fehler')));
  }, [token, schluessel, fachbereich, t]);

  if (fehler !== null) return <p role="alert">{fehler}</p>;
  if (zeile === null) return <p>{t('app.laden')}</p>;

  return (
    <section>
      <h1>{zeile.titel}</h1>
      <p>{zeile.beschreibung}</p>
      <Link to={pfad('/cockpit')}>{t('cockpit.zurueck')}</Link>

      {zeile.aggregat !== null && (
        <dl className="felder" data-testid="aggregat">
          {Object.entries(zeile.aggregat).map(([gruppe, werte]) => (
            <div key={gruppe}>
              <dt>{gruppe}</dt>
              <dd>
                {Object.entries(werte)
                  .map(([schlüssel, verteilung]) =>
                    typeof verteilung === 'object'
                      ? `${schlüssel}: ${Object.entries(verteilung)
                          .map(([tier, anzahl]) => `Tier ${tier} × ${anzahl}`)
                          .join(', ')}`
                      : `${schlüssel}: ${String(verteilung)}`,
                  )
                  .join(' · ') || '—'}
              </dd>
            </div>
          ))}
        </dl>
      )}

      {zeile.eintraege.length === 0 ? (
        <p>{t('cockpit.leer')}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t('cockpit.eintrag')}</th>
              <th>{t('cockpit.hinweisSpalte')}</th>
              <th>{t('cockpit.ziel')}</th>
            </tr>
          </thead>
          <tbody>
            {zeile.eintraege.map((eintrag) => (
              <tr key={eintrag.id}>
                <td>{eintrag.titel}</td>
                <td>{eintrag.hinweis}</td>
                <td>
                  <Link to={zielPfad(eintrag, pfad)}>{eintrag.ziel_modul}</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
