import { useState, type FormEvent } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';

import { useSprache } from '@/i18n/SprachKontext';
import { Feld, Hinweis, Knopf } from '@/ui';
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
    <div className="anmeldeflaeche">
      <form className="anmeldekarte" onSubmit={absenden}>
        <span className="zeichen" aria-hidden="true">
          G
        </span>
        <h1>{t('anmeldung.titel')}</h1>
        <p className="untertitel">{t('anmeldung.hinweis')}</p>

        <div className="entwicklungsmodus">
          <span className="etikett">{t('anmeldung.entwicklungsmodus')}</span>
          <Feld beschriftung={t('anmeldung.kennung')} wert={kennung} aendern={setKennung} pflicht />
          <Feld beschriftung={t('anmeldung.name')} wert={name} aendern={setName} />
          <Knopf type="submit" art="gefuellt" gross breit>
            {t('anmeldung.absenden')}
          </Knopf>
        </div>

        {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}
      </form>
    </div>
  );
}
