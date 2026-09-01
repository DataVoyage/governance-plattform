import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { api } from '@/api/client';
import type { Organisationseinheit, Prozess } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { useSitzung } from '@/zustand/Sitzung';

function bezeichne(einheit: Organisationseinheit | undefined): string {
  if (einheit === undefined) return '—';
  return einheit.ebene === 'LAND' ? `LAND-${einheit.land_code}` : 'INT';
}

export function ProzessDetail() {
  const { id } = useParams();
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const [prozess, setProzess] = useState<Prozess | null>(null);
  const [einheiten, setEinheiten] = useState<Organisationseinheit[]>([]);
  const [fehler, setFehler] = useState<string | null>(null);

  useEffect(() => {
    if (token === null || id === undefined) return;
    Promise.all([api.prozess(token, id), api.organisationseinheiten(token)])
      .then(([geladen, orgs]) => {
        setProzess(geladen);
        setEinheiten(orgs);
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, id, t]);

  if (fehler !== null) return <p role="alert">{fehler}</p>;
  if (prozess === null) return <p>{t('app.laden')}</p>;

  return (
    <article>
      <h1>{prozess.name}</h1>
      <Link to={pfad('/prozesse')}>{t('app.zurueck')}</Link>

      <dl className="felder">
        <dt>{t('prozess.feld.status')}</dt>
        <dd>{t(`status.${prozess.status}` as never)}</dd>
        <dt>{t('prozess.feld.supplier')}</dt>
        <dd>{prozess.supplier || '—'}</dd>
        <dt>{t('prozess.feld.processSteps')}</dt>
        <dd>{prozess.process_steps || '—'}</dd>
        <dt>{t('prozess.feld.output')}</dt>
        <dd>{prozess.output || '—'}</dd>
        <dt>{t('prozess.feld.customer')}</dt>
        <dd>{t(`kundenkreis.${prozess.customer}` as never)}</dd>
        <dt>{t('prozess.feld.ausfallfolge')}</dt>
        <dd>{t(`ausfallfolge.${prozess.ausfallfolge}` as never)}</dd>
      </dl>

      <section className="abgeleitet">
        <h2>{t('prozess.abgeleitet.titel')}</h2>
        <p>{t('prozess.abgeleitet.hinweis')}</p>
        <dl className="felder">
          <dt>{t('prozess.feld.reichweite')}</dt>
          <dd data-testid="reichweite">{prozess.reichweite ?? '—'}</dd>
          <dt>{t('prozess.feld.kritikalitaet')}</dt>
          <dd data-testid="kritikalitaet">{prozess.kritikalitaet}</dd>
          <dt>{t('prozess.feld.mitbestimmung')}</dt>
          <dd data-testid="mitbestimmung">{prozess.mitbestimmung_flag ? t('ja') : t('nein')}</dd>
        </dl>
      </section>

      <section>
        <h2>{t('prozess.umsetzungen.titel')}</h2>
        {prozess.umsetzungen.length === 0 ? (
          <p>{t('prozess.umsetzungen.leer')}</p>
        ) : (
          <ul>
            {prozess.umsetzungen.map((u) => (
              <li key={u.id}>
                {bezeichne(einheiten.find((e) => e.id === u.land_org_id))}
                {u.lokale_abweichung ? ` — ${u.lokale_abweichung}` : ''}
              </li>
            ))}
          </ul>
        )}
      </section>
    </article>
  );
}
