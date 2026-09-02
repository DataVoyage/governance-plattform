import { useEffect, useState } from 'react';

import { api } from '@/api/client';
import type { Rahmen, RahmenElement } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { Abzeichen, Hinweis, Karte, Ladeschimmer } from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

/**
 * Wo die Werte eines Elements Schlüssel sind, steht hier ihr Präfix — sonst
 * `null`, weil es Namen sind, die niemand übersetzt.
 */
const WERTSCHLUESSEL: Record<string, string | null> = {
  datenobjekte: null,
  datenkategorie: 'kategorie',
  reichweite: 'reichweite',
  externe_ziele: null,
  zugriffsart: 'zugriffsart',
  ausfuehrungsart: 'tool.lauftyp',
  ausfuehrungsidentitaet: 'rahmen.identitaet',
};

/**
 * Elemente, deren Abweichung keine Schlüssel nennt, sondern Objektnamen: beim
 * Zugriff steht dort nicht „lesen_schreiben", sondern das Datenobjekt, in das
 * geschrieben wird — die Angabe, mit der jemand etwas anfangen kann.
 */
const ABWEICHUNG_IST_NAME = new Set(['datenobjekte', 'externe_ziele', 'zugriffsart']);

/**
 * Der Erlaubnisrahmen eines Tool-Objekts (Leitdokument A.13.2).
 *
 * Die Karte stellt neben jedes erlaubte Element das gemessene. Ein Rahmen ohne
 * Messung ist eine Behauptung; erst der Vergleich macht eine Abweichung
 * sichtbar — und zwar hier, wo der technische Owner sie abstellen kann.
 *
 * Die Reichweite hat keine Messung: sie ist geerbt (A.4.4) und wird nirgends
 * beobachtet. Das steht als Satz da, statt eine Messung vorzutäuschen.
 *
 * ``stand`` ist der Änderungszähler der Seite: steigt er, lädt die Karte neu.
 */
export function Erlaubnisrahmen({ toolId, stand = 0 }: { toolId: string; stand?: number }) {
  const { t } = useSprache();
  const { token } = useSitzung();
  const [rahmen, setRahmen] = useState<Rahmen | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);

  useEffect(() => {
    if (token === null) return;
    api
      .toolErlaubnisrahmen(token, toolId)
      .then(setRahmen)
      .catch(() => setFehler(t('app.fehler')));
    // ``stand`` zaehlt die Aenderungen am Tool. Ohne ihn zeigte die Karte
    // nach dem Verknuepfen eines Datenobjekts weiter den alten Rahmen — also
    // genau dann nicht die Abweichung, wegen der jemand hinsieht.
  }, [token, toolId, t, stand]);

  const benannt = (element: RahmenElement, liste: string[], alsName: boolean) => {
    const praefix = alsName ? null : WERTSCHLUESSEL[element.schluessel];
    return liste.map((wert) => (praefix === null ? wert : t(`${praefix}.${wert}` as never)));
  };

  /**
   * Mehrere Werte stehen untereinander, nicht durch Komma getrennt: die Namen
   * enthalten selbst Kommas und Gedankenstriche, und ein Trennzeichen, das im
   * Wert vorkommt, trennt nichts mehr.
   */
  const werte = (element: RahmenElement, liste: string[], alsName = false) => {
    if (liste.length === 0) return '—';
    return benannt(element, liste, alsName).map((wert) => (
      <span className="eintrag" key={wert}>
        {wert}
      </span>
    ));
  };

  if (fehler !== null) return <Hinweis art="fehler">{fehler}</Hinweis>;
  if (rahmen === null)
    return (
      <Karte titel={t('rahmen.titel')}>
        <Ladeschimmer beschriftung={t('app.laden')} zeilen={3} />
      </Karte>
    );

  const abweichend = rahmen.elemente.filter((element) => !element.eingehalten);

  return (
    <Karte
      titel={t('rahmen.titel')}
      beischrift={t('rahmen.hinweis')}
      aktion={
        rahmen.eingehalten ? (
          <Abzeichen ton="gruen" zeichen="✓">
            {t('rahmen.eingehalten')}
          </Abzeichen>
        ) : (
          <Abzeichen ton="rot" zeichen="!">
            {(abweichend.length === 1 ? t('rahmen.abweichungen.eine') : t('rahmen.abweichungen')).replace(
              '{anzahl}',
              String(abweichend.length),
            )}
          </Abzeichen>
        )
      }
    >
      {rahmen.schicht2_befunde.length > 0 && (
        <Hinweis art="fehler">
          {t('rahmen.schicht2.erkannt')}{' '}
          {rahmen.schicht2_befunde.map((verbot) => t(`schicht2.${verbot}` as never)).join(' · ')}
        </Hinweis>
      )}

      <div className="k-rahmen">
        {rahmen.elemente.map((element) => (
          <div
            key={element.schluessel}
            className="k-rahmenzeile"
            data-testid={`rahmen-${element.schluessel}`}
            data-abweichend={element.eingehalten ? undefined : 'ja'}
          >
            <span className="name">{t(`rahmen.element.${element.schluessel}` as never)}</span>
            <div className="spalten">
              <span className="spalte">
                <span className="etikett">{t('rahmen.erlaubt')}</span>
                <span className="werte" data-testid={`erlaubt-${element.schluessel}`}>
                  {werte(element, element.erlaubt)}
                </span>
              </span>
              <span className="spalte">
                <span className="etikett">{t('rahmen.gemessen')}</span>
                <span className="werte" data-testid={`gemessen-${element.schluessel}`}>
                  {element.messbar ? werte(element, element.gemessen) : t('rahmen.ohneMessung')}
                </span>
              </span>
            </div>
            {!element.eingehalten && (
              <p className="abweichung" data-testid={`abweichung-${element.schluessel}`}>
                {t(`rahmen.abweichung.${element.schluessel}` as never).replace(
                  '{werte}',
                  benannt(
                    element,
                    element.abweichung,
                    ABWEICHUNG_IST_NAME.has(element.schluessel),
                  ).join(' · '),
                )}
              </p>
            )}
          </div>
        ))}
      </div>
    </Karte>
  );
}
