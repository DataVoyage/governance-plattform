import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type { Aussage, AussageEingabe } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { useSitzung } from '@/zustand/Sitzung';

/**
 * Selbstverpflichtung als strukturierte Checkliste (Architektur 8.4).
 *
 * Jede nummerierte Aussage aus dem Leitdokument ist eine eigene Checkbox mit
 * optionalem Kommentar — kein Freitextfeld. Der Katalog kommt vom Server,
 * damit Wortlaut und Reihenfolge an genau einer Stelle stehen.
 */
export function SelbstverpflichtungSeite() {
  const { id } = useParams();
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const navigiere = useNavigate();

  const [aussagen, setAussagen] = useState<Aussage[] | null>(null);
  const [eingaben, setEingaben] = useState<Record<string, AussageEingabe>>({});
  const [fehler, setFehler] = useState<string | null>(null);

  useEffect(() => {
    if (token === null) return;
    api
      .katalog(token)
      .then((katalog) => {
        const eintrag = katalog.find((k) => k.typ === 'prozesseigner');
        setAussagen(eintrag?.aussagen ?? []);
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, t]);

  function setze(aussageId: string, teil: Partial<AussageEingabe>) {
    setEingaben((bisher) => ({
      ...bisher,
      [aussageId]: {
        ...{ bestaetigt: false, kommentar: '' },
        ...(bisher[aussageId] ?? {}),
        ...teil,
      },
    }));
  }

  async function absenden(ereignis: FormEvent) {
    ereignis.preventDefault();
    if (token === null || id === undefined) return;
    setFehler(null);
    try {
      await api.selbstverpflichtungAbgeben(token, id, eingaben);
      navigiere(pfad(`/prozesse/${id}`));
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  if (aussagen === null)
    return fehler !== null ? <p role="alert">{fehler}</p> : <p>{t('app.laden')}</p>;

  return (
    <form className="formular" onSubmit={absenden}>
      <h1>{t('sv.titel')}</h1>
      <p>{t('sv.hinweis')}</p>

      {aussagen.map((aussage) => (
        <fieldset key={aussage.id}>
          <legend>{aussage.id}</legend>
          <label htmlFor={`bestaetigt-${aussage.id}`}>
            <input
              id={`bestaetigt-${aussage.id}`}
              type="checkbox"
              checked={eingaben[aussage.id]?.bestaetigt ?? false}
              onChange={(e) => setze(aussage.id, { bestaetigt: e.target.checked })}
            />
            {aussage.text}
          </label>
          <label htmlFor={`kommentar-${aussage.id}`}>
            {t('sv.kommentar')}
            <input
              id={`kommentar-${aussage.id}`}
              value={eingaben[aussage.id]?.kommentar ?? ''}
              onChange={(e) => setze(aussage.id, { kommentar: e.target.value })}
            />
          </label>
        </fieldset>
      ))}

      <button type="submit">{t('sv.speichern')}</button>
      <p>
        <Link to={pfad(`/prozesse/${id}`)}>{t('app.zurueck')}</Link>
      </p>
      {fehler !== null && <p role="alert">{fehler}</p>}
    </form>
  );
}
