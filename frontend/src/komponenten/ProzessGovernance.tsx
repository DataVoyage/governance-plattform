import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type { GateTyp, GateVorgang, Selbstverpflichtung } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { useSitzung } from '@/zustand/Sitzung';

/**
 * Selbstverpflichtung und Gate-Vorgänge eines Prozessobjekts
 * (Architektur 8.4 und 8.5).
 *
 * Gate 2 verlangt genau einen der fünf abschließend aufgezählten Auslöser; ein
 * sechster, freier Grund ist in der Oberfläche nicht wählbar, weil die Liste
 * im Leitdokument bewusst abschließend ist.
 */
export function ProzessGovernance({ prozessId }: { prozessId: string }) {
  const { t, pfad } = useSprache();
  const { token } = useSitzung();

  const [selbstverpflichtungen, setSelbstverpflichtungen] = useState<Selbstverpflichtung[]>([]);
  const [gates, setGates] = useState<GateVorgang[]>([]);
  const [ausloeserListe, setAusloeserListe] = useState<string[]>([]);
  const [gateTyp, setGateTyp] = useState<GateTyp>('1');
  const [ausloeser, setAusloeser] = useState('');
  const [begruendung, setBegruendung] = useState('');
  const [fehler, setFehler] = useState<string | null>(null);

  useEffect(() => {
    if (token === null) return;
    Promise.all([
      api.selbstverpflichtungen(token, prozessId),
      api.gates(token, prozessId),
      api.gateAusloeser(token),
    ])
      .then(([sv, vorgaenge, ausloeserWerte]) => {
        setSelbstverpflichtungen(sv);
        setGates(vorgaenge);
        setAusloeserListe(ausloeserWerte);
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, prozessId, t]);

  async function einreichen(ereignis: FormEvent) {
    ereignis.preventDefault();
    if (token === null) return;
    setFehler(null);
    try {
      const vorgang = await api.gateEinreichen(token, prozessId, {
        gate_typ: gateTyp,
        ausloeser: gateTyp === '2' ? ausloeser : null,
        begruendung,
      });
      setGates((bisher) => [vorgang, ...bisher]);
      setBegruendung('');
      setAusloeser('');
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  const aktuelle = selbstverpflichtungen[0];

  return (
    <>
      <section>
        <h2>{t('sv.status')}</h2>
        {aktuelle === undefined ? (
          <p>{t('sv.keine')}</p>
        ) : (
          <dl className="felder">
            <dt>{t('gate.status')}</dt>
            <dd data-testid="sv-status">
              {aktuelle.vollstaendig ? t('sv.vollstaendig') : t('sv.unvollstaendig')}
            </dd>
            <dt>{t('sv.gueltigBis')}</dt>
            <dd>{aktuelle.gueltig_bis ? aktuelle.gueltig_bis.slice(0, 10) : '—'}</dd>
          </dl>
        )}
        <Link className="knopf" to={pfad(`/prozesse/${prozessId}/selbstverpflichtung`)}>
          {t('sv.abgeben')}
        </Link>
      </section>

      <section>
        <h2>{t('gate.titel')}</h2>
        {gates.length === 0 ? (
          <p>{t('gate.leer')}</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>{t('gate.typ')}</th>
                <th>{t('gate.ausloeser')}</th>
                <th>{t('gate.status')}</th>
                <th>{t('gate.kommentar')}</th>
              </tr>
            </thead>
            <tbody>
              {gates.map((gate) => (
                <tr key={gate.id}>
                  <td>{t(`gate.typ.${gate.gate_typ}` as never)}</td>
                  <td>{gate.ausloeser ?? '—'}</td>
                  <td>{t(`gate.status.${gate.status}` as never)}</td>
                  <td>{gate.entscheidungskommentar || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <form className="formular" onSubmit={einreichen}>
          <label htmlFor="gate-typ">{t('gate.typ')}</label>
          <select
            id="gate-typ"
            value={gateTyp}
            onChange={(e) => setGateTyp(e.target.value as GateTyp)}
          >
            <option value="1">{t('gate.typ.1')}</option>
            <option value="2">{t('gate.typ.2')}</option>
          </select>

          {gateTyp === '2' && (
            <>
              <label htmlFor="gate-ausloeser">{t('gate.ausloeser')}</label>
              <select
                id="gate-ausloeser"
                required
                value={ausloeser}
                onChange={(e) => setAusloeser(e.target.value)}
              >
                <option value="">—</option>
                {ausloeserListe.map((wert) => (
                  <option key={wert} value={wert}>
                    {wert}
                  </option>
                ))}
              </select>
              <small>{t('gate.ausloeserPflicht')}</small>
            </>
          )}

          <label htmlFor="gate-begruendung">{t('gate.begruendung')}</label>
          <input
            id="gate-begruendung"
            value={begruendung}
            onChange={(e) => setBegruendung(e.target.value)}
          />
          <button type="submit">{t('gate.einreichen')}</button>
        </form>
        {fehler !== null && <p role="alert">{fehler}</p>}
      </section>
    </>
  );
}
