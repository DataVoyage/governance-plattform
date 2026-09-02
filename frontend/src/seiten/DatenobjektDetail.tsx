import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type { DatenObjekt, Datenkategorie, Fachbereich, Nutzer, Wirkung } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { KATEGORIEN, KATEGORIE_TON } from '@/seiten/DatenobjektListe';
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
  Seitenkopf,
  Werteliste,
  Zeile,
  ZeileVerweis,
} from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

/**
 * Ein Datenobjekt mit seinen beiden Rückwärtssichten (Leitdokument A.4.3).
 *
 * Wer die Kategorie ändert, sieht vorher, wen es trifft: A.4.5 verspricht, dass
 * eine Umklassifizierung **eine** Änderung ist statt einer organisationsweiten
 * Nacherfassung — dieses Versprechen ist nur dann etwas wert, wenn die Wirkung
 * auch sichtbar wird.
 */
export function DatenobjektDetail() {
  const { id } = useParams();
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const [datenobjekt, setDatenobjekt] = useState<DatenObjekt | null>(null);
  const [wirkung, setWirkung] = useState<Wirkung | null>(null);
  const [nutzer, setNutzer] = useState<Nutzer[]>([]);
  const [fachbereiche, setFachbereiche] = useState<Fachbereich[]>([]);
  const [vorschau, setVorschau] = useState<{ kategorie: string; wirkung: Wirkung } | null>(null);
  /** Freitext ist ein Entwurf, bis gespeichert wird. Er darf nicht von der
   *  Antwort einer nebenher laufenden Änderung überschrieben werden. */
  const [quellsystem, setQuellsystem] = useState('');
  const [fehler, setFehler] = useState<string | null>(null);

  const laden = useCallback(() => {
    if (token === null || id === undefined) return;
    Promise.all([
      api.datenobjekt(token, id),
      api.datenobjektWirkung(token, id),
      api.nutzer(token).catch(() => [] as Nutzer[]),
      api.fachbereiche(token).catch(() => [] as Fachbereich[]),
    ])
      .then(([geladen, stand, personen, bereiche]) => {
        setDatenobjekt(geladen);
        setQuellsystem(geladen.quellsystem ?? '');
        setWirkung(stand);
        setNutzer(personen);
        setFachbereiche(bereiche);
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, id, t]);

  useEffect(laden, [laden]);

  /** Erst die Vorschau, dann die Entscheidung — nie umgekehrt. */
  async function vorschauOeffnen(neueKategorie: string) {
    if (token === null || id === undefined) return;
    setFehler(null);
    try {
      const gerechnet = await api.datenobjektWirkung(
        token,
        id,
        neueKategorie === '' ? null : (neueKategorie as Datenkategorie),
      );
      setVorschau({ kategorie: neueKategorie, wirkung: gerechnet });
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  async function uebernehmen() {
    if (token === null || id === undefined || vorschau === null) return;
    try {
      await api.datenobjektAendern(token, id, {
        kategorie: vorschau.kategorie === '' ? null : (vorschau.kategorie as Datenkategorie),
      });
      setVorschau(null);
      laden();
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  async function feldAendern(feld: 'owner_user_id' | 'fachbereich_id' | 'quellsystem', wert: string) {
    if (token === null || id === undefined) return;
    try {
      const aktualisiert = await api.datenobjektAendern(token, id, {
        [feld]: wert === '' ? null : wert,
      });
      setDatenobjekt(aktualisiert);
      if (feld === 'quellsystem') setQuellsystem(aktualisiert.quellsystem ?? '');
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  if (fehler !== null && datenobjekt === null) return <Hinweis art="fehler">{fehler}</Hinweis>;
  if (datenobjekt === null || wirkung === null)
    return <Ladeschimmer beschriftung={t('app.laden')} zeilen={4} />;

  const gesperrt = datenobjekt.schreibgeschuetzte_felder;

  return (
    <>
      <Seitenkopf
        titel={datenobjekt.name}
        untertitel={datenobjekt.quellsystem ?? t('asset.quellsystem.leer')}
        rueckweg={{ ziel: pfad('/datenobjekte'), text: t('asset.datenobjekte.titel') }}
        aktionen={
          datenobjekt.kategorie === null ? (
            <Abzeichen ton="gelb" zeichen="!">
              {t('asset.kategorie.keine')}
            </Abzeichen>
          ) : (
            <Abzeichen ton={KATEGORIE_TON[datenobjekt.kategorie]}>
              {t(`kategorie.${datenobjekt.kategorie}` as never)}
            </Abzeichen>
          )
        }
      />

      {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}
      {gesperrt.length > 0 && <Hinweis art="information">{t('asset.importHinweis')}</Hinweis>}

      <Karte titel={t('asset.reifegrad1')} beischrift={t('asset.reifegrad1.hinweis')}>
        <Auswahl
          beschriftung={t('asset.feld.kategorie')}
          wert={datenobjekt.kategorie ?? ''}
          aendern={vorschauOeffnen}
          leertext={t('asset.kategorie.keine')}
          optionen={KATEGORIEN.map((k) => ({
            wert: k,
            text: `${t(`kategorie.${k}` as never)} — ${t(`kategorie.anker.${k}` as never)}`,
          }))}
          hilfe={t('asset.kategorie.wirkungHinweis')}
        />
        <Auswahl
          beschriftung={t('asset.feld.owner')}
          wert={datenobjekt.owner_user_id ?? ''}
          aendern={(wert) => feldAendern('owner_user_id', wert)}
          leertext="—"
          optionen={nutzer.map((n) => ({ wert: n.id, text: n.name }))}
          hilfe={t('asset.owner.hilfe')}
        />
        <Auswahl
          beschriftung={t('asset.feld.fachbereich')}
          wert={datenobjekt.fachbereich_id ?? ''}
          aendern={(wert) => feldAendern('fachbereich_id', wert)}
          leertext="—"
          optionen={fachbereiche.map((f) => ({ wert: f.id, text: f.name }))}
        />
        <Feld
          beschriftung={t('asset.feld.quellsystem')}
          wert={quellsystem}
          aendern={setQuellsystem}
          hilfe={t('asset.quellsystem.hilfe')}
          hoechstlaenge={255}
        />
        <Knopf onClick={() => feldAendern('quellsystem', quellsystem)}>
          {t('asset.speichern')}
        </Knopf>
      </Karte>

      <Gruppe etikett={t('asset.verwendung.prozesse')} hinweis={t('asset.verwendung.hinweis')}>
        {wirkung.prozesse.length === 0 ? (
          <Zeile haupt={<span className="leerhinweis">{t('asset.verwendung.keineProzesse')}</span>} />
        ) : (
          wirkung.prozesse.map((p) => (
            <ZeileVerweis
              key={p.id}
              ziel={pfad(`/prozesse/${p.id}`)}
              haupt={p.name}
              zweitzeile={[
                p.als_input ? t('asset.verwendung.alsInput') : null,
                p.als_output ? t('asset.verwendung.alsOutput') : null,
              ]
                .filter(Boolean)
                .join(' · ')}
              wert={
                <>
                  {p.mitbestimmung_flag && <Abzeichen ton="lila">MB</Abzeichen>}
                  {p.tier !== null && <Abzeichen>{`Tier ${p.tier}`}</Abzeichen>}
                </>
              }
            />
          ))
        )}
      </Gruppe>

      <Gruppe etikett={t('asset.verwendung.tools')}>
        {wirkung.tools.length === 0 ? (
          <Zeile haupt={<span className="leerhinweis">{t('asset.verwendung.keineTools')}</span>} />
        ) : (
          wirkung.tools.map((tool) => (
            <ZeileVerweis
              key={tool.id}
              ziel={pfad(`/tools/${tool.id}`)}
              haupt={tool.name}
              zweitzeile={
                tool.zugriffsart === null
                  ? t('asset.verwendung.ueberProzess')
                  : t(`zugriffsart.${tool.zugriffsart}` as never)
              }
            />
          ))
        )}
      </Gruppe>

      {vorschau !== null && (
        <Blatt
          titel={t('asset.wirkung.titel')}
          beischrift={t('asset.wirkung.hinweis')}
          schliessen={() => setVorschau(null)}
          fuss={
            <>
              <Knopf onClick={() => setVorschau(null)}>{t('prozess.abbrechen')}</Knopf>
              <Knopf art="gefuellt" onClick={uebernehmen}>
                {t('asset.wirkung.uebernehmen')}
              </Knopf>
            </>
          }
        >
          <Werteliste
            eintraege={[
              {
                beschriftung: t('asset.wirkung.von'),
                wert:
                  vorschau.wirkung.kategorie_alt === null
                    ? t('asset.kategorie.keine')
                    : t(`kategorie.${vorschau.wirkung.kategorie_alt}` as never),
              },
              {
                beschriftung: t('asset.wirkung.nach'),
                wert:
                  vorschau.wirkung.kategorie_neu === null
                    ? t('asset.kategorie.keine')
                    : t(`kategorie.${vorschau.wirkung.kategorie_neu}` as never),
              },
              {
                beschriftung: t('asset.wirkung.prozesse'),
                wert: vorschau.wirkung.prozesse.length,
                pruefkennung: 'wirkung-prozesse',
              },
              {
                beschriftung: t('asset.wirkung.tools'),
                wert: vorschau.wirkung.tools.length,
                pruefkennung: 'wirkung-tools',
              },
              {
                beschriftung: t('asset.wirkung.mitbestimmung'),
                wert: vorschau.wirkung.mitbestimmung_neu,
                herkunft: t('asset.wirkung.mitbestimmungHinweis'),
                pruefkennung: 'wirkung-mitbestimmung',
              },
            ]}
          />
          {vorschau.wirkung.mitbestimmung_neu > 0 && (
            <Hinweis art="warnung">{t('asset.wirkung.warnung')}</Hinweis>
          )}
        </Blatt>
      )}
    </>
  );
}
