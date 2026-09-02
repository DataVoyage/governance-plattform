import { useCallback, useEffect, useState } from 'react';

import { ApiFehler, api } from '@/api/client';
import type { Anforderungsklasse, Klassenbewertung, Matrixfeld, Technologie } from '@/api/typen';
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

type Ansicht = 'klassen' | 'matrix';

/**
 * Anforderungsklassen und Technologiematrix (Leitdokument A.9, Teil C.1).
 *
 * Zwei Ansichten auf denselben Gegenstand: das Nachschlagewerk der zehn
 * Klassen mit Name, Zweck und Auslöserbedingung — und die Matrix, die sagt,
 * welche Technologie welche Klasse tragen kann.
 *
 * Die Matrix ist eine Tabelle, und zwar bewusst: sie hat zwei Achsen, und ein
 * Vergleich über zwei Achsen ist genau das, wofür es Tabellen gibt. Jede Zelle
 * trägt Symbol und Wort, nie Farbe allein.
 */
export function Klassen() {
  const { t } = useSprache();
  const { token, profil } = useSitzung();
  const [ansicht, setAnsicht] = useState<Ansicht>('klassen');
  const [klassen, setKlassen] = useState<Anforderungsklasse[] | null>(null);
  const [technologien, setTechnologien] = useState<Technologie[]>([]);
  const [matrix, setMatrix] = useState<Matrixfeld[]>([]);
  const [offen, setOffen] = useState<Matrixfeld | null>(null);
  const [bewertung, setBewertung] = useState<Klassenbewertung>('erfuellt');
  const [begruendung, setBegruendung] = useState('');
  const [fehler, setFehler] = useState<string | null>(null);

  const laden = useCallback(() => {
    if (token === null) return;
    Promise.all([
      api.anforderungsklassen(token),
      api.technologien(token),
      api.technologiematrix(token),
    ])
      .then(([alle, techs, felder]) => {
        setKlassen(alle);
        setTechnologien(techs);
        setMatrix(felder);
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, t]);

  useEffect(laden, [laden]);

  const darfPflegen =
    profil?.rollen.some((zuweisung) => zuweisung.rolle === 'governance') ?? false;

  const feld = (technologie: string, klasse: string) =>
    matrix.find((e) => e.technologie === technologie && e.k_klasse === klasse);

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
            ]}
          />
        }
      />
      {/* Solange das Blatt offen ist, steht der Fehler dort — zweimal
          derselbe Satz auf einem Bildschirm liest sich wie zwei Fehler. */}
      {fehler !== null && offen === null && <Hinweis art="fehler">{fehler}</Hinweis>}

      {ansicht === 'klassen' ? (
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
      ) : (
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
