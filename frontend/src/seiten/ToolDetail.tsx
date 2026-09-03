import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type {
  Ausfuehrungsidentitaet,
  Datennutzung,
  DatenobjektKatalog,
  Deckung,
  Fachbereich,
  Lauftyp,
  Person,
  Organisationseinheit,
  Prozess,
  Technologie,
  ToolObjekt,
  Zugriffsart,
} from '@/api/typen';
import { Erlaubnisrahmen } from '@/komponenten/Erlaubnisrahmen';
import { Klassenbefund } from '@/komponenten/Klassenbefund';
import { ToolCompliance } from '@/komponenten/ToolCompliance';
import { useSprache } from '@/i18n/SprachKontext';
import { orgBezeichnung } from '@/nutzen/bezeichnungen';
import { KATEGORIE_TON } from '@/seiten/DatenobjektListe';
import { LAUFTYPEN, WIRKUNGSART_TON, mitBestandswert } from '@/seiten/ToolListe';
import {
  Abzeichen,
  Auswahl,
  Feld,
  Gruppe,
  Hinweis,
  Karte,
  Knopf,
  Ladeschimmer,
  ReferenzWaehler,
  Seitenkopf,
  SegmentierteSteuerung,
  Umschalter,
  Werteliste,
  Zeile,
  ZeileVerweis,
} from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

const ZUGRIFFSARTEN: Zugriffsart[] = ['lesen', 'schreiben', 'lesen_schreiben'];

/**
 * Die Identitäten, die ein Tool erklären kann. Das geteilte Konto steht mit
 * dabei, obwohl A.13.2 Schicht 2 es organisationsweit verbietet: was nicht
 * erfasst werden kann, kann auch nicht gefunden werden.
 */
const IDENTITAETEN: Ausfuehrungsidentitaet[] = [
  'persoenlich',
  'benannter_dienst',
  'geteiltes_konto',
];

/** Die drei Attestierungen aus Leitdokument A.6, in ihrer Reihenfolge. */
const ATTESTIERUNGEN = [
  { feld: 'attest_entscheidung_ueber_personen', text: 'tool.attest.frage1' },
  { feld: 'attest_mensch_dazwischen', text: 'tool.attest.frage2' },
  { feld: 'attest_undeklarierte_quellen', text: 'tool.attest.frage3' },
] as const;

type Antwort = '' | 'ja' | 'nein';

function alsAntwort(wert: boolean | null): Antwort {
  if (wert === null) return '';
  return wert ? 'ja' : 'nein';
}

/**
 * Das Tool-Objekt (Leitdokument A.6).
 *
 * Die Seite folgt der Reihenfolge, in der das Leitdokument argumentiert: erst
 * die drei Erklärungen, die kein System liefern kann, dann der Zweck, in
 * dessen Rahmen das Tool arbeitet, und erst daraus die geerbte Einstufung.
 * Ohne Attestierung gibt es keine Prozesskante — das ist keine Formalie,
 * sondern die Bedingung dafür, dass die Triage „verändert oder gestaltet"
 * überhaupt eine Grundlage hat.
 */
export function ToolDetail() {
  const { id } = useParams();
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const [tool, setTool] = useState<ToolObjekt | null>(null);
  const [prozesse, setProzesse] = useState<Prozess[]>([]);
  const [nutzung, setNutzung] = useState<Datennutzung[]>([]);
  const [datenobjekte, setDatenobjekte] = useState<DatenobjektKatalog[]>([]);
  const [waehlbar, setWaehlbar] = useState<Organisationseinheit[]>([]);
  const [nutzer, setNutzer] = useState<Person[]>([]);
  const [fachbereiche, setFachbereiche] = useState<Fachbereich[]>([]);
  const [technologien, setTechnologien] = useState<Technologie[]>([]);
  const [antworten, setAntworten] = useState<Record<string, Antwort>>({});
  const [zugriffsart, setZugriffsart] = useState<Zugriffsart>('lesen');
  const [neuesZiel, setNeuesZiel] = useState('');
  const [stand, setStand] = useState(0);
  const [deckung, setDeckung] = useState<Deckung | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);

  const laden = useCallback(() => {
    if (token === null || id === undefined) return;
    Promise.all([
      api.tool(token, id),
      api.prozesse(token),
      api.toolDatennutzung(token, id).catch(() => [] as Datennutzung[]),
      api.datenobjektKatalog(token).catch(() => [] as DatenobjektKatalog[]),
      api
        .organisationseinheiten(token, 'technischer_owner')
        .catch(() => [] as Organisationseinheit[]),
      api.fachbereiche(token).catch(() => [] as Fachbereich[]),
      api.toolDeckung(token, id).catch(() => null),
      api.technologien(token).catch(() => [] as Technologie[]),
    ])
      .then(([geladen, alle, kanten, objekte, meine, bereiche, deckungsstand, techs]) => {
        setTool(geladen);
        setProzesse(alle);
        setNutzung(kanten);
        setDatenobjekte(objekte);
        setWaehlbar(meine);
        setFachbereiche(bereiche);
        setDeckung(deckungsstand);
        setTechnologien(techs);
        setAntworten({
          attest_entscheidung_ueber_personen: alsAntwort(
            geladen.attest_entscheidung_ueber_personen,
          ),
          attest_mensch_dazwischen: alsAntwort(geladen.attest_mensch_dazwischen),
          attest_undeklarierte_quellen: alsAntwort(geladen.attest_undeklarierte_quellen),
        });
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, id, t]);

  useEffect(laden, [laden]);

  async function fuehreAus(aktion: () => Promise<unknown>) {
    setFehler(null);
    try {
      await aktion();
      laden();
      setStand((bisher) => bisher + 1);
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  /* Wählbar ist, wer *an der Einheit dieses Tools* technischer Owner ist.
   * Zuvor lud die Seite die Nutzerverwaltung — für jede Fachrolle 403. */
  useEffect(() => {
    const anker = tool?.organisationseinheit_id;
    if (token === null || anker === null || anker === undefined) {
      setNutzer([]);
      return;
    }
    api
      .personen(token, 'technischer_owner', { organisationseinheitId: anker })
      .then(setNutzer)
      .catch(() => setNutzer([]));
  }, [token, tool?.organisationseinheit_id]);

  if (fehler !== null && tool === null) return <Hinweis art="fehler">{fehler}</Hinweis>;
  if (tool === null) return <Ladeschimmer beschriftung={t('app.laden')} zeilen={5} />;

  const unbestaetigt = tool.status === 'importiert_unbestaetigt';
  const alleBeantwortet = ATTESTIERUNGEN.every((frage) => antworten[frage.feld] !== '');
  const abweichungen = nutzung.filter((eintrag) => !eintrag.kategorie_gedeckt).length;
  const verknuepft = prozesse.filter((p) => tool.prozessobjekt_ids.includes(p.id));

  const attestieren = async () => {
    if (token === null || id === undefined || !alleBeantwortet) return;
    await fuehreAus(() =>
      api.toolAttestieren(token, id, {
        attest_entscheidung_ueber_personen: antworten.attest_entscheidung_ueber_personen === 'ja',
        attest_mensch_dazwischen: antworten.attest_mensch_dazwischen === 'ja',
        attest_undeklarierte_quellen: antworten.attest_undeklarierte_quellen === 'ja',
      }),
    );
  };

  /** Kanten folgen der Auswahl: was dazukommt, wird verknüpft; was fehlt, gelöst. */
  const prozesseSetzen = (ids: string[]) => {
    if (token === null || id === undefined) return;
    const neu = ids.find((kandidat) => !tool.prozessobjekt_ids.includes(kandidat));
    if (neu !== undefined) {
      void fuehreAus(() => api.toolMitProzessVerknuepfen(token, id, neu));
      return;
    }
    const entfernt = tool.prozessobjekt_ids.find((vorhanden) => !ids.includes(vorhanden));
    if (entfernt !== undefined) {
      void fuehreAus(() => api.toolVonProzessLoesen(token, id, entfernt));
    }
  };

  const datenobjektVerknuepfen = (ids: string[]) => {
    if (token === null || id === undefined || ids.length === 0) return;
    void fuehreAus(() =>
      api.toolMitDatenobjektVerknuepfen(token, id, ids[ids.length - 1], zugriffsart),
    );
  };

  const stammdatenAendern = (feld: keyof ToolObjekt, wert: string) => {
    if (token === null || id === undefined) return;
    void fuehreAus(() => api.toolAendern(token, id, { [feld]: wert === '' ? null : wert }));
  };

  const personen = nutzer.map((person) => ({
    wert: person.id,
    text: person.name,
  }));

  return (
    <>
      <Seitenkopf
        titel={tool.name}
        untertitel={
          technologien.find((o) => o.schluessel === tool.technologie)?.name ??
          tool.technologie ??
          t('tool.technologie.keine')
        }
        rueckweg={{ ziel: pfad('/tools'), text: t('asset.tools.titel') }}
        aktionen={
          <>
            {tool.wirkungsart === null ? (
              <Abzeichen ton="gelb" zeichen="?">
                {t('tool.wirkungsart.offen')}
              </Abzeichen>
            ) : (
              <Abzeichen ton={WIRKUNGSART_TON[tool.wirkungsart]}>
                {t(`tool.wirkungsart.${tool.wirkungsart}` as never)}
              </Abzeichen>
            )}
            {tool.geerbt.tier !== null && <Abzeichen>{`Tier ${tool.geerbt.tier}`}</Abzeichen>}
          </>
        }
      />

      {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}
      {!tool.rechte.bearbeiten && <Hinweis art="information">{t('rechte.tool.nurLesen')}</Hinweis>}
      {tool.schreibgeschuetzte_felder.length > 0 && (
        <Hinweis art="information">{t('asset.importHinweis')}</Hinweis>
      )}

      {unbestaetigt && (
        <Karte>
          <Hinweis art="warnung">{t('asset.bestaetigenHinweis')}</Hinweis>
          {tool.rechte.bestaetigen && (
            <Knopf
              art="gefuellt"
              onClick={() => fuehreAus(() => api.toolBestaetigen(token as string, tool.id))}
            >
              {t('asset.bestaetigen')}
            </Knopf>
          )}
        </Karte>
      )}

      {/* --- Attestierungen (A.6) --------------------------------------- */}
      <Karte
        titel={t('tool.attest.titel')}
        beischrift={t('tool.attest.hinweis')}
        aktion={
          tool.attestierung_vollstaendig ? (
            <Abzeichen ton="gruen" zeichen="✓">
              {t('sv.vollstaendig')}
            </Abzeichen>
          ) : (
            <Abzeichen ton="gelb" zeichen="!">
              {t('tool.attest.offen')}
            </Abzeichen>
          )
        }
      >
        {!tool.attestierung_vollstaendig && (
          <Hinweis art="warnung">{t('tool.attest.offenHinweis')}</Hinweis>
        )}
        <Gruppe>
          {ATTESTIERUNGEN.map((frage) => (
            <Zeile
              key={frage.feld}
              pruefkennung={frage.feld}
              haupt={t(frage.text)}
              zweitzeile={t(`${frage.text}.zusatz` as never)}
              wert={
                <SegmentierteSteuerung<Antwort>
                  beschriftung={t(frage.text)}
                  wert={antworten[frage.feld] ?? ''}
                  aendern={(wert) =>
                    setAntworten((bisher) => ({
                      ...bisher,
                      [frage.feld]: wert,
                    }))
                  }
                  optionen={[
                    { wert: 'ja', text: t('ja') },
                    { wert: 'nein', text: t('nein') },
                  ]}
                  gesperrt={!tool.rechte.attestieren}
                />
              }
            />
          ))}
        </Gruppe>
        {tool.attestiert_am !== null && (
          <Werteliste
            eintraege={[
              {
                beschriftung: t('tool.attest.erklaertVon'),
                // Aus der Antwort, nicht aus der Auswahlliste: wer attestiert
                // hat, muss dort nicht stehen — attestieren kann auch die
                // Governance, die an dieser Einheit keine Rolle trägt.
                wert: tool.attestiert_von_name ?? t('tool.attest.unbekannt'),
              },
              {
                beschriftung: t('tool.attest.erklaertAm'),
                wert: new Date(tool.attestiert_am).toLocaleDateString(),
              },
            ]}
          />
        )}
        {tool.rechte.attestieren && (
          <div className="formularfuss">
            <Knopf art="gefuellt" disabled={!alleBeantwortet} onClick={attestieren}>
              {tool.attestierung_vollstaendig
                ? t('tool.attest.erneuern')
                : t('tool.attest.abgeben')}
            </Knopf>
          </div>
        )}
      </Karte>

      {/* --- Wirkungsart (A.6) ------------------------------------------ */}
      <Karte titel={t('tool.wirkungsart')}>
        <Werteliste
          eintraege={[
            {
              beschriftung: t('tool.wirkungsart'),
              wert:
                tool.wirkungsart === null
                  ? t('tool.wirkungsart.offen')
                  : t(`tool.wirkungsart.${tool.wirkungsart}` as never),
              herkunft: t(`tool.wirkungsart.grund.${tool.wirkungsart_grund}` as never),
              pruefkennung: 'wirkungsart',
            },
          ]}
        />
      </Karte>

      {/* --- Stammdaten (A.6, „deklariert") ----------------------------- */}
      <Karte titel={t('tool.stammdaten')} beischrift={t('tool.stammdaten.hinweis')}>
        <Werteliste
          eintraege={[
            {
              beschriftung: t('asset.feld.status'),
              wert: t(`asset.status.${tool.status}` as never),
              pruefkennung: 'status',
            },
            {
              beschriftung: t('asset.feld.herkunft'),
              wert: t(`asset.herkunft.${tool.herkunft}` as never),
            },
          ]}
        />
        <Auswahl
          beschriftung={t('tool.feld.owner')}
          wert={tool.technischer_owner_user_id ?? ''}
          aendern={(wert) => stammdatenAendern('technischer_owner_user_id', wert)}
          leertext="—"
          optionen={personen}
          hilfe={t('tool.owner.hilfe')}
          gesperrt={!tool.rechte.bearbeiten}
        />
        <Auswahl
          beschriftung={t('tool.feld.stellvertretung')}
          wert={tool.stellvertretung_user_id ?? ''}
          aendern={(wert) => stammdatenAendern('stellvertretung_user_id', wert)}
          leertext="—"
          optionen={personen}
          gesperrt={!tool.rechte.bearbeiten}
        />
        <Auswahl
          beschriftung={t('asset.feld.technologie')}
          wert={tool.technologie ?? ''}
          aendern={(wert) => stammdatenAendern('technologie', wert)}
          leertext={t('tool.technologie.keine')}
          optionen={mitBestandswert(
            technologien.map((o) => ({ wert: o.schluessel, text: o.name })),
            tool.technologie,
          )}
          gesperrt={!tool.rechte.bearbeiten}
        />
        <Auswahl
          beschriftung={t('tool.feld.organisationseinheit')}
          wert={tool.organisationseinheit_id ?? ''}
          aendern={(wert) => stammdatenAendern('organisationseinheit_id', wert)}
          leertext="—"
          optionen={waehlbar.map((einheit) => ({
            wert: einheit.id,
            text: orgBezeichnung(einheit, fachbereiche),
          }))}
          gesperrt={!tool.rechte.bearbeiten}
        />
        <Auswahl
          beschriftung={t('tool.feld.lauftyp')}
          wert={tool.lauftyp ?? ''}
          aendern={(wert) => stammdatenAendern('lauftyp', wert)}
          leertext={t('tool.lauftyp.keiner')}
          optionen={LAUFTYPEN.map((typ: Lauftyp) => ({
            wert: typ,
            text: t(`tool.lauftyp.${typ}` as never),
          }))}
          hilfe={t('tool.lauftyp.hilfe')}
          gesperrt={!tool.rechte.bearbeiten}
        />
        {/* --- Gemessene Seite des Rahmens (A.13.2 Schicht 1) ------------- */}
        <Auswahl
          beschriftung={t('tool.feld.identitaet')}
          wert={tool.ausfuehrungsidentitaet ?? ''}
          aendern={(wert) => stammdatenAendern('ausfuehrungsidentitaet', wert)}
          leertext={t('tool.identitaet.keine')}
          optionen={IDENTITAETEN.map((art) => ({
            wert: art,
            text: t(`rahmen.identitaet.${art}` as never),
          }))}
          hilfe={t('tool.identitaet.hilfe')}
          gesperrt={!tool.rechte.bearbeiten}
        />
        <Umschalter
          beschriftung={t('tool.feld.statischeZugangsdaten')}
          hilfe={t('tool.statischeZugangsdaten.hilfe')}
          an={tool.statische_zugangsdaten === true}
          aendern={(an) =>
            fuehreAus(() =>
              api.toolAendern(token as string, tool.id, {
                statische_zugangsdaten: an,
              }),
            )
          }
          gesperrt={!tool.rechte.bearbeiten}
        />
      </Karte>

      {/* --- Externe Ziele: was das Tool tatsächlich anspricht ------------ */}
      <Karte titel={t('tool.ziele.titel')} beischrift={t('tool.ziele.hinweis')}>
        {tool.externe_ziele.length === 0 ? (
          <p className="leerhinweis">{t('tool.ziele.leer')}</p>
        ) : (
          <Gruppe>
            {tool.externe_ziele.map((ziel) => (
              <Zeile
                key={ziel}
                pruefkennung={`tool-ziel-${ziel}`}
                haupt={ziel}
                wert={
                  <Knopf
                    disabled={!tool.rechte.bearbeiten}
                    aria-label={`${ziel} — ${t('prozess.ziele.entfernen')}`}
                    onClick={() =>
                      fuehreAus(() =>
                        api.toolAendern(token as string, tool.id, {
                          externe_ziele: tool.externe_ziele.filter((v) => v !== ziel),
                        }),
                      )
                    }
                  >
                    ×
                  </Knopf>
                }
              />
            ))}
          </Gruppe>
        )}
        <Feld
          beschriftung={t('tool.ziele.neu')}
          wert={neuesZiel}
          aendern={setNeuesZiel}
          platzhalter="sftp.partner.example"
          disabled={!tool.rechte.bearbeiten}
        />
        <div className="k-knopfreihe">
          <Knopf
            art="getoent"
            disabled={
              !tool.rechte.bearbeiten ||
              neuesZiel.trim() === '' ||
              tool.externe_ziele.includes(neuesZiel.trim())
            }
            onClick={() => {
              const ergaenzt = [...tool.externe_ziele, neuesZiel.trim()];
              setNeuesZiel('');
              void fuehreAus(() =>
                api.toolAendern(token as string, tool.id, {
                  externe_ziele: ergaenzt,
                }),
              );
            }}
            data-testid="tool-ziel-hinzufuegen"
          >
            {t('prozess.ziele.hinzufuegen')}
          </Knopf>
        </div>
      </Karte>

      {/* --- Prozesskanten (A.4.4) -------------------------------------- */}
      <Karte titel={t('asset.prozesse.titel')} beischrift={t('tool.prozesse.hinweis')}>
        {!tool.attestierung_vollstaendig || unbestaetigt ? (
          <Hinweis art="information">
            {unbestaetigt ? t('asset.bestaetigenHinweis') : t('tool.attest.offenHinweis')}
          </Hinweis>
        ) : !tool.rechte.verknuepfen ? (
          <Hinweis art="information">{t('rechte.tool.nurLesen')}</Hinweis>
        ) : (
          <ReferenzWaehler
            beschriftung={t('asset.prozesse.verknuepfen')}
            pruefkennung="waehler-prozesse"
            bestand={prozesse.map((prozess) => ({
              id: prozess.id,
              name: prozess.name,
              zusatz: t(`prozess.kundenkreis.${prozess.customer}` as never),
              abzeichen: prozess.mitbestimmung_flag ? 'MB' : undefined,
              ton: prozess.mitbestimmung_flag ? ('lila' as const) : undefined,
            }))}
            gewaehlt={tool.prozessobjekt_ids}
            aendern={prozesseSetzen}
            keineTreffer={t('asset.prozesse.leer')}
          />
        )}

        {verknuepft.length === 0 ? (
          <p className="leerhinweis">{t('asset.prozesse.leer')}</p>
        ) : (
          <Gruppe etikett={t('tool.prozesse.geerbtVon')}>
            {tool.geerbt.beitraege.map((beitrag) => (
              <ZeileVerweis
                key={beitrag.prozess_id}
                ziel={pfad(`/prozesse/${beitrag.prozess_id}`)}
                haupt={beitrag.name}
                zweitzeile={[
                  `${t('asset.geerbt.kritikalitaet')} ${beitrag.kritikalitaet}`,
                  beitrag.reichweite === null
                    ? null
                    : t(`reichweite.${beitrag.reichweite}` as never),
                ]
                  .filter(Boolean)
                  .join(' · ')}
                wert={
                  <>
                    {beitrag.massgeblich && (
                      <Abzeichen ton="blau">{t('tool.prozesse.massgeblich')}</Abzeichen>
                    )}
                    {beitrag.tier !== null && <Abzeichen>{`Tier ${beitrag.tier}`}</Abzeichen>}
                  </>
                }
              />
            ))}
          </Gruppe>
        )}
      </Karte>

      {/* --- Geerbte Klassifikation (A.4.4) ----------------------------- */}
      <Karte titel={t('asset.geerbt.titel')} beischrift={t('asset.geerbt.hinweis')}>
        <Werteliste
          eintraege={[
            {
              beschriftung: t('asset.geerbt.kritikalitaet'),
              wert: tool.geerbt.kritikalitaet,
              pruefkennung: 'geerbt-kritikalitaet',
            },
            {
              beschriftung: t('asset.geerbt.reichweite'),
              wert:
                tool.geerbt.reichweite === null
                  ? '—'
                  : t(`reichweite.${tool.geerbt.reichweite}` as never),
              pruefkennung: 'geerbt-reichweite',
            },
            {
              beschriftung: t('asset.geerbt.tier'),
              wert: tool.geerbt.tier ?? '—',
              herkunft: tool.geerbt.beitraege.find(
                (beitrag) => beitrag.tier !== null && beitrag.tier === tool.geerbt.tier,
              )?.name,
              pruefkennung: 'geerbt-tier',
            },
            {
              beschriftung: t('asset.geerbt.kKlassen'),
              wert: tool.geerbt.k_klassen.join(', ') || '—',
              pruefkennung: 'geerbt-k-klassen',
            },
          ]}
        />
      </Karte>

      {/* --- Genutzte Datenobjekte und Zweckbindung (A.4.6) ------------- */}
      <Karte titel={t('tool.daten.titel')} beischrift={t('tool.daten.hinweis')}>
        {abweichungen > 0 && (
          <Hinweis art="warnung">
            {t('tool.daten.abweichungen').replace('{anzahl}', String(abweichungen))}
          </Hinweis>
        )}
        {verknuepft.length === 0 && nutzung.length > 0 && (
          <Hinweis art="information">{t('tool.daten.ohneProzess')}</Hinweis>
        )}

        <SegmentierteSteuerung<Zugriffsart>
          beschriftung={t('tool.daten.zugriffsart')}
          beschriftungZeigen
          hilfe={t('tool.daten.zugriffsartHilfe')}
          wert={zugriffsart}
          aendern={setZugriffsart}
          optionen={ZUGRIFFSARTEN.map((art) => ({
            wert: art,
            text: t(`zugriffsart.${art}` as never),
          }))}
          gesperrt={!tool.rechte.verknuepfen}
        />
        {tool.rechte.verknuepfen && (
          <ReferenzWaehler
            beschriftung={t('tool.daten.hinzufuegen')}
            pruefkennung="waehler-datenobjekte"
            bestand={datenobjekte
              .filter((objekt) => !nutzung.some((kante) => kante.datenobjekt_id === objekt.id))
              .map((objekt) => ({
                id: objekt.id,
                name: objekt.name,
                zusatz: objekt.quellsystem ?? undefined,
                abzeichen:
                  objekt.kategorie === null
                    ? undefined
                    : t(`kategorie.${objekt.kategorie}` as never),
                ton: objekt.kategorie === null ? undefined : KATEGORIE_TON[objekt.kategorie],
              }))}
            gewaehlt={[]}
            aendern={datenobjektVerknuepfen}
            keineTreffer={t('asset.verwendung.keineTools')}
          />
        )}

        {nutzung.length === 0 ? (
          <p className="leerhinweis">{t('tool.daten.leer')}</p>
        ) : (
          <Gruppe>
            {nutzung.map((kante) => (
              <Zeile
                key={kante.datenobjekt_id}
                pruefkennung={`nutzung-${kante.datenobjekt_id}`}
                haupt={kante.name}
                zweitzeile={
                  kante.im_prozessrahmen
                    ? undefined
                    : kante.kategorie_gedeckt
                      ? t('tool.daten.nurKategorieHinweis')
                      : t('tool.daten.ausserhalbHinweis')
                }
                wert={
                  <>
                    {!kante.im_prozessrahmen && (
                      <Abzeichen ton={kante.kategorie_gedeckt ? 'gelb' : 'rot'} zeichen="!">
                        {kante.kategorie_gedeckt
                          ? t('tool.daten.nurKategorie')
                          : t('tool.daten.ausserhalb')}
                      </Abzeichen>
                    )}
                    <Auswahl
                      beschriftung={`${t('tool.daten.zugriffsart')} — ${kante.name}`}
                      beschriftungVerborgen
                      wert={kante.zugriffsart}
                      aendern={(wert) =>
                        fuehreAus(() =>
                          api.toolZugriffsartAendern(
                            token as string,
                            tool.id,
                            kante.datenobjekt_id,
                            wert as Zugriffsart,
                          ),
                        )
                      }
                      optionen={ZUGRIFFSARTEN.map((art) => ({
                        wert: art,
                        text: t(`zugriffsart.${art}` as never),
                      }))}
                      gesperrt={!tool.rechte.verknuepfen}
                    />
                    <Knopf
                      disabled={!tool.rechte.verknuepfen}
                      aria-label={`${kante.name} — ${t('tool.daten.entfernen')}`}
                      onClick={() =>
                        fuehreAus(() =>
                          api.toolVonDatenobjektLoesen(
                            token as string,
                            tool.id,
                            kante.datenobjekt_id,
                          ),
                        )
                      }
                    >
                      ×
                    </Knopf>
                  </>
                }
              />
            ))}
          </Gruppe>
        )}
      </Karte>

      <Klassenbefund toolId={tool.id} stand={stand} />

      <Erlaubnisrahmen toolId={tool.id} stand={stand} />

      {/* --- Selbstverpflichtung des technischen Owners (A.10.3) ---------
          Bis AP-5 gab es dafür keinen Weg in der Oberfläche: die Hälfte des
          Moduls war über die API erreichbar und über den Bildschirm nicht. */}
      <Karte
        titel={t('sv.titel')}
        beischrift={deckung?.grundtext ?? t('sv.untertitel.tool')}
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
            ]}
          />
        )}
        <div className="k-knopfreihe">
          <Link
            className="k-knopf k-knopf--getoent"
            to={pfad(`/tools/${tool.id}/selbstverpflichtung`)}
            data-testid="tool-sv-oeffnen"
          >
            {t('sv.abgeben')}
          </Link>
        </div>
      </Karte>

      <ToolCompliance toolId={tool.id} />
    </>
  );
}
