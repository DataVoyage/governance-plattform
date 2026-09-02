# Governance by Design für Citizen Development und Custom Code

**Gesamtarchitektur · Stand: 01.09.2026**

---

## Lesehinweis: Aufbau dieses Dokuments

Das Dokument trennt bewusst zwei Ebenen, die unterschiedlichen Änderungsrhythmen und unterschiedlichen Lesern folgen:

| | **Teil A — Governance** | **Teil B — Technische Realisierung** | **Teil C — Gesamtarchitektur** |
|---|---|---|---|
| Beantwortet | *Was* wird verlangt, und *warum* | *Wie* wird das je Technologie erfüllt | Wie fügen sich A und B zu einem Gesamtbild |
| Technologiebezug | Keiner — gilt unverändert, auch wenn morgen eine vierte Technologie hinzukommt | Je Technologie ein eigener Abschnitt | Übergreifend |
| Ändert sich, wenn… | sich Risikobewertung, Rechtslage oder Organisationsprinzip ändert | ein Produkt neue Fähigkeiten bekommt oder eine neue Plattform hinzukommt | sich die Landschaft insgesamt verschiebt |
| Zielgruppe | Compliance, Betriebsrat, Governance, Prozesseigner | Plattform-Team, technische Owner, Entwickler | Alle — Einstiegspunkt |

**Warum diese Trennung:** Governance, die an ein Produktmerkmal gebunden ist, verfällt mit dem nächsten Produkt-Update. Umgekehrt macht eine rein abstrakte Governance ohne technische Übersetzung niemanden compliant. Teil A ist deshalb bewusst so geschrieben, dass er **kein einziges Mal** eine Produktentscheidung voraussetzt — er würde unverändert gelten, wenn Apps Script, Kubernetes oder BigQuery morgen durch etwas anderes ersetzt würden. Teil B ist die Übersetzung für den heutigen Stand.

---

# TEIL A — GOVERNANCE

*Fachlich, technologieneutral. Dieser Teil gilt unverändert für jede Technologie, mit der ein Prozess umgesetzt wird — heute Apps Script, Python/Kubernetes und GCP-Datendienste, morgen möglicherweise weitere.*

## A.1 Grundidee in einem Satz

> Nicht Anwendungen werden regiert, sondern **Prozesse**. Code-Assets hängen an Prozessen und erben deren Anforderungen. Die Technologie – Citizen Development, Custom Code oder Analytics – ist dabei unerheblich.

Daraus folgt unmittelbar: Es gibt keine Möglichkeit, durch Technologiewahl in eine günstigere Regulierung auszuweichen. Und es gibt keine Notwendigkeit, für jede Anwendung einzeln eine Compliance-Bewertung zu führen.

**Geltungsbereich dieses Dokuments:** Jede fachbereichsentwickelte Anwendung, unabhängig von Technologie und Ausführungsart — Apps Script und AppSheet in Google Workspace, jede lokal oder cloud-seitig laufende Python-Anwendung eines Fachbereichs (ob interaktiv gestartet oder unbeaufsichtigt/geplant laufend, ob heute als `.exe` verteilt oder nicht), sowie jede Nutzung des GCP-Datendienste-Stacks (BigQuery, Cloud Storage und angrenzende Dienste) durch Fachbereiche. Der Geltungsbereich ist bewusst nicht auf eine Technologie begrenzt — **eine Technologie ist der Anlass, nicht die Grenze** des Modells.

---

## A.2 Designprinzipien

Diese fünf Prinzipien entscheiden, ob das Modell im Betrieb überlebt. Jede Detailentscheidung — in diesem Dokument wie in jeder künftigen Erweiterung — wird an ihnen gemessen.

### P1 — Ableiten statt abfragen
Was aus vorhandenen Daten berechenbar ist, wird nie erfragt. Menschen deklarieren nur, was Maschinen nicht wissen können.

### P2 — Registrierung dort, wo der Wert entsteht
Governance-Objekte werden nicht in einem separaten Vorgang gepflegt, sondern entstehen als Nebenprodukt der eigentlichen Arbeit. Wer eine Datenverbindung anlegt, benennt dabei zwangsläufig, was er zieht – dieses Benennen *ist* die Registrierung.

### P3 — Das Register muss tragend sein
Ein Verzeichnis, das nur dokumentiert, verrottet innerhalb eines Jahres. Ein Verzeichnis, das Eingangstor für Provisionierung, Freigaben und Support ist, bleibt aktuell, weil man ohne es nicht weiterkommt.

### P4 — Gates zählen, nicht Artefakte
Agilität stirbt an Wartezeiten, nicht an Dokumentation. Fünf Register ohne Freigabeschritt sind harmlos; ein Register mit Pflichtprüfung ist ein Nadelöhr. Das Modell kennt daher **genau zwei** Gates (Abschnitt A.11).

### P5 — Referenzieren, nie duplizieren
Jede Angabe existiert an genau einer Stelle. Andere Objekte verweisen per ID. Doppelt geführte Angaben driften unweigerlich auseinander. Dieses Dokument selbst ist ein Anwendungsfall dieses Prinzips: Es ersetzt statt ergänzt.

---

## A.3 Das Objektmodell

Drei Objekttypen, klar getrennte Zuständigkeit, unterschiedliche Lebenszyklen.

```
   PROZESSOBJEKT  ────── definiert Rahmen ──────┐
   (SIPOC+)                                     │
   Owner: Fachbereich                           │
   Lebenszyklus: Jahre                          ▼
                                          muss hineinpassen
   TOOL-OBJEKT    ◄──── n:m ────────────────────┘
   Owner: technisch
   Lebenszyklus: Wochen
        │
        │ referenziert
        ▼
   DATENOBJEKT
   Owner: datenhaltende Stelle
   Lebenszyklus: Jahre
```

**Warum drei getrennte Objekte statt eines:**

| Grund | Erklärung |
|---|---|
| n:m-Beziehung | Ein Tool kann mehrere Prozesse bedienen, ein Prozess mehrere Tools nutzen. Das lässt sich nicht in ein Objekt pressen |
| Lebenszyklus-Entkopplung | Code ändert sich wöchentlich, Prozesse jährlich. Getrennte Objekte schützen die Prozessfreigabe vor Code-Churn |
| Vererbung der Klassifikation | Datenobjekte werden **einmal** klassifiziert; alle Tools, die sie anfassen, erben die Einstufung |

**Ein Tool-Objekt ist technologieunabhängig definiert:** ein Apps-Script-Projekt, ein Python-Deployment auf Kubernetes, eine BigQuery-View mit eigener Transformationslogik, ein AppSheet — jedes davon ist ein Tool-Objekt mit denselben n:m-Kanten zu Prozess- und Datenobjekten. Die Technologie ist ein Attribut des Tool-Objekts, keine eigene Objektklasse.

---

## A.4 Warum dieses Modell überlegen ist: Referenzierung, Graph und n:m

Dieser Abschnitt begründet, warum die drei Konstruktionsentscheidungen – Prozessbezug, SIPOC+ und referenzierte Datenobjekte – keine Modellierungsästhetik sind, sondern konkrete Fähigkeiten erzeugen, die anders nicht erreichbar wären.

### A.4.1 Warum überhaupt SIPOC — und nicht irgendein Prozessmodell

SIPOC ist unter den gängigen Prozessnotationen **die einzige, die von Haus aus Kanten modelliert statt Innenleben.**

| Notation | Modelliert | Für Governance |
|---|---|---|
| BPMN, EPK | Internen Ablauf, Verzweigungen, Rollen | Detailtief, aber ohne Anschluss an Daten und Nachbarprozesse |
| **SIPOC** | **Grenzen und Schnittstellen** | Genau das, was Governance braucht |

Die vier Randspalten sind bereits die Kanten des Graphen:

| SIPOC-Spalte | Wird zur Kante |
|---|---|
| **S**upplier | ← vorgelagerter Prozess |
| **I**nput | ← Datenobjekt (Lesekante) |
| **O**utput | → Datenobjekt (Schreibkante) |
| **C**ustomer | → nachgelagerter Prozess / Konsument |

Man bekommt vier Kantentypen ohne zusätzlichen Modellierungsaufwand. Ein Fachbereich, der ein SIPOC ausfüllt, baut den Governance-Graphen mit – ohne es zu merken und ohne dass es ihm als Governance-Arbeit erscheint.

Der zweite Vorteil ist die **erzwungene Flachheit**. SIPOC ist absichtlich grob. Wer Tiefe braucht, muss verlinken statt vertiefen. Damit wandert Komplexität systematisch in den Graphen – wo sie auswertbar ist – statt in Freitextfelder, wo sie es nie ist.

### A.4.2 Was die Verkettung leistet: Kritikalität wird berechnet, nicht erfragt

Kritikalität ist keine lokale Eigenschaft. Ein Prozess ist so kritisch wie sein kritischster Abnehmer – **transitiv über die gesamte Kette.**

```
Excel-Abzug ──► Aufbereitung ──► KPI-Report ──► Produktionsfreigabe
  (wirkt trivial)                                  (kritisch)
        └────────── erbt Kritikalität über 3 Kanten ──────────┘
```

Ohne Graph ist diese Aussage **prinzipiell nicht erreichbar**: Der Besitzer des Excel-Abzugs weiß nicht, dass drei Stationen später eine Produktionsfreigabe daran hängt. Jede Befragung würde „unkritisch" ergeben. Nur die transitive Auswertung liefert die richtige Antwort.

**Das löst zugleich die Reifegrenze.** Gewinnt ein Prozess einen neuen Abnehmer, steigt die Einstufung aller vorgelagerten Prozesse automatisch. Niemand muss melden, dass sein Tool wichtig geworden ist – die Kante erzeugt die Meldung.

### A.4.3 Wirkungsanalyse in beide Richtungen

Derselbe Graph, zwei Richtungen, zwei Fragen, die heute nur durch Rundmails beantwortbar sind:

| Richtung | Frage | Antwort |
|---|---|---|
| Abwärts | „Wenn dieser Prozess drei Tage ausfällt – was steht still?" | Alle erreichbaren Nachfolgeknoten |
| Aufwärts | „Wir ändern die Struktur dieses SAP-Reports – wer ist betroffen?" | Alle Vorgängerknoten mit Lesekante auf dieses Datenobjekt |

Damit wird aus einer organisatorischen Suchaufgabe eine Abfrage. Das ist der Unterschied zwischen „wir fragen mal rum" und „wir wissen es".

### A.4.4 Was n:m leistet — und warum 1:n hier falsch wäre

Ein Tool kann mehrere Prozesse bedienen; ein Prozess nutzt mehrere Tools. Erzwänge man 1:n, blieben nur zwei Auswege, beide schädlich:

| Notlösung | Folge |
|---|---|
| Tool je Prozess duplizieren | Fünffache Pflege, garantierte Drift zwischen den Kopien |
| Tool willkürlich einem Prozess zuordnen | Für die vier anderen Prozesse gilt die falsche Klassifikation |

**Mit n:m entstehen dagegen drei Fähigkeiten:**

1. **Automatische Maximum-Vererbung.** Ein Tool trägt die höchste Klassifikation aller Prozesse, denen es dient. Ein Skript, das vier harmlose Reports und einen HR-Prozess bedient, ist ein HR-Tool – automatisch, ohne dass jemand die Verbindung ziehen muss.

2. **Geteilte Assets werden als Risikoherd sichtbar.** Ein Tool mit fünf Prozesskanten ist kein fünffaches Risiko, sondern ein **anderes** Risiko: Single Point of Failure mit einem Scope-Bedarf, der die Vereinigungsmenge aller Anforderungen ist. Diese Objekte sind die eigentlichen Kandidaten für Härtung – und sie sind ohne n:m schlicht nicht identifizierbar.

3. **Umgehung wird erkennbar.** Wer ein Tool in drei kleine aufteilt, um in Tier 1 zu bleiben, erzeugt drei Knoten mit Kanten auf denselben Prozess und dieselben Datenobjekte. Die Aggregation ist sichtbar. Ebenso eine Kette aus Tier-1-Tools, die zusammen eine Tier-3-Wirkung erzeugt – sie erscheint als Pfad, nicht als Einzelfall.

### A.4.5 Was Referenzierung leistet: der Pflegeaufwand kollabiert

Der Unterschied zwischen Freitext und ID ist der Unterschied zwischen linearem und konstantem Änderungsaufwand.

| | Freitext („SAP-Daten") | Referenz (ID auf Datenobjekt) |
|---|---|---|
| Umklassifizierung einer Quelle | Jeden betroffenen Datensatz einzeln finden und ändern | **Eine** Änderung am Datenobjekt |
| Wirkung | Manuelle Nacherfassung, unvollständig | Alle referenzierenden Prozesse und Tools re-tiern sofort |
| Konsistenz | Divergiert mit der Zeit | Strukturell garantiert |

**Konkretes Beispiel:** HR stuft „Entgeltdaten" von Kategorie 4 auf 5 hoch. Bei Freitextpflege ist das eine organisationsweite Nacherfassung mit ungewissem Ergebnis. Mit Referenzen ist es ein Feld – und jeder betroffene Prozess wechselt automatisch in Tier 3, inklusive Auslösung von Gate 2 bei den betroffenen Tools.

**Der Skalierungseffekt derselben Logik:**

| Klassifiziert wird… | Menge | Wächst mit |
|---|---|---|
| jedes Tool | 13.000+ Apps-Script-Projekte, plus wachsender Python- und BigQuery-Bestand | Jedem neuen Skript, jeder neuen App, jedem neuen Dataset |
| jede Datenquelle | endlich, stabil | Neuen Systemen, selten |

Das ist der Grund, warum das Modell überhaupt tragfähig ist — gerade weil der Geltungsbereich jetzt drei Technologien statt einer umfasst: Es macht die Klassifikationsarbeit **endlich**, unabhängig davon, wie viele Technologien darunter hängen.

### A.4.6 Der Vorteil, der Compliance am meisten wert ist: Zweckbindung wird prüfbar

Datenschutzrechtlich zählt nicht, worauf ein Tool zugreifen *könnte*, sondern zu welchem **Zweck** es Daten tatsächlich verarbeitet. Genau diese Unterscheidung ist ohne Graph nicht darstellbar:

| Ohne Graph | Mit Graph |
|---|---|
| „Skript/App hat Vollzugriff" | „Tool liest Datenobjekt D im Rahmen von Prozess P" |
| Bewertung der theoretischen Fähigkeit | Bewertung der tatsächlichen Verarbeitung mit Zweck |
| Jede App einzeln zu bewerten | Zweck einmal je Prozess bewertet |

Damit wird Zweckbindung zu einer **prüfbaren Bedingung**: Verwendet ein Tool ein Datenobjekt, dessen Kategorie der zugeordnete Prozess nicht abdeckt, ist das eine erkennbare Abweichung – nicht ein Befund, den erst jemand entdecken muss.

Für den Betriebsrat entsteht daraus die entscheidende Vereinfachung: Bewertet wird ein Prozess mit definiertem Zweck, Datenfluss und Empfängerkreis – nicht eine Anwendung mit unbestimmtem Potenzial. Die Bewertung gilt anschließend für alle vorhandenen **und künftigen** Assets desselben Prozesses, unabhängig davon, mit welcher Technologie sie umgesetzt werden.

### A.4.7 Weitere Fähigkeiten, die erst durch die Struktur entstehen

| Fähigkeit | Mechanismus |
|---|---|
| **Verwaistenerkennung** | Knoten ohne Owner-Kante oder ohne Pfad zu einem Prozess – Mengenoperation statt Sichtung |
| **Simulation vor Entscheidung** | „Was passiert, wenn Datenobjekt D höher eingestuft wird?" ist eine Abfrage, keine Studie |
| **Technologie-Unabhängigkeit** | Migriert ein Tool auf eine andere Plattform — etwa von lokalem `.exe` auf den Kubernetes-Golden-Path —, ändert sich ein Knoten. Prozess- und Datenkanten bleiben – die Governance-Historie überlebt die Plattformentscheidung |
| **Priorisierung nach Wirkung** | Härtungsaufwand fließt dorthin, wo der Blast Radius groß ist, nicht dorthin, wo jemand laut ruft |

### A.4.8 Zusammenfassung der Wirkungslogik

| Konstruktionsentscheidung | Erzeugte Fähigkeit |
|---|---|
| Prozess als Governance-Objekt | Technologieneutralität; Bewertungseinheit, die Code-Änderungen und Plattformwechsel überlebt |
| SIPOC statt Ablaufmodell | Kanten ohne Zusatzaufwand; erzwungene Flachheit |
| Verkettung der Prozesse | Kritikalität transitiv berechenbar; Reifegrenze löst sich selbst |
| n:m Tool ↔ Prozess | Maximum-Vererbung; geteilte Assets sichtbar; Umgehung erkennbar |
| Referenzierte Datenobjekte | Pflegeaufwand konstant statt linear; Klassifikation endlich |
| Kategorie an der Quelle | Semantik dort, wo sie stabil ist – nicht dort, wo sie churnt |

---

## A.5 Prozessobjekt (SIPOC+)

### Deklarierte Felder — das ist alles

| # | Feld | Anmerkung |
|---|---|---|
| 1 | Prozessname | |
| 2 | Owner (Fachbereich) | Person, nicht Abteilung |
| 3 | Stellvertretung | **Pflicht** – ohne sie stirbt das Objekt beim nächsten Personalwechsel |
| 4 | Supplier | Wer liefert zu |
| 5 | Input | Referenzen auf Datenobjekte (IDs), kein Freitext |
| 6 | Process | 5–7 Schritte, Stichworte |
| 7 | Output | Was entsteht |
| 8 | Customer | Wer konsumiert – Auswahl, kein Freitext |
| 9 | Vorgelagerte / nachgelagerte Prozesse | Verkettung |
| 10 | Ausfallfolge | „Was passiert, wenn das 3 Tage steht?" – in Worten |

Zehn Felder. Alles andere wird berechnet. Diese Erfassung ist **bereits heute Standardprozess** und gilt unverändert für Tool-Objekte jeder Technologie.

### Abgeleitete Felder — Berechnungsvorschrift

| Feld | Ableitung |
|---|---|
| **Reichweite** | Aus Customer: `Einzelperson < Team < Abteilung < Unternehmen < extern` |
| **Datenklassifikation** | Höchste Kategorie aller referenzierten Datenobjekte |
| **Kritikalität** | `max(eigene Ausfallfolge, Kritikalität aller nachgelagerten Prozesse)` |
| **Mitbestimmungsflag** | Personenbezug **und** (Wirkung auf einzelne Person **oder** Leistungs-/Verhaltensdaten) |
| **Tier** | Siehe Abschnitt A.8 |

**Der wichtigste Ableitungseffekt:** Kritikalität propagiert entlang der Prozesskette. Ein unscheinbarer Prozess, der einen kritischen beliefert, ist selbst kritisch – **automatisch**, ohne dass jemand es meldet. Damit löst sich die Reifegrenze: Bekommt ein Prozess einen neuen Abnehmer, steigt seine Einstufung ohne Zutun.

### Granularitätsregel

> Die richtige Flughöhe ist die **kleinste Einheit, die einen Owner und eine Compliance-Antwort hat.**

Zwei operative Tests:

- **Teilungstest:** Unterschiedliche Owner, unterschiedlicher Personenbezug oder unterschiedliche Abnehmer? → trennen
- **Zusammenlegungstest:** Würde eine Trennung keine Governance-Antwort verändern? → zusammenlegen

**Strukturelle Bremsen gegen Detailtiefe:**

1. Keine Freitextfelder außer den vorgesehenen; harte Zeichenbegrenzung
2. Mehr als 7 Schritte in der P-Spalte = falsche Flughöhe (Systemwarnung)
3. Drei gut geschnittene Referenzbeispiele statt Regelwerk – Regeln werden ausgelegt, Beispiele nachgeahmt
4. Flughöhen-Review nur für die ersten 20–30 Objekte, danach reguliert der Referenzkorpus
5. **Bei Detailbedarf lautet die Antwort immer: „verlinke einen weiteren Prozess"** – die Tiefe liegt im Graphen, nicht im Datensatz

---

## A.6 Tool-Objekt

### Grundsatz: maschinell befüllt, menschlich bestätigt

Auf Prozessebene deklariert ein Mensch den Soll-Zustand. Auf Tool-Ebene wäre das ein Fehler – den Ist-Zustand kennt das System bereits, sofern die Telemetrie an das Tool-Objekt angebunden ist (siehe A.12).

| Feld | Herkunft |
|---|---|
| Zugeordnete Prozesse (n:m) | **Deklariert** – die eine Sache, die nur ein Mensch weiß |
| Technischer Owner | **Deklariert** |
| Technologie | **Deklariert bzw. aus Provisionierung** — Apps Script, Python/Kubernetes, BigQuery/GCS, AppSheet |
| Genutzte Datenobjekte | Telemetrie (APIs, Endpunkte, Datenzugriffe) |
| Zugriffsberechtigungen (Scopes, IAM-Bindings) | Telemetrie |
| Lese- / Schreibzugriff | Telemetrie |
| Externe Ziele | Telemetrie (URL-Logs, Egress-Logs) |
| Lauftyp: interaktiv / getriggert / unbeaufsichtigt-geplant | Telemetrie |
| Reichweite des Deployments | Telemetrie |
| Letzte Ausführung, Frequenz | Telemetrie |

### Die drei Attestierungen

Was Telemetrie **nicht** liefern kann und daher verbindlich erklärt werden muss – mit Namen, nicht als Formularfeld:

1. **Fließt das Ergebnis in eine Entscheidung über einzelne Personen?**
2. **Steht zwischen Output und Wirkung ein Mensch?**
3. **Werden Datenkategorien verarbeitet, die nicht aus klassifizierten Quellen stammen** (Uploads, manuelle Eingaben, Zwischenablagen)?

Frage 3 ist die wichtigste – sie fängt genau die Lücke, die das Datenobjekt-Modell strukturell nicht schließen kann.

### „Verändert" vs. „gestaltet"

Teilweise ableitbar, teilweise nicht – die Kombination reicht für belastbare Triage:

| Signal | Quelle | Aussage |
|---|---|---|
| Nur lesende Berechtigungen | Telemetrie | Kann den Prozessausgang nicht direkt verändern → **gestaltend** |
| Schreibzugriff auf System of Record | Telemetrie | **Verändernd**, immer prüfpflichtig |
| Kein Mensch zwischen Output und Wirkung | Attestierung 2 | **Verändernd**, auch bei reinem Lesen |

> ⚠️ Ein rein lesendes Tool, dessen Auswertung automatisiert eine Entscheidung über Personen auslöst, ist verändernd. Das sieht man an keiner Berechtigung – deshalb ist Attestierung 2 nicht verzichtbar.

### Ausführungsart als Zusatzsignal, nicht als eigene Tier-Achse

Ob ein Tool interaktiv auf Anstoß eines Menschen oder unbeaufsichtigt/geplant läuft (Cronjob, Scheduler, CronJob-Ressource), wird als Telemetriefeld erfasst und steuert, wo relevant, **technische Entscheidungen** — etwa welches Kubernetes-Primitiv ein Python-Workload realisiert (B.2). Es fließt **nicht** als eigene, gleichrangige Dimension in die Tier-Berechnung ein (dafür siehe A.8), sondern wirkt dort ausschließlich als Korrekturfaktor bei Grenzfällen: Ein unbeaufsichtigt laufendes Tool mit ansonsten niedrigem Profil kann bei der Einzelfallprüfung in Gate 1 zur Kenntnis genommen werden, löst aber keinen automatischen Tier-Aufstieg aus.

---

## A.7 Datenobjekt und progressive Formalisierung

### Der Kerngedanke

Nicht Tools klassifizieren, sondern **Quellen**. Tools erben.

| Ansatz | Menge | Pflegeaufwand |
|---|---|---|
| Pro Tool klassifizieren | Zehntausende, wachsend | Unbeherrschbar |
| Datenquellen klassifizieren | Endliche Menge | Einmalig, dann stabil |

### Drei Reifegrade

| Stufe | Inhalt | Aufwand | Wann verlangt |
|---|---|---|---|
| **1 — Datenobjekt** | Name, Kategorie, Owner, Quellsystem | ~30 Sekunden | Immer |
| **2 — Datenprodukt** | + Schema, Feldebene | Stunden | Sobald geteilt genutzt |
| **3 — ODCS-Kontrakt** | + Qualität, SLA, Konsumenten, Feldklassifikation | Tage | Nur bei echten Produkten mit Abnehmern |

**Entscheidend: Die Compliance-Funktion ist bereits auf Stufe 1 erfüllt.** Für die Frage „ist das personenbezogen" braucht es eine Kategorie, keinen Kontrakt. Stufe 3 ist ein Upgrade, keine Eintrittshürde.

**Anbindung an den GCP-Datendienste-Stack (Details in B.3):** Jedes neu angelegte BigQuery-Dataset und jeder neue Cloud-Storage-Bucket erzeugt automatisch ein Datenobjekt der Stufe 1 als Nebenprodukt der Provisionierung selbst — Prinzip P2 in technischer Reinform. Eine Formalisierung auf Stufe 2 oder 3 bleibt optional und dem tatsächlichen Bedarf überlassen.

### Kategorien

Unter sieben halten, sonst wird falsch geklickt:

1. Öffentlich
2. Intern – geschäftlich, kein Personenbezug
3. Intern – vertraulich (Geschäftsgeheimnis, Finanzen)
4. Personenbezogen – allgemein (Kontakt, Organisation)
5. Personenbezogen – besonders (Entgelt, Gesundheit, Leistungsbewertung)

> **Mitbestimmungsrelevanz ist keine Kategorie, sondern ein abgeleitetes Flag.** Sie kann bei jeder Datenkategorie auftreten, weil sie am Verwendungszweck hängt, nicht an der Datenart. In die Kategorienliste gepresst erzeugt sie systematisch falsche Einordnungen.

### ODCS als Zielzustand der oberen Stufe

Der Open Data Contract Standard (Bitol / Linux Foundation, aktuell v3.1.0) passt aus vier Gründen:

- **YAML in Git** → läuft durch die bestehende Azure-DevOps-Pipeline, kein neues System
- **Klassifikation auf Feldebene** → genau die Auflösung für „Gehaltsliste vs. Adresse"
- **Owner/Stakeholder im Standard enthalten** → passt auf das Owner-Konzept
- **Custom Properties** → eigene Governance-Attribute anhängbar, ohne den Standard zu verbiegen

Für eine Produktebene über mehreren Kontrakten existiert ergänzend ODPS.

### Abhängigkeit, die benannt werden muss

Solange SQVI und SE16 der De-facto-Datenzugang sind, **gibt es kein klassifizierbares Datenobjekt** – jede Abfrage ist ad hoc, nichts ist vererbbar. Der flächige SAP-Datenzugang ist damit keine Effizienzmaßnahme, sondern **Voraussetzung dieser Compliance-Architektur**.

---

## A.8 Bewertungsmodell: der Sollzustand aus dem Prozess

### A.8.1 Grundsatz: bewertet wird der Prozess, nicht das Werkzeug

> Die Bewertung erfolgt **bevor und unabhängig davon**, mit welcher Technologie der Prozess umgesetzt wird.

Ob Apps Script, AppSheet, eine Python-Anwendung auf dem Kubernetes-Golden-Path oder eine BigQuery-Auswertung — für den Sollzustand ist das ohne Belang. Die Technologie bestimmt nicht, welcher Schutzbedarf besteht; sie muss ihn erfüllen. Was eine Technologie *kann*, ist keine Rechtfertigung dafür, was ein Prozess *braucht*.

Daraus folgt die zentrale Regel dieses Modells:

> **Kann eine Technologie eine abgeleitete Anforderung nicht erfüllen, ist das ein Befund — keine Ausnahme.** Die Konsequenz ist ein Technologiewechsel, keine Absenkung der Anforderung.

Diese Prüfung — Datenklassen durch Mapping auf den Prozess, daraus die erlaubten Tiers — ist der **bereits heute etablierte Standardprozess**. Was in diesem Abschnitt neu ist, ist ausschließlich die Präzisierung, *wie* die vier Dimensionen zum Tier zusammengeführt werden (A.8.5) — nicht die Dimensionen selbst und nicht der Umstand, dass sie am Prozess hängen.

### A.8.2 Die Risikodimensionen

Ein einzelner Risikowert bildet die tatsächliche Bandbreite dessen, was der Einsatz eines Tools im Unternehmen auslösen kann, nicht ab. Der Sollzustand ist deshalb ein **Profil** aus sechs Dimensionen:

| | Dimension | Leitfrage |
|---|---|---|
| **KI** | KI-Einsatz (EU AI Act) | Wird KI eingesetzt — und wenn ja, in welche Risikokategorie fällt der Einsatz nach EU AI Act? |
| **DS** | Datenschutz | Welche Personendaten, welcher Betroffenenkreis, welche Empfänger? |
| **MB** | Arbeitsrecht / Mitbestimmung | Kann das Ergebnis Leistung oder Verhalten einzelner Beschäftigter sichtbar machen, bewerten oder beeinflussen? |
| **IT** | IT-Sicherheit | Verwaltet oder nutzt die Anwendung sicherheitskritische Berechtigungen/Zugangsdaten? Wie groß ist die Angriffsfläche? |
| **RG** | Regulatorik / Nachweispflicht | Unterliegt Ergebnis oder Verarbeitung einer Aufbewahrungs-, Nachweis- oder Prüfpflicht? |
| **UR** | Unternehmerisches Risiko | Welcher Schaden entsteht bei Fehler, Ausfall, Manipulation oder Abfluss? |

**Warum IT-Sicherheit und Regulatorik getrennte Dimensionen sind:** Eine Anwendung kann hochgradig nachweispflichtig sein, ohne selbst ein IT-Sicherheitsrisiko zu sein (ein rein lesender Bericht für die Steuerprüfung), und umgekehrt ein erhebliches IT-Sicherheitsrisiko sein, ohne irgendeiner Nachweispflicht zu unterliegen (ein internes Tool mit privilegiertem Service-Account, das nichts Dokumentationspflichtiges verarbeitet). Beide Fälle brauchen unterschiedliche Auflagen.

**Warum KI/EU AI Act als eigene Dimension:** Der EU AI Act löst seit 2024 eine eigenständige, gestaffelte Rechtsfolge aus (verbotene Praktiken, Hochrisiko-Systeme, Transparenzpflichten, Minimalrisiko) — eine Systematik, die weder in Datenschutz noch in klassische Regulatorik vollständig hineinpasst. Ein Tool kann KI-rechtlich hochriskant sein, ohne besonders datenschutz- oder nachweispflichtig zu sein, und umgekehrt.

**Warum ein Entscheidungsbaum statt einer Gewichtungsformel:** Sechs Dimensionen über eine Formel mit Gewichtsklassen zu einem Tier zu kombinieren, ist in der Praxis zu abstrakt für die Gestaltung — sechs Werte gleichzeitig zu würdigen und rechnerisch zusammenzuführen ist kein Werkzeug, das jemand ohne Vorbereitung anwenden kann. Die Schwere-Reihenfolge der sechs Dimensionen wird deshalb **nicht rechnerisch, sondern als Ablauf** dargestellt — siehe A.8.5, der Entscheidungsbaum. Das Profil aus sechs Werten bleibt für die K-Klassen-Ableitung (A.9) erhalten, entsteht aber als Nebenprodukt des Baum-Durchlaufs statt als separate Bewertungssitzung.

### A.8.3 Bewertungsanker je Stufe

Jede Dimension wird auf 0–3 bewertet (KI zusätzlich mit einer Stufe „verboten" unterhalb von 0). Die Anker machen die Einstufung reproduzierbar statt ermessensabhängig und sind die Grundlage der Fragen im Entscheidungsbaum (A.8.5).

**KI — KI-Einsatz (EU AI Act)**

| Stufe | Anker |
|---|---|
| *verboten* | Praxis nach Art. 5 (z. B. Social Scoring von Personen, manipulative/täuschende Beeinflussung mit Schädigungspotenzial, unautorisierte Emotionserkennung am Arbeitsplatz, biometrische Kategorisierung nach sensiblen Merkmalen) → **kein Tier, Einsatz nicht zulässig** |
| 0 | Kein KI-/ML-Einsatz, auch nicht als Komponente (eingebettetes Modell, externe KI-API) |
| 1 | KI-Einsatz mit minimalem Risiko (z. B. Spamfilter, nicht-personenbezogene Priorisierung) |
| 2 | Transparenzpflichtig nach Art. 50 (z. B. Chatbot, Erzeugung synthetischer Inhalte, zulässige Emotionserkennung) |
| 3 | Hochrisiko-System nach Anhang III (u. a. Beschäftigung/Personalauswahl, Bewertung natürlicher Personen, Zugang zu wesentlichen Dienstleistungen) |

**DS — Datenschutz**

| Stufe | Anker |
|---|---|
| 0 | Keine personenbezogenen Daten |
| 1 | Geschäftskontaktdaten, interner Empfängerkreis |
| 2 | Personenbezogene Daten über den Kontaktrahmen hinaus, oder Empfänger außerhalb der verantwortlichen Stelle |
| 3 | Besondere Kategorien (Entgelt, Gesundheit, Bewertung), Profilbildung, Drittlandtransfer oder externe Empfänger |

**MB — Arbeitsrecht / Mitbestimmung**

| Stufe | Anker |
|---|---|
| 0 | Keine Beschäftigtendaten berührt |
| 1 | Beschäftigtendaten nur organisatorisch (Zuständigkeit, Abwesenheit), keine Bewertung |
| 2 | Ergebnis ist einzelnen Beschäftigten zurechenbar; Auswertung möglich, aber nicht Zweck |
| 3 | Ergebnis fließt in Bewertung, Steuerung oder Entscheidung über einzelne Beschäftigte — oder ist zur Leistungs-/Verhaltenskontrolle geeignet |

**IT — IT-Sicherheit**

| Stufe | Anker |
|---|---|
| 0 | Keine sicherheitsrelevanten Berechtigungen oder Zugangsdaten betroffen, keine nennenswerte Angriffsfläche |
| 1 | Interne, nicht besonders schützenswerte Zugriffsrechte; Angriffsfläche gering (rein intern, kein externer Zugriff) |
| 2 | Verwaltet oder nutzt sicherheitskritische Berechtigungen/Zugangsdaten; oder nennenswerter externer Angriffsvektor (extern erreichbar, verarbeitet nicht vertrauenswürdige Eingaben) |
| 3 | Verwaltet Identitäts-/Zugriffssteuerung selbst, oder hätte bei Kompromittierung Zugriff auf breite Teile der IT-Landschaft (z. B. privilegierte Service-Accounts, domainweite Rechte) |

**RG — Regulatorik / Nachweispflicht**

| Stufe | Anker |
|---|---|
| 0 | Ergebnis ist Arbeitsmittel ohne Nachweisfunktion |
| 1 | Interne Nachvollziehbarkeit erwünscht, keine Pflicht |
| 2 | Ergebnis geht in prüfungsrelevante Unterlagen ein (Qualität, Steuern, Handelsbücher) |
| 3 | Ergebnis ist selbst aufbewahrungs- oder testatpflichtig; Revisionssicherheit gefordert |

**UR — Unternehmerisches Risiko**

| Stufe | Anker |
|---|---|
| 0 | Ausfall bleibt beim Verursacher, kein Sachschaden |
| 1 | Mehraufwand im Team, in Stunden aufholbar |
| 2 | Abteilungsprozess steht; wirtschaftlicher Schaden, Terminrisiko, Reputationswirkung intern |
| 3 | Unternehmensprozess steht, wesentlicher wirtschaftlicher Schaden, Außenwirkung, Geschäftsgeheimnis- oder IP-Abfluss |

### A.8.4 Herkunft der Bewertung

Auch hier gilt Prinzip P1 — nur bewerten, was nicht ableitbar ist:

| Dimension | Abgeleitet aus | Zusätzlich erklärt vom Prozesseigner/technischen Owner |
|---|---|---|
| KI | Eingesetzte Bibliotheken/APIs als Signal (teilweise) | Einsatzzweck und EU-AI-Act-Kategorie — **vollständig zu erklären**, Zweckbindung ist technisch nicht ablesbar |
| DS | Kategorien der referenzierten Datenobjekte, Customer-Kreis | Empfänger außerhalb der Organisation |
| MB | Datenkategorie der Inputs, Attestierungen 1 und 2 | Eignung zur Leistungs-/Verhaltenskontrolle |
| IT | Angefragte Berechtigungen/Scopes, Netzwerk-Exposition (Telemetrie) | — |
| RG | — | Nachweis-, Aufbewahrungs- oder Prüfpflicht — **vollständig zu erklären** |
| UR | Ausfallfolge, Kritikalität aus der Prozesskette (A.4.2) | Wirtschaftliche Größenordnung |

Zwei Dimensionen — KI und RG — müssen vollständig erklärt werden; sie haben kein oder nur ein sehr partielles technisches Korrelat. Genau dafür existiert die Selbstverpflichtung in Abschnitt A.10.

### A.8.5 Ableitung des Tiers: der Entscheidungsbaum

Das Tier wird durch einen **linearen Entscheidungsbaum** ermittelt — dieselben sechs Dimensionen aus A.8.2, als Ablauf statt als gleichzeitig zu würdigende Werte dargestellt. Der Baum ist zugleich als **eigenständiges Werkzeug für die erste Betrachtung eines Prozesses** gedacht: Ein Prozesseigner kann ihn ohne Vorwissen über das Objektmodell durchgehen und erhält am Ende einen Tier-Vorschlag.

**Aufbau:** Sechs Themenblöcke in fester Reihenfolge, schwerste Konsequenz zuerst. Jeder Block ist in sich linear — die schärfste Ausprägung führt sofort zu einem Ergebnis, ohne dass etwas gegeneinander abgewogen werden muss.

```
 1 · KI-Einsatz (EU AI Act)
 2 · Datenschutz
 3 · Arbeitsrecht / Mitbestimmung
 4 · IT-Sicherheit
 5 · Regulatorik / Nachweispflicht
 6 · Unternehmerisches Risiko
         │
         ▼
  höchster in 1–6 erreichter Tier-Wert = Tier des Prozesses
```

**Der Baum im Detail:**

| Schritt | Frage | Bei „Ja" | Bei „Nein" |
|---|---|---|---|
| 1a | Wird KI/ein KI-System eingesetzt — auch als Komponente (externe KI-API, eingebettetes Modell)? | weiter zu 1b | KI = 0, weiter zu Schritt 2 |
| 1b | Verbotene Praxis nach EU AI Act Art. 5 (z. B. Social Scoring, manipulative Beeinflussung, unautorisierte Emotionserkennung am Arbeitsplatz)? | **STOPP — Einsatz nicht zulässig**, keine Tier-Einstufung, Governance/Recht einbeziehen | weiter zu 1c |
| 1c | Hochrisiko-System nach Anhang III (u. a. Beschäftigung/Personalauswahl, Bewertung natürlicher Personen)? | **Tier 3** (+ Auflage K10), weiter zu Schritt 2 | weiter zu 1d |
| 1d | Transparenzpflichtig nach Art. 50 (Chatbot, synthetische Inhalte, Emotionserkennung ohne Ausnahme)? | **mind. Tier 2** (+ Auflage K10), weiter zu Schritt 2 | KI = 1 (minimal), weiter zu Schritt 2 |
| 2a | Werden personenbezogene Daten verarbeitet? | weiter zu 2b | DS = 0, weiter zu Schritt 3 |
| 2b | Besondere Kategorien, Profilbildung, Drittlandtransfer oder externe Empfänger? | **Tier 3**, weiter zu Schritt 3 | weiter zu 2c |
| 2c | Personenbezug über Geschäftskontakt hinaus, oder Empfänger außerhalb der verantwortlichen Stelle? | **mind. Tier 2**, weiter zu Schritt 3 | DS = 1, weiter zu Schritt 3 |
| 3a | Kann das Ergebnis Leistung/Verhalten einzelner Beschäftigter bewerten, steuern oder beeinflussen? | weiter zu 3b | MB = 0, weiter zu Schritt 4 |
| 3b | Ist das Zweck oder unmittelbare Folge? | **Tier 3**, weiter zu Schritt 4 | **mind. Tier 2** (möglich, aber nicht Zweck), weiter zu Schritt 4 |
| 4a | Verwaltet/nutzt die Anwendung sicherheitskritische Berechtigungen/Zugangsdaten, oder besteht ein nennenswerter Angriffsvektor (extern erreichbar, nicht vertrauenswürdige Eingaben)? | weiter zu 4b | IT = 0/1, weiter zu Schritt 5 |
| 4b | Verwaltet Identität/Zugriffssteuerung selbst, oder bestünde bei Kompromittierung Zugriff auf breite Teile der IT-Landschaft? | **Tier 3**, weiter zu Schritt 5 | **mind. Tier 2**, weiter zu Schritt 5 |
| 5a | Unterliegt das Ergebnis einer Aufbewahrungs-, Nachweis- oder Prüfpflicht? | weiter zu 5b | RG = 0/1, weiter zu Schritt 6 |
| 5b | Ist das Ergebnis selbst aufbewahrungs- oder testatpflichtig? | **Tier 3**, weiter zu Schritt 6 | **mind. Tier 2** (fließt in prüfungsrelevante Unterlagen ein), weiter zu Schritt 6 |
| 6a | Wäre bei Ausfall, Fehler oder Datenabfluss ein Unternehmensprozess betroffen, mit wesentlichem Schaden? | **Tier 2** — bleibt Tier 2 auch bei maximaler Ausprägung, sofern 1–5 durchgehend „nein"/niedrig waren (reines Betriebsrisiko hebt allein nicht in Tier 3) | weiter zu 6b |
| 6b | Wäre ein Abteilungsprozess betroffen, mit spürbarem Schaden? | **mind. Tier 2** | kein Treffer in 1–6 → **Tier 1** |

**Zwei Nutzungsweisen:**

- **Schnell (nur Tier):** Baum von oben nach unten durchgehen, beim ersten „Tier 3"-Treffer abbrechen. Ausreichend für Freigabewege und Auflagen nach A.8.6, und genau die Form, in der der Baum als erste Betrachtung eines neuen Prozesses dient.
- **Vollständig (Profil für K-Klassen):** Alle sechs Schritte bis zum Ende durchlaufen, auch nach einem frühen Tier-3-Treffer — nur so ergibt sich das vollständige Profil, das A.9 für die K-Klassen-Ableitung braucht.

**Schreibweise für das vollständige Profil:** `KI1-DS3-MB0-IT1-RG2-UR2 → Tier 3` (höchster Einzeltreffer bestimmt den Tier — hier DS = 3 in Schritt 2b).

**Korrekturfaktor Ausführungsart:** Läuft ein Tool unbeaufsichtigt/geplant statt interaktiv, wird das bei Grenzfällen (z. B. knappes „Nein" an einem der Ja/Nein-Punkte) als zusätzlicher Anhaltspunkt in die Einzelfallprüfung bei Gate 1 einbezogen. Es verändert das Baumergebnis nicht automatisch (siehe A.6).

### A.8.6 Auflagen je Tier

| | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| Prozessobjekt | erforderlich | erforderlich | erforderlich |
| Selbstverpflichtung | Kurzform | vollständig | vollständig + jährlich |
| Code in Versionsverwaltung | empfohlen | empfohlen | **Pflicht** |
| Kontrolle der Ausführungsumgebung | Entwickler | Entwickler | **Governance** |
| Review vor Erstfreigabe | nein | nein | **ja** |
| Deployment | selbst | selbst | **Pipeline** |
| Compliance-/BR-Behandlung | entfällt | Sammelbewertung | **Einzelbewertung** |

---

## A.9 Übersetzung des Sollzustands in die Technik

### A.9.1 Zweistufige Übersetzung

Der Sollzustand darf nicht direkt gegen Produktmerkmale gemappt werden — sonst müsste der Katalog für jede neue Technologie neu geschrieben werden. Stattdessen zwei Stufen:

```
Profil (KI/DS/MB/IT/RG/UR)  ──►  abstrakte Anforderungsklasse  ──►  technologiespezifische Umsetzung
   was gebraucht wird              was erfüllt sein muss            wie es hier erfüllt wird
   (technologieneutral)            (technologieneutral)             (produktspezifisch, Teil B)
```

Die mittlere Stufe ist stabil. Nur die rechte Spalte — Teil B dieses Dokuments — wächst, wenn eine Technologie hinzukommt.

### A.9.2 Anforderungsklassen und ihre Auslöser

| # | Anforderungsklasse | Ausgelöst durch |
|---|---|---|
| K1 | Identität und Zugriffssteuerung — wer darf ausführen, wer ändern | MB ≥ 2 · DS ≥ 2 · IT ≥ 2 |
| K2 | Datenzugriffsminimierung — kein Zugriff über den deklarierten Bedarf hinaus | DS ≥ 1 |
| K3 | Nachvollziehbarkeit des Codes — Versionierung, Review, Autorschaft | RG ≥ 2 · IT ≥ 2 |
| K4 | Nachvollziehbarkeit der Ausführung — Protokollierung, Auswertbarkeit | MB ≥ 2 · RG ≥ 2 · IT ≥ 2 |
| K5 | Trennung Entwicklung / Produktion | RG ≥ 2 · UR ≥ 3 · IT ≥ 2 |
| K6 | Aufbewahrung und Revisionssicherheit | RG = 3 |
| K7 | Verfügbarkeit und Wiederanlauf | UR ≥ 2 |
| K8 | Betroffenentransparenz — Information, Auskunftsfähigkeit, Löschung | MB ≥ 2 · DS ≥ 2 |
| K9 | Nachfolge und Abhängigkeitsreduktion — kein Einzelpersonen-Wissen | UR ≥ 2 |
| K10 | KI-spezifische Auflagen — Transparenz, menschliche Aufsicht, Dokumentation nach EU AI Act | KI ≥ 2 |

**Notation:** Das Zeichen „·" zwischen mehreren Bedingungen einer Zeile bedeutet **ODER** — eine der genannten Schwellen reicht aus, alle müssen nicht gleichzeitig erfüllt sein. K1 triggert also schon, wenn nur DS ≥ 2 gilt, auch wenn MB und IT niedrig bleiben.

**Zu K10:** EU-AI-Act-Auflagen wie „menschliche Aufsicht" oder „Konformitätsbewertung" lassen sich nicht sauber in eine der übrigen neun Klassen pressen, weder Datenminimierung noch Code-Nachvollziehbarkeit erfassen diese Konzepte. K1, K3, K4 und K5 werden zusätzlich durch IT-Sicherheit ausgelöst, da Zugriffssteuerung, Code-Nachvollziehbarkeit, Ausführungsprotokollierung und Dev/Prod-Trennung ebenso genuine IT-Sicherheitsanliegen wie Compliance-Anliegen sind. K10 selbst ist überwiegend organisatorisch zu erfüllen (menschliche Aufsicht, Dokumentation, Konformitätsbewertung) — anders als K1–K9 hängt die Erfüllung kaum von der Ausführungsplattform ab; eine tiefe technologiespezifische Umsetzung je Teil-B-Abschnitt ist daher nicht in gleichem Maß sinnvoll wie bei den anderen Klassen.

### A.9.3 Wie daraus eine Entscheidung wird

Die Eignung ergibt sich aus dem Abgleich, nicht aus Vorliebe oder Gewohnheit:

1. Profil bestimmen (Abschnitt A.8)
2. Ausgelöste Anforderungsklassen ermitteln (A.9.2)
3. Gegen die Technologiematrix prüfen (Teil C.1 — die vollständige, aktuelle Matrix über alle Technologien)
4. Ein ❌ bei einer ausgelösten Klasse = **Ausschlusskriterium**; ein ⚠️ = kompensierende Maßnahme erforderlich und zu dokumentieren

Das ist die operative Fassung von „es ist unerheblich, wie die Technologie ausgestattet ist": Nicht die Technologie definiert das Machbare, sondern der Prozess das Erforderliche.

---

## A.10 Selbstverpflichtung von Prozesseigner und Entwickler

### A.10.1 Warum es sie braucht

Drei Arten von Aussagen sind auf Tool-Ebene nicht skalierend messbar:

- **Zweck** — wozu verarbeitet wird, ist nirgends technisch hinterlegt
- **Absicht** — ob eine mögliche Auswertung auch beabsichtigt ist (Dimension MB)
- **Nicht deklarierte Quellen** — Uploads, Zwischenablagen, lokale Kopien entziehen sich jeder Telemetrie

Für diese Restmenge tritt eine dokumentierte Erklärung an die Stelle der Messung. Sie ist der einzige Baustein des Modells, der nicht auf Ableitung beruht — und deshalb bewusst klein gehalten.

> **Ehrliche Einordnung:** Eine Selbstverpflichtung ist keine Kontrolle, sondern eine **Zuordnung von Verantwortung**. Sie wirkt, weil sie eine Person benennt, nicht weil sie etwas verifiziert. Sie darf deshalb nie eine messbare Kontrolle ersetzen, sondern nur schließen, was messtechnisch unerreichbar ist.

### A.10.2 Erklärung des Prozesseigners

Bezogen auf das Prozessobjekt, nicht auf einzelne Tools:

1. Der deklarierte **Zweck** ist vollständig und abschließend.
2. Die referenzierten **Datenobjekte** decken alle im Prozess verarbeiteten Daten ab.
3. Der **Empfängerkreis** ist vollständig; eine Weitergabe darüber hinaus findet nicht statt.
4. Das Ergebnis wird **nicht** zur Bewertung, Steuerung oder Kontrolle einzelner Beschäftigter verwendet — oder, falls doch: die Verwendung ist in Dimension MB deklariert.
5. Bestehende **Nachweis- oder Aufbewahrungspflichten** (Dimension RG) sind vollständig angegeben.
6. Eine **Zweckänderung** wird angezeigt, bevor sie wirksam wird.

### A.10.3 Erklärung des technischen Owners

Bezogen auf das Tool-Objekt:

1. Die Umsetzung entspricht den aus dem Profil abgeleiteten **Anforderungsklassen**; kompensierende Maßnahmen sind dokumentiert.
2. Es werden **keine undeklarierten Datenquellen** verarbeitet — keine Uploads, Zwischenablagen oder lokalen Kopien außerhalb der referenzierten Datenobjekte.
3. Es findet **keine Ausleitung** von Daten an nicht deklarierte Ziele statt.
4. **Zugangsdaten und Secrets** liegen nicht im Code und nicht in Konfigurationsdateien.
5. Eine **Rahmenverletzung** nach Abschnitt A.11 wird angezeigt, bevor sie produktiv wird.
6. Eine **Stellvertretung** ist benannt und in der Lage, den Betrieb zu übernehmen.

### A.10.4 Eigenschaften, ohne die es zur Formalie wird

| Eigenschaft | Begründung |
|---|---|
| **Namentlich und datiert** | Ohne benannte Person entsteht keine Zuordnung |
| **An die Profilversion gebunden** | Ändert sich das Profil, verfällt die Erklärung automatisch |
| **Spezifisch statt pauschal** | Konkrete Aussagen sind im Nachhinein prüfbar, allgemeine Zusagen nicht |
| **Jährliche Bestätigung** | Bestätigen, nicht neu ausfüllen — ein Klick, wenn nichts abweicht |
| **Maximal eine Seite** | Was länger ist, wird nicht gelesen und damit nicht getragen |
| **Voraussetzung, kein Anhang** | Ohne Erklärung keine Freigabe und keine Provisionierung (Prinzip P3) |

### A.10.5 Verhältnis zur Freigabe

- **Tier 1:** Erklärung in Kurzform, Bestätigung genügt, keine Prüfung
- **Tier 2:** Beide Erklärungen vollständig, keine Vorabprüfung
- **Tier 3:** Beide Erklärungen vollständig, Bestandteil der Freigabe an Gate 1, jährliche Erneuerung

Widerspricht eine Erklärung der gemessenen Telemetrie, ist das ein Cockpit-Befund (Abschnitt A.14) — der Abgleich zwischen Erklärung und Messung ist damit selbst eine Kontrolle, ohne zusätzlichen Aufwand.

---

## A.11 Die zwei Gates

Prinzip P4 operationalisiert. Im gesamten Modell — über alle drei Technologiedomänen hinweg — wartet ein Entwickler an **genau zwei** Stellen:

| Vorgang | Gate? |
|---|---|
| Prozessobjekt anlegen | ✅ kein Gate – Self-Service |
| Datenobjekt anlegen + kategorisieren (inkl. BigQuery-Dataset, GCS-Bucket) | ✅ kein Gate |
| Tool an Prozess hängen | ✅ kein Gate |
| Tier-1/2 entwickeln und deployen | ✅ kein Gate |
| Änderung innerhalb des Rahmens | ✅ kein Gate |
| **Tier-3-Erstfreigabe** | 🚦 **Gate 1** |
| **Rahmenverletzung** | 🚦 **Gate 2** |

Alles andere läuft ungebremst — unabhängig davon, ob es sich um ein Apps-Script-Projekt, ein Python-Deployment oder ein BigQuery-Dataset handelt. Es entsteht **kein dritter Gate-Typ** für Python oder GCP-Datendienste; Tier-3-Fälle in Python oder bei GCP-Datendiensten laufen durch dasselbe Gate 1 wie Tier-3-Apps-Script-Projekte.

### Das Envelope-Modell

> Das Prozessobjekt definiert einen **Rahmen**. Das Tool muss hineinpassen. Die Freigabe gilt für den Rahmen, nicht für den Stand.

**Auslöser für Gate 2 – abschließende Liste:**

1. Neues Datenobjekt mit **höherer** Kategorie als bisher deklariert
2. Customer-Kreis überschreitet die deklarierte Reichweitenstufe
3. Neuer Schreibzugriff auf ein System of Record
4. Neuer externer Endpunkt außerhalb der Allowlist (URL-Ziel bei Apps Script, Egress-Ziel bei Python/Kubernetes)
5. Wechsel von „Mensch dazwischen" zu vollautomatisiert

Alles andere – Refactoring, neue Features, geänderte Logik, Performance-Arbeit – löst **keinen** Review aus. Das ist der goldene Pfad, technisch definiert statt als Absichtserklärung.

---

## A.12 Ist-Erfassung: Telemetriequellen

Das Modell steht und fällt mit der Telemetrie. Was aus welcher Quelle kommt — je Technologie in Teil B vertieft, hier die technologieneutrale Übersicht:

| Signal | Quelle (Apps Script) | Quelle (Python/Kubernetes) | Quelle (GCP-Datendienste) |
|---|---|---|---|
| Zugriffsberechtigungen je Tool | OAuth Token Audit | Workload-Identity-Bindings, RBAC | IAM-Bindings, Dataset-/Bucket-ACLs |
| Aktivierte APIs / Dienste | Cloud Console je Standard-Projekt | Aktivierte APIs im Compute-Projekt | Aktivierte APIs im Daten-Projekt |
| Externe Ziele | Drive Log Events | NetworkPolicy-Logs, Egress-Firewall-Logs | VPC-Flow-Logs, Audit Logs |
| Reichweite Deployment | Marketplace-/Deployment-Konfiguration | Namespace/Cluster-Zuordnung | Dataset-/Bucket-Freigaben |
| Ausführungen, Frequenz | Apps-Script-Report, Cloud Logging | Kubernetes-Metriken, CronJob-Historie | Cloud Audit Logs, INFORMATION_SCHEMA |
| Projektbestand, Metadaten | Cloud Asset Inventory | Cloud Asset Inventory | Cloud Asset Inventory |
| Code-Herkunft, Scans | Azure DevOps Pipeline (Secret-/Snyk-Scan) | Azure DevOps Pipeline (Secret-/Snyk-Scan) | dbt/Terraform-Pipeline |

**Voraussetzung:** Die Telemetrie ist nur verfügbar, wenn Tools an Standard-Projekten hängen — bei Apps Script an Standard-GCP-Projekten (Teil B.1), bei Python an den Fachbereichs-Compute-Projekten (Teil B.2), bei Datendiensten an den Fachbereichs-Daten-Projekten (Teil B.3). Ohne diese Zuordnung bleibt das jeweilige Tool-Objekt leer und müsste manuell gepflegt werden, womit das Modell an Prinzip P1 scheitert.

---

## A.13 Compliance als gemessener Zustand

### A.13.1 Grundsatz

> Die Klassifizierung erfolgt auf **Prozessebene**. Die Technik bildet den Prozess lediglich ab.
>
> **Solange eine Applikation sich innerhalb des klassifizierten und auditierten Rahmens ihres Prozesses bewegt, ist sie compliant.** Überschreitet sie ihn, gilt sie als non-compliant, und es folgt ein Lenkungsprozess.

Compliance ist damit kein Urteil, das in einer Sitzung gefällt wird, sondern ein **fortlaufend abgeleiteter Zustand**. Er entsteht aus dem Vergleich zweier bereits vorhandener Größen — es ist kein zusätzlicher Erfassungsaufwand nötig:

```
Prozessbewertung (Soll)  ──►  Erlaubnisrahmen (allowed / not allowed)
                                        │
                                    Vergleich
                                        │
Telemetrie der Applikation (Ist),  ─────┘   ──►  Zustand: compliant / non-compliant
wo messbar; sonst Selbstverpflichtung
```

Die Applikation wird nie selbst bewertet. Sie erbt ihre Zulässigkeit vollständig aus dem Prozess, dem sie dient. Wo die Telemetrie eine Aussage nicht liefern kann, tritt die Selbstverpflichtung (A.10) an ihre Stelle — der Soll-Ist-Abgleich bleibt derselbe, nur die Ist-Quelle wechselt.

### A.13.2 Der Erlaubnisrahmen

Zwei Schichten, unterschiedlicher Geltungsbereich:

**Schicht 1 — Prozessspezifischer Positivrahmen** (aus der Bewertung abgeleitet)

Es gilt das Positivlistenprinzip: **Was nicht ausdrücklich erlaubt ist, ist nicht erlaubt.**

| Rahmenelement | Quelle | Messbar über |
|---|---|---|
| Erlaubte Datenobjekte | Input/Output des SIPOC | Datenzugriffe, APIs, Endpunkte |
| Obergrenze der Datenkategorie | Dimension DS | Kategorie der referenzierten Objekte |
| Erlaubte Reichweite / Empfängerkreis | Customer-Spalte | Deployment- und Freigabekonfiguration |
| Erlaubte Zugriffsart | Wirkungsart (verändert/gestaltet) | Lese- vs. Schreibberechtigungen |
| Erlaubte externe Ziele | Prozessdeklaration | URL-/Egress-Logs, Allowlist |
| Erlaubte Ausführungsart | Attestierung 2 | Lauftyp interaktiv/getriggert/geplant |
| Erlaubte Ausführungsidentität | Tier-Auflagen | Deployment-/Workload-Identity-Konfiguration |

**Schicht 2 — Organisationsweite Verbote** (gelten immer, unabhängig vom Prozess)

Diese lassen sich durch keine Prozessbewertung freischalten:

- Secrets oder Zugangsdaten im Code oder in Konfigurationsdateien
- Domain-Wide Delegation für Fachbereichsanwendungen
- Umgehung der zentralen Identität (geteilte Accounts, persönliche Keys)
- **Service-Account-Keys für Compute-Workloads** — ausschließlich Workload Identity Federation (neu, siehe B.2)
- Datenausleitung an nicht deklarierte externe Ziele
- Verarbeitung von Daten aus nicht klassifizierten Quellen bei Dimension DS ≥ 2

### A.13.3 Zustände

| Zustand | Bedingung | Bedeutung |
|---|---|---|
| 🟢 **Compliant** | Ist ⊆ Erlaubnisrahmen, keine Verletzung von Schicht 2 | Kein Handlungsbedarf, keine Prüfung, keine Freigabe nötig |
| 🟡 **Nicht zugeordnet** | Applikation ohne Prozessbezug | Kein Rahmen vorhanden, also kein Abgleich möglich — Zustand des Altbestands |
| 🔴 **Non-compliant** | Ist überschreitet den Rahmen oder verletzt Schicht 2 | Lenkungsprozess |

Der gelbe Zustand ist bewusst von Rot getrennt: Eine nicht zugeordnete Anwendung ist nicht regelwidrig, sondern **unbewertet**. Für den Altbestand ist das der Ausgangszustand und die Arbeitsliste — nicht ein Vorwurf.

### A.13.4 Der Abgleich

- **Automatisch und fortlaufend**, ausgelöst durch Telemetrieänderung (neue Berechtigung, neues Ziel, geänderte Reichweite) — nicht durch Kalender oder Stichprobe
- **Kein Mensch im Regelbetrieb.** Solange grün, sieht niemand etwas; es entsteht kein Vorgang
- Der grüne Zustand ist damit **kostenlos** — genau das macht das Modell skalierbar, gerade jetzt mit drei statt einer Technologie

Die Auslöser für den Zustandswechsel sind die in Abschnitt A.11 abschließend definierten Rahmenverletzungen. Alles andere — Refactoring, neue Funktionen, geänderte Logik — verändert den Zustand nicht.

### A.13.5 Der Lenkungsprozess

Die Fristen skalieren mit dem Tier; die Stufen sind identisch.

| Stufe | Auslöser | Maßnahme | Frist Tier 1 / 2 / 3 |
|---|---|---|---|
| **1 — Hinweis** | Zustandswechsel auf rot | Automatische Benachrichtigung an technischen Owner **und** Prozesseigner, mit Angabe der konkreten Überschreitung. Kein Eingriff | 30 / 15 / 5 Arbeitstage |
| **2 — Eskalation** | Frist verstrichen | Governance übernimmt, Führungskraft des Prozesseigners wird informiert | +15 / +10 / +5 Tage |
| **3 — Technische Maßnahme** | Weiterhin ungelöst | Zugriffsentzug, Deployment gesperrt, App/Workload in der Zugriffssteuerung blockiert | — |

Bei Verletzung von Schicht 2 entfällt Stufe 1: Diese Fälle gehen unmittelbar in Stufe 2.

### A.13.6 Die drei zulässigen Auflösungen

Non-compliant bedeutet **nicht** automatisch „fehlerhafte Anwendung". Alle drei Wege sind gleichwertig:

| Auflösung | Wann | Folge |
|---|---|---|
| **Anwendung anpassen** | Die Überschreitung war ungewollt | Zurück in den Rahmen, Zustand wird grün |
| **Rahmen erweitern** | Der Prozess hat sich real verändert; die Bewertung ist veraltet | Neubewertung nach Abschnitt A.8, ggf. neues Profil und Tier, Freigabe über Gate 2 |
| **Anwendung stilllegen** | Weder Anpassung noch Erweiterung gerechtfertigt | Abschaltung, Prozessobjekt bleibt |

> Der mittlere Weg ist der wichtigste für die Akzeptanz: Eine Überschreitung ist oft ein Signal, dass die **Bewertung** hinterherhinkt — nicht dass jemand etwas falsch gemacht hat. Wird das im Betrieb anders gelebt, entsteht Vermeidungsverhalten statt Meldeverhalten, und der gesamte Telemetrieansatz verliert seine Grundlage.

### A.13.7 Was dieses Modell leistet

| Klassische Prüfung | Gemessener Zustand |
|---|---|
| Stichprobe zu einem Zeitpunkt | Fortlaufend, vollständig |
| Aufwand wächst mit Anzahl der Anwendungen | Aufwand wächst nur mit Anzahl der **Abweichungen** |
| Ergebnis veraltet nach der ersten Änderung | Ergebnis folgt der Änderung automatisch |
| Compliance ist eine Meinung | Compliance ist ein Zustand mit nachvollziehbarer Herleitung |
| Nachweis: Protokoll einer Bewertung | Nachweis: lückenlose Zustandshistorie je Anwendung |

---

## A.14 Transparenz und Lenkung

Was das Cockpit zeigen muss, damit Steuerung möglich ist – jede Zeile ist eine **Handlungsaufforderung**, keine Statistik:

| Sicht | Zeigt | Handlung |
|---|---|---|
| Prozesse ohne Owner | Verwaiste Verantwortung | Owner benennen oder stilllegen |
| Assets ohne Prozesszuordnung (🟡) | Der Cleanup-Stapel | Zuordnen oder abschalten |
| Non-compliante Anwendungen (🔴) | Offener Lenkungsprozess je Stufe | Nach Abschnitt A.13.5 verfolgen |
| Rahmenabweichungen | Soll-Ist-Drift | Gate 2 auslösen |
| Datenobjekte ohne Kategorie | Klassifikationslücke | Kategorisieren |
| Kritikalitätsketten | Blast Radius je Prozess | Priorisierung von Absicherung |
| Tier-Verteilung über Zeit, je Technologie | Wohin wächst das Portfolio | Ressourcensteuerung |
| Assets ohne Ausführung > 12 Monate | Toter Bestand | Stilllegen |
| Attestierungen älter als 12 Monate | Veraltete Erklärungen | Bestätigung anfordern |
| Erklärung widerspricht Telemetrie | Selbstverpflichtung vs. Messung | Klärung mit Owner |
| Technologie erfüllt ausgelöste Anforderungsklasse nicht | Ausschlusskriterium nach A.9.3 | Technologiewechsel oder Kompensation |
| Alt-Executables im Melde-/Blockierungspfad | Migrationsfortschritt nach A.16 | Fristen nachhalten |

**Das eigentliche Steuerungsinstrument** ist die Rahmenabweichungs-Sicht: Governance wird damit zu einem **Abgleich** statt einer Prüfung. Ihr inspiziert nicht den Gesamtbestand, sondern behandelt Abweichungen zwischen deklariertem Bedarf und gemessenem Verhalten. Nur das skaliert.

---

## A.15 Rollen

| Rolle | Verantwortung | Aufwand |
|---|---|---|
| **Prozess-Owner** (Fachbereich) | Prozessobjekt aktuell halten, Bewertung der vier Dimensionen, Selbstverpflichtung (A.10.2) | ~1h Ersterfassung, danach jährliche Bestätigung |
| **Technischer Owner** | Tool-Zuordnung, Umsetzung der Anforderungsklassen, Selbstverpflichtung (A.10.3) | Minuten je Tool |
| **Datenobjekt-Owner** | Kategorie und Klassifikation der Quelle | Einmalig je Quelle |
| **Governance** | Gate 1 und 2, Cockpit, Regelpflege | Skaliert mit Tier-3-Menge, nicht mit Gesamtbestand |
| **Plattform** | Provisionierung, Pipeline, Telemetrie — **eine Instanz für alle drei Technologiedomänen** (Apps Script, Python/Kubernetes, GCP-Datendienste), kein getrenntes Team je Technologie | Betrieb |

**Warum eine Plattform-Instanz statt getrennter Teams:** Sobald Apps Script, Python und GCP-Datendienste hinter demselben Self-Service-Frontend liegen (B.4), würde eine Aufteilung des Betriebs nach Technologie eine künstliche Übergabegrenze mitten durch einen einzigen Nutzerfluss ziehen. Die Provisionierungslogik — Prozessobjekt vorhanden? Tier bestimmt? Pipeline auslösen? — ist technologieübergreifend identisch; nur die letzte Umsetzungsstufe unterscheidet sich (Teil B).

### Was der Prozess-Owner bekommt

Nicht „Freiheit" – die besteht heute bereits, nur unkontrolliert. Die belastbare Zusage lautet:

> **Heute ist eure Fachbereichsentwicklung geduldet. Künftig ist sie abgesichert.**

Konkret:
- Legitimiertes Selbstentwicklungsrecht im Fachbereich, gegen künftige Einschränkungen verteidigt
- **Keine Einzelvorlage beim Betriebsrat** – die Bewertung erfolgt auf Prozessebene
- Schnelle, geregelte Provisionierung statt Rückfragen — über alle drei Technologien identisch
- Pipeline, Scans und Support inklusive
- Bei Tier-Aufstieg: mehr Unterstützung, nicht mehr Strafe

> ⚠️ **Kritischer Punkt:** Ohne diese Umdeutung landet Prozessverantwortung als reine Zusatzlast – dann wird die Übernahme zur Formalie und das Modell ist hohl. Der Aufstieg zwischen Tiers muss sich als **Upgrade** anfühlen, sonst optimieren alle darauf, im untersten Tier zu bleiben.

---

## A.16 Bestands- und Migrationsprinzip

### A.16.1 Grundsatz: on touch, nicht erzwungen

Für bestehende Anwendungen gilt technologieübergreifend:

> **Migration on touch** — wer eine Anwendung ohnehin anfasst (Bugfix, neues Feature, Weiterentwicklung), läuft künftig über den goldenen Pfad. Es gibt **keine pauschale Zwangsmigration** unberührten Bestands.

Das gilt gleichermaßen für Apps-Script-Projekte, Python-Anwendungen und bestehende Nutzungen des GCP-Datendienste-Stacks.

### A.16.2 Ausnahme: strukturell nicht erfüllbare Technologie bei Tier 3

Wo eine Technologie eine ausgelöste Anforderungsklasse strukturell nicht erfüllen kann (❌ in der Technologiematrix, Teil C.1), ist reines Zuwarten kein neutraler Zustand — der Prozess trägt in der Zwischenzeit ein unkompensiertes Risiko. Für diese Fälle gilt eine **abgestufte Mindest-Kompensationspflicht**, ohne die vollständige on-touch-Regel zu ersetzen:

1. **Vollinventur.** Signaturbasierte Erkennung erfasst den vollständigen Bestand strukturell ausgeschlossener Alt-Anwendungen (heute: lokal verteilte `.exe`-Anwendungen) über die vorhandene Endpoint-/Applikationskontrolle — unabhängig davon, ob ein Owner sich meldet.
2. **Grace Period 1 — Meldepflicht.** Ab Erkennung läuft eine Frist, innerhalb derer der technische Owner die Anwendung einem Prozessobjekt zuordnen und die Mindest-Kompensation liefern muss: Code-Backup in Versionsverwaltung, Owner-Attestierung nach A.10.3. Das ist **nicht** die vollständige Migration — nur die Absicherung des Ausfall- und Bus-Faktor-Risikos, die auch ohne Technologiewechsel möglich ist.
3. **Grace Period 2 — letzte Warnung.** Nach Ablauf von Grace Period 1 ohne Erfüllung folgt eine zweite, kürzere Frist mit expliziter Ankündigung der Blockierung.
4. **Blockierung auf Applikationsebene.** Nach Ablauf von Grace Period 2 wird die Ausführung technisch unterbunden.

> Die konkreten Fristlängen sind an dieser Stelle **als Vorschlag markiert, nicht als Festlegung**: Eine Größenordnung von 60–90 Tagen für Grace Period 1 und 15–30 Tagen für Grace Period 2 ist ein plausibler Ausgangspunkt, sollte aber mit dem Fachbereich abgestimmt werden, der die Endpoint-/Applikationskontrolle betreibt.

**Warum das die on-touch-Regel nicht aufweicht:** Schritt 2 verlangt keine Migration auf eine neue Technologie — nur die zwei Mindestmaßnahmen, die das größte Einzelrisiko (kein Backup, kein benannter Verantwortlicher) schließen. Die eigentliche Migration auf den golden Path bleibt an „touch" gebunden. Nur wenn selbst diese Mindestmaßnahme verweigert wird, greift Schritt 4.

### A.16.3 Sichtbarkeit im Cockpit

Der Fortschritt durch diesen Melde- und Kompensationspfad ist ein eigener Cockpit-Befund (A.14) — nicht weil er eine neue Kontrolle wäre, sondern weil er derselben Logik folgt wie jeder andere Soll-Ist-Abgleich: Frist gesetzt, Frist eingehalten oder nicht, nächste Eskalationsstufe.

---

## A.17 Was dieses Konzept ausdrücklich NICHT verlangt

Zur Erwartungssteuerung – und weil Adoption an vermuteten Auflagen scheitert, nicht an tatsächlichen:

- ❌ Keine Dokumentation von Code oder Logik
- ❌ Keine Prüfung von Tier-1- und Tier-2-Anwendungen
- ❌ Keine ODCS-Kontrakte für normale Datennutzung
- ❌ Keine Migration bestehender Anwendungen ohne Anlass (Ausnahme: Mindest-Kompensation für strukturell ausgeschlossene Tier-3-Altfälle, A.16.2)
- ❌ Keine Freigabe für Refactoring, Features oder Bugfixes
- ❌ Keine Einzelvorlage beim Betriebsrat je Anwendung
- ❌ Keine manuelle Pflege dessen, was Telemetrie liefert
- ❌ Keine Vorab-Kategorisierung des Bestands
- ❌ Keine Vorgabe, welche Technologie zu verwenden ist – nur, welche Anforderungen sie erfüllen muss

---

## A.18 Bekannte Grenzen und Abhängigkeiten

| # | Punkt | Wirkung | Abhängigkeit |
|---|---|---|---|
| 1 | Telemetrie erfordert Standard-Projekte in allen drei Domänen | Ohne Migration bleibt das jeweilige Tool-Objekt manuell | Apps-Script-Phase 3, Python-Cluster-Rollout, Daten-Standardprojekte (Teil C.3) |
| 2 | Datenvererbung erfordert klassifizierte Quellen | Ohne SAP-Layer bleibt Personenbezug pro Tool zu klären | SAP-Datenzugang |
| 3 | Telemetrie liefert Syntax, nicht Semantik | Attestierungen bleiben unverzichtbar | – |
| 4 | Eingebaute Apps-Script-Services evtl. ohne Audit-Log | Lücke in der Ist-Erfassung | Offener Punkt in B.1.15 |
| 5 | Skript-zu-Skript-Aufrufe schwer erfassbar | Ketten auf Tool-Ebene unvollständig | Offener Punkt in B.1.15 |
| 6 | Prozess-Owner-Akzeptanz | Ohne echte Gegenleistung wird das Modell hohl | Kommunikation, Abschnitt A.15 |
| 7 | Granularitätsdrift zwischen Fachbereichen | Uneinheitliche Flughöhe entwertet Vergleichbarkeit | Referenzkorpus, Teil C.3 Stufe A |
| 8 | Selbstverpflichtung ist nicht verifizierend | Dimensionen RG und KI sowie Zweckangaben bleiben unbelegt; nur der Abgleich mit Telemetrie deckt Widersprüche auf | A.10.1 |
| 9 | Technologiematrix (Teil C.1) altert | Produktfähigkeiten ändern sich; Einstufungen sind periodisch zu prüfen | Jährliche Revision |
| 10 | Entscheidungsbaum A.8.5 ist neu und ungetestet | Reihenfolge und Schwellen der sechs Schritte beruhen auf Ableitung aus den Ankern (A.8.3), nicht auf gelebter Praxis | Erste Fälle nach Einführung parallel gegen Fachbewertung prüfen, Reihenfolge ggf. nachschärfen |
| 11 | EU-AI-Act-Kategorisierung in der KI-Dimension (A.8.3) ist vereinfacht dargestellt | Ersetzt keine Einzelfallprüfung nach Anhang III bzw. der Verbotsliste in Art. 5, insbesondere in Grenzfällen | Bei Unklarheit über die Kategorie: Rechtsabteilung vor Tier-Festlegung einbeziehen |
| 12 | Grace-Period-Fristen in A.16.2 sind Platzhalter | Zu kurze Fristen erzeugen unnötigen Druck, zu lange verlängern das ungeschützte Fenster | Abstimmung mit Endpoint-/Applikationskontrolle |

---

## A.19 Der Prüfstein

Vor jeder Detailentscheidung im weiteren Ausbau eine Frage:

> **Muss dafür jemand warten – und wenn ja, warum?**

Wenn die Antwort keine Risikoreduktion benennt, die den Wartezeitpreis rechtfertigt, gehört der Schritt nicht ins Modell. Das ist die operative Fassung des Gravitationsprinzips: Der geregelte Weg muss der schnellere sein, sonst wird er umgangen – und dann hat man Bürokratie ohne Kontrolle. Das gilt für Apps Script, für Python auf dem Kubernetes-Golden-Path und für den GCP-Datendienste-Stack in exakt gleichem Maß.

---

# TEIL B — TECHNISCHE REALISIERUNG

*Wie die in Teil A definierten Anforderungen je Technologie konkret erfüllt werden. Dieser Teil ändert sich, wenn sich Produktfähigkeiten ändern oder eine Technologie hinzukommt — Teil A bleibt davon unberührt.*

## B.0 Geltungsbereich und gemeinsame Ausgangslage

Drei Technologiedomänen werden im Folgenden behandelt:

| Domäne | Ist-Zustand | Abschnitt |
|---|---|---|
| **Google Apps Script** | Ca. 13.000 Projekte, keine Governance-Kontrolle, überwiegend an Default-GCP-Projekten | B.1 |
| **Python (Fachbereichsentwicklung)** | Jede lokal oder cloud-seitig laufende Python-Anwendung eines Fachbereichs — interaktiv oder unbeaufsichtigt/geplant laufend —, aktuell überwiegend über ein CI/CD-Framework zu `.exe` kompiliert und lokal auf Endgeräten verteilt | B.2 |
| **GCP-Datendienste** | BigQuery und Cloud Storage, von Fachbereichen bereits heute genutzt, bislang ohne einheitliches Self-Service-Provisionierungsmodell | B.3 |

Alle drei Domänen laufen künftig hinter demselben Self-Service-Frontend (B.4) und derselben Plattform-Rolle (A.15). Die Reihenfolge der folgenden Abschnitte spiegelt nicht Priorität, sondern Reifegrad der Planung: B.1 ist am weitesten ausgearbeitet, B.2 enthält die grundlegendste Neuausrichtung.

---

## B.1 Apps Script — Architektur

### B.1.1 Ausgangslage und Zielsetzung

**Ist-Zustand**

- Ca. **13.000 Apps-Script-Projekte** im Bestand
- **Keine** Governance-, Compliance- oder Security-Kontrolle
- Unklar, was die Skripte tun, auf welche Daten sie zugreifen und wer sie betreibt
- Skripte hängen überwiegend an **Default-GCP-Projekten** — für die Organisation technisch unsichtbar
- Teil eines größeren Citizen-Development-Wildwuchses (parallel dazu: der in B.2 und B.3 behandelte Python- und GCP-Datendienste-Bestand)

**Leitprinzip**

> Nicht unterbinden, sondern organisieren. Ordnung soll durch Struktur entstehen, nicht durch aktives Eingreifen im Einzelfall.

Konkret bedeutet das für diese Architektur:

- **Regulierung nach Kategorie, nie pro Skript** — bei 13.000 Objekten ist Einzelfallprüfung strukturell unmöglich
- **Beobachten vor Blockieren** — Enforcement erst, wenn die Baseline bekannt ist
- **Freiheit in den unteren Risikostufen erhalten** — Kontrolle nur dort, wo Reichweite oder Datensensitivität es rechtfertigen
- **Vererbung statt Pflege** — Berechtigungen über Ordner-/Gruppenstrukturen, die sich selbst auf neue Objekte übertragen

**Zielbild**

Ein „goldener Pfad", der so attraktiv und reibungsarm ist, dass Entwickler ihn freiwillig nutzen — und der gleichzeitig automatisch die Sichtbarkeit und Kontrolle herstellt, die Governance und Compliance brauchen.

### B.1.2 Grundlegende Mechanik: Welche Ebene steuert was

Das zentrale Verständnis für die gesamte Architektur — diese Ebenen sind **voneinander unabhängig** und dürfen nicht vermischt werden:

| Ebene | Steuert | Steuerung über |
|---|---|---|
| **Code-Zugriff** | Wer darf den Skript-Code lesen/ändern | Drive-Freigabe der Skript-Datei |
| **Ausführung/Nutzung** | Wer darf das Skript bzw. die Web-App aufrufen | Apps-Script-Deployment-Einstellungen |
| **Cloud-Plattform** | Welche APIs aktiviert sind, Logs, Consent-Screen, Quotas | GCP-IAM auf dem gebundenen Cloud-Projekt |
| **Datenzugriff (Scope)** | Welche Google-Daten die App anfragen darf | Workspace Admin Console — App Access Control |
| **Externe Ziele** | Welche Nicht-Google-URLs erreichbar sind | Workspace Admin Console — URL-Allowlist |
| **Verteilung** | Wer darf ein Add-on installieren | Workspace Admin Console — Marketplace User Install Settings |

**Wichtigste Konsequenz:** Die Bindung eines Skripts an ein GCP-Projekt ändert **nichts** daran, wer den Code bearbeiten oder das Skript benutzen darf. Sie verschiebt ausschließlich die Cloud-Plattform-Ebene aus dem für uns unsichtbaren, Google-verwalteten Raum in unseren eigenen, organisationsverwalteten Raum.

### B.1.3 Baustein 1: Standard-GCP-Projekt statt Default-Projekt

**Der Unterschied**

| Aspekt | Default-Projekt (heute) | Standard-Projekt (Ziel) |
|---|---|---|
| Sichtbarkeit für Admins | Nein — Owner ist ein Google-Systemaccount (`appsdev-apps-dev-script-auth@system.gserviceaccount.com`); in der Cloud Console i. d. R. nicht auffindbar | Ja — normales Projekt in unserer Org-/Ordner-Hierarchie |
| Cloud Asset Inventory | Nicht enthalten (blinder Fleck) | Erscheint wie jedes andere Projekt |
| Org Policies | Greifen nicht | Greifen automatisch durch Vererbung |
| Ausführungslogs | Nur flüchtig im Editor | Persistent in Cloud Logging, filterbar/exportierbar |
| Error Reporting | Nicht nutzbar | Cloud Error Reporting mit Aggregation |
| Aktivierte APIs | Automatisch und unsichtbar im Hintergrund | Sichtbar unter „APIs & Services", per IAM steuerbar |
| OAuth Consent Screen | Automatisch generiert, nicht anpassbar | Konfigurierbar und einsehbar |
| Kosten/Quota | Nicht zuordenbar | Eigenes Quota, Billing-zuordenbar |
| Mehrere Skripte bündeln | Nicht möglich | **Möglich — zentral für die Skalierung** |

**Kritischer Skalierungsfaktor: Bündelung**

Mehrere Apps-Script-Projekte können sich **ein** Standard-GCP-Projekt teilen. Das ist der Hebel, der aus 13.000 Einzelfällen eine handhabbare Zahl macht:

```
Ziel-Topologie:
  Org
   └── Ordner: Citizen Development
        ├── Ordner: Fachbereich A
        │    └── Standard-Projekt "apps-script-fb-a"  ← 200-400 Skripte
        ├── Ordner: Fachbereich B
        │    └── Standard-Projekt "apps-script-fb-b"  ← 150-300 Skripte
        └── ...
```

Statt 13.000 Konfigurationen entstehen ca. **30–50 verwaltete Einheiten**.

**⚠️ Wichtige Einschränkung: Add-ons lassen sich NICHT bündeln**

Pro Cloud-Projekt existiert **ein** Marketplace-App-Listing, und ein Listing darf **maximal ein** Google Workspace Add-on enthalten.

**→ Für jedes veröffentlichte Add-on ist ein eigenes GCP-Projekt erforderlich.**

Das führt zu einem geteilten Provisionierungsmodell:

| Objekttyp | Modell | Größenordnung |
|---|---|---|
| Normale Skripte (containergebunden, Trigger, interne Web-Apps) — Tier 1/2 | Gebündelt pro Team/Fachbereich | ~30–50 Projekte |
| Veröffentlichte Add-ons — Tier 3 | Ein Projekt pro Add-on | 1:1, realistisch Dutzende |

**Abmildernde Faktoren:**

- Ein einzelnes Workspace-Add-on kann gleichzeitig Gmail, Calendar, Chat, Drive, Docs, Sheets, Slides und Meet erweitern — es braucht also nicht pro Host ein eigenes Add-on
- Andere Integrationstypen (Web-Apps, Drive-Apps, Editor-Add-ons für Docs/Sheets/Slides/Forms) **lassen sich** in einem Listing kombinieren

**Governance-Vorteil:** Eigenes Projekt = eigene OAuth-Client-ID = eigene App-Identität in der API Access Control. Jedes Add-on ist damit individuell scope-steuerbar statt in einem Team-Topf zu verschwinden. Für Tier-3-Objekte ist das die angemessenere Granularität.

**Konsequenz für den Betrieb:** Projektanlage wird ein wiederkehrender Vorgang statt eines Einzelfalls → siehe B.1.16 und B.4.

**Wichtige Nebenbedingungen**

- Der Wechsel Default → Standard ist **nicht umkehrbar**
- Beim Wechsel müssen Advanced Services und APIs **neu aktiviert** werden
- Nutzer müssen **neu autorisieren**
- Advanced Services werden bei Standard-Projekten **nicht mehr automatisch** aktiviert — vergisst der Entwickler die manuelle Aktivierung, bricht das Skript zur Laufzeit mit einer wenig aussagekräftigen Fehlermeldung ab

### B.1.4 Baustein 2: Die drei Gates beim Google-API-Zugriff

Wenn ein Skript einen Google-Dienst aufruft, müssen **alle drei** Bedingungen erfüllt sein:

```
API im Cloud-Projekt aktiviert?
        ↓ ja
Nutzer hat den Scope bewilligt?
        ↓ ja
Admin-Regel erlaubt diesen Scope für diese App?
        ↓ ja
        → Aufruf funktioniert
```

**Gate 1 — API-Aktivierung (GCP-Projekt-Ebene)**

- Steuert, ob die technische Fähigkeit überhaupt existiert
- Bei Standard-Projekten muss die API **manuell** aktiviert werden
- Über IAM steuerbar: wer darf APIs aktivieren
- **Wichtig:** Betrifft primär Advanced Services. Eingebaute Services (`DriveApp`, `GmailApp`, `SpreadsheetApp`) benötigen ebenfalls die zugrundeliegende API, wurden bei Default-Projekten aber automatisch mit aktiviert

**Gate 2 — Nutzer-Consent (Ausführungsebene)**

- Der **ausführende Nutzer** muss den im Manifest deklarierten Scopes zustimmen
- Einmalig, nicht pro Aufruf
- Erneute Zustimmung wird erzwungen, wenn sich der Scope-Umfang ändert → **stiller Rechte-Ausbau ist technisch nicht möglich**
- Der Consent Screen bestimmt nur, **was angezeigt wird** — er ist **kein** technischer Filter für Scopes

> ⚠️ **Häufiges Missverständnis:** Die Scope-Liste im OAuth-Consent-Screen des GCP-Projekts schränkt **nicht** ein, welche Scopes ein Skript anfragen kann. Sie ist Dokumentation/Anzeige für Nutzer und für Googles Verifizierungsprozess. Die Scopes selbst kommen aus dem Skript-Manifest (`appsscript.json`), das über die Drive-Freigabe kontrolliert wird.

**Gate 3 — App Access Control (Workspace Admin Console)**

**Der eigentliche Enforcement-Hebel.**

Pfad: `Admin Console → Sicherheit → Zugriffs- und Datenkontrolle → API-Steuerung → App-Zugriff verwalten`

Jede App (identifiziert über ihre OAuth-Client-ID = das zugrundeliegende Cloud-Projekt) wird eingestuft als:

| Einstufung | Bedeutung |
|---|---|
| **Trusted** | Alle Scopes erlaubt, inkl. restricted; umgeht Context-Aware-Access-Policies |
| **Specific Google data** | Nur die explizit hinterlegten Scopes — **das Zielmodell für uns** |
| **Limited** | Nur nicht-restricted Dienste |
| **Blocked** | Kein Zugriff auf Workspace-Daten |

Fragt eine App einen nicht freigegebenen Scope an, bekommt der Nutzer **keinen** Consent-Dialog — er kann es also gar nicht bewilligen. Echte Sperre, unabhängig vom Manifest-Inhalt.

**Zusätzlich verfügbar:** Domainweite Sperre von *high-risk OAuth scopes* für Gmail und Drive — nur explizit vertrauenswürdige Apps können diese dann noch nutzen.

**Der Skalierungseffekt**

Weil die App-Identität am Cloud-Projekt hängt (nicht am einzelnen Skript), gilt eine Scope-Konfiguration automatisch für **alle** Skripte an diesem Projekt — auch für später hinzukommende.

> 🔍 **Vor Rollout zu verifizieren:** Dass mehrere Apps-Script-Projekte am selben Standard-Projekt in der Admin Console tatsächlich als **eine** App-Identität erscheinen, ist die tragende Annahme dieser Architektur. Sie ist plausibel und durch Googles Dokumentation gestützt, aber nicht abschließend für den aktuellen Stand bestätigt. **Pilotversuch:** 2–3 Testskripte an ein gemeinsames Standard-Projekt hängen, Scope-Einschränkung setzen, prüfen ob nur ein Eintrag in der Admin Console erscheint und die Sperre für alle greift.

### B.1.5 Baustein 3: Kontrolle externer Verbindungen

**URL-Allowlist für Apps Script und Sheets**

Pfad: `Admin Console → Apps → Google Workspace → Drive and Docs → Features and Applications → Importing and fetching from URLs`

- Standardmäßig darf `UrlFetchApp` (und `IMPORTDATA`/`IMPORTXML` in Sheets) **jede** URL ansprechen
- Mit Allowlist: alles andere wird geblockt, nicht erlaubte Aufrufe liefern einen Fehler
- Pro Organisationseinheit oder Gruppe konfigurierbar

**Vorgehen (zwingend in dieser Reihenfolge):**

1. **Erst beobachten:** `Reporting → Audit and investigation → Drive log events`, Filter auf Events „URL Accessed" und „Sheets Import URL" (Operator auf ODER umstellen). Zeigt 6 Monate rückwirkend alle angesprochenen URLs. Export nach Sheets möglich.
2. **Dann Allowlist befüllen** mit den identifizierten, legitimen Zielen
3. **Erst dann aktivieren** — sonst brechen bestehende Workflows unangekündigt

**Was nicht steuerbar ist**

- **Kein VPC/Netzwerk-Zuordnung:** Apps Script läuft in Googles verwalteter Runtime. Es gibt keine Möglichkeit, ein VPC-Netzwerk, eine Region oder einen VPC-Connector festzulegen. Apps Script wird von VPC Service Controls **nicht unterstützt** — kein Service-Perimeter möglich.
- **Netzwerk-Firewall nur als Alles-oder-Nichts:** Blockieren von `script.google.com` / `script.googleusercontent.com` legt Apps Script komplett lahm, inkl. Editor.
- **Keine fixe Quell-IP:** `UrlFetchApp`-Requests kommen aus Googles geteiltem IP-Bereich. Eine IP-Allowlist am eigenen API-Gateway ist daher **keine** verlässliche Absicherung.

### B.1.6 Baustein 4: Least-Privilege im Skript selbst

Diese Muster reduzieren, **wie viel** ein Skript überhaupt anfragen muss. Sie gehören als Checkliste in den goldenen Pfad.

**B.1.6.1 `@OnlyCurrentDoc`**

Bei containergebundenen Skripten (an ein Sheet/Doc/Form/Slide gebunden) beschränkt diese Annotation den Scope auf genau diese eine Datei statt auf das gesamte Drive.

> ⚠️ Wird ausgehebelt, sobald im selben Skript ein Advanced Service aktiviert ist — dann wird wieder der volle Scope erzwungen. **Advanced Services also nur bei echtem Bedarf.**

**B.1.6.2 Explizite Scope-Deklaration im Manifest**

Apps Script leitet Scopes automatisch aus dem Code ab — tendenziell großzügig. Im `appsscript.json` lässt sich das manuell eingrenzen:

```json
{
  "oauthScopes": [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets.currentonly"
  ]
}
```

Risiko: Ein versehentlich entfernter, benötigter Scope bricht die Funktion → Testen erforderlich.

**B.1.6.3 Engere Scope-Varianten wählen**

| Statt | Besser |
|---|---|
| `auth/drive` (alles) | `auth/drive.file` (nur gepickte/erstellte Dateien) |
| `auth/spreadsheets` | `auth/spreadsheets.readonly` bei reinem Lesen |
| `mail.google.com` (Vollmacht) | `gmail.readonly` / `gmail.send` |
| `auth/calendar` | `auth/calendar.readonly` |

**B.1.6.4 Google Picker statt globalem Drive-Zugriff**

Der Picker ist der Mechanismus, mit dem `drive.file` praktikabel wird: Der Nutzer wählt eine Datei aus, Google gewährt dem Skript für **genau diese** Datei Zugriff. Alles andere im Drive bleibt unsichtbar.

**Voraussetzungen im Standard-Projekt:**
- Google Picker API aktivieren
- API-Key erzeugen, per HTTP-Referrer auf `*.google.com` / eigene Domain beschränken

**Implementierung (serverseitig, `Code.gs`):**

```javascript
function showPicker() {
  const html = HtmlService.createHtmlOutputFromFile('picker')
    .setWidth(600).setHeight(425);
  SpreadsheetApp.getUi().showModalDialog(html, 'Datei auswählen');
}

function getOAuthToken() {
  return ScriptApp.getOAuthToken();
}

function processSelectedFile(fileId) {
  const file = DriveApp.getFileById(fileId); // funktioniert dank Picker-Auswahl
  // Weiterverarbeitung
}
```

**Implementierung (clientseitig, `picker.html`):**

```html
<script src="https://apis.google.com/js/api.js"></script>
<script>
  let oauthToken, pickerApiLoaded = false;

  google.script.run.withSuccessHandler(token => {
    oauthToken = token;
    gapi.load('picker', () => { pickerApiLoaded = true; createPicker(); });
  }).getOAuthToken();

  function createPicker() {
    if (!pickerApiLoaded || !oauthToken) return;
    const view = new google.picker.DocsView().setIncludeFolders(true);
    const picker = new google.picker.PickerBuilder()
      .addView(view)
      .setOAuthToken(oauthToken)
      .setDeveloperKey('API_KEY')
      .setCallback(onPicked)
      .build();
    picker.setVisible(true);
  }

  function onPicked(data) {
    if (data.action === google.picker.Action.PICKED) {
      google.script.run.processSelectedFile(data.docs[0].id);
    }
  }
</script>
```

**B.1.6.5 Ausführungs-Identität und Trigger**

- **Web-Apps:** „Als Nutzer ausführen" statt „Als Owner ausführen". Bei „Owner" läuft das Skript für **alle** Nutzer mit den vollen Rechten des Erstellers
- **Installierbare Trigger:** laufen mit den Rechten des Erstellers → keine persönlichen Admin-Accounts, sondern dedizierte Funktions-Accounts mit minimalen Rechten

**B.1.6.6 Scope-Hygiene**

Scopes bleiben im Manifest stehen, auch wenn die auslösende Code-Stelle entfernt wurde. Regelmäßiger Blick auf „Project OAuth Scopes" im Editor bzw. als Teil des Code-Reviews.

### B.1.7 Baustein 5: Der Kontext-Scope-Ansatz (Add-on-Framework)

**Das Problem**

Googles Standard-Scopes sind weitgehend Alles-oder-Nichts: Entweder eine App liest **alle** Mails oder keine. Auf Scope-Ebene existiert kaum inhaltliche Granularität.

**Die Lösung für interaktive Fälle**

Wird das Skript als **Add-on mit Contextual Triggers** gebaut, gibt es abgestufte, temporäre Scopes, die nur an das gerade geöffnete Objekt gebunden sind:

| Scope (Gmail) | Umfang |
|---|---|
| `gmail.addons.current.message.metadata` | Nur Betreff/Absender der offenen Mail |
| `gmail.addons.current.message.action` | Inhalt nur bei aktivem Klick auf eine Add-on-Aktion |
| `gmail.addons.current.message.readonly` | Inhalt + Thread der offenen Mail |
| `gmail.readonly` / `gmail.modify` | Alles, jederzeit — zu vermeiden |

Technisch: Das Add-on erhält keinen dauerhaften Token für das Postfach, sondern einen kurzlebigen Token (`e.gmail.accessToken`) für genau diese Nachricht.

```javascript
function onGmailMessageOpen(e) {
  const accessToken = e.gmail.accessToken;
  GmailApp.setCurrentMessageAccessToken(accessToken);
  const message = GmailApp.getMessageById(e.gmail.messageId);
  // nur diese Nachricht ist zugänglich
}
```

Das gleiche Prinzip existiert auch für Calendar-Add-ons (aktuelles Event), Drive-Add-ons (ausgewählte Dateien) und Editor-Add-ons (aktuelles Dokument).

> 🔍 **Zu verifizieren:** Die exakten Scope-Strings wurden nur für Gmail bestätigt. Für Calendar/Drive/Editor sollten die konkreten Bezeichnungen in Googles Add-on-Dokumentation gegengeprüft werden, bevor sie verbindlich in den goldenen Pfad aufgenommen werden.

**Die Grenze**

Kontext-Scopes funktionieren **nur, wenn ein Mensch aktiv interagiert**. Für zeitgesteuerte Hintergrund-Automatisierung — den Großteil der 13.000 Skripte — gibt es dieses Muster nicht.

**Alternative für unbeaufsichtigte Skripte: Provisionierung statt Scope**

Wenn der Scope keine Filterung erlaubt, verlagert sich die Kontrolle auf **was die ausführende Identität überhaupt sieht**:

| Dienst | Muster |
|---|---|
| **Drive** | Dediziertes Funktionskonto; nur die benötigten Ordner/Dateien teilen. Begrenzung liegt in der Drive-ACL, nicht im Scope |
| **Gmail** | Dediziertes Funktionspostfach, per Filter/Weiterleitung nur mit relevanten Mails befüllt. Der breite Scope ist dann unkritisch, weil das Postfach eng ist |
| **Chat** | Als Chat-App-Bot bauen: sieht strukturell nur Spaces, in die er eingeladen wurde — Space-Mitgliedschaft ist die Granularität |

**Was der Picker nicht kann:** `drive.file` lässt sich **nicht programmatisch** erweitern. Es gibt keinen API-Call, um eine Datei-ID ohne Nutzerklick in den erlaubten Kreis aufzunehmen. Das ist Absicht — sonst wäre der Scope wertlos.

### B.1.8 Baustein 6: Add-ons als Freigabe-Nadelöhr

**Was Google NICHT tut**

> **Interne Add-ons werden von Google nicht geprüft.** Der Verifizierungsprozess für sensible/restricted Scopes gilt ausschließlich für öffentliche Marketplace-Apps. Privat veröffentlichte Apps sind **sofort** im „Internal Apps"-Bereich verfügbar, ungeprüft.

Jede inhaltliche Validierung müssen wir selbst durchführen.

**Was der Add-on-Prozess trotzdem bringt**

| Eigenschaft | Nutzen für Governance |
|---|---|
| Diskreter Publish-Schritt | Ein definierter Moment zum Eingreifen statt fließender Code-Änderung |
| Versionierte Deployments | Installierte Instanzen laufen auf der freigegebenen Version; Änderung erfordert expliziten neuen Deploy |
| Scope-Änderung erzwingt Re-Auth | Sichtbares, im OAuth Token Audit auditierbares Ereignis |
| Install-Gate | **Der eigentliche Hebel** — siehe unten |

**Das Install-Gate**

Pfad: `Admin Console → Apps → Google Workspace Marketplace apps → User Install Settings`

| Einstellung | Wirkung |
|---|---|
| Jede App installierbar | **Kein Nadelöhr** — Entwickler veröffentlicht, Kollegen installieren selbst |
| Nur allowlisted Apps | Governance-Gruppe entscheidet pro App |
| Nur Admin-Install | Governance-Gruppe rollt aktiv für OU/Gruppe aus |

> ⚠️ **Sofort prüfen:** Steht diese Einstellung noch auf dem Auslieferungswert („jede App"), existiert das Nadelöhr faktisch nicht — der gesamte Add-on-Governance-Ansatz hätte dann keinen Ankerpunkt.

**Testen ohne Marketplace**

Entwickler können ihr Add-on vollständig testen, ohne es zu veröffentlichen:

- **Editor-Add-ons:** `Deploy → Test deployments` → Typ „Editor Add-on" → Testdatei wählen → `Save test`
- **Workspace-Add-ons (Gmail/Chat/Drive):** `Deploy → Test deployments` → Typ „Google Workspace Add-on" → `Install`

Das Add-on erscheint sofort in der echten Oberfläche (ggf. Tab-Reload).

> ⚠️ Um andere testen zu lassen, benötigen diese **Editor-Zugriff** auf das Skript-Projekt — also auch Änderungsrechte. Für die Testphase akzeptabel, für Produktion nicht.
>
> Limits von Test-Deployments: keine installierbaren Trigger, geteilte Properties nicht zuverlässig über mehrere Runs.

**Ein Listing pro Cloud-Projekt**

- Die Marketplace-SDK-Konfiguration hängt am Cloud-Projekt → **ein App-Listing pro Projekt**
- Ein Listing darf **maximal ein** Google Workspace Add-on enthalten
- Weitere Integrationstypen (Web-App, Drive-App, Editor-Add-ons) sind im selben Listing kombinierbar

**Fallstrick beim Kombinieren:** Der Consent Screen listet **alle** Scopes **aller** Integrationen des Listings zusammen. Ein Nutzer, der nur die Sheets-Funktion braucht, muss trotzdem den Scopes der Web-App zustimmen — das läuft dem Least-Privilege-Ziel zuwider.

Zusätzlich: Kommt eine Integration mit neuen Scopes zu einem bereits domain-installierten Listing hinzu, müssen Admins erst neu autorisieren; bis dahin werden Nutzer einzeln gefragt.

**→ Integrationen nur bündeln, wenn sie denselben Scope-Bedarf haben.** Andernfalls getrennte Listings, auch wenn das mehr Projekte bedeutet.

**Marketplace-Bereitstellung: Schrittfolge**

1. Standard-GCP-Projekt vorhanden (eigenes Projekt je Add-on, siehe B.1.3)
2. **Google Workspace Marketplace SDK** in der Cloud Console aktivieren
3. **OAuth Consent Screen** ausfüllen (Name, Logo, Support-Kontakt) — Pflicht auch intern
4. Im Skript-Editor: `Deploy → New deployment` → liefert **Deployment-ID** und Versionsnummer
5. Marketplace SDK → Tab **App Configuration**:
   - *App Visibility*: Private (nur eigene Domain)
   - *Installation Settings*: individual / admin install
   - *App Integration*: Zielprodukt + Deployment-ID + Version aus Schritt 4
   - *OAuth Scopes*: müssen mit Manifest und Consent Screen übereinstimmen
6. **Store Listing** ausfüllen
7. Veröffentlichen → sofort im Internal-Apps-Bereich sichtbar
8. **Install-Gate:** Governance-Freigabe entscheidet, ob es jemand installieren kann

Schritte 1–7 sind reines Self-Service. **Nur Schritt 8 erfordert Governance-Beteiligung** — dort gehört die inhaltliche Prüfung hin.

**Die verbleibende Lücke: Code-Ablage**

**Marketplace-Veröffentlichung kopiert keinen Code.** Das Skript-Projekt bleibt im Drive des Entwicklers. Wer Editor-Rechte hat, kann es weiter ändern — nach der Freigabe, ohne dass es zwangsläufig auffällt (solange keine neuen Scopes nötig werden).

**Robuste Lösung — CI/CD-Trennung:**

```
Entwickler-Workspace          Governance-kontrollierte Produktion
─────────────────────         ──────────────────────────────────
Eigenes Skript-Projekt   →    Git (Azure DevOps)
clasp push/pull               ↓ PR + Review + Snyk/Secret-Scan
freies Experimentieren        ↓ Pipeline
                              Produktions-Skriptprojekt
                              (Owner: Governance-Gruppe)
                              ↓
                              Deployment + Marketplace-Freigabe
```

- Entwicklung über **clasp** (Apps-Script-CLI) gegen ein Git-Repo
- Produktions-Skriptprojekt gehört einer Governance-kontrollierten Gruppe, nicht der Person
- Deployment nur über die Pipeline nach Merge
- **Nutzt die bereits etablierte Azure-DevOps-Pipeline** (inkl. Secret-/Snyk-Scans) statt einer Neuentwicklung — dieselbe Pipeline, die auch Python bedient (B.2.5)

### B.1.9 Baustein 7: Alternate Runtimes (HTTP-Add-ons) für Hochrisiko-Fälle

**Prinzip**

Statt Code in Googles Runtime auszuführen, wird ein **HTTPS-Endpoint** registriert. Google sendet bei Nutzerinteraktion einen POST mit JSON-Event; der eigene Server antwortet mit JSON, das die UI-Karten beschreibt. Sprache frei wählbar. Über die „Google Workspace Add-ons Cloud API" sogar ganz ohne Apps-Script-Projekt verwaltbar.

**Netzwerkfluss**

**Google ruft uns an, nicht umgekehrt.** Der Endpoint muss von Googles Servern aus über öffentliches HTTPS erreichbar sein — klassisches Webhook-Muster (vgl. Stripe/GitHub-Webhooks). Gültiges TLS-Zertifikat, Ingress in DMZ/hinter Reverse Proxy.

> 🔍 **Zu klären:** Eine private Konnektivitätsoption (VPN/Interconnect statt öffentlicher Erreichbarkeit) ist in der Dokumentation nicht auffindbar. Vor einer Entscheidung explizit mit Google bzw. dem Netzwerkteam gegenprüfen.

**Berechtigungsstruktur — zwei getrennte Ebenen**

**Ebene 1: Ist der Aufruf legitim?**

Google signiert jeden Request mit einem ID-Token (JWT) im `Authorization: Bearer`-Header. Zu verifizieren sind Signatur, Audience (= die Endpoint-URL) und Aussteller. Service-Account-E-Mail und OAuth-Client-ID finden sich im Marketplace SDK unter `HTTP Deployments → Authorization Resource`. Die Google-Auth-Bibliotheken (Node/Python/Java/Go) bieten dafür `verifyIdToken()`.

Konfigurierbar über `authorizationHeader` im Deployment:

| Option | Aussage |
|---|---|
| System-ID-Token | „Das ist Googles Add-on-Infrastruktur für dieses Add-on" |
| User-ID-Token | Zusätzlich: welcher Nutzer hat ausgelöst |
| Kein Header | Nur für unkritische Fälle |

**Ebene 2: Zugriff auf Nutzerdaten**

Im Event-Payload (`authorizationEventObject`) wird zusätzlich ein Token für den Zugriff im Namen des Nutzers mitgeliefert — analog zu `e.gmail.accessToken`. Damit ruft der eigene Server die Google-APIs auf. **Die gesamte Scope-/Consent-/Admin-Console-Logik gilt unverändert weiter.**

> 🔍 **Zu verifizieren:** Ob dieser Datenzugriffs-Token im HTTP-Modell ein JWT oder (wie im klassischen Apps-Script-Modell) ein opaker OAuth-Token ist, war aus der Dokumentation nicht zweifelsfrei zu klären. **Vorgehen:** Test-Deployment aufsetzen, eingehenden Payload einmal roh loggen, Struktur prüfen (drei punktgetrennte Base64-Teile = JWT). Relevant, weil die zentrale Verifizierungslogik in der Pipeline exakt wissen muss, was sie erhält.

**Zusatznutzen**

HTTP-Add-ons unterstützen **Granular OAuth Consent** — Nutzer können gezielt einzelne Scopes bewilligen statt alles-oder-nichts.

**Strategische Einordnung**

Der stärkste verfügbare Hebel: Bei Tier-3-Fällen läuft die eigentliche Logik auf einer Plattform, die wir kontrollieren (Pipeline, Scans, Versionierung) — Apps Script wird zum dünnen Registrierungs-Stub. Der Code verlässt den unkontrollierten Raum vollständig.

**Aber:** deutlich höherer Engineering-Aufwand. Gezielt für die höchste Risikostufe, **nicht** als Standard für alle 13.000 Skripte.

### B.1.10 Sichtbarkeit und Monitoring

Es existiert **kein einziges Dashboard**. Die Quellen müssen kombiniert werden:

| Quelle | Pfad | Liefert |
|---|---|---|
| Drive log events | `Reporting → Audit and investigation → Drive log events`, Filter Dokumenttyp „Google Script" | Aktionen an Skript-Projekten |
| Apps-Script-Report | `Reporting → Reports → Apps Reports → Apps Script` | Nutzerzahlen, Projekte/Tag, alle Ausführungen; 6 Monate; exportierbar |
| URL-Events | Drive log events, Events „URL Accessed" / „Sheets Import URL" | Angesprochene externe URLs |
| OAuth Token Audit | Audit and investigation | Welche App/welcher Scope wurde bewilligt |
| Dienst-Logs | Drive-/Gmail-/Calendar-Protokollereignisse | Konkrete Aktionen (Filter nach Akteur nötig) |
| Cloud Logging | Cloud Console (nur Standard-Projekt) | `console.log`, Exceptions, Error Reporting |
| Cloud Audit Logs | Cloud Console, pro API zu aktivieren | Einzelne API-Calls (Admin Activity kostenfrei, Data Access kostenpflichtig) |
| Cloud Asset Inventory | Cloud Console | Standard-Projekte als Assets |

**Bekannte Blindstellen**

- **Kein Call-Graph** „welches Skript ruft welches Skript" — muss aus OAuth Token Audit + Cloud Audit Logs rekonstruiert werden
- Ob **eingebaute Services** (`DriveApp`, `GmailApp`) Cloud-Audit-Log-Einträge im gebundenen Projekt erzeugen, ist **unbestätigt** — vermutlich nicht. Für diese bleiben die Workspace-Dienst-Logs die verlässlichere Quelle 🔍
- Ob **Apps-Script-Web-App-URLs** (`script.google.com/macros/.../exec`) von der URL-Allowlist erfasst werden, ist **unbestätigt** — Google-eigene Domains könnten ausgenommen sein. Zu testen 🔍
- **Cloud Audit Logs sind nicht rückwirkend aktivierbar** — was vor Aktivierung passierte, ist nicht rekonstruierbar

### B.1.11 Requirements

**Google-Workspace-Editionen**

| Funktion | Benötigte Edition |
|---|---|
| URL-Allowlist (externe Verbindungen) | Frontline Plus, Business Plus, Enterprise Standard/Plus, Education Standard/Plus, Enterprise Essentials Plus |
| Monitoring/Restriktion von OAuth-Scopes | Enterprise, Education Standard, Education Plus |
| Security Investigation Tool | Enterprise-Tier |

**→ Editionsstand vorab verifizieren.** Ohne die passende Edition entfallen zentrale Bausteine dieser Architektur.

**Admin-Berechtigungen**

- Drive & Docs bzw. Service Settings (URL-Allowlist)
- Google Workspace Marketplace (Install-Settings, Allowlist)
- Audit & Investigation (Log-Auswertung)
- Service Settings (API-Steuerung)
- Super-Admin für einige Marketplace-Operationen

**GCP-Voraussetzungen**

- Ordnerstruktur in der Org-Hierarchie, passend zur Fachbereichsstruktur — dieselbe Struktur, die B.2 für Python-Compute-Projekte und B.3 für Daten-Projekte verwendet
- Google Groups für Rollenvergabe (keine Einzelpersonen)
- Governance-Viewer-Rolle **auf Ordnerebene** → vererbt sich automatisch auf neue Projekte
- Billing-Zuordnung für die Team-Projekte
- Org Policies für erlaubte APIs

**Prozessuale Voraussetzungen**

- Definierte Risiko-Tiers (Abschnitt A.8, umgesetzt in B.1.12)
- Benanntes Prüfteam mit Kapazität für Tier-2/3-Reviews
- Git-Repos + Pipeline-Anbindung (Azure DevOps, vorhanden)
- Dedizierte Funktions-Accounts für Automatisierungen
- Kommunikationsplan Richtung Fachbereiche

### B.1.12 Risiko-Tiering (Apps-Script-spezifische Umsetzung)

Für die tägliche Praxis wird das vollständige vierdimensionale Profil aus A.8 auf zwei leicht erhebbare Proxy-Achsen verdichtet — das macht die Einstufung bei 13.000 Objekten praktikabel, ohne die Tier-Definition selbst zu verändern:

| Achse | Ausprägungen | Korreliert primär mit |
|---|---|---|
| **Reichweite** | Nur Owner → Team/Abteilung → org-weit deployte Web-App/Add-on | Dimension MB, UR |
| **Datenzugriff** | Rein persönliche Auswertung → Fachbereichsdaten → Personendaten/sensible Scopes | Dimension DS |

| Tier | Merkmal | Governance |
|---|---|---|
| **1** | Persönliche Nutzung, keine sensiblen Scopes | Nur Sichtbarkeit. Entwickler bleibt Owner. Keine Einschränkung |
| **2** | Team-Reichweite oder Fachbereichsdaten | Scope-Allowlist am Team-Projekt. Review bei Scope-Erweiterung |
| **3** | Org-weit oder sensible/restricted Scopes | Governance hält Cloud-Projekt-Owner. Pipeline-Deployment. Install-Gate. Ggf. Alternate Runtime |

**Verhältnis zu A.8:** Diese Zwei-Achsen-Heuristik ist eine **Erhebungsvereinfachung für Apps Script**, kein zweites Tier-Modell. Bei Grenzfällen — insbesondere wenn Reichweite/Datenzugriff kein eindeutiges Bild ergeben — entscheidet das vollständige Profil nach A.8.5.

**Compliance-Anschluss:** Die Reichweiten-Achse korreliert direkt mit dem von der Compliance-Abteilung genannten Kriterium „Einfluss auf Arbeitsprozesse/-abläufe der Mitarbeiter". Ein Tier-1-Skript, das nur der Owner nutzt, hat keinen Prozesseinfluss; ein org-weites Tier-3-Tool sehr wohl. Das liefert die Grundlage für den „goldenen Pfad", der eine Einzelvorlage beim Betriebsrat pro App vermeidet: **Der Tier bestimmt das Verfahren, nicht die einzelne App.**

### B.1.13 Stufenplan

**Phase 0 — Inventur, read-only (Wochen 1–3)**

- Drive log events + Apps-Script-Report auswerten: Owner, letzte Ausführung, Häufigkeit
- Aktive von toten Skripten trennen
- **Erwartung:** 60–80 % des Bestands seit Monaten/Jahren inaktiv → Problemmasse sinkt drastisch, ohne jeden Konflikt
- Editionsstand und aktuelle Admin-Console-Einstellungen prüfen (insb. Marketplace User Install Settings)

**Phase 1 — Tiering**

- Verbleibende aktive Skripte nach Reichweite/Datenzugriff klassifizieren
- Ergebnis: Handvoll Tiers statt 13.000 Einzelfälle
- Abstimmung der Tier-Definition mit Compliance und Betriebsrat

**Phase 2 — Beobachten ohne Blockieren**

- URL-Logging aktivieren, Allowlist-Enforcement **aus**
- OAuth Token Audit als Dauerlauf
- Baseline erheben: welche Scopes, welche externen Ziele sind real im Einsatz
- **Rein passiv — kein Entwickler merkt etwas**

**Phase 3 — Goldener Pfad etablieren**

- Ordnerstruktur + Team-Standard-Projekte anlegen
- Pilotversuch zur App-Identitäts-Bündelung (siehe B.1.4) 🔍
- Standard-Projekt als empfohlenen Weg anbieten, gekoppelt an das gemeinsame Self-Service-Frontend (B.4)
- **Keine Zwangsmigration** — „Migration on touch" nach A.16
- Least-Privilege-Checkliste (B.1.6) als Skript-Vorlage bereitstellen
- **Läuft parallel zum Rollout von B.2 und B.3** (Details Teil C.3) — kein sequenzieller Nachzug

**Phase 4 — Gezieltes Enforcement**

- Scope-Allowlist („Specific Google data") pro Team-Projekt — zuerst Tier 3, dann Tier 2
- URL-Allowlist scharf schalten, **nur** für hohe Tiers
- Marketplace Install-Gate aktivieren
- Verwaiste Skripte (Owner ausgeschieden, lange inaktiv) stilllegen
- **Einziger Schritt mit echtem Eingriff — bewusst spät und eng begrenzt**

**Phase 5 — Neuanlagen strukturell sauber**

- Neue Projekte laufen automatisch durch den goldenen Pfad
- Vererbung über Ordnerstruktur sorgt für Selbsterhalt
- Bestand wächst nicht mehr unkontrolliert nach

### B.1.14 Impact auf die Entwickler

**Was sich NICHT ändert**

- Freies Entwickeln im Apps-Script-Editor
- Code-Zugriff weiterhin über Drive-Freigabe
- Testen jederzeit ohne Freigabeprozess (Test-Deployments)
- Tier-1-Skripte (persönliche Nutzung) bleiben vollständig unreguliert
- Kein Skript wird zwangsmigriert

**Was sich ändert — nach Tier**

| | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| Cloud-Projekt-Owner | Entwickler | Entwickler | Governance |
| Neue API aktivieren | selbst | selbst | Anfrage |
| Neuen Scope nutzen | frei | innerhalb Allowlist | Review |
| Externe URL | frei | Allowlist | Allowlist |
| Deployment | selbst | selbst | Pipeline |
| Verteilung an Nutzer | — | Install-Gate | Install-Gate + Review |

**Konkrete Reibungspunkte, offen zu kommunizieren**

1. **Advanced Services brechen nach Migration**, wenn die API nicht manuell aktiviert wurde — mit unklarer Fehlermeldung. → Migrationsanleitung mit Checkliste bereitstellen.
2. **Re-Authorization nach Projektwechsel** — Nutzer müssen erneut zustimmen. → Vorab ankündigen.
3. **Scope-Einschränkung kann funktionierende Skripte brechen**, wenn die Baseline unvollständig war. → Deshalb Phase 2 (Beobachten) nicht überspringen.
4. **Pipeline-Deployment ist langsamer** als „Speichern im Editor". → Nur für Tier 3, wo es gerechtfertigt ist.
5. **Picker-Muster erfordert Umbau** bestehender Skripte. → Nicht rückwirkend erzwingen, nur für Neuentwicklung empfehlen.

**Der Deal, den wir anbieten**

> Wer im goldenen Pfad arbeitet, bekommt: persistente Logs, Error Reporting, ein geteiltes Team-Projekt ohne eigene Einrichtung, Pipeline mit Security-Scans, und — der wichtigste Punkt — **eine Vorab-Freigabe für seinen Tier, statt jede App einzeln vorlegen zu müssen.**
>
> Das ist die Gravitation: Der geregelte Weg ist schneller als der ungeregelte.

### B.1.15 Offene Punkte — vor Rollout zu verifizieren

| # | Punkt | Warum kritisch | Vorgehen |
|---|---|---|---|
| 1 | Mehrere Skripte an einem Standard-Projekt = **eine** App-Identität in der Admin Console | Tragende Annahme der gesamten Skalierung | Pilot: 2–3 Skripte, gemeinsames Projekt, Scope-Sperre setzen, Admin Console prüfen |
| 2 | Aktueller Stand „Marketplace User Install Settings" | Ohne Gate kein Nadelöhr | Admin Console prüfen |
| 3 | Workspace-Editionsstand | Bestimmt, welche Bausteine überhaupt verfügbar sind | Lizenzübersicht prüfen |
| 4 | Erzeugen eingebaute Services Cloud-Audit-Log-Einträge? | Bestimmt, ob Cloud Audit Logs ein lückenloser Trail sein können | Testskript mit `DriveApp` an Standard-Projekt, Data Access Logs aktiviert |
| 5 | Werden Apps-Script-Web-App-URLs von der URL-Allowlist erfasst? | Bestimmt, ob Skript-zu-Skript-Aufrufe kontrollierbar sind | Testaufruf mit aktiver Allowlist |
| 6 | Token-Format im HTTP-Add-on-Payload (JWT vs. opak) | Bestimmt die Verifizierungslogik in der Pipeline | Test-Deployment, Payload roh loggen |
| 7 | Exakte Kontext-Scope-Strings für Calendar/Drive/Editor | Nur Gmail wurde bestätigt | Add-on-Doku pro Dienst gegenprüfen |
| 8 | Private Konnektivität für Alternate-Runtime-Endpoints | Bestimmt, ob echtes On-Prem ohne öffentliche Exposition möglich ist | Google/Netzwerkteam anfragen |
| 9 | Ist die **Marketplace-SDK-App-Konfiguration** per API setzbar? | Bestimmt den Automatisierungsgrad der Add-on-Provisionierung (B.1.16) | API-Referenz prüfen, Testautomatisierung |
| 10 | Ist die **Scope-Allowlist der API Access Control** per API setzbar? | Ohne API bleibt ein manueller Schritt pro Projekt/Add-on | Admin SDK prüfen |

### B.1.16 CI/CD-gesteuerte Provisionierung der GCP-Projekte

**Warum das relevant wird**

Solange GCP-Projekte Einzelfälle waren, war manuelle Anlage vertretbar. Mit dieser Architektur ändert sich das:

- **Pro veröffentlichtem Add-on ein eigenes Projekt** (B.1.3) — Projektanlage wird ein wiederkehrender Vorgang
- Jedes Team-Projekt muss identisch konfiguriert sein, damit Governance-Vererbung greift
- Von Hand angelegte Projekte landen erfahrungsgemäß im falschen Ordner, ohne Governance-Viewer, mit zu vielen aktivierten APIs — jede Abweichung erzeugt später einen Sonderfall

**Kernargument:** Governance, die auf Vererbung durch Struktur setzt, funktioniert nur, wenn die Struktur zuverlässig entsteht. Manuelle Anlage untergräbt das Prinzip an der Wurzel.

**Was provisioniert werden sollte**

| Element | Wirkung |
|---|---|
| Projekt im korrekten Ordner | Erbt Org Policies und Governance-Sichtbarkeit automatisch |
| IAM-Bindings über Google Groups | Tier-abhängige Rollenverteilung, keine Einzelpersonen |
| API-Aktivierung | Nur freigegebene APIs — Gate 1 wird strukturell durchgesetzt |
| Labels/Metadaten | Owner, Fachbereich, Tier, Kostenstelle — macht künftige Inventuren auswertbar statt spekulativ |
| OAuth-/Marketplace-Konfiguration | Soweit per API möglich (offene Punkte 9/10 in B.1.15) |
| Apps-Script-Deployment via clasp | Aus dem Repo, nicht aus dem persönlichen Drive |

**Compliance bis in die GCP-Projekte hinein**

Die bisher beschriebenen Kontrollen (Scopes, URL-Allowlist, Install-Gate) wirken auf der Workspace-Ebene. Sie sagen nichts darüber aus, was **innerhalb** des zugehörigen GCP-Projekts passiert. Compliance, die nur bis zur Workspace-Grenze reicht, lässt genau die Ebene ungeprüft, auf der die eigentlichen Berechtigungen entstehen.

Über die Pipeline wird das GCP-Projekt selbst zum kontrollierten, auditierbaren Artefakt: Jede Änderung an APIs, IAM oder Service Accounts ist ein Commit mit Reviewer und Historie statt eines Klicks in der Console.

Die Projekt-Provisionierung ist bewusst nicht als Apps-Script-Sonderlösung gebaut, sondern als **gemeinsame Grundlage für alle Citizen-Development-Kontexte** — B.2, B.3 und B.4 setzen das um. Apps Script ist der Anlass, nicht der Geltungsbereich.

**Anknüpfungspunkte im Bestand**

- **Azure-DevOps-Pipeline** (inkl. Secret- und Snyk-Scans) ist etabliert — keine Neuentwicklung nötig, nur Erweiterung um GCP-Provisionierung und, für Python, um Container-Build (B.2.5)
- Das **Self-Service-Frontend** (B.4) ist technologieübergreifend für alle drei Domänen konzipiert, nicht nur für Python

**Der strategische Effekt**

Wenn ein korrekt konfiguriertes Projekt über Self-Service in Minuten verfügbar ist, während der ungeregelte Weg Rückfragen und Wartezeit bedeutet, wählen Entwickler den goldenen Pfad freiwillig. Governance entsteht dann als Nebenprodukt der Bequemlichkeit — genau das angestrebte Gravitationsprinzip, ohne dass etwas verboten werden muss.

### B.1.17 Anhang: Was nachweislich NICHT geht

Zur Vermeidung von Fehlplanungen — diese Optionen wurden geprüft und scheiden aus:

- **VPC-Zuordnung für Apps Script** — keine Netzwerk-/Regionszuordnung möglich
- **VPC Service Controls für Apps Script** — nicht unterstützt, kein Service-Perimeter
- **Fixe Quell-IP für UrlFetchApp** — Googles geteilter IP-Bereich; IP-Allowlists am Gateway sind keine verlässliche Absicherung
- **Consent Screen als Scope-Filter** — reine Anzeige/Dokumentation, kein technischer Filter
- **Google-Review interner Add-ons** — findet nicht statt
- **Programmatische `drive.file`-Erweiterung** — kein API-Call ersetzt den Nutzerklick im Picker
- **Selektives Firewall-Blocking einzelner Skripte** — auf Netzwerkebene nur alles oder nichts
- **Rückwechsel Standard → Default-Projekt** — irreversibel
- **Kontext-Scopes für Hintergrund-Automatisierung** — setzen zwingend Nutzerinteraktion voraus
- **Mehrere Add-ons in einem Cloud-Projekt** — ein Listing pro Projekt, ein Workspace-Add-on pro Listing

---

## B.2 Python — Kubernetes-natives Golden Path

### B.2.0 Ausgangslage

- Fachbereiche entwickeln Python-Anwendungen lokal und verteilen sie überwiegend als kompilierte `.exe`-Datei, gebaut über ein bestehendes CI/CD-Framework
- Daneben existieren Python-Skripte, die ohne Kompilierung direkt lokal oder auf Fachbereichs-Servern laufen — interaktiv gestartet oder über lokale Scheduler (z. B. Windows Task Scheduler, Cronjobs) unbeaufsichtigt
- Ein GCP-Datendienste-Stack (BigQuery, Cloud Storage) wird von denselben Fachbereichen bereits genutzt (B.3), bislang jedoch **ohne eigene Compute-Komponente** — Python-Ausführung selbst findet aktuell nicht in GCP statt
- Damit ist der heutige Zustand exakt der in A.9.3/Teil C.1 als strukturell ausgeschlossen beschriebene Fall: K4, K5, K6, K7 und K9 sind nicht erfüllbar, sobald ein Prozess Tier 3 erreicht (vgl. A.9.4-Beispielrechnung)

### B.2.1 Zielbild und Geltungsbereich

**Geltungsbereich:** Jede lokale Python-Anwendung eines Fachbereichs — ob heute als `.exe` verteilt oder nicht — sowie jeder unbeaufsichtigt/geplant laufende Python-Job (Scheduler, Cronjob). Der Geltungsbereich ist damit bewusst **weiter** gefasst als „nur das, was heute zu `.exe` kompiliert wird".

**Zielbild:** `.exe`-Verteilung wird **abgelöst**, nicht nur abgesichert. Ziel ist verwaltete, cloud-seitige Ausführung. Das ist die konsequenteste der denkbaren Zielrichtungen — sie schreibt die in A.9.3/Teil C.1 dokumentierten strukturellen Ausschlüsse einer lokalen Python-Lösung im Kern neu, statt sie durch kompensierende Maßnahmen nur abzumildern.

**Rollout:** Parallel zu den Apps-Script-Phasen (B.1.13), nicht nachgelagert — ein gemeinsamer Stufenplan (Teil C.3).

### B.2.2 Warum kein GCP-Managed-Compute (Cloud Run, Cloud Functions, Cloud Scheduler)

Cloud Run, Cloud Functions und Cloud Scheduler sind aus Datenschutzgründen für diesen golden Path **nicht vorgesehen** — diese Entscheidung beruht auf einer internen Datenschutzbewertung, die dieses Dokument nicht im Einzelnen reproduziert. Sie betrifft sowohl den interaktiven Pfad (Cloud Run) als auch den geplanten/unbeaufsichtigten Pfad (Cloud Functions, Cloud Scheduler) — es handelt sich nicht um eine punktuelle Einschränkung nur des interaktiven Falls.

**Konsequenz:** Compute für Python-Workloads läuft ausschließlich auf **Google Kubernetes Engine (GKE)**, die die Organisation selbst betreibt und deren Konfiguration — anders als bei vollständig verwalteten Serverless-Produkten — im eigenen Verantwortungsbereich liegt.

> Diese Festlegung ist eine Rahmenbedingung dieses Dokuments, keine technische Notwendigkeit — GKE ist hier nicht „die bessere Technologie", sondern die Technologie, die die datenschutzrechtliche Bedingung erfüllt, unter der Python-Compute in GCP überhaupt zulässig ist. Das ist eine unmittelbare Anwendung von A.8.1: Der Sollzustand bestimmt die zulässige Technik, nicht umgekehrt.

### B.2.3 Compute-Architektur: Kubernetes-Primitive

Statt eines einzelnen Ausführungsmodells für alle Fälle wird nach Lauftyp unterschieden — dasselbe Telemetriefeld, das ohnehin am Tool-Objekt erfasst wird (A.6), steuert die Zuordnung:

| Lauftyp (aus Tool-Objekt-Telemetrie) | Kubernetes-Primitiv | Beispiel |
|---|---|---|
| Interaktiv / getriggert durch Nutzeraktion | **Deployment + Service** | Internes Web-Tool, das ein Fachbereich aufruft |
| Unbeaufsichtigt / zeitgesteuert | **CronJob** | Nächtlicher Datenabgleich, wöchentlicher Report |
| Einmaliger Lauf ohne feste Wiederholung | **Job** | Einmalige Migration, Ad-hoc-Auswertung |

Diese Zuordnung ist eine reine Technikroutung (A.6) — sie verändert die Tier-Berechnung nicht, sondern bestimmt nur, welches Kubernetes-Objekt ein Tool-Objekt bei der Bereitstellung erhält.

### B.2.4 Cluster- und Projekttopologie

**Compute und Daten in getrennten Projekten, IAM-verknüpft:**

```
Org
 └── Ordner: Citizen Development
      ├── Ordner: Fachbereich A
      │    ├── Standard-Projekt "apps-script-fb-a"   (B.1)
      │    ├── Standard-Projekt "python-fb-a"         ← GKE-Cluster dieses Fachbereichs
      │    └── Standard-Projekt "data-fb-a"           ← BigQuery/GCS (B.3)
      ├── Ordner: Fachbereich B
      │    ├── Standard-Projekt "apps-script-fb-b"
      │    ├── Standard-Projekt "python-fb-b"
      │    └── Standard-Projekt "data-fb-b"
      └── ...
```

Compute (`python-fb-x`) und Daten (`data-fb-x`) liegen bewusst in **getrennten** Projekten statt in einem gemeinsamen Blob. IAM-Bindings verknüpfen sie: Der GKE-Cluster in `python-fb-x` erhält über Workload Identity (B.2.7) gezielte, auf einzelne Deployments herunterskalierte Berechtigungen auf Datasets/Buckets in `data-fb-x` — nicht projektweiten Zugriff. Das schärft K1 (A.9.2): Compute- und Datenzugriff werden unabhängig voneinander granular vergeben.

**Ein Cluster je Fachbereich, Dev und Prod getrennt darin:**

```
Standard-Projekt "python-fb-a"
 └── GKE-Cluster "python-fb-a"
      ├── Namespace/Node-Pool: dev        ← Notebooks, Code-Server-Workspaces
      └── Namespace/Node-Pool: prod       ← Deployments, CronJobs, Jobs
```

Diese Trennung **innerhalb** eines gemeinsamen, fachbereichsweiten Clusters erfüllt K5 (Trennung Entwicklung/Produktion, A.9.2) ohne die Kosten- und Betriebslast getrennter Cluster je Fachbereich und Umgebung. Ein experimenteller Notebook-Prozess kann Ressourcen des `dev`-Node-Pools beanspruchen, ohne den `prod`-Node-Pool zu beeinträchtigen.

### B.2.5 CI/CD-Pipeline

Die bestehende, bereits für Apps Script genutzte **Azure-DevOps-Pipeline** (inkl. Secret- und Snyk-Scans, B.1.8) wird um Python-Container-Build und GKE-Deployment erweitert — keine neue Pipeline-Landschaft.

```
Ephemerer Workspace (Notebook/Code-Server)
        │  git commit / push
        ▼
   Git-Repo (Azure DevOps)
        │
        ▼
   Azure-DevOps-Pipeline
        ├─ Security-/Secret-Scan (Snyk)          ← hartes Gate, alle Tiers
        ├─ Tests / Lint                          ← Empfehlung, kein Gate
        ├─ Container-Build (auf zentralem Basis-Image, B.2.9)
        └─ Push → Artifact Registry
        │
        ▼
   Deployment auf GKE (python-fb-x)
        ├─ Deployment + Service   (interaktiv)
        └─ CronJob / Job          (geplant/einmalig)
```

**Deploy-Gates:** Der Security-/Secret-Scan ist für **alle** Tiers ein hartes Gate — kein Deployment ohne grünen Scan-Lauf. Tests und Lint bleiben Empfehlung, kein Blocker. Diese Asymmetrie ist bewusst: Sie schließt die eine Lücke, die unmittelbar an ein Schicht-2-Verbot grenzt (Secrets, bekannte Schwachstellen), ohne den golden Path durch Qualitätsanforderungen zu verlangsamen, die keine Governance-Funktion haben.

### B.2.6 Entwicklungsumgebung: Notebooks und Code-Server, vollständig browserbasiert

**Kein lokales Tooling.** Es gibt keinen lokal zu installierenden Client, keine CLI, kein `git clone` auf den eigenen Laptop. Der gesamte Entwicklungsfluss läuft im Browser, gehostet auf demselben GKE-Cluster, der später auch die Produktion trägt (`dev`-Namespace/Node-Pool, B.2.4).

**Zwei parallele Einstiegsformen für unterschiedliche Reifegrade:**

| Umgebung | Zielgruppe | Charakter |
|---|---|---|
| **Notebooks** (Jupyter-artig) | Einstieg, exploratives Arbeiten, Datenanalyse | Niedrige Einstiegshürde, zellbasiert, sofort lauffähig |
| **Code-Server** (VS-Code-artig) | Vollwertige Anwendungsentwicklung | Vollständige IDE-Erfahrung, Debugging, Projektstruktur |

Beide sind gleichrangig vorgesehen, nicht als Vorstufe zueinander — ein Fachbereichsmitarbeiter kann direkt mit Code-Server beginnen, wenn die Aufgabe das nahelegt.

**Workspaces sind ephemer:**

- Jede Session startet **frisch aus Git** — es gibt kein persistentes Workspace-Volume, das über das Ende einer Session hinaus erhalten bleibt
- Alles, was nicht committed und gepusht wurde, existiert nach Sitzungsende nicht mehr
- Diese Entscheidung ist eine unmittelbare, technische Umsetzung von Prinzip P1 und der K3-Anforderung: Git wird nicht empfohlen, sondern durch die Architektur selbst zur **einzig möglichen** Quelle der Wahrheit. Das genau war der strukturelle Mangel der alten `.exe`-Praxis (K3: „technisch möglich, organisatorisch selten") — mit ephemeren Workspaces ist Organisationslaxheit gar nicht mehr möglich

**Zugriff:** Authentifizierung über die zentrale Unternehmensidentität (dieselbe, die Schicht 2 in A.13.2 als verpflichtend voraussetzt) — kein separates Login, kein VPN-Zwang; der Zugriff läuft über einen identitätsbasierten Proxy vor dem Cluster.

### B.2.7 Identität: Workload Identity Federation

**Schicht-2-Verbot, ab Tag 1 ohne Übergangsregelung (A.13.2):** Für Compute-Workloads werden **keine Service-Account-Keys** ausgestellt. Ausschließlich Workload Identity Federation.

Da der Fachbereichs-GCP-Bestand bislang **keine Compute-Komponente** enthielt (B.2.0), gibt es keinen bestehenden Key-basierten Zugriff, der abgelöst werden müsste — die Regel gilt von Beginn an, ohne Migrationsfenster oder Ausnahmeliste. Das ist ein seltener Fall, in dem eine Sicherheitsanforderung nicht gegen gewachsenen Bestand durchgesetzt werden muss, sondern von Anfang an Teil des Fundaments ist.

**Mechanik (Kurzfassung):** Ein Kubernetes-ServiceAccount im jeweiligen Namespace wird über eine IAM-Policy-Bindung mit einer GCP-IAM-Identität verknüpft (`roles/iam.workloadIdentityUser`). Pods, die dieses ServiceAccount referenzieren, erhalten darüber kurzlebige, automatisch rotierte Tokens für den Zugriff auf GCP-APIs — ohne dass ein Schlüssel jemals als Datei oder Umgebungsvariable existiert.

```yaml
# Beispiel: Bindung eines K8s-ServiceAccounts an eine GCP-IAM-Identität
apiVersion: v1
kind: ServiceAccount
metadata:
  name: tool-<tool-objekt-id>
  namespace: prod
  annotations:
    iam.gke.io/gcp-service-account: tool-<tool-objekt-id>@python-fb-a.iam.gserviceaccount.com
```

Jedes Tool-Objekt erhält eine **eigene** GCP-IAM-Identität statt einer geteilten Projekt-weiten Identität — das setzt K2 (Datenzugriffsminimierung) technisch um: Ein Deployment kann nur auf die Datasets/Buckets zugreifen, für die seine eigene Identität explizit berechtigt wurde.

### B.2.8 Netzwerk: Default-Deny-Egress

Die Schicht-2-Prohibition „Datenausleitung an nicht deklarierte Ziele" (A.13.2) wird für Python/Kubernetes **technisch erzwungen**, nicht nur telemetrisch gemessen — anders als etwa bei Apps Script, wo eine Allowlist auf Anwendungsebene das einzig verfügbare Mittel ist (B.1.5), erlaubt Kubernetes echte Netzwerkdurchsetzung.

```yaml
# Beispiel: Default-Deny-Egress-NetworkPolicy je Namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-egress
  namespace: prod
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress: []   # keine Ziele erlaubt, bis ein Tool-Objekt spezifische Ziele deklariert
```

Ein neu bereitgestelltes Tool-Objekt erhält zunächst **keine** ausgehende Verbindung. Erlaubte Ziele — GCP-APIs, freigegebene externe Endpunkte — werden als zusätzliche, spezifische `NetworkPolicy`-Regeln aus der Prozessdeklaration (Schicht 1, A.13.2) abgeleitet. Ein neuer, nicht deklarierter Endpunkt ist damit keine Ermessensfrage der Anwendung, sondern schlicht nicht erreichbar — das Gate-2-Kriterium „neuer externer Endpunkt außerhalb der Allowlist" (A.11) wird für Python damit zur Netzwerkrealität statt zur nachträglichen Feststellung.

### B.2.9 Basis-Images

Alle Deployments, CronJobs und Jobs bauen auf einem **zentral gepflegten, gehärteten Basis-Image je Sprachversion** — verpflichtend, keine freie Wahl.

| Eigenschaft | Wirkung |
|---|---|
| Zentral gepflegt (Plattform-Rolle, A.15) | Sicherheitsupdates laufen einmal ein, nicht dezentral in jedem Repo |
| Vorab gescannte Basis-Abhängigkeiten | Der Snyk-Scan in der Pipeline (B.2.5) prüft nur noch Projekt-eigene Zusätze, nicht den gesamten Unterbau |
| Pro Sprachversion, nicht pro Projekt | Reproduzierbare Builds; Abweichungen sind sichtbar statt implizit |

Diese Pflicht ist die Umsetzung von K2/K3 auf Container-Ebene: Sie reduziert, was ein einzelnes Deployment an Angriffsfläche mitbringt, bevor eigener Code überhaupt beginnt.

### B.2.10 Deployment-Granularität: striktes 1:1-Mapping

**Ein Kubernetes-Deployment/CronJob/Job pro Tool-Objekt** — keine Bündelung mehrere fachlicher Tools in einer gemeinsamen Ausführungseinheit.

| Vorteil | Erklärung |
|---|---|
| Klarer Blast Radius | Ein kompromittiertes oder fehlerhaftes Tool betrifft nur seinen eigenen Workload |
| Saubere Telemetrie | Logs, Ressourcenverbrauch und Netzwerkverhalten sind eindeutig einem Tool-Objekt zuordenbar (A.12) |
| 1:1 zur Workload Identity | Jedes Tool-Objekt hat exakt eine eigene IAM-Identität (B.2.7) — eine Bündelung würde diese Zuordnung auflösen |

Der Preis dieser Entscheidung — mehr einzelne Kubernetes-Objekte als bei einer Bündelung — wird bewusst getragen, weil GKE-Autopilot-artiger Betrieb (Ressourcenzuteilung pro Pod statt pro Node) diesen Mehraufwand nicht in proportional mehr Betriebsaufwand übersetzt.

### B.2.11 Registrierungspunkt im Self-Service-Fluss

> **Explorieren bleibt frei; Registrierung greift beim ersten Deploy oder Datenzugriff.**

Das Öffnen eines Notebook- oder Code-Server-Workspace erfordert **keine** vorherige Zuordnung zu einem Prozessobjekt — Prinzip P1 in Reinform: Solange jemand nur lernt, exploriert oder einen Prototyp baut, entsteht kein Governance-Vorgang, weil noch kein Tool-Objekt existiert, das etwas täte.

Der Registrierungspunkt liegt technisch **genau dort, wo P2 ihn vorsieht** — beim ersten Schritt, der tatsächlich einen Wert außerhalb des Workspace erzeugt:

| Aktion | Erfordert Prozessobjekt-Zuordnung? |
|---|---|
| Workspace öffnen (Notebook oder Code-Server) | Nein |
| Code schreiben, lokal (im Workspace) testen | Nein |
| Ersten Deploy auslösen (Pipeline-Trigger) | **Ja** |
| Erste Datenverbindung zu BigQuery/GCS herstellen | **Ja** |

Diese zwei Auslöser sind bewusst gewählt: Beide sind die Momente, in denen aus einem Experiment ein Tool-Objekt mit realer Wirkung wird — und damit exakt die Momente, an denen P3 („das Register muss tragend sein") greift: Ohne Prozessobjekt-Zuordnung lässt sich weder ein Deployment auslösen noch eine Workload-Identity-Bindung auf ein Dataset einrichten, weil beides über dasselbe Self-Service-Frontend läuft (B.4), das die Zuordnung technisch voraussetzt.

### B.2.12 Anforderungsklassen K1–K9: die Transformation

Diese Tabelle ist der eigentliche Beleg für die in B.2.1 formulierte Zielrichtung — sie zeigt, wie sich die in A.9.3 dokumentierten strukturellen Ausschlüsse einer lokalen Python-Lösung durch die hier beschriebene Architektur auflösen:

| # | Anforderungsklasse | Alt: lokale `.exe` | Neu: Kubernetes-Golden-Path |
|---|---|---|---|
| K1 | Identität und Zugriffssteuerung | ⚠️ Nur Dateisystemrechte des Laptops | ✅ Workload Identity (B.2.7), RBAC über Namespace, getrennte Compute-/Daten-Projekte (B.2.4) |
| K2 | Datenzugriffsminimierung | ⚠️ Meist volle Rechte der persönlichen Kennung | ✅ Tool-eigene Workload-Identity-Bindung, Default-Deny-Egress (B.2.8) |
| K3 | Nachvollziehbarkeit des Codes | ⚠️ Git technisch möglich, organisatorisch selten | ✅ Ephemere Workspaces erzwingen Git als einzige Quelle (B.2.6) |
| K4 | Nachvollziehbarkeit der Ausführung | ❌ Nicht vorhanden | ✅ Cloud Logging je Cluster/Namespace (A.12) |
| K5 | Trennung Entwicklung / Produktion | ❌ Nicht vorhanden | ✅ Namespace-/Node-Pool-Trennung im Fachbereichs-Cluster (B.2.4) |
| K6 | Aufbewahrung und Revisionssicherheit | ❌ Nicht vorhanden | ✅ Git-Historie + Artifact-Registry-Versionierung |
| K7 | Verfügbarkeit und Wiederanlauf | ❌ Endet mit dem Gerät | ✅ Kubernetes-natives Self-Healing, Plattform-Betrieb (A.15) |
| K8 | Betroffenentransparenz | Organisatorisch zu lösen | Organisatorisch zu lösen — unverändert, technologieunabhängig |
| K9 | Nachfolge und Abhängigkeitsreduktion | ❌ Bindet an eine Person und ein Gerät | ✅ Gruppen-Ownership über Fachbereichs-Projekt, Plattform-Betrieb |

**Sieben von neun Klassen wechseln von ❌/⚠️ auf ✅.** Das ist der eigentliche Business Case dieses Abschnitts: Nicht „Kubernetes ist moderner", sondern „Kubernetes ist die einzige unter den geprüften Optionen, mit der ein Tier-3-Python-Prozess die für ihn geltenden Anforderungen überhaupt erfüllen kann". Die vollständige Matrix — inklusive Apps Script und GCP-Datendienste im direkten Vergleich — steht in Teil C.1.

### B.2.13 Bestand und Migration

Es gilt das technologieneutrale Migrationsprinzip aus A.16 unverändert: **on touch**, mit signaturbasierter Vollinventur und gestufter Mindest-Kompensationspflicht für strukturell ausgeschlossene Tier-3-Altfälle.

**Python-spezifische Ergänzung zur Erkennung:** Die signaturbasierte Erkennung (A.16.2, Schritt 1) nutzt die bestehende Endpoint-/Applikationskontrolle, die ausführbare Dateien anhand ihrer Signatur identifiziert — unabhängig davon, ob ein Owner sich meldet. Für den Python-Bestand bedeutet das konkret: Jede lokal installierte `.exe`, die aus dem bestehenden CI/CD-Framework stammt, ist über diese Signatur auffindbar, auch wenn das zugehörige Tool-Objekt heute nicht existiert.

Der weitere Ablauf — Grace Period, Meldepflicht, zweite Grace Period, Blockierung auf Applikationsebene — folgt vollständig A.16.2 und wird hier nicht dupliziert (Prinzip P5).

### B.2.14 Impact auf die Entwickler

**Was sich grundlegend ändert (anders als bei Apps Script, B.1.14):**

| | Heute (`.exe`, lokal) | Golden Path (Kubernetes) |
|---|---|---|
| Entwicklungsumgebung | Lokaler Laptop, eigene Python-Installation | Browserbasiert, kein lokales Setup |
| Wo lebt der Code zwischendurch | Lokal, oft nur auf einem Gerät | Nur in Git — Workspace ist ephemer |
| Wie wird verteilt | `.exe`-Datei, manuell oder über Softwareverteilung | Deployment/CronJob über Pipeline |
| Wo läuft es produktiv | Auf dem Gerät des Entwicklers oder eines Kollegen | GKE-Cluster des Fachbereichs |
| Was passiert bei Personalwechsel | Tool fällt aus, niemand weiß wie es läuft | Gruppen-Ownership, Plattform betreibt weiter |

**Der Deal, den wir anbieten (analog B.1.14):**

> Wer im golden Path arbeitet, startet ohne lokale Installation, ohne Docker-Kenntnisse, ohne Kubernetes-Wissen — die Scaffolding-Logik im Self-Service-Frontend (B.4) und die zentralen Basis-Images (B.2.9) übernehmen das. Im Gegenzug entfällt die Frage „was passiert, wenn mein Laptop kaputtgeht" vollständig, weil nichts mehr lokal liegt.

**Konkrete Reibungspunkte, offen zu kommunizieren:**

1. **Kein Offline-Arbeiten** — die Entwicklungsumgebung braucht eine Verbindung zum Cluster. Für Fachbereiche mit echtem Offline-Bedarf ist das eine reale Einschränkung, die vor Rollout benannt werden sollte.
2. **Ephemere Workspaces bestrafen unvollständige Commits** — wer eine Session beendet, ohne zu pushen, verliert den Stand. Auto-Save-in-Git oder ein deutlicher Warnhinweis vor Sitzungsende sollte Teil der Umsetzung sein.
3. **Erstmalige Umstellung für bestehende `.exe`-Entwickler** ist ein größerer Sprung als der entsprechende Schritt bei Apps Script — hier wird nicht nur ein Projekt umgehängt, sondern das gesamte Entwicklungsmodell gewechselt. Schulungsbedarf einplanen.

### B.2.15 Offene Punkte — vor Rollout zu klären

| # | Punkt | Warum relevant | Vorgehen |
|---|---|---|---|
| 1 | Exakte Dauer der beiden Grace Periods (A.16.2) | Zu kurz erzeugt unnötigen Druck, zu lang verlängert das ungeschützte Fenster | Abstimmung mit dem Team, das die Endpoint-/Applikationskontrolle betreibt |
| 2 | Ressourcenkontingente je Notebook-/Code-Server-Session | Ohne Limits kann ein einzelner Workspace den `dev`-Node-Pool eines Fachbereichs auslasten | Quotas je Nutzer/Session definieren, an bestehende Kostenstellen-Logik anschließen |
| 3 | Idle-Timeout für offene Sessions | Offene, ungenutzte Sessions sind Kosten- **und** Sicherheitsrisiko (Prinzip Least Privilege über Zeit) | Automatische Terminierung nach Inaktivität, Schwellenwert festlegen |
| 4 | Umgang mit Python-Abhängigkeiten außerhalb des Basis-Images | Ergänzende Pakete müssen weiterhin durch den Snyk-Scan (B.2.5), aber der Prozess dafür ist hier nicht spezifiziert | Abhängigkeits-Deklaration (z. B. `requirements.txt`/`pyproject.toml`) als Pipeline-Eingabe definieren |
| 5 | Genaues Autorisierungsmodell des identitätsbasierten Zugriffsproxys vor dem Cluster (B.2.6) | Bestimmt, wie granular sich Zugriff auf einzelne Fachbereichs-Workspaces steuern lässt | Mit dem Team abstimmen, das die zentrale Unternehmensidentität betreibt |

---

## B.3 GCP-Datendienste — BigQuery und Cloud Storage

### B.3.0 Ausgangslage

Fachbereiche nutzen BigQuery und Cloud Storage bereits heute — anders als bei Python (B.2.0) existiert hier also schon eine Nutzungspraxis, aber kein einheitliches Self-Service-Provisionierungsmodell und keine automatische Anbindung an das Datenobjekt-Modell aus A.7.

### B.3.1 Zielbild: Self-Service mit Guardrails

Analog zum Apps-Script-Standardprojekt (B.1.3): Fachbereiche erhalten Datenressourcen über Self-Service statt über zentrale Einzelvergabe — begrenzt durch Guardrails, die aus dem Tier des jeweiligen Prozesses folgen, nicht durch eine manuelle Prüfung vor jeder Provisionierung.

### B.3.2 Projekttopologie

Ein eigenes Standardprojekt `data-fb-x` je Fachbereich, getrennt vom Compute-Projekt `python-fb-x`, IAM-verknüpft — die vollständige Topologie ist bereits in B.2.4 dargestellt und gilt hier unverändert (Prinzip P5: nicht dupliziert).

### B.3.3 Self-Service-Provisionierung und automatische Datenobjekt-Registrierung

**Vollautomatisch bis Tier 3:** Ein neues BigQuery-Dataset oder ein neuer Cloud-Storage-Bucket wird über das Self-Service-Frontend (B.4) angelegt — dieser Vorgang erzeugt **automatisch** ein Datenobjekt der Stufe 1 (Name, Kategorie, Owner, Quellsystem, A.7) als Nebenprodukt der Provisionierung. Kein manuelles Gate, solange der anfragende Prozess unterhalb Tier 3 liegt.

**Ab Tier 3:** Die Provisionierung läuft weiterhin über dasselbe Self-Service-Frontend, durchläuft aber Gate 1 (A.11) — dieselbe Freigabestelle, die auch Tier-3-Apps-Script- und Tier-3-Python-Fälle behandelt, kein separates Gremium für Datenressourcen.

**Warum das P2 konsequent umsetzt:** Wer ein Dataset anlegt, muss dabei zwangsläufig einen Namen und einen Owner angeben — das ist bereits die Information, die ein Datenobjekt der Stufe 1 braucht. Eine separate Erfassung wäre doppelte Arbeit für dieselbe Angabe.

### B.3.4 Anforderungsklassen K1–K9

| # | Anforderungsklasse | Umsetzung |
|---|---|---|
| K1 | Identität und Zugriffssteuerung | IAM auf Projekt-/Dataset-Ebene, Row-Level-Security für feingranulare Fälle |
| K2 | Datenzugriffsminimierung | Authorized Views, Policy Tags (Spaltenebene), Spaltenmaskierung |
| K3 | Nachvollziehbarkeit des Codes | Views und Transformationen als Code (dbt/Terraform), durch dieselbe Pipeline-Logik wie B.1/B.2 versioniert |
| K4 | Nachvollziehbarkeit der Ausführung | Cloud Audit Logs, `INFORMATION_SCHEMA`-Abfragen |
| K5 | Trennung Entwicklung / Produktion | Getrennte Datasets/Projekte je Umgebung |
| K6 | Aufbewahrung und Revisionssicherheit | Snapshots, BigQuery Time Travel, Export ins Archivsystem für Langzeitaufbewahrung |
| K7 | Verfügbarkeit und Wiederanlauf | Google-SLA, Wiederherstellung aus Snapshot/Time-Travel-Fenster |
| K8 | Betroffenentransparenz | Organisatorisch zu lösen — unverändert, technologieunabhängig |
| K9 | Nachfolge und Abhängigkeitsreduktion | Gruppen-Ownership auf Projekt- und Dataset-Ebene |

Diese Domäne ist technisch bereits gut abgedeckt — entsprechend sind hier keine strukturellen ❌ zu schließen, nur die Self-Service-Provisionierung (B.3.3) ist neu.

### B.3.5 Telemetrie

Vollständig in A.12 (technologieneutrale Übersicht) enthalten — hier nicht dupliziert.

### B.3.6 Offene Punkte

| # | Punkt | Warum relevant |
|---|---|---|
| 1 | Genaue Kontingente für Self-Service-Provisionierung (Anzahl Datasets/Buckets je Fachbereich, Speicher-/Abfragekosten-Budget) | Ohne Obergrenze skaliert Self-Service-Bequemlichkeit direkt in Kosten |
| 2 | Bestehender, nicht über Self-Service angelegter Datenbestand — wie wird er nachträglich an das Datenobjekt-Modell angeschlossen | Betrifft nur Bestand vor Einführung dieses Modells; folgt grundsätzlich A.16 (on touch) |

---

## B.4 Gemeinsame Plattform und Self-Service-Frontend

### B.4.1 Ein Frontend für alle drei Technologien

Apps Script, Python und GCP-Datendienste werden über **ein gemeinsames** Self-Service-Frontend beantragt und bereitgestellt — nicht über drei getrennte Zugänge. Die browserbasierte Entwicklungsumgebung aus B.2.6 (Notebooks, Code-Server) ist zugleich die zentrale Andockstelle für:

| Anfrage | Was das Frontend tut |
|---|---|
| Neues Apps-Script-Standardprojekt (B.1.3) | Provisioniert Projekt im korrekten Ordner, mit korrekten IAM-Bindings und Labels |
| Neuer Python-Workspace (B.2.6) | Startet ephemeren Notebook- oder Code-Server-Workspace im `dev`-Node-Pool des Fachbereichs |
| Python-Deployment auslösen (B.2.11) | Verlangt Prozessobjekt-Zuordnung, triggert die Pipeline (B.2.5) |
| Neues BigQuery-Dataset / GCS-Bucket (B.3.3) | Provisioniert Ressource, registriert automatisch ein Datenobjekt Stufe 1 |

**Warum ein Frontend statt drei:** Aus genau dem in P3 formulierten Grund: Ein Register, das Eingangstor für Provisionierung ist, bleibt aktuell. Drei getrennte Frontends würden drei getrennte, potenziell auseinanderdriftende Register erzeugen.

### B.4.2 Betrieb

Die bestehende Plattform-Rolle (A.15) betreibt das Frontend, die zugrundeliegende Pipeline (Azure DevOps, B.1.8/B.2.5) und die GKE-Cluster (B.2.4) als **eine** Instanz — kein getrenntes Team je Technologie. Wächst der Geltungsbereich künftig um eine vierte Technologie, ist die Erwartung, dass sie sich in dasselbe Frontend einfügt, nicht ein viertes System entsteht.

### B.4.3 Zusammenspiel mit Gate 1/Gate 2

Das Frontend kennt den Tier eines anfragenden Prozesses (aus dem Prozessobjekt, A.5) und entscheidet danach, ob eine Anfrage sofort ausgeführt wird oder Gate 1 durchläuft (A.11) — unabhängig davon, welche der drei Technologien betroffen ist. Diese Logik liegt **im Frontend**, nicht in drei parallelen, technologiespezifischen Implementierungen.

---

# TEIL C — GESAMTARCHITEKTUR

*Führt Teil A und Teil B zu einem Gesamtbild zusammen.*

## C.1 Technologiematrix

Die Python-Spalte ist aufgeteilt in **Alt-Bestand** (heutige `.exe`-Praxis, zum Vergleich) und **Golden Path** (Kubernetes, Zielbild) — der Unterschied zwischen beiden Spalten ist der eigentliche Wirkungsnachweis von B.2.

**Legende:** ✅ strukturell erfüllt · ⚠️ eingeschränkt erfüllbar / kompensierende Maßnahme nötig · ❌ strukturell nicht erfüllbar

| # | Anforderungsklasse | Apps Script | AppSheet | Python — Alt (`.exe`) | **Python — Golden Path** | BigQuery / GCS |
|---|---|---|---|---|---|---|
| K1 | Identität/Zugriff | ✅ Standard-Projekt, IAM über Gruppen | ✅ App-Owner als Gruppe, Security Filter | ⚠️ Nur Dateisystemrechte | ✅ Workload Identity, RBAC | ✅ IAM, Row-Level-Security |
| K2 | Minimierung | ✅ Enge Scopes, `@OnlyCurrentDoc`, Picker | ✅ Datenquelle auf Bedarf begrenzt | ⚠️ Meist volle Rechte der Kennung | ✅ Scoped Workload Identity, Default-Deny-Egress | ✅ Authorized Views, Policy Tags |
| K3 | Code-Nachvollziehbarkeit | ✅ clasp + Git + Pipeline | ⚠️ Nur App-Versionierung | ⚠️ Git möglich, organisatorisch selten | ✅ Ephemere Workspaces erzwingen Git | ✅ Views als Code (dbt/Terraform) |
| K4 | Ausführungs-Nachvollziehbarkeit | ✅ Cloud Logging, OAuth Token Audit | ✅ Nutzungs-/Änderungsprotokoll | ❌ Nicht vorhanden | ✅ Cloud Logging je Cluster/Namespace | ✅ Cloud Audit Logs, `INFORMATION_SCHEMA` |
| K5 | Trennung Dev/Prod | ✅ Getrennte Projekte | ⚠️ Eingeschränkt möglich | ❌ Nicht vorhanden | ✅ Namespace-/Node-Pool-Trennung | ✅ Getrennte Datasets/Projekte |
| K6 | Revisionssicherheit | ⚠️ Nur über Export | ⚠️ Nur über Export | ❌ Nicht vorhanden | ✅ Git + Artifact-Registry-Historie | ✅ Snapshots, Time Travel |
| K7 | Verfügbarkeit | ⚠️ Google-SLA, kein eigener Wiederanlauf | ✅ Google-SLA | ❌ Endet mit dem Gerät | ✅ K8s-Self-Healing, Plattform-Betrieb | ✅ Google-SLA + Wiederherstellung |
| K8 | Betroffenentransparenz | Organisatorisch | Organisatorisch | Organisatorisch | Organisatorisch | Organisatorisch |
| K9 | Nachfolge | ✅ Gruppen-Ownership, Repo | ✅ Gruppen-Ownership | ❌ Bindet an Person und Gerät | ✅ Gruppen-Ownership, Plattform-Betrieb | ✅ Gruppen-Ownership |
| K10 | KI-Auflagen (EU AI Act) | Organisatorisch | Organisatorisch | Organisatorisch | Organisatorisch | Organisatorisch |

**Zu K10:** Anders als K1–K9 hängt die Erfüllung kaum von der Ausführungsplattform ab — menschliche Aufsicht, Dokumentation und Konformitätsbewertung sind Prozesspflichten, keine Infrastrukturmerkmale. Die Zeile ist deshalb technologieunabhängig „Organisatorisch", vergleichbar mit K8.

**Lesart für Gate 1 (A.9.3):** Ein Tier-3-Prozess mit Profil `KI0-DS3-MB1-IT1-RG2-UR2` (Ableitung über den Entscheidungsbaum, A.8.5) löst K1, K2, K3, K4, K5, K7, K8 und K9 aus, nicht aber K6 oder K10. Für K4, K5, K7 und K9 ist eine lokale Python-Lösung ohne den Golden Path aus B.2 strukturell ausgeschlossen; mit ihm ist sie es nicht — das ist die praktische Wirkung der in B.2 beschriebenen Architektur.

> ⚠️ Diese Matrix altert, sobald sich Produktfähigkeiten ändern. Periodische Prüfung bleibt jährliche Pflicht (A.18, Punkt 9).

## C.2 Gesamtarchitektur im Überblick

```
                    ┌─────────────────────────────────────┐
                    │   PROZESSOBJEKT · TOOL-OBJEKT        │
                    │   DATENOBJEKT  (Teil A, technologie- │
                    │   neutrales Register, P1–P5)         │
                    └──────────────────┬────────────────────┘
                                       │ definiert Rahmen, Tier, K-Klassen
                                       ▼
                    ┌─────────────────────────────────────┐
                    │   GEMEINSAMES SELF-SERVICE-FRONTEND  │
                    │   (B.4 — Notebooks / Code-Server als │
                    │   Andockstelle für alle drei Domänen)│
                    └───┬───────────────┬───────────────┬───┘
                        │               │               │
                        ▼               ▼               ▼
              ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
              │ Apps Script  │ │   Python     │ │ GCP-Daten-   │
              │   (B.1)      │ │  (B.2)       │ │ dienste (B.3)│
              │              │ │              │ │              │
              │ Standard-    │ │ GKE-Cluster  │ │ BigQuery /   │
              │ Projekt je   │ │ je Fach-     │ │ Cloud Storage│
              │ Fachbereich  │ │ bereich,     │ │ je Fach-     │
              │ apps-script- │ │ python-fb-x  │ │ bereich,     │
              │ fb-x         │ │ (dev+prod    │ │ data-fb-x    │
              │              │ │ getrennt)    │ │              │
              └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
                     │                │                │
                     └────────────────┼────────────────┘
                                       ▼
                    ┌─────────────────────────────────────┐
                    │   AZURE-DEVOPS-PIPELINE              │
                    │   (Secret-/Snyk-Scan, gemeinsam für  │
                    │   alle drei Domänen, B.1.8 / B.2.5)  │
                    └───────────────────┬───────────────────┘
                                       │ Telemetrie zurück ins Register
                                       ▼
                    ┌─────────────────────────────────────┐
                    │   SOLL-IST-ABGLEICH, COCKPIT         │
                    │   (A.13, A.14 — technologieneutral)  │
                    └─────────────────────────────────────┘
```

**Lesart:** Das Register (oben) definiert, was erlaubt ist. Das Frontend (B.4) ist der einzige Weg, wie aus einer Absicht ein Tool-Objekt wird. Alle drei Technologiedomänen hängen an derselben Pipeline und liefern Telemetrie an denselben Abgleichsmechanismus zurück — es gibt keinen Pfad, der das Register umgeht, ohne gegen Schicht 2 zu verstoßen.

## C.3 Gemeinsamer Stufenplan

Die für Apps Script definierten Phasen 0–5 (B.1.13) und die Einführung des Governance-Fundaments laufen **parallel**, nicht sequenziell — das zieht sich durch die gesamte Architektur.

| Zeitachse | Apps Script (B.1.13) | Python (B.2) | GCP-Datendienste (B.3) | Governance-Fundament (Teil A) |
|---|---|---|---|---|
| **Start** | Phase 0 — Inventur, read-only | Signaturbasierte Vollinventur (A.16.2) beginnt parallel | Bestandsaufnahme heutiger Nutzung | Objektmodell, Kategorienliste, Tier-Regel verbindlich definieren; drei Referenz-Prozessobjekte mit Pilot-Fachbereich |
| **Früh** | Phase 1 — Tiering; Phase 2 — Beobachten ohne Blockieren | GKE-Cluster-Grundgerüst je Pilot-Fachbereich; Basis-Images aufsetzen | `data-fb-x`-Standardprojekt für Pilot-Fachbereich | Register technisch anlegen, **an Provisionierung koppeln** (P3) — gilt für alle drei Domänen gleichzeitig |
| **Mitte** | Phase 3 — Goldener Pfad etablieren | Self-Service-Frontend (B.4) live für Python-Workspaces; erste Pipeline-Deployments | Self-Service-Provisionierung für Datasets/Buckets live | Prozesse top-down aus den Fachbereichen erfassen, nicht aus dem Bestand rückwärts ableiten |
| **Spät** | Phase 4 — Gezieltes Enforcement | Grace-Period-Mechanismus (A.16.2) für Tier-3-Altbestand scharf schalten | — | Tier-Berechnung und beide Gates aktivieren; Cockpit in Betrieb |
| **Fortlaufend** | Phase 5 — Neuanlagen strukturell sauber | Neue Python-Anwendungen laufen ausschließlich über den Golden Path | Neue Datenressourcen laufen ausschließlich über Self-Service | Datenobjekte zu Datenprodukten ausbauen, wo geteilt genutzt; jährliche Revision der Technologiematrix (C.1) |

## C.4 Zusammenfassung offener Bestätigungen

Dieses Dokument enthält an mehreren Stellen Annahmen oder Vorschläge, die aus der Systematik abgeleitet, aber nicht ausdrücklich bestätigt sind. Zur schnellen Prüfung an einer Stelle gesammelt — Einzelheiten jeweils am Fundort:

| # | Annahme/Vorschlag | Fundort | Bei fehlender Bestätigung zu ändern |
|---|---|---|---|
| 1 | Reihenfolge und Schwellen der sechs Schritte im Entscheidungsbaum sind aus den Ankern (A.8.3) abgeleitet, nicht gesondert bestätigt | A.8.5 | Reihenfolge/Schwellen im Baum |
| 2 | EU-AI-Act-Risikokategorien (verboten/Anhang III/Art. 50/minimal) sind vereinfachend auf vier Stufen abgebildet | A.8.3, A.8.5 Schritt 1 | KI-Anker und Baum-Schritt 1a–1d |
| 3 | Größenordnung der beiden Grace Periods (60–90 / 15–30 Tage) | A.16.2 | Fristangaben in A.16.2, A.18 Punkt 12 |
| 4 | Ressourcenkontingente, Idle-Timeout für Notebook-/Code-Server-Sessions | B.2.15 | Konkrete Werte ergänzen |
| 5 | Genaues Autorisierungsmodell des Zugriffsproxys vor dem Cluster | B.2.6, B.2.15 | Technische Umsetzung |
| 6–15 | Die zehn technisch zu verifizierenden Punkte aus B.1.15 (App-Identitäts-Bündelung, Editionsstand, Audit-Log-Verhalten eingebauter Services u. a.) | B.1.15 | Je nach Prüfergebnis einzelne Bausteine in B.1 |

---

*Ende des Dokuments.*
