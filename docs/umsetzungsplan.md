# Umsetzungsplan — Governance-Plattform nach Spezifikation

**Stand:** 2026-09-01 · **Grundlage:** `docs/feedback-2026-09-01.md`, Leitdokument Teil A,
Architekturdokument · **Ziel:** Die Anwendung leistet über die Oberfläche genau das, was die
Vorgabe verlangt — und sieht dabei aus wie eine moderne Anwendung, nicht wie ein Formularserver.

Alles Abhakbare steht als To-Do. Ein Haken bedeutet: umgesetzt, getestet, über die **Oberfläche**
nachgewiesen.

---

## 0. Vorgehen in einem Absatz

Wir bauen nicht neu, wir machen erreichbar. Das Datenmodell trägt (siehe Feedback, „Was trägt") —
die Lücke liegt in der Präsentationsschicht und in einer Handvoll fachlicher Details. Deshalb:
zuerst ein Design-System und eine Anwendungshülle (AP-0), dann Modul für Modul, wobei **jedes
Arbeitspaket fachlich vollständig und gestalterisch fertig** abgeschlossen wird — kein „Styling
kommt später". Jedes Paket endet mit einem Abnahmetest, der ausschließlich über die Oberfläche
läuft.

### Getroffene Entscheidungen

Diese Punkte habe ich entschieden, damit der Plan konkret wird. Widerspruch jederzeit möglich —
sie sind einzeln umkehrbar:

| # | Entscheidung | Begründung |
|---|---|---|
| E-A | React 18 + Vite bleiben, kein Framework-Wechsel | Architektur 6.2 legt React fest; das Problem ist die Oberfläche, nicht das Werkzeug |
| E-B | Eigenes Design-System, **keine** UI-Bibliothek (kein MUI, kein Tailwind, kein Radix) | Der Apple-Stil lebt von Details, die eine generische Bibliothek überschreibt; die Abhängigkeitsliste bleibt schlank und auditierbar. Barrierefreiheit bauen wir bewusst selbst, mit Tests |
| E-C | System-Schriftstapel statt Webfont | SF Pro auf Apple-Geräten, Segoe/Roboto sonst — kein Nachladen, kein Datenschutzthema, sofort scharf |
| E-D | Hell- **und** Dunkelmodus von Anfang an, über Design-Token | Nachträglich eingezogen wird es nie sauber |
| E-E | Sprachpfade `/de/…`, `/fr/…` bleiben unverändert | Architektur 9.2; die Navigation ändert sich, die URL-Struktur nicht |
| E-F | Deutsche Fachbegriffe bleiben Fachbegriffe (Prozessobjekt, Tool-Objekt, Datenobjekt, Tier) | Sie stehen so im Leitdokument und sind der gemeinsame Wortschatz mit Compliance und Betriebsrat |
| E-G | Kategorie `mitarbeiterbezogen` entfällt, Bestandsdaten werden migriert | Leitdokument A.7 schließt sie ausdrücklich aus (Befund B9) |

---

## 1. Design-System „Klar"

Der Name ist Programm und stammt aus dem ersten Apple-Grundsatz: *Clarity, Deference, Depth* —
Klarheit vor Dekoration, die Oberfläche tritt hinter den Inhalt zurück, Tiefe schafft Ordnung
statt Schmuck.

### 1.1 Grundsätze für dieses Produkt

1. **Der Inhalt ist die Oberfläche.** Kein Rahmen, keine Linie, keine Farbe ohne Aufgabe.
2. **Eine Handlung je Bildschirm ist die Hauptsache.** Sie steht rechts oben oder am Fuß des
   Formulars, immer an derselben Stelle.
3. **Nie ein technischer Schlüssel im Sichtfeld.** Keine UUID, kein `besondere_kategorie`, kein
   nacktes `K1` — alles trägt einen Namen und, wo nötig, einen Erklärungssatz.
4. **Zustand wird gezeigt, nicht erklärt.** Compliance-Farben immer mit Symbol und Wort, nie mit
   Farbe allein (Barrierefreiheit und Ausdruck in Schwarzweiß).
5. **Ruhe.** Bewegung nur, wo sie Herkunft erklärt (Blatt kommt von unten, Detail schiebt von
   rechts). 200–260 ms, `ease-out`, `prefers-reduced-motion` respektiert.

### 1.2 Farbe (Token, hell / dunkel)

Systemnahe Palette, semantisch benannt — Komponenten benutzen **nie** einen Rohwert.

| Token | Hell | Dunkel | Verwendung |
|---|---|---|---|
| `--farbe-akzent` | `#007AFF` | `#0A84FF` | Primäraktion, Auswahl, Fokus |
| `--farbe-gruen` | `#34C759` | `#30D158` | Compliance grün |
| `--farbe-gelb` | `#FF9F0A` | `#FFD60A` | Nicht zugeordnet |
| `--farbe-rot` | `#FF3B30` | `#FF453A` | Non-compliant, Zerstörendes |
| `--farbe-lila` | `#AF52DE` | `#BF5AF2` | Gate-Vorgänge |
| `--text-primaer` | `#000000` (85 %) | `#FFFFFF` (92 %) | Fließtext, Überschriften |
| `--text-sekundaer` | `#3C3C43` (60 %) | `#EBEBF5` (60 %) | Beschriftungen, Hilfstext |
| `--text-tertiaer` | `#3C3C43` (30 %) | `#EBEBF5` (30 %) | Platzhalter, deaktiviert |
| `--flaeche` | `#FFFFFF` | `#1C1C1E` | Karten, Listen |
| `--flaeche-gruppiert` | `#F2F2F7` | `#000000` | Seitenhintergrund |
| `--flaeche-erhoben` | `#FFFFFF` | `#2C2C2E` | Blätter, Popover |
| `--trennlinie` | `#3C3C43` (18 %) | `#545458` (40 %) | Haarlinie 0.5 px |
| `--fuellung-steuerung` | `#78788014` | `#7878805C` | Segmentierte Steuerung, Suchfeld |

Tier-Kennzeichnung: Tier 1 grau, Tier 2 orange, Tier 3 rot, gesperrt schwarz mit Warnsymbol.
Jede Farbe erreicht in beiden Modi mindestens AA gegen ihren Untergrund.

### 1.3 Typografie

System-Stapel: `-apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif`.
Ziffern in Tabellen und Kennzahlen `font-variant-numeric: tabular-nums`.

| Rolle | Größe / Zeilenhöhe | Gewicht | Verwendung |
|---|---|---|---|
| Großtitel | 34 / 41 | 700 | Seitentitel im Cockpit |
| Titel 1 | 28 / 34 | 700 | Seitentitel |
| Titel 2 | 22 / 28 | 600 | Abschnitte |
| Titel 3 | 20 / 25 | 600 | Kartenüberschriften |
| Kopfzeile | 17 / 22 | 600 | Listenzeile, Betonung |
| Fließtext | 17 / 22 | 400 | Standard |
| Hinweis | 15 / 20 | 400 | Beschriftungen, Sekundäres |
| Fußnote | 13 / 18 | 400 | Hilfstexte, Zeitstempel |
| Etikett | 12 / 16 | 600, `0.06em` Laufweite, Versalien | Gruppenüberschriften in Listen |

### 1.4 Raster, Radien, Tiefe

- **Raster:** 4 px Basis; benutzt werden 4, 8, 12, 16, 20, 24, 32, 48. Inhaltsbreite max. 960 px,
  Formulare max. 640 px — Zeilenlänge bleibt lesbar.
- **Radien:** 8 px Steuerelemente, 12 px Karten, 20 px Blätter, 999 px Pillen.
- **Tiefe:** genau drei Stufen. Haarlinie (Listen), weiche Karte
  (`0 1px 3px rgba(0,0,0,.08), 0 8px 24px rgba(0,0,0,.04)`), Blatt
  (`0 24px 64px rgba(0,0,0,.24)`). Keine weiteren Schatten.
- **Material:** Titelleiste und Seitenleiste mit `backdrop-filter: saturate(180%) blur(20px)` über
  halbtransparenter Fläche.

### 1.5 Bewegung

| Anlass | Dauer | Kurve |
|---|---|---|
| Zustandswechsel (Farbe, Deckkraft) | 150 ms | `ease-out` |
| Blatt / Dialog erscheint | 260 ms | `cubic-bezier(.32,.72,0,1)` |
| Listenzeile aus-/einblenden | 200 ms | `ease-out` |
| Ladeschimmer | 1.4 s | Schleife, bei `reduced-motion` statischer Platzhalter |

### 1.6 Komponenteninventar (`frontend/src/ui/`)

Jede Komponente: eigene Datei, gemeinsame `ui.css` (die Bausteine teilen Masse und Zustaende —
getrennte Dateien wuerden diese Bezuege verstecken), Test, beide Sprachen, Tastaturbedienung.

- [x] `Knopf` — Varianten: gefüllt, getönt, unauffällig, zerstörend; Größen m/l; Ladezustand
- [x] `Feld` — Text, Zahl, mehrzeilig; Beschriftung, Hilfstext, Fehlertext, Zeichenzähler
- [x] `Auswahl` — einzeln, mit Beschreibungstext je Option
- [x] `Umschalter` — Apple-Switch, 51 × 31, mit Beschriftung links
- [x] `SegmentierteSteuerung` — für Filter und den Modus des Bewertungs-Wizards
- [x] `Suchfeld` — Grundform steht; Löschknopf und globaler `⌘K`-Aufruf kommen mit AP-8
- [x] **`ReferenzWaehler`** — Kernstück: Suche über Bestand, Mehrfachauswahl als Chips,
      Kategorie-Abzeichen je Treffer, „neu anlegen" inline, Tastatur vollständig, ARIA-Combobox
- [x] `GruppierteListe` + `Zeile` — iOS-Settings-Muster: Beschriftung links, Wert/Steuerung rechts,
      Haarlinie zwischen Zeilen, abgerundete Gruppe mit Etikett darüber
- [x] `Karte` — Inhaltsbehälter mit Titel, optionaler Fußzeile und Aktion
- [x] `Abzeichen` — Statuspille: Compliance (Symbol + Wort), Tier, Herkunft, Gate-Status
- [x] `Blatt` — Sheet von unten (mobil) / mittig (Schreibtisch), Fokusfalle, `Esc`
- [ ] `Dialog` — Bestätigung für zerstörende Aktionen (mit AP-2, Umklassifizierungs-Vorschau)
- [x] `Hinweisstreifen` — Erfolg / Warnung / Fehler, mit Symbol
- [x] `Leerzustand` — Symbol, Satz, Hauptaktion — nie eine leere Fläche
- [x] `Ladeschimmer` — Platzhalter in Zeilen- und Kartenform
- [x] `Seitenkopf` — Titel, Rückweg, Hauptaktion, Untertitelzeile
- [x] `Werteliste` — Beschriftung/Wert-Paare für Detailansichten, mit „abgeleitet"-Kennzeichnung
- [ ] `Fortschrittspunkte` — Schrittanzeige des Wizards (mit AP-4)

### 1.7 Markenschichten

Die Token-Schicht macht die Marke austauschbar: eine Marke ist ein Satz Werte, keine zweite
Komponentenbibliothek. Wer `data-marke` am Wurzelelement setzt, bekommt dieselben Bausteine in
einem anderen Auftritt — die Bausteine selbst werden dafuer nicht angefasst.

- **`klar`** (Standard) — die in 1.1 bis 1.6 beschriebene Ausprägung.
- **`kaufland`** (`src/stil/marke-kaufland.css`, Vorschau) — Markenrot `#E10915`
  (Pantone 2035 C) und Weiß; kantigere Radien (4 px), flache Flächen mit Konturlinie statt
  weicher Schatten, kräftigere Schriftschnitte, durchgefärbt rote Seitenleiste. Umschaltbar auf
  der Stilprobe.

Zwei Dinge sind dabei bewusst entschieden und gelten für jede künftige Marke:

1. **Markenrot ist nicht Statusrot.** Wo die Marke rot ist, bleibt das Markenrot der Hauptaktion
   vorbehalten; der Zustand „non-compliant" trägt eine dunklere Nuance und wie überall zusätzlich
   Symbol und Wort. In der Dunkelvariante bleibt eine Restnähe der beiden Rottöne — hier
   entscheidet am Ende der Markenverantwortliche.
2. **Informationsblau ist ein eigenes Token.** `--farbe-blau` hängt nicht am Akzent, sonst wäre in
   einer roten Marke „Importiert" nicht von „non-compliant" zu unterscheiden.

Öffentlich festgelegt sind bei Kaufland nur Rot und Weiß; Grauabstufungen, Statusfarben und die
gesamte Dunkelvariante sind daraus abgeleitet und als Vorschlag zu lesen. Die Hausschrift ist
nicht frei lizenziert — ersetzt durch eine sachliche Grotesk aus dem Systemstapel.

### 1.8 Wiederkehrende Muster

- **Referenz statt Freitext:** Überall, wo die Vorgabe eine ID verlangt, steht der
  `ReferenzWaehler`. Er zeigt beim Treffer sofort die Kategorie mit Farbe — der Nutzer sieht beim
  Auswählen, was er sich einhandelt.
- **Abgeleitet ist sichtbar abgeleitet:** Berechnete Werte stehen in einer eigenen Gruppe mit
  Schlosssymbol und dem Satz „Abgeleitet — nicht eingebbar", jeder Wert mit Herkunftsangabe
  („Kritikalität 3 — aus nachgelagertem Prozess *Produktionsfreigabe*").
- **Wizard als Blatt:** Der Bewertungsbaum läuft in einem Blatt über der Prozessansicht, eine Frage
  je Bildschirm, große Antwortknöpfe, Fortschrittspunkte, Zurück erlaubt.
- **Cockpit als Kartenraster:** Je A.14-Zeile eine Karte mit Zahl, Kurzsatz und Farbpunkt; Klick
  öffnet die gefilterte Liste. Keine Kennzahl ohne Handlungsangebot.

---

## 2. Arbeitspakete

### AP-0 — Design-System und Anwendungshülle

**Anwendervorgänge** aus `docs/vorgaenge.md`: 6 laufen (V-ANM-01–06). Das Paket gilt erst als
fertig, wenn sie im Durchlauf `npm run vorgaenge` grün sind.

*Kein fachliches Verhalten ändert sich. Danach sieht jede Folgearbeit richtig aus, ohne Nacharbeit.*

- [x] `src/stil/token.css` — Farben, Typografie, Abstände, Radien, Tiefe, Bewegung; hell/dunkel
      über `prefers-color-scheme` **und** manuelle Übersteuerung per `data-farbschema`
- [x] `src/stil/basis.css` — Zurücksetzung, Fokusring (2 px Akzent, 2 px Abstand), Auswahlfarbe,
      `prefers-reduced-motion`, 44 px Mindest-Trefferfläche
- [x] Komponenten aus 1.6 anlegen, je mit Test (Tastatur, ARIA, beide Farbschemata)
- [x] `Layout` neu: Seitenleiste (Cockpit · Prozesse · Tools · Datenobjekte · Gates · Lenkung ·
      Administration), Titelleiste mit Suche, Nutzermenü mit Rollenanzeige, Sprach- und
      Farbschemawahl; auf schmalen Fenstern Leiste unten
- [x] `Anmeldung` neu gestalten (zentriertes Blatt, Produktname, Hinweis auf zentrale Identität)
- [x] Route `/:sprache/stilprobe` — Musterseite aller Komponenten in beiden Schemata, dient als
      lebende Dokumentation und als Sichtprüfung
- [x] Übersetzungen de/fr für alle neuen Texte
- [x] `npm run coverage` hält 90 % / 85 % Zweige

**Abnahme:** Stilprobe zeigt alle Komponenten in hell und dunkel; Tastaturweg durch die gesamte
Hülle ohne Maus; keine Regression in `./pruefen.sh`.

### AP-1 — Prozessobjekt vollständig *(Befunde B1, B2, B3, B14)*

**Anwendervorgänge** aus `docs/vorgaenge.md`: 22 laufen (V-PRO-01–22). Das Paket gilt erst als
fertig, wenn sie im Durchlauf `npm run vorgaenge` grün sind.

**Backend**
- [x] `output_datenobjekt_ids` in `ProzessAnlegen` und `ProzessAendern` aufnehmen, im Service
      verarbeiten (`services/prozess.py`), Changelog-Diff ergänzen
- [x] Granularitätsregeln aus A.5: Warnung ab 8 Schritten in der P-Spalte (Feld `process_steps`),
      Zeichenbegrenzungen (Supplier 200, Schritte 1000, Output 200, Ausfallfolge-Freitext entfällt)
- [x] Prüfung: Vorgänger/Nachfolger dürfen keinen Zyklus erzeugen — mit klarer Fehlermeldung
- [x] Tests: Kante über API erzeugbar, Zyklus abgelehnt, Zeichengrenzen greifen

**Oberfläche**
- [x] Anlageformular neu: die zehn A.5-Felder, davon **Input-Datenobjekte, Output-Datenobjekte,
      vorgelagerte und nachgelagerte Prozesse als `ReferenzWaehler`**, Supplier als Auswahl
      vorgelagerter Prozesse mit Freitext-Ausweichfeld
- [x] Organisationseinheiten sprechend benennen: „Finance — INT" / „Finance — Land DE" statt
      UUID-Fragment
- [x] Schrittzähler unter der P-Spalte mit Warnung ab 8 Schritten
- [x] **Bearbeiten-Ansicht** (`prozesse/:id/bearbeiten`) mit denselben Feldern
- [x] Statusaktionen „Aktivieren" / „Stilllegen"; verweigert die Prüfung aus E-9, wird der Grund
      genannt („Gate 1 ist noch nicht freigegeben") mit Sprung zum fehlenden Schritt
- [x] Detailansicht: Datenobjekte und Prozesskette als klickbare Chips, abgeleitete Werte mit
      Herkunftsangabe, Tier- und K-Klassen-Abzeichen
- [x] Ansicht „Wirkung" je Prozess: aufwärts (wer beliefert) und abwärts (was steht still) als
      Kettenliste — A.4.3

**Abnahme (nur über die Oberfläche):** Ein Prozess-Owner legt einen Prozess mit zwei
Input-Datenobjekten, einem Output-Datenobjekt und einem nachgelagerten Prozess an, sieht die
Kritikalität aus der Kette berechnet, ändert die Ausfallfolge des Nachfolgers und sieht die
Kritikalität des Vorgängers steigen.

### AP-2 — Datenobjekt vollständig *(B4, B9)*

**Anwendervorgänge** aus `docs/vorgaenge.md`: 12 laufen (V-DAT-01–12). Das Paket gilt erst als
fertig, wenn sie im Durchlauf `npm run vorgaenge` grün sind.

**Backend**
- [x] Feld `quellsystem` (fachliche Herkunft, A.7 Stufe 1) getrennt von `quelle` (Sync-Quelle)
- [x] Kategorien auf die fünf aus A.7 zurückführen; Alembic-Migration bildet
      `mitarbeiterbezogen` → `personenbezogen` ab und setzt einen Vermerk im Changelog
- [x] Mitbestimmungsflag neu ableiten: Personenbezug **und** (Wirkung auf Einzelperson **oder**
      Leistungs-/Verhaltensdaten aus Attestierung/Bewertung) — A.5
- [x] Endpunkt „Wirkung einer Umklassifizierung": welche Prozesse und Tools betrifft eine
      Kategorieänderung, welches Tier ergäbe sich (A.4.7, Simulation vor Entscheidung)

**Oberfläche**
- [x] Anlage als Blatt: Name, Kategorie (mit Ankertext aus A.7 je Option), Owner, Fachbereich,
      Quellsystem, Beschreibung — die „30 Sekunden" aus A.7
- [x] Detailseite `datenobjekte/:id` mit zwei Rückwärtssichten: „referenziert von Prozessen",
      „genutzt von Tools" (mit Zugriffsart)
- [x] Umklassifizierung zeigt vor dem Speichern die Wirkung: „betrifft 6 Prozesse, 14 Tools, davon
      3 künftig Tier 3" mit Bestätigungsdialog
- [x] Kategorien übersetzt, farbig abgezeichnet, sortiert nach Schutzbedarf

**Abnahme:** Kategorie eines Datenobjekts über die Oberfläche ändern, Wirkungsvorschau sehen,
danach am verknüpften Prozess das geänderte Mitbestimmungsflag sehen.

### AP-3 — Tool-Objekt vollständig *(B5, B6)*

**Anwendervorgänge** aus `docs/vorgaenge.md`: 22 laufen (V-INT-01–05, V-TOO-01–17). Das Paket gilt
erst als fertig, wenn sie im Durchlauf `npm run vorgaenge` grün sind.

**Backend**
- [x] Attestierungen 1–3 aus A.6 als eigene Felder mit Erklärendem, Zeitpunkt und Person
- [x] `lauftyp` (interaktiv / getriggert / geplant) und `stellvertretung_user_id` am Tool-Objekt
- [x] Attestierungen fließen in Mitbestimmungs- und Wirkungsbewertung ein („kein Mensch dazwischen"
      ⇒ verändernd) — E-23, E-24
- [x] Pflicht: Ohne beantwortete Attestierungen keine Prozessverknüpfung — E-22
- [x] Zweckbindungsprüfung nach A.4.6, zweistufig — E-25
- [x] Kantenänderungen erzeugen einen Changelog-Eintrag — E-26

**Oberfläche**
- [x] Tool-Anlage mit technischem Owner, Stellvertretung, Technologie, Organisationseinheit
- [x] **Datenobjekt-Verknüpfung im Tool-Detail** mit Zugriffsart (liest / schreibt / beides),
      genutzt den `ReferenzWaehler`; Warnhinweis, wenn ein genutztes Datenobjekt außerhalb des
      Prozessrahmens liegt
- [x] Attestierungskarte: drei Fragen im Klartext aus A.6, mit Umschaltern und Datum der Erklärung
- [x] Geerbte Klassifikation mit Quellenangabe je Prozesskante
- [x] Altregel `button { … }` aufgehoben, die jeden Knopf einfärbte — sie machte Namen im
      Referenz-Wähler unsichtbar (Betriebsbefund, E-27); `e2e/darstellung.spec.ts` sichert es ab
- [x] Compliance-Zustand am Tool ins Design-System überführt — die letzte Rohtabelle auf dieser
      Seite; „Styling kommt später" gilt auch für mitgezogene Bestandteile nicht

**Abnahme:** Tool anlegen, Owner setzen, Attestierungen beantworten, mit zwei Prozessen und drei
Datenobjekten verknüpfen, geerbtes Maximum und Rahmenwarnung sehen.
✅ `e2e/phase3.spec.ts`, vier Durchläufe über die Oberfläche.

### AP-4 — Bewertung mit Ableitung *(B8)*

**Anwendervorgänge** aus `docs/vorgaenge.md`: V-BEW-01–12, alle zwölf im Durchlauf
`npm run vorgaenge` grün.

**Backend**
- [x] Vorschlagsdienst je Dimension nach A.8.4: DS aus Datenobjektkategorien und Kundenkreis, MB
      aus Kategorien und Attestierungen, UR aus Ausfallfolge und Kettenkritikalität; KI und RG
      bleiben vollständig zu erklären — `services/vorschlag.py`, siehe E-29 zur Beweislastregel
- [x] Vorschlag und tatsächliche Antwort werden **beide** gespeichert; Abweichung verlangt eine
      Begründung, schon im Wizard-Schritt und nicht erst beim Abschluss
- [x] Cockpit-Befund „Antwort widerspricht Datenlage", der begründete Abweichung von geänderter
      Datenlage unterscheidet (E-30)

**Oberfläche**
- [x] Wizard neu: eine Frage je Bildschirm, große Antwortflächen, Fortschrittspunkte, Zurück mit
      erhaltener Vorbelegung, Abbruch mit Sicherung als Blatt
- [x] Modusauswahl „Schnell" / „Vollständig" als segmentierte Steuerung zu Beginn, mit Erklärung
      der Folge (A.8.5)
- [x] Vorschlagskarte je Frage mit Beleg und Quelle; abweichende Antwort öffnet ein
      Begründungsfeld und hält den Schritt an
- [x] Ergebnisseite: Tier groß, Profil als Kette `KI0-DS3-…`, ausgelöste Klassen **mit Namen und
      Erklärungssatz** aus A.9.2, dazu die Auflagen je Tier aus A.8.6
- [x] Verbotstatbestand (1b): eigener roter Ausgang, keine Bewertung, Alarm sichtbar, Verweis auf
      Governance/Recht

**Abnahme:** Bewertung mit Profil `KI0-DS3-MB1-IT1-RG2-UR2` liefert über die Oberfläche Tier 3 und
genau K1, K2, K3, K4, K5, K7, K8, K9 — mit lesbaren Namen.

### AP-5 — Selbstverpflichtung nach A.10 *(B7)*

**Anwendervorgänge** aus `docs/vorgaenge.md`: V-GAT-01–06 und V-SEL-01–08, alle vierzehn im
Durchlauf `npm run vorgaenge` grün.

- [x] Katalog wortgetreu auf A.10.2 (sechs Aussagen) und A.10.3 (sechs Aussagen) umgestellt; neue
      Kennungen `PE1`…`PE6` und `TO1`…`TO6`, Bestandsdaten unangetastet mit `katalog_version = 1`
      (E-32). Die Schicht-2-Verbote aus A.13.2 sind aus dem Katalog entfernt — sie gehören nach AP-6
- [x] Bindung an `bewertung_id`: eine neue Bewertung entwertet die Erklärung automatisch (A.10.4);
      bei Tool-Objekten trägt `tier_bei_abgabe` dieselbe Aufgabe
- [x] Kurzform für Tier 1 (A.10.5), vollständige Form ab Tier 2, Jahresbestätigung ab Tier 3
- [x] Route und Ansicht für die Erklärung des **technischen Owners** am Tool-Objekt
- [x] Oberfläche: je Aussage ein Block mit Umschalter und einklappbarem Kommentar, Kopfzeile mit
      Datum und gebundener Profilversion; Jahresbestätigung als ein Klick
- [x] Cockpit-Anschluss: neue Zeile „Attestierungen älter als die Frist"; die Zeile
      „Selbstverpflichtungen ohne Deckung" nennt jetzt auch die Erklärungen, die mit dem Profil
      verfallen sind
- [x] Eine Gate-Ablehnung ist zu begründen (V-GAT-03) — ohne Grund erfährt der Einreichende nur,
      dass es nicht weitergeht

**Abnahme:** Tier-3-Prozess lässt sich ohne vollständige Erklärung nicht aktivieren; nach
Neubewertung erscheint die Erklärung als „verfallen".

### AP-6 — Erlaubnisrahmen, Schicht 2, Lenkungsfristen *(B10, B11)*

**Anwendervorgänge** aus `docs/vorgaenge.md`: V-PRO-23, V-RAH-01–10, V-TOO-18 und V-ADM-07, alle
dreizehn im Durchlauf `npm run vorgaenge` grün. V-ADM-07 stand für AP-9 vorgesehen — die
Konfigurationsansicht kommt aber mit diesem Paket, und ein Vorgang gehört zu der Lieferung, die
ihn erfüllt.

**Backend**
- [x] Rahmen um die fehlenden vier Elemente ergänzt: Obergrenze der Datenkategorie, erlaubte
      Zugriffsart, erlaubte Ausführungsart, erlaubte Ausführungsidentität — `services/rahmen.py`,
      siehe E-38 zur Herkunft jedes Elements und zum Zirkel, den die Zugriffsart vermeidet
- [x] Neben jedem erlaubten Wert der **gemessene**; die Reichweite hat als einzige keinen und sagt
      das auch. Die Query-API bekommt weiterhin nur die erlaubte Seite
- [x] Schicht 2 als abschließende Liste der sechs Verbote mit Prüffunktion; vier erkennt die
      Anwendung selbst, zwei sind zu melden (E-37). Ein Verstoß startet den Lenkungsvorgang
      **unmittelbar in Stufe 2** und hebt einen laufenden Stufe-1-Vorgang an
- [x] Fristen berichtigt: Stufe 1 = 30 / 15 / 5 **Arbeitstage**, Stufe 2 = zusätzlich 15 / 10 / 5,
      ab Stufe 3 keine mehr; Wochenenden übersprungen, Feiertage erklärt ausgenommen (E-39)
- [x] Ein neu erklärtes externes Ziel reicht Gate 2 selbst ein (A.11, E-40)

**Oberfläche**
- [x] „Erlaubnisrahmen" als Karte am Tool: erlaubt, gemessen und die Abweichung als Satz, dazu die
      selbst erkannten Schicht-2-Befunde
- [x] Lenkungsvorgang als Karte mit Frist als Countdown in Arbeitstagen und den drei
      Auflösungswegen als gleichrangige Knöpfe (A.13.6); „Rahmen erweitern" wählt eine Bewertung
      statt einer UUID (E-41)
- [x] Schicht-2-Meldung am Tool-Objekt: Auswahl aus den sechs Verboten, mit der Folge davor
- [x] Erlaubte externe Ziele am Prozessformular, gemessene am Tool-Objekt
- [x] Konfigurationsansicht für die Governance-Rolle (Fristen, Schwellen, Vorlauf) — Architektur 6.6

**Abnahme:** Ein gemeldeter Schicht-2-Verstoß erzeugt sofort Stufe 2; ein Tier-1-Verstoß bekommt
30 Arbeitstage, nach Ablauf 15 weitere.

### AP-7 — Anforderungsklassen und Technologiematrix *(B12)*

**Anwendervorgänge** aus `docs/vorgaenge.md`: V-KLA-01–06, alle sechs im Durchlauf
`npm run vorgaenge` grün.

- [x] K1–K10 mit Name, Zweck und Auslöserbedingung (A.9.2). Name und Zweck standen schon in
      `services/bewertung.py`; die Auslöserbedingung ist neu und wird von einem Test gegen die
      Rechnung gehalten, damit der Satz nicht von ihr abdriftet
- [x] Technologiematrix als Tabelle Technologie × Klasse mit `erfuellt` / `kompensierbar` /
      `nicht_erfuellbar` (Teil C.1) — gepflegte Stammdaten in der Datenbank, änderbar durch die
      Governance-Rolle, jedes Feld mit Pflichtbegründung (E-42)
- [x] Prüfdienst `services/klassen.py`: ausgelöste Klassen gegen die Technologie der Tools.
      Ausschluss, fehlende Kompensation und **ungeprüft** sind drei Befundarten — eine fehlende
      Technologieangabe ist kein Nachweis
- [x] Cockpit-Zeile „Technologie erfüllt ausgelöste Anforderungsklasse nicht" (A.14)
- [x] Oberfläche: Klassen- und Matrixansicht unter `/klassen`, Befundkarte am Tool mit dem
      nötigen Schritt, Sammelkarte am Prozess, Kompensationsvermerk mit Pflichttext
- [x] Die Technologieliste kommt vom Server: Tool-Auswahl und Matrix benutzen dieselbe Liste

**Abnahme:** Ein Tier-3-Prozess mit einer Technologie, die K5 nicht erfüllt, erscheint als
Ausschlussfall im Cockpit und am Tool.

### AP-8 — Cockpit *(B12)*

**Anwendervorgänge** aus `docs/vorgaenge.md`: V-COC-01–10, alle zehn im Durchlauf
`npm run vorgaenge` grün.

- [x] „Technologie erfüllt ausgelöste Anforderungsklasse nicht" — mit AP-7 gekommen, weil die
      Abnahme dieses Pakets sie verlangt
- [x] „Alt-Anwendungen im Melde-/Blockierungspfad" (A.16) als vierzehnte Zeile ergänzt, mit
      Melde- und Blockierungspfad an einer konfigurierbaren Frist (E-43)
- [x] Übersicht als Kachelraster mit Zahl, Zustandszeichen und Handlungssatz je Zeile
- [x] Detailliste je Zeile mit dem Filter in der URL (Architektur 9.3) und Sprung ins
      vorgefilterte Zielmodul — das Ziel mit seinem **Namen**, nicht mit seinem Schlüssel
- [x] „Tier-Verteilung je Technologie und Zeit" als Balkendiagramm: Farbrolle nach Einstufung,
      Menge als Zahl am Segment, dieselben Werte als Tabelle für Vorleseprogramme. Der
      `dataviz`-Leitfaden liegt diesem Repository nicht bei; angewandt sind die drei Punkte, die
      der Plan aus ihm nennt (Farbrolle, Achsen, Zugänglichkeit)
- [x] Sichtbarkeitsregel aus Architektur 4.3 in jeder Ansicht geprüft (V-COC-05, V-COC-06)

**Abnahme:** Alle zwölf Zeilen aufrufbar; ein Nutzer mit LAND-Scope sieht ausschließlich seinen
Bereich; jeder Klick landet vorgefiltert im Zielmodul.

### AP-9 — Administration und Rollen *(B13)*

**Anwendervorgänge** aus `docs/vorgaenge.md`: V-ADM-01–06 und V-INT-06, alle sieben im Durchlauf
`npm run vorgaenge` grün.

- [x] Nutzerliste mit Suche über Name und E-Mail, Aktivstatus und Führungskraft. Die
      Führungskraft ist auch **setzbar** — ohne sie läuft die Eskalation nach A.13.5 an den
      Betroffenen selbst zurück
- [x] Rollenzuweisung `(Nutzer, Rolle, Scope)` als Blatt, mit der Erklärung je Rolle aus A.15
- [x] Wirkungsvorschau vor der Entscheidung: „Diese Zuweisung gibt zusätzlich Zugriff auf N
      Prozessobjekte" — gezählt wird das **Hinzukommende**, über dieselben
      Sichtbarkeitsfunktionen, die später auch greifen (E-45)
- [x] Nachweisansicht unter `/nachweis`: jede schreibende Aktion mit Zeitpunkt, Person und
      Vorher/Nachher je Feld (A.13.7, V-INT-06)
- [x] Konfigurationsansicht steht seit AP-6 unter `/konfiguration`
- [x] Verwaltung nur für den App-Administrator, Nachweis zusätzlich für Auditor und Governance —
      in der Navigation ausgeblendet **und** serverseitig geprüft

**Abnahme:** Der Bootstrap-Administrator vergibt über die Oberfläche eine Prozess-Owner-Rolle auf
einer INT-Einheit; der so berechtigte Nutzer sieht danach genau die zugehörigen Prozesse.

### AP-10 — Abnahme neu aufsetzen *(B15)*

**Anwendervorgänge:** keine eigenen. Dieses Paket macht den Katalog zur Abnahmegrundlage —
alle **124** Vorgänge aus `docs/vorgaenge.md` laufen, keiner wird mehr übersprungen. (Der
Playwright-Bericht zeigt 132 Läufe: die 124 Vorgänge und die acht Selbstprüfungen des Katalogs.)

- [x] Für jedes Kriterium aus Architektur 11, das mit „ein *Rolle* kann" beginnt, ein Durchlauf,
      der **ausschließlich** über die Oberfläche arbeitet — das ist der Vorgangskatalog, gewachsen
      mit AP-1 bis AP-9
- [x] API-Aufrufe im Aufbau nur für Vorbedingungen, die die geprüfte Rolle selbst nicht herstellen
      darf; jede Ausnahme steht als Kommentar am Ort (E-35)
- [x] `pruefen.sh` benennt den Durchlauf als **Abnahme** und sagt, warum er die Grundlage ist
- [x] `docs/phasen.md` neu belegt: je Kriterium die Vorgänge, die es über die Oberfläche zeigen —
      die technischen Tests stehen daneben, nicht mehr allein (E-46)
- [x] Die Zuordnung prüft sich selbst: zwei Läufe in `katalog.vorgang.ts` halten jede zitierte
      Kennung gegen den Katalog und jedes Kriterium gegen seine Vorgangsspalte
- [x] Phasen 1 bis 7 auf dieser Grundlage erneut abgenommen

### AP-11 — Rechte bis ins Frontend

**Anwendervorgänge:** V-RCH-01 bis V-RCH-08. Spezifikation in
[`docs/rechte-und-rollen.md`](rechte-und-rollen.md).

Das Rechtemodell ist tragfähig und wird nicht angefasst: Rolle × Bereich, sechs objektbezogene
`darf_*`-Funktionen, Scope-Filterung im Lesepfad, 40 Testfälle. Es endet nur an der API. Wo
jemand lesen, aber nicht schreiben darf, zeigt die Oberfläche heute Eingabefelder und quittiert
erst das Speichern mit einem generischen Fehler. Dieses Paket reicht die Auskunft durch —
**ohne die Durchsetzung zu verlagern.**

- [ ] `RechtAus` (Erlaubnis plus Grund) und je Objekt ein benanntes Rechtebündel, berechnet aus
      den vorhandenen `darf_*`-Funktionen — keine zweite Rechtequelle (E-48, E-49)
- [ ] Zuordnungstabelle `Route → Objektrecht` für jede schreibende Route, und der Test, der
      beide Seiten gegeneinander hält: verweigertes Recht ⟹ 403, erteiltes Recht ⟹ kein 403.
      Eine Route ohne Eintrag lässt den Test fehlschlagen
- [ ] `hatRolle` bekommt den Bereich zurück — dieselbe Auflösung wie `Principal.hat_rolle`;
      ohne Bereichsangabe bleibt das heutige Verhalten (`Sitzung.tsx:97`)
- [ ] Der vorhandene `gesperrt`-Pfad (`ToolDetail.tsx:223`) bekommt einen zweiten Sperrgrund;
      Herkunftssperre und Rechtesperre sind im Text unterscheidbar (E-52)
- [ ] Gesperrte Felder bleiben sichtbar und nennen den Grund am Feld; Aktionsknöpfe hängen am
      Objektrecht statt an der Rolle (E-51)
- [ ] Fehlt die Rechteangabe, gilt „bedienbar" — die Oberfläche wirkt nie strenger als der
      Server entscheidet (E-50)
- [ ] V-RCH-01 bis V-RCH-08 scharfgeschaltet, insbesondere V-RCH-07: zwei Rollen in
      verschiedenen Bereichen in derselben Sitzung

---

## 3. Reihenfolge und Meilensteine

| Meilenstein | Enthält | Ergebnis |
|---|---|---|
| **M1 — Sichtbar anders** | AP-0 | Die Anwendung sieht aus wie ein Produkt; Stilprobe als Beleg |
| **M2 — Der Graph steht** | AP-1, AP-2, AP-3 | Alle Kanten über die Oberfläche erfassbar; damit erfüllt die Anwendung erstmals ihren Zweck |
| **M3 — Bewertung trägt** | AP-4, AP-5 | Ableiten statt abfragen; Erklärungen nach Vorgabe |
| **M4 — Regelkreis geschlossen** | AP-6, AP-7 | Rahmen, Verbote, Fristen, Technologieentscheidung |
| **M5 — Steuerung** | AP-8, AP-9 | Cockpit vollständig, Anwendung selbsttragend |
| **M6 — Abgenommen** | AP-10 | Nachweise über den Nutzerweg statt über die API |

Zwischen den Meilensteinen bleibt die Anwendung jederzeit lauffähig und nutzbar — kein Paket
hinterlässt einen halben Zustand.

---

## 4. Für jedes Arbeitspaket gilt (Definition of Done)

- [ ] Fachlich vollständig **und** gestalterisch fertig — kein „Styling kommt später"
- [ ] Bedienbar mit Tastatur allein; Fokus immer sichtbar; Beschriftungen verbunden
- [ ] Hell und dunkel geprüft; Farbe nie alleiniger Bedeutungsträger
- [ ] Texte in `de` und `fr`, keine rohen Schlüssel im Sichtfeld
- [ ] Bildschirmtext ist richtiges Deutsch, auch der aus dem Server (E-34). Die im berührten
      Modul verbliebenen ASCII-Umschreibungen („Ueberfaellige", „haengen") werden dabei
      mitgezogen — dafür gibt es keinen eigenen Sammeldurchlauf
- [ ] Serverseitige Berechtigungsprüfung auf jeder neuen Route (Architektur 10.2)
- [ ] Schreibende Aktion erzeugt einen Changelog-Eintrag
- [ ] Backend ≥ 90 % Abdeckung, Frontend ≥ 90 % (85 % Zweige), `./pruefen.sh` grün
- [ ] Abnahme über die Oberfläche, nicht über die API
- [ ] Die zugeordneten **Anwendervorgänge** aus `docs/vorgaenge.md` sind von `offen` auf
      `erfüllt` gesetzt und laufen im Durchlauf `npm run vorgaenge`
- [ ] Abweichung von der Vorgabe? Dann als Eintrag in `docs/entscheidungen.md`, mit Grund
