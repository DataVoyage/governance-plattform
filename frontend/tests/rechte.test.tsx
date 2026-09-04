/**
 * Rollen wirken bis in die Oberfläche.
 *
 * Bis hierher zeigte die Anwendung jedem alles, ließ alles bearbeiten und
 * lieferte den Bescheid erst beim Speichern als 403 — der Anwender erfuhr also
 * erst nach getaner Arbeit, dass er sie nicht tun durfte.
 *
 * Die Regeln stehen weiterhin ausschließlich auf dem Server; er schreibt sie
 * als `rechte` an jedes Objekt. Diese Tests halten fest, dass die Oberfläche
 * sie auch auswertet — und dass sie erklärt, warum etwas fehlt.
 */

import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import {
  ALLE_DATENOBJEKTRECHTE,
  ALLE_PROZESSRECHTE,
  ALLE_TOOLRECHTE,
  EINHEITEN,
  PROFIL,
  fetchAttrappe,
  prozess,
  rahmen,
  tool,
  zeichne,
} from './hilfen';

const OHNE_PROZESSRECHTE = {
  bearbeiten: false,
  bewerten: false,
  selbstverpflichten: false,
  gate_einreichen: false,
  umsetzung_pflegen: false,
};

const OHNE_TOOLRECHTE = {
  bearbeiten: false,
  attestieren: false,
  verknuepfen: false,
  zustand_melden: false,
  kompensieren: false,
  selbstverpflichten: false,
  bestaetigen: false,
};

const OHNE_DATENOBJEKTRECHTE = {
  bearbeiten: false,
  kategorisieren: false,
  anker_aendern: false,
  bestaetigen: false,
};

function prozessAttrappe(rechte: typeof ALLE_PROZESSRECHTE) {
  fetchAttrappe([
    { pfad: '/api/v1/auth/me', koerper: PROFIL },
    { pfad: /\/prozesse\/p-1$/, koerper: prozess({ id: 'p-1', rechte }) },
    { pfad: /\/bewertungen$/, koerper: [] },
    { pfad: /\/selbstverpflichtungen\/deckung/, koerper: null },
    { pfad: /\/gates$/, koerper: [] },
    { pfad: '/api/v1/gate-ausloeser', koerper: [] },
    { pfad: '/api/v1/prozesse', koerper: [] },
    { pfad: '/api/v1/tools', koerper: [] },
    { pfad: '/api/v1/datenobjekte', koerper: [] },
    { pfad: '/api/v1/nutzer', koerper: [] },
    { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    { pfad: '/api/v1/fachbereiche', koerper: [] },
  ]);
}

describe('Prozessobjekt', () => {
  it('zeigt dem Berechtigten die Schaltflächen', async () => {
    prozessAttrappe(ALLE_PROZESSRECHTE);
    zeichne('/de/prozesse/p-1');
    expect(await screen.findByRole('link', { name: 'Bearbeiten' })).toBeInTheDocument();
  });

  it('blendet sie aus, wo nichts erlaubt ist — und sagt warum', async () => {
    prozessAttrappe(OHNE_PROZESSRECHTE);
    zeichne('/de/prozesse/p-1');
    expect(await screen.findByText(/dürfen es aber nicht ändern/)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Bearbeiten' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Aktivieren' })).not.toBeInTheDocument();
  });

  it('nennt dem Umsetzer den einen Weg, den er hat', async () => {
    prozessAttrappe({ ...OHNE_PROZESSRECHTE, umsetzung_pflegen: true });
    zeichne('/de/prozesse/p-1');
    expect(
      await screen.findByText(/lokale Abweichung Ihrer Landesorganisation/),
    ).toBeInTheDocument();
  });

  it('bietet die Bewertung nur an, wer sie durchlaufen darf', async () => {
    prozessAttrappe(OHNE_PROZESSRECHTE);
    zeichne('/de/prozesse/p-1');
    await screen.findByText(/dürfen es aber nicht ändern/);
    expect(screen.queryByRole('link', { name: 'Bewertung durchführen' })).not.toBeInTheDocument();
  });
});

function toolAttrappe(rechte: typeof ALLE_TOOLRECHTE) {
  fetchAttrappe([
    { pfad: '/api/v1/auth/me', koerper: PROFIL },
    { pfad: /\/tools\/t-1$/, koerper: tool({ id: 't-1', rechte }) },
    { pfad: /\/tools\/t-1\/datennutzung/, koerper: [] },
    { pfad: /\/erlaubnisrahmen$/, koerper: rahmen() },
    { pfad: /\/tools\/t-1\/compliance/, koerper: { farbe: 'gruen', offene_abweichungen: [], verlauf: [] } },
    {
      pfad: /\/klassenbefund$/,
      koerper: {
        tool_id: 't-1',
        tool_name: 'Rechnungs-Skript',
        technologie: 'apps-script',
        k_klassen: [],
        befunde: [],
        ausschluss: false,
        offen: 0,
      },
    },
    { pfad: /\/selbstverpflichtungen\/deckung/, koerper: null },
    { pfad: '/api/v1/prozesse', koerper: [] },
    { pfad: '/api/v1/datenobjekte', koerper: [] },
    { pfad: '/api/v1/nutzer', koerper: [] },
    { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    { pfad: '/api/v1/fachbereiche', koerper: [] },
    { pfad: '/api/v1/technologien', koerper: [] },
  ]);
}

describe('Tool-Objekt', () => {
  it('sperrt die Stammdaten, wo nichts erlaubt ist', async () => {
    toolAttrappe(OHNE_TOOLRECHTE);
    zeichne('/de/tools/t-1');
    // Der Satz steht zweimal: einmal unter dem Kopf, einmal dort, wo sonst
    // der Wähler für die Prozesskanten stünde.
    expect((await screen.findAllByText(/dürfen es aber nicht ändern/)).length).toBeGreaterThan(0);
    expect(screen.getByLabelText('Technologie')).toBeDisabled();
  });

  it('lässt den technischen Owner arbeiten', async () => {
    toolAttrappe(ALLE_TOOLRECHTE);
    zeichne('/de/tools/t-1');
    expect(await screen.findByLabelText('Technologie')).not.toBeDisabled();
    expect(screen.queryByText(/dürfen es aber nicht ändern/)).not.toBeInTheDocument();
  });
});

describe('Datenobjekt', () => {
  /* Das Datenobjekt trägt die feinsten Rechte: Stammdaten pflegt auch der Owner
   * des gebenden Prozesses, die Kategorie nur der Datenobjekt-Owner des
   * Fachbereichs, den Anker nur die Governance (rollen-und-scopes.md, 7.4).
   * Drei Rollen an einem Objekt — deshalb drei Fälle. */
  function datenobjektAttrappe(rechte: typeof ALLE_DATENOBJEKTRECHTE) {
    fetchAttrappe([
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      {
        pfad: '/api/v1/datenobjekte/do-1',
        koerper: {
          id: 'do-1',
          name: 'Kreditorenstamm',
          beschreibung: '',
          kategorie: 'intern',
          fachbereich_id: 'fb-1',
          quellsystem: 'SAP FI',
          herkunft: 'manuell',
          quelle: null,
          externe_id: null,
          status: 'bestaetigt',
          metadaten: {},
          schreibgeschuetzte_felder: [],
          rechte,
        },
      },
      {
        pfad: '/api/v1/datenobjekte/do-1/wirkung',
        koerper: {
          kategorie_alt: 'intern',
          kategorie_neu: null,
          prozesse: [],
          tools: [],
          mitbestimmung_neu: 0,
        },
      },
    ]);
  }

  it('lässt den Datenobjekt-Owner klassifizieren', async () => {
    datenobjektAttrappe(ALLE_DATENOBJEKTRECHTE);
    zeichne('/de/datenobjekte/do-1');
    expect(await screen.findByLabelText('Kategorie')).not.toBeDisabled();
    expect(screen.getByLabelText('Quellsystem')).not.toBeDisabled();
    expect(screen.queryByText(/dürfen es aber nicht ändern/)).not.toBeInTheDocument();
  });

  it('trennt Stammdaten von der Kategorie', async () => {
    // Der Owner des gebenden Prozesses: er pflegt, was er erzeugt — aber die
    // Kategorie wirkt in jeden fremden Prozess, der die Quelle nutzt.
    datenobjektAttrappe({ ...OHNE_DATENOBJEKTRECHTE, bearbeiten: true });
    zeichne('/de/datenobjekte/do-1');
    expect(await screen.findByLabelText('Quellsystem')).not.toBeDisabled();
    expect(screen.getByLabelText('Kategorie')).toBeDisabled();
    expect(screen.getByText(/Kategorie setzt der Datenobjekt-Owner/)).toBeInTheDocument();
  });

  it('sperrt alles, wo nichts erlaubt ist — und sagt warum', async () => {
    datenobjektAttrappe(OHNE_DATENOBJEKTRECHTE);
    zeichne('/de/datenobjekte/do-1');
    expect(await screen.findByLabelText('Kategorie')).toBeDisabled();
    expect(screen.getByLabelText('Quellsystem')).toBeDisabled();
    expect(screen.getByText(/dürfen es aber nicht ändern/)).toBeInTheDocument();
  });

  it('zeigt den Anker als Text, wo er nicht wandern darf', async () => {
    datenobjektAttrappe({ ...ALLE_DATENOBJEKTRECHTE, anker_aendern: false });
    zeichne('/de/datenobjekte/do-1');
    const fachbereich = await screen.findByLabelText('Fachbereich');
    expect(fachbereich).toBeDisabled();
    expect(fachbereich.tagName).toBe('INPUT'); // kein Dropdown: nichts zu wählen
  });
});
