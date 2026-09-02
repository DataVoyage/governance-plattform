/**
 * Bausteine des Design-Systems „Klar" (Umsetzungsplan AP-0).
 *
 * Geprueft wird, was den Bausteinen ihren Wert gibt: die Verbindung von
 * Beschriftung und Steuerelement, die Ankuendigung von Fehlern, die
 * Tastaturbedienung des Referenz-Waehlers und die Fokusfalle des Blatts.
 * Aussehen prueft dieser Test nicht — dafuer ist die Stilprobe da.
 */

import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { SprachAnbieter } from '@/i18n/SprachKontext';
import { Stilprobe } from '@/seiten/Stilprobe';
import {
  Abzeichen,
  Auswahl,
  Blatt,
  Feld,
  Feldgruppe,
  Gruppe,
  Hinweis,
  Karte,
  Knopf,
  Ladeschimmer,
  Leerzustand,
  ReferenzWaehler,
  SegmentierteSteuerung,
  Seitenkopf,
  Suchfeld,
  Umschalter,
  Werteliste,
  Zeile,
  ZeileKnopf,
  ZeileVerweis,
  type Referenz,
} from '@/ui';

function imRouter(inhalt: React.ReactNode) {
  return render(<MemoryRouter initialEntries={['/de/prozesse']}>{inhalt}</MemoryRouter>);
}

const BESTAND: Referenz[] = [
  { id: '1', name: 'Entgeltdaten', zusatz: 'SAP HCM', abzeichen: 'Besondere Kategorie', ton: 'rot' },
  { id: '2', name: 'Kreditorenstamm', zusatz: 'SAP FI' },
  { id: '3', name: 'Artikelstamm' },
];

describe('Knopf', () => {
  it('traegt die Art als Klasse und meldet den Klick', async () => {
    const gedrueckt = vi.fn();
    render(
      <Knopf art="gefuellt" gross breit onClick={gedrueckt}>
        Speichern
      </Knopf>,
    );
    const knopf = screen.getByRole('button', { name: 'Speichern' });
    expect(knopf).toHaveClass('k-knopf--gefuellt', 'k-knopf--gross', 'k-knopf--breit');
    await userEvent.click(knopf);
    expect(gedrueckt).toHaveBeenCalledOnce();
  });

  it('ist als abgesendeter Knopf vom Typ submit', () => {
    render(<Knopf type="submit">Anmelden</Knopf>);
    expect(screen.getByRole('button', { name: 'Anmelden' })).toHaveAttribute('type', 'submit');
  });
});

describe('Abzeichen', () => {
  it('traegt seinen Text und blendet das Zeichen fuer Vorlesesoftware aus', () => {
    render(
      <Abzeichen ton="gruen" zeichen="●">
        Compliant
      </Abzeichen>,
    );
    const abzeichen = screen.getByText('Compliant');
    expect(abzeichen).toHaveClass('k-abzeichen--gruen');
    expect(abzeichen.querySelector('.punkt')).toHaveAttribute('aria-hidden', 'true');
  });

  it('bleibt ohne Ton neutral', () => {
    render(<Abzeichen>Tier 1</Abzeichen>);
    expect(screen.getByText('Tier 1').className).toBe('k-abzeichen');
  });
});

describe('Karte und Seitenkopf', () => {
  it('zeigt Titel, Beischrift und Aktion', () => {
    render(
      <Karte titel="Erlaubnisrahmen" beischrift="Schicht 1" aktion={<Knopf>Ändern</Knopf>}>
        <p>Inhalt</p>
      </Karte>,
    );
    expect(screen.getByRole('heading', { name: 'Erlaubnisrahmen' })).toBeInTheDocument();
    expect(screen.getByText('Schicht 1')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Ändern' })).toBeInTheDocument();
  });

  it('kommt ohne Kopf aus', () => {
    render(
      <Karte>
        <p>Nur Inhalt</p>
      </Karte>,
    );
    expect(screen.getByText('Nur Inhalt')).toBeInTheDocument();
    expect(screen.queryByRole('heading')).not.toBeInTheDocument();
  });

  it('verlinkt den Rueckweg und zeigt den Untertitel', () => {
    imRouter(
      <Seitenkopf
        titel="Rechnungsprüfung"
        untertitel="Finance · INT"
        rueckweg={{ ziel: '/de/prozesse', text: 'Zurück' }}
        aktionen={<Knopf>Bearbeiten</Knopf>}
      />,
    );
    expect(screen.getByRole('link', { name: /Zurück/ })).toHaveAttribute('href', '/de/prozesse');
    expect(screen.getByText('Finance · INT')).toBeInTheDocument();
  });

  it('zeigt einen Seitenkopf auch ohne Rueckweg und Aktionen', () => {
    imRouter(<Seitenkopf titel="Cockpit" />);
    expect(screen.getByRole('heading', { name: 'Cockpit' })).toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });
});

describe('Feld', () => {
  function Probe({ fehler, hilfe }: { fehler?: string; hilfe?: string }) {
    const [wert, setWert] = useState('');
    return (
      <Feld
        beschriftung="Prozessname"
        wert={wert}
        aendern={setWert}
        pflicht
        hoechstlaenge={20}
        hilfe={hilfe}
        fehler={fehler}
      />
    );
  }

  it('verbindet Beschriftung und Eingabe und zaehlt die Zeichen', async () => {
    render(<Probe hilfe="Kurz halten" />);
    const eingabe = screen.getByLabelText('Prozessname');
    await userEvent.type(eingabe, 'Rechnung');
    expect(eingabe).toHaveValue('Rechnung');
    expect(screen.getByText('8 / 20')).toBeInTheDocument();
    expect(eingabe).toHaveAccessibleDescription('Kurz halten');
  });

  it('kuendigt einen Fehler an', () => {
    render(<Probe fehler="Pflichtfeld" />);
    const eingabe = screen.getByLabelText('Prozessname');
    expect(eingabe).toHaveAttribute('aria-invalid', 'true');
    expect(eingabe).toHaveAccessibleDescription('Pflichtfeld');
  });

  it('kann mehrzeilig sein', async () => {
    function Mehrzeilig() {
      const [wert, setWert] = useState('');
      return (
        <Feld beschriftung="Schritte" wert={wert} aendern={setWert} mehrzeilig platzhalter="1 … 7" />
      );
    }
    render(<Mehrzeilig />);
    const feld = screen.getByLabelText('Schritte');
    expect(feld.tagName).toBe('TEXTAREA');
    await userEvent.type(feld, 'Prüfen');
    expect(feld).toHaveValue('Prüfen');
  });
});

describe('Auswahl, Umschalter, Segmente, Suche', () => {
  it('waehlt eine Option und meldet sie', async () => {
    function Probe() {
      const [wert, setWert] = useState('');
      return (
        <Auswahl
          beschriftung="Kategorie"
          wert={wert}
          aendern={setWert}
          leertext="Ohne"
          pflicht
          hilfe="Einmal je Quelle"
          optionen={[
            { wert: 'intern', text: 'Intern' },
            { wert: 'vertraulich', text: 'Vertraulich' },
          ]}
        />
      );
    }
    render(<Probe />);
    const auswahl = screen.getByLabelText('Kategorie');
    await userEvent.selectOptions(auswahl, 'vertraulich');
    expect(auswahl).toHaveValue('vertraulich');
    expect(auswahl).toHaveAccessibleDescription('Einmal je Quelle');
  });

  it('meldet einen Fehler an der Auswahl', () => {
    render(
      <Auswahl
        beschriftung="Kategorie"
        wert=""
        aendern={() => undefined}
        fehler="Bitte wählen"
        optionen={[{ wert: 'a', text: 'A' }]}
      />,
    );
    expect(screen.getByLabelText('Kategorie')).toHaveAccessibleDescription('Bitte wählen');
  });

  it('schaltet um', async () => {
    function Probe() {
      const [an, setAn] = useState(false);
      return <Umschalter beschriftung="Aktiv" zweitzeile="Gilt sofort" an={an} aendern={setAn} />;
    }
    render(<Probe />);
    const schalter = screen.getByRole('checkbox', { name: /Aktiv/ });
    await userEvent.click(schalter);
    expect(schalter).toBeChecked();
    expect(screen.getByText('Gilt sofort')).toBeInTheDocument();
  });

  it('drueckt genau ein Segment', async () => {
    function Probe() {
      const [wert, setWert] = useState<'schnell' | 'voll'>('schnell');
      return (
        <SegmentierteSteuerung
          beschriftung="Modus"
          wert={wert}
          aendern={setWert}
          optionen={[
            { wert: 'schnell', text: 'Schnell' },
            { wert: 'voll', text: 'Vollständig' },
          ]}
        />
      );
    }
    render(<Probe />);
    const gruppe = screen.getByRole('group', { name: 'Modus' });
    await userEvent.click(within(gruppe).getByRole('button', { name: 'Vollständig' }));
    expect(within(gruppe).getByRole('button', { name: 'Vollständig' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(within(gruppe).getByRole('button', { name: 'Schnell' })).toHaveAttribute(
      'aria-pressed',
      'false',
    );
  });

  it('nimmt eine Sucheingabe entgegen', async () => {
    function Probe() {
      const [wert, setWert] = useState('');
      return <Suchfeld beschriftung="Suche" wert={wert} aendern={setWert} platzhalter="Suchen" />;
    }
    render(<Probe />);
    await userEvent.type(screen.getByLabelText('Suche'), 'Entgelt');
    expect(screen.getByLabelText('Suche')).toHaveValue('Entgelt');
  });

  it('umschliesst eine Feldgruppe mit ihrer Beschriftung', () => {
    render(
      <Feldgruppe titel="Umsetzung">
        <p>Inhalt</p>
      </Feldgruppe>,
    );
    expect(screen.getByRole('group', { name: 'Umsetzung' })).toBeInTheDocument();
  });

  it('kommt als Feldgruppe auch ohne Titel aus', () => {
    render(
      <Feldgruppe>
        <p>Ohne Titel</p>
      </Feldgruppe>,
    );
    expect(screen.getByText('Ohne Titel')).toBeInTheDocument();
  });
});

describe('Gruppierte Liste', () => {
  it('zeigt Etikett, Hinweis, Verweis- und Knopfzeilen', async () => {
    const gedrueckt = vi.fn();
    imRouter(
      <Gruppe etikett="Prozesse" hinweis="Nur der eigene Bereich">
        <ZeileVerweis
          ziel="/de/prozesse/p-1"
          haupt="Rechnungsprüfung"
          zweitzeile="Finance"
          wert={<Abzeichen>Tier 1</Abzeichen>}
          pruefkennung="zeile-p1"
        />
        <ZeileKnopf handeln={gedrueckt} haupt="Weitere laden" />
        <Zeile beschriftung="Reichweite" wert="Team" pruefkennung="reichweite" />
      </Gruppe>,
    );
    expect(screen.getByText('Prozesse')).toBeInTheDocument();
    expect(screen.getByText('Nur der eigene Bereich')).toBeInTheDocument();
    expect(screen.getByTestId('zeile-p1')).toHaveAttribute('href', '/de/prozesse/p-1');
    expect(screen.getByTestId('reichweite')).toHaveTextContent('Team');
    await userEvent.click(screen.getByRole('button', { name: /Weitere laden/ }));
    expect(gedrueckt).toHaveBeenCalledOnce();
  });

  it('kommt ohne Etikett und Hinweis aus', () => {
    imRouter(
      <Gruppe>
        <Zeile haupt="Nur eine Zeile" />
      </Gruppe>,
    );
    expect(screen.getByText('Nur eine Zeile')).toBeInTheDocument();
  });
});

describe('Werteliste', () => {
  it('zeigt Wert und Herkunft', () => {
    render(
      <Werteliste
        eintraege={[
          {
            beschriftung: 'Kritikalität',
            wert: '3',
            herkunft: 'Aus nachgelagertem Prozess',
            pruefkennung: 'kritikalitaet',
          },
          { beschriftung: 'Reichweite', wert: 'Team' },
        ]}
      />,
    );
    expect(screen.getByTestId('kritikalitaet')).toHaveTextContent('Aus nachgelagertem Prozess');
    expect(screen.getByText('Reichweite')).toBeInTheDocument();
  });
});

describe('Hinweis, Leerzustand, Ladeschimmer', () => {
  it('meldet einen Fehler als Alarm', () => {
    render(<Hinweis art="fehler">Gate 1 fehlt</Hinweis>);
    expect(screen.getByRole('alert')).toHaveTextContent('Gate 1 fehlt');
  });

  it('meldet andere Arten als Status', () => {
    render(<Hinweis>Rahmen gilt für alle Tools</Hinweis>);
    expect(screen.getByRole('status')).toHaveTextContent('Rahmen gilt für alle Tools');
  });

  it('bietet im Leerzustand die Hauptaktion an', () => {
    render(
      <Leerzustand
        titel="Noch nichts erfasst"
        text="Legen Sie das erste Objekt an."
        aktion={<Knopf art="gefuellt">Anlegen</Knopf>}
      />,
    );
    expect(screen.getByRole('heading', { name: 'Noch nichts erfasst' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Anlegen' })).toBeInTheDocument();
  });

  it('kommt im Leerzustand ohne Text und Aktion aus', () => {
    render(<Leerzustand titel="Leer" />);
    expect(screen.getByRole('heading', { name: 'Leer' })).toBeInTheDocument();
  });

  it('kuendigt das Laden an', () => {
    render(<Ladeschimmer beschriftung="Wird geladen" zeilen={2} />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByText('Wird geladen')).toBeInTheDocument();
  });
});

describe('Blatt', () => {
  function Probe({ schliessen }: { schliessen: () => void }) {
    return (
      <Blatt
        titel="Datenobjekt anlegen"
        beischrift="Reifegrad 1"
        schliessen={schliessen}
        fuss={<Knopf art="gefuellt">Anlegen</Knopf>}
      >
        <Feld beschriftung="Name" wert="" aendern={() => undefined} />
      </Blatt>
    );
  }

  it('setzt den Fokus hinein und schliesst mit Escape', async () => {
    const schliessen = vi.fn();
    render(<Probe schliessen={schliessen} />);
    const blatt = screen.getByRole('dialog', { name: 'Datenobjekt anlegen' });
    expect(blatt).toHaveAttribute('aria-modal', 'true');
    await waitFor(() => expect(screen.getByLabelText('Name')).toHaveFocus());
    await userEvent.keyboard('{Escape}');
    expect(schliessen).toHaveBeenCalledOnce();
  });

  it('haelt den Fokus im Blatt', async () => {
    render(<Probe schliessen={() => undefined} />);
    await waitFor(() => expect(screen.getByLabelText('Name')).toHaveFocus());
    await userEvent.tab();
    expect(screen.getByRole('button', { name: 'Anlegen' })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByLabelText('Name')).toHaveFocus();
    await userEvent.tab({ shift: true });
    expect(screen.getByRole('button', { name: 'Anlegen' })).toHaveFocus();
  });

  it('schliesst beim Klick auf den Hintergrund, nicht im Blatt', async () => {
    const schliessen = vi.fn();
    const { container } = render(<Probe schliessen={schliessen} />);
    await userEvent.click(screen.getByRole('dialog'));
    expect(schliessen).not.toHaveBeenCalled();
    await userEvent.click(container.querySelector('.k-blatt-grund') as HTMLElement);
    expect(schliessen).toHaveBeenCalledOnce();
  });
});

describe('ReferenzWaehler', () => {
  function Probe({ start = [] as string[] }) {
    const [gewaehlt, setGewaehlt] = useState<string[]>(start);
    return (
      <ReferenzWaehler
        beschriftung="Input — Datenobjekte"
        hilfe="Referenz, kein Freitext"
        bestand={BESTAND}
        gewaehlt={gewaehlt}
        aendern={setGewaehlt}
        platzhalter="Suchen …"
        keineTreffer="Kein Eintrag gefunden"
        pruefkennung="input"
      />
    );
  }

  it('sucht, waehlt mit der Maus und zeigt die Einstufung des Treffers', async () => {
    render(<Probe />);
    const eingabe = screen.getByLabelText('Input — Datenobjekte');
    expect(eingabe).toHaveAccessibleDescription('Referenz, kein Freitext');
    await userEvent.type(eingabe, 'entgelt');
    const liste = screen.getByRole('listbox', { name: 'Input — Datenobjekte' });
    expect(within(liste).getByText('Besondere Kategorie')).toBeInTheDocument();
    await userEvent.click(within(liste).getByText('Entgeltdaten'));
    expect(screen.getByRole('button', { name: 'Entgeltdaten entfernen' })).toBeInTheDocument();
  });

  it('waehlt vollstaendig ueber die Tastatur', async () => {
    render(<Probe />);
    const eingabe = screen.getByLabelText('Input — Datenobjekte');
    await userEvent.click(eingabe);
    await userEvent.keyboard('{ArrowDown}{ArrowDown}{Enter}');
    expect(screen.getByRole('button', { name: 'Artikelstamm entfernen' })).toBeInTheDocument();
    // Ein Schritt hinunter und wieder hinauf landet zurueck beim ersten Treffer.
    await userEvent.keyboard('{ArrowDown}{ArrowUp}{Enter}');
    expect(screen.getByRole('button', { name: 'Entgeltdaten entfernen' })).toBeInTheDocument();
  });

  it('entfernt den letzten Chip mit der Rueckschritttaste und ueber den Knopf', async () => {
    render(<Probe start={['1', '2']} />);
    const eingabe = screen.getByLabelText('Input — Datenobjekte');
    await userEvent.click(eingabe);
    await userEvent.keyboard('{Backspace}');
    expect(
      screen.queryByRole('button', { name: 'Kreditorenstamm entfernen' }),
    ).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Entgeltdaten entfernen' }));
    expect(screen.queryByRole('button', { name: 'Entgeltdaten entfernen' })).not.toBeInTheDocument();
  });

  it('meldet, wenn nichts passt, und schliesst mit Escape', async () => {
    render(<Probe />);
    const eingabe = screen.getByLabelText('Input — Datenobjekte');
    await userEvent.type(eingabe, 'gibtesnicht');
    expect(screen.getByText('Kein Eintrag gefunden')).toBeInTheDocument();
    await userEvent.keyboard('{Enter}');
    expect(screen.getByText('Kein Eintrag gefunden')).toBeInTheDocument();
    await userEvent.keyboard('{Escape}');
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('bietet bereits gewaehlte Eintraege nicht erneut an', async () => {
    render(<Probe start={['1']} />);
    await userEvent.click(screen.getByLabelText('Input — Datenobjekte'));
    const liste = screen.getByRole('listbox', { name: 'Input — Datenobjekte' });
    expect(within(liste).queryByText('Entgeltdaten')).not.toBeInTheDocument();
    expect(within(liste).getByText('Kreditorenstamm')).toBeInTheDocument();
  });
});

describe('Stilprobe', () => {
  it('zeigt alle Bausteine und oeffnet das Blatt', async () => {
    render(
      <MemoryRouter initialEntries={['/de/stilprobe']}>
        <SprachAnbieter>
          <Stilprobe />
        </SprachAnbieter>
      </MemoryRouter>,
    );
    expect(screen.getByRole('heading', { name: 'Stilprobe', level: 1 })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Blatt öffnen' }));
    expect(screen.getByRole('dialog', { name: 'Datenobjekt anlegen' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Abbrechen' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
  });

  it('schaltet die Markenschicht um und raeumt sie wieder ab', async () => {
    const { unmount } = render(
      <MemoryRouter initialEntries={['/de/stilprobe']}>
        <SprachAnbieter>
          <Stilprobe />
        </SprachAnbieter>
      </MemoryRouter>,
    );
    const gruppe = screen.getByRole('group', { name: 'Marke' });
    expect(document.documentElement).not.toHaveAttribute('data-marke');
    await userEvent.click(within(gruppe).getByRole('button', { name: 'Kaufland' }));
    expect(document.documentElement).toHaveAttribute('data-marke', 'kaufland');
    await userEvent.click(within(gruppe).getByRole('button', { name: 'Klar' }));
    expect(document.documentElement).not.toHaveAttribute('data-marke');
    await userEvent.click(within(gruppe).getByRole('button', { name: 'Kaufland' }));
    unmount();
    expect(document.documentElement).not.toHaveAttribute('data-marke');
  });

  it('warnt bei mehr als sieben Prozessschritten', async () => {
    render(
      <MemoryRouter initialEntries={['/de/stilprobe']}>
        <SprachAnbieter>
          <Stilprobe />
        </SprachAnbieter>
      </MemoryRouter>,
    );
    const schritte = screen.getByLabelText('Prozessschritte');
    await userEvent.type(schritte, 'a{enter}b{enter}c{enter}d{enter}e{enter}f{enter}g{enter}h');
    expect(screen.getByText(/falsche Flughöhe/)).toBeInTheDocument();
  });
});
