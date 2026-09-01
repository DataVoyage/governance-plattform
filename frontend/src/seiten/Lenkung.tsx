import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type { Aufloesungsart, Lenkungsvorgang, ToolObjekt } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { useSitzung } from '@/zustand/Sitzung';

const ARTEN: Aufloesungsart[] = ['anpassen', 'rahmen_erweitern', 'stilllegen'];

/**
 * Lenkungsvorgänge mit ihren drei Auflösungswegen (Leitdokument A.13.6).
 *
 * Jede Auflösung ist eine eigene, benannte Aktion — keine Interpretation eines
 * Freitextkommentars. „Rahmen erweitern" verlangt zusätzlich die neue
 * Bewertung; ohne sie schließt der Vorgang nicht.
 */
export function Lenkung() {
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const [vorgaenge, setVorgaenge] = useState<Lenkungsvorgang[] | null>(null);
  const [tools, setTools] = useState<ToolObjekt[]>([]);
  const [arten, setArten] = useState<Record<string, Aufloesungsart>>({});
  const [bewertungen, setBewertungen] = useState<Record<string, string>>({});
  const [fehler, setFehler] = useState<string | null>(null);

  useEffect(() => {
    if (token === null) return;
    Promise.all([api.lenkungsvorgaenge(token), api.tools(token)])
      .then(([offen, alle]) => {
        setVorgaenge(offen);
        setTools(alle);
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, t]);

  async function aufloesen(vorgang: Lenkungsvorgang) {
    if (token === null) return;
    setFehler(null);
    const art = arten[vorgang.id] ?? 'anpassen';
    try {
      await api.lenkungAufloesen(token, vorgang.id, {
        art,
        bewertung_id: art === 'rahmen_erweitern' ? (bewertungen[vorgang.id] ?? null) : null,
      });
      setVorgaenge((bisher) => (bisher ?? []).filter((v) => v.id !== vorgang.id));
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  if (vorgaenge === null)
    return fehler !== null ? <p role="alert">{fehler}</p> : <p>{t('app.laden')}</p>;

  return (
    <section>
      <h1>{t('lenkung.titel')}</h1>
      {vorgaenge.length === 0 ? (
        <p>{t('lenkung.leer')}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t('lenkung.tool')}</th>
              <th>{t('lenkung.stufe')}</th>
              <th>{t('lenkung.frist')}</th>
              <th>{t('lenkung.aufloesen')}</th>
            </tr>
          </thead>
          <tbody>
            {vorgaenge.map((vorgang) => {
              const art = arten[vorgang.id] ?? 'anpassen';
              return (
                <tr key={vorgang.id}>
                  <td>
                    <Link to={pfad(`/tools/${vorgang.tool_objekt_id}`)}>
                      {tools.find((tool) => tool.id === vorgang.tool_objekt_id)?.name ??
                        vorgang.tool_objekt_id}
                    </Link>
                  </td>
                  <td data-testid={`stufe-${vorgang.id}`}>
                    {vorgang.eskalationsstufe}
                    {vorgang.eskalationsstufe >= 3 && <p>{t('lenkung.stufe3')}</p>}
                  </td>
                  <td>{vorgang.frist.slice(0, 10)}</td>
                  <td>
                    <select
                      aria-label={`${t('lenkung.art')} — ${vorgang.id}`}
                      value={art}
                      onChange={(e) =>
                        setArten((bisher) => ({
                          ...bisher,
                          [vorgang.id]: e.target.value as Aufloesungsart,
                        }))
                      }
                    >
                      {ARTEN.map((wert) => (
                        <option key={wert} value={wert}>
                          {t(`lenkung.art.${wert}` as never)}
                        </option>
                      ))}
                    </select>
                    {art === 'rahmen_erweitern' && (
                      <>
                        <input
                          aria-label={`${t('lenkung.bewertung')} — ${vorgang.id}`}
                          value={bewertungen[vorgang.id] ?? ''}
                          onChange={(e) =>
                            setBewertungen((bisher) => ({
                              ...bisher,
                              [vorgang.id]: e.target.value,
                            }))
                          }
                        />
                        <small>{t('lenkung.bewertungPflicht')}</small>
                      </>
                    )}
                    <button type="button" onClick={() => aufloesen(vorgang)}>
                      {t('lenkung.aufloesen')}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      {fehler !== null && <p role="alert">{fehler}</p>}
    </section>
  );
}
