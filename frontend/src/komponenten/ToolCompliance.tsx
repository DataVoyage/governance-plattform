import { useEffect, useState, type FormEvent } from 'react';

import { ApiFehler, api } from '@/api/client';
import type { ComplianceFarbe, ComplianceZustand } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { useSitzung } from '@/zustand/Sitzung';

const FARBEN: ComplianceFarbe[] = ['gruen', 'gelb', 'rot'];

/**
 * Compliance-Zeitreihe eines Tool-Objekts (Architektur 8.6).
 *
 * Der aktuelle Zustand ist der oberste Eintrag; ältere bleiben stehen, damit
 * der Verlauf einer Abweichung nachvollziehbar bleibt. Eine rote Meldung
 * eröffnet serverseitig einen Lenkungsvorgang — die Oberfläche weist darauf
 * hin, entscheidet es aber nicht.
 */
export function ToolCompliance({ toolId }: { toolId: string }) {
  const { t } = useSprache();
  const { token } = useSitzung();
  const [verlauf, setVerlauf] = useState<ComplianceZustand[]>([]);
  const [farbe, setFarbe] = useState<ComplianceFarbe>('gruen');
  const [begruendung, setBegruendung] = useState('');
  const [abweichung, setAbweichung] = useState('');
  const [fehler, setFehler] = useState<string | null>(null);

  useEffect(() => {
    if (token === null) return;
    api
      .compliance(token, toolId)
      .then(setVerlauf)
      .catch(() => setFehler(t('app.fehler')));
  }, [token, toolId, t]);

  async function melden(ereignis: FormEvent) {
    ereignis.preventDefault();
    if (token === null) return;
    setFehler(null);
    try {
      const meldung = await api.complianceMelden(token, toolId, {
        farbe,
        begruendung,
        abweichung_art: abweichung || null,
      });
      setVerlauf((bisher) => [meldung.zustand, ...bisher]);
      setBegruendung('');
      setAbweichung('');
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  return (
    <section>
      <h2>{t('compliance.titel')}</h2>
      <p>{t('compliance.hinweis')}</p>

      {verlauf.length === 0 ? (
        <p>{t('compliance.leer')}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t('compliance.farbe')}</th>
              <th>{t('compliance.begruendung')}</th>
              <th>{t('compliance.abweichung')}</th>
              <th>{t('compliance.festgestelltAm')}</th>
            </tr>
          </thead>
          <tbody>
            {verlauf.map((zustand, i) => (
              <tr key={zustand.id} data-testid={i === 0 ? 'aktueller-zustand' : undefined}>
                <td>{t(`compliance.farbe.${zustand.farbe}` as never)}</td>
                <td>{zustand.begruendung || '—'}</td>
                <td>{zustand.abweichung_art ?? '—'}</td>
                <td>{zustand.festgestellt_am.slice(0, 10)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <form className="formular" onSubmit={melden}>
        <label htmlFor="compliance-farbe">{t('compliance.melden')}</label>
        <select
          id="compliance-farbe"
          value={farbe}
          onChange={(e) => setFarbe(e.target.value as ComplianceFarbe)}
        >
          {FARBEN.map((wert) => (
            <option key={wert} value={wert}>
              {t(`compliance.farbe.${wert}` as never)}
            </option>
          ))}
        </select>
        {farbe === 'rot' && <small>{t('compliance.rotHinweis')}</small>}

        <label htmlFor="compliance-begruendung">{t('compliance.begruendung')}</label>
        <input
          id="compliance-begruendung"
          value={begruendung}
          onChange={(e) => setBegruendung(e.target.value)}
        />

        <label htmlFor="compliance-abweichung">{t('compliance.abweichung')}</label>
        <input
          id="compliance-abweichung"
          value={abweichung}
          onChange={(e) => setAbweichung(e.target.value)}
        />

        <button type="submit">{t('compliance.melden')}</button>
      </form>

      {fehler !== null && <p role="alert">{fehler}</p>}
    </section>
  );
}
