import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type {
  Ausfallfolge,
  Kundenkreis,
  Nutzer,
  Organisationseinheit,
  ProzessEingabe,
} from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { useSitzung } from '@/zustand/Sitzung';

const KUNDENKREISE: Kundenkreis[] = ['persoenlich', 'team', 'bereich', 'unternehmen', 'extern'];
const AUSFALLFOLGEN: Ausfallfolge[] = ['keine', 'gering', 'spuerbar', 'kritisch'];

/**
 * Anlageformular mit genau den zehn Feldern aus Leitdokument A.5.
 *
 * Reichweite, Kritikalitaet und Mitbestimmungsflag fehlen hier bewusst: sie
 * werden serverseitig berechnet und erst in der Detailansicht gezeigt
 * (Architektur 8.1, Prinzip P-App-1 — kein Formularfeld ohne Grund).
 */
export function ProzessFormular() {
  const { t, pfad } = useSprache();
  const { token, profil } = useSitzung();
  const navigiere = useNavigate();

  const [nutzer, setNutzer] = useState<Nutzer[]>([]);
  const [intEinheiten, setIntEinheiten] = useState<Organisationseinheit[]>([]);
  const [landEinheiten, setLandEinheiten] = useState<Organisationseinheit[]>([]);
  const [fehler, setFehler] = useState<string | null>(null);

  const [name, setName] = useState('');
  const [owner, setOwner] = useState('');
  const [stellvertretung, setStellvertretung] = useState('');
  const [prozessgeber, setProzessgeber] = useState('');
  const [supplier, setSupplier] = useState('');
  const [schritte, setSchritte] = useState('');
  const [ergebnis, setErgebnis] = useState('');
  const [kundenkreis, setKundenkreis] = useState<Kundenkreis>('team');
  const [ausfallfolge, setAusfallfolge] = useState<Ausfallfolge>('keine');
  const [umsetzungen, setUmsetzungen] = useState<string[]>([]);

  useEffect(() => {
    if (token === null) return;
    api
      .organisationseinheiten(token)
      .then((alle) => {
        setIntEinheiten(alle.filter((e) => e.ebene === 'INT'));
        setLandEinheiten(alle.filter((e) => e.ebene === 'LAND'));
      })
      .catch(() => setFehler(t('app.fehler')));
    api.nutzer(token).then(setNutzer).catch(() => setNutzer([]));
  }, [token, t]);

  useEffect(() => {
    if (owner === '' && profil !== null) setOwner(profil.id);
  }, [profil, owner]);

  async function absenden(ereignis: FormEvent) {
    ereignis.preventDefault();
    setFehler(null);
    if (token === null) return;
    const eingabe: ProzessEingabe = {
      name,
      owner_user_id: owner,
      stellvertretung_user_id: stellvertretung,
      prozessgeber_org_id: prozessgeber,
      supplier,
      input_datenobjekt_ids: [],
      process_steps: schritte,
      output: ergebnis,
      customer: kundenkreis,
      ausfallfolge,
      umsetzung_land_org_ids: umsetzungen,
    };
    try {
      const angelegt = await api.prozessAnlegen(token, eingabe);
      navigiere(pfad(`/prozesse/${angelegt.id}`));
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  const nutzerAuswahl = nutzer.length > 0 ? nutzer : profil ? [profil as unknown as Nutzer] : [];

  return (
    <form className="formular" onSubmit={absenden}>
      <h1>{t('prozess.liste.neu')}</h1>

      <label htmlFor="name">{t('prozess.feld.name')}</label>
      <input id="name" required value={name} onChange={(e) => setName(e.target.value)} />

      <label htmlFor="owner">{t('prozess.feld.owner')}</label>
      <select id="owner" required value={owner} onChange={(e) => setOwner(e.target.value)}>
        <option value="">—</option>
        {nutzerAuswahl.map((n) => (
          <option key={n.id} value={n.id}>
            {n.name}
          </option>
        ))}
      </select>

      <label htmlFor="stellvertretung">{t('prozess.feld.stellvertretung')}</label>
      <select
        id="stellvertretung"
        required
        value={stellvertretung}
        onChange={(e) => setStellvertretung(e.target.value)}
      >
        <option value="">—</option>
        {nutzerAuswahl.map((n) => (
          <option key={n.id} value={n.id}>
            {n.name}
          </option>
        ))}
      </select>
      <small>{t('prozess.stellvertretungPflicht')}</small>

      <label htmlFor="prozessgeber">{t('prozess.feld.prozessgeber')}</label>
      <select
        id="prozessgeber"
        required
        value={prozessgeber}
        onChange={(e) => setProzessgeber(e.target.value)}
      >
        <option value="">—</option>
        {intEinheiten.map((e) => (
          <option key={e.id} value={e.id}>
            {e.id.slice(0, 8)}
          </option>
        ))}
      </select>

      <label htmlFor="supplier">{t('prozess.feld.supplier')}</label>
      <input id="supplier" value={supplier} onChange={(e) => setSupplier(e.target.value)} />

      <label htmlFor="schritte">{t('prozess.feld.processSteps')}</label>
      <textarea id="schritte" value={schritte} onChange={(e) => setSchritte(e.target.value)} />

      <label htmlFor="ergebnis">{t('prozess.feld.output')}</label>
      <input id="ergebnis" value={ergebnis} onChange={(e) => setErgebnis(e.target.value)} />

      <label htmlFor="kundenkreis">{t('prozess.feld.customer')}</label>
      <select
        id="kundenkreis"
        value={kundenkreis}
        onChange={(e) => setKundenkreis(e.target.value as Kundenkreis)}
      >
        {KUNDENKREISE.map((k) => (
          <option key={k} value={k}>
            {t(`kundenkreis.${k}` as never)}
          </option>
        ))}
      </select>

      <label htmlFor="ausfallfolge">{t('prozess.feld.ausfallfolge')}</label>
      <select
        id="ausfallfolge"
        value={ausfallfolge}
        onChange={(e) => setAusfallfolge(e.target.value as Ausfallfolge)}
      >
        {AUSFALLFOLGEN.map((a) => (
          <option key={a} value={a}>
            {t(`ausfallfolge.${a}` as never)}
          </option>
        ))}
      </select>

      <fieldset>
        <legend>{t('prozess.umsetzungen.titel')}</legend>
        {landEinheiten.map((e) => (
          <label key={e.id} htmlFor={`umsetzung-${e.id}`}>
            <input
              id={`umsetzung-${e.id}`}
              type="checkbox"
              checked={umsetzungen.includes(e.id)}
              onChange={(ereignis) =>
                setUmsetzungen((bisher) =>
                  ereignis.target.checked
                    ? [...bisher, e.id]
                    : bisher.filter((vorhanden) => vorhanden !== e.id),
                )
              }
            />
            {`LAND-${e.land_code}`}
          </label>
        ))}
      </fieldset>

      <button type="submit">{t('prozess.speichern')}</button>
      {fehler !== null && <p role="alert">{fehler}</p>}
    </form>
  );
}
