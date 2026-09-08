import { useCallback, useEffect, useState } from 'react';

import { ApiFehler, api } from '@/api/client';
import type {
  Anforderungsklasse,
  Ausfallfolge,
  Klassenbewertung,
  Matrixfeld,
  Technologie,
  UrKompositionsfeld,
} from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import {
  Abzeichen,
  Auswahl,
  Blatt,
  Feld,
  Gruppe,
  Hinweis,
  Karte,
  Knopf,
  Ladeschimmer,
  SegmentierteSteuerung,
  Seitenkopf,
  Zeile,
  type Ton,
} from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

const BEWERTUNGEN: Klassenbewertung[] = ['erfuellt', 'kompensierbar', 'nicht_erfuellbar'];

const BEWERTUNG_TON: Record<Klassenbewertung, Ton> = {
  erfuellt: 'gruen',
  kompensierbar: 'gelb',
  nicht_erfuellbar: 'rot',
};

const BEWERTUNG_ZEICHEN: Record<Klassenbewertung, string> = {
  erfuellt: '✓',
  kompensierbar: '!',
  nicht_erfuellbar: '✕',
};

type Ansicht = 'klassen' | 'matrix' | 'komposition';

/** Die beiden Achsen der UR-Kompositionstabelle, in der Ordnung aus A.8.4. */
const AUSFALLFOLGEN: Ausfallfolge[] = ['keine', 'gering', 'spuerbar', 'kritisch'];
const REICHWEITEN = ['persoenlich', 'team', 'bereich', 'unternehmen', 'extern'];
const UR_STUFEN = [0, 1, 2, 3];

/** Kein Farbverlauf, sondern die Aussage: ab 3 traegt die Stufe allein nichts mehr bei. */
const UR_TON: Record<number, Ton> = { 0: 'neutral', 1: 'gruen', 2: 'gelb', 3: 'rot' };

/**
 * Anforderungsklassen, Technologiematrix und UR-Komposition (A.8.4, A.9, Teil C.1).
 *
 * Drei Ansichten auf gepflegte Bewertungsgrundlagen: das Nachschlagewerk der
 * zehn Klassen mit Name, Zweck und Auslöserbedingung — die Matrix, die sagt,
 * welche Technologie welche Klasse tragen kann — und die Tabelle, aus der sich
 * das unternehmerische Risiko aus Ausfallfolge und Reichweite ergibt.
 *
 * Alle drei sind Tabellen, und zwar bewusst: sie haben zwei Achsen, und ein
 * Vergleich über zwei Achsen ist genau das, wofür es Tabellen gibt. Jede Zelle
 * trägt Symbol und Wort, nie Farbe allein.
 *
 * Die Komposition steht hier und nicht bei der Bewertung, weil sie dasselbe ist
 * wie die Matrix: eine fachliche Setzung, die ohne Auslieferung korrigierbar
 * sein muss (E-66, analog E-42).
 */
export function Klassen() {
  const { t } = useSprache();
  const { token, profil } = useSitzung();
  const [ansicht, setAnsicht] = useState<Ansicht>('klassen');
  const [klassen, setKlassen] = useState<Anforderungsklasse[] | null>(null);
  const [technologien, setTechnologien] = useState<Technologie[]>([]);
  const [matrix, setMatrix] = useState<Matrixfeld[]>([]);
  const [komposition, setKomposition] = useState<UrKompositionsfeld[]>([]);
  const [offen, setOffen] = useState<Matrixfeld | null>(null);
  const [offenesFeld, setOffenesFeld] = useState<UrKompositionsfeld | null>(null);
  const [bewertung, setBewertung] = useState<Klassenbewertung>('erfuellt');
  const [stufe, setStufe] = useState(0);
  const [begruendung, setBegruendung] = useState('');
  const [fehler, setFehler] = useState<string | null>(null);

  const laden = useCallback(() => {
    if (token === null) return;
    Promise.all([
      api.anforderungsklassen(token),
      api.technologien(token),
      api.technologiematrix(token),
      api.urKomposition(token),
    ])
      .then(([alle, techs, felder, ur]) => {
        setKlassen(alle);
        setTechnologien(techs);
        setMatrix(felder);
        setKomposition(ur);
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, t]);

  useEffect(laden, [laden]);

  const darfPflegen =
    profil?.rollen.some((zuweisung) => zuweisung.rolle === 'governance') ?? false;

  const feld = (technologie: string, klasse: string) =>
    matrix.find((e) => e.technologie === technologie && e.k_klasse === klasse);

  const urFeld = (ausfallfolge: string, reichweite: string) =>
    komposition.find((e) => e.ausfallfolge === ausfallfolge && e.reichweite === reichweite);

  async function sichereKomposition() {
    if (token === null || offenesFeld === null) return;
    setFehler(null);
    try {
      const neu = await api.urKompositionsfeldSetzen(
        token,
        offenesFeld.ausfallfolge,
        offenesFeld.reichweite,
        { stufe, begruendung },
      );
      setKomposition((bisher) =>
        bisher.map((e) =>
          e.ausfallfolge === neu.ausfallfolge && e.reichweite === neu.reichweite ? neu : e,
        ),
      );
      setOffenesFeld(null);
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  async function sichern() {
    if (token === null || offen === null) return;
    setFehler(null);
    try {
      const neu = await api.matrixfeldSetzen(token, offen.technologie, offen.k_klasse, {
        bewertung,
        begruendung,
      });
      setMatrix((bisher) =>
        bisher.map((e) =>
          e.technologie === neu.technologie && e.k_klasse === neu.k_klasse ? neu : e,
        ),
      );
      setOffen(null);
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  if (klassen === null)
    return fehler !== null ? (
      <Hinweis art="fehler">{fehler}</Hinweis>
    ) : (
      <Ladeschimmer beschriftung={t('app.laden')} zeilen={6} />
    );

  return (
    <>
      <Seitenkopf
        titel={t('klassen.titel')}
        untertitel={t('klassen.hinweis')}
        aktionen={
          <SegmentierteSteuerung<Ansicht>
            beschriftung={t('klassen.ansicht')}
            wert={ansicht}
            aendern={setAnsicht}
            optionen={[
              { wert: 'klassen', text: t('klassen.ansicht.klassen') },
              { wert: 'matrix', text: t('klassen.ansicht.matrix') },
              { wert: 'komposition', text: t('klassen.ansicht.komposition') },
            ]}
          />
        }
      />
      {/* Solange das Blatt offen ist, steht der Fehler dort — zweimal
          derselbe Satz auf einem Bildschirm liest sich wie zwei Fehler. */}
      {fehler !== null && offen === null && <Hinweis art="fehler">{fehler}</Hinweis>}

      {ansicht === 'klassen' && (
        <Karte titel={t('klassen.katalog')} beischrift={t('klassen.katalogHinweis')}>
          <Gruppe>
            {klassen.map((klasse) => (
              <Zeile
                key={klasse.schluessel}
                pruefkennung={`klasse-${klasse.schluessel}`}
                haupt={`${klasse.schluessel} — ${klasse.name}`}
                zweitzeile={
                  <>
                    <span className="satzzeile">{klasse.zweck}</span>
                    <span className="satzzeile">
                      {t('klassen.ausloeser')}: {klasse.ausloeser}
                    </span>
                  </>
                }
              />
            ))}
          </Gruppe>
        </Karte>
      )}

      {ansicht === 'matrix' && (
        <Karte titel={t('klassen.matrix')} beischrift={t('klassen.matrixHinweis')}>
          {!darfPflegen && <Hinweis art="information">{t('klassen.nurLesen')}</Hinweis>}
          <div className="k-matrix">
            <table>
              <caption className="k-nur-vorlesen">{t('klassen.matrix')}</caption>
              <thead>
                <tr>
                  <th scope="col">{t('klassen.spalte.klasse')}</th>
                  {technologien.map((technologie) => (
                    <th scope="col" key={technologie.schluessel}>
                      {technologie.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {klassen.map((klasse) => (
                  <tr key={klasse.schluessel}>
                    <th scope="row">
                      <span className="kuerzel">{klasse.schluessel}</span>
                      <span className="name">{klasse.name}</span>
                    </th>
                    {technologien.map((technologie) => {
                      const eintrag = feld(technologie.schluessel, klasse.schluessel);
                      if (eintrag === undefined) return <td key={technologie.schluessel}>—</td>;
                      const abzeichen = (
                        <Abzeichen
                          ton={BEWERTUNG_TON[eintrag.bewertung]}
                          zeichen={BEWERTUNG_ZEICHEN[eintrag.bewertung]}
                        >
                          {t(`klassen.bewertung.${eintrag.bewertung}` as never)}
                        </Abzeichen>
                      );
                      return (
                        <td
                          key={technologie.schluessel}
                          data-testid={`matrix-${technologie.schluessel}-${klasse.schluessel}`}
                        >
                          {darfPflegen ? (
                            <button
                              type="button"
                              className="zelle"
                              title={eintrag.begruendung}
                              onClick={() => {
                                setOffen(eintrag);
                                setBewertung(eintrag.bewertung);
                                setBegruendung(eintrag.begruendung);
                                setFehler(null);
                              }}
                            >
                              {abzeichen}
                            </button>
                          ) : (
                            <span className="zelle" title={eintrag.begruendung}>
                              {abzeichen}
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Karte>
      )}

      {ansicht === 'komposition' && (
        <Karte titel={t('klassen.komposition')} beischrift={t('klassen.kompositionHinweis')}>
          {!darfPflegen && <Hinweis art="information">{t('klassen.nurLesen')}</Hinweis>}
          {/* Die Kappung gehört als Satz dazu: Ohne sie liest man die Zeile
              „kritisch" als Weg auf Tier 3, und genau das ist sie nicht. */}
          <Hinweis art="information">{t('klassen.kompositionKappung')}</Hinweis>
          <div className="k-matrix">
            <table>
              <caption className="k-nur-vorlesen">{t('klassen.komposition')}</caption>
              <thead>
                <tr>
                  <th scope="col">{t('klassen.spalte.ausfallfolge')}</th>
                  {REICHWEITEN.map((reichweite) => (
                    <th scope="col" key={reichweite}>
                      {t(`reichweite.${reichweite}` as never)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {AUSFALLFOLGEN.map((ausfallfolge) => (
                  <tr key={ausfallfolge}>
                    <th scope="row">
                      <span className="name">{t(`ausfallfolge.${ausfallfolge}` as never)}</span>
                    </th>
                    {REICHWEITEN.map((reichweite) => {
                      const eintrag = urFeld(ausfallfolge, reichweite);
                      if (eintrag === undefined) return <td key={reichweite}>—</td>;
                      const abzeichen = (
                        <Abzeichen ton={UR_TON[eintrag.stufe] ?? 'neutral'}>
                          {`${t('klassen.urStufe')} ${eintrag.stufe}`}
                        </Abzeichen>
                      );
                      return (
                        <td
                          key={reichweite}
                          data-testid={`komposition-${ausfallfolge}-${reichweite}`}
                        >
                          {darfPflegen ? (
                            <button
                              type="button"
                              className="zelle"
                              title={eintrag.begruendung}
                              onClick={() => {
                                setOffenesFeld(eintrag);
                                setStufe(eintrag.stufe);
                                setBegruendung(eintrag.begruendung);
                                setFehler(null);
                              }}
                            >
                              {abzeichen}
                            </button>
                          ) : (
                            <span className="zelle" title={eintrag.begruendung}>
                              {abzeichen}
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Karte>
      )}

      {offenesFeld !== null && (
        <Blatt
          titel={`${t(`ausfallfolge.${offenesFeld.ausfallfolge}` as never)} — ${t(
            `reichweite.${offenesFeld.reichweite}` as never,
          )}`}
          beischrift={t('klassen.kompositionFeldHinweis')}
          schliessen={() => setOffenesFeld(null)}
          fuss={
            <Knopf
              art="gefuellt"
              disabled={begruendung.trim() === ''}
              onClick={sichereKomposition}
              data-testid="komposition-sichern"
            >
              {t('klassen.feld.sichern')}
            </Knopf>
          }
        >
          {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}
          <Auswahl
            beschriftung={t('klassen.urStufe')}
            wert={String(stufe)}
            aendern={(wert) => setStufe(Number(wert))}
            optionen={UR_STUFEN.map((wert) => ({ wert: String(wert), text: String(wert) }))}
          />
          <Feld
            beschriftung={t('klassen.feld.begruendung')}
            wert={begruendung}
            aendern={setBegruendung}
            mehrzeilig
            pflicht
            hilfe={t('klassen.kompositionBegruendungHilfe')}
          />
        </Blatt>
      )}

      {offen !== null && (
        <Blatt
          titel={`${offen.k_klasse} — ${
            technologien.find((tech) => tech.schluessel === offen.technologie)?.name ??
            offen.technologie
          }`}
          beischrift={t('klassen.feld.hinweis')}
          schliessen={() => setOffen(null)}
          fuss={
            <Knopf
              art="gefuellt"
              disabled={begruendung.trim() === ''}
              onClick={sichern}
              data-testid="matrix-sichern"
            >
              {t('klassen.feld.sichern')}
            </Knopf>
          }
        >
          {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}
          <Auswahl
            beschriftung={t('klassen.feld.bewertung')}
            wert={bewertung}
            aendern={(wert) => setBewertung(wert as Klassenbewertung)}
            optionen={BEWERTUNGEN.map((wert) => ({
              wert,
              text: t(`klassen.bewertung.${wert}` as never),
            }))}
          />
          <Feld
            beschriftung={t('klassen.feld.begruendung')}
            wert={begruendung}
            aendern={setBegruendung}
            mehrzeilig
            pflicht
            hilfe={t('klassen.feld.begruendungHilfe')}
          />
        </Blatt>
      )}
    </>
  );
}
