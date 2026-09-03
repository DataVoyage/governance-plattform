import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type { Aufloesungsart, Bewertung, Lenkungsvorgang, ToolObjekt } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { fristlage } from '@/nutzen/fristen';
import {
  Abzeichen,
  Blatt,
  Feld,
  Gruppe,
  Hinweis,
  Karte,
  Knopf,
  Ladeschimmer,
  Leerzustand,
  Seitenkopf,
  ZeileKnopf,
  type Ton,
} from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

/**
 * Die drei Wege aus A.13.6 — gleichrangig, deshalb drei gleich aussehende
 * Knöpfe und keine Auswahlliste mit einem Vorgabewert. Eine Vorauswahl wäre
 * eine Empfehlung, und das Leitdokument gibt keine.
 */
const ARTEN: Aufloesungsart[] = ['anpassen', 'rahmen_erweitern', 'stilllegen'];

const STUFENTON: Record<number, Ton> = { 1: 'gelb', 2: 'rot', 3: 'rot' };

/** Ein offener Vorgang mit dem, was für seine Auflösung gebraucht wird. */
interface Auswahl {
  vorgang: Lenkungsvorgang;
  art: Aufloesungsart;
}

/**
 * Lenkungsvorgänge mit ihren drei Auflösungswegen (Leitdokument A.13.6).
 *
 * Jede Auflösung ist eine eigene, benannte Aktion — keine Interpretation eines
 * Freitextkommentars. „Rahmen erweitern" verlangt zusätzlich die neue
 * Bewertung; sie wird hier aus den Bewertungen der betroffenen Prozessobjekte
 * gewählt, statt als Kennung eingetippt. Eine UUID gehört nicht ins Sichtfeld.
 */
export function Lenkung() {
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const [vorgaenge, setVorgaenge] = useState<Lenkungsvorgang[] | null>(null);
  const [tools, setTools] = useState<ToolObjekt[]>([]);
  const [auswahl, setAuswahl] = useState<Auswahl | null>(null);
  const [bewertungen, setBewertungen] = useState<Bewertung[] | null>(null);
  const [kommentar, setKommentar] = useState('');
  const [fehler, setFehler] = useState<string | null>(null);

  const laden = useCallback(() => {
    if (token === null) return;
    Promise.all([api.lenkungsvorgaenge(token), api.tools(token)])
      .then(([offen, alle]) => {
        setVorgaenge(offen);
        setTools(alle);
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, t]);

  useEffect(laden, [laden]);

  const toolVon = (vorgang: Lenkungsvorgang) =>
    tools.find((eintrag) => eintrag.id === vorgang.tool_objekt_id);

  /**
   * Die Bewertungen der betroffenen Prozessobjekte, die **nach** der Eröffnung
   * entstanden sind. Ältere würden den erweiterten Rahmen nicht abbilden — der
   * Server weist sie ab, und was er abweist, bietet die Oberfläche nicht an.
   */
  async function oeffne(vorgang: Lenkungsvorgang, art: Aufloesungsart) {
    setAuswahl({ vorgang, art });
    setKommentar('');
    setFehler(null);
    setBewertungen(null);
    if (art !== 'rahmen_erweitern' || token === null) return;
    const tool = toolVon(vorgang);
    const listen = await Promise.all(
      (tool?.prozessobjekt_ids ?? []).map((id) => api.bewertungen(token, id).catch(() => [])),
    );
    setBewertungen(
      listen
        .flat()
        .filter((bewertung) => bewertung.bewertet_am > vorgang.erstellt_am)
        .sort((a, b) => b.bewertet_am.localeCompare(a.bewertet_am)),
    );
  }

  async function aufloesen(bewertungId: string | null) {
    if (token === null || auswahl === null) return;
    setFehler(null);
    try {
      await api.lenkungAufloesen(token, auswahl.vorgang.id, {
        art: auswahl.art,
        bewertung_id: bewertungId,
        kommentar,
      });
      setAuswahl(null);
      laden();
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  if (vorgaenge === null)
    return fehler !== null ? (
      <Hinweis art="fehler">{fehler}</Hinweis>
    ) : (
      <Ladeschimmer beschriftung={t('app.laden')} zeilen={4} />
    );

  return (
    <>
      <Seitenkopf titel={t('lenkung.titel')} untertitel={t('lenkung.hinweis')} />
      {/* Solange das Blatt offen ist, steht der Fehler dort — zweimal
          derselbe Satz auf einem Bildschirm liest sich wie zwei Fehler. */}
      {fehler !== null && auswahl === null && <Hinweis art="fehler">{fehler}</Hinweis>}

      {vorgaenge.length === 0 ? (
        <Leerzustand titel={t('lenkung.leer')} text={t('lenkung.leerHinweis')} />
      ) : (
        vorgaenge.map((vorgang) => {
          const tool = toolVon(vorgang);
          const lage = fristlage(vorgang.frist);
          return (
            <Karte
              key={vorgang.id}
              titel={tool?.name ?? t('lenkung.tool')}
              beischrift={vorgang.beschreibung || undefined}
              aktion={
                <Abzeichen
                  ton={STUFENTON[vorgang.eskalationsstufe] ?? 'rot'}
                  zeichen={vorgang.eskalationsstufe >= 3 ? '!' : undefined}
                >
                  <span data-testid={`stufe-${vorgang.id}`}>
                    {t('lenkung.stufeKurz')} {vorgang.eskalationsstufe}
                  </span>
                </Abzeichen>
              }
            >
              {vorgang.schicht2_verbot !== null && (
                <Hinweis art="fehler">
                  {t('lenkung.schicht2').replace(
                    '{verbot}',
                    t(`schicht2.${vorgang.schicht2_verbot}` as never),
                  )}
                </Hinweis>
              )}
              {vorgang.eskalationsstufe >= 3 && <Hinweis art="warnung">{t('lenkung.stufe3')}</Hinweis>}

              {/* Der Countdown steht groß und in Arbeitstagen — die Einheit,
                  in der die Frist gesetzt wurde. Wer rechnen muss, um zu
                  wissen, wie lange er noch hat, weiß es nicht. */}
              <div className="k-countdown" data-abgelaufen={lage.abgelaufen ? 'ja' : undefined}>
                <span className="zahl" data-testid={`frist-${vorgang.id}`}>
                  {lage.abgelaufen ? t('lenkung.abgelaufen') : lage.tage}
                </span>
                <span className="einheit">
                  {lage.abgelaufen
                    ? lage.tage === 0
                      ? t('lenkung.abgelaufenHeute')
                      : t('lenkung.abgelaufenSeit').replace('{tage}', String(lage.tage))
                    : lage.tage === 1
                      ? t('lenkung.arbeitstagRest')
                      : t('lenkung.arbeitstageRest')}
                </span>
                <span className="datum" data-testid={`fristdatum-${vorgang.id}`}>
                  {t('lenkung.frist')} {vorgang.frist.slice(0, 10)}
                </span>
              </div>

              {/* Ein Verweis, kein zweiter Name: die Überschrift nennt das
                  Tool bereits. Er steht abseits der drei Auflösungen, damit er
                  nicht wie eine vierte, gleichrangige Handlung aussieht. */}
              {tool !== undefined && (
                <p className="k-verweiszeile">
                  <Link to={pfad(`/tools/${tool.id}`)}>{t('lenkung.zumTool')}</Link>
                </p>
              )}

              {vorgang.rechte.aufloesen ? (
                <div className="k-knopfreihe">
                  {ARTEN.map((art) => (
                    <Knopf
                      key={art}
                      art="getoent"
                      onClick={() => oeffne(vorgang, art)}
                      data-testid={`${art}-${vorgang.id}`}
                    >
                      {t(`lenkung.art.${art}` as never)}
                    </Knopf>
                  ))}
                </div>
              ) : (
                <Hinweis art="information">{t('rechte.lenkung.nurLesen')}</Hinweis>
              )}
            </Karte>
          );
        })
      )}

      {auswahl !== null && (
        <Blatt
          titel={t(`lenkung.art.${auswahl.art}` as never)}
          beischrift={t(`lenkung.art.${auswahl.art}.hinweis` as never)}
          schliessen={() => setAuswahl(null)}
          fuss={
            auswahl.art === 'rahmen_erweitern' ? undefined : (
              <Knopf art="gefuellt" onClick={() => aufloesen(null)} data-testid="aufloesen">
                {t('lenkung.aufloesen')}
              </Knopf>
            )
          }
        >
          {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}
          <Feld beschriftung={t('lenkung.kommentar')} wert={kommentar} aendern={setKommentar} />

          {auswahl.art === 'rahmen_erweitern' &&
            (bewertungen === null ? (
              <Ladeschimmer beschriftung={t('app.laden')} zeilen={2} />
            ) : bewertungen.length === 0 ? (
              <Hinweis art="information">{t('lenkung.bewertungFehlt')}</Hinweis>
            ) : (
              <Gruppe etikett={t('lenkung.bewertung')} hinweis={t('lenkung.bewertungPflicht')}>
                {bewertungen.map((bewertung) => (
                  <ZeileKnopf
                    key={bewertung.id}
                    pruefkennung={`bewertung-${bewertung.id}`}
                    handeln={() => aufloesen(bewertung.id)}
                    haupt={`${t('bewertung.tier')} ${bewertung.tier}`}
                    zweitzeile={bewertung.bewertet_am.slice(0, 10)}
                  />
                ))}
              </Gruppe>
            ))}
        </Blatt>
      )}
    </>
  );
}
