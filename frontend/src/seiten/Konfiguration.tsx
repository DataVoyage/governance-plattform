import { useCallback, useEffect, useState } from 'react';

import { ApiFehler, api } from '@/api/client';
import type { Einstellung } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { Feld, Gruppe, Hinweis, Karte, Knopf, Ladeschimmer, Seitenkopf, Zeile } from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

/** Die Gruppen, in denen die Einstellungen auf dem Bildschirm stehen. */
const GRUPPEN: { etikett: string; praefix: string[] }[] = [
  { etikett: 'konfiguration.gruppe.lenkung', praefix: ['lenkung_frist', 'lenkung_nachfrist'] },
  { etikett: 'konfiguration.gruppe.fristen', praefix: ['selbstverpflichtung_', 'bewertung_'] },
  { etikett: 'konfiguration.gruppe.schwellen', praefix: ['asset_'] },
];

/**
 * Governance-Einstellungen (Architektur 6.6).
 *
 * Fristen, Vorlaufzeiten und Schwellen sind Governance-Inhalt, keine
 * Betriebsparameter: sie gehören nicht in eine Umgebungsvariable, sondern in
 * die Hand der Governance-Rolle. Jede Änderung läuft über den Nachweis wie
 * jede andere schreibende Aktion.
 *
 * **Sie wirkt auf neue Vorgänge, nicht rückwirkend.** Eine Frist wird beim
 * Eröffnen gerechnet und gespeichert; ein laufender Vorgang behält deshalb
 * seine. Das ist Absicht — eine Frist, die sich unter dem Betroffenen ändert,
 * wäre keine.
 */
export function Konfiguration() {
  const { t } = useSprache();
  const { token, profil } = useSitzung();
  const [einstellungen, setEinstellungen] = useState<Einstellung[] | null>(null);
  const [entwuerfe, setEntwuerfe] = useState<Record<string, string>>({});
  const [gesichert, setGesichert] = useState<string | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);

  const laden = useCallback(() => {
    if (token === null) return;
    api
      .konfiguration(token)
      .then((liste) => {
        setEinstellungen(liste);
        setEntwuerfe(Object.fromEntries(liste.map((e) => [e.schluessel, e.wert])));
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, t]);

  useEffect(laden, [laden]);

  async function sichern(schluessel: string) {
    if (token === null) return;
    setFehler(null);
    setGesichert(null);
    try {
      const neu = await api.konfigurationSetzen(token, schluessel, entwuerfe[schluessel] ?? '');
      setEinstellungen((bisher) =>
        (bisher ?? []).map((e) => (e.schluessel === schluessel ? neu : e)),
      );
      setGesichert(schluessel);
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  if (einstellungen === null)
    return fehler !== null ? (
      <Hinweis art="fehler">{fehler}</Hinweis>
    ) : (
      <Ladeschimmer beschriftung={t('app.laden')} zeilen={5} />
    );

  // Die Route ist ohnehin nur für die Governance-Rolle sichtbar; der Server
  // prüft zusätzlich. Hier steht der Grund, damit niemand rät, warum die
  // Knöpfe fehlen (Architektur 10.2).
  const darfAendern = profil?.rollen.some((zuweisung) => zuweisung.rolle === 'governance') ?? false;

  return (
    <>
      <Seitenkopf titel={t('konfiguration.titel')} untertitel={t('konfiguration.hinweis')} />
      {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}
      {!darfAendern && <Hinweis art="information">{t('konfiguration.nurLesen')}</Hinweis>}
      <Hinweis art="information">{t('konfiguration.nichtRueckwirkend')}</Hinweis>

      <Karte>
        {GRUPPEN.map(({ etikett, praefix }) => {
          const passend = einstellungen.filter((eintrag) =>
            praefix.some((anfang) => eintrag.schluessel.startsWith(anfang)),
          );
          if (passend.length === 0) return null;
          return (
            <Gruppe key={etikett} etikett={t(etikett as never)}>
              {passend.map((eintrag) => (
                <Zeile
                  key={eintrag.schluessel}
                  pruefkennung={`einstellung-${eintrag.schluessel}`}
                  haupt={t(`konfiguration.${eintrag.schluessel}` as never)}
                  zweitzeile={eintrag.beschreibung}
                  wert={
                    <>
                      <Feld
                        beschriftung={t(`konfiguration.${eintrag.schluessel}` as never)}
                        beschriftungVerborgen
                        wert={entwuerfe[eintrag.schluessel] ?? ''}
                        aendern={(wert) =>
                          setEntwuerfe((bisher) => ({ ...bisher, [eintrag.schluessel]: wert }))
                        }
                        disabled={!darfAendern}
                      />
                      <Knopf
                        art="getoent"
                        disabled={!darfAendern || entwuerfe[eintrag.schluessel] === eintrag.wert}
                        onClick={() => sichern(eintrag.schluessel)}
                        data-testid={`sichern-${eintrag.schluessel}`}
                      >
                        {gesichert === eintrag.schluessel &&
                        entwuerfe[eintrag.schluessel] === eintrag.wert
                          ? t('konfiguration.gesichert')
                          : t('konfiguration.sichern')}
                      </Knopf>
                    </>
                  }
                />
              ))}
            </Gruppe>
          );
        })}
      </Karte>
    </>
  );
}
