/**
 * Compliance und Lenkung in der Oberflaeche (Architektur 8.6).
 */

import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { ComplianceZustand, Lenkungsvorgang } from '@/api/typen';
import { EINHEITEN, PROFIL, fetchAttrappe, prozess, tool, zeichne, type Route } from './hilfen';

afterEach(() => vi.useRealTimers());

function zustand(ueberschreibungen: Partial<ComplianceZustand> = {}): ComplianceZustand {
  return {
    id: 'cz-1',
    tool_objekt_id: 'tool-1',
    farbe: 'gruen',
    begruendung: 'Erstpruefung',
    abweichung_art: null,
    schicht2_verbot: null,
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
    schicht2_verbot: null,
    frist: '2026-09-15T10:00:00Z',
    zugewiesen_an: 'user-1',
    status: 'offen',
    aufloesungsart: null,
    aufloesung_bewertung_id: null,
    aufgeloest_am: null,
    beschreibung: 'Schreibt ausserhalb des Rahmens',
    aufloesungskommentar: '',
    offene_abweichungen: [],
    erstellt_am: '2026-09-01T10:00:00Z',
    rechte: { aufloesen: true, abbrechen: true },
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
      schicht2_verbot: null,
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
  function lenkungsrouten(vorgaenge: Lenkungsvorgang[], werkzeug = tool()): Route[] {
    return [
      { pfad: '/api/v1/auth/me', koerper: PROFIL },
      { pfad: '/api/v1/lenkungsvorgaenge', koerper: vorgaenge },
      { pfad: '/api/v1/tools', koerper: [werkzeug] },
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
    expect(screen.getByTestId('stufe-lv-1')).toHaveTextContent('Stufe 1');
    expect(screen.getByTestId('fristdatum-lv-1')).toHaveTextContent('2026-09-15');
    // Die Überschrift nennt das Tool; der Verweis nennt den Weg dorthin.
    expect(screen.getByRole('heading', { name: 'Rechnungs-Skript' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Zum Tool-Objekt' })).toHaveAttribute(
      'href',
      '/de/tools/tool-1',
    );
  });

  it('zaehlt die verbleibende Zeit in Arbeitstagen', async () => {
    // Vom Dienstag, 1. September, bis Dienstag, 15. September: zehn
    // Arbeitstage, weil zwei Wochenenden dazwischenliegen.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date('2026-09-01T09:00:00Z'));
    fetchAttrappe(lenkungsrouten([vorgang()]));
    zeichne('/de/lenkung');
    expect(await screen.findByTestId('frist-lv-1')).toHaveTextContent('10');
    expect(screen.getByText('Arbeitstage verbleiben')).toBeInTheDocument();
  });

  it('zeigt eine abgelaufene Frist als abgelaufen', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date('2026-09-18T09:00:00Z'));
    fetchAttrappe(lenkungsrouten([vorgang()]));
    zeichne('/de/lenkung');
    expect(await screen.findByTestId('frist-lv-1')).toHaveTextContent('Abgelaufen');
    expect(screen.getByText('seit 3 Arbeitstagen')).toBeInTheDocument();
  });

  it('nennt eine heute abgelaufene Frist als seit heute abgelaufen', async () => {
    // Eine Frist, die heute um 9 Uhr endete, ist um 15 Uhr abgelaufen — auch
    // wenn dazwischen kein Arbeitstag liegt.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date('2026-09-15T15:00:00Z'));
    fetchAttrappe(lenkungsrouten([vorgang({ frist: '2026-09-15T09:00:00Z' })]));
    zeichne('/de/lenkung');
    expect(await screen.findByTestId('frist-lv-1')).toHaveTextContent('Abgelaufen');
    expect(screen.getByText('seit heute')).toBeInTheDocument();
  });

  it('nennt bei einem Schicht-2-Verstoss das Verbot und die Folge', async () => {
    fetchAttrappe(
      lenkungsrouten([vorgang({ eskalationsstufe: 2, schicht2_verbot: 'identitaet_umgangen' })]),
    );
    zeichne('/de/lenkung');
    expect(
      await screen.findByText(/Ausführung unter umgangener Unternehmensidentität/),
    ).toBeInTheDocument();
    expect(screen.getByText(/ohne erste Stufe/)).toBeInTheDocument();
  });

  it('nennt die stehende Abweichung, bevor jemand vergeblich klickt', async () => {
    // E-63: „Angepasst" schliesst nur, wenn die Messung es hergibt. Das gehoert
    // vor den Klick — eine Fehlermeldung danach erklaert nichts.
    fetchAttrappe(
      lenkungsrouten([
        vorgang({ offene_abweichungen: ['Verbot identitaet_umgangen', 'datenobjekte'] }),
      ]),
    );
    zeichne('/de/lenkung');
    const hinweis = await screen.findByTestId('abweichungen-lv-1');
    expect(hinweis).toHaveTextContent('Verbot identitaet_umgangen, datenobjekte');
    expect(hinweis).toHaveTextContent('schließen erst, wenn sie behoben ist');
  });

  it('schweigt, wo die Anwendung nichts misst', async () => {
    fetchAttrappe(lenkungsrouten([vorgang()]));
    zeichne('/de/lenkung');
    await screen.findByTestId('stufe-lv-1');
    expect(screen.queryByTestId('abweichungen-lv-1')).not.toBeInTheDocument();
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

  it('bietet die drei Wege gleichrangig an, ohne Vorauswahl', async () => {
    fetchAttrappe(lenkungsrouten([vorgang()]));
    zeichne('/de/lenkung');
    await screen.findByTestId('anpassen-lv-1');
    // Drei Knöpfe derselben Art — eine Auswahlliste hätte einen Vorgabewert,
    // und ein Vorgabewert wäre eine Empfehlung. A.13.6 gibt keine.
    for (const art of ['anpassen', 'rahmen_erweitern', 'stilllegen']) {
      expect(screen.getByTestId(`${art}-lv-1`)).toHaveClass('k-knopf--getoent');
    }
  });

  it('loest per Anpassen auf', async () => {
    const { aufrufe } = fetchAttrappe([
      // Nach der Auflösung lädt die Seite neu; beim zweiten Mal ist der
      // Vorgang weg — so, wie der Server ihn dann auch nicht mehr liefert.
      {
        pfad: '/api/v1/lenkungsvorgaenge',
        koerper: (aufruf: number) => (aufruf === 1 ? [vorgang()] : []),
      },
      ...lenkungsrouten([vorgang()]),
      {
        pfad: '/api/v1/lenkungsvorgaenge/lv-1/aufloesung',
        methode: 'POST',
        koerper: vorgang({ status: 'aufgeloest', aufloesungsart: 'anpassen' }),
      },
    ]);
    zeichne('/de/lenkung');
    await userEvent.click(await screen.findByTestId('anpassen-lv-1'));
    await userEvent.type(screen.getByLabelText('Kommentar'), 'Schreibzugriff entfernt');
    await userEvent.click(screen.getByTestId('aufloesen'));
    await waitFor(() =>
      expect(screen.getByText('Es ist kein Lenkungsvorgang offen.')).toBeInTheDocument(),
    );
    expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
      art: 'anpassen',
      bewertung_id: null,
      kommentar: 'Schreibzugriff entfernt',
    });
  });

  it('bietet bei Rahmen erweitern nur Bewertungen nach der Eroeffnung an', async () => {
    const { aufrufe } = fetchAttrappe([
      ...lenkungsrouten([vorgang()], tool({ prozessobjekt_ids: ['p-1'] })),
      {
        pfad: '/api/v1/prozesse/p-1/bewertungen',
        koerper: [
          { id: 'b-alt', tier: 2, bewertet_am: '2026-08-01T10:00:00Z' },
          { id: 'b-neu', tier: 3, bewertet_am: '2026-09-05T10:00:00Z' },
        ],
      },
      {
        pfad: '/api/v1/lenkungsvorgaenge/lv-1/aufloesung',
        methode: 'POST',
        koerper: vorgang({ status: 'aufgeloest', aufloesungsart: 'rahmen_erweitern' }),
      },
    ]);
    zeichne('/de/lenkung');
    await userEvent.click(await screen.findByTestId('rahmen_erweitern-lv-1'));

    // Die ältere Bewertung bildet den erweiterten Rahmen nicht ab; der Server
    // weist sie ab, und was er abweist, bietet die Oberfläche nicht an.
    expect(await screen.findByTestId('bewertung-b-neu')).toBeInTheDocument();
    expect(screen.queryByTestId('bewertung-b-alt')).not.toBeInTheDocument();

    await userEvent.click(screen.getByTestId('bewertung-b-neu'));
    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
        art: 'rahmen_erweitern',
        bewertung_id: 'b-neu',
        kommentar: '',
      }),
    );
  });

  it('sagt bei Rahmen erweitern, wenn die neue Bewertung fehlt', async () => {
    fetchAttrappe([
      ...lenkungsrouten([vorgang()], tool({ prozessobjekt_ids: ['p-1'] })),
      { pfad: '/api/v1/prozesse/p-1/bewertungen', koerper: [] },
    ]);
    zeichne('/de/lenkung');
    await userEvent.click(await screen.findByTestId('rahmen_erweitern-lv-1'));
    expect(await screen.findByText(/keine neue Bewertung/)).toBeInTheDocument();
    expect(screen.queryByTestId('aufloesen')).not.toBeInTheDocument();
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
    await userEvent.click(await screen.findByTestId('stilllegen-lv-1'));
    expect(screen.getByText(/Das ist keine Rückkehr in den Rahmen/)).toBeInTheDocument();
    await userEvent.click(screen.getByTestId('aufloesen'));
    await waitFor(() =>
      expect(aufrufe.find((a) => a.methode === 'POST')?.koerper).toEqual({
        art: 'stilllegen',
        bewertung_id: null,
        kommentar: '',
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
    await userEvent.click(await screen.findByTestId('anpassen-lv-1'));
    await userEvent.click(screen.getByTestId('aufloesen'));
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
