import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type { DatenObjekt, Datenkategorie, Fachbereich, Prozess } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import {
  Abzeichen,
  Auswahl,
  Blatt,
  Feld,
  Gruppe,
  Hinweis,
  Knopf,
  Ladeschimmer,
  Leerzustand,
  Seitenkopf,
  Suchfeld,
  ZeileVerweis,
  type Ton,
} from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

/** Die fünf Kategorien aus Leitdokument A.7, nach Schutzbedarf sortiert. */
export const KATEGORIEN: Datenkategorie[] = [
  'oeffentlich',
  'intern',
  'vertraulich',
  'personenbezogen',
  'besondere_kategorie',
];

export const KATEGORIE_TON: Record<Datenkategorie, Ton> = {
  oeffentlich: 'gruen',
  intern: 'neutral',
  vertraulich: 'gelb',
  personenbezogen: 'gelb',
  besondere_kategorie: 'rot',
};

/**
 * Datenobjekte (Architektur 8.3, Leitdokument A.7).
 *
 * Reifegrad 1 verlangt Name, Kategorie, datenhaltende Stelle und Quellsystem —
 * mehr nicht, und das in rund dreißig Sekunden. Die Stelle ist ein
 * Fachbereich, keine Person (docs/rollen-und-scopes.md, 7). Sie wird nicht
 * frei gewählt, sondern ergibt sich: aus dem gebenden Prozess, wenn ein
 * Prozess-Owner die Quelle als Output anlegt, oder aus dem eigenen Bereich,
 * wenn ein Datenobjekt-Owner sie erfasst. Das Formular bietet genau die Wege
 * an, die der Angemeldete hat.
 */
export function DatenobjektListe() {
  const { t, pfad } = useSprache();
  const { token, profil, hatRolle } = useSitzung();
  const [datenobjekte, setDatenobjekte] = useState<DatenObjekt[] | null>(null);
  const [fachbereiche, setFachbereiche] = useState<Fachbereich[]>([]);
  /** Die Bereiche, in denen der Angemeldete Datenobjekt-Owner ist — vom Server. */
  const [eigeneFachbereiche, setEigeneFachbereiche] = useState<Fachbereich[]>([]);
  const [prozesse, setProzesse] = useState<Prozess[]>([]);
  const [suche, setSuche] = useState('');
  const [blattOffen, setBlattOffen] = useState(false);
  const [fehler, setFehler] = useState<string | null>(null);

  const [name, setName] = useState('');
  const [kategorie, setKategorie] = useState('');
  const [fachbereich, setFachbereich] = useState('');
  const [gebender, setGebender] = useState('');
  const [quellsystem, setQuellsystem] = useState('');

  useEffect(() => {
    if (token === null) return;
    Promise.all([
      api.datenobjekte(token),
      api.fachbereiche(token).catch(() => [] as Fachbereich[]),
      // Nicht aus dem Profil ableiten: welche Bereiche wählbar sind, rechnet
      // der Server — sonst stünde die Regel zweimal da (E-53).
      api.fachbereiche(token, 'datenobjekt_owner').catch(() => [] as Fachbereich[]),
      api.prozesse(token).catch(() => [] as Prozess[]),
    ])
      .then(([alle, bereiche, meine, eigene]) => {
        setDatenobjekte(alle);
        setFachbereiche(bereiche);
        setEigeneFachbereiche(meine);
        setProzesse(eigene);
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, t]);

  /** Prozesse, die der Angemeldete schreiben darf — nur die geben Output. */
  const gebendeProzesse = useMemo(() => prozesse.filter((p) => p.rechte.bearbeiten), [prozesse]);
  const kannAnlegen = eigeneFachbereiche.length > 0 || gebendeProzesse.length > 0;

  useEffect(() => {
    if (fachbereich === '' && eigeneFachbereiche.length === 1) {
      setFachbereich(eigeneFachbereiche[0].id);
    }
  }, [eigeneFachbereiche, fachbereich]);

  const fachbereichName = (id: string | null) =>
    fachbereiche.find((f) => f.id === id)?.name ?? null;

  async function anlegen(ereignis: FormEvent) {
    ereignis.preventDefault();
    if (token === null) return;
    try {
      const angelegt = await api.datenobjektAnlegen(token, {
        name,
        kategorie: kategorie === '' ? null : (kategorie as Datenkategorie),
        fachbereich_id: gebender !== '' || fachbereich === '' ? null : fachbereich,
        prozessobjekt_id: gebender === '' ? null : gebender,
        quellsystem: quellsystem === '' ? null : quellsystem,
      });
      setDatenobjekte((bisher) => [...(bisher ?? []), angelegt]);
      setName('');
      setKategorie('');
      setGebender('');
      setQuellsystem('');
      setBlattOffen(false);
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  if (fehler !== null && datenobjekte === null) return <Hinweis art="fehler">{fehler}</Hinweis>;
  if (datenobjekte === null) return <Ladeschimmer beschriftung={t('app.laden')} zeilen={4} />;

  const begriff = suche.trim().toLowerCase();
  const treffer = datenobjekte.filter(
    (d) =>
      d.name.toLowerCase().includes(begriff) ||
      (d.quellsystem ?? '').toLowerCase().includes(begriff),
  );

  const anlegenKnopf = kannAnlegen ? (
    <Knopf art="gefuellt" onClick={() => setBlattOffen(true)}>
      {t('asset.datenobjekte.neu')}
    </Knopf>
  ) : undefined;

  return (
    <>
      <Seitenkopf
        titel={t('asset.datenobjekte.titel')}
        untertitel={t('asset.datenobjekte.hinweis')}
        aktionen={datenobjekte.length === 0 ? undefined : anlegenKnopf}
      />

      {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}
      {!kannAnlegen && profil !== null && (
        <Hinweis art="information">{t('asset.anlegen.keinWeg')}</Hinweis>
      )}

      {datenobjekte.length === 0 ? (
        <Leerzustand
          zeichen="◇"
          titel={t('asset.datenobjekte.leer')}
          text={t('asset.datenobjekte.hinweis')}
          aktion={anlegenKnopf}
        />
      ) : (
        <>
          <div className="listenkopf">
            <Suchfeld beschriftung={t('asset.feld.name')} wert={suche} aendern={setSuche} />
          </div>
          <Gruppe>
            {treffer.map((datenobjekt) => (
              <ZeileVerweis
                key={datenobjekt.id}
                ziel={pfad(`/datenobjekte/${datenobjekt.id}`)}
                haupt={datenobjekt.name}
                zweitzeile={[
                  datenobjekt.quellsystem ?? t('asset.quellsystem.leer'),
                  fachbereichName(datenobjekt.fachbereich_id),
                ]
                  .filter(Boolean)
                  .join(' · ')}
                wert={
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
            ))}
          </Gruppe>
        </>
      )}

      {blattOffen && (
        <Blatt
          titel={t('asset.datenobjekte.neu')}
          beischrift={t('asset.reifegrad1')}
          schliessen={() => setBlattOffen(false)}
        >
          <form onSubmit={anlegen}>
            <Feld beschriftung={t('asset.feld.name')} wert={name} aendern={setName} pflicht />
            <Auswahl
              beschriftung={t('asset.feld.kategorie')}
              wert={kategorie}
              aendern={setKategorie}
              leertext={t('asset.kategorie.keine')}
              optionen={KATEGORIEN.map((k) => ({
                wert: k,
                text: `${t(`kategorie.${k}` as never)} — ${t(`kategorie.anker.${k}` as never)}`,
              }))}
              hilfe={t('asset.kategorie.hilfe')}
            />
            <p className="k-hilfe">{t('asset.anlegen.weg')}</p>
            {gebendeProzesse.length > 0 && (
              <Auswahl
                beschriftung={t('asset.feld.gebenderProzess')}
                wert={gebender}
                aendern={setGebender}
                leertext="—"
                optionen={gebendeProzesse.map((p) => ({ wert: p.id, text: p.name }))}
                hilfe={t('asset.gebenderProzess.hilfe')}
              />
            )}
            {eigeneFachbereiche.length > 0 && (
              <Auswahl
                beschriftung={t('asset.feld.fachbereich')}
                wert={gebender === '' ? fachbereich : ''}
                aendern={setFachbereich}
                leertext="—"
                optionen={eigeneFachbereiche.map((f) => ({ wert: f.id, text: f.name }))}
                hilfe={t('asset.fachbereich.hilfe')}
                gesperrt={
                  gebender !== '' || (eigeneFachbereiche.length === 1 && !hatRolle('governance'))
                }
              />
            )}
            <Feld
              beschriftung={t('asset.feld.quellsystem')}
              wert={quellsystem}
              aendern={setQuellsystem}
              hilfe={t('asset.quellsystem.hilfe')}
              hoechstlaenge={255}
            />
            <div className="formularfuss">
              <Knopf onClick={() => setBlattOffen(false)}>{t('prozess.abbrechen')}</Knopf>
              <Knopf type="submit" art="gefuellt">
                {t('asset.speichern')}
              </Knopf>
            </div>
          </form>
        </Blatt>
      )}

      <p className="leerhinweis">
        <Link to={pfad('/cockpit/datenobjekte_ohne_kategorie')}>
          {t('asset.datenobjekte.ohneKategorie')}
        </Link>
      </p>
    </>
  );
}
