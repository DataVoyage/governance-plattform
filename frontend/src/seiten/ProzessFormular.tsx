import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { ApiFehler, api } from '@/api/client';
import type {
  Ausfallfolge,
  DatenObjekt,
  Fachbereich,
  Kundenkreis,
  Nutzer,
  Organisationseinheit,
  Prozess,
  ProzessEingabe,
} from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { orgBezeichnung } from '@/nutzen/bezeichnungen';
import {
  Auswahl,
  Feld,
  Feldgruppe,
  Gruppe,
  Hinweis,
  Karte,
  Knopf,
  Ladeschimmer,
  ReferenzWaehler,
  Seitenkopf,
  Umschalter,
  Zeile,
  type Referenz,
} from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

const KUNDENKREISE: Kundenkreis[] = ['persoenlich', 'team', 'bereich', 'unternehmen', 'extern'];
const AUSFALLFOLGEN: Ausfallfolge[] = ['keine', 'gering', 'spuerbar', 'kritisch'];

/** Dieselbe Grenze wie in ``app/schemas/prozess.py`` (Leitdokument A.5). */
const HOECHSTZAHL_SCHRITTE = 7;

/** Zaehlt wie der Server: getrennt an Zeilenumbruch oder Semikolon. */
export function zaehleSchritte(text: string): number {
  return text
    .replace(/;/g, '\n')
    .split('\n')
    .map((teil) => teil.trim())
    .filter(Boolean).length;
}

const KATEGORIE_TON: Record<string, Referenz['ton']> = {
  oeffentlich: 'gruen',
  intern: 'neutral',
  vertraulich: 'gelb',
  personenbezogen: 'gelb',
  besondere_kategorie: 'rot',
};

/**
 * Anlage- und Bearbeitungsformular des Prozessobjekts (Leitdokument A.5).
 *
 * Die vier Randspalten des SIPOC sind Referenzen, keine Freitexte: Supplier und
 * Customer als vor- und nachgelagerte Prozesse, Input und Output als
 * Datenobjekte (A.4.1, P5). Nur so entsteht der Graph, auf dem Kritikalität,
 * Wirkungsanalyse und Erlaubnisrahmen überhaupt beruhen.
 *
 * Reichweite, Kritikalität und Mitbestimmungsflag fehlen hier bewusst: sie
 * werden serverseitig berechnet und erst in der Detailansicht gezeigt.
 */
export function ProzessFormular() {
  const { id } = useParams();
  const bearbeiten = id !== undefined;
  const { t, pfad } = useSprache();
  const { token, profil } = useSitzung();
  const navigiere = useNavigate();

  const [nutzer, setNutzer] = useState<Nutzer[]>([]);
  const [fachbereiche, setFachbereiche] = useState<Fachbereich[]>([]);
  const [einheiten, setEinheiten] = useState<Organisationseinheit[]>([]);
  const [datenobjekte, setDatenobjekte] = useState<DatenObjekt[]>([]);
  const [prozesse, setProzesse] = useState<Prozess[]>([]);
  const [laedt, setLaedt] = useState(true);
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
  const [eingaenge, setEingaenge] = useState<string[]>([]);
  const [ausgaenge, setAusgaenge] = useState<string[]>([]);
  const [vorgelagert, setVorgelagert] = useState<string[]>([]);
  const [nachgelagert, setNachgelagert] = useState<string[]>([]);
  const [umsetzungen, setUmsetzungen] = useState<string[]>([]);
  const [ziele, setZiele] = useState<string[]>([]);
  const [neuesZiel, setNeuesZiel] = useState('');
  /** Lokale Abweichung je Landesorganisation — sie gehoert an die Umsetzung,
   *  nicht an den Prozess (Architektur 4.2). */
  const [abweichungen, setAbweichungen] = useState<Record<string, string>>({});

  useEffect(() => {
    if (token === null) return;
    Promise.all([
      api.organisationseinheiten(token),
      api.fachbereiche(token),
      api.nutzer(token).catch(() => [] as Nutzer[]),
      api.datenobjekte(token).catch(() => [] as DatenObjekt[]),
      api.prozesse(token).catch(() => [] as Prozess[]),
      bearbeiten ? api.prozess(token, id as string) : Promise.resolve(null),
    ])
      .then(([orgs, bereiche, personen, daten, alle, vorhanden]) => {
        setEinheiten(orgs);
        setFachbereiche(bereiche);
        setNutzer(personen);
        setDatenobjekte(daten);
        setProzesse(alle);
        if (vorhanden !== null) {
          setName(vorhanden.name);
          setOwner(vorhanden.owner_user_id);
          setStellvertretung(vorhanden.stellvertretung_user_id);
          setProzessgeber(vorhanden.prozessgeber_org_id);
          setSupplier(vorhanden.supplier);
          setSchritte(vorhanden.process_steps);
          setErgebnis(vorhanden.output);
          setKundenkreis(vorhanden.customer);
          setAusfallfolge(vorhanden.ausfallfolge);
          setEingaenge(vorhanden.input_datenobjekt_ids);
          setAusgaenge(vorhanden.output_datenobjekt_ids);
          setVorgelagert(vorhanden.vorgelagert_ids);
          setNachgelagert(vorhanden.nachgelagert_ids);
          setUmsetzungen(vorhanden.umsetzungen.map((u) => u.land_org_id));
          setZiele(vorhanden.erlaubte_externe_ziele);
          setAbweichungen(
            Object.fromEntries(
              vorhanden.umsetzungen.map((u) => [u.land_org_id, u.lokale_abweichung ?? '']),
            ),
          );
        }
        setLaedt(false);
      })
      .catch(() => {
        setFehler(t('app.fehler'));
        setLaedt(false);
      });
  }, [token, id, bearbeiten, t]);

  useEffect(() => {
    if (owner === '' && profil !== null && !bearbeiten) setOwner(profil.id);
  }, [profil, owner, bearbeiten]);

  const datenbestand: Referenz[] = useMemo(
    () =>
      datenobjekte.map((objekt) => ({
        id: objekt.id,
        name: objekt.name,
        zusatz: objekt.quelle ?? undefined,
        abzeichen:
          objekt.kategorie === null ? t('asset.kategorie.keine') : t(`kategorie.${objekt.kategorie}` as never),
        ton: objekt.kategorie === null ? 'gelb' : KATEGORIE_TON[objekt.kategorie],
      })),
    [datenobjekte, t],
  );

  const prozessbestand: Referenz[] = useMemo(
    () =>
      prozesse
        .filter((p) => p.id !== id)
        .map((p) => ({
          id: p.id,
          name: p.name,
          zusatz: orgBezeichnung(
            einheiten.find((e) => e.id === p.prozessgeber_org_id),
            fachbereiche,
          ),
          abzeichen: p.tier === null ? undefined : `Tier ${p.tier}`,
          ton: p.tier === 3 ? 'rot' : p.tier === 2 ? 'gelb' : 'neutral',
        })),
    [prozesse, einheiten, fachbereiche, id],
  );

  const intEinheiten = einheiten.filter((e) => e.ebene === 'INT');
  const landEinheiten = einheiten.filter((e) => e.ebene === 'LAND');
  const schrittzahl = zaehleSchritte(schritte);

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
      input_datenobjekt_ids: eingaenge,
      output_datenobjekt_ids: ausgaenge,
      process_steps: schritte,
      output: ergebnis,
      customer: kundenkreis,
      ausfallfolge,
      vorgelagert_ids: vorgelagert,
      nachgelagert_ids: nachgelagert,
      erlaubte_externe_ziele: ziele,
    };
    try {
      if (bearbeiten) {
        await api.prozessAendern(token, id as string, eingabe);
        await gleicheUmsetzungenAb(token, id as string);
        navigiere(pfad(`/prozesse/${id}`));
      } else {
        const angelegt = await api.prozessAnlegen(token, {
          ...eingabe,
          umsetzung_land_org_ids: umsetzungen,
        });
        await gleicheAbweichungenAb(token, angelegt.id);
        navigiere(pfad(`/prozesse/${angelegt.id}`));
      }
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  /** Umsetzungen sind eigene Datensätze; beim Ändern wird die Differenz gepflegt. */
  async function gleicheUmsetzungenAb(gueltigesToken: string, prozessId: string) {
    const vorhanden = await api.prozess(gueltigesToken, prozessId);
    for (const umsetzung of vorhanden.umsetzungen) {
      if (!umsetzungen.includes(umsetzung.land_org_id)) {
        await api.umsetzungEntfernen(gueltigesToken, prozessId, umsetzung.id);
      }
    }
    for (const landOrgId of umsetzungen) {
      if (!vorhanden.umsetzungen.some((u) => u.land_org_id === landOrgId)) {
        await api.umsetzungAnlegen(gueltigesToken, prozessId, landOrgId);
      }
    }
    await gleicheAbweichungenAb(gueltigesToken, prozessId);
  }

  /** Die Abweichung wird erst geschrieben, wenn die Umsetzung existiert. */
  async function gleicheAbweichungenAb(gueltigesToken: string, prozessId: string) {
    const stand = await api.prozess(gueltigesToken, prozessId);
    for (const umsetzung of stand.umsetzungen) {
      const gewuenscht = abweichungen[umsetzung.land_org_id] ?? '';
      if (gewuenscht === (umsetzung.lokale_abweichung ?? '')) continue;
      await api.umsetzungAendern(
        gueltigesToken,
        prozessId,
        umsetzung.id,
        gewuenscht === '' ? null : gewuenscht,
      );
    }
  }

  if (laedt) return <Ladeschimmer beschriftung={t('app.laden')} zeilen={6} />;

  const nutzerAuswahl = nutzer.length > 0 ? nutzer : profil ? [profil as unknown as Nutzer] : [];
  const personen = nutzerAuswahl.map((n) => ({ wert: n.id, text: n.name }));

  return (
    <>
      <Seitenkopf
        titel={bearbeiten ? t('prozess.bearbeiten.titel') : t('prozess.liste.neu')}
        rueckweg={{
          ziel: pfad(bearbeiten ? `/prozesse/${id}` : '/prozesse'),
          text: t('app.zurueck'),
        }}
      />

      <form className="prozessformular" onSubmit={absenden}>
        <Karte titel={t('prozess.gruppe.beteiligte')}>
          <Feld
            beschriftung={t('prozess.feld.name')}
            wert={name}
            aendern={setName}
            pflicht
            hoechstlaenge={255}
          />
          <Auswahl
            beschriftung={t('prozess.feld.owner')}
            wert={owner}
            aendern={setOwner}
            optionen={personen}
            leertext="—"
            pflicht
          />
          <Auswahl
            beschriftung={t('prozess.feld.stellvertretung')}
            wert={stellvertretung}
            aendern={setStellvertretung}
            optionen={personen}
            leertext="—"
            pflicht
            hilfe={t('prozess.stellvertretungPflicht')}
          />
          <Auswahl
            beschriftung={t('prozess.feld.prozessgeber')}
            wert={prozessgeber}
            aendern={setProzessgeber}
            optionen={intEinheiten.map((e) => ({
              wert: e.id,
              text: orgBezeichnung(e, fachbereiche),
            }))}
            leertext="—"
            pflicht
          />
        </Karte>

        <Karte titel={t('prozess.gruppe.sipoc')}>
          <ReferenzWaehler
            beschriftung={t('prozess.feld.vorgelagert')}
            hilfe={t('prozess.hilfe.vorgelagert')}
            bestand={prozessbestand}
            gewaehlt={vorgelagert}
            aendern={setVorgelagert}
            platzhalter={t('prozess.suchen.prozess')}
            keineTreffer={t('prozess.keineTreffer')}
            pruefkennung="waehler-vorgelagert"
          />
          <Feld
            beschriftung={t('prozess.feld.supplier')}
            wert={supplier}
            aendern={setSupplier}
            hilfe={t('prozess.hilfe.supplier')}
            hoechstlaenge={200}
          />
          <ReferenzWaehler
            beschriftung={t('prozess.feld.inputDatenobjekte')}
            hilfe={t('prozess.hilfe.inputDatenobjekte')}
            bestand={datenbestand}
            gewaehlt={eingaenge}
            aendern={setEingaenge}
            platzhalter={t('prozess.suchen.datenobjekt')}
            keineTreffer={t('prozess.keineTreffer')}
            pruefkennung="waehler-input"
          />
          <Feld
            beschriftung={t('prozess.feld.processSteps')}
            wert={schritte}
            aendern={setSchritte}
            mehrzeilig
            hoechstlaenge={1000}
            hilfe={`${t('prozess.hilfe.schritte')} — ${t('prozess.schritte.zaehler')}: ${schrittzahl}`}
            fehler={
              schrittzahl > HOECHSTZAHL_SCHRITTE ? t('prozess.schritte.warnung') : undefined
            }
          />
          <Feld
            beschriftung={t('prozess.feld.output')}
            wert={ergebnis}
            aendern={setErgebnis}
            hilfe={t('prozess.hilfe.output')}
            hoechstlaenge={200}
          />
          <ReferenzWaehler
            beschriftung={t('prozess.feld.outputDatenobjekte')}
            hilfe={t('prozess.hilfe.outputDatenobjekte')}
            bestand={datenbestand}
            gewaehlt={ausgaenge}
            aendern={setAusgaenge}
            platzhalter={t('prozess.suchen.datenobjekt')}
            keineTreffer={t('prozess.keineTreffer')}
            pruefkennung="waehler-output"
          />
          <Auswahl
            beschriftung={t('prozess.feld.customer')}
            wert={kundenkreis}
            aendern={(wert) => setKundenkreis(wert as Kundenkreis)}
            optionen={KUNDENKREISE.map((k) => ({ wert: k, text: t(`kundenkreis.${k}` as never) }))}
          />
          <ReferenzWaehler
            beschriftung={t('prozess.feld.nachgelagert')}
            hilfe={t('prozess.hilfe.nachgelagert')}
            bestand={prozessbestand}
            gewaehlt={nachgelagert}
            aendern={setNachgelagert}
            platzhalter={t('prozess.suchen.prozess')}
            keineTreffer={t('prozess.keineTreffer')}
            pruefkennung="waehler-nachgelagert"
          />
          <Auswahl
            beschriftung={t('prozess.feld.ausfallfolge')}
            wert={ausfallfolge}
            aendern={(wert) => setAusfallfolge(wert as Ausfallfolge)}
            optionen={AUSFALLFOLGEN.map((a) => ({ wert: a, text: t(`ausfallfolge.${a}` as never) }))}
          />
        </Karte>

        {/* --- Erklärter Rahmen (A.13.2 Schicht 1) ----------------------
            Kein SIPOC-Feld: hier erklärt der Prozess-Owner, wohin dieser
            Prozess übermitteln darf. Ein später ergänztes Ziel löst an einem
            aktiven Prozessobjekt Gate 2 aus (A.11) — der Hinweis steht am
            Feld, damit die Folge vor dem Speichern bekannt ist. */}
        <Karte titel={t('prozess.ziele.titel')} beischrift={t('prozess.ziele.hinweis')}>
          {ziele.length === 0 ? (
            <p className="leerhinweis">{t('prozess.ziele.leer')}</p>
          ) : (
            <Gruppe>
              {ziele.map((ziel) => (
                <Zeile
                  key={ziel}
                  pruefkennung={`ziel-${ziel}`}
                  haupt={ziel}
                  wert={
                    <Knopf
                      aria-label={`${ziel} — ${t('prozess.ziele.entfernen')}`}
                      onClick={() => setZiele((bisher) => bisher.filter((v) => v !== ziel))}
                    >
                      ×
                    </Knopf>
                  }
                />
              ))}
            </Gruppe>
          )}
          <Feld
            beschriftung={t('prozess.ziele.neu')}
            wert={neuesZiel}
            aendern={setNeuesZiel}
            hilfe={bearbeiten ? t('prozess.ziele.gateHinweis') : undefined}
            platzhalter="sftp.partner.example"
          />
          <div className="k-knopfreihe">
            <Knopf
              art="getoent"
              disabled={neuesZiel.trim() === '' || ziele.includes(neuesZiel.trim())}
              onClick={() => {
                setZiele((bisher) => [...bisher, neuesZiel.trim()]);
                setNeuesZiel('');
              }}
              data-testid="ziel-hinzufuegen"
            >
              {t('prozess.ziele.hinzufuegen')}
            </Knopf>
          </div>
        </Karte>

        <Karte titel={t('prozess.umsetzungen.titel')}>
          <Feldgruppe>
            {landEinheiten.map((e) => (
              <div key={e.id}>
                <Umschalter
                  beschriftung={orgBezeichnung(e, fachbereiche)}
                  an={umsetzungen.includes(e.id)}
                  aendern={(an) =>
                    setUmsetzungen((bisher) =>
                      an ? [...bisher, e.id] : bisher.filter((vorhanden) => vorhanden !== e.id),
                    )
                  }
                />
                {umsetzungen.includes(e.id) && (
                  <Feld
                    beschriftung={`${t('prozess.umsetzungen.abweichung')} — ${orgBezeichnung(e, fachbereiche)}`}
                    wert={abweichungen[e.id] ?? ''}
                    aendern={(wert) =>
                      setAbweichungen((bisher) => ({ ...bisher, [e.id]: wert }))
                    }
                    hilfe={t('prozess.umsetzungen.abweichungHilfe')}
                  />
                )}
              </div>
            ))}
          </Feldgruppe>
        </Karte>

        {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}

        <div className="formularfuss">
          <Knopf
            onClick={() => navigiere(pfad(bearbeiten ? `/prozesse/${id}` : '/prozesse'))}
          >
            {t('prozess.abbrechen')}
          </Knopf>
          <Knopf type="submit" art="gefuellt" gross>
            {t('prozess.speichern')}
          </Knopf>
        </div>
      </form>
    </>
  );
}
