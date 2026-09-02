import { useCallback, useEffect, useMemo, useState } from 'react';

import { ApiFehler, api } from '@/api/client';
import type {
  Fachbereich,
  Nutzer,
  Organisationseinheit,
  Rolle,
  RolleErklaert,
  Rollenzuweisung,
  ScopeTyp,
  Rollenwirkung,
} from '@/api/typen';
import { useSprache } from '@/i18n/SprachKontext';
import { orgBezeichnung } from '@/nutzen/bezeichnungen';
import {
  Abzeichen,
  Auswahl,
  Blatt,
  Gruppe,
  Hinweis,
  Karte,
  Knopf,
  Ladeschimmer,
  Leerzustand,
  Seitenkopf,
  Suchfeld,
  Umschalter,
  Zeile,
  ZeileKnopf,
} from '@/ui';
import { useSitzung } from '@/zustand/Sitzung';

const SCOPES: ScopeTyp[] = ['global', 'fachbereich', 'organisationseinheit'];

/**
 * Nutzer- und Rollenverwaltung (Architektur 5.3, Leitdokument A.15).
 *
 * Rollen wurden bisher nur über die API vergeben — die Anwendung konnte sich
 * selbst nicht in Betrieb nehmen. Hier bekommt das seinen Weg über den
 * Bildschirm, mit zwei Dingen, die eine API nicht mitliefert: der **Erklärung**
 * je Rolle und der **Wirkung** einer Zuweisung, bevor sie gilt.
 *
 * Sichtbar nur für den App-Administrator; der Server prüft es noch einmal
 * (Architektur 10.2). Die Rolle vergibt jeden anderen Zugriff und ist deshalb
 * die, die man am sparsamsten vergibt — das steht auch auf dem Bildschirm.
 */
export function Verwaltung() {
  const { t } = useSprache();
  const { token, profil } = useSitzung();
  const [nutzer, setNutzer] = useState<Nutzer[] | null>(null);
  const [zuweisungen, setZuweisungen] = useState<Rollenzuweisung[]>([]);
  const [rollen, setRollen] = useState<RolleErklaert[]>([]);
  const [einheiten, setEinheiten] = useState<Organisationseinheit[]>([]);
  const [fachbereiche, setFachbereiche] = useState<Fachbereich[]>([]);
  const [suche, setSuche] = useState('');
  const [offen, setOffen] = useState<Nutzer | null>(null);
  const [rolle, setRolle] = useState<Rolle>('prozess_owner');
  const [scopeTyp, setScopeTyp] = useState<ScopeTyp>('organisationseinheit');
  const [scopeId, setScopeId] = useState('');
  const [wirkung, setWirkung] = useState<Rollenwirkung | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);

  const darfVerwalten =
    profil?.rollen.some((z) => z.rolle === 'app_administrator') ?? false;

  const laden = useCallback(() => {
    if (token === null) return;
    Promise.all([
      api.nutzer(token),
      api.rollenzuweisungen(token),
      api.rollen(token),
      api.organisationseinheiten(token),
      api.fachbereiche(token),
    ])
      .then(([alle, zuweisung, rollenliste, orgs, bereiche]) => {
        setNutzer(alle);
        setZuweisungen(zuweisung);
        setRollen(rollenliste);
        setEinheiten(orgs);
        setFachbereiche(bereiche);
      })
      .catch((ausnahme) =>
        setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler')),
      );
  }, [token, t]);

  useEffect(laden, [laden]);

  /** Die Ziele, aus denen ein Scope gewählt wird — je nach Scope-Typ. */
  const scopeziele = useMemo(() => {
    if (scopeTyp === 'global') return [];
    if (scopeTyp === 'fachbereich')
      return fachbereiche.map((b) => ({ wert: b.id, text: b.name }));
    return einheiten.map((e) => ({ wert: e.id, text: orgBezeichnung(e, fachbereiche) }));
  }, [scopeTyp, fachbereiche, einheiten]);

  // Die Vorschau folgt der Auswahl: wer die Rolle wechselt, sieht sofort, was
  // sie eröffnen würde — nicht erst nach einem Klick auf „berechnen".
  useEffect(() => {
    if (token === null || offen === null) return;
    if (scopeTyp !== 'global' && scopeId === '') {
      setWirkung(null);
      return;
    }
    let gilt = true;
    api
      .rollenwirkung(token, {
        user_id: offen.id,
        rolle,
        scope_typ: scopeTyp,
        scope_id: scopeTyp === 'global' ? null : scopeId,
      })
      .then((ergebnis) => {
        if (gilt) setWirkung(ergebnis);
      })
      .catch(() => {
        if (gilt) setWirkung(null);
      });
    return () => {
      gilt = false;
    };
  }, [token, offen, rolle, scopeTyp, scopeId]);

  async function fuehreAus(aktion: () => Promise<unknown>) {
    setFehler(null);
    try {
      await aktion();
      laden();
    } catch (ausnahme) {
      setFehler(ausnahme instanceof ApiFehler ? ausnahme.message : t('app.fehler'));
    }
  }

  const scopeName = (zuweisung: Rollenzuweisung) => {
    if (zuweisung.scope_typ === 'global') return t('verwaltung.scope.global');
    if (zuweisung.scope_typ === 'fachbereich')
      return fachbereiche.find((b) => b.id === zuweisung.scope_id)?.name ?? '—';
    return orgBezeichnung(
      einheiten.find((e) => e.id === zuweisung.scope_id),
      fachbereiche,
    );
  };

  if (fehler !== null && nutzer === null) return <Hinweis art="fehler">{fehler}</Hinweis>;
  if (nutzer === null) return <Ladeschimmer beschriftung={t('app.laden')} zeilen={6} />;

  const begriff = suche.trim().toLowerCase();
  const treffer = nutzer.filter(
    (person) =>
      begriff === '' ||
      person.name.toLowerCase().includes(begriff) ||
      person.email.toLowerCase().includes(begriff),
  );

  return (
    <>
      <Seitenkopf titel={t('verwaltung.titel')} untertitel={t('verwaltung.hinweis')} />
      {fehler !== null && offen === null && <Hinweis art="fehler">{fehler}</Hinweis>}
      {!darfVerwalten && <Hinweis art="information">{t('verwaltung.nurLesen')}</Hinweis>}

      <Karte titel={t('verwaltung.nutzer')} beischrift={t('verwaltung.nutzerHinweis')}>
        <Suchfeld
          beschriftung={t('verwaltung.suche')}
          wert={suche}
          aendern={setSuche}
          platzhalter={t('verwaltung.suchePlatzhalter')}
        />
        {treffer.length === 0 ? (
          <Leerzustand titel={t('verwaltung.keineTreffer')} />
        ) : (
          <Gruppe>
            {treffer.map((person) => {
              const seine = zuweisungen.filter((z) => z.user_id === person.id);
              const fuehrung = nutzer.find((k) => k.id === person.fuehrungskraft_user_id);
              return (
                <ZeileKnopf
                  key={person.id}
                  pruefkennung={`nutzer-${person.id}`}
                  handeln={() => {
                    setOffen(person);
                    setWirkung(null);
                    setFehler(null);
                  }}
                  haupt={person.name}
                  zweitzeile={
                    <>
                      <span className="satzzeile">{person.email}</span>
                      <span className="satzzeile">
                        {t('verwaltung.fuehrungskraft')}:{' '}
                        {fuehrung?.name ?? t('verwaltung.ohneFuehrungskraft')}
                      </span>
                      {seine.length > 0 && (
                        <span className="satzzeile">
                          {seine
                            .map((z) => `${t(`rolle.${z.rolle}` as never)} (${scopeName(z)})`)
                            .join(' · ')}
                        </span>
                      )}
                    </>
                  }
                  wert={
                    <Abzeichen
                      ton={person.ist_aktiv ? 'gruen' : 'neutral'}
                      zeichen={person.ist_aktiv ? '✓' : '—'}
                    >
                      {person.ist_aktiv ? t('verwaltung.aktiv') : t('verwaltung.inaktiv')}
                    </Abzeichen>
                  }
                />
              );
            })}
          </Gruppe>
        )}
      </Karte>

      {offen !== null && (
        <Blatt
          titel={offen.name}
          beischrift={offen.email}
          schliessen={() => setOffen(null)}
          fuss={
            <Knopf
              art="gefuellt"
              disabled={!darfVerwalten || (scopeTyp !== 'global' && scopeId === '')}
              onClick={() =>
                fuehreAus(async () => {
                  await api.rolleZuweisen(token as string, {
                    user_id: offen.id,
                    rolle,
                    scope_typ: scopeTyp,
                    scope_id: scopeTyp === 'global' ? null : scopeId,
                  });
                })
              }
              data-testid="rolle-zuweisen"
            >
              {t('verwaltung.zuweisen')}
            </Knopf>
          }
        >
          {fehler !== null && <Hinweis art="fehler">{fehler}</Hinweis>}

          <Umschalter
            beschriftung={t('verwaltung.aktivstatus')}
            an={offen.ist_aktiv}
            aendern={(an) =>
              fuehreAus(async () => {
                const neu = await api.nutzerAendern(token as string, offen.id, { ist_aktiv: an });
                setOffen(neu);
              })
            }
          />
          <Auswahl
            beschriftung={t('verwaltung.fuehrungskraft')}
            wert={offen.fuehrungskraft_user_id ?? ''}
            aendern={(wert) =>
              fuehreAus(async () => {
                const neu = await api.nutzerAendern(token as string, offen.id, {
                  fuehrungskraft_user_id: wert === '' ? null : wert,
                });
                setOffen(neu);
              })
            }
            leertext={t('verwaltung.ohneFuehrungskraft')}
            optionen={nutzer
              .filter((k) => k.id !== offen.id)
              .map((k) => ({ wert: k.id, text: k.name }))}
            hilfe={t('verwaltung.fuehrungskraftHilfe')}
          />

          <Gruppe etikett={t('verwaltung.bestehende')}>
            {zuweisungen.filter((z) => z.user_id === offen.id).length === 0 ? (
              <Zeile haupt={t('verwaltung.keineRolle')} />
            ) : (
              zuweisungen
                .filter((z) => z.user_id === offen.id)
                .map((z) => (
                  <Zeile
                    key={z.id}
                    pruefkennung={`zuweisung-${z.id}`}
                    haupt={t(`rolle.${z.rolle}` as never)}
                    zweitzeile={scopeName(z)}
                    wert={
                      <Knopf
                        disabled={!darfVerwalten}
                        onClick={() =>
                          fuehreAus(() => api.rolleEntziehen(token as string, z.id))
                        }
                        data-testid={`entziehen-${z.id}`}
                      >
                        {t('verwaltung.entziehen')}
                      </Knopf>
                    }
                  />
                ))
            )}
          </Gruppe>

          <Auswahl
            beschriftung={t('verwaltung.rolle')}
            wert={rolle}
            aendern={(wert) => setRolle(wert as Rolle)}
            optionen={rollen.map((r) => ({
              wert: r.schluessel,
              text: t(`rolle.${r.schluessel}` as never),
            }))}
            hilfe={rollen.find((r) => r.schluessel === rolle)?.erklaerung}
          />
          <Auswahl
            beschriftung={t('verwaltung.scopeTyp')}
            wert={scopeTyp}
            aendern={(wert) => {
              setScopeTyp(wert as ScopeTyp);
              setScopeId('');
            }}
            optionen={SCOPES.map((wert) => ({
              wert,
              text: t(`verwaltung.scope.${wert}` as never),
            }))}
          />
          {scopeTyp !== 'global' && (
            <Auswahl
              // Die Beschriftung nennt, was gewählt wird — „Bereich" neben
              // „Geltungsbereich" wäre für Auge und Vorleseprogramm dasselbe.
              beschriftung={t(`verwaltung.scope.${scopeTyp}` as never)}
              wert={scopeId}
              aendern={setScopeId}
              leertext="—"
              optionen={scopeziele}
              pflicht
            />
          )}

          {/* Die Wirkung steht vor der Entscheidung, nicht danach:
              „Prozess-Owner auf FIN-INT" sagt niemandem, wie viel Zugriff das
              ist. */}
          {wirkung !== null && (
            <Hinweis art="information">
              <span data-testid="wirkung">
                {t('verwaltung.wirkung')
                  .replace('{prozesse}', String(wirkung.prozessobjekte))
                  .replace('{tools}', String(wirkung.tool_objekte))
                  .replace('{scope}', wirkung.scope_name || '—')}
              </span>
              {wirkung.beispiele.length > 0 && (
                <span className="satzzeile">
                  {t('verwaltung.wirkungBeispiele')}: {wirkung.beispiele.join(', ')}
                </span>
              )}
            </Hinweis>
          )}
        </Blatt>
      )}
    </>
  );
}
