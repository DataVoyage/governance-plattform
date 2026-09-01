import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '@/api/client';
import type { Prozess } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { useSitzung } from '@/zustand/Sitzung';

export function ProzessListe() {
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const [prozesse, setProzesse] = useState<Prozess[] | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);

  useEffect(() => {
    if (token === null) return;
    api
      .prozesse(token)
      .then(setProzesse)
      .catch(() => setFehler(t('app.fehler')));
  }, [token, t]);

  if (fehler !== null) return <p role="alert">{fehler}</p>;
  if (prozesse === null) return <p>{t('app.laden')}</p>;

  return (
    <section>
      <h1>{t('prozess.liste.titel')}</h1>
      <Link className="knopf" to={pfad('/prozesse/neu')}>
        {t('prozess.liste.neu')}
      </Link>
      {prozesse.length === 0 ? (
        <p>{t('prozess.liste.leer')}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t('prozess.feld.name')}</th>
              <th>{t('prozess.feld.status')}</th>
              <th>{t('prozess.feld.reichweite')}</th>
              <th>{t('prozess.feld.kritikalitaet')}</th>
            </tr>
          </thead>
          <tbody>
            {prozesse.map((p) => (
              <tr key={p.id}>
                <td>
                  <Link to={pfad(`/prozesse/${p.id}`)}>{p.name}</Link>
                </td>
                <td>{t(`status.${p.status}` as never)}</td>
                <td>{p.reichweite ?? '—'}</td>
                <td>{p.kritikalitaet}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
