import { useEffect, useState, type FormEvent } from 'react';

import { ApiFehler, api } from '@/api/client';
import type {
  ComplianceFarbe,
  ComplianceZustand,
  Schicht2Verbot,
  Schicht2VerbotEintrag,
} from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { Abzeichen, Auswahl, Feld, Gruppe, Hinweis, Karte, Knopf, Zeile, type Ton } from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

const FARBEN: ComplianceFarbe[] = ['gruen', 'gelb', 'rot'];

const FARBTON: Record<ComplianceFarbe, Ton> = {
  gruen: 'gruen',
  gelb: 'gelb',
  rot: 'rot',
};

/**
 * Compliance-Zeitreihe eines Tool-Objekts (Architektur 8.6).
 *
 * Der aktuelle Zustand ist der oberste Eintrag; ältere bleiben stehen, damit
 * der Verlauf einer Abweichung nachvollziehbar bleibt. Eine rote Meldung
 * eröffnet serverseitig einen Lenkungsvorgang — die Oberfläche weist darauf
 * hin, entscheidet es aber nicht.
 *
 * Wer einen Verstoß gegen Schicht 2 meldet, wählt ihn aus der abschließenden
 * Liste der sechs Verbote (A.13.2). Ein siebter, freier Grund ist nicht
 * wählbar: eine Liste, die sich ergänzen lässt, wäre keine.
 */
export function ToolCompliance({ toolId }: { toolId: string }) {
  const { t } = useSprache();
  const { token } = useSitzung();
  const [verlauf, setVerlauf] = useState<ComplianceZustand[]>([]);
  const [verbote, setVerbote] = useState<Schicht2VerbotEintrag[]>([]);
  const [farbe, setFarbe] = useState<ComplianceFarbe>('gruen');
  const [begruendung, setBegruendung] = useState('');
  const [abweichung, setAbweichung] = useState('');
  const [verbot, setVerbot] = useState('');
  const [fehler, setFehler] = useState<string | null>(null);

  useEffect(() => {
    if (token === null) return;
    Promise.all([api.compliance(token, toolId), api.schicht2Verbote(token)])
      .then(([eintraege, liste]) => {
        setVerlauf(eintraege);
        setVerbote(liste);
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, toolId, t]);

  async function melden(ereignis: FormEvent) {
    ereignis.preventDefault();
    if (token === null) return;
    setFehler(null);
    try {
      const meldung = await api.complianceMelden(token, toolId, {
        farbe,
        begruendung,
        abweichung_art: abweichung || null,
        schicht2_verbot: farbe === 'rot' && verbot ? (verbot as Schicht2Verbot) : null,
      });
      setVerlauf((bisher) => [meldung.zustand, ...bisher]);
      setBegruendung('');
      setAbweichung('');
      setVerbot('');
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  /** Woran der Eintrag lag — mit Namen, nie mit dem technischen Schlüssel. */
  const anlass = (zustand: ComplianceZustand) =>
    [
      zustand.begruendung,
      zustand.schicht2_verbot === null
        ? zustand.abweichung_art
        : t(`schicht2.${zustand.schicht2_verbot}` as never),
    ]
      .filter(Boolean)
      .join(' · ') || undefined;

  return (
    <Karte titel={t('compliance.titel')} beischrift={t('compliance.hinweis')}>
      {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}

      {verlauf.length === 0 ? (
        <p className="leerhinweis">{t('compliance.leer')}</p>
      ) : (
        <Gruppe>
          {verlauf.map((zustand, nummer) => (
            <Zeile
              key={zustand.id}
              pruefkennung={nummer === 0 ? 'aktueller-zustand' : undefined}
              haupt={
                <Abzeichen ton={FARBTON[zustand.farbe]}>
                  {t(`compliance.farbe.${zustand.farbe}` as never)}
                </Abzeichen>
              }
              zweitzeile={anlass(zustand)}
              wert={zustand.festgestellt_am.slice(0, 10)}
            />
          ))}
        </Gruppe>
      )}

      <form onSubmit={melden}>
        <Auswahl
          beschriftung={t('compliance.melden')}
          wert={farbe}
          aendern={(wert) => setFarbe(wert as ComplianceFarbe)}
          optionen={FARBEN.map((wert) => ({
            wert,
            text: t(`compliance.farbe.${wert}` as never),
          }))}
          hilfe={farbe === 'rot' ? t('compliance.rotHinweis') : undefined}
        />
        {farbe === 'rot' && (
          <Auswahl
            beschriftung={t('compliance.schicht2')}
            wert={verbot}
            aendern={setVerbot}
            hilfe={t('compliance.schicht2Hilfe')}
            optionen={[
              { wert: '', text: t('compliance.schicht2.keiner') },
              ...verbote.map((eintrag) => ({
                wert: eintrag.schluessel,
                text: t(`schicht2.${eintrag.schluessel}` as never),
              })),
            ]}
          />
        )}
        {farbe === 'rot' && verbot !== '' && (
          <Hinweis art="warnung">{t('compliance.schicht2Folge')}</Hinweis>
        )}
        <Feld
          beschriftung={t('compliance.begruendung')}
          wert={begruendung}
          aendern={setBegruendung}
        />
        <Feld
          beschriftung={t('compliance.abweichung')}
          wert={abweichung}
          aendern={setAbweichung}
        />
        <div className="formularfuss">
          <Knopf type="submit" art="gefuellt">
            {t('compliance.melden')}
          </Knopf>
        </div>
      </form>
    </Karte>
  );
}
