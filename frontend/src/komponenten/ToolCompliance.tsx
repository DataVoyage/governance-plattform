import { useEffect, useState, type FormEvent } from 'react';

import { ApiFehler, api } from '@/api/client';
import type { Compliance, ComplianceFarbe } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { Abzeichen, Feld, Gruppe, Hinweis, Karte, Knopf, Zeile, type Ton } from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

const FARBTON: Record<ComplianceFarbe, Ton> = {
  gruen: 'gruen',
  gelb: 'gelb',
  rot: 'rot',
};

/**
 * Compliance eines Tool-Objekts (Architektur 8.6, Leitdokument A.13).
 *
 * Oben der **gerechnete** Zustand: der Server misst den Erlaubnisrahmen und
 * alle sechs Verbote aus Schicht 2 und sagt, welche Farbe daraus folgt. Bis
 * E-64 wählte sie ein Mensch aus einer Liste — er konnte also etwas anderes
 * eintragen, als der Sachstand hergab.
 *
 * Darunter die Zeitreihe: was gemeldet und wie geschlossen wurde, mit Datum
 * und Namen. Und ein einziger Knopf, für das eine, was nur ein Mensch
 * beisteuern kann — die Beobachtung. Läuft schon ein ungeklärter Vorgang,
 * passiert nichts: dieselbe Abweichung zweimal zu melden ist dieselbe.
 */
export function ToolCompliance({ toolId }: { toolId: string }) {
  const { t } = useSprache();
  const { token } = useSitzung();
  const [stand, setStand] = useState<Compliance | null>(null);
  const [begruendung, setBegruendung] = useState('');
  const [hinweis, setHinweis] = useState<string | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);

  useEffect(() => {
    if (token === null) return;
    api
      .compliance(token, toolId)
      .then(setStand)
      .catch(() => setFehler(t('app.fehler')));
  }, [token, toolId, t]);

  async function melden(ereignis: FormEvent) {
    ereignis.preventDefault();
    if (token === null) return;
    setFehler(null);
    setHinweis(null);
    try {
      const meldung = await api.abweichungMelden(token, toolId, begruendung);
      setBegruendung('');
      if (meldung.zustand === null) {
        setHinweis(t('compliance.laeuftSchon'));
        return;
      }
      setStand(await api.compliance(token, toolId));
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  if (stand === null) {
    return (
      <Karte titel={t('compliance.titel')} beischrift={t('compliance.hinweis')}>
        {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}
      </Karte>
    );
  }

  return (
    <Karte titel={t('compliance.titel')} beischrift={t('compliance.hinweis')}>
      {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}

      {/* Der Zustand von jetzt — gemessen, nicht gemeldet. */}
      <div className="k-zustandskopf">
        <Abzeichen ton={FARBTON[stand.farbe]}>
          <span data-testid="aktueller-zustand">
            {t(`compliance.farbe.${stand.farbe}` as never)}
          </span>
        </Abzeichen>
        <span className="beischrift" data-testid="zustand-grund">
          {stand.offene_abweichungen.length === 0
            ? t(`compliance.grund.${stand.farbe}` as never)
            : t('compliance.grund.gemessen').replace(
                '{elemente}',
                stand.offene_abweichungen.join(', '),
              )}
        </span>
      </div>

      {stand.verlauf.length === 0 ? (
        <p className="leerhinweis">{t('compliance.leer')}</p>
      ) : (
        <Gruppe etikett={t('compliance.verlauf')}>
          {stand.verlauf.map((zustand) => (
            <Zeile
              key={zustand.id}
              haupt={
                <Abzeichen ton={FARBTON[zustand.farbe]}>
                  {t(`compliance.farbe.${zustand.farbe}` as never)}
                </Abzeichen>
              }
              zweitzeile={zustand.begruendung || undefined}
              wert={zustand.festgestellt_am.slice(0, 10)}
            />
          ))}
        </Gruppe>
      )}

      {hinweis !== null && <Hinweis art="information">{hinweis}</Hinweis>}

      <form onSubmit={melden}>
        <Feld
          beschriftung={t('compliance.beobachtung')}
          hilfe={t('compliance.beobachtung.hilfe')}
          wert={begruendung}
          aendern={setBegruendung}
          pflicht
        />
        <div className="formularfuss">
          <Knopf type="submit" art="gefuellt" data-testid="abweichung-melden">
            {t('compliance.melden')}
          </Knopf>
        </div>
      </form>
    </Karte>
  );
}
