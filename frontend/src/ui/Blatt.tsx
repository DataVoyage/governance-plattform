/**
 * Design-System „Klar" — Blatt (Sheet).
 *
 * Legt sich ueber die Seite, statt sie zu verlassen: Anlegen, Bestaetigen und
 * der Bewertungs-Wizard behalten so ihren Zusammenhang. Der Fokus bleibt im
 * Blatt gefangen, ``Esc`` schliesst.
 */

import { useEffect, useRef, type ReactNode } from 'react';

const FOKUSSIERBAR =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function Blatt({
  titel,
  beischrift,
  schliessen,
  fuss,
  children,
}: {
  titel: string;
  beischrift?: string;
  schliessen: () => void;
  fuss?: ReactNode;
  children: ReactNode;
}) {
  const blatt = useRef<HTMLDivElement>(null);
  // Der Rueckruf wechselt bei jedem Zeichen die Identitaet, weil die
  // aufrufende Seite ihn inline erzeugt. Er darf deshalb nicht in der
  // Abhaengigkeitsliste stehen: sonst liefe der Effekt bei jedem Tastendruck
  // erneut und wuerde den Fokus zurueck ins erste Feld ziehen.
  const schliessenRef = useRef(schliessen);
  schliessenRef.current = schliessen;

  useEffect(() => {
    const vorher = document.activeElement as HTMLElement | null;
    blatt.current?.querySelector<HTMLElement>(FOKUSSIERBAR)?.focus();

    function beiTaste(ereignis: KeyboardEvent) {
      if (ereignis.key === 'Escape') {
        schliessenRef.current();
        return;
      }
      if (ereignis.key !== 'Tab' || blatt.current === null) return;
      const ziele = Array.from(blatt.current.querySelectorAll<HTMLElement>(FOKUSSIERBAR));
      if (ziele.length === 0) return;
      const erster = ziele[0];
      const letzter = ziele[ziele.length - 1];
      if (ereignis.shiftKey && document.activeElement === erster) {
        ereignis.preventDefault();
        letzter.focus();
      } else if (!ereignis.shiftKey && document.activeElement === letzter) {
        ereignis.preventDefault();
        erster.focus();
      }
    }

    document.addEventListener('keydown', beiTaste);
    return () => {
      document.removeEventListener('keydown', beiTaste);
      vorher?.focus();
    };
    // Nur beim Oeffnen: Fokus setzen und Falle stellen.
  }, []);

  return (
    <div
      className="k-blatt-grund"
      onMouseDown={(ereignis) => {
        if (ereignis.target === ereignis.currentTarget) schliessen();
      }}
    >
      <div className="k-blatt" role="dialog" aria-modal="true" aria-label={titel} ref={blatt}>
        <header>
          <div>
            <h2>{titel}</h2>
            {beischrift !== undefined && <p className="beischrift">{beischrift}</p>}
          </div>
        </header>
        {children}
        {fuss !== undefined && <div className="k-blatt-fuss">{fuss}</div>}
      </div>
    </div>
  );
}
