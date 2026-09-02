import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type { GateVorgang, Prozess } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import {
  Abzeichen,
  Feld,
  Hinweis,
  Karte,
  Knopf,
  Ladeschimmer,
  Leerzustand,
  Seitenkopf,
  Werteliste,
} from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

/**
 * Arbeitsvorrat der Governance-Rolle (Architektur 8.5).
 *
 * Entscheiden darf ausschliesslich die Governance-Rolle; das Frontend blendet
 * die Knöpfe für andere aus, verlässt sich aber nicht darauf — die Route prüft
 * unabhängig (Architektur 10.2).
 */
export function Gates() {
  const { t, pfad } = useSprache();
  const { token, hatRolle } = useSitzung();
  const [gates, setGates] = useState<GateVorgang[] | null>(null);
  const [prozesse, setProzesse] = useState<Prozess[]>([]);
  const [kommentare, setKommentare] = useState<Record<string, string>>({});
  const [fehler, setFehler] = useState<string | null>(null);

  useEffect(() => {
    if (token === null) return;
    Promise.all([api.offeneGates(token), api.prozesse(token)])
      .then(([offen, alle]) => {
        setGates(offen);
        setProzesse(alle);
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, t]);

  async function entscheiden(gateId: string, status: 'freigegeben' | 'abgelehnt') {
    if (token === null) return;
    setFehler(null);
    try {
      await api.gateEntscheiden(token, gateId, status, kommentare[gateId] ?? '');
      setGates((bisher) => (bisher ?? []).filter((g) => g.id !== gateId));
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  if (gates === null) {
    if (fehler !== null) return <Hinweis art="fehler">{fehler}</Hinweis>;
    return <Ladeschimmer beschriftung={t('app.laden')} zeilen={4} />;
  }

  const darfEntscheiden = hatRolle('governance');

  return (
    <>
      <Seitenkopf titel={t('gate.arbeitsvorrat')} untertitel={t('gate.arbeitsvorratHinweis')} />
      {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}

      {gates.length === 0 ? (
        <Leerzustand zeichen="✓" titel={t('gate.arbeitsvorratLeer')} />
      ) : (
        gates.map((gate) => {
          const kommentar = kommentare[gate.id] ?? '';
          return (
            <Karte
              key={gate.id}
              titel={
                prozesse.find((p) => p.id === gate.prozessobjekt_id)?.name ?? gate.prozessobjekt_id
              }
              beischrift={t(`gate.typ.${gate.gate_typ}` as never)}
              aktion={
                <Abzeichen ton="gelb">{t(`gate.status.${gate.status}` as never)}</Abzeichen>
              }
            >
              <Werteliste
                eintraege={[
                  {
                    beschriftung: t('gate.ausloeser'),
                    wert:
                      gate.ausloeser === null
                        ? '—'
                        : t(`gate.ausloeser.${gate.ausloeser}` as never),
                  },
                  { beschriftung: t('gate.begruendung'), wert: gate.begruendung || '—' },
                ]}
              />
              {/* Entscheiden darf ausschliesslich die Governance-Rolle. Ist
                  sie nicht da, gibt es hier gar keine Entscheidung — und die
                  Route prueft unabhaengig nach (Architektur 10.2). */}
              {darfEntscheiden && (
                <Feld
                  beschriftung={t('gate.kommentar')}
                  wert={kommentar}
                  aendern={(wert) => setKommentare((bisher) => ({ ...bisher, [gate.id]: wert }))}
                  hilfe={t('gate.ablehnungBegruendung')}
                />
              )}
              <div className="k-knopfreihe">
                {darfEntscheiden && (
                  <>
                    <Knopf
                      art="gefuellt"
                      onClick={() => entscheiden(gate.id, 'freigegeben')}
                      data-testid={`freigeben-${gate.id}`}
                    >
                      {t('gate.freigeben')}
                    </Knopf>
                    {/* Ohne Grund keine Ablehnung: wer abgelehnt wird, erfaehrt
                        sonst nur, dass es nicht weitergeht. */}
                    <Knopf
                      art="zerstoerend"
                      onClick={() => entscheiden(gate.id, 'abgelehnt')}
                      disabled={kommentar.trim() === ''}
                      data-testid={`ablehnen-${gate.id}`}
                    >
                      {t('gate.ablehnen')}
                    </Knopf>
                  </>
                )}
                <Link className="k-knopf" to={pfad(`/prozesse/${gate.prozessobjekt_id}`)}>
                  {t('gate.prozess')}
                </Link>
              </div>
            </Karte>
          );
        })
      )}
    </>
  );
}
