import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type { Deckung, GateStatus, GateTyp, GateVorgang } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { Abzeichen, Auswahl, Feld, Gruppe, Hinweis, Karte, Knopf, Werteliste, Zeile } from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

const GATE_TON: Record<GateStatus, 'gruen' | 'gelb' | 'rot' | 'neutral'> = {
  eingereicht: 'gelb',
  in_pruefung: 'gelb',
  freigegeben: 'gruen',
  abgelehnt: 'rot',
};

/**
 * Selbstverpflichtung und Gate-Vorgänge eines Prozessobjekts
 * (Architektur 8.4 und 8.5).
 *
 * Der Stand der Erklärung kommt als Deckungsurteil vom Server, nicht als
 * Rohliste: ob eine Erklärung trägt, hängt seit AP-5 nicht mehr nur an einem
 * Datum, sondern an der Bewertung, zu der sie abgegeben wurde (A.10.4). Diese
 * Regel gehört nicht in die Oberfläche.
 *
 * Gate 2 verlangt genau einen der fünf abschließend aufgezählten Auslöser; ein
 * sechster, freier Grund ist hier nicht wählbar, weil die Liste im
 * Leitdokument bewusst abschließend ist.
 */
export function ProzessGovernance({ prozessId }: { prozessId: string }) {
  const { t, pfad } = useSprache();
  const { token } = useSitzung();

  const [deckung, setDeckung] = useState<Deckung | null>(null);
  const [gates, setGates] = useState<GateVorgang[]>([]);
  const [ausloeserListe, setAusloeserListe] = useState<string[]>([]);
  const [gateTyp, setGateTyp] = useState<GateTyp>('1');
  const [ausloeser, setAusloeser] = useState('');
  const [begruendung, setBegruendung] = useState('');
  const [fehler, setFehler] = useState<string | null>(null);

  const laden = useCallback(() => {
    if (token === null) return;
    Promise.all([
      api.prozessDeckung(token, prozessId),
      api.gates(token, prozessId),
      api.gateAusloeser(token),
    ])
      .then(([stand, vorgaenge, ausloeserWerte]) => {
        setDeckung(stand);
        setGates(vorgaenge);
        setAusloeserListe(ausloeserWerte);
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, prozessId, t]);

  useEffect(laden, [laden]);

  async function einreichen() {
    if (token === null) return;
    setFehler(null);
    try {
      const vorgang = await api.gateEinreichen(token, prozessId, {
        gate_typ: gateTyp,
        ausloeser: gateTyp === '2' ? ausloeser : null,
        begruendung,
      });
      setGates((bisher) => [vorgang, ...bisher]);
      setBegruendung('');
      setAusloeser('');
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  // Gate 2 ohne Auslöser ist nicht einreichbar — die Sperre steht hier und im
  // Server, damit ein direkter Aufruf sie nicht umgeht (Architektur 10.2).
  const einreichbar = gateTyp === '1' || ausloeser !== '';

  return (
    <>
      <Karte
        titel={t('sv.status')}
        beischrift={deckung?.grundtext}
        aktion={
          deckung === null ? undefined : deckung.gedeckt ? (
            <Abzeichen ton="gruen" zeichen="✓">
              {t('sv.gedeckt')}
            </Abzeichen>
          ) : (
            <Abzeichen ton="gelb" zeichen="!">
              {t(`sv.grund.${deckung.grund || 'keine'}.kurz` as never)}
            </Abzeichen>
          )
        }
      >
        {deckung?.aktuelle != null && (
          <Werteliste
            eintraege={[
              {
                beschriftung: t('sv.abgegebenAm'),
                wert: deckung.aktuelle.abgegeben_am.slice(0, 10),
              },
              {
                beschriftung: t('sv.gebundenAn'),
                wert: `${t('bewertung.tier')} ${deckung.aktuelle.tier_bei_abgabe ?? '—'}`,
              },
              {
                beschriftung: t('sv.gueltigBis'),
                wert: deckung.aktuelle.gueltig_bis?.slice(0, 10) ?? '—',
              },
            ]}
          />
        )}
        <div className="k-knopfreihe">
          <Link
            className="k-knopf k-knopf--getoent"
            to={pfad(`/prozesse/${prozessId}/selbstverpflichtung`)}
            data-testid="sv-oeffnen"
          >
            {t('sv.abgeben')}
          </Link>
        </div>
      </Karte>

      <Karte titel={t('gate.titel')} beischrift={t('gate.hinweis')}>
        {gates.length === 0 ? (
          <p className="leerhinweis">{t('gate.leer')}</p>
        ) : (
          <Gruppe>
            {gates.map((gate) => (
              <Zeile
                key={gate.id}
                pruefkennung={`gate-${gate.id}`}
                haupt={t(`gate.typ.${gate.gate_typ}` as never)}
                zweitzeile={
                  [
                    // Der Auslöser ist ein Schlüssel — auf dem Bildschirm
                    // gehört sein Name hin, nicht seine Kennung.
                    gate.ausloeser === null
                      ? null
                      : t(`gate.ausloeser.${gate.ausloeser}` as never),
                    gate.begruendung,
                    gate.entscheidungskommentar,
                  ]
                    .filter(Boolean)
                    .join(' — ') || undefined
                }
                wert={
                  <Abzeichen ton={GATE_TON[gate.status]}>
                    {t(`gate.status.${gate.status}` as never)}
                  </Abzeichen>
                }
              />
            ))}
          </Gruppe>
        )}

        <Auswahl
          beschriftung={t('gate.typ')}
          wert={gateTyp}
          aendern={(wert) => setGateTyp(wert as GateTyp)}
          optionen={[
            { wert: '1', text: t('gate.typ.1') },
            { wert: '2', text: t('gate.typ.2') },
          ]}
        />
        {gateTyp === '2' && (
          <Auswahl
            beschriftung={t('gate.ausloeser')}
            wert={ausloeser}
            aendern={setAusloeser}
            hilfe={t('gate.ausloeserPflicht')}
            pflicht
            optionen={[
              { wert: '', text: '—' },
              ...ausloeserListe.map((wert) => ({
                wert,
                text: t(`gate.ausloeser.${wert}` as never),
              })),
            ]}
          />
        )}
        <Feld
          beschriftung={t('gate.begruendung')}
          wert={begruendung}
          aendern={setBegruendung}
          hilfe={t('gate.begruendungHilfe')}
        />
        {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}
        <div className="k-knopfreihe">
          <Knopf
            art="gefuellt"
            onClick={einreichen}
            disabled={!einreichbar}
            data-testid="gate-einreichen"
          >
            {t('gate.einreichen')}
          </Knopf>
        </div>
      </Karte>
    </>
  );
}
