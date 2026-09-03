import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { useSprache } from '@/i18n/SprachKontext';
import { liesVortrag, type Block, type Folie, type Teil } from '@/nutzen/folien';
import { Hinweis, Karte, Knopf, SegmentierteSteuerung, Seitenkopf } from '@/ui';

// Die eine Quelle: dieselbe Datei, die im Repository liegt und die Marp zu
// einem PDF macht. Vite liest sie beim Bauen ein — es gibt keine zweite,
// gepflegte Fassung im Frontend (siehe `nutzen/folien.ts`).
import quelle from '../../../docs/praesentation.md?raw';

// Die Bildschirmfotos liegen neben dem Dokument. Der Vortrag adressiert sie
// relativ (`bilder/cockpit.png`); hier werden daraus die Adressen, unter denen
// der Bau sie ablegt.
const BILDER = import.meta.glob('../../../docs/bilder/*.png', {
  eager: true,
  query: '?url',
  import: 'default',
}) as Record<string, string>;

function bildAdresse(quelle: string): string | undefined {
  const name = quelle.split('/').pop();
  const treffer = Object.entries(BILDER).find(([pfad]) => pfad.endsWith(`/${name}`));
  return treffer?.[1];
}

function Textteile({ teile }: { teile: Teil[] }) {
  return (
    <>
      {teile.map((teil, stelle) => {
        const schluessel = `${stelle}-${teil.text.slice(0, 12)}`;
        if (teil.art === 'stark') return <strong key={schluessel}>{teil.text}</strong>;
        if (teil.art === 'betont') return <em key={schluessel}>{teil.text}</em>;
        if (teil.art === 'code') return <code key={schluessel}>{teil.text}</code>;
        return <span key={schluessel}>{teil.text}</span>;
      })}
    </>
  );
}

function Blockinhalt({ block }: { block: Block }) {
  if (block.art === 'ueberschrift') {
    return block.ebene === 1 ? (
      <h2 className="leitfolie">
        <Textteile teile={block.inhalt} />
      </h2>
    ) : (
      <h2>
        <Textteile teile={block.inhalt} />
      </h2>
    );
  }
  if (block.art === 'absatz') {
    return (
      <p>
        <Textteile teile={block.inhalt} />
      </p>
    );
  }
  if (block.art === 'liste') {
    const punkte = block.punkte.map((punkt, stelle) => (
      <li key={`${stelle}-${punkt[0]?.text.slice(0, 12) ?? ''}`}>
        <Textteile teile={punkt} />
      </li>
    ));
    return block.geordnet ? <ol>{punkte}</ol> : <ul>{punkte}</ul>;
  }
  if (block.art === 'zitat') {
    return (
      <blockquote>
        {block.absaetze.map((absatz, stelle) => (
          <p key={`${stelle}-${absatz[0]?.text.slice(0, 12) ?? ''}`}>
            <Textteile teile={absatz} />
          </p>
        ))}
      </blockquote>
    );
  }
  if (block.art === 'code') {
    return (
      <pre>
        <code>{block.text}</code>
      </pre>
    );
  }
  if (block.art === 'bild') {
    const adresse = bildAdresse(block.quelle);
    if (adresse === undefined) return null;
    return <img src={adresse} alt="" style={block.breite ? { maxWidth: '100%' } : undefined} />;
  }
  return (
    <div className="k-tabellenrahmen">
      <table>
        <thead>
          <tr>
            {block.kopf.map((zelle, stelle) => (
              <th key={`${stelle}-${zelle[0]?.text ?? ''}`} scope="col">
                <Textteile teile={zelle} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {block.zeilen.map((reihe, zeile) => (
            <tr key={`${zeile}-${reihe[0]?.[0]?.text ?? ''}`}>
              {reihe.map((zelle, spalte) => (
                <td key={`${spalte}-${zelle[0]?.text ?? ''}`}>
                  <Textteile teile={zelle} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Folieninhalt({ folie }: { folie: Folie }) {
  return (
    <>
      {folie.bloecke.map((block, stelle) => (
        <Blockinhalt key={`${stelle}-${block.art}`} block={block} />
      ))}
    </>
  );
}

type Ansicht = 'vortrag' | 'dokument';

/**
 * Das Konzept — als Vortrag und als Dokument (Leitdokument A.1 bis A.16).
 *
 * Der Vortrag erklärt das Vorgehen; er bittet um keine Erlaubnis. Deshalb
 * steht er in der Anwendung selbst und nicht nur als Datei daneben: wer
 * wissen will, warum die Anwendung etwas verlangt, findet die Begründung
 * dort, wo er arbeitet.
 *
 * Zwei Ansichten für zwei Anlässe. **Vortrag** zeigt eine Folie und lässt sich
 * mit den Pfeiltasten und im Vollbild führen — das ist der Modus für den Raum.
 * **Dokument** setzt alles untereinander, zum Lesen und Nachschlagen. Die
 * Foliennummer steht in der Adresse; eine Stelle im Vortrag ist damit
 * genauso teilbar wie ein gefilterter Cockpit-Ausschnitt (Architektur 9.3).
 */
export function Konzept() {
  const { t, sprache } = useSprache();
  const [suche, setSuche] = useSearchParams();
  const [ansicht, setAnsicht] = useState<Ansicht>('vortrag');
  const buehne = useRef<HTMLDivElement>(null);

  const folien = useMemo(() => liesVortrag(quelle), []);
  const gewaehlt = Number(suche.get('folie') ?? '1');
  const nummer = Number.isFinite(gewaehlt) ? Math.min(Math.max(gewaehlt, 1), folien.length) : 1;
  const folie = folien[nummer - 1];

  const springe = useCallback(
    (ziel: number) => {
      const begrenzt = Math.min(Math.max(ziel, 1), folien.length);
      setSuche(begrenzt === 1 ? {} : { folie: String(begrenzt) }, { replace: true });
    },
    [folien.length, setSuche],
  );

  useEffect(() => {
    if (ansicht !== 'vortrag') return undefined;
    const taste = (ereignis: KeyboardEvent) => {
      if (ereignis.target instanceof HTMLElement && ereignis.target.closest('input, select')) return;
      if (ereignis.key === 'ArrowRight' || ereignis.key === 'PageDown') springe(nummer + 1);
      else if (ereignis.key === 'ArrowLeft' || ereignis.key === 'PageUp') springe(nummer - 1);
      else if (ereignis.key === 'Home') springe(1);
      else if (ereignis.key === 'End') springe(folien.length);
      else return;
      ereignis.preventDefault();
    };
    window.addEventListener('keydown', taste);
    return () => window.removeEventListener('keydown', taste);
  }, [ansicht, nummer, folien.length, springe]);

  const vollbild = () => {
    const flaeche = buehne.current;
    if (flaeche === null) return;
    if (document.fullscreenElement === null) void flaeche.requestFullscreen?.();
    else void document.exitFullscreen?.();
  };

  return (
    <>
      <Seitenkopf
        titel={t('konzept.titel')}
        untertitel={t('konzept.hinweis')}
        aktionen={
          <SegmentierteSteuerung<Ansicht>
            beschriftung={t('konzept.ansicht')}
            wert={ansicht}
            aendern={setAnsicht}
            optionen={[
              { wert: 'vortrag', text: t('konzept.ansicht.vortrag') },
              { wert: 'dokument', text: t('konzept.ansicht.dokument') },
            ]}
          />
        }
      />

      {sprache !== 'de' && <Hinweis art="information">{t('konzept.nurDeutsch')}</Hinweis>}

      {ansicht === 'vortrag' ? (
        <div className="k-vortrag" ref={buehne}>
          <div
            className="fortschritt"
            role="progressbar"
            aria-valuenow={nummer}
            aria-valuemin={1}
            aria-valuemax={folien.length}
            aria-label={t('konzept.fortschritt')}
          >
            <span style={{ inlineSize: `${(nummer / folien.length) * 100}%` }} />
          </div>

          <article
            className={`folie${folie.klasse ? ` ${folie.klasse}` : ''}`}
            data-testid={`folie-${nummer}`}
            aria-label={folie.titel}
          >
            <Folieninhalt folie={folie} />
          </article>

          <footer className="steuerung">
            <Knopf onClick={() => springe(nummer - 1)} disabled={nummer === 1}>
              {t('konzept.zurueck')}
            </Knopf>
            <span className="zaehler" aria-live="polite">
              {nummer} / {folien.length}
            </span>
            <Knopf onClick={() => springe(nummer + 1)} disabled={nummer === folien.length}>
              {t('konzept.weiter')}
            </Knopf>
            <Knopf art="unauffaellig" onClick={vollbild}>
              {t('konzept.vollbild')}
            </Knopf>
          </footer>
        </div>
      ) : (
        <div className="k-vortragsdokument">
          {folien.map((eintrag) => (
            <Karte key={eintrag.nummer}>
              <span className="nummer" aria-hidden="true">
                {eintrag.nummer}
              </span>
              <div className="folie">
                <Folieninhalt folie={eintrag} />
              </div>
            </Karte>
          ))}
        </div>
      )}
    </>
  );
}
