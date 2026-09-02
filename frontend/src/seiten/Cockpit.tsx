import { useCallback, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import { api } from '@/api/client';
import type { CockpitEintrag, CockpitZeile, CockpitZeilenkopf, Fachbereich } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { Verteilung } from '@/komponenten/Verteilung';
import {
  Abzeichen,
  Auswahl,
  Gruppe,
  Hinweis,
  Karte,
  Ladeschimmer,
  Leerzustand,
  Seitenkopf,
  ZeileVerweis,
} from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

/** Baut aus Zielmodul und Filter den Deep-Link ins passende Modul (Architektur 9.3). */
export function zielPfad(eintrag: CockpitEintrag, pfad: (rest: string) => string): string {
  const { id, ...rest } = eintrag.ziel_filter;
  if (id !== undefined && (eintrag.ziel_modul === 'prozesse' || eintrag.ziel_modul === 'tools')) {
    return pfad(`/${eintrag.ziel_modul}/${id}`);
  }
  const abfrage = new URLSearchParams(rest).toString();
  return pfad(`/${eintrag.ziel_modul}${abfrage ? `?${abfrage}` : ''}`);
}

function useFachbereiche(): Fachbereich[] {
  const { token } = useSitzung();
  const [fachbereiche, setFachbereiche] = useState<Fachbereich[]>([]);
  useEffect(() => {
    if (token === null) return;
    api
      .fachbereiche(token)
      .then(setFachbereiche)
      .catch(() => setFachbereiche([]));
  }, [token]);
  return fachbereiche;
}

/** Der Fachbereichsfilter, in Übersicht und Detailansicht derselbe. */
function Fachbereichsfilter({
  wert,
  aendern,
}: {
  wert: string;
  aendern: (wert: string) => void;
}) {
  const { t } = useSprache();
  const fachbereiche = useFachbereiche();
  return (
    <Auswahl
      beschriftung={t('cockpit.fachbereich')}
      wert={wert}
      aendern={aendern}
      leertext={t('cockpit.alleFachbereiche')}
      optionen={fachbereiche.map((f) => ({ wert: f.id, text: f.name }))}
      hilfe={t('cockpit.filterHinweis')}
    />
  );
}

/**
 * Cockpit-Übersicht (Architektur 8.7, Leitdokument A.14).
 *
 * Kein überladenes Dashboard, sondern ein Raster gezielt aufrufbarer Karten:
 * je Zeile die Zahl, ein Zustandszeichen und der Satz, was zu tun ist. A.14
 * nennt die Abweichung den „eigentlichen Steuerungshebel" — eine Zeile ohne
 * Handlungssatz wäre eine Kennzahl, und Kennzahlen steuern nichts.
 *
 * Der Fachbereichsfilter steht in der URL, damit eine gefilterte Ansicht
 * teilbar ist (Architektur 9.3) — er verleiht dabei keine Rechte: was ein
 * Nutzer sieht, entscheidet weiterhin allein der Server (Architektur 4.3).
 */
export function Cockpit() {
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const [suche, setSuche] = useSearchParams();
  const [zeilen, setZeilen] = useState<CockpitZeilenkopf[] | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);

  const fachbereich = suche.get('fachbereich') ?? '';

  useEffect(() => {
    if (token === null) return;
    api
      .cockpit(token, fachbereich ? `?fachbereich_id=${fachbereich}` : '')
      .then(setZeilen)
      .catch(() => setFehler(t('app.fehler')));
  }, [token, fachbereich, t]);

  if (fehler !== null) return <Hinweis art="fehler">{fehler}</Hinweis>;
  if (zeilen === null) return <Ladeschimmer beschriftung={t('app.laden')} zeilen={6} />;

  const offen = zeilen.reduce((summe, zeile) => summe + zeile.anzahl, 0);

  return (
    <>
      <Seitenkopf
        titel={t('cockpit.titel')}
        untertitel={t('cockpit.hinweis')}
        aktionen={
          <Abzeichen ton={offen === 0 ? 'gruen' : 'gelb'} zeichen={offen === 0 ? '✓' : '!'}>
            {offen === 0
              ? t('cockpit.allesErledigt')
              : t('cockpit.gesamt').replace('{anzahl}', String(offen))}
          </Abzeichen>
        }
      />

      <Karte>
        <Fachbereichsfilter
          wert={fachbereich}
          aendern={(wert) => setSuche(wert === '' ? {} : { fachbereich: wert })}
        />
      </Karte>

      <div className="k-raster">
        {zeilen.map((zeile) => (
          <Link
            key={zeile.schluessel}
            className="k-kachel"
            data-testid={`kachel-${zeile.schluessel}`}
            data-zustand={zeile.anzahl === 0 ? 'ruhig' : 'offen'}
            to={pfad(
              `/cockpit/${zeile.schluessel}${fachbereich ? `?fachbereich=${fachbereich}` : ''}`,
            )}
          >
            <span className="kopf">
              <span className="punkt" aria-hidden="true">
                {zeile.anzahl === 0 ? '✓' : '!'}
              </span>
              <span className="titel">{zeile.titel}</span>
            </span>
            <span className="zahl" data-testid={`anzahl-${zeile.schluessel}`}>
              {zeile.anzahl}
            </span>
            <span className="satz">{zeile.beschreibung}</span>
            <span className="k-nur-vorlesen">
              {zeile.anzahl === 0 ? t('cockpit.nichtsOffen') : t('cockpit.anzahl')}
            </span>
          </Link>
        ))}
      </div>
    </>
  );
}

/**
 * Eine einzelne Cockpit-Zeile mit ihren Einträgen und deren Zielen.
 *
 * Jeder Eintrag führt vorgefiltert dorthin, wo er abgearbeitet wird — mit dem
 * **Namen** des Zielmoduls, nicht mit seinem Schlüssel.
 */
export function CockpitZeileAnsicht() {
  const { schluessel } = useParams();
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const [suche, setSuche] = useSearchParams();
  const [zeile, setZeile] = useState<CockpitZeile | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);

  const fachbereich = suche.get('fachbereich') ?? '';

  const laden = useCallback(() => {
    if (token === null || schluessel === undefined) return;
    api
      .cockpitZeile(token, schluessel, fachbereich ? `?fachbereich_id=${fachbereich}` : '')
      .then(setZeile)
      .catch(() => setFehler(t('app.fehler')));
  }, [token, schluessel, fachbereich, t]);

  useEffect(laden, [laden]);

  if (fehler !== null) return <Hinweis art="fehler">{fehler}</Hinweis>;
  if (zeile === null) return <Ladeschimmer beschriftung={t('app.laden')} zeilen={5} />;

  return (
    <>
      <Seitenkopf
        titel={zeile.titel}
        untertitel={zeile.beschreibung}
        rueckweg={{ ziel: pfad('/cockpit'), text: t('cockpit.zurueck') }}
        aktionen={
          <Abzeichen ton={zeile.anzahl === 0 ? 'gruen' : 'gelb'}>{String(zeile.anzahl)}</Abzeichen>
        }
      />

      <Karte>
        <Fachbereichsfilter
          wert={fachbereich}
          aendern={(wert) => setSuche(wert === '' ? {} : { fachbereich: wert })}
        />
      </Karte>

      {zeile.aggregat !== null && <Verteilung aggregat={zeile.aggregat} />}

      {zeile.eintraege.length === 0 ? (
        zeile.aggregat === null && (
          <Leerzustand zeichen="✓" titel={t('cockpit.leer')} text={t('cockpit.leerHinweis')} />
        )
      ) : (
        <Karte titel={t('cockpit.eintraege')}>
          <Gruppe>
            {zeile.eintraege.map((eintrag) => (
              <ZeileVerweis
                key={`${eintrag.id}-${eintrag.hinweis}`}
                pruefkennung={`eintrag-${eintrag.id}`}
                ziel={zielPfad(eintrag, pfad)}
                haupt={eintrag.titel}
                zweitzeile={eintrag.hinweis}
                wert={<Abzeichen>{t(`cockpit.modul.${eintrag.ziel_modul}` as never)}</Abzeichen>}
              />
            ))}
          </Gruppe>
        </Karte>
      )}
    </>
  );
}
