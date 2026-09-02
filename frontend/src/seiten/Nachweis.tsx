import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type { Nachweiseintrag } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import {
  Abzeichen,
  Auswahl,
  Gruppe,
  Hinweis,
  Karte,
  Ladeschimmer,
  Leerzustand,
  Seitenkopf,
  Zeile,
  type Ton,
} from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

/** Die Objektarten, nach denen sich der Nachweis sinnvoll filtern lässt. */
const ARTEN = [
  'prozessobjekte',
  'bewertungen',
  'tool_objekte',
  'datenobjekte',
  'selbstverpflichtungen',
  'gate_vorgaenge',
  'lenkungsvorgaenge',
  'compliance_zustaende',
  'rollenzuweisungen',
  'konfiguration',
];

const AKTION_TON: Record<string, Ton> = {
  erstellt: 'gruen',
  geaendert: 'blau',
  geloescht: 'rot',
};

/**
 * Nachweis (Leitdokument A.13.7, Architektur 10.4).
 *
 * Das Änderungsprotokoll war nur über die Datenbank oder die Delta-Abfrage der
 * Query-API zu lesen — die erste ist niemandem zumutbar, die zweite ist für
 * andockende Anwendungen gedacht und liefert bewusst keine Inhalte.
 *
 * Hier steht, was eine Prüfung braucht: **wer** hat **wann** **was** geändert,
 * mit Vorher und Nachher je Feld. Belanglose Felder — die Zeitstempel, die
 * sich bei jeder Änderung ändern — bleiben weg; sie erklären nichts und
 * verdecken das, was zählt.
 */
export function Nachweis() {
  const { t } = useSprache();
  const { token } = useSitzung();
  const [suche, setSuche] = useSearchParams();
  const [eintraege, setEintraege] = useState<Nachweiseintrag[] | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);

  const art = suche.get('art') ?? '';

  useEffect(() => {
    if (token === null) return;
    api
      .nachweis(token, art ? `?entity_type=${art}` : '')
      .then(setEintraege)
      .catch((ausnahme) =>
        setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler')),
      );
  }, [token, art, t]);

  if (fehler !== null) return <Hinweis art="fehler">{fehler}</Hinweis>;
  if (eintraege === null) return <Ladeschimmer beschriftung={t('app.laden')} zeilen={6} />;

  return (
    <>
      <Seitenkopf titel={t('nachweis.titel')} untertitel={t('nachweis.hinweis')} />

      <Karte>
        <Auswahl
          beschriftung={t('nachweis.art')}
          wert={art}
          aendern={(wert) => setSuche(wert === '' ? {} : { art: wert })}
          leertext={t('nachweis.alleArten')}
          optionen={ARTEN.map((wert) => ({ wert, text: t(`nachweis.art.${wert}` as never) }))}
          hilfe={t('nachweis.filterHinweis')}
        />
      </Karte>

      {eintraege.length === 0 ? (
        <Leerzustand titel={t('nachweis.leer')} text={t('nachweis.leerHinweis')} />
      ) : (
        <Karte titel={t('nachweis.eintraege')}>
          <Gruppe>
            {eintraege.map((eintrag) => (
              <Zeile
                key={eintrag.cursor}
                pruefkennung={`nachweis-${eintrag.cursor}`}
                haupt={
                  eintrag.gegenstand ||
                  t(`nachweis.art.${eintrag.entity_type}` as never) ||
                  eintrag.entity_type
                }
                zweitzeile={
                  <>
                    <span className="satzzeile">
                      {eintrag.akteur} · {eintrag.zeitpunkt.slice(0, 16).replace('T', ' ')} ·{' '}
                      {t(`nachweis.art.${eintrag.entity_type}` as never) || eintrag.entity_type}
                    </span>
                    {eintrag.aenderungen.map((aenderung) => (
                      <span className="satzzeile" key={aenderung.feld}>
                        {aenderung.feld}: {aenderung.vorher} → {aenderung.nachher}
                      </span>
                    ))}
                  </>
                }
                wert={
                  <Abzeichen ton={AKTION_TON[eintrag.aktion] ?? 'neutral'}>
                    {t(`nachweis.aktion.${eintrag.aktion}` as never)}
                  </Abzeichen>
                }
              />
            ))}
          </Gruppe>
        </Karte>
      )}
    </>
  );
}
