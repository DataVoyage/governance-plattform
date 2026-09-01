/**
 * Compliance und Lenkung in der Oberflaeche (Architektur 8.6).
 */

import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import type { ComplianceZustand, Lenkungsvorgang, ToolObjekt } from '@/api/typen';
import { EINHEITEN, PROFIL, fetchAttrappe, prozess, zeichne, type Route } from './hilfen';

function tool(ueberschreibungen: Partial<ToolObjekt> = {}): ToolObjekt {
  return {
    id: 'tool-1',
    name: 'Rechnungs-Skript',
    beschreibung: '',
    technologie: null,
    kategorie: null,
    technischer_owner_user_id: null,
    organisationseinheit_id: 'org-de',
    herkunft: 'manuell',
    quelle: null,
    externe_id: null,
    status: 'bestaetigt',
    metadaten: {},
    letzte_aktivitaet_am: null,
    prozessobjekt_ids: [],
    geerbt: {
      kritikalitaet: 0,
      reichweite: null,
      tier: null,
      mitbestimmung_flag: false,
      k_klassen: [],
      quelle_prozess_ids: [],
    },
    schreibgeschuetzte_felder: [],
    ...ueberschreibungen,
  };
}

function zustand(ueberschreibungen: Partial<ComplianceZustand> = {}): ComplianceZustand {
  return {
    id: 'cz-1',
    tool_objekt_id: 'tool-1',
    farbe: 'gruen',
    begruendung: 'Erstpruefung',
    abweichung_art: null,
    festgestellt_am: '2026-09-01T10:00:00Z',
    festgestellt_von: 'user-1',
    ...ueberschreibungen,
  };
}

function vorgang(ueberschreibungen: Partial<Lenkungsvorgang> = {}): Lenkungsvorgang {
  return {
    id: 'lv-1',
    tool_objekt_id: 'tool-1',
    compliance_zustand_id: 'cz-2',
    eskalationsstufe: 1,
    frist: '2026-09-15T10:00:00Z',
    zugewiesen_an: 'user-1',
    status: 'offen',
    aufloesungsart: null,
    aufloesung_bewertung_id: null,
    aufgeloest_am: null,
    beschreibung: 'Schreibt ausserhalb des Rahmens',
    erstellt_am: '2026-09-01T10:00:00Z',
    ...ueberschreibungen,
  };
}

function toolrouten(verlauf: ComplianceZustand[] = []): Route[] {
  return [
    { pfad: '/api/v1/auth/me', koerper: PROFIL },
    { pfad: '/api/v1/organisationseinheiten', koerper: EINHEITEN },
    { pfad: '/api/v1/prozesse', koerper: [prozess()] },
    { pfad: '/api/v1/tools/tool-1/compliance', koerper: verlauf },
    { pfad: '/api/v1/tools/tool-1', koerper: tool() },
  ];
}

describe('Compliance-Zeitreihe', () => {
  it('meldet einen leeren Verlauf', async () => {
    fetchAttrappe(toolrouten());
    zeichne('/de/tools/tool-1');
    expect(
      await screen.findByText('Für dieses Tool-Objekt ist noch kein Zustand erfasst.'),
    ).toBeInTheDocument();
  });

  it('zeigt den neuesten Zustand oben', async () => {
    fetchAttrappe(
      toolrouten([
        zustand({ id: 'cz-2', farbe: 'rot', begruendung: 'Rahmen verlassen' }),
        zustand(),
      ]),
    );
    zeichne('/de/tools/tool-1');
    const aktuell = await screen.findByTestId('aktueller-zustand');
    expect(aktuell).toHaveTextContent('Rot — Rahmenüberschreitung');
    expect(aktuell).toHaveTextContent('Rahmen verlassen');
    // Der aeltere Eintrag bleibt sichtbar.
    expect(screen.getByText('Erstpruefung')).toBeInTheDocument();
  });

  it('weist auf die Folge einer roten Meldung hin', async () => {
    fetchAttrappe(toolrouten());
    zeichne('/de/tools/tool-1');
    await userEvent.selectOptions(await screen.findByLabelText('Zustand melden'), 'rot');
    expect(
      screen.getByText(
        'Eine rote Meldung eröffnet automatisch einen Lenkungsvorgang in Eskalationsstufe 1 mit der tier-abhängigen Frist.',
      ),
    ).toBeInTheDocument();
  });

  it('meldet einen Zustand und ergaenzt die Zeitreihe', async () => {
    const { aufrufe } = fetchAttrappe([
      ...toolrouten(),
      {
        pfad: '/api/v1/tools/tool-1/compliance',
        methode: 'POST',
        status: 201,
        koerper: {
          zustand: zustand({ id: 'cz-3', farbe: 'rot', abweichung_art: 'externes_ziel' }),
          lenkungsvorgang: vorgang(),
        },
      },
    ]);
    zeichne('/de/tools/tool-1');
    await userEvent.selectOptions(await screen.findByLabelText('Zustand melden'), 'rot');
    await userEvent.type(screen.getByLabelText('Begründung'), 'Neues externes Ziel');
    await userEvent.type(screen.getByLabelText('Art der Abweichung'), 'externes_ziel');
    await userEvent.click(screen.getByRole('button', { name: 'Zustand melden' }));

    await waitFor(() =>
      expect(screen.getByTestId('aktueller-zustand')).toHaveTextContent('externes_ziel'),
    );
    expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
      farbe: 'rot',
      begruendung: 'Neues externes Ziel',
      abweichung_art: 'externes_ziel',
    });
  });

  it('meldet einen abgelehnten Versuch', async () => {
    fetchAttrappe([
      ...toolrouten(),
      {
        pfad: '/api/v1/tools/tool-1/compliance',
        methode: 'POST',
        status: 403,
        koerper: { detail: 'Compliance-Meldungen erfasst der technische Owner' },
      },
    ]);
    zeichne('/de/tools/tool-1');
    await userEvent.click(await screen.findByRole('button', { name: 'Zustand melden' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('technische Owner');
  });

  it('meldet einen Ladefehler', async () => {
    fetchAttrappe([
      { pfad: '/api/v1/tools/tool-1/compliance', status: 500, koerper: {} },
      ...toolrouten(),
    ]);
    zeichne('/de/tools/tool-1');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});

describe('Lenkungsvorgaenge', () => {
  function lenkungsrouten(vorgaenge: Lenkungsvorgang[]): Route[] {
    return [
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      { pfad: '/api/v1/lenkungsvorgaenge', koerper: vorgaenge },
      { pfad: '/api/v1/tools', koerper: [tool()] },
    ];
  }

  it('meldet einen leeren Vorrat', async () => {
    fetchAttrappe(lenkungsrouten([]));
    zeichne('/de/lenkung');
    expect(await screen.findByText('Es ist kein Lenkungsvorgang offen.')).toBeInTheDocument();
  });

  it('zeigt Stufe, Frist und das betroffene Tool', async () => {
    fetchAttrappe(lenkungsrouten([vorgang()]));
    zeichne('/de/lenkung');
    await screen.findByRole('heading', { name: 'Lenkungsvorgänge' });
    expect(screen.getByTestId('stufe-lv-1')).toHaveTextContent('1');
    expect(screen.getByText('2026-09-15')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Rechnungs-Skript' })).toBeInTheDocument();
  });

  it('weist in Stufe 3 auf die technische Massnahme hin', async () => {
    fetchAttrappe(lenkungsrouten([vorgang({ eskalationsstufe: 3 })]));
    zeichne('/de/lenkung');
    expect(
      await screen.findByText(
        'Stufe 3 kennzeichnet den Vorgang für eine technische Maßnahme. Der Zugriffsentzug erfolgt außerhalb dieser Anwendung.',
      ),
    ).toBeInTheDocument();
  });

  it('bietet genau die drei Aufloesungswege an', async () => {
    fetchAttrappe(lenkungsrouten([vorgang()]));
    zeichne('/de/lenkung');
    const wahl = await screen.findByLabelText('Auflösungsart — lv-1');
    expect(wahl).toHaveDisplayValue('Anpassen — Tool in den Rahmen zurückführen');
    const optionen = Array.from(wahl.querySelectorAll('option')).map((o) => o.value);
    expect(optionen).toEqual(['anpassen', 'rahmen_erweitern', 'stilllegen']);
  });

  it('loest per Anpassen auf', async () => {
    const { aufrufe } = fetchAttrappe([
      ...lenkungsrouten([vorgang()]),
      {
        pfad: '/api/v1/lenkungsvorgaenge/lv-1/aufloesung',
        methode: 'POST',
        koerper: vorgang({ status: 'aufgeloest', aufloesungsart: 'anpassen' }),
      },
    ]);
    zeichne('/de/lenkung');
    await userEvent.click(await screen.findByRole('button', { name: 'Auflösen' }));
    await waitFor(() =>
      expect(screen.getByText('Es ist kein Lenkungsvorgang offen.')).toBeInTheDocument(),
    );
    expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
      art: 'anpassen',
      bewertung_id: null,
    });
  });

  it('verlangt bei Rahmen erweitern eine Bewertung', async () => {
    const { aufrufe } = fetchAttrappe([
      ...lenkungsrouten([vorgang()]),
      {
        pfad: '/api/v1/lenkungsvorgaenge/lv-1/aufloesung',
        methode: 'POST',
        koerper: vorgang({ status: 'aufgeloest', aufloesungsart: 'rahmen_erweitern' }),
      },
    ]);
    zeichne('/de/lenkung');
    await userEvent.selectOptions(
      await screen.findByLabelText('Auflösungsart — lv-1'),
      'rahmen_erweitern',
    );
    expect(
      screen.getByText('Der Vorgang schließt erst, wenn die neue Bewertung abgeschlossen ist.'),
    ).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Neue Bewertung — lv-1'), 'b-9');
    await userEvent.click(screen.getByRole('button', { name: 'Auflösen' }));
    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
        art: 'rahmen_erweitern',
        bewertung_id: 'b-9',
      }),
    );
  });

  it('legt ein Tool per Stilllegen still', async () => {
    const { aufrufe } = fetchAttrappe([
      ...lenkungsrouten([vorgang()]),
      {
        pfad: '/api/v1/lenkungsvorgaenge/lv-1/aufloesung',
        methode: 'POST',
        koerper: vorgang({ status: 'aufgeloest', aufloesungsart: 'stilllegen' }),
      },
    ]);
    zeichne('/de/lenkung');
    await userEvent.selectOptions(
      await screen.findByLabelText('Auflösungsart — lv-1'),
      'stilllegen',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Auflösen' }));
    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
        art: 'stilllegen',
        bewertung_id: null,
      }),
    );
  });

  it('meldet eine abgelehnte Aufloesung', async () => {
    fetchAttrappe([
      ...lenkungsrouten([vorgang()]),
      {
        pfad: '/api/v1/lenkungsvorgaenge/lv-1/aufloesung',
        methode: 'POST',
        status: 422,
        koerper: { detail: "'Rahmen erweitern' verlangt eine neue Bewertung" },
      },
    ]);
    zeichne('/de/lenkung');
    await userEvent.selectOptions(
      await screen.findByLabelText('Auflösungsart — lv-1'),
      'rahmen_erweitern',
    );
    await userEvent.click(screen.getByRole('button', { name: 'Auflösen' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('verlangt eine neue Bewertung');
  });

  it('meldet einen Ladefehler', async () => {
    fetchAttrappe([
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      { pfad: '/api/v1/lenkungsvorgaenge', status: 500, koerper: {} },
    ]);
    zeichne('/de/lenkung');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
