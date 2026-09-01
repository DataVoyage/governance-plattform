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

Die Testsuite, die Oberflächentests und die Pipeline laufen gegen dieselbe
PostgreSQL wie Entwicklung und Produktion. Die Verbindung kommt aus
`GP_TEST_DATABASE_URL` beziehungsweise `GP_E2E_DATABASE_URL`; lokal genügt
`docker compose up -d datenbank`, in der Pipeline stellt ein Service-Container
dieselbe Datenbank bereit.

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

Die Kategorien eines Datenobjekts (Leitdokument A.7) sind hier als
`oeffentlich`, `intern`, `vertraulich`, `personenbezogen`, `mitarbeiterbezogen`
und `besondere_kategorie` gesetzt. Sie sind bewusst nullable, damit die
Cockpit-Ansicht „Datenobjekte ohne Kategorie" (Architektur 8.7) überhaupt
etwas zu zeigen hat.

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

## E-17 — Offene Punkte der Architektur

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
