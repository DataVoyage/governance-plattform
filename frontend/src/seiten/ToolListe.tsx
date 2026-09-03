import { useEffect, useState, type FormEvent } from 'react';

import { ApiFehler, api } from '@/api/client';
import type {
  Fachbereich,
  Lauftyp,
  Person,
  Organisationseinheit,
  Technologie,
  ToolObjekt,
  Wirkungsart,
} from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { orgBezeichnung } from '@/nutzen/bezeichnungen';
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

export const LAUFTYPEN: Lauftyp[] = ['interaktiv', 'getriggert', 'geplant'];

export const WIRKUNGSART_TON: Record<Wirkungsart, Ton> = {
  veraendernd: 'rot',
  gestaltend: 'gruen',
};

/** Ergänzt die Auswahl um einen Bestandswert, der nicht in der Liste steht. */
export function mitBestandswert(
  optionen: { wert: string; text: string }[],
  wert: string | null,
): { wert: string; text: string }[] {
  if (wert === null || wert === '' || optionen.some((o) => o.wert === wert)) return optionen;
  return [...optionen, { wert, text: wert }];
}

/**
 * Tool-Objekte (Leitdokument A.6, Architektur 8.3).
 *
 * Die Anlage fragt genau das ab, was A.6 als „deklariert" führt — technischer
 * Owner, Stellvertretung, Technologie, Organisationseinheit und Lauftyp. Alles
 * Übrige kommt aus der Telemetrie oder wird attestiert; dafür ist die
 * Detailseite zuständig.
 */
export function ToolListe() {
  const { t, pfad } = useSprache();
  const { token, profil } = useSitzung();
  const [tools, setTools] = useState<ToolObjekt[] | null>(null);
  const [nutzer, setNutzer] = useState<Person[]>([]);
  const [einheiten, setEinheiten] = useState<Organisationseinheit[]>([]);
  const [fachbereiche, setFachbereiche] = useState<Fachbereich[]>([]);
  const [suche, setSuche] = useState('');
  const [blattOffen, setBlattOffen] = useState(false);
  const [fehler, setFehler] = useState<string | null>(null);

  const [name, setName] = useState('');
  const [owner, setOwner] = useState('');
  const [stellvertretung, setStellvertretung] = useState('');
  const [technologie, setTechnologie] = useState('');
  const [technologien, setTechnologien] = useState<Technologie[]>([]);
  const [organisationseinheit, setOrganisationseinheit] = useState('');
  const [lauftyp, setLauftyp] = useState('');

  useEffect(() => {
    if (token === null) return;
    Promise.all([
      api.tools(token),
      api
        .organisationseinheiten(token, 'technischer_owner')
        .catch(() => [] as Organisationseinheit[]),
      api.fachbereiche(token).catch(() => [] as Fachbereich[]),
      // Die Technologien kommen vom Server: Tool-Auswahl und
      // Technologiematrix müssen dieselbe Liste benutzen, sonst zeigt die
      // eine einen Namen und die andere einen Schlüssel.
      api.technologien(token).catch(() => [] as Technologie[]),
    ])
      .then(([alle, orgs, bereiche, techs]) => {
        setTools(alle);
        setEinheiten(orgs);
        setFachbereiche(bereiche);
        setTechnologien(techs);
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, t]);

  async function anlegen(ereignis: FormEvent) {
    ereignis.preventDefault();
    if (token === null) return;
    try {
      const angelegt = await api.toolAnlegen(token, {
        name,
        technischer_owner_user_id: owner === '' ? null : owner,
        stellvertretung_user_id: stellvertretung === '' ? null : stellvertretung,
        technologie: technologie === '' ? null : technologie,
        organisationseinheit_id: organisationseinheit === '' ? null : organisationseinheit,
        lauftyp: lauftyp === '' ? null : (lauftyp as Lauftyp),
      });
      setTools((bisher) => [...(bisher ?? []), angelegt]);
      setName('');
      setTechnologie('');
      setLauftyp('');
      setBlattOffen(false);
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  useEffect(() => {
    if (organisationseinheit === '' && einheiten.length === 1) {
      setOrganisationseinheit(einheiten[0].id);
    }
  }, [einheiten, organisationseinheit]);

  useEffect(() => {
    if (token === null || organisationseinheit === '') {
      setNutzer([]);
      return;
    }
    api
      .personen(token, 'technischer_owner', { organisationseinheitId: organisationseinheit })
      .then(setNutzer)
      .catch(() => setNutzer([]));
  }, [token, organisationseinheit]);

  if (fehler !== null && tools === null) return <Hinweis art="fehler">{fehler}</Hinweis>;
  if (tools === null) return <Ladeschimmer beschriftung={t('app.laden')} zeilen={4} />;

  const begriff = suche.trim().toLowerCase();
  const treffer = tools.filter(
    (tool) =>
      tool.name.toLowerCase().includes(begriff) ||
      (tool.technologie ?? '').toLowerCase().includes(begriff),
  );

  const anlegenKnopf = (
    <Knopf art="gefuellt" onClick={() => setBlattOffen(true)}>
      {t('asset.tools.neu')}
    </Knopf>
  );

  /* Wählbar ist, wer an der gewählten Einheit technischer Owner ist — deshalb
   * erst die Einheit, dann die Personen (rollen-und-scopes.md, 6). */
  const auswahl =
    profil !== null && !nutzer.some((n) => n.id === profil.id) ? [profil, ...nutzer] : nutzer;
  const personen = auswahl.map((n) => ({ wert: n.id, text: n.name }));

  return (
    <>
      <Seitenkopf
        titel={t('asset.tools.titel')}
        untertitel={t('tool.hinweis')}
        aktionen={tools.length === 0 ? undefined : anlegenKnopf}
      />

      {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}

      {tools.length === 0 ? (
        <Leerzustand
          zeichen="◈"
          titel={t('asset.tools.leer')}
          text={t('tool.hinweis')}
          aktion={anlegenKnopf}
        />
      ) : (
        <>
          <div className="listenkopf">
            <Suchfeld
              beschriftung={t('tool.tools.suche')}
              platzhalter={t('tool.tools.platzhalter')}
              wert={suche}
              aendern={setSuche}
            />
          </div>
          <Gruppe>
            {treffer.map((tool) => (
              <ZeileVerweis
                key={tool.id}
                ziel={pfad(`/tools/${tool.id}`)}
                haupt={tool.name}
                zweitzeile={[
                  technologien.find((o) => o.schluessel === tool.technologie)?.name ??
                    tool.technologie ??
                    t('tool.technologie.keine'),
                  tool.lauftyp === null ? null : t(`tool.lauftyp.${tool.lauftyp}` as never),
                ]
                  .filter(Boolean)
                  .join(' · ')}
                wert={
                  <>
                    {!tool.attestierung_vollstaendig && (
                      <Abzeichen ton="gelb" zeichen="!">
                        {t('tool.attestierungFehlt')}
                      </Abzeichen>
                    )}
                    {tool.wirkungsart !== null && (
                      <Abzeichen ton={WIRKUNGSART_TON[tool.wirkungsart]}>
                        {t(`tool.wirkungsart.${tool.wirkungsart}` as never)}
                      </Abzeichen>
                    )}
                    {tool.geerbt.tier !== null && (
                      <Abzeichen>{`Tier ${tool.geerbt.tier}`}</Abzeichen>
                    )}
                  </>
                }
              />
            ))}
          </Gruppe>
        </>
      )}

      {blattOffen && (
        <Blatt
          titel={t('asset.tools.neu')}
          beischrift={t('tool.stammdaten.hinweis')}
          schliessen={() => setBlattOffen(false)}
        >
          <form onSubmit={anlegen}>
            <Feld beschriftung={t('asset.feld.name')} wert={name} aendern={setName} pflicht />
            <Auswahl
              beschriftung={t('tool.feld.owner')}
              wert={owner}
              aendern={setOwner}
              leertext="—"
              optionen={personen}
              hilfe={t('tool.owner.hilfe')}
            />
            <Auswahl
              beschriftung={t('tool.feld.stellvertretung')}
              wert={stellvertretung}
              aendern={setStellvertretung}
              leertext="—"
              optionen={personen}
            />
            <Auswahl
              beschriftung={t('asset.feld.technologie')}
              wert={technologie}
              aendern={setTechnologie}
              leertext={t('tool.technologie.keine')}
              optionen={technologien.map((o) => ({ wert: o.schluessel, text: o.name }))}
            />
            <Auswahl
              beschriftung={t('tool.feld.organisationseinheit')}
              wert={organisationseinheit}
              aendern={setOrganisationseinheit}
              leertext="—"
              optionen={einheiten.map((einheit) => ({
                wert: einheit.id,
                text: orgBezeichnung(einheit, fachbereiche),
              }))}
            />
            <Auswahl
              beschriftung={t('tool.feld.lauftyp')}
              wert={lauftyp}
              aendern={setLauftyp}
              leertext={t('tool.lauftyp.keiner')}
              optionen={LAUFTYPEN.map((typ) => ({
                wert: typ,
                text: t(`tool.lauftyp.${typ}` as never),
              }))}
              hilfe={t('tool.lauftyp.hilfe')}
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
    </>
  );
}
