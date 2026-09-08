import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { Link, useParams } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type {
  Bewertung,
  DatenObjekt,
  Fachbereich,
  Organisationseinheit,
  Prozess,
  Technologie,
  ToolObjekt,
  ProzessStatus,
} from '@/api/typen';
import { ProzessGovernance } from '@/komponenten/ProzessGovernance';
import { ProzessKlassen } from '@/komponenten/ProzessKlassen';
import { useSprache } from '@/i18n/SprachKontext';
import { orgBezeichnung } from '@/nutzen/bezeichnungen';
import {
  Abzeichen,
  Gruppe,
  Hinweis,
  Karte,
  Knopf,
  Ladeschimmer,
  Seitenkopf,
  Werteliste,
  Zeile,
  ZeileVerweis,
  type Ton,
} from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

function tierTon(tier: number | null): Ton {
  if (tier === 3) return 'rot';
  if (tier === 2) return 'gelb';
  return 'neutral';
}

/** Alle über die Kette erreichbaren Prozesse, in Richtung ``richtung``. */
function kette(
  start: Prozess,
  alle: Prozess[],
  richtung: 'nachgelagert_ids' | 'vorgelagert_ids',
): Prozess[] {
  const gefunden = new Map<string, Prozess>();
  const stapel = [...start[richtung]];
  while (stapel.length > 0) {
    const id = stapel.pop() as string;
    if (gefunden.has(id) || id === start.id) continue;
    const treffer = alle.find((p) => p.id === id);
    if (treffer === undefined) continue;
    gefunden.set(id, treffer);
    stapel.push(...treffer[richtung]);
  }
  return [...gefunden.values()];
}

/** „Läuft ohne Deckung" ist kein neutraler Zustand — er sieht auch nicht so aus. */
const STATUS_TON: Record<ProzessStatus, Ton> = {
  entwurf: 'neutral',
  aktiv: 'gruen',
  freigabe_ausstehend: 'rot',
  stillgelegt: 'neutral',
};

export function ProzessDetail() {
  const { id } = useParams();
  const { t, pfad } = useSprache();
  const { token } = useSitzung();
  const [prozess, setProzess] = useState<Prozess | null>(null);
  const [einheiten, setEinheiten] = useState<Organisationseinheit[]>([]);
  const [fachbereiche, setFachbereiche] = useState<Fachbereich[]>([]);
  const [bewertungen, setBewertungen] = useState<Bewertung[]>([]);
  const [tools, setTools] = useState<ToolObjekt[]>([]);
  const [datenobjekte, setDatenobjekte] = useState<DatenObjekt[]>([]);
  const [prozesse, setProzesse] = useState<Prozess[]>([]);
  const [technologien, setTechnologien] = useState<Technologie[]>([]);
  const [fehler, setFehler] = useState<string | null>(null);

  const laden = useCallback(() => {
    if (token === null || id === undefined) return;
    Promise.all([
      api.prozess(token, id),
      api.organisationseinheiten(token),
      api.fachbereiche(token),
      api.bewertungen(token, id),
      api.tools(token),
      api.datenobjekte(token).catch(() => [] as DatenObjekt[]),
      api.prozesse(token).catch(() => [] as Prozess[]),
      api.technologien(token).catch(() => [] as Technologie[]),
    ])
      .then(([geladen, orgs, bereiche, historie, alleTools, daten, alleProzesse, techs]) => {
        setProzess(geladen);
        setEinheiten(orgs);
        setFachbereiche(bereiche);
        setBewertungen(historie);
        setTools(alleTools.filter((tool) => tool.prozessobjekt_ids.includes(geladen.id)));
        setDatenobjekte(daten);
        setProzesse(alleProzesse);
        setTechnologien(techs);
      })
      .catch(() => setFehler(t('app.fehler')));
  }, [token, id, t]);

  useEffect(laden, [laden]);

  async function setzeStatus(status: 'aktiv' | 'stillgelegt' | 'entwurf') {
    if (token === null || prozess === null) return;
    setFehler(null);
    try {
      setProzess(await api.prozessAendern(token, prozess.id, { status }));
    } catch (ausnahme) {
      // Die Gründe stehen in der Geschäftslogik (Bewertung, Selbstverpflichtung,
      // Gate 1) — hier wird genau der Satz gezeigt, den der Server nennt.
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  if (fehler !== null && prozess === null) return <Hinweis art="fehler">{fehler}</Hinweis>;
  if (prozess === null) return <Ladeschimmer beschriftung={t('app.laden')} zeilen={5} />;

  const datenobjektChip = (objektId: string) => {
    const objekt = datenobjekte.find((d) => d.id === objektId);
    return (
      <span className="k-chip" key={objektId}>
        {objekt?.name ?? objektId}
      </span>
    );
  };

  const prozessChip = (prozessId: string) => {
    const ziel = prozesse.find((p) => p.id === prozessId);
    return (
      <Link className="k-chip" key={prozessId} to={pfad(`/prozesse/${prozessId}`)}>
        {ziel?.name ?? prozessId}
      </Link>
    );
  };

  const chipreihe = (ids: string[], zeichne: (id: string) => ReactNode, leer: string) =>
    ids.length === 0 ? (
      <span className="leerhinweis">{leer}</span>
    ) : (
      <span className="k-chipreihe">{ids.map(zeichne)}</span>
    );

  const abwaerts = kette(prozess, prozesse, 'nachgelagert_ids');
  const aufwaerts = kette(prozess, prozesse, 'vorgelagert_ids');
  // Die juengste Bewertung traegt seit AP-19 den Sollzustand: Tier samt
  // Herkunft und die eingefrorene Reichweite (E-70).
  const bewertung = bewertungen.length > 0 ? bewertungen[0] : null;

  return (
    <>
      <Seitenkopf
        titel={prozess.name}
        untertitel={orgBezeichnung(
          einheiten.find((e) => e.id === prozess.prozessgeber_org_id),
          fachbereiche,
        )}
        rueckweg={{ ziel: pfad('/prozesse'), text: t('prozess.liste.titel') }}
        aktionen={
          <>
            <Abzeichen ton={STATUS_TON[prozess.status]}>
              {t(`status.${prozess.status}` as never)}
            </Abzeichen>
            {prozess.tier !== null && (
              <Abzeichen ton={tierTon(prozess.tier)}>{`Tier ${prozess.tier}`}</Abzeichen>
            )}
            {prozess.rechte.bearbeiten && (
              <>
                <Link
                  className="k-knopf k-knopf--getoent"
                  to={pfad(`/prozesse/${prozess.id}/bearbeiten`)}
                >
                  {t('prozess.bearbeiten')}
                </Link>
                {prozess.status !== 'aktiv' ? (
                  <Knopf art="gefuellt" onClick={() => setzeStatus('aktiv')}>
                    {t('prozess.aktivieren')}
                  </Knopf>
                ) : (
                  <Knopf art="zerstoerend" onClick={() => setzeStatus('stillgelegt')}>
                    {t('prozess.stilllegen')}
                  </Knopf>
                )}
              </>
            )}
          </>
        }
      />

      {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}
      {prozess.status === 'freigabe_ausstehend' && (
        <Hinweis art="warnung">{t('prozess.freigabeAusstehend')}</Hinweis>
      )}

      {/* Eine fehlende Schaltfläche erklärt sich nicht von selbst. Wer nichts
          ändern darf, soll wissen warum — und wen er fragen kann. */}
      {!prozess.rechte.bearbeiten && (
        <Hinweis art="information">
          {prozess.rechte.umsetzung_pflegen
            ? t('rechte.prozess.nurUmsetzung')
            : t('rechte.prozess.nurLesen')}
        </Hinweis>
      )}

      <Gruppe etikett={t('prozess.gruppe.sipoc')}>
        <Zeile
          beschriftung={t('prozess.feld.vorgelagert')}
          wert={chipreihe(prozess.vorgelagert_ids, prozessChip, t('prozess.wirkung.leer'))}
        />
        <Zeile beschriftung={t('prozess.feld.supplier')} wert={prozess.supplier || '—'} />
        <Zeile
          beschriftung={t('prozess.feld.inputDatenobjekte')}
          wert={chipreihe(
            prozess.input_datenobjekt_ids,
            datenobjektChip,
            t('prozess.datenobjekte.leer'),
          )}
        />
        <Zeile
          beschriftung={t('prozess.feld.processSteps')}
          wert={`${prozess.process_steps || '—'} (${prozess.schritt_anzahl})`}
        />
        <Zeile beschriftung={t('prozess.feld.output')} wert={prozess.output || '—'} />
        <Zeile
          beschriftung={t('prozess.feld.outputDatenobjekte')}
          wert={chipreihe(
            prozess.output_datenobjekt_ids,
            datenobjektChip,
            t('prozess.datenobjekte.leer'),
          )}
        />
        <Zeile
          beschriftung={t('prozess.feld.customer')}
          wert={t(`kundenkreis.${prozess.customer}` as never)}
        />
        {/*
          Die Reichweite steht direkt bei dem Feld, aus dem sie folgt — als
          unmittelbare Konsequenz der Erklärung, nicht als eigene Ebene. Wer
          einen Kundenkreis wählt, muss sehen, was er damit sagt, und zwar
          bevor er bewertet.
        */}
        <Zeile
          pruefkennung="reichweite"
          beschriftung={t('prozess.feld.reichweite')}
          wert={prozess.reichweite === null ? '—' : t(`reichweite.${prozess.reichweite}` as never)}
          zweitzeile={
            prozess.umsetzungen.length > 1
              ? t('prozess.herkunft.reichweiteUmsetzung')
              : t('prozess.herkunft.reichweite')
          }
        />
        <Zeile
          beschriftung={t('prozess.feld.nachgelagert')}
          wert={chipreihe(prozess.nachgelagert_ids, prozessChip, t('prozess.wirkung.leer'))}
        />
        <Zeile
          pruefkennung="ausfallfolge"
          beschriftung={t('prozess.feld.ausfallfolge')}
          wert={t(`ausfallfolge.${prozess.ausfallfolge}` as never)}
        />
        {/*
          Hier stand bis AP-19 die abgeleitete „Kritikalität" — die eigene
          Ausfallfolge, hochgezogen auf das Maximum der Kette. Sie ist entfallen:
          Was die Kette bewirkt, sagt jetzt das Tier, und zwar aus dem kompositen
          UR der Nachfolger. Zwei Zahlen über dieselbe Kette nebeneinander wären
          genau die zweite Ebene, die AP-19 aufgelöst hat.
        */}
        <Zeile
          pruefkennung="mitbestimmung"
          beschriftung={t('prozess.feld.mitbestimmung')}
          wert={prozess.mitbestimmung_flag ? t('ja') : t('nein')}
          zweitzeile={t('prozess.herkunft.mitbestimmung')}
        />
      </Gruppe>

      {prozess.schritte_zu_viele && (
        <Hinweis art="warnung">{t('prozess.schritte.warnung')}</Hinweis>
      )}

      {/*
        Die Karte „Abgeleitet" stand hier bis AP-19 als eigene Ebene neben der
        Bewertung und zeigte dieselben Größen ein zweites Mal. Sie ist
        aufgelöst: Reichweite und Ausfallfolge sind erklärte Erwartungen und
        stehen oben bei den Stammdaten, ihre Wirkung steht in der Bewertung.
        Hier bleibt der Verweis darauf — und der Hinweis, wenn beides
        auseinanderläuft.
      */}
      <Karte titel={t('prozess.bewertet.titel')} beischrift={t('prozess.bewertet.hinweis')}>
        {bewertung === null ? (
          <Hinweis art="information">{t('prozess.bewertet.keine')}</Hinweis>
        ) : (
          <>
            <Werteliste
              eintraege={[
                {
                  beschriftung: t('bewertung.tier'),
                  wert: bewertung.tier,
                  herkunft: t(`bewertung.herkunft.${bewertung.tier_herkunft}` as never),
                  pruefkennung: 'tier-herkunft',
                },
                {
                  beschriftung: t('prozess.feld.reichweite'),
                  wert:
                    bewertung.reichweite === null
                      ? '—'
                      : t(`reichweite.${bewertung.reichweite}` as never),
                  herkunft: t('prozess.bewertet.stand'),
                  pruefkennung: 'bewertung-reichweite',
                },
                {
                  beschriftung: t('bewertung.ur'),
                  wert: bewertung.ur_stufe,
                  herkunft: t('prozess.feld.ausfallfolge'),
                  pruefkennung: 'ur-stufe',
                },
                {
                  beschriftung: t('prozess.feld.mitbestimmung'),
                  wert: prozess.mitbestimmung_flag ? t('ja') : t('nein'),
                  herkunft: t('prozess.herkunft.mitbestimmung'),
                  pruefkennung: 'bewertung-mitbestimmung',
                },
              ]}
            />
            {bewertung.ueberholt_am !== null && (
              <Hinweis art="warnung">
                {t('bewertung.ueberholt')} — {bewertung.ueberholt_grund}
              </Hinweis>
            )}
            {bewertung.ueberholt_am === null &&
              bewertung.reichweite !== null &&
              prozess.reichweite !== null &&
              prozess.reichweite !== bewertung.reichweite && (
                <Hinweis art="information">
                  {t('prozess.drift')}: {t(`reichweite.${prozess.reichweite}` as never)} —{' '}
                  {t('prozess.drift.hinweis')}
                </Hinweis>
              )}
          </>
        )}
      </Karte>

      <Karte titel={t('prozess.wirkung.titel')} beischrift={t('prozess.wirkung.hinweis')}>
        <Werteliste
          eintraege={[
            {
              beschriftung: t('prozess.wirkung.abwaerts'),
              wert:
                abwaerts.length === 0 ? (
                  t('prozess.wirkung.leer')
                ) : (
                  <span className="k-chipreihe">{abwaerts.map((p) => prozessChip(p.id))}</span>
                ),
              pruefkennung: 'wirkung-abwaerts',
            },
            {
              beschriftung: t('prozess.wirkung.aufwaerts'),
              wert:
                aufwaerts.length === 0 ? (
                  t('prozess.wirkung.leer')
                ) : (
                  <span className="k-chipreihe">{aufwaerts.map((p) => prozessChip(p.id))}</span>
                ),
              pruefkennung: 'wirkung-aufwaerts',
            },
          ]}
        />
      </Karte>

      <Karte
        titel={t('bewertung.historie')}
        aktion={
          prozess.rechte.bewerten ? (
            <Link
              className="k-knopf k-knopf--getoent"
              to={pfad(`/prozesse/${prozess.id}/bewertung`)}
            >
              {t('bewertung.starten')}
            </Link>
          ) : undefined
        }
      >
        {bewertungen.length === 0 ? (
          <p className="leerhinweis">{t('bewertung.historie.leer')}</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>{t('bewertung.bewertetAm')}</th>
                <th>{t('bewertung.tier')}</th>
                <th>{t('bewertung.profil')}</th>
                <th>{t('bewertung.kKlassen')}</th>
                <th>{t('bewertung.gueltigBis')}</th>
              </tr>
            </thead>
            <tbody>
              {/* Neueste zuerst — die erste Zeile ist die maßgebliche. Ältere
                  bleiben stehen: eine Neubewertung ersetzt keine Geschichte. */}
              {bewertungen.map((b, rang) => (
                <tr key={b.id} data-testid={rang === 0 ? 'bewertung-massgeblich' : undefined}>
                  <td>
                    {b.bewertet_am.slice(0, 10)}
                    {rang === 0 && (
                      <>
                        {' '}
                        <Abzeichen ton="blau">{t('bewertung.massgeblich')}</Abzeichen>
                      </>
                    )}
                  </td>
                  <td>
                    <Abzeichen ton={tierTon(b.tier)}>{`Tier ${b.tier}`}</Abzeichen>
                  </td>
                  <td>
                    {`KI${b.ki_stufe}-DS${b.ds_stufe}-MB${b.mb_stufe}-` +
                      `IT${b.it_stufe}-RG${b.rg_stufe}-UR${b.ur_stufe}`}
                  </td>
                  <td>{b.ausgeloeste_k_klassen.join(', ') || '—'}</td>
                  <td>{b.gueltig_bis ? b.gueltig_bis.slice(0, 10) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Karte>

      <ProzessKlassen prozessId={prozess.id} />

      <ProzessGovernance prozessId={prozess.id} rechte={prozess.rechte} />

      <Gruppe etikett={t('asset.tools.amProzess')}>
        {tools.length === 0 ? (
          <Zeile haupt={<span className="leerhinweis">{t('asset.tools.amProzessLeer')}</span>} />
        ) : (
          tools.map((tool) => (
            <ZeileVerweis
              key={tool.id}
              ziel={pfad(`/tools/${tool.id}`)}
              haupt={tool.name}
              zweitzeile={
                technologien.find((o) => o.schluessel === tool.technologie)?.name ??
                tool.technologie ??
                undefined
              }
              wert={
                tool.geerbt.tier === null ? undefined : (
                  <Abzeichen
                    ton={tierTon(tool.geerbt.tier)}
                  >{`Tier ${tool.geerbt.tier}`}</Abzeichen>
                )
              }
            />
          ))
        )}
      </Gruppe>

      <Gruppe etikett={t('prozess.umsetzungen.titel')}>
        {prozess.umsetzungen.length === 0 ? (
          <Zeile haupt={<span className="leerhinweis">{t('prozess.umsetzungen.leer')}</span>} />
        ) : (
          prozess.umsetzungen.map((u) => (
            <Zeile
              key={u.id}
              haupt={orgBezeichnung(
                einheiten.find((e) => e.id === u.land_org_id),
                fachbereiche,
              )}
              zweitzeile={u.lokale_abweichung ?? undefined}
            />
          ))
        )}
      </Gruppe>
    </>
  );
}
