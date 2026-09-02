import { useEffect, useState } from 'react';

import { api } from '@/api/client';
import type { Toolbefund } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { Abzeichen, Gruppe, Hinweis, Karte, Ladeschimmer, ZeileVerweis } from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

/**
 * Der Technologieabgleich aus Prozesssicht (Leitdokument A.9.3).
 *
 * Der Prozess hat selbst keine Technologie — er sieht die Befunde seiner
 * Werkzeuge. Genau so ist die Frage gestellt: „darf dieser Prozess mit diesen
 * Werkzeugen betrieben werden?" Die Karte fasst je Tool zusammen und führt
 * dorthin, wo der Schritt getan wird; die Einzelheiten stehen am Tool-Objekt
 * und werden hier nicht ein zweites Mal ausgebreitet.
 */
export function ProzessKlassen({ prozessId }: { prozessId: string }) {
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const [befunde, setBefunde] = useState<Toolbefund[] | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);

  useEffect(() => {
    if (token === null) return;
    api
      .prozessKlassenbefund(token, prozessId)
      .then(setBefunde)
      .catch(() => setFehler(t('app.fehler')));
  }, [token, prozessId, t]);

  if (fehler !== null) return <Hinweis art="fehler">{fehler}</Hinweis>;
  if (befunde === null)
    return (
      <Karte titel={t('klassen.prozess.titel')}>
        <Ladeschimmer beschriftung={t('app.laden')} zeilen={2} />
      </Karte>
    );

  const ausschluesse = befunde.filter((b) => b.ausschluss).length;
  const offen = befunde.reduce((summe, b) => summe + b.offen, 0);

  return (
    <Karte
      titel={t('klassen.prozess.titel')}
      beischrift={t('klassen.prozess.hinweis')}
      aktion={
        befunde.length === 0 ? undefined : ausschluesse > 0 ? (
          <Abzeichen ton="rot" zeichen="✕">
            {t('klassen.befund.ausschluss')}
          </Abzeichen>
        ) : offen > 0 ? (
          <Abzeichen ton="gelb" zeichen="!">
            {(offen === 1 ? t('klassen.befund.offen.eine') : t('klassen.befund.offen')).replace(
              '{anzahl}',
              String(offen),
            )}
          </Abzeichen>
        ) : (
          <Abzeichen ton="gruen" zeichen="✓">
            {t('klassen.befund.getragen')}
          </Abzeichen>
        )
      }
    >
      {befunde.length === 0 ? (
        <p className="leerhinweis">{t('klassen.prozess.leer')}</p>
      ) : (
        <Gruppe>
          {befunde.map((befund) => (
            <ZeileVerweis
              key={befund.tool_id}
              pruefkennung={`prozessbefund-${befund.tool_id}`}
              ziel={pfad(`/tools/${befund.tool_id}`)}
              haupt={befund.tool_name}
              zweitzeile={
                befund.offen === 0
                  ? t('klassen.prozess.getragen')
                  : befund.befunde
                      .filter((e) => e.offen)
                      .map((e) => `${e.k_klasse}: ${t(`klassen.art.${e.art}` as never)}`)
                      .join(' · ')
              }
              wert={
                befund.ausschluss ? (
                  <Abzeichen ton="rot" zeichen="✕">
                    {t('klassen.befund.ausschluss')}
                  </Abzeichen>
                ) : befund.offen > 0 ? (
                  <Abzeichen ton="gelb" zeichen="!">
                    {String(befund.offen)}
                  </Abzeichen>
                ) : (
                  <Abzeichen ton="gruen" zeichen="✓">
                    {t('klassen.befund.getragen')}
                  </Abzeichen>
                )
              }
            />
          ))}
        </Gruppe>
      )}
    </Karte>
  );
}
