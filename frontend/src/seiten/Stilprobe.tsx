import { useEffect, useState } from 'react';

import { useSprache } from '@/i18n/SprachKontext';
import {
  Abzeichen,
  Auswahl,
  Blatt,
  Feld,
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
  ZeileVerweis,
  type Referenz,
} from '@/ui';

const BESTAND: Referenz[] = [
  { id: '1', name: 'Entgeltdaten', zusatz: 'SAP HCM', abzeichen: 'Besondere Kategorie', ton: 'rot' },
  { id: '2', name: 'Kreditorenstamm', zusatz: 'SAP FI', abzeichen: 'Vertraulich', ton: 'gelb' },
  { id: '3', name: 'Artikelstamm', zusatz: 'SAP MM', abzeichen: 'Intern', ton: 'neutral' },
  { id: '4', name: 'Pressemitteilungen', zusatz: 'Confluence', abzeichen: 'Öffentlich', ton: 'gruen' },
];

/**
 * Musterseite aller Bausteine (Umsetzungsplan AP-0).
 *
 * Sie dient zwei Zwecken: lebende Dokumentation fuer die weitere Umsetzung und
 * Sichtpruefung beider Farbschemata an einer Stelle.
 */
export function Stilprobe() {
  const { t } = useSprache();
  const [marke, setMarke] = useState<'klar' | 'kaufland'>('klar');
  const [text, setText] = useState('Rechnungsprüfung');
  const [notiz, setNotiz] = useState('');
  const [auswahl, setAuswahl] = useState('team');
  const [an, setAn] = useState(true);
  const [segment, setSegment] = useState<'schnell' | 'vollstaendig'>('schnell');
  const [suche, setSuche] = useState('');
  const [referenzen, setReferenzen] = useState<string[]>(['1']);
  const [blattOffen, setBlattOffen] = useState(false);

  // Die Marke gilt nur, solange diese Seite offen ist: die Stilprobe ist eine
  // Vorschau, keine Einstellung der Anwendung.
  useEffect(() => {
    const wurzel = document.documentElement;
    if (marke === 'klar') wurzel.removeAttribute('data-marke');
    else wurzel.setAttribute('data-marke', marke);
    return () => wurzel.removeAttribute('data-marke');
  }, [marke]);

  return (
    <>
      <Seitenkopf
        titel={t('stilprobe.titel')}
        untertitel={t('stilprobe.untertitel')}
        aktionen={
          <>
            <SegmentierteSteuerung
              beschriftung={t('stilprobe.marke')}
              wert={marke}
              aendern={setMarke}
              optionen={[
                { wert: 'klar', text: t('stilprobe.marke.klar') },
                { wert: 'kaufland', text: t('stilprobe.marke.kaufland') },
              ]}
            />
            <Knopf art="getoent">Zweitrangig</Knopf>
            <Knopf art="gefuellt">Hauptaktion</Knopf>
          </>
        }
      />

      <Karte titel={t('stilprobe.knoepfe')}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--abstand-2)' }}>
          <Knopf art="gefuellt">Gefüllt</Knopf>
          <Knopf art="getoent">Getönt</Knopf>
          <Knopf art="schlicht">Schlicht</Knopf>
          <Knopf art="unauffaellig">Unauffällig</Knopf>
          <Knopf art="zerstoerend">Stilllegen</Knopf>
          <Knopf art="gefuellt" disabled>
            Gesperrt
          </Knopf>
          <Knopf art="gefuellt" gross>
            Groß
          </Knopf>
        </div>
      </Karte>

      <Karte titel={t('stilprobe.abzeichen')}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--abstand-2)' }}>
          <Abzeichen ton="gruen" zeichen="●">
            Compliant
          </Abzeichen>
          <Abzeichen ton="gelb" zeichen="●">
            Nicht zugeordnet
          </Abzeichen>
          <Abzeichen ton="rot" zeichen="●">
            Non-compliant
          </Abzeichen>
          <Abzeichen ton="rot">Tier 3</Abzeichen>
          <Abzeichen ton="gelb">Tier 2</Abzeichen>
          <Abzeichen>Tier 1</Abzeichen>
          <Abzeichen ton="lila">Gate 2 eingereicht</Abzeichen>
          <Abzeichen ton="blau">Importiert</Abzeichen>
        </div>
      </Karte>

      <Karte titel={t('stilprobe.eingaben')}>
        <Feld
          beschriftung="Prozessname"
          wert={text}
          aendern={setText}
          pflicht
          hoechstlaenge={60}
          hilfe="Die kleinste Einheit, die einen Owner und eine Compliance-Antwort hat."
        />
        <Feld
          beschriftung="Prozessschritte"
          wert={notiz}
          aendern={setNotiz}
          mehrzeilig
          platzhalter="5 bis 7 Schritte, Stichworte"
          fehler={notiz.split('\n').filter(Boolean).length > 7 ? 'Mehr als 7 Schritte — falsche Flughöhe.' : undefined}
        />
        <Auswahl
          beschriftung="Kundenkreis"
          wert={auswahl}
          aendern={setAuswahl}
          optionen={[
            { wert: 'persoenlich', text: 'Einzelperson' },
            { wert: 'team', text: 'Team' },
            { wert: 'bereich', text: 'Abteilung' },
            { wert: 'unternehmen', text: 'Unternehmen' },
            { wert: 'extern', text: 'Extern' },
          ]}
          hilfe="Bestimmt die abgeleitete Reichweite."
        />
        <div style={{ display: 'flex', gap: 'var(--abstand-4)', flexWrap: 'wrap' }}>
          <SegmentierteSteuerung
            beschriftung="Bewertungsmodus"
            wert={segment}
            aendern={setSegment}
            optionen={[
              { wert: 'schnell', text: 'Schnell' },
              { wert: 'vollstaendig', text: 'Vollständig' },
            ]}
          />
          <div style={{ minWidth: '14rem', flex: 1 }}>
            <Suchfeld beschriftung="Suche" wert={suche} aendern={setSuche} platzhalter="Suchen" />
          </div>
        </div>
      </Karte>

      <Karte titel={t('stilprobe.referenz')}>
        <ReferenzWaehler
          pruefkennung="waehler-stilprobe"
          beschriftung="Input — Datenobjekte"
          hilfe="Referenz auf bestehende Datenobjekte, kein Freitext (Leitdokument P5)."
          bestand={BESTAND}
          gewaehlt={referenzen}
          aendern={setReferenzen}
          platzhalter="Datenobjekt suchen …"
          keineTreffer={t('stilprobe.keineTreffer')}
        />
      </Karte>

      <Gruppe etikett={t('stilprobe.listen')} hinweis="Haarlinie statt Tabellenraster.">
        <ZeileVerweis
          ziel="#"
          haupt="Rechnungsprüfung"
          zweitzeile="Finance · INT"
          wert={<Abzeichen ton="rot">Tier 3</Abzeichen>}
        />
        <ZeileVerweis
          ziel="#"
          haupt="Urlaubsplanung"
          zweitzeile="HR · Land DE"
          wert={<Abzeichen ton="gelb">Tier 2</Abzeichen>}
        />
        <Zeile beschriftung="Reichweite" wert="Unternehmen" />
        <Zeile
          beschriftung="Mitbestimmung"
          wert={
            <Umschalter beschriftung="" an={an} aendern={setAn} />
          }
        />
      </Gruppe>

      <Karte titel="Abgeleitete Werte" beischrift="Abgeleitet — nicht eingebbar">
        <Werteliste
          eintraege={[
            {
              beschriftung: 'Reichweite',
              wert: 'Unternehmen',
              herkunft: 'Aus Kundenkreis „Team", angehoben durch zwei Umsetzungen',
            },
            {
              beschriftung: 'Kritikalität',
              wert: '3',
              herkunft: 'Aus nachgelagertem Prozess „Produktionsfreigabe"',
            },
            { beschriftung: 'Profil', wert: 'KI0-DS3-MB1-IT1-RG2-UR2' },
          ]}
        />
      </Karte>

      <Karte titel={t('stilprobe.zustaende')}>
        <Hinweis art="information">Der Rahmen dieses Prozesses gilt für alle verknüpften Tools.</Hinweis>
        <Hinweis art="warnung">Ein genutztes Datenobjekt liegt außerhalb des Erlaubnisrahmens.</Hinweis>
        <Hinweis art="fehler">Gate 1 ist noch nicht freigegeben — Aktivierung nicht möglich.</Hinweis>
        <Hinweis art="erfolg">Selbstverpflichtung vollständig abgegeben.</Hinweis>
        <Ladeschimmer beschriftung={t('app.laden')} />
      </Karte>

      <Leerzustand
        zeichen="◇"
        titel="Noch kein Datenobjekt erfasst"
        text="Datenobjekte werden einmal klassifiziert und von allen Prozessen und Tools referenziert."
        aktion={<Knopf art="gefuellt">Datenobjekt anlegen</Knopf>}
      />

      <Karte titel={t('stilprobe.blatt')}>
        <Knopf art="getoent" onClick={() => setBlattOffen(true)}>
          {t('stilprobe.blattOeffnen')}
        </Knopf>
      </Karte>

      {blattOffen && (
        <Blatt
          titel="Datenobjekt anlegen"
          beischrift="Reifegrad 1 — Name, Kategorie, Owner, Quellsystem"
          schliessen={() => setBlattOffen(false)}
          fuss={
            <>
              <Knopf onClick={() => setBlattOffen(false)}>Abbrechen</Knopf>
              <Knopf art="gefuellt" onClick={() => setBlattOffen(false)}>
                Anlegen
              </Knopf>
            </>
          }
        >
          <Feld beschriftung="Name" wert={text} aendern={setText} pflicht />
          <Auswahl
            beschriftung="Kategorie"
            wert={auswahl}
            aendern={setAuswahl}
            leertext="Noch nicht kategorisiert"
            optionen={[
              { wert: 'oeffentlich', text: 'Öffentlich' },
              { wert: 'intern', text: 'Intern — geschäftlich' },
              { wert: 'vertraulich', text: 'Intern — vertraulich' },
              { wert: 'personenbezogen', text: 'Personenbezogen — allgemein' },
              { wert: 'besondere_kategorie', text: 'Personenbezogen — besonders' },
            ]}
          />
        </Blatt>
      )}
    </>
  );
}
