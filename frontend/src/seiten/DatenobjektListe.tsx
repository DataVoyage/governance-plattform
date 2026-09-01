import { useEffect, useState, type FormEvent } from 'react';

import { ApiFehler, api } from '@/api/client';
import type { DatenObjekt, Datenkategorie } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { useSitzung } from '@/zustand/Sitzung';

const KATEGORIEN: Datenkategorie[] = [
  'oeffentlich',
  'intern',
  'vertraulich',
  'personenbezogen',
  'mitarbeiterbezogen',
  'besondere_kategorie',
];

/**
 * Datenobjekte mit ihrer Kategorie (Architektur 8.3).
 *
 * Die Kategorie wird genau hier gepflegt und nirgends sonst: verknüpfte
 * Prozessobjekte lesen sie, statt sie erneut zu erfassen (Leitdokument P5).
 */
export function DatenobjektListe() {
  const { t } = useSprache();
  const { token } = useSitzung();
  const [datenobjekte, setDatenobjekte] = useState<DatenObjekt[] | null>(null);
  const [name, setName] = useState('');
  const [fehler, setFehler] = useState<string | null>(null);

  useEffect(() => {
    if (token === null) return;
    api
      .datenobjekte(token)
      .then(setDatenobjekte)
      .catch(() => setFehler(t('app.fehler')));
  }, [token, t]);

  async function anlegen(ereignis: FormEvent) {
    ereignis.preventDefault();
    if (token === null) return;
    try {
      const angelegt = await api.datenobjektAnlegen(token, { name });
      setDatenobjekte((bisher) => [...(bisher ?? []), angelegt]);
      setName('');
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  async function kategorisieren(id: string, kategorie: string) {
    if (token === null) return;
    try {
      const aktualisiert = await api.datenobjektKategorisieren(
        token,
        id,
        kategorie === '' ? null : (kategorie as Datenkategorie),
      );
      setDatenobjekte((bisher) =>
        (bisher ?? []).map((d) => (d.id === aktualisiert.id ? aktualisiert : d)),
      );
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  if (datenobjekte === null)
    return fehler !== null ? <p role="alert">{fehler}</p> : <p>{t('app.laden')}</p>;

  return (
    <section>
      <h1>{t('asset.datenobjekte.titel')}</h1>
      {datenobjekte.length === 0 ? (
        <p>{t('asset.datenobjekte.leer')}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t('asset.feld.name')}</th>
              <th>{t('asset.feld.kategorie')}</th>
              <th>{t('asset.feld.herkunft')}</th>
            </tr>
          </thead>
          <tbody>
            {datenobjekte.map((datenobjekt) => (
              <tr key={datenobjekt.id}>
                <td>{datenobjekt.name}</td>
                <td>
                  <select
                    aria-label={`${t('asset.feld.kategorie')} — ${datenobjekt.name}`}
                    value={datenobjekt.kategorie ?? ''}
                    onChange={(e) => kategorisieren(datenobjekt.id, e.target.value)}
                  >
                    <option value="">{t('asset.kategorie.keine')}</option>
                    {KATEGORIEN.map((kategorie) => (
                      <option key={kategorie} value={kategorie}>
                        {kategorie}
                      </option>
                    ))}
                  </select>
                </td>
                <td>{t(`asset.herkunft.${datenobjekt.herkunft}` as never)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <form className="formular" onSubmit={anlegen}>
        <label htmlFor="datenobjekt-name">{t('asset.datenobjekte.neu')}</label>
        <input
          id="datenobjekt-name"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button type="submit">{t('asset.speichern')}</button>
      </form>

      {fehler !== null && <p role="alert">{fehler}</p>}
    </section>
  );
}
