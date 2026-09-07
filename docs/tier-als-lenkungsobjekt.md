# Das Tier als Lenkungsobjekt, UR als komposite Ebene — Spezifikation

**Gegenstand:** Reichweite, Ausfallfolge und Kritikalität stehen als eigene Ebene neben der
Bewertung. Diese Spezifikation gliedert sie auseinander und führt sie dorthin zurück, wo sie
wirken: die erklärten Erwartungen in die UR-Achse, die Prozesskette an das Tier.

**Vorgesehen in:** AP-19 · **Vorgänge:** V-TIE-01 bis V-TIE-08 · **Stand der Belege:** `07a7c19`

---

## 1. Die Gliederung

Vier Ebenen, jede mit genau einer Aufgabe:

| Ebene | Inhalt | Herkunft |
|---|---|---|
| **Erklärte Erwartung** | Kundenkreis, Ausfallfolge | Der Prozess-Owner dokumentiert sie bei der Prozesserstellung. Es sind Sollzustände, keine Messwerte. |
| **Ableitung** | erlaubte Reichweite aus Kundenkreis und Umsetzungen | Rechnung über der Erwartung. Sie ist **Vorauswahl der Achse**, nicht deren Ursprung. |
| **Achse in der Bewertung** | UR als komposite Stufe aus erlaubter Reichweite **und** Ausfallfolge | Gerechnet, nicht erfragt. |
| **Tier** | zentrales Lenkungs- und Maßnahmenobjekt | Trägt die Auflagen und die Folgen. Die Prozesskette ist seine Bedingung. |

**Der Grundsatz dahinter:** Es gibt keine Ebene neben der Bewertung. Was governance-relevant und
berechenbar ist, ist Bestandteil der Fragen und Stufen — nicht ein Feld daneben, das dieselbe
Aussage ein zweites Mal trifft.

## 2. Warum überhaupt: der Bestand

**2.1 — Die Anwendung kennt die Antwort und fragt trotzdem.** `services/vorschlag.py:275-277`
sagt es selbst:

> „Als einzige Dimension ist diese **vollständig ableitbar**: die Ausfallfolge ist ein Pflichtfeld,
> und die Vererbung entlang der Kette ist gerechnet."

Und rechnet dann die Stufe aus, um sie als Vorschlag für drei Ja/Nein-Fragen zu verpacken
(`vorschlag.py:294-296`, Block 6 in `bewertungsbaum.py:166`). Das steht gegen P1: *„Was aus
vorhandenen Daten berechenbar ist, wird nie erfragt."* Eine Rechnung, die man überstimmen kann,
ist eine Meinung.

Bemerkenswert: AP-18 hat den Grundsatz bereits zum Titel gemacht — *„Nichts abfragen, was die
Anwendung weiß"* (E-64). An dieser Stelle ist er noch nicht eingelöst.

**2.2 — Die Kette rechnet, aber sie wirkt nicht.** `ableitung.aktualisiere_kette`
(`ableitung.py:164`) läuft transitiv über alle Vorgänger und **gibt die Betroffenenliste zurück**.
Der Rückgabewert wird nur zum Speichern der abgeleiteten Felder benutzt (`jobs.py:69`). Eine
Bewertung wird von einer Kettenänderung **nie** entwertet — der einzige Entwertungspfad ist
`gueltig_bis`, also Zeit.

Folge: Ein kritischer Nachfolger hebt die Kritikalität aller transitiven Vorgänger; deren
Bewertungen behalten ihre alte UR-Stufe, ihr Tier bleibt zu niedrig, still.

**2.3 — Das Tier kann nichts sagen, was das Profil nicht schon sagt.** `bewertung.py:105-110`:
`tier()` ist `max(Profilstufen)`. Der Docstring von `TIER_AUFLAGEN` (`bewertung.py:181-184`)
formuliert die Trennung bereits — die K-Klassen sagen, *was* der Prozess braucht, die Auflagen,
*wie streng* er geführt wird — aber sie ist folgenlos, solange das Tier nur ein Maximum ist.

**2.4 — Der Erlaubnisrahmen liest den lebenden Wert.** `rahmen.py:208-209` baut das Element
„Erlaubte Reichweite" aus dem abgeleiteten Feld, geerbt über `asset.erbe_klassifikation`
(`asset.py:111`). Eine zweite Umsetzung hebt die Reichweite (`ableitung.py:39-52`) — und der
Rahmen des Tools weitet sich von selbst, ohne Bewertung und ohne Gate 2. A.13.1 verlangt das
Gegenteil: *Prozessbewertung (Soll) ──► Erlaubnisrahmen.*

**2.5 — Die zweite Ebene ist auch sichtbar.** `ProzessDetail.tsx:252` zeigt die drei Größen als
eigene Karte „Abgeleitet", neben der Bewertung. Der Bewertungs-Wizard erwähnt sie kein einziges
Mal.

## 3. UR als komposite Ebene

### 3.1 Die beiden Anteile

Das unternehmerische Risiko ist keine einzelne Aussage. Es besteht aus **wie weit reicht der
Prozess** und **was passiert, wenn er ausfällt**. Keiner der beiden Werte trägt allein: Ein
kritischer Ausfall, der eine Person betrifft, ist kein Unternehmensrisiko; eine geringe Störung,
die das ganze Unternehmen trifft, kann eines sein.

| Anteil | Skala | Erklärt durch |
|---|---|---|
| **Erlaubte Reichweite** | persönlich (0) · Team (1) · Bereich (2) · Unternehmen (3) · extern (4) | Kundenkreis, angehoben durch mehr als eine Umsetzung (`ableitung.py:39-52`) |
| **Ausfallfolge** | keine (0) · gering (1) · spürbar (2) · kritisch (3) | Direkt erklärtes Pflichtfeld (`models/governance.py:104`) |

### 3.2 Die Kompositionstabelle — **zur Bestätigung**

UR-Stufe aus beiden Anteilen. Diese Belegung ist ein Vorschlag und der eine Punkt dieser
Spezifikation, der eine fachliche Entscheidung braucht:

| Ausfallfolge ↓ / Reichweite → | persönlich | Team | Bereich | Unternehmen | extern |
|---|---|---|---|---|---|
| **keine** | 0 | 0 | 0 | 0 | 1 |
| **gering** | 0 | 1 | 1 | 2 | 2 |
| **spürbar** | 1 | 1 | 2 | 3 | 3 |
| **kritisch** | 1 | 2 | 3 | 3 | 3 |

Die Tabelle ist gepflegte Konfiguration, keine Konstante — sie ist eine Bewertungsgrundlage, und
eine, die nur mit einer Auslieferung änderbar wäre, veraltet zwischen zwei Releases (analog E-42).

### 3.3 Was aus dem Fragebogen verschwindet

Block 6 (`bewertungsbaum.py:166` ff., Fragen 6a bis 6c) entfällt. An seine Stelle tritt in der
Bewertung eine **Ausgangslage**: beide erklärten Anteile, die daraus gerechnete Stufe und der
Satz, wie sie zustande kommt. Sichtbar, nachvollziehbar, nicht bedienbar.

Damit entfallen für UR auch `vorschlaege` und `abweichungen` — es gibt keine Abweichung mehr von
einer Rechnung. Wer die Stufe ändern will, ändert die Erwartung, und das ist protokolliert.

**Der Zielkonflikt, der dabei entsteht:** Kundenkreis und Ausfallfolge werden der einzige Hebel
auf UR. Wer ein niedrigeres Tier will, senkt sie. Heute ist die Baumfrage eine zweite, getrennt
zurechenbare Aussage. Abgemildert wird das durch die Protokollierung und dadurch, dass die Kette
nachrechnet — aufgehoben nicht. Das ist der Preis von P1 und wird als Entscheidung festgehalten,
nicht weggeredet.

## 4. Das Tier als Lenkungsobjekt

### 4.1 Die Rechnung

```
Tier = max(
    KI, DS, MB, IT, RG,        # das Profil
    min(UR, 2),                # eigenes Betriebsrisiko — gekappt (A.8.5, Schritt 6a)
    UR_kette,                   # aus der abhaengigen Prozesskette — ungekappt
)
```

`UR_kette` = die höchste UR-Stufe über alle **transitiven Nachfolger**. Die Richtung folgt A.4.2:
Wer einen kritischen Prozess beliefert, ist selbst kritisch. Die Mechanik existiert
(`ableitung.leite_kritikalitaet_ab`, `ableitung.kritikalitaetsquelle` in `ableitung.py:72`).

### 4.2 Warum die Kappung hier erstmals formulierbar wird

A.8.5 Schritt 6a verlangt: *„reines Betriebsrisiko hebt allein nicht in Tier 3."* Die Kappung
fehlt und ist im Test sogar festgeschrieben — `test_bewertung.py:109` prüft
`tier(stand) == max(1, max(kombination))`.

Erst durch die Trennung wird sie aussagbar: Das **eigene** Betriebsrisiko ist „rein" und kappt bei
Tier 2. Die **abhängige Kette** ist kein reines Betriebsrisiko, sondern Abhängigkeit — sie darf
auf Tier 3 heben. Beides steckt heute in derselben Zahl und lässt sich deshalb nicht
unterscheiden.

### 4.3 Was dem Profil folgt und was dem Tier

Sobald das Tier das Profil übersteigen kann, entkoppeln sich beide. Die Zuordnung folgt der
Trennung, die `TIER_AUFLAGEN` bereits beschreibt:

| | Hängt an | Begründung |
|---|---|---|
| **K-Klassen** (Maßnahmenklassen) | dem **Profil** | Ein Prozess, den die Kette hebt, braucht deswegen keine Folgenabschätzung — seine eigenen Eigenschaften haben sich nicht geändert |
| **Tier-Auflagen und Lenkung** | dem **Tier** | Er wird strenger geführt; genau das rechtfertigt die Kette |

### 4.4 Das Tier trägt seine Herkunft

Nicht nur die Zahl, sondern der Satz dazu: „Tier 3 — aus der Prozesskette, nicht aus dem eigenen
Profil; verantwortlich ist Prozess *X*." `ableitung.kritikalitaetsquelle` (`ableitung.py:72`)
liefert diesen Prozess bereits und kann die Begründung unverändert tragen.

## 5. Die Bewertung wird die einzige Quelle

Nachgelagerte Verwendungen lesen aus der gültigen Bewertung statt vom lebenden Prozessobjekt:

| Verwendung | Heute | Künftig |
|---|---|---|
| Erlaubnisrahmen, Element „Reichweite" (`rahmen.py:208`) | lebendes Feld über `erbe_klassifikation` | erlaubte Reichweite aus der Bewertung |
| Vererbung an das Tool-Objekt (`asset.py:111` ff.) | lebende Felder | Werte der gültigen Bewertung |
| Cockpit „Kritikalitätsketten" (`cockpit.py:246`) | lebende Kritikalität | Tier samt Herkunft |

**Ein Tool an einem Prozess ohne gültige Bewertung erbt dann nichts** — sein Rahmen deckt nichts.
Nach dem Positivlistenprinzip aus A.13.2 ist das richtig, aber es ist eine Verhaltensänderung und
wird als eigene Entscheidung festgehalten.

## 6. Der Auslöser

### 6.1 Warum er exakt sein kann

Weil UR gerechnet statt erfragt wird, kann die Anwendung selbst ausrechnen, ob eine Neubewertung
nötig ist. Unter dem heutigen Frage-mit-Vorschlag-Modell ginge das nicht — man müsste jemanden
fragen, um zu wissen, ob man ihn fragen muss.

### 6.2 Die Stufung

Bei jeder Änderung an Kundenkreis, Ausfallfolge, Umsetzungen oder Prozesskanten:

1. `aktualisiere_kette` liefert die Betroffenenliste — transitiv, zyklensicher, existiert.
2. Für jeden Betroffenen wird das Tier neu gerechnet.
3. **Ändert sich das Tier:** die gültige Bewertung ist überholt, Neubewertung fällig, Gate 2 nach
   A.11 (`REICHWEITENERWEITERUNG` beziehungsweise `KRITIKALITAET_GESTIEGEN`) wird **automatisch**
   eingereicht.
4. **Ändert sich das Tier nicht:** die Änderung wird sichtbar eingetragen und löst nichts aus.

Damit werden zwei der fünf Gate-2-Auslöser, die heute reine Selbstmeldung sind, automatisch
erkannt — und A.13.4 („automatisch und fortlaufend, kein Mensch im Regelbetrieb") gilt erstmals
auch für die Soll-Seite. AP-17 hat das für die Ist-Seite bereits geleistet (E-63); dies ist das
Gegenstück.

Punkt 4 ist nicht Bequemlichkeit, sondern P4: Agilität stirbt an Wartezeiten. Eine Kettenänderung
darf nur die Bewertungen entwerten, bei denen sich das Soll tatsächlich verschoben hat.

## 7. Abzuleitende Prüfungen

### 7.1 Die tragenden Prüfungen

| Prüfung | Erwartung |
|---|---|
| **UR ist nirgends erfragbar** | Kein Pfad — API, Wizard, Import — kann eine UR-Stufe setzen, die von der Rechnung abweicht |
| **Kappung** | Kein Profil hebt allein über das eigene Betriebsrisiko auf Tier 3, auch bei Reichweite „extern" und Ausfallfolge „kritisch" |
| **Kette hebt** | Ein Prozess mit leerem eigenen Profil, der einen UR-3-Prozess beliefert, erreicht Tier 3 |
| **Kette ist transitiv** | Auch der Vorgänger des Vorgängers wird gehoben; ein Zyklus terminiert |
| **Auslöser ist exakt** | Tier-Änderung ⟹ Bewertung überholt **und** Gate 2 eingereicht; keine Tier-Änderung ⟹ beides nicht |
| **Rahmen folgt der Bewertung** | Eine zweite Umsetzung weitet den Erlaubnisrahmen **nicht**, solange keine neue Bewertung vorliegt |
| **Kein Erbe ohne Bewertung** | Ein Tool an einem unbewerteten Prozess erbt nichts; sein Rahmen deckt nichts |
| **Kompositionstabelle** | Jede der 20 Kombinationen liefert die tabellierte Stufe; die Tabelle ist die Quelle, nicht der Code |
| **Herkunft** | Jedes Tier, das über das Profil hinausgeht, nennt den verantwortlichen Prozess |

`test_bewertung.py:109` muss dabei mitgezogen werden — er schreibt die fehlende Kappung heute fest
und würde die Korrektur sonst als Regression melden.

### 7.2 Abgrenzung

| Prüfung | Erwartung |
|---|---|
| K-Klassen folgen dem Profil | Ein von der Kette gehobener Prozess löst keine zusätzliche K-Klasse aus |
| Auflagen folgen dem Tier | Derselbe Prozess trägt die Auflagen seines gehobenen Tiers |

### 7.3 Anwendervorgänge

V-TIE-01 bis V-TIE-08 in `docs/vorgaenge.md`, hinterlegt in
`frontend/vorgaenge/tier.vorgang.ts`. Die tragenden sind **V-TIE-03** (von der gerechneten Stufe
lässt sich nicht abweichen — es gibt keinen Weg dorthin) und **V-TIE-05** bis **V-TIE-07** (die
Kette wirkt, und sie wirkt nur, wenn sich das Tier ändert).

## 8. Nachtrag am Leitdokument

Das Leitdokument liegt seit `cea90b2` im Repository. Diese Spezifikation ändert Fachlogik, die
dort steht; der Nachtrag ist Bestandteil des Arbeitspakets, nicht Nacharbeit.

| Abschnitt | Änderung |
|---|---|
| **A.8.2** | unverändert — es bleiben sechs Dimensionen; die Reichweite wird **keine** siebte Achse |
| **A.8.4** | UR: statt „Ausfallfolge + Kritikalität der Prozesskette" nun „erlaubte Reichweite + Ausfallfolge"; der Kettenanteil wandert zum Tier |
| **A.8.5** | Tier-Rechnung um die Kettenbedingung ergänzen; Schritt 6a als Kappung des **eigenen** Betriebsrisikos präzisieren |
| **A.13.2** | „Erlaubte Reichweite" bezieht ihr Soll aus der Bewertung, nicht aus dem lebenden Prozessobjekt |

## 9. Vorgeschlagene Entscheidungen

- **E-65 — UR wird gerechnet, nicht erfragt.** Block 6 entfällt; P1 gilt auch dort, wo es
  bequemer wäre zu fragen. Löst ein, was AP-18 (E-64) zum Titel gemacht hat.
- **E-66 — UR ist komposit aus erlaubter Reichweite und Ausfallfolge.** Keiner der beiden Werte
  trägt allein.
- **E-67 — Die Prozesskette ist eine Bedingung des Tiers, nicht der Dimension.** Nur so lassen
  sich eigenes Betriebsrisiko und Abhängigkeit unterscheiden — und nur so wird die Kappung aus
  A.8.5 formulierbar.
- **E-68 — K-Klassen folgen dem Profil, Auflagen folgen dem Tier.** Die Trennung stand schon im
  Docstring von `TIER_AUFLAGEN`; jetzt wird sie wirksam.
- **E-69 — Eine Kettenänderung entwertet nur bei Tier-Wirkung.** Sonst stirbt Agilität an
  Wartezeiten (P4).
- **E-70 — Ohne gültige Bewertung erbt ein Tool nichts.** Positivlistenprinzip statt stiller
  Restdeckung.
- **E-71 — Der einzige Hebel auf UR ist die erklärte Erwartung.** Bewusst in Kauf genommener
  Zielkonflikt zwischen P1 und Manipulationsfestigkeit, abgesichert über Protokoll und Kette.

## 10. Zuschnitt

1. Kompositionstabelle als gepflegte Stammdaten, UR-Rechnung, Block 6 raus
2. Tier-Rechnung mit Kappung, Kettenbedingung und Herkunft; `test_bewertung.py:109` mitziehen
3. Bewertung wird einzige Quelle: Rahmen, Vererbung, Cockpit lesen um
4. Auslöser: Betroffenenliste → Tier-Vergleich → Entwertung und Gate 2
5. Oberfläche: Ausgangslage statt Fragen, Tier mit Herkunftssatz, Karte „Abgeleitet" auflösen
6. Leitdokument-Nachtrag, Entscheidungen, Vorgänge scharf

Der Aufwand liegt in Schritt 3 und 4, nicht in 1 und 2: Die Rechnungen sind klein, das Umlesen der
nachgelagerten Verwendungen ist die eigentliche Arbeit — und der Auslöser ist der Teil, ohne den
Schritt 3 gefährlich wäre, weil er sonst echtes Risiko verstecken würde.
