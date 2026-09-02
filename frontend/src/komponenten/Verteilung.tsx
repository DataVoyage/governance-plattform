import { useSprache } from '@/i18n/SprachKontext';
import { Karte } from '@/ui';

/** Die Tier-Stufen in ihrer Ordnung — die Farbrolle folgt der Einstufung. */
const TIER = ['1', '2', '3'] as const;

/**
 * Tier-Verteilung je Technologie und je Zeit (Leitdokument A.14).
 *
 * Drei Vorgaben tragen die Darstellung:
 *
 * * **Farbrolle.** Die Farbe steht für die Einstufung, nicht für die Reihe:
 *   Tier 1 ruhig, Tier 2 gelb, Tier 3 rot — dieselben Töne wie überall sonst
 *   in der Anwendung. Eine Legende, die für jedes Diagramm neue Farben
 *   vergibt, zwingt zum Nachschlagen.
 * * **Achsen.** Die Kategorie steht links am Balken und ist lesbar, ohne den
 *   Kopf zu drehen; die Menge steht als Zahl **am** Segment. Eine Skala, die
 *   man auf ein Lineal beziehen muss, beantwortet die Frage „wie viele" nicht.
 * * **Zugänglichkeit.** Farbe ist nie der einzige Bedeutungsträger: jedes
 *   Segment nennt seine Stufe und seine Zahl, und dieselben Werte stehen als
 *   Tabelle für Vorleseprogramme darunter.
 */
export function Verteilung({ aggregat }: { aggregat: Record<string, unknown> }) {
  const { t } = useSprache();

  const gruppen = Object.entries(aggregat).filter(
    (eintrag): eintrag is [string, Record<string, Record<string, number>>] =>
      typeof eintrag[1] === 'object' && eintrag[1] !== null,
  );

  return (
    <>
      {gruppen.map(([gruppe, werte]) => {
        const zeilen = Object.entries(werte);
        const summen = zeilen.map(([, verteilung]) =>
          TIER.reduce((summe, stufe) => summe + (verteilung[stufe] ?? 0), 0),
        );
        const hoechste = Math.max(1, ...summen);

        return (
          <Karte
            key={gruppe}
            titel={t(`cockpit.verteilung.${gruppe}` as never)}
            beischrift={t('cockpit.verteilung.hinweis')}
          >
            {zeilen.length === 0 ? (
              <p className="leerhinweis">{t('cockpit.verteilung.leer')}</p>
            ) : (
              <>
                <div className="k-legende" aria-hidden="true">
                  {TIER.map((stufe) => (
                    <span key={stufe} className="eintrag" data-tier={stufe}>
                      <span className="feld" />
                      {t('bewertung.tier')} {stufe}
                    </span>
                  ))}
                </div>

                <div className="k-verteilung" data-testid={`verteilung-${gruppe}`}>
                  {zeilen.map(([schluessel, verteilung]) => {
                    const summe = TIER.reduce(
                      (wert, stufe) => wert + (verteilung[stufe] ?? 0),
                      0,
                    );
                    return (
                      <div className="reihe" key={schluessel}>
                        <span className="kategorie">
                          {gruppe === 'je_technologie'
                            ? (t(`technologie.${schluessel}` as never) ?? schluessel)
                            : schluessel}
                        </span>
                        <span className="balken" style={{ inlineSize: `${(summe / hoechste) * 100}%` }}>
                          {TIER.map((stufe) =>
                            (verteilung[stufe] ?? 0) === 0 ? null : (
                              <span
                                key={stufe}
                                className="segment"
                                data-tier={stufe}
                                style={{ flexGrow: verteilung[stufe] }}
                              >
                                {verteilung[stufe]}
                              </span>
                            ),
                          )}
                        </span>
                        <span className="summe">{summe}</span>
                      </div>
                    );
                  })}
                </div>

                {/* Dieselben Werte ohne Farbe und ohne Länge — die Fassung,
                    die ein Vorleseprogramm nutzt. */}
                <table className="k-nur-vorlesen">
                  <caption>{t(`cockpit.verteilung.${gruppe}` as never)}</caption>
                  <thead>
                    <tr>
                      <th scope="col">{t('cockpit.verteilung.kategorie')}</th>
                      {TIER.map((stufe) => (
                        <th scope="col" key={stufe}>
                          {t('bewertung.tier')} {stufe}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {zeilen.map(([schluessel, verteilung]) => (
                      <tr key={schluessel}>
                        <th scope="row">{schluessel}</th>
                        {TIER.map((stufe) => (
                          <td key={stufe}>{verteilung[stufe] ?? 0}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </Karte>
        );
      })}
    </>
  );
}
