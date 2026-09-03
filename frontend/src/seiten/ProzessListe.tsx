import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { api } from '@/api/client';
import type { Fachbereich, Organisationseinheit, Prozess } from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { orgBezeichnung } from '@/nutzen/bezeichnungen';
import {
  Abzeichen,
  Gruppe,
  Hinweis,
  Ladeschimmer,
  Leerzustand,
  Seitenkopf,
  Suchfeld,
  ZeileVerweis,
  type Ton,
} from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

function tierTon(tier: number | null): Ton {
  if (tier === 3) return 'rot';
  if (tier === 2) return 'gelb';
  return 'neutral';
}

export function ProzessListe() {
  const { t, pfad } = useSprache();
  const { token, hatRolle } = useSitzung();
  const [prozesse, setProzesse] = useState<Prozess[] | null>(null);
  const [einheiten, setEinheiten] = useState<Organisationseinheit[]>([]);
  const [fachbereiche, setFachbereiche] = useState<Fachbereich[]>([]);
  const [suche, setSuche] = useState('');
  const [fehler, setFehler] = useState<string | null>(null);

  useEffect(() => {
    if (token === null) return;
    Promise.all([api.prozesse(token), api.organisationseinheiten(token), api.fachbereiche(token)])
      .then(([alle, orgs, bereiche]) => {
        setProzesse(alle);
        setEinheiten(orgs);
        setFachbereiche(bereiche);
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, t]);

  if (fehler !== null) return <Hinweis art="fehler">{fehler}</Hinweis>;
  if (prozesse === null) return <Ladeschimmer beschriftung={t('app.laden')} zeilen={4} />;

  // Anlegen darf, wer irgendwo Prozess-Owner ist. In welchem Bereich, prüft
  // der Server beim Speichern — hier geht es nur darum, niemandem ein Formular
  // hinzustellen, das er nicht abschicken kann.
  const darfAnlegen = hatRolle('prozess_owner') || hatRolle('governance');

  const begriff = suche.trim().toLowerCase();
  const treffer = prozesse.filter((p) => p.name.toLowerCase().includes(begriff));

  return (
    <>
      <Seitenkopf
        titel={t('prozess.liste.titel')}
        aktionen={
          prozesse.length === 0 || !darfAnlegen ? undefined : (
            <Link className="k-knopf k-knopf--gefuellt" to={pfad('/prozesse/neu')}>
              {t('prozess.liste.neu')}
            </Link>
          )
        }
      />

      {prozesse.length === 0 ? (
        <Leerzustand
          zeichen="▤"
          titel={t('prozess.liste.leer')}
          text={darfAnlegen ? t('prozess.hilfe.nachgelagert') : t('rechte.liste.leer')}
          aktion={
            darfAnlegen ? (
              <Link className="k-knopf k-knopf--gefuellt" to={pfad('/prozesse/neu')}>
                {t('prozess.liste.neu')}
              </Link>
            ) : undefined
          }
        />
      ) : (
        <>
          <div className="listenkopf">
            <Suchfeld beschriftung={t('prozess.feld.name')} wert={suche} aendern={setSuche} />
          </div>
          <Gruppe>
            {treffer.map((p) => (
              <ZeileVerweis
                key={p.id}
                ziel={pfad(`/prozesse/${p.id}`)}
                haupt={p.name}
                zweitzeile={`${orgBezeichnung(
                  einheiten.find((e) => e.id === p.prozessgeber_org_id),
                  fachbereiche,
                )} · ${t(`status.${p.status}` as never)}`}
                wert={
                  <>
                    {p.mitbestimmung_flag && <Abzeichen ton="lila">MB</Abzeichen>}
                    <Abzeichen>{`${t('prozess.feld.kritikalitaet')} ${p.kritikalitaet}`}</Abzeichen>
                    {p.tier !== null && (
                      <Abzeichen ton={tierTon(p.tier)}>{`Tier ${p.tier}`}</Abzeichen>
                    )}
                  </>
                }
              />
            ))}
          </Gruppe>
        </>
      )}
    </>
  );
}
