import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type { ToolObjekt } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { useSitzung } from '@/zustand/Sitzung';

/**
 * Asset-Sicht auf Tool-Objekte (Architektur 8.3).
 *
 * Reine Verwaltungsaufgabe, deshalb tabellarisch — hier ist Übersicht
 * wichtiger als Führung (Architektur 9.1, Punkt 3).
 */
export function ToolListe() {
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const [tools, setTools] = useState<ToolObjekt[] | null>(null);
  const [name, setName] = useState('');
  const [fehler, setFehler] = useState<string | null>(null);

  useEffect(() => {
    if (token === null) return;
    api
      .tools(token)
      .then(setTools)
      .catch(() => setFehler(t('app.fehler')));
  }, [token, t]);

  async function anlegen(ereignis: FormEvent) {
    ereignis.preventDefault();
    if (token === null) return;
    try {
      const angelegt = await api.toolAnlegen(token, { name });
      setTools((bisher) => [...(bisher ?? []), angelegt]);
      setName('');
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  if (fehler !== null) return <p role="alert">{fehler}</p>;
  if (tools === null) return <p>{t('app.laden')}</p>;

  return (
    <section>
      <h1>{t('asset.tools.titel')}</h1>
      {tools.length === 0 ? (
        <p>{t('asset.tools.leer')}</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>{t('asset.feld.name')}</th>
              <th>{t('asset.feld.status')}</th>
              <th>{t('asset.feld.herkunft')}</th>
              <th>{t('asset.geerbt.kritikalitaet')}</th>
              <th>{t('asset.geerbt.tier')}</th>
            </tr>
          </thead>
          <tbody>
            {tools.map((tool) => (
              <tr key={tool.id}>
                <td>
                  <Link to={pfad(`/tools/${tool.id}`)}>{tool.name}</Link>
                </td>
                <td>{t(`asset.status.${tool.status}` as never)}</td>
                <td>{t(`asset.herkunft.${tool.herkunft}` as never)}</td>
                <td>{tool.geerbt.kritikalitaet}</td>
                <td>{tool.geerbt.tier ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <form className="formular" onSubmit={anlegen}>
        <label htmlFor="tool-name">{t('asset.tools.neu')}</label>
        <input id="tool-name" required value={name} onChange={(e) => setName(e.target.value)} />
        <button type="submit">{t('asset.speichern')}</button>
      </form>
    </section>
  );
}
