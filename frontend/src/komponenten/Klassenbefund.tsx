import { useCallback, useEffect, useState } from 'react';

import { ApiFehler, api } from '@/api/client';
import type { Anforderungsklasse, Befund, Befundart, Toolbefund } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import {
  Abzeichen,
  Blatt,
  Feld,
  Gruppe,
  Hinweis,
  Karte,
  Knopf,
  Ladeschimmer,
  Zeile,
  type Ton,
} from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

const BEFUND_TON: Record<Befundart, Ton> = {
  erfuellt: 'gruen',
  kompensiert: 'gruen',
  kompensation_fehlt: 'gelb',
  ausschluss: 'rot',
  ungeprueft: 'gelb',
};

const BEFUND_ZEICHEN: Record<Befundart, string | undefined> = {
  erfuellt: '✓',
  kompensiert: '✓',
  kompensation_fehlt: '!',
  ausschluss: '✕',
  ungeprueft: '?',
};

/**
 * Der Abgleich ausgelöste Klasse gegen Technologie (Leitdokument A.9.3).
 *
 * Die Karte beantwortet die Frage, auf die das Bewertungsmodell zuläuft: kann
 * die eingesetzte Technologie tragen, was dieser Prozess auslöst? Jede Zeile
 * nennt Klasse, Befund und den nötigen Schritt — „K5 ❌" allein verlagert die
 * Übersetzungsarbeit auf den Leser.
 *
 * `stand` ist der Änderungszähler der Seite: steigt er, lädt die Karte neu.
 */
export function Klassenbefund({ toolId, stand = 0 }: { toolId: string; stand?: number }) {
  const { t } = useSprache();
  const { token } = useSitzung();
  const [befund, setBefund] = useState<Toolbefund | null>(null);
  const [namen, setNamen] = useState<Record<string, string>>({});
  const [offen, setOffen] = useState<Befund | null>(null);
  const [massnahme, setMassnahme] = useState('');
  const [fehler, setFehler] = useState<string | null>(null);

  const laden = useCallback(() => {
    if (token === null) return;
    // Die Namen kommen aus derselben Quelle wie die Klassenseite; eine zweite
    // Liste in der Übersetzungsdatei würde von ihr abdriften.
    Promise.all([api.toolKlassenbefund(token, toolId), api.anforderungsklassen(token)])
      .then(([inhalt, klassen]: [Toolbefund, Anforderungsklasse[]]) => {
        setBefund(inhalt);
        setNamen(Object.fromEntries(klassen.map((k) => [k.schluessel, k.name])));
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, toolId, t]);

  useEffect(laden, [laden, stand]);

  async function kompensieren() {
    if (token === null || offen === null) return;
    setFehler(null);
    try {
      await api.kompensationSetzen(token, toolId, offen.k_klasse, massnahme);
      setOffen(null);
      laden();
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  if (fehler !== null && befund === null) return <Hinweis art="fehler">{fehler}</Hinweis>;
  if (befund === null)
    return (
      <Karte titel={t('klassen.befund.titel')}>
        <Ladeschimmer beschriftung={t('app.laden')} zeilen={3} />
      </Karte>
    );

  return (
    <>
      <Karte
        titel={t('klassen.befund.titel')}
        beischrift={t('klassen.befund.hinweis')}
        aktion={
          befund.k_klassen.length === 0 ? undefined : befund.ausschluss ? (
            <Abzeichen ton="rot" zeichen="✕">
              {t('klassen.befund.ausschluss')}
            </Abzeichen>
          ) : befund.offen > 0 ? (
            <Abzeichen ton="gelb" zeichen="!">
              {(befund.offen === 1
                ? t('klassen.befund.offen.eine')
                : t('klassen.befund.offen')
              ).replace('{anzahl}', String(befund.offen))}
            </Abzeichen>
          ) : (
            <Abzeichen ton="gruen" zeichen="✓">
              {t('klassen.befund.getragen')}
            </Abzeichen>
          )
        }
      >
        {/* Solange das Blatt offen ist, steht der Fehler dort. */}
        {fehler !== null && offen === null && <Hinweis art="fehler">{fehler}</Hinweis>}
        {befund.k_klassen.length === 0 ? (
          <p className="leerhinweis">{t('klassen.befund.leer')}</p>
        ) : (
          <Gruppe>
            {befund.befunde.map((eintrag) => (
              <Zeile
                key={eintrag.k_klasse}
                pruefkennung={`befund-${eintrag.k_klasse}`}
                haupt={`${eintrag.k_klasse} — ${namen[eintrag.k_klasse] ?? ''}`}
                zweitzeile={
                  <>
                    <span className="satzzeile">
                      {t(`klassen.schritt.${eintrag.art}` as never)}
                    </span>
                    {/* Bei einer erfüllten Klasse sagt die Begründung dasselbe
                        wie der Schritt — viermal derselbe Satz untereinander ist
                        Lärm. Sie steht dort, wo die Technologie etwas begrenzt. */}
                    {eintrag.begruendung !== '' && eintrag.art !== 'erfuellt' && (
                      <span className="satzzeile">{eintrag.begruendung}</span>
                    )}
                    {eintrag.massnahme !== '' && (
                      <span className="satzzeile">
                        {t('klassen.massnahme')}: {eintrag.massnahme}
                      </span>
                    )}
                  </>
                }
                wert={
                  <>
                    <Abzeichen ton={BEFUND_TON[eintrag.art]} zeichen={BEFUND_ZEICHEN[eintrag.art]}>
                      {t(`klassen.art.${eintrag.art}` as never)}
                    </Abzeichen>
                    {(eintrag.art === 'kompensation_fehlt' || eintrag.art === 'kompensiert') && (
                      <Knopf
                        onClick={() => {
                          setOffen(eintrag);
                          setMassnahme(eintrag.massnahme);
                          setFehler(null);
                        }}
                        data-testid={`kompensieren-${eintrag.k_klasse}`}
                      >
                        {eintrag.massnahme === ''
                          ? t('klassen.kompensieren')
                          : t('klassen.kompensationAendern')}
                      </Knopf>
                    )}
                  </>
                }
              />
            ))}
          </Gruppe>
        )}
      </Karte>

      {offen !== null && (
        <Blatt
          titel={`${offen.k_klasse} — ${namen[offen.k_klasse] ?? ''}`}
          beischrift={t('klassen.kompensation.hinweis')}
          schliessen={() => setOffen(null)}
          fuss={
            <Knopf
              art="gefuellt"
              disabled={massnahme.trim() === ''}
              onClick={kompensieren}
              data-testid="kompensation-sichern"
            >
              {t('klassen.kompensation.sichern')}
            </Knopf>
          }
        >
          {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}
          <Hinweis art="information">{offen.begruendung}</Hinweis>
          <Feld
            beschriftung={t('klassen.kompensation.feld')}
            wert={massnahme}
            aendern={setMassnahme}
            mehrzeilig
            pflicht
            hilfe={t('klassen.kompensation.feldHilfe')}
          />
        </Blatt>
      )}
    </>
  );
}
