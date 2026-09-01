import { useState, type FormEvent } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';

import { Kopfzeile } from '@/komponenten/Layout';
import { useSprache } from '@/i18n/SprachKontext';
import { useSitzung } from '@/zustand/Sitzung';

/**
 * Anmeldemaske.
 *
 * Produktiv leitet diese Seite auf die zentrale Unternehmensidentitaet weiter;
 * im Entwicklungsmodus stellt das Backend ein lokales Token aus, damit die
 * Oberflaeche ohne Identitaetsanbindung entwickelbar und testbar bleibt.
 */
export function Anmeldung() {
  const { t, pfad } = useSprache();
  const { token, anmelden } = useSitzung();
  const navigiere = useNavigate();
  const [kennung, setKennung] = useState('');
  const [name, setName] = useState('');
  const [fehler, setFehler] = useState<string | null>(null);

  if (token !== null) return <Navigate to={pfad('/prozesse')} replace />;

  async function absenden(ereignis: FormEvent) {
    ereignis.preventDefault();
    setFehler(null);
    try {
      await anmelden(kennung, name || kennung);
      navigiere(pfad('/prozesse'));
    } catch {
      setFehler(t('app.fehler'));
    }
  }

  return (
    <div className="huelle">
      <Kopfzeile />
      <main>
        <h1>{t('anmeldung.titel')}</h1>
        <p>{t('anmeldung.hinweis')}</p>
        <form onSubmit={absenden} className="formular">
          <fieldset>
            <legend>{t('anmeldung.entwicklungsmodus')}</legend>
            <label htmlFor="kennung">{t('anmeldung.kennung')}</label>
            <input
              id="kennung"
              required
              value={kennung}
              onChange={(e) => setKennung(e.target.value)}
            />
            <label htmlFor="name">{t('anmeldung.name')}</label>
            <input id="name" value={name} onChange={(e) => setName(e.target.value)} />
            <button type="submit">{t('anmeldung.absenden')}</button>
          </fieldset>
        </form>
        {fehler !== null && <p role="alert">{fehler}</p>}
      </main>
    </div>
  );
}
