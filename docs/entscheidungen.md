# Entwurfsentscheidungen und Auslegungen

Dieses Dokument hält fest, wo die Umsetzung die Architekturvorgabe auslegt,
präzisiert oder bewusst von ihr abweicht. Alles andere folgt der Vorgabe
unverändert.

Die Vorgabe selbst — das interne Dokument „Governance-Plattform — Technische
Architektur" und das übergeordnete Leitdokument — liegt nicht in diesem
Repository. Verweise darauf erfolgen über Abschnittsnummern: `Architektur 7.3`
meint Abschnitt 7.3 des Architekturdokuments, `Leitdokument A.13.5` den
entsprechenden Abschnitt des Leitdokuments.

## E-1 — `customer` und `ausfallfolge` sind kontrollierte Listen, kein Freitext

**Vorgabe:** Abschnitt 3.2 führt `customer` als „Enum/Text" mit dem Zusatz
„Reichweiten-Ableitung" und `ausfallfolge` als „Text".

**Umsetzung:** Beide Felder sind Auswahllisten (`Kundenkreis`,
`Ausfallfolge`).

**Grund:** Reichweite und Kritikalität werden serverseitig abgeleitet und nicht
abgefragt (Leitdokument P1, Architektur 8.1). Eine Ableitung aus Freitext wäre
nicht bestimmbar und damit nicht prüfbar — das Abnahmekriterium „nach Speichern
serverseitig berechnet" ließe sich gegen ein Freitextfeld nicht testen. Die
übrigen acht SIPOC-Felder bleiben Freitext beziehungsweise Referenz; die Zahl
der Felder im Formular bleibt bei zehn.

## E-2 — Ableitungsregeln

Das Leitdokument liegt diesem Repository nicht bei; die konkreten Formeln sind
hier festgelegt und in `app/services/ableitung.py` dokumentiert:

- **Reichweite** = Kundenkreis, angehoben auf `unternehmen`, sobald der Prozess
  in mehr als einer Landesorganisation umgesetzt wird.
- **Kritikalität** = eigene Ausfallfolge (0–3), angehoben auf das Maximum der
  transitiven Nachfolger in der Prozesskette (Leitdokument A.4.2). Die Rekursion
  ist gegen Zyklen abgesichert, weil die Kette technisch n:m ist.
- **Mitbestimmungsflag** = wahr, sobald ein beteiligtes Datenobjekt die
  Kategorie `mitarbeiterbezogen` trägt oder die neueste Bewertung eine
  Mitbestimmungsstufe größer null hat.

Ändert sich eine Ausfallfolge, führt die Anwendung die Kritikalität aller
transitiven Vorgänger nach; sonst wäre sie nach einer Änderung still veraltet.

## E-3 — Erstzugang über `GP_BOOTSTRAP_ADMIN_SUBJECTS`

Rollen vergibt ausschließlich der App-Administrator (Matrix 5.3). Damit die
allererste Zuweisung überhaupt möglich ist, erhält ein in dieser ENV-Variable
genanntes OIDC-Subject bei seiner ersten Anmeldung global die Rollen
App-Administrator und Governance. Der Vorgang ist idempotent und greift nur für
ausdrücklich konfigurierte Subjects.

## E-4 — Entwicklungsanmeldung statt zweitem Anmeldeweg

`GP_AUTH_DEV_MODE` ersetzt nur den *Aussteller* des Tokens, nicht die Prüfkette:
auch dort wird ein signiertes JWT erwartet und validiert. Ist der Modus aus —
der Produktionsfall —, antwortet die Route `POST /api/v1/auth/dev-token` mit
404, damit es keinen zweiten Anmeldeweg neben der zentralen Identität gibt
(Architektur 10.1). Ein Test hält das fest.

## E-5 — Tests laufen gegen PostgreSQL, nicht gegen eine Ersatzdatenbank

Die Testsuite und die Oberflächentests laufen gegen dieselbe PostgreSQL wie
Entwicklung und Produktion, jede Ebene mit einer eigenen Datenbank auf
demselben Server. Die Verbindung kommt aus `GP_TEST_DATABASE_URL`
beziehungsweise `GP_E2E_DATABASE_URL`; gestartet wird sie mit
`docker compose up -d datenbank`.

**Diese Entscheidung war zwischenzeitlich anders und wurde korrigiert.** Die
Tests liefen zunächst gegen SQLite, mit dem Argument, sie seien so ohne
Container-Start reproduzierbar. Das Argument hält gegen Abschnitt 6.5 nicht
stand — dort steht ausdrücklich, dass es keine abweichende lokale Umgebung
geben soll — und es war auch sachlich falsch:

- Zwei Typ-Adapter (`GUID`, `TZDateTime`) existierten allein, um
  Dialektunterschiede auszugleichen. Beide sind mit der Umstellung entfallen.
- Kein einziger Test lief je gegen die Zieldatenbank. Genau die Fehler, die
  eine Testsuite finden soll, blieben deshalb verborgen: der Wechsel auf
  PostgreSQL deckte sofort eine Wettlaufsituation im Sitzungsumgang auf
  (siehe E-15), die jeden echten Client getroffen hätte.
- Die Migrationen hingen an App-Code (`app.db.GUID`). Sie referenzieren jetzt
  den SQLAlchemy-Dialekttyp direkt und sind damit unabhängig davon, wie die
  Anwendung ihre Typen benennt.

Das Schema entsteht einmal je Testlauf aus den Migrationen; zwischen den Tests
werden die Tabellen mit `TRUNCATE … RESTART IDENTITY` geleert. Das ist
schneller als der bisherige Weg über eine Datei je Test und prüft die
Migrationen trotzdem bei jedem Lauf einmal vollständig durch.

## E-6 — Datenkategorien

Die Kategorien eines Datenobjekts sind die fünf aus Leitdokument A.7:
`oeffentlich`, `intern`, `vertraulich`, `personenbezogen` und
`besondere_kategorie`. Sie sind bewusst nullable, damit die Cockpit-Ansicht
„Datenobjekte ohne Kategorie" (Architektur 8.7) überhaupt etwas zu zeigen hat.

**Korrigiert am 2026-09-01, siehe E-19:** Zwischenzeitlich gab es eine sechste
Kategorie `mitarbeiterbezogen`.

## E-7 — Fragen des Bewertungsbaums und Bedingungen der K-Klassen

Das Leitdokument (A.8.5, A.9.2) liegt diesem Repository nicht bei. Der Baum ist
deshalb in `app/services/bewertungsbaum.py` ausformuliert, die Bedingungen der
zehn Maßnahmenklassen in `app/services/bewertung.py`. Beide sind so gesetzt,
dass das im Leitdokument durchgerechnete Beispiel exakt herauskommt: Profil
`KI0-DS3-MB1-IT1-RG2-UR2` löst K1, K2, K3, K4, K5, K7, K8 und K9 aus — nicht K6
und nicht K10. Ein Test hält genau das fest.

Struktur des Baums: sechs Blöcke in fester Reihenfolge, innerhalb eines Blocks
die Fragen absteigend nach Schwere. Die erste bejahte Frage bestimmt die Stufe;
wird keine bejaht, ist die Stufe 0. Der KI-Block hat eine Einstiegsfrage: ohne
KI-Einsatz wird der Rest übersprungen. Das Tier ist die höchste erreichte Stufe,
mindestens 1.

Der Wizard ist **zustandslos**: der Client schickt alle bisherigen Antworten
mit, der Server bestimmt daraus die nächste Frage. Damit liegt die Reihenfolge
in der Geschäftslogik und nicht in der Oberfläche, ohne dass eine serverseitige
Wizard-Sitzung nötig wäre.


> **Nachtrag vom 02.09.2026:** Das Leitdokument liegt seit heute bei (`docs/leitdokument.md`). Der Abgleich hat gezeigt, dass die hier beschriebene Fassung von der damaligen Vorgabe abweicht — die Entscheidung fiel, **das Dokument** an den Code anzupassen, nicht umgekehrt (E-48). Was unten steht, ist damit nicht mehr meine Auslegung, sondern die geltende Fassung.

## E-8 — Zeitstempel sind `timestamptz`

Alle Zeitstempel sind `TIMESTAMP WITH TIME ZONE`; PostgreSQL liefert sie
zeitzonenbehaftet zurück. Ein eigener Typ-Adapter dafür ist entfallen, seit die
Tests gegen dieselbe Datenbank laufen (E-5) — er hatte nur den Unterschied zu
SQLite ausgeglichen. Die Fachlogik rechnet durchgehend in UTC.

## E-9 — Aktivierung eines Tier-3-Prozessobjekts

Abnahmekriterium 4.1 nennt die vollständige Selbstverpflichtung als Bedingung
für den Wechsel nach `aktiv`. Die Umsetzung prüft zwei weitere Bedingungen:

1. **Eine Bewertung muss vorliegen.** Ohne Bewertung ist weder Tier noch
   K-Klassen-Bild bekannt; ein aktives, unbewertetes Prozessobjekt wäre genau
   die Lücke, die das Leitdokument schließen will.
2. **Ab Tier 3 muss Gate 1 freigegeben sein.** Architektur 8.5 beschreibt
   Gate 1 als „Tier-3-Erstfreigabe" — die Aktivierung *ist* die erste Freigabe.
   Bliebe sie ungeprüft, wäre Gate 1 ein Vorgang ohne Wirkung.

Beide Prüfungen liegen in der Geschäftslogik (`prozess.pruefe_aktivierung`),
nicht in der Oberfläche, damit ein direkter API-Aufruf sie nicht umgeht.

## E-10 — Aussagenkataloge der Selbstverpflichtung

Die nummerierten Aussagen aus A.10.2 (sechs für den Prozesseigner) und A.10.3
(sechs für den technischen Owner) sind in
`app/services/selbstverpflichtung.py` ausformuliert, weil das Leitdokument
diesem Repository nicht beiliegt. Sie sind strukturierte Wahrheitswerte mit
optionalem Kommentar, nie ein Freitextfeld: nur so bleibt auswertbar, was
Cockpit und Lenkung später auswerten müssen. Die Oberfläche baut ihre
Checkliste aus dem Katalog-Endpunkt, damit Wortlaut und Reihenfolge an genau
einer Stelle stehen.

**Korrigiert am 2026-09-02, siehe E-32:** Der hier ausformulierte Katalog war
frei erfunden und sagte etwas anderes als A.10.2 und A.10.3. Die Struktur —
Wahrheitswerte mit Kommentar, Katalog-Endpunkt als einzige Quelle — hat sich
gehalten; die Aussagen selbst sind ersetzt.

## E-11 — Definition zweier Cockpit-Zeilen

Zwei der zehn Zeilen aus A.14 lassen sich nicht unmittelbar aus dem Datenmodell
ablesen und sind deshalb hier definiert:

- **Prozesse ohne Owner.** `owner_user_id` ist ein Pflichtfeld und nie leer.
  Die Zeile zeigt deshalb Prozesse, deren eingetragener Owner deaktiviert ist
  oder keine Prozess-Owner-Rolle besitzt — beides führt dazu, dass niemand den
  Prozess tatsächlich verantwortet.
- **Widersprüche zwischen Erklärung und Telemetrie.** Telemetrie kommt erst mit
  künftigen Adaptern (Architektur 7.4). Bis dahin ist der Widerspruch die
  Kombination aus bestätigter Aussage T1 („das Tool-Objekt läuft im
  vorgesehenen Rahmen") und einem aktuellen Compliance-Zustand auf rot. Sobald
  ein Adapter rote Zustände selbst meldet, trägt dieselbe Zeile ohne Änderung.

## E-12 — Datenobjekte ohne Fachbereich sind nicht öffentlich

Ein Datenobjekt ist bereichsweit sichtbar, damit es von vielen Tool-Objekten
wiederverwendet werden kann (Leitdokument A.4.5). Ein Datenobjekt **ohne**
Fachbereich ist aber niemandem zugeordnet; es bleibt den global lesenden Rollen
und seinem Owner vorbehalten. Wäre es für jeden Angemeldeten sichtbar, ließe
sich die Sichtbarkeitsregel aus Architektur 4.3 dadurch aushebeln, dass man die
Zuordnung einfach wegließe.

## E-13 — Erklärter Rahmen externer Ziele

Die Query-API muss zum Erlaubnisrahmen eines Tool-Objekts sagen können, welche
externen Ziele erlaubt sind (Architektur 7.3, Leitdokument A.13.2 Schicht 1).
Gate 2 kennt dafür den Auslöser „neues externes Ziel" — es muss also einen Ort
geben, an dem der erlaubte Stand steht.

Das Prozessobjekt trägt deshalb das Feld `erlaubte_externe_ziele` (Liste von
Zeichenketten). Es ist **kein** SIPOC-Feld: das Anlageformular fragt weiterhin
genau zehn Felder ab. Es ist eine Governance-Angabe, die nach der Bewertung
gepflegt wird — und deren Änderung ein Gate-2-Verfahren nach sich zieht.

## E-14 — Der Cursor der Delta-Abfrage wird einschließend gelesen

`GET /changes?since={cursor}` liefert alle Einträge mit `cursor >= since`, und
die Antwort nennt als `naechster_cursor` die Sequenznummer des letzten
gelieferten Eintrags plus eins. Eine andockende Anwendung gibt diesen Wert beim
nächsten Lauf unverändert wieder hinein.

Die Alternative — ausschließendes Lesen — hätte zur Folge, dass der Eintrag mit
genau dieser Nummer übersprungen wird, sobald er nach der letzten Antwort
entsteht. Genau das verbietet Abnahmekriterium 7.4 („ohne Lücken"). Die
Funktion heißt deshalb `changelog.eintraege_ab` und nicht `…_seit`: der Name
soll die Lesart tragen.

## E-15 — Die Arbeitseinheit ist die Anfrage, nicht der Abbau der Abhängigkeit

Die Datenbanksitzung wird von einer Middleware je Anfrage geöffnet und dort
auch abgeschlossen: bei einer Antwort unter Status 400 mit `commit`, sonst mit
`rollback`.

Zuvor lag der Commit im Abbau der FastAPI-Abhängigkeit `get_db`. Der läuft,
nachdem die Antwort die Anwendung verlassen hat — ein Client, der auf ein `201`
sofort mit einer Folgeanfrage reagiert, fand den eben angelegten Datensatz
deshalb gelegentlich noch nicht. Unter PostgreSQL war das reproduzierbar: in
einer Schleife über 200 Aufrufe „Fachbereich anlegen, sofort darauf verweisen"
scheiterte einer mit `404 Fachbereich nicht gefunden`. Nach der Umstellung
blieben 1000 von 1000 Aufrufen fehlerfrei.

Das war kein Testartefakt, sondern ein Fehler, der jeden echten Client
getroffen hätte — gefunden erst, als die Tests gegen die Zieldatenbank liefen.

## E-16 — Der Bewertungs-Wizard verwirft verspätete Antworten

Jeder Schritt des Wizards fragt den Server; die Antwort trägt die nächste
Frage. Trifft die Antwort auf einen älteren Schritt später ein als die auf
einen neueren — bei langsamer Verbindung oder schnellem Klicken —, würde sie
den aktuellen Schritt überschreiben und der Wizard spränge zurück.

Die Komponente führt deshalb eine laufende Nummer mit und verwirft jede
Antwort, die nicht zur zuletzt gestellten Abfrage gehört. Ohne diese Sicherung
war der Oberflächentest sporadisch rot; sie behebt aber nicht nur den Test,
sondern das Verhalten für jeden Nutzer mit träger Verbindung.

## E-17 — Keine Pipeline, sondern ein lokales Prüfskript

Geprüft wird lokal mit `./pruefen.sh`: Stil, Migrationen vorwärts und rückwärts,
beide Testsuiten mit ihren Abdeckungsschwellen, die headless-Oberflächentests
und auf Wunsch die drei Images gegen zwei Registry-Ziele.

Eine CI/CD-Pipeline ist ausdrücklich nicht gewollt. Damit verliert Architektur
11 keinen Abnahmenachweis — die Kriterien bleiben dieselben und sind weiterhin
durch Tests belegt —, aber sie werden auf Zuruf geprüft statt bei jedem Push.
Wer das Skript nicht laufen lässt, bekommt kein Signal; diese Verantwortung
liegt bewusst bei der Person, die committet.

## E-18 — Offene Punkte der Architektur

Die fünf offenen Punkte aus Architektur 12 bleiben offen; die Umsetzung nimmt
keine Entscheidung vorweg:

1. **Cloud SQL vs. selbstbetriebenes PostgreSQL** — die Anwendung kennt nur
   `GP_DATABASE_URL`; beide Varianten sind ohne Codeänderung bedienbar.
2. **Frontend-Framework** — React wie in der Architektur begründet gewählt.
3. **Format und Frequenz des Imports** — der Zielvertrag steht
   (`POST /api/v1/import/assets`); der Sync-Worker liest wahlweise eine Datei
   oder eine HTTP-Quelle in genau diesem Format.
4. **Format der `owner_hinweis`-Zuordnung** — wird als Zeichenkette gespeichert
   und nicht als harter Fremdschlüssel aufgelöst.
5. **Ausstellung der Service-Zugangsdaten** — die Query-API prüft Tokens aus
   `GP_QUERY_API_SERVICE_TOKENS`; wer sie ausstellt, ist Betriebsfrage.

## E-19 — Mitbestimmung ist ein abgeleitetes Flag, keine Datenkategorie

**Diese Entscheidung korrigiert E-2 und E-6.** Beide entstanden ohne Zugriff auf
das Leitdokument; seit es vorliegt, ist die Abweichung nicht mehr haltbar.

**Vorgabe:** A.7 sagt wörtlich: „Mitbestimmungsrelevanz ist keine Kategorie,
sondern ein abgeleitetes Flag. Sie kann bei jeder Datenkategorie auftreten, weil
sie am Verwendungszweck hängt, nicht an der Datenart. In die Kategorienliste
gepresst erzeugt sie systematisch falsche Einordnungen." A.5 gibt die
Ableitungsregel: Personenbezug **und** (Wirkung auf einzelne Person **oder**
Leistungs-/Verhaltensdaten).

**Vorher:** eine sechste Kategorie `mitarbeiterbezogen`, und das Flag war wahr,
sobald ein Datenobjekt sie trug oder irgendeine Bewertung eine
Mitbestimmungsstufe über null hatte — eine Disjunktion, wo die Vorgabe eine
Konjunktion verlangt.

**Jetzt:** Die Kategorie ist entfallen (Migration `a1c4e7b2f930`, Bestand wandert
nach `personenbezogen`). Das Flag entsteht aus beiden Hälften:

1. **Personenbezug** — mindestens ein referenziertes Datenobjekt trägt
   `personenbezogen` oder `besondere_kategorie`.
2. **Wirkung** — entweder die besondere Kategorie selbst (A.7 zählt dort
   Entgelt, Gesundheit und Leistungsbewertung auf, also genau Leistungs- und
   Verhaltensdaten) oder eine Bewertung mit MB-Stufe ≥ 2, ab der das Ergebnis
   nach A.8.3 einzelnen Beschäftigten zurechenbar ist.

**Folge, die man kennen muss:** Ein Prozess mit personenbezogenen Daten, aber
ohne Bewertung und ohne besondere Kategorie trägt das Flag jetzt **nicht** mehr.
Das ist gewollt — die zweite Hälfte der Regel ist aus den Stammdaten allein
nicht bestimmbar. Mit den Attestierungen des technischen Owners (A.6, Fragen 1
und 2) bekommt sie in AP-3 eine zweite Quelle.

## E-20 — Quellsystem getrennt von der Sync-Quelle

Reifegrad 1 in A.7 verlangt Name, Kategorie, Owner **und Quellsystem**. Das
Datenobjekt trug bisher nur `quelle`, und das ist die Kennung des
Import-Adapters (Architektur 7.2), nicht die fachliche Herkunft. Beides fällt
oft zusammen, ist aber nicht dasselbe: ein manuell angelegtes Datenobjekt hat
ein Quellsystem, aber keine Sync-Quelle. Deshalb ein eigenes Feld
`quellsystem`.

## E-21 — Die Wirkungsvorschau rechnet keine Tiers vor

`GET /api/v1/datenobjekte/{id}/wirkung?kategorie=…` beantwortet die Frage aus
A.4.7 („Was passiert, wenn Datenobjekt D höher eingestuft wird?") mit dem, was
heute berechenbar ist: den referenzierenden Prozessobjekten samt künftigem
Mitbestimmungsflag und den betroffenen Tool-Objekten.

Ein künftiges Tier weist sie **nicht** aus. Das Tier entsteht heute aus den
Antworten des Bewertungs-Wizards, nicht aus den Datenkategorien; eine
vorgerechnete Zahl wäre erfunden. Sobald die Bewertung ihre DS-Dimension aus den
Kategorien ableitet (Umsetzungsplan AP-4), liefert dieselbe Abfrage sie mit.

Die Vorschau arbeitet auf einer Probe-Zuweisung, die im `finally` zurückgesetzt
wird — sie ändert nichts und schreibt nichts in den `change_log`.

## E-22 — Ohne Attestierung keine Prozessverknüpfung

A.6 nennt drei Erklärungen, die Telemetrie nicht liefern kann, und markiert die
dritte ausdrücklich als „die wichtigste — sie fängt genau die Lücke, die das
Datenobjekt-Modell strukturell nicht schließen kann". Das Dokument sagt aber
nicht, wann sie fällig sind.

**Entschieden:** vor der ersten Prozesskante. `POST /tools/{id}/prozesse`
weist die Verknüpfung mit 422 ab, solange eine der drei Antworten fehlt.

Der Grund ist nicht Formalismus. Mit der Prozesskante erbt das Tool eine
Klassifikation (A.4.4) und tritt in den Erlaubnisrahmen ein (A.13.2). Beides
setzt die Triage „verändert oder gestaltet" voraus, und die trägt Attestierung 2.
Ein Tool, das erbt, bevor jemand erklärt hat, ob ein Mensch zwischen Output und
Wirkung steht, trägt eine Einstufung, die niemand verantwortet.

**Die drei Antworten kommen zusammen oder gar nicht.** Ein Teil-Update wäre
falsch: die Attestierung ist eine Erklärung zu einem Zeitpunkt, keine Sammlung
unabhängiger Felder. Deshalb ein eigener Endpunkt
`PUT /tools/{id}/attestierungen`, der alle drei verlangt und Zeitpunkt und
Person **serverseitig** setzt — A.6 verlangt die Erklärung „mit Namen, nicht als
Formularfeld", und ein mitgeschicktes Datum wäre kein Nachweis.

`NULL` heißt unbeantwortet und ist von einem erklärten „Nein" zu unterscheiden.
Bestandsdaten wurden deshalb nicht mit `false` vorbelegt: das wäre eine
Erklärung, die niemand abgegeben hat. Die Oberfläche zeigt den offenen Zustand
als leere segmentierte Steuerung, nicht als Schalter in Ruhestellung.

## E-23 — Attestierung 1 ist die zweite Quelle der Mitbestimmung

E-19 hielt fest, dass die zweite Hälfte der A.5-Regel — die Wirkung auf Einzelne
— aus Stammdaten allein nicht bestimmbar ist, und kündigte für AP-3 eine zweite
Quelle an. Das ist Attestierung 1: „Fließt das Ergebnis in eine Entscheidung
über einzelne Personen?"

Trägt ein verknüpftes Tool-Objekt hier ein erklärtes Ja, gilt die zweite Hälfte
als erfüllt. Das Flag entsteht damit aus drei Quellen, in dieser Reihenfolge
geprüft: besondere Datenkategorie (A.7 zählt dort Entgelt, Gesundheit und
Leistungsbewertung auf), erklärte Entscheidung über Personen (A.6), oder
MB-Stufe ≥ 2 aus der Bewertung (A.8.3).

Attestierung 2 fließt **nicht** in die Mitbestimmung ein. Sie entscheidet, ob
ein Tool verändert oder gestaltet — eine andere Frage. Ein Prozess, dessen
Ergebnis über einzelne Personen entscheidet, ist mitbestimmungsrelevant, ob nun
ein Mensch das Ergebnis prüft oder nicht.

**Folge:** Attestieren und Verknüpfen ziehen die Ableitung nach. Beide Wege —
`PUT /attestierungen` und `POST|DELETE /prozesse` — rufen
`ableitung.aktualisiere_kette`, sonst wäre das Flag nach einer korrigierten
Erklärung still veraltet.

## E-24 — Die Wirkungsart bleibt offen, statt „gestaltend" zu behaupten

A.6 stellt drei Signale nebeneinander: Schreibzugriff macht ein Tool immer
verändernd; fehlt ein Mensch zwischen Output und Wirkung, ist es das auch bei
reinem Lesen. Der Umkehrschluss steht dort nicht — und lässt sich auch nicht
ziehen, solange Attestierung 2 unbeantwortet ist.

`GET /tools/{id}` liefert deshalb `wirkungsart: null` mit dem Grund `offen`,
wenn ein Tool nur liest und niemand erklärt hat, ob ein Mensch dazwischensteht.
Erst mit der Erklärung wird daraus `gestaltend`. Die Alternative — Schweigen als
„gestaltend" zu lesen — wäre genau der Fehler, vor dem die Warnung in A.6 steht.

Mitgeliefert wird immer der Grund (`schreibzugriff`, `kein_mensch`,
`nur_lesend`, `offen`) als Schlüssel, nicht als Satz: die Übersetzung gehört in
die Oberfläche, die Regel ins Backend.

## E-25 — Zweckbindung wird zweistufig geprüft

A.4.6 formuliert die Abweichung als „ein Tool verwendet ein Datenobjekt, dessen
Kategorie der zugeordnete Prozess nicht abdeckt". Wörtlich genommen prüft das
die Kategorie; praktisch interessiert zuerst das Objekt selbst.

`GET /tools/{id}/datenobjekte` liefert deshalb je Kante zwei Wahrheitswerte:

* `im_prozessrahmen` — das Datenobjekt ist an mindestens einem verknüpften
  Prozessobjekt als Input oder Output deklariert.
* `kategorie_gedeckt` — der schwächere Test aus A.4.6: seine Kategorie kommt im
  Rahmen wenigstens vor.

Aus dem ersten folgt der zweite. Die Oberfläche unterscheidet beide Befunde
sichtbar: „Außerhalb des Prozessrahmens" (rot) für die echte Abweichung nach
A.4.6, „Nicht deklariert" (gelb) für den milderen Fall, in dem die Kategorie
gedeckt ist, das Objekt selbst aber nicht erklärt wurde. Eine gemeinsame Warnung
für beide würde die schwerwiegende in der häufigen ertränken.

Ein Tool ohne Prozesskante hat gar keinen Rahmen; dann ist beides unerfüllt, und
die Oberfläche sagt das statt zu warnen.

## E-26 — Kantenänderungen brauchen einen eigenen Protokollpfad

`protokolliere_aenderung` vergleicht Spaltenwerte und schweigt, wenn sich keiner
geändert hat. Eine neue Verknüpfung ändert aber keine Spalte des Knotens,
sondern schreibt in eine Verknüpfungstabelle — die Aufrufe an den
Tool-Prozess-Kanten haben deshalb **nie** einen Eintrag erzeugt, obwohl der Code
danach aussah.

Neu ist `protokolliere_kante`: sie schreibt immer und trägt die Kante selbst als
Vorher/Nachher-Paar ein. Verwendet wird sie für Tool↔Prozess und
Tool↔Datenobjekt, einschließlich der geänderten Zugriffsart — die entscheidet
nach A.6 über die Wirkungsart und ist damit selbst governance-relevant.

## E-27 — Keine Sammelregel auf `button`

Gemeldet aus dem Betrieb: im Referenz-Wähler stand nur beim hervorgehobenen
Treffer der Name; bei allen übrigen war die Zeile leer. Der Name war da — weiß
auf weiß.

**Ursache** war nicht die Trefferliste, sondern eine Regel aus `src/stil.css`,
dem Stylesheet aus der Zeit vor dem Design-System:

```css
button, .knopf { … background: var(--farbe-akzent); color: var(--text-auf-akzent); }
```

Sie färbte **jeden** `button` der Anwendung akzentblau mit weißer Schrift und
stand wegen der Importreihenfolge nach `ui.css`. Bausteine mit eigener Fläche
setzen ihre Schriftfarbe meist mit; die Trefferzeile setzte nur
`background: none` und erbte damit die weiße Schrift auf die weiße Klappliste.
Dass jemand vorher schon eine Ausnahmeliste für `margin-block-start`
angelegt hatte — `.k-knopf, .k-zeile, .k-chip button, .k-segmente button,
.k-referenz .treffer button` — zeigt, dass die Regel bereits als Störung
empfunden, aber umgangen statt aufgehoben wurde.

**Entschieden:** Die Sammelregel gilt nur noch für `.knopf`. Die noch nicht
umgestellten Seiten (Bewertung, Gates, Selbstverpflichtung, Lenkung,
Prozess-Governance) tragen die Klasse ausdrücklich, bis sie in AP-4 bis AP-9
auf den Baustein `Knopf` wechseln. Kein Baustein hängt mehr an der
Kaskadenreihenfolge.

Zusätzlich setzen `.k-feld`-Eingaben, das Suchfeld und die Trefferzeile ihre
Schriftfarbe jetzt selbst, statt sie zu erben. Das ist keine Dopplung, sondern
dieselbe Regel wie bei Flächen: ein Baustein bringt seine Farben mit.

**Nebenbefund, mit behoben:** `color-scheme` stand fest auf `light dark` und
folgte damit dem Gerät, nicht der gewählten Darstellung. Wer auf einem dunklen
Telefon „Hell" wählt, bekam vom Browser dunkel gemalte Eigenflächen —
Bildlaufleisten, die Klappliste eines `select`, ausgefüllte Felder — in einer
hell gemalten Anwendung. Jetzt folgt `color-scheme` dem Attribut
`data-farbschema`.

**Abgesichert** in `e2e/darstellung.spec.ts`: für alle sechs Kombinationen aus
Darstellung und Geräteschema muss jede Trefferzeile im Wähler ihren Namen
tragen und im Kontrast zu der Fläche stehen, auf der sie steht. Gegen den alten
Stand schlägt der Test fehl — geprüft.

## E-28 — Der Vorgangskatalog steht neben den Tests, nicht in ihnen

Die technischen Tests beantworten „funktioniert es". Sie sagen nichts darüber,
ob die Anwendung **vollständig** ist — ein Handgriff, den niemand vorgesehen
hat, fehlt in beiden: im Code und im Test.

Deshalb ein zweites Artefakt: `docs/vorgaenge.md` listet jeden Vorgang auf, den
ein Anwender später ausführt, mit Rolle, erwartetem Ergebnis und dem
Arbeitspaket, das ihn trägt. Der ausführbare Teil steht in `frontend/vorgaenge/`
mit eigener Playwright-Konfiguration, eigener Datenbank
(`governance_vorgaenge`) und eigenem Befehl `npm run vorgaenge`.

**Getrennt gehalten**, weil beide Durchläufe verschiedene Fragen stellen und
verschieden altern: die Abnahmetests je Phase hängen an Architektur 11, der
Katalog an der Sicht des Bedieners. Eine gemeinsame Datei hätte beides vermischt.

**Offene Vorgänge bleiben in der Liste**, als übersprungen mit ihrem
Arbeitspaket als Grund. Eine Spezifikation, aus der Unfertiges verschwindet,
verliert genau die Aussage, für die es sie gibt.

**Der Katalog prüft sich selbst** (`vorgaenge/katalog.vorgang.ts`): jede
Kennung braucht genau einen Durchlauf und umgekehrt, jedes genannte
Arbeitspaket muss es geben, und ein Paket, dessen Punkte alle abgehakt sind,
darf keinen offenen Vorgang mehr tragen. Ohne diese Klammer wäre das Dokument
in zwei Wochen ein Wunschzettel.

### Was der Katalog erbracht hat

Die Liste wächst mit jedem Arbeitspaket. Sie steht hier und nicht im
Umsetzungsplan, weil sie die Frage beantwortet, ob sich der Katalog lohnt.

**Beim Aufsetzen** — beide behoben:

* `lokale_abweichung` an der Prozessumsetzung konnte die API seit Phase 1, die
  Oberfläche fragte sie nie ab (V-PRO-14). Derselbe Fehlertyp wie B5.
* Auf der Datenobjekt-Detailseite überschrieb die Antwort einer nebenher
  laufenden Änderung, was der Anwender inzwischen ins Quellsystem-Feld getippt
  hatte (V-DAT-09). Freitext ist jetzt ein eigener Entwurfszustand.

Ein dritter Befund blieb als Korrektur am Katalog: „Prozess wieder in Entwurf
setzen" gab es als Übersetzungstext, aber weder als Vorgabe noch als Aktion.
Der Vorgang heißt jetzt „wieder in Betrieb nehmen", der verwaiste Textbaustein
ist entfernt.

**In AP-4:** V-BEW-12 verlangt, dass jede Bewertungsversion „mit Datum und
Profil nachvollziehbar" ist. Die Historie zeigte weder ein Datum noch, welche
Version die maßgebliche war — bei einem versionierten Objekt, dessen ganzer
Sinn die Nachvollziehbarkeit ist. Beides ergänzt.

**In AP-5:** zwei Stellen, an denen der Katalog etwas verlangte, das die
Umsetzung nicht leistete.

* V-GAT-03 sagt: „Die Ablehnung verlangt eine Begründung." Die tat sie nicht —
  eine Ablehnung mit leerem Kommentar ging durch. Wer abgelehnt wird, erfährt
  dann nur, dass es nicht weitergeht, aber nicht, was zu ändern wäre. Jetzt
  weist der Server sie ab und die Oberfläche sperrt den Knopf.
* V-GAT-05 sagt: „Nur die fünf benannten Auslöser stehen zur Wahl." Sie standen
  zur Wahl — aber mit ihrem technischen Schlüssel als Beschriftung
  (`neues_externes_ziel`). Auf dem Bildschirm gehört der Name hin, nicht die
  Kennung.

**In AP-6:** drei Befunde, davon einer in einem Abnahmetest.

* V-RAH-04 und V-RAH-09 lesen die Frist als **Zahl** ab. Damit fiel auf, dass
  der Abnahmetest aus Phase 5 seinen „Tier-3-Tool" nie attestiert hatte: ohne
  die drei Erklärungen aus A.6 gibt es keine Prozesskante, das Tool erbte
  nichts, und die tier-abhängige Frist wurde gegen den Tier-1-Rückfall geprüft.
  Der Test hatte drei Phasen lang bestanden, ohne zu prüfen, was sein Name sagt.
* V-TOO-18 verknüpft ein Datenobjekt und sieht danach in den Rahmen. Die Karte
  zeigte den alten Stand — sie lud einmal beim Aufbau und nie wieder. Also
  genau dann nicht die Abweichung, wegen der jemand hinsieht.
* V-RAH-03 wählt ein Schicht-2-Verbot aus. Die Auswahl war nicht eindeutig
  ansprechbar, weil der Hilfetext eines Umschalters in dessen zugänglichem
  Namen steckte und dieselbe Wortfolge enthielt. Ein Vorleseprogramm hätte den
  ganzen Satz als Namen des Schalters gelesen; der Text hängt jetzt über
  `aria-describedby` daran, wie bei Feld und Auswahl.

**In AP-7 bis AP-9:** vier Befunde, die alle denselben Ursprung haben — ein
Vorgang liest, was auf dem Bildschirm steht, und stolpert über das, was ein
Test mit `getByTestId` nie bemerkt hätte.

* V-KLA-02 liest die Matrix. Die Zeilenköpfe standen in **Versalien**, weil die
  Übergangsstile für rohe Tabellen `text-transform: uppercase` global setzen —
  auf Produktnamen angewandt ist das schlicht falsch geschrieben.
* V-ADM-02 wählt einen Geltungsbereich. Zwei Felder hießen „Geltungsbereich"
  und „Bereich"; für ein Vorleseprogramm ist das dasselbe Wort. Sie heißen
  jetzt nach dem, was gewählt wird — „Fachbereich" oder „Organisationseinheit".
* V-COC-08 prüft den Befund „Antwort widerspricht Datenlage". Beim Schreiben
  fiel auf, dass eine **begründete** Abweichung gar kein Befund ist (E-30) —
  der Vorgang muss die Datenlage nach der Bewertung ändern, sonst prüft er
  nichts. Das ist keine Korrektur am Code, sondern eine am Verständnis.
* Der Nachweis zeigte **UUIDs** als Feldwerte („eingereicht_von: —
  → 5883a1a8-…"). Personenfelder werden jetzt zu Namen aufgelöst, reine
  Beziehungsfelder ganz weggelassen und Zeitstempel auf die Minute gekürzt.

## E-29 — Ein „ja" braucht einen Beleg, ein „nein" braucht Vollständigkeit

Der Vorschlagsdienst nach A.8.4 (`services/vorschlag.py`) rechnet vor, was die
vorhandenen Daten zu einer Bewertungsfrage hergeben. Die Versuchung ist, dabei
möglichst viel zu beantworten — jede abgeleitete Dimension ist eine Frage
weniger. Genau das wäre falsch, denn die **Abweichung vom Vorschlag ist
begründungspflichtig**. Ein geratener Vorschlag kostet den Anwender einen Satz
Rechtfertigung für etwas, das das System gar nicht wusste. Ein falscher
Vorschlag ist damit schlechter als keiner.

Deshalb zwei asymmetrische Regeln:

* **Positiv** wird nur vorgeschlagen, was ein konkretes Objekt hergibt. Der
  Vorschlag nennt es beim Namen: „Datenobjekt ‚Entgeltdaten' trägt die
  Kategorie besondere Kategorie."
* **Negativ** nur bei geschlossener Datenlage. Ein Datenobjekt ohne Kategorie
  kann alles sein und verbietet jedes „nein"; ein Prozess ganz ohne
  Datenobjekt erst recht.

Was keine der beiden Regeln erfüllt, bleibt **offen** — frei beantwortbar, ohne
Begründungspflicht. Das ist derselbe Gedanke wie E-24 zur Wirkungsart: kein
Vorschlag ist ein gültiger Zustand.

Konkrete Folgen dieser Regeln:

* **Frage 2a** („besondere Kategorien **oder** Profilbildung") bekommt nur ein
  „ja". Die erste Hälfte steht in den Daten, die zweite nicht — ein „nein"
  würde behaupten, dass keine Profilbildung stattfindet, und das weiß nur der
  Prozesseigner.
* **Frage 2b** geht in beide Richtungen, weil die fünf Kategorien aus A.7
  abschließend sind: „keine davon ist personenbezogen" ist eine Antwort und
  kein Schweigen.
* **Frage 2c** bekommt ein „nein" nur, wenn ausnahmslos alles öffentlich ist.
  „intern" oder „vertraulich" kann sehr wohl personenbeziehbar sein.
* **Der Kundenkreis** wirkt ausschließlich negativ: „extern" verhindert das
  „nein" bei 2b, statt ein „ja" zu behaupten. Ein Prozess mit externem
  Kundenkreis kann eine Preisliste veröffentlichen und dabei keine einzige
  personenbezogene Angabe verarbeiten.
* **KI, IT und RG** bekommen gar keinen Vorschlag. A.8.4 nennt KI und RG als
  vollständig zu erklären; IT wäre aus Telemetrie abzuleiten, die diese
  Plattform nicht hat.

**UR ist die einzige vollständig ableitbare Dimension**, weil die Ausfallfolge
ein Pflichtfeld ist und die Vererbung entlang der Kette gerechnet wird (A.4.2).
Ihre drei Fragen bekommen deshalb einen Vorschlag in beide Richtungen, und der
Beleg nennt den nachgelagerten Prozess, wenn die Stufe von dort stammt.

Die Konjunktion aus A.5 wird für MB **nicht nachgebaut**, sondern aus
`ableitung.mitbestimmung_aus_daten` aufgerufen. Diese Funktion kennt bewusst
keine Bewertung: ein Vorschlag, der die letzte Antwort auf dieselbe Frage
zitiert, wäre ein Zirkelschluss statt einer Ableitung.

## E-30 — Der gespeicherte Vorschlag trennt Entscheidung von Verfall

Die Bewertung hält ab AP-4 nicht nur fest, **was** geantwortet wurde, sondern
auch, **was die Datenlage zum selben Zeitpunkt hergab** (`vorschlaege`) und, wo
beides auseinanderfiel, **warum** (`abweichungen`). Der Mehraufwand einer
zusätzlichen Spalte trägt eine Unterscheidung, die sonst unmöglich wäre.

Die Cockpit-Zeile „Antwort widerspricht Datenlage" vergleicht die gespeicherten
Antworten mit den **heutigen** Vorschlägen. Drei Fälle sehen gleich aus:

1. **Bewusst abgewichen, begründet, Datenlage unverändert.** Kein Befund,
   sondern eine dokumentierte Entscheidung — A.8.4 lässt die Abweichung
   ausdrücklich zu, wenn sie erklärt wird.
2. **Die Daten haben sich seither geändert.** Ein Datenobjekt wurde
   umklassifiziert, ein Tool hat attestiert, ein Nachfolgeprozess ist kritischer
   geworden. Die Antwort von damals steht neben einer neuen Wirklichkeit, und
   eine Begründung von damals bezieht sich auf eine Lage, die es nicht mehr
   gibt.
3. **Damals war nichts abzuleiten, heute schon.** Kein Vorwurf: die Grundlage
   für den Vorschlag entstand erst später. Bewertungen von vor AP-4 fallen
   ebenfalls hierunter, weil zu ihnen überhaupt kein Vorschlag gerechnet wurde.

Nur der erste Fall verschwindet aus der Zeile; die anderen beiden nennt der
Hinweis beim Namen. Ohne den mitgespeicherten Vorschlag wären alle drei
ununterscheidbar, und die Zeile wäre entweder blind für den Verfall oder ein
Dauerärgernis für jede bewusst getroffene Entscheidung.

Die Begründungspflicht sitzt **im Wizard-Schritt**, nicht erst beim Speichern.
Wer erst am Ende erfährt, dass Frage 2b eine Begründung braucht, müsste sich an
eine Entscheidung von vor fünf Bildschirmen erinnern. Eine Begründung zu einer
Frage, die am Ende doch nicht abweicht, wird nicht mitgespeichert: sie würde
eine Abweichung dokumentieren, die es nicht gibt.

## E-31 — Die Auflagen je Tier stehen neben den K-Klassen, nicht in ihnen

Die Ergebnisseite zeigt zwei Listen, und das ist Absicht. Die **K-Klassen** aus
A.9.2 hängen am Profil und sagen, *was* dieser Prozess wegen seiner
Eigenschaften braucht — K4 wegen DS 3, K7 wegen MB. Die **Auflagen** aus A.8.6
hängen allein am erreichten Tier und sagen, *wie streng* er insgesamt geführt
wird. Sie gelten kumulativ: Tier 3 trägt auch die Auflagen von Tier 2 und 1.

Beides in eine Liste zu werfen hätte den Unterschied verwischt, an dem später
die Rückfrage hängt: „warum gilt das für uns?" Bei einer K-Klasse ist die
Antwort eine Profilstelle, bei einer Auflage das Tier.

Jede K-Klasse steht mit **Namen und einem Erklärungssatz** da, nicht als
Kürzel. Das Kürzel bleibt als Abzeichen davor, weil Query-API, Historie und
Nachweis damit arbeiten. Eine Ergebnisseite, die nur „K4" anzeigt, verlagert
die Übersetzungsarbeit auf den Leser — genau das soll sie nach Architektur 9.1
nicht.

Wie schon bei E-7 gilt: das Leitdokument liegt diesem Repository nicht bei. Die
Auflagen sind in `services/bewertung.py` so ausformuliert, dass sie zu dem
passen, was die Plattform tatsächlich tut — die Jahresfrist ab Tier 3 etwa
entspricht der bereits vorhandenen `gueltig_bis`-Logik.


> **Nachtrag vom 02.09.2026:** Das Leitdokument liegt seit heute bei (`docs/leitdokument.md`). Der Abgleich hat gezeigt, dass die hier beschriebene Fassung von der damaligen Vorgabe abweicht — die Entscheidung fiel, **das Dokument** an den Code anzupassen, nicht umgekehrt (E-48). Was unten steht, ist damit nicht mehr meine Auslegung, sondern die geltende Fassung.

## E-32 — Zustimmung zu Text A ist keine Zustimmung zu Text B

Der Aussagenkatalog der Selbstverpflichtung war frei erfunden (E-10, weil das
Leitdokument nicht beilag) und sagte nachweislich etwas anderes als A.10.2 und
A.10.3. Vier der sechs Prozesseigner-Aussagen fehlten ganz — Zweck,
Empfängerkreis, Absicht, Nachweispflicht —, und ausgerechnet das sind die, die
A.10.1 als „nicht skalierend messbar" begründet. Der Baustein, der die
Messlücke schließen sollte, schloss sie nicht.

Beim Umstellen gab es zwei Wege. Man hätte die Texte hinter den vorhandenen
Kennungen `P1`…`P6` austauschen können — dann hätte jede bestehende Erklärung
plötzlich etwas bestätigt, das nie jemand gelesen hat. Das ist bei einer
Erklärung, die persönlich abgegeben wird, nicht vertretbar.

Deshalb: **neue Kennungen** (`PE1`…`PE6`, `TO1`…`TO6`), die sich von den alten
unterscheiden, plus eine `katalog_version` an jeder Erklärung. Bestandsdaten
werden nicht umgeschrieben. Sie bleiben in der Historie lesbar, zählen aber
nicht mehr als Deckung, und der Grund steht wörtlich da: „nach einem früheren
Aussagenkatalog abgegeben". Wer betroffen ist, sieht es im Cockpit.

**A.10.4 schließt pauschale Formeln aus**: „spezifisch statt pauschal —
konkrete Aussagen sind im Nachhinein prüfbar, allgemeine Zusagen nicht." Die
alte Aussage „Die Bewertung wurde **nach bestem Wissen** durchgeführt" ist
genau das, was damit gemeint ist: nicht widerlegbar und deshalb wertlos. Ein
Test hält fest, dass die Formulierung im Katalog nicht vorkommt.

**Die Schicht-2-Verbote sind aus A.10.3 entfernt.** Umgangene
Unternehmensidentität und statische Zugangsdaten standen dort als Aussagen T2
und T3. Sie gehören nicht in eine Erklärung: A.13.2 verbietet sie
organisationsweit und „durch keine Prozessbewertung freischaltbar". Was
ausnahmslos gilt, wird durchgesetzt und nicht erklärt — die Umsetzung steht in
AP-6.

## E-33 — Die Erklärung verfällt mit dem Profil, nicht mit dem Kalender

Bis AP-5 hing die Gültigkeit einer Selbstverpflichtung allein an `gueltig_bis`.
A.10.4 verlangt etwas anderes: „an die Profilversion gebunden — ändert sich das
Profil, verfällt die Erklärung automatisch."

Das ist der eigentliche Zweck des Bausteins. Wer erklärt „das Ergebnis wird
nicht zur Kontrolle einzelner Beschäftigter verwendet", erklärt das über einen
bestimmten Prozess in einem bestimmten Zustand. Wird derselbe Prozess neu
bewertet, weil er jetzt Personaldaten verarbeitet, bezieht sich die Erklärung
auf einen Sachverhalt, den es nicht mehr gibt. Eine Erklärung, die eine
Neubewertung überlebt, ist schlimmer als keine: sie sieht aus wie Deckung.

Umgesetzt über `bewertung_id` an der Erklärung. **Tool-Objekte bekommen keine
solche Bindung**, weil ihr Tier geerbt ist und aus mehreren Prozessen stammen
kann — eine einzelne Bewertungs-ID wäre dort willkürlich. Bei ihnen trägt
`tier_bei_abgabe` dieselbe Aufgabe: steigt das geerbte Tier, deckt die
Erklärung weniger ab, als jetzt verlangt wird.

Statt eines Wahrheitswerts liefert der Server ein **Deckungsurteil mit Grund**:
`keine`, `unvollstaendig`, `alter_katalog`, `profil_veraltet`,
`tier_gestiegen`, `frist_abgelaufen`. Der Unterschied ist für den Owner
handlungsleitend — bei abgelaufener Frist genügt ein Klick, bei verfallenem
Profil ist die Erklärung neu abzugeben. Die Oberfläche zeigt diesen Satz
wortgleich an und baut die Regel nicht nach.

**Die Kurzform aus A.10.5** steckt als `ab_tier` in den Aussagen selbst, nicht
in einer Verzweigung: bei Tier 1 werden nur die Aussagen mit `ab_tier == 1`
verlangt. Welche das sind, ist nicht willkürlich, sondern folgt den Dimensionen
— Empfängerkreis, Verwendung gegenüber Beschäftigten und Aufbewahrungspflicht
sind genau die Punkte, die ein Tier-1-Objekt gar nicht auslösen kann. Vollständig
heißt deshalb „jede **verlangte** Aussage bestätigt", nicht „alle sechs".

## E-34 — Bildschirmtext ist Deutsch, Quelltext ist ASCII

Bis AP-4 waren alle serverseitigen Zeichenketten umlautfrei: der Bewertungsbaum
fragte nach „Kuenstliche Intelligenz", die Maßnahmenklasse hieß
„Datenschutz-Folgenabschaetzung". Das fiel nicht auf, solange diese Texte in
Tests und Protokollen standen. Mit AP-4 rücken sie in die Mitte des
Bildschirms: der Vorschlag zu einer Frage soll gelesen und geglaubt werden, und
„Datenobjekt ‚Entgeltdaten' **traegt** die Kategorie" liest sich wie ein
Übertragungsfehler.

Die Regel lautet deshalb:

* **Was ein Mensch auf dem Bildschirm liest, ist richtiges Deutsch** — mit
  Umlauten und ß. Das gilt für Fragetexte, Belege, Klassennamen, Auflagen,
  Aussagen der Selbstverpflichtung, Cockpit-Hinweise und **Fehlermeldungen**;
  eine Fehlermeldung ist Bildschirmtext, auch wenn sie aus dem Server kommt.
* **Was nur im Quelltext steht, bleibt ASCII** — Docstrings, Kommentare,
  Bezeichner, Aufzählungswerte, Datenbankschlüssel.

Die Trennlinie verläuft also nicht zwischen Backend und Frontend, sondern
zwischen Text für Menschen und Text für Entwickler. Enum-Werte wie
`besondere_kategorie` bleiben ASCII, weil sie Schlüssel sind; ihre Beschriftung
lebt in der Übersetzungsdatei.

**Stand der Umstellung.** Umgestellt sind die Flächen, die AP-4 bis AP-9
angefasst haben: `bewertungsbaum.py` (Fragen und Blocktitel), `vorschlag.py`
(Belege), `bewertung.py` (Klassennamen, Erklärungen, Auflagen,
Begründungspflicht), `selbstverpflichtung.py` (die zwölf Aussagen und die
Deckungsgründe), mit AP-6 `lenkung.py`, `gate.py`, `query.py`, `prozess.py`
und die Beschreibungen der Konfigurationsschlüssel, mit AP-8 **alle**
Cockpit-Titel, -Beschreibungen und -Hinweise. `rahmen.py`, `klassen.py` und
`verwaltung.py` sind von Anfang an in richtigem Deutsch geschrieben. Die Tests,
die auf den alten Wortlaut zeigten, sind jeweils mitgezogen.

**Nicht umgestellt** sind zwölf Zeichenketten in `asset.py` (5),
`erinnerung.py` (2), `api/deps.py` (3) sowie den Routern `admin.py` und
`auth.py` (je 1) — die Module, die seit AP-3 kein Arbeitspaket mehr berührt
hat. Sie sind als offener
Punkt in der Definition of Done geführt und werden mit dem jeweiligen
Arbeitspaket mitgezogen, statt in einem großen Durchlauf: eine Sammeländerung
brächte Testbruch ohne fachlichen Bezug und wäre schlecht zu prüfen.

## E-35 — Die Anwendervorgänge kennen keine Schleichwege

Der Vorgangskatalog prüft, was ein Anwender tun kann. Ein Testendpunkt, der
einen Zustand herstellt, den es über die Oberfläche nicht gibt, würde genau
diese Aussage aufheben — und stünde als Produktionscode in der API.

V-SEL-07 („Die Jahresbestätigung ab Tier 3 abgeben") brauchte eine abgelaufene
Erklärung. Naheliegend wäre `POST /testhilfe/frist-vorziehen` gewesen. Statt
dessen setzt der Vorgang die Gültigkeitsdauer über die **vorhandene
Konfiguration** auf null Tage — das ist eine echte Handlung der
Governance-Rolle (Architektur 6.6, Vorgang V-RAH-10), keine Hintertür. Die
Erklärung ist damit mit ihrer Abgabe fällig, und der Vorgang zeigt genau den
Bildschirm, den ein Owner nach einem Jahr sieht.

Zwei Regeln folgen daraus:

* **Vorbedingungen über die API sind erlaubt**, wo sie eine Rolle herstellen,
  die der Geprüfte selbst nicht vergeben darf — das steht als Kommentar am Ort.
  Der geprüfte Vorgang selbst läuft über die Oberfläche.
* **Global wirksame Einstellungen werden zurückgestellt**, und zwar sofort nach
  der Beobachtung, nicht am Ende des Durchlaufs. Ein Vorgang, der auf halbem
  Weg scheitert, darf den folgenden keine Nullfrist hinterlassen.

## E-36 — Klassennamen des Design-Systems tragen `k-`

Die Bausteine heißen `k-karte`, `k-zeile`, `k-abzeichen`. Innerhalb eines
Bausteins dürfen verschachtelte Namen schlicht sein — `.k-karte > header`,
`.k-seitenkopf .titelblock` —, weil der Elternselektor sie einschließt.

Diese Freiheit hat eine Grenze, die AP-5 auf die harte Tour gezeigt hat: das
Anwendungslayout benutzt einige **unpräfixierte** Klassen global, darunter
`.inhalt` für den Seiteninhaltsbereich mit einem Innenabstand von 32 px. Ein
neuer Baustein mit einem `<div className="inhalt">` erbte diesen Abstand
lautlos und riss achtzig Pixel Leerraum in jeden Aussagenblock der
Selbstverpflichtung.

Die Regel ist deshalb schärfer als „Präfix an der Wurzel": **ein
verschachtelter Name darf nicht so heißen wie eine der wenigen unpräfixierten
Klassen der Anwendungshülle**. Das sind, Stand heute, `huelle`,
`seitenleiste`, `seitenleiste-fuss`, `nutzerzeile`, `inhalt`, `anmeldeflaeche`
und `anmeldekarte` in `src/stil/basis.css` — sie beschreiben das Gerüst, nicht
die Bausteine, und tragen deshalb kein `k-`. Im Zweifel ein Wort wählen, das
den Inhalt benennt: der Block heißt jetzt `.satz`, weil dort ein Satz steht.

## E-37 — Schicht 2 ist eine Liste von sechs Sätzen, keine offene Meldung

A.13.2 nennt sechs organisationsweite Verbote, „durch keine Prozessbewertung
freischaltbar". Das Leitdokument liegt diesem Repository nicht bei (wie schon
bei E-7 und E-31), aber zwei der sechs sind über E-32 wörtlich bekannt: die
umgangene Unternehmensidentität und statisch hinterlegte Zugangsdaten. Sie
standen bis AP-5 fälschlich im Aussagenkatalog der Selbstverpflichtung.

Die sechs sind hier als `Schicht2Verbot` ausformuliert — abschließend wie die
fünf Gate-2-Auslöser und aus demselben Grund: eine Liste, die sich um einen
freien siebten Grund ergänzen lässt, ist keine Liste mehr. Wo der Wortlaut aus
dem Dokument nicht vorlag, ist er so gewählt, dass er zu dem passt, was die
Plattform tatsächlich erfassen kann.

**Vier der sechs erkennt die Anwendung selbst**, aus Daten, die sie ohnehin
hat: das geteilte Konto aus der Ausführungsidentität, die statischen
Zugangsdaten aus ihrem Feld, die undeklarierten Quellen aus Attestierung 3 und
die automatisierte Entscheidung über Personen aus Attestierung 1 zusammen mit
Attestierung 2. Die übrigen beiden — Datenabfluss aus der freigegebenen
Infrastruktur und umgangene Protokollierung — betreffen Vorgänge in der
Zielplattform, von denen die Governance-Plattform nichts sieht; sie sind zu
melden. Beides steht in der Antwort der API (`automatisch_erkennbar`), damit
niemand die eine Hälfte für die ganze Wahrheit hält.

Die Folge eines Schicht-2-Verstoßes ist nicht Verhandlung, sondern Abstellen:
A.13.5 streicht bei ihnen die erste Eskalationsstufe. Der Lenkungsvorgang
beginnt deshalb in Stufe 2, mit der kurzen Nachfrist und der sofortigen
Meldung an die Führungskraft. Eine Meldung mit Verbot **und** gelber Farbe wird
abgewiesen: was keine Bewertung freischaltet, ist keine Beobachtung.

Ein laufender Stufe-1-Vorgang wird durch eine spätere Schicht-2-Meldung
angehoben, statt daneben einen zweiten zu eröffnen. Sonst hätte die Reihenfolge
der Meldungen über die Schwere entschieden.


> **Nachtrag vom 02.09.2026:** Das Leitdokument liegt seit heute bei (`docs/leitdokument.md`). Der Abgleich hat gezeigt, dass die hier beschriebene Fassung von der damaligen Vorgabe abweicht — die Entscheidung fiel, **das Dokument** an den Code anzupassen, nicht umgekehrt (E-48). Was unten steht, ist damit nicht mehr meine Auslegung, sondern die geltende Fassung.

## E-38 — Der Rahmen zeigt neben jedem erlaubten Wert den gemessenen

A.13.2 Schicht 1 listet sieben Rahmenelemente; umgesetzt waren drei. Die vier
fehlenden brauchten nicht nur eine Ableitung, sondern je ein **Gegenstück am
Tool**, gegen das sie sich prüfen lässt. Ein Rahmen ohne Messung ist eine
Behauptung; erst der Vergleich macht eine Abweichung sichtbar.

| Element | Erlaubt aus | Gemessen an |
|---|---|---|
| Datenobjekte | Input und Output der Prozesskanten | den Tool-Datenobjekt-Kanten |
| Obergrenze der Datenkategorie | höchster Kategorie im Rahmen | höchster Kategorie der genutzten Objekte |
| Reichweite | Maximum-Vererbung (A.4.4) | **nichts** |
| Externe Ziele | `erlaubte_externe_ziele` der Prozesse | `externe_ziele` des Tools |
| Zugriffsart | der Output-Kante (A.4.1) | der Zugriffsart je Kante |
| Ausführungsart | Attestierung 2 | dem Lauftyp |
| Ausführungsidentität | der Ausführungsart | `ausfuehrungsidentitaet` |

Die Reichweite ist der einzige Fall ohne Messung: sie ist nach A.4.4 geerbt und
nach P1 nie eingegeben, es gibt am Tool nichts, wogegen sie zu prüfen wäre. Das
steht als Satz auf dem Bildschirm — „Nicht gemessen — abgeleitet" —, statt eine
leere Spalte zu zeigen, die wie eine Messung ohne Befund aussähe.

**Die Zugriffsart kommt aus dem Prozess, nicht aus der Wirkungsart.** Der
naheliegende Weg wäre gewesen, „darf schreiben" aus der Triage `verändernd` zu
folgern. Das wäre ein Zirkel: `bestimme_wirkungsart` leitet `verändernd`
gerade daraus ab, dass ein Tool Schreibzugriff hat. Jede Schreibkante hätte
sich damit selbst genehmigt. Stattdessen gilt A.4.1: die Output-Kante des
SIPOC ist die Schreibkante. Ein Tool darf nur dort schreiben, wo der Prozess
das Datenobjekt als Ergebnis führt — und die Abweichung nennt dann das
Datenobjekt, nicht die Zugriffsart, weil damit jemand etwas anfangen kann.

**Die Ausführungsart hängt an Attestierung 2** (so führt A.13.2 sie zurück).
Steht ein Mensch zwischen Output und Wirkung, ist jede Ausführungsart gedeckt;
steht keiner dazwischen, bleibt nur die interaktive, denn ein Lauf ohne
Anwesenden wäre ein Tool, das allein handelt. Ohne Attestierung ist **nichts**
gedeckt — nicht alles: was nicht erklärt ist, ist nicht erlaubt.

Die Ausführungsidentität folgt daraus: interaktiv heißt, ein Mensch bedient,
also läuft es unter dessen Identität; getriggert oder geplant heißt, niemand
ist da, der eine Identität leihen könnte, und dann ist eine benannte
Dienstidentität die einzige, die sich später noch zuordnen lässt.

Die **Query-API bekommt nur die erlaubte Seite**. Eine andockende Anwendung
fragt, was erlaubt ist; was am Tool gemessen wurde, ist ihre eigene Sache. Die
gemessene Spalte steht dort, wo jemand sitzt, der die Abweichung abstellen
kann — am Tool-Objekt.

## E-39 — Fristen laufen in Arbeitstagen, und die zweite Stufe verkürzt

Die Lenkungsfristen standen auf 90/30/14 **Kalendertagen**; A.13.5 verlangt
30/15/5 **Arbeitstage**. Ein Tier-1-Fall lief damit ein halbes Jahr statt sechs
Wochen. Schwerer wog der zweite Fehler: die Eskalation setzte für Stufe 2
erneut die volle Tier-Frist an, statt der Nachfrist von 15/10/5. Die Eskalation
soll den Druck erhöhen; sie drehte die Uhr zurück.

Beides ist berichtigt, mit eigenen Konfigurationsschlüsseln je Stufe. Ab Stufe
3 gibt es **keine** Frist mehr: dort steht die technische Maßnahme an, es ist
nichts mehr abzuwarten. Die Frist bleibt deshalb stehen, wie sie war —
abgelaufen.

**Feiertage bleiben außen vor.** Ein Feiertagskalender ist landesabhängig, die
Anwendung läuft in mehreren Ländern, und eine halbe Lösung wäre hier schlechter
als eine erklärte Vereinfachung: ein Vorgang gewinnt dadurch höchstens einen
Tag, und die Fristen sind nicht auf den Tag genau gedacht, sondern als
Eskalationsdruck.

Die Arbeitstagrechnung steht **zweimal** — im Server (`lenkung.py`) und in der
Oberfläche (`nutzen/fristen.ts`). Das ist bewusst: der Server *setzt* die
Frist, die Oberfläche *liest* sie und zählt herunter. Eine Zahl vom Server
wäre beim Neuladen veraltet, und ein Countdown, der eine andere Zahl nennt als
die Eskalation verwendet, wäre schlimmer als keiner. Ein Test hält beide auf
derselben Zählweise fest.

Der Countdown unterscheidet **abgelaufen** von **null verbleibenden Tagen** an
der Uhrzeit, nicht am Vorzeichen: eine Frist, die heute um 14 Uhr endete, ist
um 15 Uhr abgelaufen, obwohl zwischen beiden kein Arbeitstag liegt. Null hat
kein Vorzeichen — deshalb liefert die Rechnung ein Wertepaar aus Tagen und
einem Kennzeichen, keine vorzeichenbehaftete Zahl.

## E-40 — Ein neu erklärtes externes Ziel reicht Gate 2 selbst ein

A.11 nennt „neues externes Ziel" als einen der fünf Gate-2-Auslöser. Bis AP-6
musste der Prozess-Owner das Ziel eintragen **und** anschließend selbst ein
Gate einreichen — also die Regel kennen und anwenden, die die Anwendung kennt.

Wer ein Ziel ergänzt, meldet damit den Auslöser. Der Gate-2-Vorgang entsteht
deshalb beim Speichern von selbst, mit dem Ziel in der Begründung. Drei
Einschränkungen halten das eng:

* **Nur an einem aktiven Prozessobjekt.** Ein Entwurf hat noch keinen Rahmen,
  den er verlassen könnte; seine Erstfreigabe läuft über Gate 1.
* **Nur bei einem wirklich neuen Ziel.** Verglichen wird vor dem Setzen; ein
  erneutes Speichern derselben Liste löst nichts aus.
* **Kein zweiter Vorgang**, solange einer offen ist. Der Vorgang ist schon da,
  und die neue Erklärung steht in der Historie des Prozessobjekts.

Die Folge steht am Feld, bevor jemand speichert. Eine Automatik, die erst nach
dem Klick erkennbar wird, ist eine Überraschung, keine Hilfe.

## E-41 — Die Auflösung „Rahmen erweitern" wählt eine Bewertung, keine Kennung

Die Lenkungsseite verlangte für „Rahmen erweitern" die **UUID** der neuen
Bewertung in einem Textfeld. Das verstößt gegen den dritten Grundsatz des
Design-Systems („Nie ein technischer Schlüssel im Sichtfeld") und ist
praktisch nicht bedienbar: niemand hat eine UUID zur Hand.

Jetzt lädt das Blatt die Bewertungen der betroffenen Prozessobjekte und zeigt
davon genau die, die **nach** der Eröffnung des Vorgangs entstanden sind — mit
Tier und Datum. Ältere bildet der erweiterte Rahmen nicht ab; der Server weist
sie ab, und was er abweist, bietet die Oberfläche gar nicht erst an. Gibt es
keine, steht der Satz da, was zuerst zu tun ist, statt eines Knopfes, der in
eine Ablehnung liefe.

Die drei Wege aus A.13.6 stehen als drei gleich aussehende Knöpfe nebeneinander
statt als Auswahlliste. Eine Auswahlliste hat einen Vorgabewert, ein Vorgabewert
ist eine Empfehlung — und das Leitdokument gibt keine.

## E-42 — Die Technologiematrix ist gepflegt, nicht einprogrammiert

A.9.1 beschreibt zwei Übersetzungsstufen: vom Profil zu den
Anforderungsklassen und von den Klassen zu einer Entscheidung über die
eingesetzte Technologie. Die erste war da, die zweite nicht — die Anwendung
sagte, welche Klassen ausgelöst sind, aber nicht, ob die gewählte Technologie
sie tragen kann. Damit fehlte genau die Entscheidung, auf die das
Bewertungsmodell zuläuft.

**Die Matrix liegt in der Datenbank, nicht im Code.** Sie ist eine
Entscheidungsgrundlage; eine, die nur mit einer Auslieferung änderbar wäre,
veraltet zwischen zwei Releases. Die Standardbelegung steht in
`services/klassen.py` und wird beim ersten Zugriff angelegt — ein fehlendes
Feld wird ergänzt, ein vorhandenes nie überschrieben. **Jedes Feld trägt eine
Pflichtbegründung**, auch die Standardbelegung: eine Farbe ohne Satz ist keine
Entscheidungsgrundlage, und wer ein Feld ändert, schuldet den Grund.

**Sieben der zehn Klassen stehen überall auf „erfüllt"**, und das ist kein
Versehen. Dokumentation, Selbstverpflichtung, benannter Owner,
Folgenabschätzung, KI-Transparenz, Mitbestimmung und Gate 2 sind
organisatorische Anforderungen — keine Plattform hindert jemanden daran, den
Betriebsrat zu beteiligen. Eine Matrix, die so täte, wäre falsch. Es
unterscheiden sich die drei technischen Klassen: das Zugriffs- und
Rechtekonzept (K5), die revisionssichere Aufbewahrung (K8) und das
Wiederanlaufkonzept (K9). Dort entscheidet das Werkzeug, überall sonst die
Organisation.

Wie schon bei E-7 und E-31 gilt: Teil C.1 liegt diesem Repository nicht bei.
Die Belegung ist so gewählt, dass sie zu dem passt, was die Plattform
tatsächlich erfassen kann, und jedes abweichende Feld begründet sich selbst.

**„Ungeprüft" ist eine eigene Befundart** und kein stiller Erfolg. Steht am
Tool keine Technologie, gibt es nichts abzugleichen — und eine fehlende Angabe
ist kein Nachweis. Sie erscheint deshalb als offener Befund im Cockpit, neben
dem Ausschluss und der fehlenden Kompensation: alle drei verlangen denselben
nächsten Schritt, nämlich eine Entscheidung.

**Ein Ausschluss lässt sich nicht wegkompensieren.** Der Server weist den
Versuch ab, und die Oberfläche bietet ihn gar nicht erst an. „Nicht erfüllbar"
ist nach A.9.3 ein Ausschlusskriterium; eine Kompensation darauf wäre die
Umgehung des Kriteriums, nicht seine Erfüllung. Umgekehrt braucht eine
erfüllte Klasse keine Maßnahme — auch das wird abgewiesen, damit die Liste der
Kompensationen aussagekräftig bleibt.

**Die Auslöserbedingung ist Text und hängt trotzdem an der Rechnung.** A.9.2
verlangt zu jeder Klasse Name, Zweck **und** die Bedingung, unter der sie
ausgelöst wird. Name und Zweck standen schon in `services/bewertung.py`; die
Bedingung ist neu und als Satz formuliert. Ein Satz kann von der Rechnung
abdriften — deshalb hält ein Test je Klasse ein auslösendes und ein nicht
auslösendes Profil gegen `leite_k_klassen_ab`.

**Die Technologieliste kommt vom Server.** Sie stand als Konstante in der
Oberfläche und hätte, sobald die Matrix dieselben Schlüssel benutzt,
auseinanderlaufen können: die eine Ansicht zeigte einen Namen, die andere
einen Schlüssel. Tool-Auswahl, Tool-Liste, Prozessdetail und Matrix lesen sie
jetzt aus derselben Quelle.


> **Nachtrag vom 02.09.2026:** Das Leitdokument liegt seit heute bei (`docs/leitdokument.md`). Der Abgleich hat gezeigt, dass die hier beschriebene Fassung von der damaligen Vorgabe abweicht — die Entscheidung fiel, **das Dokument** an den Code anzupassen, nicht umgekehrt (E-48). Was unten steht, ist damit nicht mehr meine Auslegung, sondern die geltende Fassung.

## E-43 — Eine Alt-Anwendung ist eine, die niemand angemeldet hat

A.16 beschreibt den Weg für Anwendungen, die es vor dem Rahmenwerk schon gab:
sie sind zu melden, und wer die Frist verstreichen lässt, landet im
Blockierungspfad. Die Cockpit-Zeile dazu fehlte.

**Woran erkennt die Anwendung eine Alt-Anwendung?** Ein Startdatum des
Rahmenwerks gibt es hier nicht, und ein solches Datum wäre auch das falsche
Kriterium — es gibt keinen Tag, an dem alle Anwendungen gleichzeitig bekannt
wurden. Das tragende Merkmal ist ein anderes: `herkunft = importiert`. Diese
Tool-Objekte hat der Sync **vorgefunden**; niemand hat sie angemeldet. Wer sein
Werkzeug selbst einträgt, ist den Weg gegangen und steht nicht auf dem Weg.

**Melde- und Blockierungspfad sind derselbe Fall zu verschiedenen Zeiten.** Die
offene Aufgabe ist in beiden dieselbe — bestätigen, zuordnen, den Prozess
bewerten. Was sie unterscheidet, ist die Frist: bis dahin Meldepfad, danach
Blockierungspfad. Deshalb eine Zeile mit zwei Zuständen und nicht zwei Zeilen;
der Hinweis nennt Pfad, Aufgabe und die Zahl der Tage.

Die Frist steht in der Konfiguration (`altanwendung_meldefrist_tage`,
Vorgabe 90) und ist damit dort, wo die anderen Governance-Fristen auch stehen —
sie ist Inhalt, kein Betriebsparameter.

**Wer den Weg hinter sich hat, verschwindet aus der Zeile.** Eine bestätigte,
einem bewerteten Prozess zugeordnete Alt-Anwendung ist keine Alt-Anwendung
mehr, sondern ein geführtes Tool-Objekt. Eine Zeile, die sie weiter mitführte,
würde die Zahl bedeutungslos machen.


> **Nachtrag vom 02.09.2026:** Das Leitdokument liegt seit heute bei (`docs/leitdokument.md`). Der Abgleich hat gezeigt, dass die hier beschriebene Fassung von der damaligen Vorgabe abweicht — die Entscheidung fiel, **das Dokument** an den Code anzupassen, nicht umgekehrt (E-48). Was unten steht, ist damit nicht mehr meine Auslegung, sondern die geltende Fassung.

## E-44 — Das Cockpit zeigt Kacheln, keine Tabelle

A.14 nennt die Abweichung den „eigentlichen Steuerungshebel". Die erste Fassung
zeigte die vierzehn Zeilen als Tabelle mit einer Spalte „Ansehen" — technisch
vollständig und als Steuerungsmittel unbrauchbar: eine Tabelle lädt zum
Überfliegen ein, und beim Überfliegen bleibt eine Zahl hängen, kein Auftrag.

Jede Zeile ist jetzt eine Kachel mit drei Dingen: dem **Zustandszeichen**, der
**Zahl** und dem **Satz**, was zu tun ist. Die ganze Kachel ist der Verweis —
kein „Ansehen"-Link in einer eigenen Spalte, den man erst suchen muss.

Zwei kleinere Dinge fielen dabei auf und sind mit erledigt:

* Die Detailliste zeigte das Zielmodul als **technischen Schlüssel**
  (`datenobjekte`). Jetzt steht dort sein Name. Das ist derselbe Fehler wie bei
  den Gate-Auslösern in AP-5 — der dritte Grundsatz des Design-Systems.
* Die Titel und Beschreibungen der älteren Cockpit-Zeilen waren noch in
  ASCII-Umschrift („Kritikalitaetsketten", „Attestierungen aelter als die
  Frist"). Sie stehen groß auf dem Bildschirm und sind mit diesem Paket
  mitgezogen worden (E-34).

**Das Diagramm.** Die Tier-Verteilung war eine Definitionsliste mit Text wie
„apps-script: Tier 3 × 2". Sie ist jetzt ein Balkendiagramm, und drei Vorgaben
tragen es:

* **Farbrolle:** die Farbe steht für die Einstufung, nicht für die Reihe —
  dieselben Töne wie überall sonst. Eine Legende, die für jedes Diagramm neue
  Farben vergibt, zwingt zum Nachschlagen.
* **Achsen:** die Kategorie steht links am Balken und ist lesbar, ohne den Kopf
  zu drehen; die Menge steht als **Zahl am Segment**. Eine Skala, die man auf
  ein Lineal beziehen muss, beantwortet die Frage „wie viele" nicht.
* **Zugänglichkeit:** Farbe ist nie der einzige Bedeutungsträger. Jedes Segment
  nennt seine Zahl, die Legende ihre Stufe, und dieselben Werte stehen als
  Tabelle für Vorleseprogramme darunter.

Der im Plan genannte `dataviz`-Leitfaden liegt diesem Repository nicht bei;
angewandt sind die drei Punkte, die der Plan aus ihm benennt.

## E-45 — Die Wirkungsvorschau zählt, was hinzukommt

„Diese Zuweisung gibt Zugriff auf N Prozessobjekte" (V-ADM-03) lässt sich auf
zwei Arten rechnen: was der Nutzer **danach insgesamt** sieht, oder was die
Zuweisung **hinzufügt**. Der Satz meint das zweite, und nur das zweite hilft
bei der Entscheidung.

Der Unterschied ist nicht theoretisch. Die Sichtbarkeitsregel aus
Architektur 4.3 zeigt einem Nutzer jedes Prozessobjekt, das er selbst
verantwortet oder vertritt — ohne jede Rolle. Rechnete die Vorschau die
Gesamtsicht, stünde bei einem Prozess-Owner mit zwölf eigenen Objekten „gibt
Zugriff auf 12 Prozessobjekte", auch wenn die Zuweisung auf einen fremden
Fachbereich zeigt und nichts eröffnet.

Gerechnet wird deshalb zweimal auf einem **gedachten** Principal — dem
betroffenen Nutzer mit genau dieser einen Zuweisung, und demselben Nutzer ganz
ohne — und die Differenz gebildet. Beide Seiten laufen über dieselben
Sichtbarkeitsfunktionen, die später auch greifen; eine zweite, näherungsweise
Rechnung wäre eine Vorschau auf etwas anderes als das Ergebnis.

## E-46 — Abgenommen wird über den Vorgang, belegt über den Test

Befund B15 nennt die Wurzel der übrigen Befunde: die Abnahmekriterien sind als
Aussagen über eine Rolle formuliert — „ein Prozess-Owner **kann** ein
Prozessobjekt anlegen" —, wurden aber als Aussagen über die API gelesen und mit
API-Tests belegt. So konnten sieben Phasen als abgeschlossen gelten, während
der Nutzerweg für die zentrale Fähigkeit nie existierte.

Seit AP-10 steht in `docs/phasen.md` je Kriterium eine eigene Spalte
**„Vorgang über die Oberfläche"**. Sie kommt vor dem technischen Nachweis, weil
sie das Kriterium beantwortet; die Tests daneben belegen die Fachlogik
dahinter und bleiben als zweites Netz stehen. Wo keine Rolle handelt — der Bau
der Images —, steht ausdrücklich „kein Nutzerweg", statt die Spalte leer zu
lassen.

**Die Zuordnung prüft sich selbst.** Zwei Läufe in `katalog.vorgang.ts` halten
`phasen.md` gegen den Katalog: jede zitierte Kennung muss existieren **und**
erfüllt sein, und jedes Kriterium braucht eine Vorgangsspalte. Eine Tabelle in
einer Markdown-Datei rottet sonst still vor sich hin — und diese hier ist die
Abnahmegrundlage.

`pruefen.sh` benennt den Durchlauf jetzt so: „Abnahme: die Anwendervorgänge aus
docs/vorgaenge.md". Der Name ist keine Kosmetik. Wer den Namen liest, weiß, was
gilt.

## E-47 — Fachbereich ist das Was, Organisationseinheit das Wo

Beide Begriffe stehen seit Phase 1 im Modell, ihre Aufgabenteilung stand
nirgends — sie lebte in zwei Prüfungen in `services/prozess.py`. Nachgetragen:

Ein **Fachbereich** ist die fachliche Domäne: Finance, HR, Logistik. Er trägt
einen Namen und einen Code, sonst nichts — keine Ebene, kein Land.

Eine **Organisationseinheit** ist eine Ausprägung innerhalb eines Fachbereichs,
gekennzeichnet durch `ebene` (INT oder LAND) und bei LAND durch `land_code`.
Ihr eindeutiger Schlüssel ist `(Fachbereich, Ebene, Land)`; einen eigenen Namen
hat sie bewusst nicht und wird als „Finance · INT" zusammengesetzt. Sie ist
kein eigenständiges Gebilde, sondern eine Facette ihres Fachbereichs.

Die Trennung trägt zwei Dinge, die sonst verloren gingen:

* **Die Ebene trägt das Prozessgeber-Umsetzer-Modell.** Ein Prozessobjekt wird
  immer von einer **INT**-Einheit gegeben und von **LAND**-Einheiten umgesetzt;
  beides weist der Server ab, wenn es anders versucht wird. Ein Prozess wird
  international einmal definiert und in mehreren Ländern umgesetzt — die lokale
  Abweichung hängt an der Umsetzung, nicht am Prozess. Aus der Zahl der
  Umsetzungen folgt außerdem die Reichweite (A.4.4).
* **Der Fachbereich trägt den Geltungsbereich einer Rolle.** Ein Scope auf
  einen Fachbereich löst sich in *alle* seine Einheiten auf, ein Scope auf eine
  Einheit nur in diese. Das ist der Unterschied zwischen „Prozess-Owner für
  Finance" und „Prozess-Owner für Finance Deutschland".

**Die Grenze des Modells:** je Fachbereich und Land ist genau **eine** Einheit
möglich. Hat die Organisation zwei Finance-Einheiten in Deutschland, bildet das
Modell sie nicht ab — dann bräuchte die Organisationseinheit einen eigenen
Namen, und die Eindeutigkeit über `(Fachbereich, Ebene, Land)` müsste fallen.
Das ist kein Versehen, sondern die Annahme, auf der die Ableitung der
Reichweite und die Scope-Auflösung heute stehen.

## E-48 — Das Leitdokument folgt dem Code, nicht umgekehrt

Am 02.09.2026 kam das Leitdokument ins Repository. Der Abgleich mit der
Umsetzung ergab sechs Abweichungen, davon vier im Kern des Modells: die zehn
Anforderungsklassen (A.9.2), die Technologiematrix (C.1), die sechs
Schicht-2-Verbote (A.13.2) und das Migrationsprinzip (A.16). Dazu zwei
Gate-2-Auslöser und eine Tier-Schwelle.

**Die Entscheidung war, das Dokument anzupassen.** Nicht weil der Code
maßgeblich wäre — ein Leitdokument geht der Umsetzung vor —, sondern weil die
gewachsene Fassung die bessere Abbildung ist. Drei Gründe, die jeweils an einer
konkreten Stelle hängen:

**Die Anforderungsklassen sind organisatorisch statt technisch geschnitten.**
Die ursprüngliche Fassung nannte K1 „Identität und Zugriffssteuerung", K4
„Nachvollziehbarkeit der Ausführung", K5 „Trennung Dev/Prod" — Eigenschaften
einer Plattform. Damit beantwortet die Matrix aber eine Frage, die sie nicht
beantworten soll: was eine Technologie kann. Die Klassen sollen sagen, was ein
**Prozess braucht**. In der gewachsenen Fassung heißen sie
„Dokumentationspflicht", „Datenschutz-Folgenabschätzung",
„Mitbestimmungsverfahren einleiten" — Pflichten, die jemand erfüllt, nicht
Merkmale, die etwas hat. Der Unterschied wird an K7 sichtbar: das
Mitbestimmungsverfahren ist eine Klasse, die ausgelöst wird und dann läuft;
„Verfügbarkeit" war ein Zustand, den eine Plattform mitbringt oder nicht.

**Die Technologiematrix wird dadurch ehrlicher.** Sieben der zehn Zeilen stehen
jetzt überall auf ✅, und genau das ist die Aussage: keine Plattform hindert
jemanden daran, den Betriebsrat zu beteiligen. Es unterscheiden sich die drei
technischen Klassen — Rechtekonzept, Aufbewahrung, Wiederanlauf. Die alte
Matrix verteilte Unterschiede über alle zehn Zeilen und suggerierte damit, die
Technologiewahl entscheide über Dinge, über die sie nicht entscheidet.

**Das unternehmerische Risiko kann Tier 3 auslösen.** Die alte Fassung
deckelte es ausdrücklich bei Tier 2 — „reines Betriebsrisiko hebt allein nicht
in Tier 3". Ein Prozess, dessen Ausfall den Geschäftsbetrieb gefährdet, wird
jetzt streng geführt, auch wenn er keine Personendaten berührt. Das ist die
sachlich richtige Konsequenz: die Auflagen ab Tier 3 — benannter Owner,
Wiederanlaufkonzept, Governance-Freigabe — sind genau die, die ein solcher
Prozess braucht.

**Was dabei verloren ging, und bewusst.** Die alte A.16 kannte eine
signaturbasierte Vollinventur und **zwei** Grace Periods. Die Umsetzung hat
eine Frist und erkennt Alt-Anwendungen an ihrer Herkunft aus dem Sync. Das ist
schlanker und deckt den Fall; wer die zweite Frist braucht, hat mit
`altanwendung_meldefrist_tage` die Stellschraube und müsste eine zweite
ergänzen.

**Was offen bleibt: Teil B.** Er belegt an 34 Stellen technische Eigenschaften
mit K-Nummern der alten, technisch geschnittenen Fassung. Die Aussagen bleiben
richtig, ihre Etiketten nicht. Sie sind **nicht** umgeschrieben worden — eine
Zuordnung technischer Fähigkeiten auf organisatorische Klassen wäre eine
inhaltliche Entscheidung, keine Redaktion. Am Kopf von Teil B steht das jetzt
als offener Punkt.

**Was das Dokument weiterhin nicht enthält:** das Architekturdokument. Alle
Verweise der Form „Architektur 4.3", „Architektur 7.3", „Architektur 10.2"
zeigen auf ein zweites Dokument, das nicht beiliegt. Was aus ihm stammt —
Sichtbarkeitsregel, Query-API-Vertrag, Rollenmatrix 5.3 — ist nach wie vor
ungeprüft.

## E-49 — Der Beispielbestand entsteht über die Fachlogik, nicht neben ihr

**Anlass.** Die Anwendung ließ sich mit drei Prozessobjekten bedienen, aber
nicht beurteilen: leere Cockpit-Zeilen, eine Tier-Verteilung aus einem
einzigen Balken, ein Nachweis mit acht Einträgen aus derselben Minute. Für
Abnahme, Schulung und jede Gestaltungsfrage fehlte ein Bestand, der aussieht
wie ein Unternehmen im Betrieb.

**Entscheidung.** `app/bestand` baut einen vollständigen Datenbestand einer
Einzelhandelsgruppe auf — zehn Fachbereiche, einunddreißig
Landesgesellschaften, siebzig Menschen, dreiundneunzig Datenobjekte,
fünfundfünfzig Prozessobjekte, zweiundsiebzig Tool-Objekte samt allen
Vorgängen daran. Drei Regeln tragen ihn:

1. **Kein Schreibpfad an den Diensten vorbei.** Jede Zeile entsteht über
   dieselbe Geschäftslogik wie im Betrieb, unter der Kennung des Menschen, der
   sie täte. Damit läuft der Aufbau durch jede Berechtigungsprüfung, jeden
   Torwächter und jeden Vorschlagsabgleich — und ist selbst der schärfste
   Integrationstest dieser Suite (`tests/test_bestand.py`).
2. **Keine Testsignaturen.** Kein Name, kein Datenobjekt, kein Prozess weist
   sich als erfunden aus. Was auf dem Bildschirm steht, liest sich als
   Handelsgruppe bei der Arbeit.
3. **Eine echte Zeitachse.** Jeder Vorgang trägt sein Datum; der Aufbau
   datiert nach jedem Schritt zurück.

**Drei Stellen, an denen der Aufbau eingreift, und warum.**

*Selbstverpflichtung, Gate 1 und Inbetriebnahme stehen in einem Vorgang.*
A.10.5 macht die vollständige Erklärung und die Gate-1-Freigabe zur Bedingung
der Aktivierung, und `pruefe_aktivierung` prüft das gegen die **laufende** Uhr.
Eine Erklärung, die schon zurückdatiert ist, ist beim Aktivieren abgelaufen.
Die drei Schritte laufen deshalb zusammen und werden gemeinsam datiert. Der
Alternativweg wäre gewesen, den Torwächter zu umgehen — und ein Bestand, der
die eigene Regel umgeht, sagt über sie nichts aus.

*Der Protokoll-Cursor wird am Ende nach der Zeit umnummeriert.* Im Betrieb
steigt er mit der Zeit, weil dort in der Zeit gearbeitet wird. Dieser Aufbau
legt ein zwei Jahre altes Prozessobjekt vor einem halbjahralten an, aber beides
in derselben Minute. Ohne die Umnummerierung stünden die Einträge im Nachweis
in einer Reihenfolge, die keiner Uhr folgt. Geändert wird nur der Cursor,
nichts am Inhalt.

*Datenobjekte werden nicht gepflegt, sondern gerechnet.* Ihr Anlagedatum
ergibt sich aus dem ältesten Verweis auf sie — ein Datenobjekt gibt es, bevor
der erste Prozess es referenziert. Das hält den Bestand stimmig, ohne dass
jemand dreiundneunzig Daten von Hand nachziehen muss.

**Was der Aufbau gefunden hat.** Er ist an vier Stellen laut gescheitert, und
jede war ein echter Befund: eine Bewertungsantwort, die dem Vorschlag aus A.8.4
widersprach, ohne begründet zu sein; eine Aktivierung ohne tragende Erklärung;
eine Compliance-Meldung durch die Plattform-Rolle, die auf Tool-Objekten nicht
schreiben darf; und die Übernahme einer vorgefundenen Anwendung durch einen
technischen Owner, der auf ein Objekt ohne Zuordnung noch gar nicht zugreifen
kann. Alle vier sind im Bestand jetzt so abgebildet, wie die Anwendung sie
erzwingt.

## E-50 — Ein geteilter Link behält sein Ziel über die Anmeldung hinweg

**Befund.** Die Anwendung verspricht teilbare Adressen: der Fachbereichsfilter
des Cockpits steht in der URL, „diese Ansicht lässt sich so weitergeben"
(Architektur 9.3). Wer eine solche Adresse öffnet, ohne angemeldet zu sein,
landete nach der Anmeldung auf der Prozessliste. Das Ziel ging verloren — und
zwar genau in dem Moment, in dem es zählt: beim ersten Öffnen durch den
Empfänger. Aufgefallen ist es an der schlichtesten Stelle: `…/de/cockpit`
aufrufen und danach das Cockpit nicht sehen.

**Entscheidung.** Die Umleitung zur Anmeldemaske nimmt die verlangte Adresse
mit, und die Anmeldemaske kehrt nach dem Anmelden dorthin zurück. Fehlt eine
Angabe, bleibt es bei der Prozessliste.

**Die Ausnahme, und warum sie eine eigene Zustandsvariable braucht.** Eine
**Abmeldung** darf kein Ziel hinterlassen: wer sich danach an diesem Browser
anmeldet, gehört nicht auf die letzte Seite seines Vorgängers — schon gar
nicht, wenn er sie nicht sehen darf. Der erste Versuch, das im Abmeldeknopf zu
lösen (abmelden, dann zur Anmeldemaske navigieren), scheiterte reproduzierbar:
die Umleitung des Layouts gewinnt gegen die Navigation im Klick, weil sie im
selben Rendervorgang entsteht. Deshalb liegt die Unterscheidung jetzt dort, wo
beide Zustände zusammenliegen — in der Sitzung selbst. `abgemeldet` wird im
gleichen Zug mit dem Token gesetzt und ist beim Rendern der Umleitung bereits
gültig.

Der Vorgangskatalog trägt den Fall als **V-ANM-07**; ein Einheitentest hält
zusätzlich fest, dass eine Abmeldung dem Nächsten kein Ziel anhängt.

## E-51 — Umbruchpunkte stehen als `max-width`, nicht als `max-inline-size`

**Befund.** Auf einem schmalen Gerät zeigte die Tier-Verteilung farbige Zahlen
in Spalten statt Balken — aus dem Diagramm war eine Tabelle geworden. Auf einem
breiten Bildschirm war davon nichts zu sehen.

**Ursache.** Zwei Medienabfragen im Stylesheet lauteten
`@media (max-inline-size: 40rem)`. Das logische Pendant zu `width` gibt es nur
in **Container**-Abfragen; in einer Medienabfrage ist `inline-size` kein
gültiges Merkmal, und die gesamte Regel verfällt stillschweigend — ohne Fehler,
ohne Warnung, ohne Spur im Bau. Betroffen waren die Tier-Verteilung und die
Gegenüberstellung „erlaubt / gemessen" im Erlaubnisrahmen; beide sollten auf
schmalen Geräten einspaltig werden und taten es nie.

Bei der Verteilung fiel das besonders auf, weil der Balken neben einer
zwölf Zeichen breiten Beschriftung so wenig Platz behielt, dass alle Segmente
auf ihre Mindestbreite fielen. Damit waren alle Reihen gleich lang — und die
Länge ist bei einem Balkendiagramm die ganze Aussage.

**Entscheidung.** Beide Abfragen stehen jetzt als `max-width`, wie die übrigen
Umbruchpunkte des Stylesheets auch. Bei der Verteilung rückt die Beschriftung
zusätzlich über den Balken, damit er die volle Breite bekommt.

**Warum das eine Prüfung braucht.** Ein Fehler dieser Art ist auf dem
Bildschirm des Entwicklers unsichtbar. `e2e/darstellung.spec.ts` verstellt
deshalb die Fensterbreite und prüft, dass die Balken unterschiedlich lang
bleiben und der längste einen nennenswerten Teil der Breite einnimmt. Ohne die
Korrektur scheitert genau der schmale Fall. Dafür steht das Diagramm jetzt auch
in der Stilprobe: dort hat es festen Bestand, und die Prüfung legt keine Daten
an, die einer Abnahme im Weg stünden.

## E-52 — Der Vortrag steht in der Anwendung und hat genau eine Quelle

**Anlass.** Die Konzeptvorstellung lag als Datei neben der Anwendung. Wer
wissen wollte, *warum* die Anwendung etwas verlangt, musste das Repository
öffnen. Das ist die falsche Reihenfolge: das Vorgehen erklärt sich dort, wo
damit gearbeitet wird.

**Entscheidung.** Der Vortrag bekommt einen eigenen Punkt in der Navigation
(„Konzept") mit zwei Ansichten — **Vortrag** für den Raum, mit Pfeiltasten,
Vollbild und der Foliennummer in der Adresse, und **Dokument** zum Lesen und
Nachschlagen.

**Eine Quelle, nicht zwei.** `docs/praesentation.md` bleibt die einzige
Fassung: lesbar im Repository, projizierbar über Marp, und dieselbe Datei
trägt die Ansicht in der Anwendung. Eine gepflegte Kopie im Frontend wäre
genau die Doppelpflege, die P5 überall sonst verbietet.

**Kein allgemeiner Markdown-Übersetzer.** `nutzen/folien.ts` kennt genau die
Auszeichnungen, die im Dokument vorkommen, und **meldet jede andere als
Fehler**, statt sie stillschweigend als Fließtext auszugeben. Ein Test liest
das vollständige Dokument durch; wer eine neue Auszeichnung benutzt, bekommt
einen roten Test und keine Folie mit Sternchen darauf. Das ist billiger und
ehrlicher als eine Abhängigkeit, die tausend Fälle kann und neunhundert davon
nie sieht.

**Der Preis: der Bau des Frontend-Images läuft jetzt über dem
Wurzelverzeichnis.** Er braucht `docs/praesentation.md` und `docs/bilder/`, und
die lagen außerhalb seines Kontexts. Kopiert wird ausdrücklich nur beides und
nicht das ganze Verzeichnis; ein `.dockerignore` hält den Kontext klein. Die
Alternative — eine Kopie im Frontend — hätte den Bau einfacher gelassen und
die Quelle verdoppelt. Das ist der schlechtere Tausch.

**Zum Ton.** Der Vortrag bittet um keine Erlaubnis. Er erklärt ein Vorgehen und
beschreibt, wie es greift. Frühere Fassungen waren als Entscheidungsvorlage
geschrieben („die Entscheidung, um die wir bitten", „Abbruchkriterium"); das
ist umgestellt. Was offen ist — der Zugang des Betriebsrats — steht weiter
drin, aber als gemeinsam festzulegender Punkt, nicht als Antrag.

Der Vorgangskatalog trägt den Fall als **V-ANM-08**.

## E-53 — Die Rechte stehen am Objekt, nicht im Frontend

**Befund aus dem Betrieb.** Die Rollen wirkten ausschließlich auf der API. Die
Oberfläche zeigte jedem alles, ließ jedes Feld bearbeiten — und lieferte den
Bescheid erst beim Speichern als 403. Wer nicht schreiben durfte, erfuhr das
also erst **nach** getaner Arbeit. Das ist die schlechteste aller Reihenfolgen.

Bemerkenswert daran: der Anspruch stand längst im Code. Über `Sitzung.tsx`
steht seit Phase 1 „Das Frontend blendet nicht erlaubte Aktionen aus, verlässt
sich aber nicht darauf." Ausgeblendet wurde bis hierher nichts außer der
Gate-Entscheidung und zwei Navigationspunkten.

**Die naheliegende Abhilfe wäre falsch gewesen.** Die Regeln im Frontend
nachzubauen hätte eine zweite Fassung derselben Logik ergeben — und zwei
Fassungen laufen auseinander. Die eine, die zählt, wäre immer die andere
gewesen.

**Entscheidung.** Der Server rechnet je Objekt aus, was der Anfragende damit
tun darf, und schreibt es als `rechte` an die Antwort (`services/rechte.py`).
Die Oberfläche liest es und blendet aus, was nicht geht. Sie kennt die Regeln
nicht und soll sie nicht kennen.

Das ist eine **Auskunft, keine Sicherung**: jede schreibende Route prüft
unverändert weiter (Architektur 10.2). Wer die API direkt anspricht, läuft in
dieselbe Prüfung wie zuvor.

**Die Grenze verläuft am Objekt.** Am Objekt hängt, was vom Objekt abhängt: ob
jemand *dieses* Prozessobjekt bearbeiten darf, entscheidet dessen Prozessgeber.
Rein rollengebundene Rechte — Gate entscheiden, Matrix pflegen, Einstellungen
ändern, Rollen vergeben — stehen nicht dort; sie hängen an keinem Objekt, und
die Oberfläche kennt die eigenen Rollen ohnehin aus dem Profil.

**Was ausgeblendet wird und was nicht.** Schaltflächen verschwinden,
Eingabefelder bleiben stehen und werden gesperrt. Ein ausgeblendetes Feld wäre
eine Lücke im Bild, kein Schutz — wer nichts ändern darf, soll den Wert
trotzdem sehen. Dafür haben die Formularbausteine `Auswahl`, `Umschalter` und
`SegmentierteSteuerung` eine Eigenschaft `gesperrt` bekommen.

**Und die Anwendung erklärt sich.** Eine fehlende Schaltfläche erklärt sich
nicht von selbst. Wo nichts geht, steht ein Satz, der sagt warum und wer es
darf — beim Prozess-Umsetzer sogar, welchen einen Weg er hat.

**Zehn Zugänge für die Vorführung.** Der Beispielbestand legt je Rolle einen an,
dazu dieselbe Rolle mit zwei Geltungsbereichen und einen ganz ohne Rolle. Sie
tragen keine erfundenen Personennamen, sondern die Bezeichnung ihrer
Zugangsart; Kennung und Name sind dasselbe eine Wort. Dokumentiert in
`docs/demo-zugaenge.md`, festgehalten als V-ADM-07 und V-ADM-08.

## E-54 — Die Sichtbarkeitsregel gilt auch beim Direktaufruf

*Datum: 2026-09-03 — Status: umgesetzt*

Die Frage war berechtigt: liefert eine Liste weniger, weil das Frontend
weniger zeigt, oder weil weniger da ist? Die Messung über alle zehn
Demo-Zugänge hat beides gefunden.

**Der Regelfall war richtig.** Listen filtern in SQL, nicht in der Antwort:
`ohnerolle` bekommt auf `/prozesse`, `/tools`, `/datenobjekte` und `/lenkung`
ein leeres Feld, `prozessowner` sieht 11 von 56 Prozessobjekten. Der
Direktaufruf eines fremden Prozess- oder Tool-Objekts antwortet mit 403,
ebenso `/nachweis` und `/admin/users` für jede nicht globale Rolle. Die Daten
sind nicht ausgeblendet, sie kommen nicht.

**Zwei Routen waren es nicht.** `GET /datenobjekte/{id}` rief
`hole_datenobjekt` ohne jede Prüfung auf und antwortete jedem Angemeldeten mit
200 — auch `ohnerolle` auf einem Datenobjekt des Fachbereichs Personal.
`/datenobjekte/{id}/wirkung` hatte sogar ein ausdrückliches `del principal`
und gab zusätzlich preis, an wie vielen Prozessen und Tool-Objekten das
Datenobjekt hängt. Wer eine Kennung kannte — aus einer geteilten Adresse, aus
einer Verknüpfung, durch Raten —, las an der Liste vorbei.

**Eine dritte Route war es auch.** `GET /selbstverpflichtungen/ueberfaellig`
lieferte jedem Angemeldeten alle 27 überfälligen Erklärungen des Unternehmens —
also namentlich, wer welche Frist hat verstreichen lassen. Die Route ist der
Vorgriff auf eine Cockpit-Zeile aus Phase 6; das Cockpit filtert längst über
`_sichtbare_prozesse`, der Vorgriff wurde nie nachgezogen. Die Oberfläche ruft
ihn nicht mehr auf, was den Fehler so lange am Leben hielt.

**Die Ursache war die doppelte Regel.** Die Bedingung stand nur als
SQL-Ausdruck für Listen (`datenobjekt_sichtbarkeitsbedingung`); für ein
einzelnes Objekt gab es keine Entsprechung, also stand an der Detailroute
nichts. Prozess- und Tool-Objekte hatten ihre — deshalb waren sie dicht.

Jetzt hat der Dienst `darf_datenobjekt_lesen` und `hole_datenobjekt_sichtbar`
neben der Listenbedingung. Beide Routen gehen darüber. Ein Test hält es fest:
derselbe fremde Zugang bekommt auf Liste, Detail, Wirkung und PATCH die
gleiche Antwort — und ein Datenobjekt-Owner seines Bereichs weiterhin 200.

Bei den Erinnerungen heißt die ungefilterte Fassung jetzt
`ueberfaellige_gesamt` und sagt im Namen, was sie ist: für geplante Läufe und
Prüfungen, nie für eine Antwort. `ueberfaellige` verlangt einen Principal und
schneidet auf die sichtbaren Prozess- und Tool-Objekte zu. Diese Route hat
bewusst **keinen** Eintrag im Vorgangskatalog: eine Frist lässt sich über HTTP
nicht ablaufen lassen, ein Durchlauf könnte die Aussage also nicht belegen.
Sie steht als Backend-Test in `test_gates.py`, wo sich die Uhr stellen lässt.

**Was geprüft und für richtig befunden wurde.** Ungefiltert bleiben
`/anforderungsklassen`, `/technologien`, `/technologiematrix`,
`/selbstverpflichtungen/katalog`, `/gates/ausloeser`, `/konfiguration`,
`/admin/rollen`, `/fachbereiche` und `/organisationseinheiten`. Das ist kein
Versehen: das sind das Regelwerk und die Organisationsstruktur, nicht die
Gegenstände der Governance. Wer bewertet wird, muss den Maßstab lesen dürfen.

**Die Lehre ist die Regel selbst.** Eine Sichtbarkeitsregel, die zweimal
formuliert wird, wird irgendwo nur einmal angewandt. Wo eine Liste gefiltert
wird, gehört die Einzelprüfung in denselben Dienst und in dieselbe Datei —
sonst fällt beim nächsten Endpunkt wieder auf, dass er sie nicht kennt.

## E-55 — Erst der Sollzustand, dann der Code: Rollen, Scopes, Datenobjekte

*Datum: 2026-09-03 — Status: umgesetzt (AP-11)*

Nach E-54 fielen an der laufenden Anwendung mehrere Dinge zugleich auf:
Datenobjekte trugen eine **Person** als Owner — unter einer Hilfe, die von der
„datenhaltenden Stelle" sprach und dann ein Dropdown mit allen Nutzernamen
bot. Fachrollen konnten den Fachbereich eines Datenobjekts frei wechseln, wo
ein Tool-Objekt seinen Bereich nicht verlassen kann. Wer sich selbst als Owner
eintrug, durfte in jedem Fachbereich anlegen. Und die Sicht auf Datenobjekte
war bereichsweit für jede Rolle mit Scope im Fachbereich — auch für den
Prozess-Umsetzer.

**Die Entscheidung war eine über die Reihenfolge.** Jede dieser Stellen ließ
sich für sich plausibel korrigieren, und genau so war es bis dahin gelaufen:
E-54 hatte zwei Routen dicht gemacht, ohne dass irgendwo stand, was die Regel
ist. Einzelkorrekturen an Berechtigungen verschieben Widersprüche, sie lösen
sie nicht — beim nächsten Formular trifft jemand wieder eine eigene Annahme.
Deshalb zuerst `docs/rollen-und-scopes.md`: die drei Bereiche, die acht
Rollen, der Anker je Objekt, die Matrix Rolle × Objekt × Aktion, die
Datenobjekte ausgearbeitet, und die Abweichungen des Codes nummeriert (R-1 bis
R-11), damit Änderungen darauf zeigen können. Erst danach der Code.

**Was am Datenobjekt entschieden ist.** Ein Datenobjekt ist eine Quelle, kein
Werk. Es hat genau einen Anker — den **Fachbereich** als datenhaltende Stelle —
und keine Person: ein Prozess hat einen Eigner, weil jemand bewertet und sich
verpflichtet; ein Tool hat einen Owner, weil jemand attestiert; eine Quelle
verlangt keine persönliche Erklärung. Wer sie klassifiziert, ist der
Datenobjekt-Owner des Fachbereichs — eine Rolle, keine Eigenschaft des Objekts.
Die Spalte `owner_user_id` fällt weg (Migration `d4f7a2c19e60`).

Der Fachbereich wird nicht gewählt, er ergibt sich (P1): aus dem **gebenden
Prozess**, wenn ein Prozess-Owner die Quelle als Output anlegt — der Prozess
erzeugt die Daten, sein Prozessgeber bestimmt die Stelle, und der gebende
Prozess ist kein eigenes Feld, sondern die Output-Kante; oder aus dem Scope
des Datenobjekt-Owners. Ohne Anker gibt es ein Datenobjekt nur vorgefunden und
unbestätigt; bestätigen heißt zuordnen.

Die Rechte trennen sich nach Feld: **Stammdaten** pflegt der Datenobjekt-Owner
oder der Owner des gebenden Prozesses; die **Kategorie** setzt nur der
Datenobjekt-Owner, weil sie in jeden referenzierenden Prozess wirkt; den
**Anker** wechselt nur die Governance, weil mit ihm jede Berechtigung wandert.
Die Antwort trägt deshalb vier Rechte statt eines.

**Sicht über die Referenz, nicht über den Bereich.** Ein Prozess-Owner sieht
die Quellen, die seine Prozesse nutzen, ein Technischer Owner die, auf die
seine Tools zugreifen — vollständig, weil sie die Wirkung einer Kategorie auf
ihr Objekt verstehen müssen. Die übrigen Quellen ihres Fachbereichs sehen sie
nicht; dafür gibt es keinen Grund. Damit bereichsübergreifende
Wiederverwendung — der Sinn von A.7 — trotzdem möglich bleibt, gibt es einen
**Katalog**: Name, Fachbereich, Kategorie, Quellsystem jeder bestätigten
Quelle, als eigener Endpunkt mit eigenem Schema. Das ist die eine, schmale
Ausnahme von „außerhalb des Bereichs kommt nichts", und sie ist als solche
benannt. Ohne Rolle gibt es auch den Katalog nicht.

**Was die Oberfläche daraus macht.** Das Formular bietet genau die Wege an,
die der Angemeldete hat: dem Datenobjekt-Owner seinen Fachbereich (bei genau
einem vorbelegt und gesperrt), dem Prozess-Owner seine Prozesse als gebende,
der Governance beides. Wer keinen Weg hat, sieht kein „Anlegen", sondern einen
Satz, der sagt, was fehlt. Am Detail steht der Fachbereich als Text, der
gebende Prozess als Verweis, und die Kategorie ist gesperrt, wenn das Recht
fehlt — mit dem Satz, wer es hat.

**Was bewusst offen bleibt.** R-7 — Scopes zählen rollenblind, ein
Prozess-Umsetzer in Vertrieb DE hat damit den Bereich für alles, was über
`erlaubte_org_ids` läuft — ist die tiefste Abweichung, weil sie jede Sichtregel
berührt; sie ist im Sollzustand benannt und folgt als eigenes Paket, ebenso
R-9 (Tool-Anker) und die Personen-Dropdowns an Prozess und Tool (R-8, R-10).
Für Datenobjekte ist R-7 bereits umgangen: `datenobjekt_owner_fachbereiche`
zählt nur die Scopes dieser einen Rolle.

