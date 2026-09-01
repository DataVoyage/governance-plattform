import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type { BewertungsModus, Ergebnis, Frage } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { useSitzung } from '@/zustand/Sitzung';

/**
 * Geführter Wizard über den Entscheidungsbaum (Architektur 8.2).
 *
 * Ein Schritt pro Bildschirm, zwei Antwortoptionen als Buttons — keine Tabelle
 * mit sechs gleichzeitig auszufüllenden Werten. Die Reihenfolge der Blöcke
 * kommt vom Server; diese Komponente kennt sie nicht und kann sie deshalb auch
 * nicht versehentlich verschieben.
 *
 * Der Zwischenstand wird nicht angezeigt: das Ergebnis erscheint erst, wenn
 * der Durchlauf abgeschlossen ist.
 */
export function BewertungsWizard() {
  const { id } = useParams();
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const navigiere = useNavigate();

  const [modus, setModus] = useState<BewertungsModus | null>(null);
  const [antworten, setAntworten] = useState<Record<string, boolean>>({});
  const [frage, setFrage] = useState<Frage | null>(null);
  const [ergebnis, setErgebnis] = useState<Ergebnis | null>(null);
  const [verboten, setVerboten] = useState(false);
  const [fehler, setFehler] = useState<string | null>(null);

  const schritt = useCallback(
    async (gewaehlterModus: BewertungsModus, bisher: Record<string, boolean>) => {
      if (token === null || id === undefined) return;
      try {
        const stand = await api.wizardSchritt(token, id, gewaehlterModus, bisher);
        setFrage(stand.naechste_frage);
        setVerboten(stand.verboten);
        setErgebnis(stand.vorschau);
      } catch (ausnahme) {
        setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
      }
    },
    [token, id, t],
  );

  useEffect(() => {
    if (modus !== null) void schritt(modus, antworten);
  }, [modus, antworten, schritt]);

  function beantworte(wert: boolean) {
    if (frage === null) return;
    setAntworten((bisher) => ({ ...bisher, [frage.id]: wert }));
  }

  function vonVorn() {
    setAntworten({});
    setFrage(null);
    setErgebnis(null);
    setVerboten(false);
    setModus(null);
  }

  async function speichern() {
    if (token === null || id === undefined || modus === null) return;
    try {
      await api.bewertungAbschliessen(token, id, modus, antworten);
      navigiere(pfad(`/prozesse/${id}`));
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  if (fehler !== null) return <p role="alert">{fehler}</p>;

  if (modus === null) {
    return (
      <section>
        <h1>{t('bewertung.titel')}</h1>
        <p>{t('bewertung.modus.frage')}</p>
        <p>{t('bewertung.modus.hinweis')}</p>
        <button type="button" onClick={() => setModus('schnell')}>
          {t('bewertung.modus.schnell')}
        </button>{' '}
        <button type="button" onClick={() => setModus('vollstaendig')}>
          {t('bewertung.modus.vollstaendig')}
        </button>
        <p>
          <Link to={pfad(`/prozesse/${id}`)}>{t('app.zurueck')}</Link>
        </p>
      </section>
    );
  }

  if (verboten) {
    return (
      <section>
        <h1>{t('bewertung.verboten.titel')}</h1>
        <p role="alert">{t('bewertung.verboten.text')}</p>
        <button type="button" onClick={speichern}>
          {t('bewertung.verboten.alarm')}
        </button>{' '}
        <button type="button" onClick={vonVorn}>
          {t('bewertung.zurueckZurAuswahl')}
        </button>
      </section>
    );
  }

  if (ergebnis !== null) {
    return (
      <section>
        <h1>{t('bewertung.ergebnis')}</h1>
        <dl className="felder">
          <dt>{t('bewertung.tier')}</dt>
          <dd data-testid="tier">{ergebnis.tier}</dd>
          <dt>{t('bewertung.profil')}</dt>
          <dd data-testid="profil">
            {Object.entries(ergebnis.profil)
              .map(([block, stufe]) => `${block.toUpperCase()}${stufe}`)
              .join('-')}
          </dd>
        </dl>
        <h2>{t('bewertung.kKlassen')}</h2>
        {ergebnis.ausgeloeste_k_klassen.length === 0 ? (
          <p>{t('bewertung.keineKKlassen')}</p>
        ) : (
          <ul data-testid="k-klassen">
            {ergebnis.ausgeloeste_k_klassen.map((klasse) => (
              <li key={klasse}>{klasse}</li>
            ))}
          </ul>
        )}
        <button type="button" onClick={speichern}>
          {t('bewertung.speichern')}
        </button>{' '}
        <button type="button" onClick={vonVorn}>
          {t('bewertung.zurueckZurAuswahl')}
        </button>
      </section>
    );
  }

  if (frage === null) return <p>{t('app.laden')}</p>;

  return (
    <section>
      <h1>{t('bewertung.titel')}</h1>
      <p className="fortschritt">
        {t('bewertung.schritt')} {frage.nummer} {t('bewertung.von')} {frage.anzahl_bloecke} —{' '}
        {frage.block_titel}
      </p>
      <p data-testid="frage" data-frage-id={frage.id}>
        {frage.text}
      </p>
      <button type="button" onClick={() => beantworte(true)}>
        {t('bewertung.ja')}
      </button>{' '}
      <button type="button" onClick={() => beantworte(false)}>
        {t('bewertung.nein')}
      </button>
      <p>
        <button type="button" onClick={vonVorn}>
          {t('bewertung.zurueckZurAuswahl')}
        </button>
      </p>
    </section>
  );
}
