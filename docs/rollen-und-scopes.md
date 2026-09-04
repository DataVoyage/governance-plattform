# Rollen und Scopes — der Sollzustand

Dieses Dokument legt fest, **wer in der Anwendung was mit welchem Objekt tun
darf**. Es leitet die Regeln aus dem Leitdokument (A.4, A.6, A.7, A.10, A.13,
A.15) und aus den tatsächlichen Sichten der Anwendung ab und beschreibt den
Zustand, den Code, Oberfläche und Beispielbestand einhalten müssen. Wo der Code
heute davon abweicht, steht es am Ende in Abschnitt 9 — als nummerierte Liste,
damit Änderungen darauf verweisen können.

Es ist die eine Stelle, an der eine Berechtigungsregel entschieden wird. Eine
Route, ein Formular oder ein Dropdown, das etwas anderes tut als hier
beschrieben, ist ein Fehler — nicht eine zweite Meinung.

---

## 1. Die Grundregel: Rolle × Bereich

Eine Berechtigung entsteht **nie aus einer Rolle allein** und **nie aus einem
Bereich allein**, sondern immer aus der Kombination (P-App-3). „Prozess-Owner"
sagt, *was* jemand darf; der Bereich sagt, *woran*. Dieselbe Rolle mit zwei
Bereichen ergibt zwei verschiedene Berechtigungen — der Beispielbestand zeigt
das an `prozessowner` (ganzer Vertrieb) und `bereichsowner` (nur Logistik
International).

Daraus folgen drei Sätze, die an jeder Stelle gelten:

1. **Sehen ist eine Berechtigung.** Was jemand nicht sehen darf, liefert die
   API nicht — weder in Listen noch beim Direktaufruf über die Kennung, noch
   in Auswertungen, noch in Dropdowns. Die Oberfläche blendet nichts aus, was
   der Server geliefert hat; sie bekommt es gar nicht erst.
2. **Die Regel steht einmal.** Für jedes Objekt gibt es *eine* Sichtregel und
   *eine* Schreibregel im Dienst. Liste, Detail, Auswertung, Cockpit und
   Wirkungsvorschau benutzen dieselbe Funktion. Zwei Fassungen laufen
   auseinander (E-54).
3. **Der Server rechnet, die Oberfläche liest.** Jede Antwort trägt `rechte`;
   das Frontend baut die Regeln nicht nach (E-53).

---

## 2. Die drei Bereiche

| Scope-Typ | Reichweite | Wer ihn tragen darf |
|---|---|---|
| **global** | das ganze Unternehmen | Governance, Plattform, Auditor, App-Administrator — **nur** diese vier |
| **fachbereich** | ein Fachbereich mit all seinen INT- und LAND-Einheiten | Prozess-Owner, Technischer Owner, Datenobjekt-Owner |
| **organisationseinheit** | genau eine Einheit (INT oder ein Land) | Prozess-Owner, Prozess-Umsetzer, Technischer Owner |

Ein Scope auf einen Fachbereich schließt jede Einheit darunter ein. Ein Scope
auf eine Einheit schließt **nicht** den Fachbereich ein — wer nur Logistik
International hat, sieht Logistik DE nicht.

**Ein Scope zählt nur für seine Rolle.** Wer als Prozess-Umsetzer in Vertrieb
DE eingetragen ist, hat damit den Bereich „Vertrieb DE" — aber nur für das,
was ein Prozess-Umsetzer darf. Er sieht dadurch nicht die Tool-Objekte oder
Datenobjekte des Vertriebs, die einem Technischen Owner oder Datenobjekt-Owner
zustehen. Der Bereich ist an die Rolle gebunden, nicht an die Person.

Die vier globalen Rollen sind die einzigen, die bereichsübergreifend lesen.
Fachbereichsrollen mit Scope „global" gibt es nicht; ein Prozess-Owner für
das ganze Unternehmen wäre die Governance.

---

## 3. Die acht Rollen

Aus A.15, ergänzt um das, was die Anwendung daraus macht.

### Prozess-Owner (Fachbereich)

Trägt das Prozessobjekt. Legt an, hält aktuell, bewertet die sechs
Dimensionen, gibt die Selbstverpflichtung nach A.10.2 ab, reicht Gates ein,
setzt Kanten zu Tool- und Datenobjekten. Scope: Fachbereich oder Einheit.
Sein Recht endet am Prozessgeber: er darf Prozessobjekte, deren
Prozessgeber-Einheit in seinem Bereich liegt — und über diese Prozesse die
angehängten Tool- und Datenobjekte **lesen**.

### Prozess-Umsetzer

Pflegt die lokale Abweichung einer Umsetzung — und nur diese. Der Prozess
gehört ihm nicht. Scope: eine Einheit (LAND). Er sieht die Prozessobjekte,
die in seiner Einheit umgesetzt werden, mit allem, was daran hängt; er
schreibt ausschließlich das Feld `lokale_abweichung` seiner Umsetzung.

### Technischer Owner

Trägt das Tool-Objekt: Zuordnung, die drei Attestierungen nach A.6, Umsetzung
der Anforderungsklassen, Selbstverpflichtung nach A.10.3, Compliance-Meldungen,
kompensierende Maßnahmen. Scope: Fachbereich oder Einheit. Sein Recht endet an
der Einheit des Tool-Objekts. Er liest die Prozess- und Datenobjekte, an denen
seine Tools hängen.

### Datenobjekt-Owner

Klassifiziert die **Quellen** seines Fachbereichs: Kategorie und Stammdaten
der Datenobjekte, einmalig je Quelle. Scope: **nur Fachbereich** — eine Quelle
gehört einer datenhaltenden Stelle, nicht einer Landesorganisation. Er sieht
die Datenobjekte seines Fachbereichs und, um die Wirkung einer
Umklassifizierung zu verstehen, **die Namen** der Prozess- und Tool-Objekte,
die sie referenzieren — in der Wirkungsvorschau am Datenobjekt, nicht als
Zugriff auf deren Detailseiten. Er soll wissen, wen eine Umstufung trifft;
er muss deren Bewertung nicht lesen können.

### Governance

Entscheidet Gate 1 und 2, pflegt Technologiematrix, Anforderungsklassen und
Einstellungen, führt Lenkungsvorgänge, sieht das Cockpit über alles. Scope:
global. Governance darf **alles schreiben**, was eine Fachbereichsrolle
schreiben darf — sie ist die Rückfallebene, wenn ein Bereich keinen Owner hat
(etwa bei vorgefundenen Alt-Anwendungen, A.16). Das ist kein Freibrief, sondern
eine dokumentierte Vertretung: jede solche Handlung steht im Nachweis unter
ihrem Namen.

### Plattform

Betreibt die Adapter: Import, Telemetrie, Bestätigung vorgefundener Objekte.
Scope: global. Liest alles, schreibt **nur** den Bestätigungsstatus
importierter Objekte, deren Anker (solange sie unbestätigt sind) und
Telemetriefelder. Fachliche Felder — Kategorie, Attestierungen, Bewertung —
nie.

Der Import gehört **ihr allein**, auch die Governance hat ihn nicht: ein
Import ist keine fachliche Entscheidung, sondern ein Betriebsvorgang, und im
Nachweis soll stehen, unter welcher Rolle er lief.

### Auditor

Liest bereichsübergreifend mit, einschließlich Nachweis. Ändert **nichts**;
die Rolle ist in `NUR_LESEND` und keine Schreibregel darf sie je bejahen.
Scope: global.

### App-Administrator

Verwaltet Nutzer und Rollenzuweisungen — und sonst nichts. Scope: global.
Sieht Nutzer, Rollen und den Nachweis (um eine Vergabe wiederzufinden). Sieht
die Governance-Objekte nicht anders als jeder Angemeldete: er ist keine
Fachrolle. Die Rolle, die man am sparsamsten vergibt (A.15).

### Ohne Rolle

Ein angemeldeter Nutzer ohne Zuweisung ist kein Fehlerfall, sondern ein
Zustand: er sieht das Regelwerk (Abschnitt 6) und sein Profil — und keine
Governance-Objekte. Nichts, keine leere Liste mit „Anlegen".

---

## 4. Die Objekte und ihr Anker

Jedes Objekt hat genau **einen organisatorischen Anker**, aus dem seine
Sicht- und Schreibregel folgt. Personen hängen an Objekten nur dort, wo das
Leitdokument eine persönliche Verantwortung verlangt.

| Objekt | Organisatorischer Anker | Persönliche Verantwortung | Warum |
|---|---|---|---|
| **Prozessobjekt** | Prozessgeber-Einheit (Pflicht) | Owner + Stellvertretung (Pflicht) | A.5/A.10.2: der Prozesseigner erklärt persönlich |
| **Umsetzung** | Landes-Einheit (Pflicht) | — | gehört zum Prozess, nur die Abweichung ist lokal |
| **Tool-Objekt** | Einheit (Pflicht) | Technischer Owner + Stellvertretung | A.6/A.10.3: der Entwickler attestiert persönlich |
| **Datenobjekt** | **Fachbereich** (Pflicht, s. Abschnitt 7) | **keine** | A.7: eine Quelle gehört einer datenhaltenden Stelle |
| Bewertung, Selbstverpflichtung, Gate | erben vom Prozessobjekt | — | sind Zustände des Prozesses |
| Lenkungsvorgang | erbt vom Tool-Objekt | zugewiesen an | A.13.5: der Owner des Tools löst auf |
| Nachweis | keiner — unternehmensweit | — | ein Ausschnitt würde die Prüfung verhindern |

Ein Objekt **ohne** Anker gibt es nur in einem Zustand: importiert und
unbestätigt (Plattform hat es vorgefunden). Es ist dann ausschließlich den
globalen Rollen sichtbar; die Bestätigung verlangt die Zuordnung. Ein manuell
angelegtes Objekt ohne Anker gibt es nicht.

**Ein Anker wandert nicht.** Ein Tool-Objekt lässt sich nicht in einen
anderen Fachbereich übertragen, ein Datenobjekt ebenso wenig. Wer den Anker
ändern kann, ist ausschließlich die Governance — und der Nachweis hält es
fest. Der Grund: mit dem Anker wandern alle Berechtigungen, und eine
Fachbereichsrolle darf sich nicht selbst aus dem Bereich hinausbewegen.

---

## 5. Die Matrix: Rolle × Objekt × Aktion

Lesen: **S** = im eigenen Bereich, **R** = über eine Referenz (der Prozess
hängt an meinem Tool, das Datenobjekt an meinem Prozess), **G** = global,
**–** = nicht. Schreiben: **✓** = im eigenen Bereich, **G** = global, **–** =
nicht. „Eigener Bereich" heißt immer: der Anker des Objekts liegt im Scope
*dieser* Rolle.

### Prozessobjekt

| Aktion | P-Owner | P-Umsetzer | T-Owner | D-Owner | Governance | Plattform | Auditor | Admin |
|---|---|---|---|---|---|---|---|---|
| Liste, Detail lesen | S | S (als Umsetzer) | R (über sein Tool) | – | G | G | G | – |
| Anlegen | ✓ | – | – | – | G | – | – | – |
| Stammdaten, Status, Kanten | ✓ | – | – | – | G | – | – | – |
| Bewerten (A.8) | ✓ | – | – | – | G | – | – | – |
| Selbstverpflichtung Eigner (A.10.2) | ✓ | – | – | – | G | – | – | – |
| Gate einreichen | ✓ | – | – | – | G | – | – | – |
| Gate entscheiden | – | – | – | – | G | – | – | – |
| Umsetzung: lokale Abweichung | ✓ (jede Umsetzung seines Prozesses) | ✓ (nur sein Land) | – | – | G | – | – | – |

### Tool-Objekt

| Aktion | P-Owner | P-Umsetzer | T-Owner | D-Owner | Governance | Plattform | Auditor | Admin |
|---|---|---|---|---|---|---|---|---|
| Liste, Detail lesen | R (über seinen Prozess) | R | S | – | G | G | G | – |
| Anlegen | – | – | ✓ | – | G | – | – | – |
| Stammdaten, Technologie | – | – | ✓ | – | G | – | – | – |
| Einheit (Anker) ändern | – | – | – | – | G | – | – | – |
| Attestierungen (A.6) | – | – | ✓ | – | G | – | – | – |
| Prozess-/Datenkanten | ✓ (an seinem Prozess) | – | ✓ | – | G | – | – | – |
| Zustand melden (A.13.3) | – | – | ✓ | – | G | – | – | – |
| Kompensation (A.9.3) | – | – | ✓ | – | G | – | – | – |
| Selbstverpflichtung Owner (A.10.3) | – | – | ✓ | – | G | – | – | – |
| Importiertes bestätigen | – | – | ✓ | – | G | ✓ | – | – |
| Lenkungsvorgang auflösen | – | – | ✓ / zugewiesen | – | G | – | – | – |
| Lenkungsvorgang abbrechen | – | – | – | – | G | – | – | – |

Die Prozesskante steht in beiden Tabellen: sie hat zwei Enden, und wer eines
davon trägt, darf sie setzen. Das ist gewollt — A.4.4, n:m.

### Datenobjekt

| Aktion | P-Owner | P-Umsetzer | T-Owner | D-Owner | Governance | Plattform | Auditor | Admin |
|---|---|---|---|---|---|---|---|---|
| Katalog (Name, Fachbereich, Kategorie, Quellsystem) | alle Angemeldeten mit Rolle | | | | | | | – |
| Detail, Verwendung, Wirkung | R | R | R | S | G | G | G | – |
| Anlegen | ✓ (als Output seines Prozesses) | – | – | ✓ | G | Import | – | – |
| Name, Beschreibung, Quellsystem | ✓ (gebender Prozess) | – | – | ✓ | G | – | – | – |
| **Kategorie** | – | – | – | ✓ | G | – | – | – |
| Fachbereich (Anker) ändern | – | – | – | – | G | – | – | – |
| Als Input nutzen (Kante an eigenem Prozess) | ✓ | – | ✓ (an seinem Tool) | – | G | – | – | – |
| Importiertes bestätigen | – | – | – | ✓ | G | G | – | – |

### Regelwerk und Verwaltung

| Aktion | Fachrollen | Governance | Plattform | Auditor | Admin | ohne Rolle |
|---|---|---|---|---|---|---|
| Anforderungsklassen, Technologien, Matrix, Katalog SV, Gate-Auslöser, Einstellungen **lesen** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Fachbereiche, Einheiten **lesen** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Matrix, Klassen, Einstellungen **schreiben** | – | ✓ | – | – | – | – |
| Cockpit | im eigenen Bereich | ✓ | ✓ | ✓ | – | leer |
| Nachweis | – | ✓ | ✓ | ✓ | ✓ | – |
| Nutzerliste | – | ✓ | ✓ | ✓ | ✓ | – |
| Nutzer, Rollen vergeben | – | – | – | – | ✓ | – |
| Auswertungen (überfällig, Klassenbefund …) | im eigenen Bereich | ✓ | ✓ | ✓ | – | leer |

Das Regelwerk ist bewusst für jeden lesbar: wer bewertet wird, muss den
Maßstab lesen dürfen. Die Organisationsstruktur ebenso — sie ist Kontext,
nicht Gegenstand der Governance.

---

## 6. Personen in Dropdowns

Wo ein Formular eine Person verlangt (Owner, Stellvertretung, Technischer
Owner, Zuweisung), zeigt es **nur Personen, die für diesen Anker in Frage
kommen**: die Nutzer mit einer passenden Rolle im Bereich des Objekts. Ein
Prozess-Owner in Vertrieb sieht als Stellvertretung nur Prozess-Owner des
Vertriebs. Governance sieht alle.

Dafür gibt es `GET /personen?rolle=&fachbereich_id=` bzw.
`&organisationseinheit_id=`. Er liefert Kennung und Name, sonst nichts, und
fragen darf, wer die Rolle dort selbst trägt — „wer kann hier außer mir Owner
sein" ist eine Frage unter Zuständigen. Die Nutzerverwaltung
(`/admin/users`, mit E-Mail, Status, Führungskraft) bleibt den globalen Rollen
vorbehalten. Ein leeres Dropdown, weil die Nutzerliste 403 liefert, ist ein
Fehler — kein Hinweis auf fehlende Rechte.

Wo ein Formular einen **Bereich** verlangt (Fachbereich, Einheit), zeigt es
nur die Bereiche im Scope der handelnden Rolle:
`GET /organisationseinheiten?fuer_rolle=` bzw. `GET /fachbereiche?fuer_rolle=`.
Hat sie genau einen, ist er vorbelegt und gesperrt. Ohne `fuer_rolle` liefern
beide weiter die ganze Gliederung — sie ist Kontext und benennt Objekte in
Anzeigen (Abschnitt 5).

Daraus folgt eine Reihenfolge im Formular: **erst der Bereich, dann die
Personen.** Wer als Owner oder Vertretung in Frage kommt, hängt am Anker des
Objekts; solange der nicht steht, gibt es nichts zu wählen als sich selbst.

---

## 7. Datenobjekte — ausgearbeitet

Hier wich die Anwendung am weitesten ab, deshalb steht der Sollzustand
ausführlich.

### 7.1 Was ein Datenobjekt ist

Ein Datenobjekt ist eine **Quelle**: Personalstammdaten in SAP HCM, der
Artikelstamm, die Kassenbelege einer Filiale. Nicht ein Werkzeug, nicht ein
Werk. Es wird **einmal klassifiziert** und von beliebig vielen Prozessen und
Tools referenziert; die Klassifikation erbt sich (A.7, A.4.5). Deshalb hat es
weder einen persönlichen Owner noch eine Landesorganisation:

- **Keine Person.** Ein Prozess hat einen Eigner, weil eine Person die
  Bewertung verantwortet und die Selbstverpflichtung abgibt. Ein Tool hat
  einen Technischen Owner, weil eine Person attestiert. Ein Datenobjekt
  verlangt keine persönliche Erklärung — seine Kategorie ist eine Feststellung
  über die Daten, keine Zusage. Wer sie trifft, ist der Datenobjekt-Owner des
  Fachbereichs, und das ist eine Rolle, keine Eigenschaft des Objekts. Die
  Hilfe im Formular sagte es bereits richtig — „die datenhaltende Stelle" —
  und bot dann Personen an.
- **Keine Einheit.** Eine Quelle gehört einer datenhaltenden Stelle; die ist
  der Fachbereich. Landesorganisationen *nutzen* sie.

### 7.2 Der Anker: Fachbereich

`fachbereich_id` ist **Pflicht**. Es gibt zwei Wege, auf denen es gesetzt
wird — beide leiten ab, keiner fragt (P1):

1. **Aus dem gebenden Prozess.** Legt ein Prozess-Owner ein Datenobjekt als
   *Output* seines Prozesses an, ist der Fachbereich der des Prozessgebers.
   Der Prozess ist der **gebende Prozess** — er erzeugt die Daten, und wer ihn
   trägt, darf die Stammdaten der Quelle pflegen. Das ist die Zweckbindung
   aus A.4.6 in Reinform: die Quelle weiß, woher sie kommt.
2. **Aus dem Scope des Anlegenden.** Legt ein Datenobjekt-Owner eine Quelle
   ohne Prozess an (SAP-Stammdaten, ein Legacy-System), ist der Fachbereich
   sein Scope. Hat er genau einen, steht er fest.

Importierte Objekte (Plattform, B.3: jedes BigQuery-Dataset, jeder Bucket)
kommen ohne Fachbereich an, wenn die Quelle ihn nicht liefert. Sie sind
„vorgefunden", nur global sichtbar, und die **Bestätigung verlangt den
Fachbereich**. Governance oder Plattform ordnen zu; danach gilt Regel 7.3.

Der **gebende Prozess** ist kein eigenes Feld: er ergibt sich aus den
Output-Kanten. Hat ein Datenobjekt mehrere Prozesse als Output-Quelle, sind
alle gebend — jeder ihrer Owner darf die Stammdaten pflegen, denn jeder
verantwortet, was dort entsteht. Die Kategorie bleibt beim Datenobjekt-Owner.

### 7.3 Wer sieht ein Datenobjekt

- **Datenobjekt-Owner** des Fachbereichs: alle Datenobjekte seines
  Fachbereichs, vollständig.
- **Prozess-Owner, Prozess-Umsetzer, Technischer Owner:** jedes Datenobjekt,
  das an einem Prozess oder Tool hängt, das sie sehen dürfen — als Input oder
  Output. Vollständig, weil sie die Wirkung einer Kategorie auf ihr Objekt
  verstehen müssen. **Nicht** die übrigen Datenobjekte ihres Fachbereichs:
  ein Prozess-Owner im Vertrieb hat keinen Grund, die Kassenbelege zu sehen,
  wenn keiner seiner Prozesse sie nutzt.
- **Katalog:** Jeder Angemeldete mit einer Fachrolle sieht von **jedem
  bestätigten** Datenobjekt Name, Fachbereich, Kategorie und Quellsystem — die
  vier Felder der Stufe 1. Ohne diesen Katalog könnte ein Prozess-Owner im
  Vertrieb die Personalstammdaten nicht als Input wählen, und genau diese
  bereichsübergreifende Wiederverwendung ist der Sinn von A.7. Der Katalog
  ist eine bewusste, schmale Ausnahme von Abschnitt 1 Satz 1 — ein eigener
  Endpunkt mit eigenem Antwortschema, nicht die Detailantwort mit
  ausgeblendeten Feldern.
- **Globale Rollen:** alles. **Ohne Rolle:** nichts, auch nicht den Katalog.

### 7.4 Wer schreibt was

| Feld / Handlung | Datenobjekt-Owner (FB) | Prozess-Owner (gebender Prozess) | Governance | Plattform |
|---|---|---|---|---|
| Anlegen | ✓ im eigenen FB | ✓ als Output seines Prozesses | ✓ | Import |
| Name, Beschreibung, Quellsystem | ✓ | ✓ | ✓ | – |
| **Kategorie** | ✓ | – | ✓ | – |
| Fachbereich | – | – | ✓ | ✓ nur bei unbestätigten |
| Bestätigen (importiert) | ✓ | – | ✓ | ✓ |
| Input-Kante an einem Prozess | – | ✓ (jeder Prozess-Owner an seinem Prozess) | ✓ | – |

Die Kategorie ist das eine Feld, das den Fachbereich bindet: sie wirkt auf
jeden referenzierenden Prozess (A.7, „Tools erben"), und deshalb setzt sie
die Stelle, die die Daten hält — nicht die, die sie erzeugt oder nutzt. Die
Wirkungsvorschau vor dem Übernehmen bleibt.

Ein Datenobjekt, dessen Fachbereich keinen Datenobjekt-Owner hat, hat keinen,
der es klassifizieren darf. Das ist kein Fehler des Modells, sondern eine
Lücke in der Rollenvergabe — das Cockpit zeigt „Datenobjekte ohne Kategorie",
und die Governance kann übergangsweise selbst klassifizieren.

### 7.5 Was aus dem Formular verschwindet und was hinzukommt

- Weg: das Personen-Dropdown „Owner" und das Feld `owner_user_id`.
- Weg: das Fachbereich-Dropdown für Fachrollen. Der Fachbereich steht als
  Text; nur Governance bekommt eine Auswahl.
- Hinzu: „Gebender Prozess" — die Output-Prozesse als Verweise, abgeleitet.
- Hinzu: der Katalog-Endpunkt für die Input-Auswahl am Prozess.
- Die Anlage: aus dem Prozessformular heraus (als Output) oder aus der
  Datenobjektliste (Datenobjekt-Owner, Fachbereich vorbelegt).

---

## 8. Der Prüfstein

Für jede Route, jedes Formular und jedes Dropdown lassen sich vier Fragen
stellen. Bleibt eine ohne Antwort aus diesem Dokument, fehlt hier ein Satz —
nicht im Code.

1. Welcher Anker entscheidet? (Abschnitt 4)
2. Welche Rolle mit welchem Scope trifft diesen Anker? (Abschnitt 2, 5)
3. Steht die Regel genau einmal, im Dienst? (Abschnitt 1)
4. Bekommt der Anfragende weniger Daten — oder nur weniger Anzeige?

---

## 9. Abweichungen des heutigen Codes

Nummeriert, damit Änderungen und Entscheidungen darauf verweisen können.
Stand: 2026-09-03, nach E-54.

| Nr. | Abweichung | Wo | Soll |
|---|---|---|---|
| **R-1** | Datenobjekt hat `owner_user_id`; Formular bietet ein Dropdown mit **allen** Nutzernamen | Modell, `DatenobjektDetail`, `DatenobjektListe` | 7.1: kein persönlicher Owner; Feld entfällt |
| **R-2** | Wer sich selbst als Owner einträgt, darf jedes Datenobjekt anlegen und ändern — in jedem Fachbereich | `darf_datenobjekt_schreiben` | 7.4: Datenobjekt-Owner des FB, gebender Prozess-Owner, Governance |
| **R-3** | `fachbereich_id` ist optional; manuell angelegte Datenobjekte ohne Fachbereich sind möglich | Modell, Anlage | 7.2: Pflicht; ohne Anker nur importiert-unbestätigt |
| **R-4** | Fachrollen können den Fachbereich eines Datenobjekts frei wechseln (Dropdown mit allen) | `DatenobjektDetail` | 4: Anker wandert nur durch Governance |
| **R-5** | Prozess-Owner ändert Kategorie, wenn er zufällig Owner ist; Prozess-Owner des gebenden Prozesses darf **nichts** | `darf_datenobjekt_schreiben` | 7.4 |
| **R-6** | Sicht auf Datenobjekte ist bereichsweit für **jede** Rolle mit Scope im Fachbereich — auch Prozess-Umsetzer; kein Weg über Referenzen; kein Katalog | `datenobjekt_sichtbarkeitsbedingung`, `darf_datenobjekt_lesen` | 7.3 |
| **R-7** | Scopes zählen rollenblind: `scope_fachbereiche`, `erlaubte_org_ids` sammeln die Bereiche **aller** Rollen | `Principal`, `prozess.erlaubte_org_ids` | 2: ein Scope zählt nur für seine Rolle |
| **R-8** | Personen-Dropdowns laden `/admin/users`; für Fachrollen 403 → leer | `ProzessFormular`, `ToolDetail`, `ToolListe`, `DatenobjektListe`, `DatenobjektDetail` | 6: `/personen` mit Rolle und Bereich |
| **R-9** | Tool-Objekt: `organisationseinheit_id` optional; Fachrollen können sie frei wechseln | Modell, `ToolDetail` | 4: Pflicht außer importiert-unbestätigt; Wechsel nur Governance |
| **R-10** | Bereichs-Dropdowns (Fachbereich, Einheit) zeigen alle Bereiche | Formulare | 6: nur der eigene Scope, bei genau einem vorbelegt und gesperrt |
| **R-11** | Datenobjekt-Owner kann auf eine Einheit gescoped werden; die Schreibregel prüft dann nie positiv | Rollenvergabe, `darf_datenobjekt_schreiben` | 3: nur Fachbereich; die Vergabe lehnt Einheit ab |

**Stand nach AP-12 (E-55, E-56, E-57): keine offenen Punkte.** R-1 bis R-11
sind umgesetzt. R-7 zuletzt: es gibt keine Abfrage „alle meine Bereiche" mehr,
sondern nur `Principal.bereiche_fuer(rolle)`; die rollenblinden Eigenschaften
sind entfernt, damit niemand wieder danach greift.

Dabei kamen vier weitere Abweichungen ans Licht, die niemand gemeldet hatte —
sie standen so im Dokument, aber nicht im Code:

| Nr. | Abweichung | Aufgelöst |
|---|---|---|
| **R-12** | Der App-Administrator las bereichsübergreifend mit (`GLOBAL_LESEND`) | Er ist keine Fachrolle mehr; Nutzerliste und Nachweis bleiben ihm ausdrücklich |
| **R-13** | Der Prozess-Owner einer Kante durfte das Tool-Objekt vollständig schreiben — bis hin zur Attestierung | `darf_tool_schreiben` endet beim technischen Owner; für die Kante gibt es `darf_tool_verknuepfen` |
| **R-14** | Der Prozess-Owner durfte eine Umsetzung anlegen, ihre lokale Abweichung aber nicht ändern | Beide Wege prüfen jetzt dasselbe |
| **R-15** | Der App-Administrator durfte Assets importieren, entgegen dem eigenen Docstring | Import ausschließlich Plattform |
| **R-16** | Beim Anlegen eines Tool-Objekts entschied die **Nutzlast**: wer sich selbst als technischen Owner eintrug, erfüllte die Bedingung, die er gerade gesetzt hatte — jeder Angemeldete konnte anlegen, attestieren und an einen fremden Prozess hängen | Der Anker entscheidet: Einheit ist Pflicht, geprüft wird die Rolle dort (R-9 damit ebenfalls erledigt) |
| **R-17** | `NUR_LESEND` war unbenutzt — die Zusage „der Auditor ändert nichts" ruhte allein darauf, dass keine Regel ihn trifft | Zentral in `deps.py`: wer nur lesende Rollen trägt, kommt an keiner verändernden Methode vorbei |

Die Matrix aus Abschnitt 5 ist als ausführbare Tabelle hinterlegt:
`backend/tests/test_rollen_und_scopes.py` fährt **jede Zelle** an — 41
Handlungen mal 11 Zugänge — und prüft für jede einzeln, ob sie erlaubt oder
verweigert wird. Ein Recht, das nirgends verweigert wird, fällt dort auf.

**Eine Regel für jede Route, die anlegt.** Die Erlaubnis entscheidet der
**Anker**, nie die Nutzlast. Wer ein Objekt anlegt, gibt darin an, wem es
gehören soll — und diese Angabe darf niemals die Erlaubnis begründen, über die
sie entscheidet. Sonst erteilt sich jeder die Rechte selbst, indem er seinen
Namen einträgt. Deshalb steht in der Tabelle neben jeder Anlage auch die
Fassung mit **manipulierter** Nutzlast: die Matrix prüfte anfangs nur, was ein
Formular schickt, und übersah damit R-16.
