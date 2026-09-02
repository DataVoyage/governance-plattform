import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type { Aussage, AussageEingabe, Deckung, SelbstverpflichtungTyp } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import {
  Abzeichen,
  Feld,
  Hinweis,
  Karte,
  Knopf,
  Ladeschimmer,
  Seitenkopf,
  Umschalter,
  Werteliste,
} from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

/** Welches Objekt erklärt — Prozessobjekt oder Tool-Objekt (A.10.2 / A.10.3). */
type Gegenstand = 'prozess' | 'tool';

const TYP: Record<Gegenstand, SelbstverpflichtungTyp> = {
  prozess: 'prozesseigner',
  tool: 'technischer_owner',
};

/**
 * Die Selbstverpflichtung nach Leitdokument A.10.
 *
 * Zwei Dinge unterscheiden sie von einer Checkliste. Erstens ist jede Aussage
 * **spezifisch** (A.10.4): sie behauptet etwas, das sich im Nachhinein prüfen
 * lässt. Zweitens hängt die Erklärung an der Bewertung, zu der sie abgegeben
 * wurde — ändert sich das Profil, verfällt sie. Beides steht in der Kopfzeile,
 * damit niemand eine Erklärung für gültig hält, die es nicht mehr ist.
 *
 * Welche Aussagen verlangt sind, entscheidet der Server (Kurzform bei Tier 1,
 * A.10.5). Diese Seite baut ihre Liste aus dem Katalog und der Deckung — sie
 * kennt die Regel nicht und kann sie deshalb auch nicht anders auslegen.
 */
export function SelbstverpflichtungSeite({ gegenstand }: { gegenstand: Gegenstand }) {
  const { id } = useParams();
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const navigiere = useNavigate();

  const [aussagen, setAussagen] = useState<Aussage[] | null>(null);
  const [deckung, setDeckung] = useState<Deckung | null>(null);
  const [eingaben, setEingaben] = useState<Record<string, AussageEingabe>>({});
  const [offeneKommentare, setOffeneKommentare] = useState<Record<string, boolean>>({});
  const [fehler, setFehler] = useState<string | null>(null);

  const zurueck = pfad(gegenstand === 'prozess' ? `/prozesse/${id}` : `/tools/${id}`);

  const laden = useCallback(() => {
    if (token === null || id === undefined) return;
    Promise.all([
      api.katalog(token),
      gegenstand === 'prozess' ? api.prozessDeckung(token, id) : api.toolDeckung(token, id),
    ])
      .then(([katalog, stand]) => {
        setAussagen(katalog.find((k) => k.typ === TYP[gegenstand])?.aussagen ?? []);
        setDeckung(stand);
        // Eine bestehende Erklärung ist der Ausgangspunkt: wer nachbessert,
        // soll nicht alles noch einmal anklicken.
        setEingaben(stand.aktuelle?.aussagen ?? {});
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, id, gegenstand, t]);

  useEffect(laden, [laden]);

  function setze(aussageId: string, teil: Partial<AussageEingabe>) {
    setEingaben((bisher) => ({
      ...bisher,
      [aussageId]: {
        ...{ bestaetigt: false, kommentar: '' },
        ...(bisher[aussageId] ?? {}),
        ...teil,
      },
    }));
  }

  async function fuehreAus(aktion: () => Promise<unknown>) {
    setFehler(null);
    try {
      await aktion();
      navigiere(zurueck);
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  if (aussagen === null || deckung === null) {
    if (fehler !== null) return <Hinweis art="fehler">{fehler}</Hinweis>;
    return <Ladeschimmer beschriftung={t('app.laden')} zeilen={5} />;
  }

  const verlangt = new Set(deckung.verlangte_aussagen);
  const zuErklaeren = aussagen.filter((a) => verlangt.has(a.id));
  const offen = zuErklaeren.filter((a) => !eingaben[a.id]?.bestaetigt);
  const bestehende = deckung.aktuelle;

  const absenden = () =>
    fuehreAus(() =>
      gegenstand === 'prozess'
        ? api.selbstverpflichtungAbgeben(token as string, id as string, eingaben)
        : api.toolVerpflichtungAbgeben(token as string, id as string, eingaben),
    );

  return (
    <>
      <Seitenkopf
        titel={t('sv.titel')}
        untertitel={t(`sv.untertitel.${gegenstand}` as never)}
        rueckweg={{ ziel: zurueck, text: t('app.zurueck') }}
        aktionen={
          deckung.gedeckt ? (
            <Abzeichen ton="gruen" zeichen="✓">
              {t('sv.gedeckt')}
            </Abzeichen>
          ) : (
            <Abzeichen ton="gelb" zeichen="!">
              {t(`sv.grund.${deckung.grund || 'keine'}.kurz` as never)}
            </Abzeichen>
          )
        }
      />

      {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}

      {/* --- Kopfzeile: wer, wann, an welches Profil gebunden -------------- */}
      <Karte titel={t('sv.stand')} beischrift={deckung.grundtext}>
        {bestehende === null ? (
          <p className="beischrift">{t('sv.nochkeine')}</p>
        ) : (
          <Werteliste
            eintraege={[
              { beschriftung: t('sv.abgegebenAm'), wert: bestehende.abgegeben_am.slice(0, 10) },
              {
                beschriftung: t('sv.gebundenAn'),
                // Beim Prozess an die Bewertung, beim Tool an das geerbte Tier
                // — beides trägt dieselbe Aussage: „gilt für diesen Stand".
                wert: `${t('bewertung.tier')} ${bestehende.tier_bei_abgabe ?? '—'}${
                  bestehende.bewertung_id === null
                    ? ''
                    : ` · ${bestehende.bewertung_id.slice(0, 8)}`
                }`,
              },
              {
                beschriftung: t('bewertung.gueltigBis'),
                wert: bestehende.gueltig_bis ? bestehende.gueltig_bis.slice(0, 10) : '—',
              },
            ]}
          />
        )}
        {/* Die Jahresbestätigung ab Tier 3: ein Klick, kein neuer Durchgang. */}
        {bestehende !== null && deckung.grund === 'frist_abgelaufen' && (
          <div className="k-knopfreihe">
            <Knopf
              art="gefuellt"
              data-testid="sv-bestaetigen"
              onClick={() =>
                fuehreAus(() => api.verpflichtungBestaetigen(token as string, bestehende.id))
              }
            >
              {t('sv.bestaetigen')}
            </Knopf>
          </div>
        )}
      </Karte>

      {/* --- Die Aussagen ------------------------------------------------- */}
      <Karte
        titel={t('sv.aussagen')}
        beischrift={
          deckung.tier === null || deckung.tier < 2 ? t('sv.kurzform') : t('sv.vollform')
        }
        aktion={
          <Abzeichen ton={offen.length === 0 ? 'gruen' : 'neutral'}>
            {`${zuErklaeren.length - offen.length} / ${zuErklaeren.length}`}
          </Abzeichen>
        }
      >
        <div className="k-aussagen">
          {zuErklaeren.map((aussage) => {
            const eingabe = eingaben[aussage.id] ?? { bestaetigt: false, kommentar: '' };
            const kommentarSichtbar = offeneKommentare[aussage.id] || eingabe.kommentar !== '';
            return (
              <div
                key={aussage.id}
                className={`k-aussage${eingabe.bestaetigt ? ' bestaetigt' : ''}`}
                data-testid={`aussage-${aussage.id}`}
              >
                <Abzeichen ton={eingabe.bestaetigt ? 'gruen' : 'neutral'}>{aussage.id}</Abzeichen>
                <div className="satz">
                  <Umschalter
                    beschriftung={aussage.text}
                    an={eingabe.bestaetigt}
                    aendern={(an) => setze(aussage.id, { bestaetigt: an })}
                  />
                  {/* Der Kommentar hängt an der Aussage, nicht an der Erklärung
                      als Ganzes: „gilt mit Einschränkung" ist nur dort
                      verwertbar, wo die Einschränkung steht. Eingeklappt, weil
                      er die Ausnahme ist und nicht die Regel. */}
                  {kommentarSichtbar ? (
                    <Feld
                      beschriftung={`${t('sv.kommentar')} — ${aussage.id}`}
                      wert={eingabe.kommentar}
                      aendern={(wert) => setze(aussage.id, { kommentar: wert })}
                    />
                  ) : (
                    <Knopf
                      art="schlicht"
                      data-testid={`kommentar-oeffnen-${aussage.id}`}
                      onClick={() =>
                        setOffeneKommentare((bisher) => ({ ...bisher, [aussage.id]: true }))
                      }
                    >
                      {t('sv.kommentarZu')}
                    </Knopf>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </Karte>

      {offen.length > 0 && (
        <Hinweis art="warnung">
          {`${t('sv.offen')} ${offen.map((a) => a.id).join(', ')}`}
        </Hinweis>
      )}

      <div className="k-knopfreihe">
        <Knopf art="gefuellt" onClick={absenden} data-testid="sv-abgeben">
          {t('sv.abgeben')}
        </Knopf>
        <Knopf onClick={() => navigiere(zurueck)}>{t('prozess.abbrechen')}</Knopf>
      </div>
    </>
  );
}
