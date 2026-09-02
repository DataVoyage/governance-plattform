import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type { Beleg, BewertungsModus, Ergebnis, Frage } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import {
  Abzeichen,
  Blatt,
  Feld,
  Hinweis,
  Karte,
  Knopf,
  Ladeschimmer,
  Seitenkopf,
  SegmentierteSteuerung,
  Werteliste,
} from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

/** Reihenfolge der Blöcke im Profil — dieselbe wie im Baum (A.8.5). */
const BLOECKE = ['ki', 'ds', 'mb', 'it', 'rg', 'ur'] as const;

type Phase = 'modus' | 'frage' | 'ergebnis' | 'verboten';

/**
 * Der Bewertungs-Wizard (Leitdokument A.8, Umsetzungsplan AP-4).
 *
 * Eine Frage je Bildschirm. Die Reihenfolge kommt vom Server; diese Komponente
 * kennt sie nicht und kann sie deshalb auch nicht versehentlich verschieben.
 *
 * Der Unterschied zur ersten Fassung liegt in dem, was **neben** der Frage
 * steht: A.8.4 verlangt, dass ableitbare Dimensionen nicht erfragt, sondern
 * vorgeschlagen werden. Der Server liefert den Vorschlag samt Belegen mit, die
 * Karte zeigt beides, und wer anders antwortet, schreibt einen Satz dazu —
 * erst dann geht es weiter. Der Zwischenstand bleibt verborgen, damit niemand
 * seine Antworten auf ein Wunschergebnis hin einrichtet.
 */
export function BewertungsWizard() {
  const { id } = useParams();
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const navigiere = useNavigate();

  const [modus, setModus] = useState<BewertungsModus>('vollstaendig');
  const [phase, setPhase] = useState<Phase>('modus');
  const [antworten, setAntworten] = useState<Record<string, boolean>>({});
  const [begruendungen, setBegruendungen] = useState<Record<string, string>>({});
  const [verlauf, setVerlauf] = useState<string[]>([]);
  // Was auf eine Frage schon einmal geantwortet wurde. Anders als `antworten`
  // wird hier nichts geloescht: geht man einen Schritt zurueck, soll die
  // vorige Antwort noch dastehen und sich aendern lassen — sonst muesste man
  // sich erinnern, was man vorhin geklickt hat.
  const [gesehen, setGesehen] = useState<Record<string, boolean>>({});
  const [frage, setFrage] = useState<Frage | null>(null);
  const [ergebnis, setErgebnis] = useState<Ergebnis | null>(null);
  const [entwurf, setEntwurf] = useState<{ wert: boolean; text: string } | null>(null);
  const [abbruchFrage, setAbbruchFrage] = useState(false);
  const [fehler, setFehler] = useState<string | null>(null);

  // Laufende Nummer der Abfrage. Antwortet der Server auf einen älteren
  // Schritt später als auf einen neueren — bei langsamer Verbindung oder
  // schnellem Klicken —, würde die veraltete Antwort sonst den aktuellen
  // Schritt überschreiben und der Wizard spränge zurück.
  const laufendeNummer = useRef(0);

  const schritt = useCallback(
    async (
      gewaehlterModus: BewertungsModus,
      bisher: Record<string, boolean>,
      gruende: Record<string, string>,
    ) => {
      if (token === null || id === undefined) return;
      laufendeNummer.current += 1;
      const meine = laufendeNummer.current;
      try {
        const stand = await api.wizardSchritt(token, id, gewaehlterModus, bisher, gruende);
        if (meine !== laufendeNummer.current) return;
        setFehler(null);
        setFrage(stand.naechste_frage);
        setErgebnis(stand.vorschau);
        setEntwurf(null);
        if (stand.verboten) setPhase('verboten');
        else if (stand.vorschau !== null) setPhase('ergebnis');
        else setPhase('frage');
      } catch (ausnahme) {
        if (meine !== laufendeNummer.current) return;
        setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
      }
    },
    [token, id, t],
  );

  // Der Modusbildschirm fragt noch nichts ab; erst mit dem Start beginnt der
  // Durchlauf. Danach folgt jeder Schritt einer Antwort, nicht einem Effekt.
  useEffect(() => {
    if (phase !== 'modus' && frage === null && ergebnis === null) {
      void schritt(modus, antworten, begruendungen);
    }
    // Nur beim Übergang aus der Modusauswahl.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  const zurueckZumProzess = () => navigiere(pfad(`/prozesse/${id}`));

  const starten = () => {
    setAntworten({});
    setGesehen({});
    setBegruendungen({});
    setVerlauf([]);
    setFrage(null);
    setErgebnis(null);
    setPhase('frage');
  };

  /** Übernimmt eine Antwort und geht einen Schritt weiter. */
  const uebernimm = (wert: boolean, begruendung?: string) => {
    if (frage === null) return;
    const naechste = { ...antworten, [frage.id]: wert };
    const gruende =
      begruendung === undefined
        ? begruendungen
        : { ...begruendungen, [frage.id]: begruendung };
    setAntworten(naechste);
    setGesehen((bisher) => ({ ...bisher, [frage.id]: wert }));
    setBegruendungen(gruende);
    setVerlauf((bisher) => [...bisher, frage.id]);
    void schritt(modus, naechste, gruende);
  };

  /**
   * Eine Antwort wählen. Stimmt sie mit dem Vorschlag überein oder gibt es
   * keinen, geht es sofort weiter — der übliche Fall soll schnell sein. Weicht
   * sie ab, hält der Wizard an und verlangt den Satz, der A.8.4 genügt.
   */
  const antworte = (wert: boolean) => {
    if (frage === null) return;
    if (frage.vorschlag !== null && frage.vorschlag !== wert) {
      setEntwurf({ wert, text: begruendungen[frage.id] ?? '' });
      return;
    }
    setEntwurf(null);
    uebernimm(wert);
  };

  /** Einen Schritt zurück: die letzte Antwort fällt weg, die Frage kommt wieder. */
  const zurueck = () => {
    const letzte = verlauf[verlauf.length - 1];
    if (letzte === undefined) {
      setPhase('modus');
      return;
    }
    const naechste = { ...antworten };
    delete naechste[letzte];
    setAntworten(naechste);
    setVerlauf((bisher) => bisher.slice(0, -1));
    setErgebnis(null);
    void schritt(modus, naechste, begruendungen);
  };

  const speichern = async () => {
    if (token === null || id === undefined) return;
    try {
      await api.bewertungAbschliessen(token, id, modus, antworten, begruendungen);
      zurueckZumProzess();
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  };

  const kopf = (
    <Seitenkopf
      titel={t('bewertung.titel')}
      untertitel={t('bewertung.untertitel')}
      rueckweg={{ ziel: pfad(`/prozesse/${id}`), text: t('nav.prozesse') }}
    />
  );

  // --- Modusauswahl (A.8.5) ----------------------------------------------

  if (phase === 'modus') {
    return (
      <>
        {kopf}
        <Karte titel={t('bewertung.modus.frage')} beischrift={t('bewertung.modus.hinweis')}>
          {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}
          <SegmentierteSteuerung<BewertungsModus>
            beschriftung={t('bewertung.modus.frage')}
            wert={modus}
            aendern={setModus}
            optionen={[
              { wert: 'vollstaendig', text: t('bewertung.modus.vollstaendig.kurz') },
              { wert: 'schnell', text: t('bewertung.modus.schnell.kurz') },
            ]}
          />
          <Hinweis art="information">
            {modus === 'schnell'
              ? t('bewertung.modus.schnell.folge')
              : t('bewertung.modus.vollstaendig.folge')}
          </Hinweis>
          <div className="k-knopfreihe">
            <Knopf art="gefuellt" onClick={starten} data-testid="bewertung-starten">
              {t('bewertung.starten')}
            </Knopf>
            <Knopf onClick={zurueckZumProzess}>{t('prozess.abbrechen')}</Knopf>
          </div>
        </Karte>
      </>
    );
  }

  // --- Verbotstatbestand (1b): eigener roter Ausgang ---------------------

  if (phase === 'verboten') {
    return (
      <>
        {kopf}
        <Karte>
          <div className="k-ausgang k-ausgang--rot" data-testid="verbotstatbestand">
            <span className="symbol" aria-hidden="true">
              ⨯
            </span>
            <h2>{t('bewertung.verboten.titel')}</h2>
            <p role="alert">{t('bewertung.verboten.text')}</p>
            <p className="beischrift">{t('bewertung.verboten.weg')}</p>
          </div>
          {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}
          <div className="k-knopfreihe">
            <Knopf art="zerstoerend" onClick={speichern} data-testid="alarm-ausloesen">
              {t('bewertung.verboten.alarm')}
            </Knopf>
            <Knopf onClick={zurueck}>{t('bewertung.zurueck')}</Knopf>
          </div>
        </Karte>
      </>
    );
  }

  // --- Ergebnis ----------------------------------------------------------

  if (phase === 'ergebnis' && ergebnis !== null) {
    const profil = BLOECKE.map((block) => `${block.toUpperCase()}${ergebnis.profil[block] ?? 0}`);
    return (
      <>
        {kopf}
        <Karte>
          <div className="k-ergebnis">
            <div className="stufe">
              <span className="zahl" data-testid="tier">
                {ergebnis.tier}
              </span>
              <span className="wort">{t('bewertung.tier')}</span>
            </div>
            <p className="profil" data-testid="profil">
              {profil.join('-')}
            </p>
          </div>
          {!ergebnis.vollstaendig && <Hinweis art="warnung">{t('bewertung.keineKKlassen')}</Hinweis>}
        </Karte>

        <Karte titel={t('bewertung.kKlassen')} beischrift={t('bewertung.kKlassen.hinweis')}>
          {ergebnis.klassen.length === 0 ? (
            <p className="beischrift">{t('bewertung.kKlassen.leer')}</p>
          ) : (
            <ul className="k-klassen" data-testid="k-klassen">
              {ergebnis.klassen.map((klasse) => (
                <li key={klasse.kennung}>
                  <Abzeichen ton="blau">{klasse.kennung}</Abzeichen>
                  <div>
                    <p className="name">{klasse.name}</p>
                    <p className="beischrift">{klasse.erklaerung}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Karte>

        <Karte
          titel={t('bewertung.auflagen')}
          beischrift={`${t('bewertung.tier')} ${ergebnis.tier} — ${t('bewertung.auflagen.hinweis')}`}
        >
          <ul className="k-auflagen" data-testid="auflagen">
            {ergebnis.auflagen.map((satz) => (
              <li key={satz}>{satz}</li>
            ))}
          </ul>
        </Karte>

        {Object.keys(begruendungen).length > 0 && (
          <Karte titel={t('bewertung.abweichungen')} beischrift={t('bewertung.abweichungen.hinweis')}>
            <Werteliste
              eintraege={Object.entries(begruendungen).map(([frageId, text]) => ({
                beschriftung: `${t('bewertung.frage')} ${frageId}`,
                wert: text,
              }))}
            />
          </Karte>
        )}

        {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}
        <div className="k-knopfreihe">
          <Knopf art="gefuellt" onClick={speichern} data-testid="bewertung-speichern">
            {t('bewertung.speichern')}
          </Knopf>
          <Knopf onClick={zurueck}>{t('bewertung.zurueck')}</Knopf>
        </div>
      </>
    );
  }

  // Scheitert schon der erste Schritt — fehlende Berechtigung, Netz weg —,
  // darf hier kein Ladeschimmer stehenbleiben: es kommt nichts mehr nach.
  if (frage === null) {
    if (fehler === null) return <Ladeschimmer beschriftung={t('app.laden')} zeilen={4} />;
    return (
      <>
        {kopf}
        <Karte>
          <Hinweis art="fehler">{fehler}</Hinweis>
          <div className="k-knopfreihe">
            <Knopf onClick={() => setPhase('modus')}>{t('bewertung.zurueckZurAuswahl')}</Knopf>
            <Knopf onClick={zurueckZumProzess}>{t('prozess.abbrechen')}</Knopf>
          </div>
        </Karte>
      </>
    );
  }

  // --- Eine Frage je Bildschirm ------------------------------------------

  const gewaehlt = entwurf?.wert ?? antworten[frage.id] ?? gesehen[frage.id];
  const abweichend = entwurf !== null;

  return (
    <>
      {kopf}
      <Karte>
        <div className="k-fortschritt">
          <ol aria-label={t('bewertung.fortschritt')}>
            {Array.from({ length: frage.anzahl_bloecke }, (_, nummer) => (
              <li
                key={nummer}
                className={
                  nummer + 1 < frage.nummer ? 'erledigt' : nummer + 1 === frage.nummer ? 'hier' : ''
                }
                aria-current={nummer + 1 === frage.nummer ? 'step' : undefined}
              >
                <span className="k-nur-vorlesen">
                  {t('bewertung.schritt')} {nummer + 1}
                </span>
              </li>
            ))}
          </ol>
          <p className="beischrift">
            {t('bewertung.schritt')} {frage.nummer} {t('bewertung.von')} {frage.anzahl_bloecke} —{' '}
            {frage.block_titel}
          </p>
        </div>

        <h2 className="k-frage" data-testid="frage" data-frage-id={frage.id}>
          {frage.text}
        </h2>

        {frage.vorschlag !== null ? (
          <div className="k-vorschlag" data-testid="vorschlag" data-wert={String(frage.vorschlag)}>
            <p className="titel">
              {t('bewertung.vorschlag')}{' '}
              <strong>{frage.vorschlag ? t('bewertung.ja') : t('bewertung.nein')}</strong>
            </p>
            <BelegListe belege={frage.belege} />
          </div>
        ) : (
          frage.belege.length > 0 && (
            <div className="k-vorschlag k-vorschlag--offen" data-testid="vorschlag" data-wert="offen">
              <p className="titel">{t('bewertung.vorschlag.offen')}</p>
              <BelegListe belege={frage.belege} />
            </div>
          )
        )}

        <div className="k-antwortflaechen">
          <button
            type="button"
            className={`k-antwort${gewaehlt === true ? ' gewaehlt' : ''}`}
            aria-pressed={gewaehlt === true}
            onClick={() => antworte(true)}
          >
            {t('bewertung.ja')}
          </button>
          <button
            type="button"
            className={`k-antwort${gewaehlt === false ? ' gewaehlt' : ''}`}
            aria-pressed={gewaehlt === false}
            onClick={() => antworte(false)}
          >
            {t('bewertung.nein')}
          </button>
        </div>

        {abweichend && (
          <div className="k-begruendung" data-testid="begruendung">
            <Hinweis art="warnung">{t('bewertung.abweichung.hinweis')}</Hinweis>
            <Feld
              beschriftung={t('bewertung.abweichung.feld')}
              hilfe={t('bewertung.abweichung.hilfe')}
              wert={entwurf.text}
              mehrzeilig
              pflicht
              aendern={(text) => setEntwurf({ wert: entwurf.wert, text })}
            />
            <div className="k-knopfreihe">
              <Knopf
                art="gefuellt"
                onClick={() => uebernimm(entwurf.wert, entwurf.text.trim())}
                disabled={entwurf.text.trim() === ''}
                data-testid="abweichung-uebernehmen"
              >
                {t('bewertung.weiter')}
              </Knopf>
              <Knopf onClick={() => setEntwurf(null)}>{t('prozess.abbrechen')}</Knopf>
            </div>
          </div>
        )}

        {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}

        <div className="k-knopfreihe k-knopfreihe--getrennt">
          <Knopf onClick={zurueck} data-testid="bewertung-zurueck">
            {t('bewertung.zurueck')}
          </Knopf>
          <Knopf art="schlicht" onClick={() => setAbbruchFrage(true)}>
            {t('bewertung.abbrechen')}
          </Knopf>
        </div>
      </Karte>

      {abbruchFrage && (
        <Blatt
          titel={t('bewertung.abbruch.titel')}
          beischrift={t('bewertung.abbruch.text')}
          schliessen={() => setAbbruchFrage(false)}
          fuss={
            <>
              <Knopf onClick={() => setAbbruchFrage(false)}>
                {t('bewertung.abbruch.weiterbewerten')}
              </Knopf>
              <Knopf art="zerstoerend" onClick={zurueckZumProzess} data-testid="abbruch-verwerfen">
                {t('bewertung.abbruch.verwerfen')}
              </Knopf>
            </>
          }
        >
          <p>
            {verlauf.length === 1
              ? t('bewertung.abbruch.zaehler.eine')
              : `${verlauf.length} ${t('bewertung.abbruch.zaehler')}`}
          </p>
        </Blatt>
      )}
    </>
  );
}

/** Die Belege eines Vorschlags — je Zeile ein Grund mit seiner Quelle. */
function BelegListe({ belege }: { belege: Beleg[] }) {
  const { t } = useSprache();
  if (belege.length === 0) return null;
  return (
    <ul className="belege">
      {belege.map((beleg) => (
        <li key={beleg.text}>
          <span className="quelle">{t(`bewertung.quelle.${beleg.quelle}` as never)}</span>
          {beleg.text}
        </li>
      ))}
    </ul>
  );
}
