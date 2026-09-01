import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type { GateVorgang, Prozess } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { useSitzung } from '@/zustand/Sitzung';

/**
 * Arbeitsvorrat der Governance-Rolle (Architektur 8.5).
 *
 * Entscheiden darf ausschliesslich die Governance-Rolle; das Frontend blendet
 * die Knöpfe für andere aus, verlässt sich aber nicht darauf — die Route prüft
 * unabhängig (Architektur 10.2).
 */
export function Gates() {
  const { t, pfad } = useSprache();
  const { token, hatRolle } = useSitzung();
  const [gates, setGates] = useState<GateVorgang[] | null>(null);
  const [prozesse, setProzesse] = useState<Prozess[]>([]);
  const [kommentare, setKommentare] = useState<Record<string, string>>({});
  const [fehler, setFehler] = useState<string | null>(null);

  useEffect(() => {
    if (token === null) return;
    Promise.all([api.offeneGates(token), api.prozesse(token)])
      .then(([offen, alle]) => {
        setGates(offen);
        setProzesse(alle);
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, t]);

  async function entscheiden(gateId: string, status: 'freigegeben' | 'abgelehnt') {
    if (token === null) return;
    setFehler(null);
    try {
      await api.gateEntscheiden(token, gateId, status, kommentare[gateId] ?? '');
      setGates((bisher) => (bisher ?? []).filter((g) => g.id !== gateId));
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  if (gates === null)
    return fehler !== null ? <p role="alert">{fehler}</p> : <p>{t('app.laden')}</p>;

  const darfEntscheiden = hatRolle('governance');

  return (
    <section>
      <h1>{t('gate.arbeitsvorrat')}</h1>
      {gates.length === 0 ? (
        <p>{t('gate.arbeitsvorratLeer')}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t('gate.prozess')}</th>
              <th>{t('gate.typ')}</th>
              <th>{t('gate.ausloeser')}</th>
              <th>{t('gate.status')}</th>
              {darfEntscheiden && <th>{t('gate.entscheiden')}</th>}
            </tr>
          </thead>
          <tbody>
            {gates.map((gate) => (
              <tr key={gate.id}>
                <td>
                  <Link to={pfad(`/prozesse/${gate.prozessobjekt_id}`)}>
                    {prozesse.find((p) => p.id === gate.prozessobjekt_id)?.name ??
                      gate.prozessobjekt_id}
                  </Link>
                </td>
                <td>{t(`gate.typ.${gate.gate_typ}` as never)}</td>
                <td>{gate.ausloeser ?? '—'}</td>
                <td>{t(`gate.status.${gate.status}` as never)}</td>
                {darfEntscheiden && (
                  <td>
                    <input
                      aria-label={`${t('gate.kommentar')} — ${gate.id}`}
                      value={kommentare[gate.id] ?? ''}
                      onChange={(e) =>
                        setKommentare((bisher) => ({ ...bisher, [gate.id]: e.target.value }))
                      }
                    />
                    <button type="button" onClick={() => entscheiden(gate.id, 'freigegeben')}>
                      {t('gate.freigeben')}
                    </button>{' '}
                    <button type="button" onClick={() => entscheiden(gate.id, 'abgelehnt')}>
                      {t('gate.ablehnen')}
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {fehler !== null && <p role="alert">{fehler}</p>}
    </section>
  );
}
