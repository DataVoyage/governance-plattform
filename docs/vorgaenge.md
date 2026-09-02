# Vorgangskatalog — was ein Anwender in dieser Anwendung tun können muss

Dieses Dokument ist eine **Spezifikation**, keine Testdokumentation. Es listet jeden Vorgang auf,
den ein Mensch später in der Anwendung durchführen wird, und nennt zu jedem das erwartete Ergebnis.

## Wozu, und wozu nicht

Die technischen Tests prüfen, ob der Code tut, was er tut: Einheitentests am Dienst, Vertragstests
an der API, Abnahmetests je Phase. Sie beantworten die Frage **„funktioniert es"**.

Dieser Katalog beantwortet eine andere Frage: **„ist es vollständig"**. Er ist die Liste aller
Handgriffe, die die Anwendung tragen soll — aus der Sicht dessen, der sie bedient, nicht aus der
Sicht des Moduls, das sie bedient. Ein Vorgang, der hier fehlt, ist ein Vorgang, den niemand
spezifiziert hat; ein Vorgang, der hier steht und offen ist, ist eine bekannte Lücke mit Adresse.

Der Katalog ist damit auch die Gegenprobe zum Umsetzungsplan: jedes Arbeitspaket schaltet die ihm
zugeordneten Vorgänge scharf, und erst wenn sie laufen, ist das Paket fertig.

## Aufbau

Jede Zeile ist ein Vorgang mit einer festen Kennung. Die Kennung ändert sich nie — sie ist die
Verbindung zwischen dieser Spezifikation, dem Umsetzungsplan und dem ausführbaren Durchlauf in
`frontend/vorgaenge/`.

| Spalte | Bedeutung |
|---|---|
| **Kennung** | `V-<Bereich>-<Nr>`, unveränderlich |
| **Vorgang** | Was der Anwender tut, in seinen Worten |
| **Rolle** | Wer ihn ausführt (Leitdokument A.15) |
| **Erwartetes Ergebnis** | Woran der Anwender erkennt, dass es geklappt hat — die geprüfte Zusage |
| **AP** | Arbeitspaket aus `umsetzungsplan.md`, das den Vorgang trägt |
| **Stand** | `erfüllt` = läuft im Durchlauf · `offen` = spezifiziert, noch nicht umgesetzt |

## Ausführung

```bash
cd frontend && npm run vorgaenge          # alle erfüllten Vorgänge
npm run vorgaenge -- --grep V-PRO         # ein Bereich
```

Der Durchlauf läuft **ausschließlich über die Oberfläche**. Wo eine Vorbedingung außerhalb der
Rechte des geprüften Anwenders liegt, wird sie über die API hergestellt und im Test begründet.

Offene Vorgänge erscheinen im Bericht als übersprungen, mit ihrem Arbeitspaket als Grund. Sie
verschwinden nicht — die Liste bleibt vollständig, damit sichtbar bleibt, was noch fehlt.

`vorgaenge/katalog.vorgang.ts` hält Katalog und Durchlauf gegeneinander: jede Kennung hier braucht
genau einen Durchlauf, jeder Durchlauf braucht eine Kennung hier. Wer einen Vorgang hinzufügt, ohne
ihn zu hinterlegen, bekommt einen roten Test — und umgekehrt.

---

## V-ANM — Zugang, Sprache, Darstellung

| Kennung | Vorgang | Rolle | Erwartetes Ergebnis | AP | Stand |
|---|---|---|---|---|---|
| V-ANM-01 | Mit der Unternehmensidentität anmelden | alle | Die Prozessliste erscheint, der eigene Name steht in der Seitenleiste | AP-0 | erfüllt |
| V-ANM-02 | Eine Adresse ohne Anmeldung aufrufen | alle | Umleitung zur Anmeldemaske, kein Inhalt sichtbar | AP-0 | erfüllt |
| V-ANM-03 | Abmelden | alle | Zurück zur Anmeldemaske; ein erneuter Aufruf führt nicht zurück in die Anwendung | AP-0 | erfüllt |
| V-ANM-04 | Auf Französisch umschalten | alle | Dieselbe Seite mit übersetzten Beschriftungen, die Adresse trägt `/fr/`, die Daten bleiben unverändert | AP-0 | erfüllt |
| V-ANM-05 | Darstellung auf „Dunkel" stellen | alle | Die Anwendung wird dunkel und bleibt es nach dem Neuladen | AP-0 | erfüllt |
| V-ANM-06 | Auf einem dunkel gestellten Gerät „Hell" wählen | alle | Alle Texte bleiben lesbar — auch die vom Browser gemalten Flächen | AP-0 | erfüllt |

## V-PRO — Prozessobjekt

| Kennung | Vorgang | Rolle | Erwartetes Ergebnis | AP | Stand |
|---|---|---|---|---|---|
| V-PRO-01 | Einen Prozess mit den Pflichtangaben anlegen | Prozess-Owner | Der Prozess erscheint in der Liste im Status „Entwurf" und ist über seine Detailseite erreichbar | AP-1 | erfüllt |
| V-PRO-02 | Ohne Stellvertretung speichern | Prozess-Owner | Das Speichern wird verweigert, der Fokus springt in das fehlende Feld | AP-1 | erfüllt |
| V-PRO-03 | Input-Datenobjekte als Referenz erfassen | Prozess-Owner | Die gewählten Objekte erscheinen als Chips; ihre Kategorie ist am Treffer sichtbar, bevor gewählt wird | AP-1 | erfüllt |
| V-PRO-04 | Output-Datenobjekte als Referenz erfassen | Prozess-Owner | Die Detailseite weist sie getrennt vom Input aus | AP-1 | erfüllt |
| V-PRO-05 | Einen vorgelagerten Prozess referenzieren | Prozess-Owner | Die Kette ist auf beiden Seiten sichtbar, ohne sie zweimal zu erfassen | AP-1 | erfüllt |
| V-PRO-06 | Einen Lieferanten außerhalb des Registers als Freitext erfassen | Prozess-Owner | Der Text bleibt erhalten; das Feld ist ausdrücklich für Zulieferer ohne eigenes Prozessobjekt gedacht | AP-1 | erfüllt |
| V-PRO-07 | Einen nachgelagerten Prozess referenzieren | Prozess-Owner | Die Wirkung „abwärts betroffen" nennt ihn | AP-1 | erfüllt |
| V-PRO-08 | Mehr als sieben Prozessschritte eintragen | Prozess-Owner | Eine Warnung nennt die falsche Flughöhe und empfiehlt einen weiteren Prozess; Speichern bleibt möglich | AP-1 | erfüllt |
| V-PRO-09 | Einen Kreis in der Prozesskette anlegen | Prozess-Owner | Das Speichern wird mit Begründung abgelehnt | AP-1 | erfüllt |
| V-PRO-10 | Den Kundenkreis festlegen | Prozess-Owner | Die Reichweite wird abgeleitet, ist schreibgeschützt und nennt ihre Herkunft | AP-1 | erfüllt |
| V-PRO-11 | Die Ausfallfolge festlegen | Prozess-Owner | Die Kritikalität wird abgeleitet und nennt ihre Herkunft | AP-1 | erfüllt |
| V-PRO-12 | Einen kritischeren Nachfolger verknüpfen | Prozess-Owner | Die eigene Kritikalität steigt auf dessen Wert, die Herkunft wechselt auf „aus der Prozesskette geerbt" | AP-1 | erfüllt |
| V-PRO-13 | Den Prozess in zwei Landesorganisationen umsetzen | Prozess-Owner | Die Reichweite steigt auf „Unternehmen", beide Einheiten sind mit sprechendem Namen sichtbar | AP-1 | erfüllt |
| V-PRO-14 | Eine lokale Abweichung zur Umsetzung erfassen | Prozess-Umsetzer | Die Abweichung steht an der Umsetzung, nicht am Prozess | AP-1 | erfüllt |
| V-PRO-15 | Eine Umsetzung entfernen | Prozess-Owner | Die Reichweite wird neu abgeleitet | AP-1 | erfüllt |
| V-PRO-16 | Einen bestehenden Prozess bearbeiten | Prozess-Owner | Alle Referenzen sind vorbelegt; ungeänderte Angaben bleiben unangetastet | AP-1 | erfüllt |
| V-PRO-17 | Einen Prozess ohne Bewertung aktivieren | Prozess-Owner | Die Aktivierung wird verweigert und nennt den Grund | AP-1 | erfüllt |
| V-PRO-18 | Einen Prozess stilllegen | Prozess-Owner | Der Status wechselt; verknüpfte Tools bleiben erhalten | AP-1 | erfüllt |
| V-PRO-19 | Einen stillgelegten Prozess wieder in Betrieb nehmen | Prozess-Owner | Die gültige Bewertung trägt weiter, der Prozess wird ohne Neubewertung wieder aktiv | AP-1 | erfüllt |
| V-PRO-20 | Die Wirkung eines Prozesses ansehen | Prozess-Owner | Abwärts steht, was stillsteht; aufwärts, wer zuliefert | AP-1 | erfüllt |
| V-PRO-21 | Die Prozessliste durchsuchen | alle | Die Liste zeigt nur die Treffer, mit Tier- und Mitbestimmungsabzeichen | AP-1 | erfüllt |
| V-PRO-22 | Einen Prozess außerhalb des eigenen Bereichs aufrufen | Prozess-Owner | Er ist weder in der Liste noch über seine Adresse erreichbar | AP-1 | erfüllt |
| V-PRO-23 | Erlaubte externe Ziele am Prozess erklären | Prozess-Owner | Die Ziele stehen als Rahmen am Prozess; ein neues Ziel löst Gate 2 aus | AP-6 | erfüllt |

## V-DAT — Datenobjekt

| Kennung | Vorgang | Rolle | Erwartetes Ergebnis | AP | Stand |
|---|---|---|---|---|---|
| V-DAT-01 | Ein Datenobjekt mit Reifegrad 1 anlegen | Datenobjekt-Owner | Name, Kategorie, Owner, Fachbereich und Quellsystem sind in einem Zug erfassbar; das Objekt erscheint in der Liste | AP-2 | erfüllt |
| V-DAT-02 | Ein Datenobjekt ohne Kategorie anlegen | Datenobjekt-Owner | Es trägt sichtbar „Ohne Kategorie" und erscheint im Cockpit-Befund | AP-2 | erfüllt |
| V-DAT-03 | Die Kategorie mit ihrem Ankertext wählen | Datenobjekt-Owner | Jede der fünf Kategorien aus A.7 nennt ihre Beispiele, damit die Wahl ohne Rückfrage gelingt | AP-2 | erfüllt |
| V-DAT-04 | Sehen, welche Prozesse dieses Datenobjekt referenzieren | Datenobjekt-Owner | Die Liste nennt jeden Prozess mit Input- oder Output-Kennzeichnung und seiner Einstufung | AP-2 | erfüllt |
| V-DAT-05 | Sehen, welche Tools darauf zugreifen | Datenobjekt-Owner | Die Liste nennt jedes Tool mit seiner Zugriffsart oder dem Hinweis, dass die Verbindung über den Prozess läuft | AP-2 | erfüllt |
| V-DAT-06 | Vor einer Umklassifizierung die Wirkung ansehen | Datenobjekt-Owner | Betroffene Prozesse, betroffene Tools und die Zahl neu mitbestimmungsrelevanter Prozesse stehen vor der Entscheidung | AP-2 | erfüllt |
| V-DAT-07 | Die Umklassifizierung abbrechen | Datenobjekt-Owner | Nichts wird geschrieben, die Kategorie bleibt unverändert | AP-2 | erfüllt |
| V-DAT-08 | Die Umklassifizierung übernehmen | Datenobjekt-Owner | Die Kategorie wechselt, und die abgeleiteten Flags der referenzierenden Prozesse sind sofort nachgeführt | AP-2 | erfüllt |
| V-DAT-09 | Owner, Fachbereich und Quellsystem ändern | Datenobjekt-Owner | Die Änderung greift sofort und ist im Nachweis protokolliert | AP-2 | erfüllt |
| V-DAT-10 | Ein importiertes Datenobjekt bearbeiten | Datenobjekt-Owner | Stammdatenfelder sind gesperrt mit Verweis auf das Ursprungssystem, die Kategorie bleibt pflegbar | AP-2 | erfüllt |
| V-DAT-11 | Die Datenobjektliste durchsuchen | alle | Name und Quellsystem sind durchsuchbar, die Kategorie ist je Zeile sichtbar | AP-2 | erfüllt |
| V-DAT-12 | Ein Datenobjekt ohne Fachbereich aufrufen | Datenobjekt-Owner | Es ist nur für seinen Owner und global lesende Rollen sichtbar | AP-2 | erfüllt |

## V-TOO — Tool-Objekt

| Kennung | Vorgang | Rolle | Erwartetes Ergebnis | AP | Stand |
|---|---|---|---|---|---|
| V-TOO-01 | Ein Tool mit Owner, Stellvertretung, Technologie, Einheit und Lauftyp anlegen | technischer Owner | Das Tool erscheint in der Liste mit Technologie und Lauftyp in Klartext | AP-3 | erfüllt |
| V-TOO-02 | Die drei Attestierungen aus A.6 abgeben | technischer Owner | Die Erklärung wird mit Name und Datum festgehalten; sie ist als vollständig gekennzeichnet | AP-3 | erfüllt |
| V-TOO-03 | Ohne Attestierung mit einem Prozess verknüpfen | technischer Owner | Die Verknüpfung ist gesperrt, der Grund steht an der Stelle, an der sie erwartet wird | AP-3 | erfüllt |
| V-TOO-04 | Eine abgegebene Attestierung korrigieren | technischer Owner | Die Erklärung wird neu datiert, und abgeleitete Flags der verknüpften Prozesse sind nachgeführt | AP-3 | erfüllt |
| V-TOO-05 | Das Tool mit einem Prozess verknüpfen | technischer Owner | Es erbt dessen Einstufung; die Quelle des Erbes ist benannt | AP-3 | erfüllt |
| V-TOO-06 | Das Tool mit einem zweiten, höher eingestuften Prozess verknüpfen | technischer Owner | Es trägt das Maximum, und die maßgebliche Kante ist als solche gekennzeichnet | AP-3 | erfüllt |
| V-TOO-07 | Eine Prozesskante lösen | technischer Owner | Das Erbe wird neu berechnet | AP-3 | erfüllt |
| V-TOO-08 | Ein Datenobjekt mit Zugriffsart verknüpfen | technischer Owner | Die Kante erscheint mit ihrer Zugriffsart in der Liste der genutzten Datenobjekte | AP-3 | erfüllt |
| V-TOO-09 | Die Zugriffsart einer bestehenden Kante ändern | technischer Owner | Die Wirkungsart des Tools wird neu bestimmt und nennt ihren Grund | AP-3 | erfüllt |
| V-TOO-10 | Ein Datenobjekt außerhalb des Prozessrahmens nutzen | technischer Owner | Die Abweichung ist am Objekt und als Gesamtwarnung sichtbar, ohne dass jemand sie suchen muss | AP-3 | erfüllt |
| V-TOO-11 | Ein nicht deklariertes Objekt gedeckter Kategorie nutzen | technischer Owner | Der mildere Befund „Nicht deklariert" erscheint, unterscheidbar von der echten Abweichung | AP-3 | erfüllt |
| V-TOO-12 | Die Wirkungsart eines unattestierten Tools ansehen | technischer Owner | Sie steht auf „Noch offen" statt auf „gestaltend" | AP-3 | erfüllt |
| V-TOO-13 | Erklären, dass kein Mensch zwischen Output und Wirkung steht | technischer Owner | Das Tool gilt als verändernd, auch wenn es ausschließlich liest | AP-3 | erfüllt |
| V-TOO-14 | Ein importiertes Tool bestätigen | technischer Owner | Erst danach ist es überhaupt verknüpfbar | AP-3 | erfüllt |
| V-TOO-15 | Ein importiertes, unbestätigtes Tool verknüpfen | technischer Owner | Die Verknüpfung ist gesperrt und nennt den Grund | AP-3 | erfüllt |
| V-TOO-16 | Die Tool-Liste durchsuchen und Zustände erkennen | alle | Fehlende Attestierung, Wirkungsart und geerbtes Tier sind je Zeile sichtbar | AP-3 | erfüllt |
| V-TOO-17 | Einen Compliance-Zustand melden | technischer Owner | Der Zustand steht oben in der Zeitreihe; ältere bleiben stehen | AP-3 | erfüllt |
| V-TOO-18 | Den Erlaubnisrahmen des Tools ansehen | technischer Owner | Erlaubt, gemessen und Abweichung stehen nebeneinander | AP-6 | erfüllt |

## V-BEW — Bewertung

| Kennung | Vorgang | Rolle | Erwartetes Ergebnis | AP | Stand |
|---|---|---|---|---|---|
| V-BEW-01 | Eine vollständige Bewertung durchführen | Prozess-Owner | Alle sechs Dimensionen werden gefragt; das Ergebnis nennt Tier, Profil und ausgelöste Klassen | AP-4 | erfüllt |
| V-BEW-02 | Die schnelle Variante wählen | Prozess-Owner | Der Durchlauf endet beim ersten Tier-3-Treffer; das Fehlen der K-Klassen wird erklärt, nicht verschwiegen | AP-4 | erfüllt |
| V-BEW-03 | Den Vorschlag je Dimension ansehen | Prozess-Owner | Jeder Vorschlag nennt seinen Grund im Klartext, mit dem Objekt, aus dem er stammt | AP-4 | erfüllt |
| V-BEW-04 | Vom Vorschlag abweichen | Prozess-Owner | Ein Begründungsfeld öffnet sich; Vorschlag und Antwort werden beide festgehalten | AP-4 | erfüllt |
| V-BEW-05 | Abweichend antworten ohne Begründung | Prozess-Owner | Der Schritt wird nicht angenommen | AP-4 | erfüllt |
| V-BEW-06 | Das Ergebnis lesen | Prozess-Owner | Die ausgelösten Klassen stehen mit Namen und Erklärungssatz da, nicht als Kürzel | AP-4 | erfüllt |
| V-BEW-07 | Die Auflagen des erreichten Tiers ansehen | Prozess-Owner | Die Auflagen aus A.8.6 stehen am Ergebnis | AP-4 | erfüllt |
| V-BEW-08 | Einen Verbotstatbestand angeben | Prozess-Owner | Eigener roter Ausgang, keine gespeicherte Bewertung, sichtbarer Alarm und Verweis auf Governance | AP-4 | erfüllt |
| V-BEW-09 | Die Bewertung abbrechen | Prozess-Owner | Vor dem Verwerfen wird zurückgefragt | AP-4 | erfüllt |
| V-BEW-10 | Im Wizard einen Schritt zurückgehen | Prozess-Owner | Die vorige Antwort steht noch da und lässt sich ändern | AP-4 | erfüllt |
| V-BEW-11 | Neu bewerten | Prozess-Owner | Die alte Bewertung bleibt erhalten, die neue ist maßgeblich | AP-4 | erfüllt |
| V-BEW-12 | Den Bewertungsverlauf ansehen | Prozess-Owner | Jede Version ist mit Datum und Profil nachvollziehbar | AP-4 | erfüllt |

## V-SEL — Selbstverpflichtung

| Kennung | Vorgang | Rolle | Erwartetes Ergebnis | AP | Stand |
|---|---|---|---|---|---|
| V-SEL-01 | Die Erklärung des Prozesseigners abgeben | Prozess-Owner | Die sechs Aussagen aus A.10.2 stehen wortgetreu da und werden einzeln bestätigt | AP-5 | erfüllt |
| V-SEL-02 | Einen Prozess ohne vollständige Erklärung aktivieren | Prozess-Owner | Die Aktivierung wird verweigert und nennt die fehlende Erklärung | AP-5 | erfüllt |
| V-SEL-03 | Die Erklärung des technischen Owners am Tool abgeben | technischer Owner | Die sechs Aussagen aus A.10.3 sind am Tool-Objekt erreichbar | AP-5 | erfüllt |
| V-SEL-04 | Die Kurzform bei Tier 1 nutzen | Prozess-Owner | Nur die Kurzform wird verlangt (A.10.5) | AP-5 | erfüllt |
| V-SEL-05 | Ab Tier 2 die vollständige Form abgeben | Prozess-Owner | Die vollständige Form wird verlangt | AP-5 | erfüllt |
| V-SEL-06 | Nach einer Neubewertung die Erklärung ansehen | Prozess-Owner | Sie gilt als verfallen, weil sie an die Profilversion gebunden war | AP-5 | erfüllt |
| V-SEL-07 | Die Jahresbestätigung ab Tier 3 abgeben | Prozess-Owner | Ein Klick genügt; das Datum wird festgehalten | AP-5 | erfüllt |
| V-SEL-08 | Einen Kommentar zu einer Aussage hinterlegen | Prozess-Owner | Der Kommentar steht an der Aussage, nicht an der Erklärung als Ganzes | AP-5 | erfüllt |

## V-GAT — Gates

| Kennung | Vorgang | Rolle | Erwartetes Ergebnis | AP | Stand |
|---|---|---|---|---|---|
| V-GAT-01 | Gate 1 einreichen | Prozess-Owner | Der Vorgang erscheint als eingereicht | AP-5 | erfüllt |
| V-GAT-02 | Gate 1 freigeben | Governance | Der Prozess ist danach aktivierbar | AP-5 | erfüllt |
| V-GAT-03 | Gate 1 ablehnen | Governance | Die Ablehnung verlangt eine Begründung und blockiert die Aktivierung | AP-5 | erfüllt |
| V-GAT-04 | Gate 2 ohne Auslöser einreichen | Prozess-Owner | Das Einreichen ist nicht möglich | AP-5 | erfüllt |
| V-GAT-05 | Gate 2 mit einem Auslöser aus A.11 einreichen | Prozess-Owner | Nur die fünf benannten Auslöser stehen zur Wahl, kein freier Grund | AP-5 | erfüllt |
| V-GAT-06 | Als Nicht-Governance eine Entscheidung suchen | Prozess-Owner | Es gibt keine Entscheidungsmöglichkeit in der Oberfläche | AP-5 | erfüllt |

## V-RAH — Erlaubnisrahmen und Lenkung

| Kennung | Vorgang | Rolle | Erwartetes Ergebnis | AP | Stand |
|---|---|---|---|---|---|
| V-RAH-01 | Den vollständigen Rahmen nach A.13.2 Schicht 1 ansehen | technischer Owner | Alle Elemente inklusive Obergrenze der Datenkategorie, Zugriffsart, Ausführungsart und Ausführungsidentität | AP-6 | erfüllt |
| V-RAH-02 | Eine Rahmenüberschreitung melden | technischer Owner | Ein Lenkungsvorgang in Stufe 1 mit Frist entsteht | AP-6 | erfüllt |
| V-RAH-03 | Einen Schicht-2-Verstoß melden | technischer Owner | Der Vorgang startet unmittelbar in Stufe 2 | AP-6 | erfüllt |
| V-RAH-04 | Die Frist eines Tier-1-Verstoßes ablesen | technischer Owner | 30 Arbeitstage, Wochenenden übersprungen | AP-6 | erfüllt |
| V-RAH-05 | Eine abgelaufene Frist beobachten | Governance | Der Vorgang eskaliert in die nächste Stufe | AP-6 | erfüllt |
| V-RAH-06 | Den Vorgang durch Anpassen auflösen | technischer Owner | Der Vorgang schließt, der Zustand wird grün | AP-6 | erfüllt |
| V-RAH-07 | Den Vorgang durch Rahmenerweiterung auflösen | Governance | Eine neue Bewertung wird verlangt | AP-6 | erfüllt |
| V-RAH-08 | Den Vorgang durch Stilllegung auflösen | Governance | Das Tool gilt als inaktiv | AP-6 | erfüllt |
| V-RAH-09 | Die Frist im Countdown ablesen | technischer Owner | Die verbleibende Zeit ist ohne Rechnen erkennbar | AP-6 | erfüllt |
| V-RAH-10 | Fristen und Schwellen konfigurieren | Governance | Die Änderung wirkt auf neue Vorgänge, nicht rückwirkend | AP-6 | erfüllt |

## V-KLA — Anforderungsklassen und Technologiematrix

| Kennung | Vorgang | Rolle | Erwartetes Ergebnis | AP | Stand |
|---|---|---|---|---|---|
| V-KLA-01 | Die Klassen K1–K10 nachschlagen | alle | Jede Klasse mit Name, Zweck und Auslöserbedingung aus A.9.2 | AP-7 | erfüllt |
| V-KLA-02 | Die Technologiematrix ansehen | alle | Technologie × Klasse mit erfüllt, kompensierbar oder nicht erfüllbar | AP-7 | erfüllt |
| V-KLA-03 | Die Matrix pflegen | Governance | Änderungen sind sofort in den Befunden wirksam | AP-7 | erfüllt |
| V-KLA-04 | Einen Ausschlussfall erkennen | Prozess-Owner | Die Technologie erfüllt eine ausgelöste Klasse nicht; der Fall erscheint am Prozess, am Tool und im Cockpit | AP-7 | erfüllt |
| V-KLA-05 | Einen kompensierbaren Fall dokumentieren | technischer Owner | Ohne Kompensationsvermerk bleibt der Befund offen | AP-7 | erfüllt |
| V-KLA-06 | Die Befundkarte am Tool lesen | technischer Owner | Sie nennt Klasse, Technologie und den nötigen Schritt | AP-7 | erfüllt |

## V-COC — Cockpit

| Kennung | Vorgang | Rolle | Erwartetes Ergebnis | AP | Stand |
|---|---|---|---|---|---|
| V-COC-01 | Die Übersicht öffnen | Governance | Alle zwölf Zeilen aus A.14 mit Zahl, Farbpunkt und Handlungssatz | AP-8 | erfüllt |
| V-COC-02 | Eine Zeile öffnen | Governance | Die Detailliste nennt jeden Einzelfall mit Hinweis | AP-8 | erfüllt |
| V-COC-03 | Aus einem Befund ins Zielmodul springen | Governance | Das Zielmodul öffnet vorgefiltert auf genau diesen Fall | AP-8 | erfüllt |
| V-COC-04 | Nach Fachbereich filtern | Governance | Der Filter steht in der Adresse und ist teilbar | AP-8 | erfüllt |
| V-COC-05 | Als Nutzer mit LAND-Scope ins Cockpit gehen | Prozess-Owner | Nur der eigene Bereich erscheint | AP-8 | erfüllt |
| V-COC-06 | Ohne Rolle ins Cockpit gehen | alle | Das Cockpit ist leer, nicht fehlerhaft | AP-8 | erfüllt |
| V-COC-07 | Die Tier-Verteilung je Technologie und Zeit lesen | Governance | Ein Diagramm mit lesbaren Achsen; Farbe ist nicht der einzige Bedeutungsträger | AP-8 | erfüllt |
| V-COC-08 | Den Befund „Antwort widerspricht Datenlage" prüfen | Governance | Er nennt Vorschlag, Antwort und die Begründung des Abweichenden | AP-8 | erfüllt |
| V-COC-09 | Den Befund „Technologie erfüllt Klasse nicht" prüfen | Governance | Er nennt Prozess, Tool, Klasse und Technologie | AP-8 | erfüllt |
| V-COC-10 | Den Befund „Alt-Anwendungen im Melde-/Blockierungspfad" prüfen | Governance | Er nennt die betroffenen Anwendungen nach A.16 | AP-8 | erfüllt |

## V-ADM — Administration und Rollen

| Kennung | Vorgang | Rolle | Erwartetes Ergebnis | AP | Stand |
|---|---|---|---|---|---|
| V-ADM-01 | Die Nutzerliste durchsuchen | App-Administrator | Name, Aktivstatus und Führungskraft sind sichtbar und durchsuchbar | AP-9 | erfüllt |
| V-ADM-02 | Eine Rolle mit Scope zuweisen | App-Administrator | Die Zuweisung erscheint am Nutzer; die Rolle ist mit ihrer Erklärung aus A.15 beschrieben | AP-9 | erfüllt |
| V-ADM-03 | Vor der Zuweisung ihre Wirkung sehen | App-Administrator | „Diese Zuweisung gibt Zugriff auf N Prozessobjekte" steht vor der Entscheidung | AP-9 | erfüllt |
| V-ADM-04 | Eine Rolle entziehen | App-Administrator | Der Zugriff endet sofort | AP-9 | erfüllt |
| V-ADM-05 | Als frisch berechtigter Nutzer arbeiten | Prozess-Owner | Genau die Objekte des zugewiesenen Scopes sind sichtbar, keine anderen | AP-9 | erfüllt |
| V-ADM-06 | Ohne Administratorrolle die Verwaltung suchen | alle | Sie ist weder verlinkt noch über ihre Adresse erreichbar | AP-9 | erfüllt |
| V-ADM-07 | Die Konfiguration pflegen | Governance | Fristen, Schwellen und Vorlauf sind ohne Neustart änderbar | AP-6 | erfüllt |

## V-INT — Integration und Nachweis

| Kennung | Vorgang | Rolle | Erwartetes Ergebnis | AP | Stand |
|---|---|---|---|---|---|
| V-INT-01 | Assets aus dem Ursprungssystem importieren | Plattform | Sie erscheinen als „importiert, unbestätigt" und sind noch nicht verknüpfbar | AP-3 | erfüllt |
| V-INT-02 | Denselben Datensatz erneut importieren | Plattform | Stammdaten werden aktualisiert, governance-relevante Felder bleiben unangetastet | AP-3 | erfüllt |
| V-INT-03 | Als andockendes System das Tier abfragen | Plattform | Auskunft nur mit Service-Token; die Antwort nennt Tier und Profil | AP-3 | erfüllt |
| V-INT-04 | Ohne Service-Token abfragen | Plattform | Die Auskunft wird verweigert | AP-3 | erfüllt |
| V-INT-05 | Änderungen über den Cursor abholen | Plattform | Derselbe Cursor liefert keine Dopplungen | AP-3 | erfüllt |
| V-INT-06 | Eine schreibende Aktion im Nachweis wiederfinden | Auditor | Jede Änderung steht mit Zeitpunkt, Person und Vorher/Nachher im Änderungsprotokoll | AP-9 | erfüllt |
