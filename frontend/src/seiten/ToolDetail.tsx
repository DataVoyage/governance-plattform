import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type { Prozess, ToolObjekt } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { useSitzung } from '@/zustand/Sitzung';

/**
 * Asset-Sicht: an welchen Prozessen hängt dieses Tool, und was erbt es daraus?
 *
 * Die geerbte Klassifikation ist immer das Maximum aller Prozesskanten
 * (Leitdokument A.4.4) und wird hier zusammen mit ihren Quellen gezeigt.
 */
export function ToolDetail() {
  const { id } = useParams();
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const [tool, setTool] = useState<ToolObjekt | null>(null);
  const [prozesse, setProzesse] = useState<Prozess[]>([]);
  const [auswahl, setAuswahl] = useState('');
  const [fehler, setFehler] = useState<string | null>(null);

  useEffect(() => {
    if (token === null || id === undefined) return;
    Promise.all([api.tool(token, id), api.prozesse(token)])
      .then(([geladen, alle]) => {
        setTool(geladen);
        setProzesse(alle);
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, id, t]);

  async function fuehreAus(aktion: () => Promise<ToolObjekt>) {
    setFehler(null);
    try {
      setTool(await aktion());
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  if (tool === null) return fehler !== null ? <p role="alert">{fehler}</p> : <p>{t('app.laden')}</p>;

  const verknuepfbar = prozesse.filter((p) => !tool.prozessobjekt_ids.includes(p.id));
  const unbestaetigt = tool.status === 'importiert_unbestaetigt';

  return (
    <article>
      <h1>{tool.name}</h1>
      <Link to={pfad('/tools')}>{t('app.zurueck')}</Link>

      <dl className="felder">
        <dt>{t('asset.feld.status')}</dt>
        <dd data-testid="status">{t(`asset.status.${tool.status}` as never)}</dd>
        <dt>{t('asset.feld.herkunft')}</dt>
        <dd>{t(`asset.herkunft.${tool.herkunft}` as never)}</dd>
        <dt>{t('asset.feld.technologie')}</dt>
        <dd>{tool.technologie ?? '—'}</dd>
        <dt>{t('asset.feld.kategorie')}</dt>
        <dd>{tool.kategorie ?? '—'}</dd>
      </dl>

      {tool.schreibgeschuetzte_felder.length > 0 && <p>{t('asset.importHinweis')}</p>}

      {unbestaetigt && (
        <section>
          <p role="alert">{t('asset.bestaetigenHinweis')}</p>
          <button
            type="button"
            onClick={() => fuehreAus(() => api.toolBestaetigen(token as string, tool.id))}
          >
            {t('asset.bestaetigen')}
          </button>
        </section>
      )}

      <section className="abgeleitet">
        <h2>{t('asset.geerbt.titel')}</h2>
        <p>{t('asset.geerbt.hinweis')}</p>
        <dl className="felder">
          <dt>{t('asset.geerbt.kritikalitaet')}</dt>
          <dd data-testid="geerbt-kritikalitaet">{tool.geerbt.kritikalitaet}</dd>
          <dt>{t('asset.geerbt.reichweite')}</dt>
          <dd data-testid="geerbt-reichweite">{tool.geerbt.reichweite ?? '—'}</dd>
          <dt>{t('asset.geerbt.tier')}</dt>
          <dd data-testid="geerbt-tier">{tool.geerbt.tier ?? '—'}</dd>
          <dt>{t('asset.geerbt.kKlassen')}</dt>
          <dd data-testid="geerbt-k-klassen">{tool.geerbt.k_klassen.join(', ') || '—'}</dd>
        </dl>
      </section>

      <section>
        <h2>{t('asset.prozesse.titel')}</h2>
        {tool.prozessobjekt_ids.length === 0 ? (
          <p>{t('asset.prozesse.leer')}</p>
        ) : (
          <ul>
            {tool.prozessobjekt_ids.map((prozessId) => (
              <li key={prozessId}>
                <Link to={pfad(`/prozesse/${prozessId}`)}>
                  {prozesse.find((p) => p.id === prozessId)?.name ?? prozessId}
                </Link>{' '}
                <button
                  type="button"
                  onClick={() =>
                    fuehreAus(() =>
                      api.toolVonProzessLoesen(token as string, tool.id, prozessId),
                    )
                  }
                >
                  {t('asset.prozesse.loesen')}
                </button>
              </li>
            ))}
          </ul>
        )}

        {!unbestaetigt && verknuepfbar.length > 0 && (
          <>
            <label htmlFor="prozesswahl">{t('asset.prozesse.verknuepfen')}</label>
            <select
              id="prozesswahl"
              value={auswahl}
              onChange={(e) => setAuswahl(e.target.value)}
            >
              <option value="">—</option>
              {verknuepfbar.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>{' '}
            <button
              type="button"
              disabled={auswahl === ''}
              onClick={() =>
                fuehreAus(() =>
                  api.toolMitProzessVerknuepfen(token as string, tool.id, auswahl),
                ).then(() => setAuswahl(''))
              }
            >
              {t('asset.prozesse.verknuepfen')}
            </button>
          </>
        )}
      </section>

      {fehler !== null && <p role="alert">{fehler}</p>}
    </article>
  );
}
