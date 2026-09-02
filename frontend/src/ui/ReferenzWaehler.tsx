/**
 * Design-System „Klar" — Referenz-Waehler.
 *
 * Das Kernstueck der Oberflaeche: ueberall, wo die Vorgabe eine Referenz
 * verlangt (Leitdokument P5 — „referenzieren, nie duplizieren"), steht dieser
 * Baustein statt eines Freitextfelds. Er sucht im Bestand, zeigt beim Treffer
 * sofort dessen Einstufung und legt die Auswahl als entfernbare Chips ab.
 *
 * Bedienung vollstaendig ueber die Tastatur: Pfeiltasten waehlen, Eingabe
 * uebernimmt, Rueckschritt im leeren Feld entfernt den letzten Chip, Escape
 * schliesst die Trefferliste.
 */

import { useId, useMemo, useRef, useState, type KeyboardEvent } from 'react';

import { Abzeichen, type Ton } from '@/ui/Basis';

export interface Referenz {
  id: string;
  name: string;
  /** Zweite Zeile im Treffer, etwa Quellsystem oder Fachbereich. */
  zusatz?: string;
  /** Einstufung, die der Nutzer beim Auswaehlen sehen soll. */
  abzeichen?: string;
  ton?: Ton;
}

export function ReferenzWaehler({
  beschriftung,
  hilfe,
  bestand,
  gewaehlt,
  aendern,
  platzhalter,
  keineTreffer,
  pruefkennung,
}: {
  beschriftung: string;
  hilfe?: string;
  bestand: Referenz[];
  gewaehlt: string[];
  aendern: (ids: string[]) => void;
  platzhalter?: string;
  keineTreffer: string;
  pruefkennung?: string;
}) {
  const kennung = useId();
  const eingabe = useRef<HTMLInputElement>(null);
  const [suche, setSuche] = useState('');
  const [offen, setOffen] = useState(false);
  const [hervorgehoben, setHervorgehoben] = useState(0);

  const gewaehlteObjekte = useMemo(
    () =>
      gewaehlt
        .map((id) => bestand.find((eintrag) => eintrag.id === id))
        .filter((eintrag): eintrag is Referenz => eintrag !== undefined),
    [gewaehlt, bestand],
  );

  const treffer = useMemo(() => {
    const begriff = suche.trim().toLowerCase();
    return bestand
      .filter((eintrag) => !gewaehlt.includes(eintrag.id))
      .filter(
        (eintrag) =>
          begriff === '' ||
          eintrag.name.toLowerCase().includes(begriff) ||
          (eintrag.zusatz ?? '').toLowerCase().includes(begriff),
      )
      .slice(0, 8);
  }, [bestand, gewaehlt, suche]);

  function waehle(eintrag: Referenz) {
    aendern([...gewaehlt, eintrag.id]);
    setSuche('');
    setHervorgehoben(0);
    eingabe.current?.focus();
  }

  function entferne(id: string) {
    aendern(gewaehlt.filter((vorhanden) => vorhanden !== id));
  }

  function beiTaste(ereignis: KeyboardEvent<HTMLInputElement>) {
    if (ereignis.key === 'ArrowDown') {
      ereignis.preventDefault();
      setOffen(true);
      setHervorgehoben((bisher) => (treffer.length === 0 ? 0 : (bisher + 1) % treffer.length));
    } else if (ereignis.key === 'ArrowUp') {
      ereignis.preventDefault();
      setHervorgehoben((bisher) =>
        treffer.length === 0 ? 0 : (bisher - 1 + treffer.length) % treffer.length,
      );
    } else if (ereignis.key === 'Enter') {
      const gewaehlterTreffer = treffer[hervorgehoben];
      if (offen && gewaehlterTreffer !== undefined) {
        ereignis.preventDefault();
        waehle(gewaehlterTreffer);
      }
    } else if (ereignis.key === 'Escape') {
      setOffen(false);
    } else if (ereignis.key === 'Backspace' && suche === '' && gewaehlt.length > 0) {
      entferne(gewaehlt[gewaehlt.length - 1]);
    }
  }

  return (
    <div className="k-feld k-referenz" data-testid={pruefkennung}>
      <label className="beschriftung" htmlFor={kennung}>
        {beschriftung}
      </label>

      {gewaehlteObjekte.length > 0 && (
        <div className="chips">
          {gewaehlteObjekte.map((eintrag) => (
            <span className="k-chip" key={eintrag.id}>
              {eintrag.name}
              <button
                type="button"
                aria-label={`${eintrag.name} entfernen`}
                onClick={() => entferne(eintrag.id)}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      <input
        id={kennung}
        ref={eingabe}
        type="text"
        role="combobox"
        autoComplete="off"
        aria-expanded={offen}
        aria-controls={`${kennung}-treffer`}
        aria-activedescendant={
          offen && treffer.length > 0 ? `${kennung}-treffer-${hervorgehoben}` : undefined
        }
        aria-describedby={hilfe !== undefined ? `${kennung}-hilfe` : undefined}
        placeholder={platzhalter}
        value={suche}
        onChange={(e) => {
          setSuche(e.target.value);
          setOffen(true);
          setHervorgehoben(0);
        }}
        onFocus={() => setOffen(true)}
        onBlur={() => window.setTimeout(() => setOffen(false), 120)}
        onKeyDown={beiTaste}
      />

      {offen && (
        <ul className="treffer" id={`${kennung}-treffer`} role="listbox" aria-label={beschriftung}>
          {treffer.length === 0 ? (
            <li className="leer" role="option" aria-selected="false">
              {keineTreffer}
            </li>
          ) : (
            treffer.map((eintrag, nummer) => (
              <li
                key={eintrag.id}
                id={`${kennung}-treffer-${nummer}`}
                role="option"
                aria-selected={nummer === hervorgehoben}
              >
                <button
                  type="button"
                  tabIndex={-1}
                  onMouseDown={(ereignis) => ereignis.preventDefault()}
                  onClick={() => waehle(eintrag)}
                >
                  <span className="haupt">
                    {eintrag.name}
                    {eintrag.zusatz !== undefined && (
                      <span className="zweitzeile">{eintrag.zusatz}</span>
                    )}
                  </span>
                  {eintrag.abzeichen !== undefined && (
                    <span className="wert">
                      <Abzeichen ton={eintrag.ton}>{eintrag.abzeichen}</Abzeichen>
                    </span>
                  )}
                </button>
              </li>
            ))
          )}
        </ul>
      )}

      {hilfe !== undefined && (
        <span className="hilfe" id={`${kennung}-hilfe`}>
          {hilfe}
        </span>
      )}
    </div>
  );
}
