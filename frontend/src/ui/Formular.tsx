/**
 * Design-System „Klar" — Eingabebausteine.
 *
 * Jede Beschriftung ist mit ihrem Steuerelement verbunden, jeder Fehler wird
 * ueber ``aria-describedby`` angekuendigt: die Oberflaeche ist ohne Maus und
 * ohne Blick auf Farbe bedienbar.
 */

import { useId, type ReactNode } from 'react';

interface FeldRahmen {
  beschriftung: string;
  hilfe?: string;
  fehler?: string;
  pflicht?: boolean;
}

function beschreibung(fehler: string | undefined, hilfe: string | undefined, kennung: string) {
  const teile: string[] = [];
  if (fehler !== undefined) teile.push(`${kennung}-fehler`);
  if (hilfe !== undefined) teile.push(`${kennung}-hilfe`);
  return teile.length > 0 ? teile.join(' ') : undefined;
}

export function Feld({
  beschriftung: text,
  wert,
  aendern,
  hilfe,
  fehler,
  pflicht = false,
  mehrzeilig = false,
  hoechstlaenge,
  platzhalter,
  beschriftungVerborgen = false,
  disabled = false,
}: FeldRahmen & {
  wert: string;
  aendern: (wert: string) => void;
  mehrzeilig?: boolean;
  hoechstlaenge?: number;
  platzhalter?: string;
  /** Wie bei ``Auswahl``: nur fuer Vorleseprogramme, in Listenzeilen. */
  beschriftungVerborgen?: boolean;
  disabled?: boolean;
}) {
  const kennung = useId();
  const gemeinsam = {
    id: kennung,
    value: wert,
    required: pflicht,
    disabled,
    maxLength: hoechstlaenge,
    placeholder: platzhalter,
    'aria-describedby': beschreibung(fehler, hilfe, kennung),
    'aria-invalid': fehler !== undefined ? true : undefined,
    onChange: (e: { target: { value: string } }) => aendern(e.target.value),
  };
  return (
    <div
      className={`k-feld${fehler !== undefined ? ' k-feld--fehlerhaft' : ''}${pflicht ? ' k-feld--pflicht' : ''}${beschriftungVerborgen ? ' k-feld--schmal' : ''}`}
    >
      <label
        className={beschriftungVerborgen ? 'k-nur-vorlesen' : 'beschriftung'}
        htmlFor={kennung}
      >
        {text}
      </label>
      {mehrzeilig ? <textarea {...gemeinsam} /> : <input {...gemeinsam} />}
      {fehler !== undefined && (
        <span className="fehler" id={`${kennung}-fehler`}>
          {fehler}
        </span>
      )}
      {hilfe !== undefined && (
        <span className="hilfe" id={`${kennung}-hilfe`}>
          {hilfe}
        </span>
      )}
      {hoechstlaenge !== undefined && (
        <span className="zaehler">
          {wert.length} / {hoechstlaenge}
        </span>
      )}
    </div>
  );
}

export interface AuswahlOption {
  wert: string;
  text: string;
}

export function Auswahl({
  beschriftung: text,
  wert,
  aendern,
  optionen,
  hilfe,
  fehler,
  pflicht = false,
  leertext,
  beschriftungVerborgen = false,
  gesperrt = false,
}: FeldRahmen & {
  wert: string;
  aendern: (wert: string) => void;
  optionen: AuswahlOption[];
  leertext?: string;
  /**
   * Der Baustein bleibt sichtbar, nimmt aber keine Eingabe an.
   *
   * Wer nichts aendern darf, soll den Wert trotzdem sehen — ein
   * ausgeblendetes Feld waere eine Luecke im Bild, kein Schutz. Der Server
   * prueft ohnehin unabhaengig (Architektur 10.2).
   */
  gesperrt?: boolean;
  /**
   * Beschriftung nur fuer Vorleseprogramme.
   *
   * Fuer Auswahlen in einer Listenzeile: die Zeile nennt den Gegenstand
   * bereits, eine zweite sichtbare Beschriftung waere Laerm — verbunden bleibt
   * sie trotzdem.
   */
  beschriftungVerborgen?: boolean;
}) {
  const kennung = useId();
  return (
    <div
      className={`k-feld${fehler !== undefined ? ' k-feld--fehlerhaft' : ''}${pflicht ? ' k-feld--pflicht' : ''}${beschriftungVerborgen ? ' k-feld--schmal' : ''}`}
    >
      <label
        className={beschriftungVerborgen ? 'k-nur-vorlesen' : 'beschriftung'}
        htmlFor={kennung}
      >
        {text}
      </label>
      <select
        id={kennung}
        value={wert}
        required={pflicht}
        disabled={gesperrt}
        aria-describedby={beschreibung(fehler, hilfe, kennung)}
        aria-invalid={fehler !== undefined ? true : undefined}
        onChange={(e) => aendern(e.target.value)}
      >
        {leertext !== undefined && <option value="">{leertext}</option>}
        {optionen.map((option) => (
          <option key={option.wert} value={option.wert}>
            {option.text}
          </option>
        ))}
      </select>
      {fehler !== undefined && (
        <span className="fehler" id={`${kennung}-fehler`}>
          {fehler}
        </span>
      )}
      {hilfe !== undefined && (
        <span className="hilfe" id={`${kennung}-hilfe`}>
          {hilfe}
        </span>
      )}
    </div>
  );
}

export function Umschalter({
  beschriftung: text,
  zweitzeile,
  hilfe,
  an,
  aendern,
  gesperrt = false,
}: {
  beschriftung: string;
  zweitzeile?: string;
  /**
   * Erklaerung zum Schalter — ueber ``aria-describedby`` angebunden, nicht in
   * der Beschriftung. Ein ganzer Satz im zugaenglichen Namen wird bei jedem
   * Fokuswechsel vorgelesen; als Beschreibung wird er einmal genannt.
   */
  hilfe?: string;
  an: boolean;
  aendern: (an: boolean) => void;
  /** Sichtbar, aber nicht bedienbar — siehe ``Auswahl``. */
  gesperrt?: boolean;
}) {
  const kennung = useId();
  return (
    <div className="k-umschalter-rahmen">
      <label className="k-umschalter">
        <span className="text">
          {text}
          {zweitzeile !== undefined && <span className="zweitzeile">{zweitzeile}</span>}
        </span>
        <input
          type="checkbox"
          checked={an}
          disabled={gesperrt}
          aria-describedby={hilfe === undefined ? undefined : `${kennung}-hilfe`}
          onChange={(e) => aendern(e.target.checked)}
        />
      </label>
      {hilfe !== undefined && (
        <span className="hinweis" id={`${kennung}-hilfe`}>
          {hilfe}
        </span>
      )}
    </div>
  );
}

export function SegmentierteSteuerung<T extends string>({
  beschriftung,
  wert,
  aendern,
  optionen,
  beschriftungZeigen = false,
  hilfe,
  gesperrt = false,
}: {
  beschriftung: string;
  wert: T;
  aendern: (wert: T) => void;
  optionen: { wert: T; text: string }[];
  /** Sichtbar, aber nicht bedienbar — siehe ``Auswahl``. */
  gesperrt?: boolean;
  /** Sichtbare Beschriftung, wo die Knopftexte allein nicht sagen, worum es geht. */
  beschriftungZeigen?: boolean;
  hilfe?: string;
}) {
  const gruppe = (
    <div className="k-segmente" role="group" aria-label={beschriftung}>
      {optionen.map((option) => (
        <button
          key={option.wert}
          type="button"
          aria-pressed={option.wert === wert}
          disabled={gesperrt}
          onClick={() => aendern(option.wert)}
        >
          {option.text}
        </button>
      ))}
    </div>
  );
  if (!beschriftungZeigen && hilfe === undefined) return gruppe;
  return (
    <div className="k-feld">
      {beschriftungZeigen && <span className="beschriftung">{beschriftung}</span>}
      {gruppe}
      {hilfe !== undefined && <span className="hilfe">{hilfe}</span>}
    </div>
  );
}

export function Suchfeld({
  beschriftung,
  wert,
  aendern,
  platzhalter,
}: {
  beschriftung: string;
  wert: string;
  aendern: (wert: string) => void;
  platzhalter?: string;
}) {
  return (
    <div className="k-suche">
      <span className="lupe" aria-hidden="true">
        ⌕
      </span>
      <input
        type="search"
        aria-label={beschriftung}
        value={wert}
        placeholder={platzhalter}
        onChange={(e) => aendern(e.target.value)}
      />
    </div>
  );
}

export function Feldgruppe({ titel, children }: { titel?: string; children: ReactNode }) {
  return (
    <fieldset className="k-feldgruppe">
      {titel !== undefined && <legend>{titel}</legend>}
      {children}
    </fieldset>
  );
}
