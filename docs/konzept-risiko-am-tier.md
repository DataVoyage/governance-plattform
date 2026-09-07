# Warum das Risiko an das Tier gehört — das Konzept hinter AP-19

Dieses Dokument beschreibt die **Absicht**. Wie sie umgesetzt wurde, steht in
[`tier-als-lenkungsobjekt.md`](tier-als-lenkungsobjekt.md); die einzelnen
Festlegungen stehen als E-65 bis E-71 in [`entscheidungen.md`](entscheidungen.md).
Hier geht es um die Frage davor: **Welches Problem sollte die Umstellung lösen,
und woran erkennt man, dass sie es gelöst hat?**

---

## 1. Der Auslöser: eine zweite Ebene neben der Bewertung

Die Anwendung führte drei Größen, die niemand eingegeben hatte und die trotzdem
governance-relevant waren:

| Größe | Woraus sie entstand |
|---|---|
| **Reichweite** | Kundenkreis, angehoben durch mehrere Landesumsetzungen |
| **Kritikalität** | eigene Ausfallfolge, angehoben durch die Prozesskette (A.4.2) |
| **Mitbestimmungsflag** | Datenkategorien und Attestierungen |

Sie standen auf der Prozess-Detailseite in einer eigenen Karte mit der
Überschrift „Abgeleitet". Sie wirkten in die Bewertung hinein — aber nur als
**Vorschlag**: Die Anwendung rechnete die Stufe aus, verpackte sie als Antwort
auf eine Ja/Nein-Frage und ließ zu, dass jemand anders antwortete, sofern er
einen Satz dazuschrieb.

Damit gab es zwei Orte für dieselbe fachliche Aussage. Und das ist der Kern des
Problems: **Zwei Orte für eine Aussage driften auseinander, und der Ort, der
zählt, ist immer der andere.**

## 2. Was daran konkret schiefging

Die zweite Ebene war kein Schönheitsfehler. Sie hatte vier messbare Folgen.

### 2.1 Die Anwendung fragte, was sie wusste

Grundsatz P1 lautet: *„Was aus vorhandenen Daten berechenbar ist, wird **nie**
erfragt."* Der Vorschlagsdienst schrieb über das unternehmerische Risiko in
seinem eigenen Docstring:

> „Als einzige Dimension ist diese **vollständig ableitbar**: die Ausfallfolge
> ist ein Pflichtfeld, und die Vererbung entlang der Kette ist gerechnet."

Und stellte dann drei Fragen dazu. Wer ein niedrigeres Tier wollte, setzte sie
auf „nein" und begründete es — das Risiko verschwand aus der Bewertung, ohne
sich in der Wirklichkeit zu ändern. **Eine Rechnung, die man überstimmen kann,
ist keine Rechnung, sondern eine Meinung.**

### 2.2 Die Kette rechnete, aber sie wirkte nicht

Ändert jemand eine Prozesskante, läuft `aktualisiere_kette` transitiv über alle
Vorgänger und liefert die Liste der Betroffenen zurück. Benutzt wurde sie nur,
um abgeleitete Felder zu speichern. **Keine Bewertung wurde je entwertet.** Der
einzige Weg, auf dem eine Bewertung ungültig werden konnte, war Zeitablauf.

Ein kritischer Nachfolger hob damit die Kritikalität aller Vorgänger — während
deren Bewertungen ihr altes Tier behielten. Still.

### 2.3 Das Tier konnte nichts sagen

Das Tier war `max(Profilstufen)`. Ein Maximum kann nichts aussagen, was seine
Summanden nicht schon sagen. Der Docstring der Tier-Auflagen beschrieb seit
Langem eine Trennung —

> die K-Klassen sagen, **was** dieser Prozess wegen seiner Eigenschaften
> braucht, die Auflagen sagen, **wie streng** er insgesamt geführt wird

— aber sie war folgenlos. Und weil eigenes Betriebsrisiko und Kettenanteil in
derselben Zahl steckten, ließ sich die Kappung aus A.8.5 Schritt 6a („reines
Betriebsrisiko hebt allein nicht in Tier 3") gar nicht formulieren, ohne die
Kette mitzukappen. Sie fehlte deshalb — und ein Test schrieb ihr Fehlen sogar
fest.

### 2.4 Der Erlaubnisrahmen weitete sich von selbst

A.13.1 verlangt: *Prozessbewertung (Soll) ──► Erlaubnisrahmen.* Tatsächlich las
der Rahmen die **lebende** abgeleitete Reichweite. Legte jemand eine zweite
Landesumsetzung an, stieg sie über den Nachtlauf — und der Erlaubnisrahmen des
Tools wurde weiter. Ohne Bewertung, ohne Gate, ohne dass jemand es sah.

## 3. Der Grundsatz, an dem wir uns ausgerichtet haben

> **Die Bewertung ist der Dreh- und Angelpunkt des Prozesses. Es darf keine
> Ebene daneben geben.**

Daraus folgen zwei Präzisierungen, die das eigentliche Konzept ausmachen:

**Erstens: Abgeleitete Größen sind konstitutiv, nicht beratend.** Sie sind nicht
Kontext neben der Bewertung und auch nicht bloß mitzuspeichernde Begleitwerte —
sie bilden eigene Stufen ab und damit das Soll. Ein Vorschlag, den ein Mensch
bestätigt oder überstimmt, ist dafür zu schwach.

**Zweitens: Das Tier ist das zentrale Lenkungs- und Maßnahmenobjekt.** Es trägt
die Auflagen und die Folgen. Deshalb setzt auch die Berücksichtigung der
Prozesskette dort an und nicht an der einzelnen Dimension: **Die Kette ist eine
Bedingung des Tiers.**

## 4. Die Gliederung, die daraus entsteht

Vier Ebenen, jede mit genau einer Aufgabe — und keine davon doppelt:

```
  ERKLÄRTE ERWARTUNG          Kundenkreis · Ausfallfolge
  (Prozess-Owner)             Sollzustände, keine Messwerte
          │
          ▼
  ABLEITUNG                   erlaubte Reichweite
                              Rechnung über der Erwartung, ihre Normalform
          │
          ▼
  ACHSE IN DER BEWERTUNG      UR = f(Reichweite, Ausfallfolge)
                              gerechnet, nicht erfragt
          │
          ▼
  TIER                        max(Profil, min(UR,2), UR der Kette)
                              trägt Auflagen und Folgen
```

Zwei Entscheidungen darin verdienen eine eigene Begründung.

### 4.1 Warum UR komposit ist

Das unternehmerische Risiko ist keine einzelne Aussage. Es besteht aus **wie
weit reicht der Prozess** und **was passiert, wenn er ausfällt**. Keiner der
beiden Werte trägt allein:

- Ein **kritischer Ausfall, der eine Person betrifft**, ist kein
  Unternehmensrisiko.
- Eine **geringe Störung, die das ganze Unternehmen trifft**, kann eines sein.

Deshalb entsteht die Stufe aus einer Tabelle über beiden Anteilen, nicht aus
einer Zahl. Die Tabelle ist gepflegte Konfiguration — sie ist eine fachliche
Setzung und muss ohne Auslieferung korrigierbar sein.

Die Reichweite wird dabei ausdrücklich **keine siebte Dimension**. A.8.2 kennt
sechs, und eine siebte zu erfinden hätte genau die Drift erzeugt, die wir gerade
beseitigen wollten.

### 4.2 Warum die Kette am Tier ansetzt und nicht an der Dimension

Weil sich nur so zwei Dinge unterscheiden lassen, die verschieden sind:

| | Was es ist | Wie es wirkt |
|---|---|---|
| **Eigenes Betriebsrisiko** | „rein" im Sinne von A.8.5 | gekappt bei Tier 2 |
| **Abhängige Prozesskette** | Abhängigkeit, kein eigenes Risiko | ungekappt bis Tier 3 |

Wer einen kritischen Prozess beliefert, ist selbst kritisch (A.4.2) — aber er
ist es nicht *aus eigenem Betrieb*. Solange beides in derselben Zahl steckte,
war die Kappung unformulierbar. Getrennt ist sie beides: aussagbar und prüfbar.

Damit bekommt das Tier zum ersten Mal eine **eigene Stimme**. Es kann jetzt
etwas sagen, was das Profil nicht sagt — und muss deshalb auch sagen, woher es
kommt: `profil`, `ur` oder `kette`, im letzten Fall mit dem verantwortlichen
Prozess. Eine Zahl, die sich der Prozess-Owner nicht erklären kann, macht die
Auflage daneben willkürlich.

## 5. Was wir damit erreichen wollten — und woran man es prüft

| Ziel | Woran erkennbar |
|---|---|
| **P1 gilt auch dort, wo Fragen bequemer wären** | Der Bewertungsbaum hat keinen UR-Block mehr. Es gibt keinen Weg, die Stufe zu überstimmen — nur den, die Erwartung zu ändern, und die ist protokolliert |
| **Die Kappung aus A.8.5 wird wirksam** | Maximales eigenes Betriebsrisiko ergibt Tier 2, nicht 3 |
| **Die Kette wirkt sichtbar** | Ein Prozess mit leerem eigenen Profil, der einen kritischen beliefert, erreicht Tier 3 — und nennt den Prozess, der ihn dorthin bringt |
| **Der Erlaubnisrahmen folgt der Bewertung** | Eine zweite Umsetzung weitet ihn nicht mehr; sein Soll ist eingefroren |
| **Zwei Gate-2-Auslöser werden automatisch erkannt** | „Reichweitenerweiterung" und „Kritikalität gestiegen" waren reine Selbstmeldung. Jetzt rechnet die Anwendung nach — das Gegenstück zu E-63 auf der Soll-Seite |
| **Es gibt keine Ebene neben der Bewertung** | Die Karte „Abgeleitet" ist aufgelöst |

### 5.1 Der Nebeneffekt, der die Umstellung erst trägt

Weil UR gerechnet statt erfragt wird, kann die Anwendung **selbst ausrechnen,
ob eine Neubewertung nötig ist**. Sie nimmt die gespeicherten Antworten,
bestimmt die gerechneten Anteile neu und vergleicht das Tier.

Das war unter dem alten Modell unmöglich: Man hätte jemanden fragen müssen, um
zu wissen, ob man ihn fragen muss.

Daraus folgt die Stufung, die den Regelkreis erst benutzbar macht:

- **Tier verschiebt sich** → die Bewertung gilt als überholt, bei einem Anstieg
  wird Gate 2 automatisch eingereicht.
- **Tier bleibt** → die Änderung wird eingetragen und löst nichts aus.

Ohne diese Unterscheidung würde jede Kettenänderung dutzende Bewertungen auf
einmal entwerten. Agilität stirbt an Wartezeiten, nicht an Dokumentation (P4).

## 6. Was es kostet — offen benannt

Kein Konzept ohne Preis. Drei Punkte, die wir bewusst in Kauf genommen haben:

**Der einzige Hebel auf UR ist die erklärte Erwartung.** Wer ein niedrigeres
Tier will, senkt Kundenkreis oder Ausfallfolge. Vorher war die Baumfrage eine
zweite, getrennt zurechenbare Aussage; jetzt gibt es nur noch eine. Abgemildert
wird das dreifach — beide Felder sind kontrollierte Listen, jede Änderung steht
mit Person und Zeitpunkt im Nachweis, und die Kette rechnet nach, sodass niemand
dem Risiko seiner Nachfolger entkommt. Aufgehoben ist der Zielkonflikt nicht.

**Ohne gültige Bewertung erbt ein Tool nichts.** Das ist nach dem
Positivlistenprinzip richtig — was nicht bewertet ist, deckt nichts —, aber es
ist eine Verhaltensänderung und keine Nebenwirkung.

**Bestehende Bewertungen werden nicht rückwirkend neu gerechnet.** Eine
rückwirkend veränderte Bewertung wäre keine; A.13.7 verlangt eine lückenlose
Historie. Sie tragen deshalb keine eingefrorene Erwartung, und die neuen Fälle
werden erst nach einer Neubewertung sichtbar.

## 7. Was die Umstellung über das Modell verraten hat

Zwei Beobachtungen, die über AP-19 hinaus gelten.

**Die Fälle waren schon da.** Der Demobestand enthielt nach der Umstellung von
selbst acht Bewertungen mit Tier aus der Kette, drei mit gekapptem Eigenrisiko,
eine überholte und drei Prozesse ohne Bewertung, an denen Tools hängen — ohne
dass jemand sie dafür angelegt hätte. Sie fallen aus einem realistisch
modellierten Bestand an. Das ist ein besseres Argument für die Gliederung als
jede Konstruktion: Die Fälle sind nicht ausgedacht, sie kommen vor.

**Die Auflösung der zweiten Ebene war beim ersten Versuch zu weit gegriffen.**
Nachdem die Karte „Abgeleitet" verschwunden war, war die abgeleitete Reichweite
auf einem noch unbewerteten Prozess gar nicht mehr sichtbar. „Welchen Kreis
impliziert mein Kundenkreis?" ist aber eine berechtigte Frage *vor* der
Bewertung. Die Lösung war nicht, die Karte zurückzuholen, sondern die
abgeleitete Folge dorthin zu stellen, wo sie herkommt: **direkt an das Feld, aus
dem sie folgt.** Keine zweite Ebene — aber auch kein Loch.

Daraus wurde eine Regel, die über diesen Fall hinaus taugt: *Eine abgeleitete
Größe gehört an ihre Quelle, ihre Wirkung gehört in die Bewertung.*

## 8. Der Nachtrag am Leitdokument

Fachlogik, die sich ändert, muss im Leitdokument nachgezogen werden — im selben
Zug, nicht als Nacharbeit. Sonst entsteht mit offenen Augen genau die Drift,
gegen die diese ganze Umstellung gerichtet ist.

| Abschnitt | Was sich geändert hat |
|---|---|
| **A.8.2** | unverändert — es bleiben sechs Dimensionen |
| **A.8.4** | UR ist vollständig gerechnet, aus erlaubter Reichweite und Ausfallfolge; der Kettenanteil wandert zum Tier |
| **A.8.5** | Block 6 entfällt; die Tier-Formel nennt Profil, gekapptes Eigenrisiko und Kette; das Tier trägt seine Herkunft |
| **A.13.2** | „Erlaubte Reichweite" bezieht ihr Soll aus der gültigen Bewertung |
