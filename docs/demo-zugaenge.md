# Zugänge für Vorführung und Entwicklung

Beide Bestände legen **dieselben elf Zugänge** an — einen je Rolle, dazu die
drei Fälle, an denen sich der Unterschied zeigt: **dieselbe Rolle mit zwei
Geltungsbereichen**, **dieselbe Rolle in einem fremden Bereich**, und ein
Zugang **ganz ohne Rolle**. Wer den Bestand wechselt, muss sich nicht umgewöhnen.

```bash
docker compose exec backend python -m app.lehrbestand --leeren   # Entwicklung
docker compose exec backend python -m app.bestand --leeren       # Vorführung
```

## Kennung und Name sind dasselbe eine Wort

In der Anmeldemaske genügt die **Kennung**; das Namensfeld darf frei bleiben,
dann gilt die Kennung auch als Name. Ein Wort in einem Feld — vor Publikum soll
das in zwei Sekunden getippt sein.

Dass Kennung und Name übereinstimmen, ist nicht nur bequem, sondern notwendig.
Die Anwendung führt keine eigene Nutzerverwaltung: sie übernimmt den Namen aus
der Identität, mit der man sich anmeldet (Architektur 10.1). Trüge ein Zugang
im Bestand einen beschreibenden Namen wie „Prozess-Owner, ganze Logistik", dann
würde die erste Anmeldung mit `prozessowner` diesen Namen überschreiben — und
derselbe Mensch stünde je nach Ansicht unter zwei Namen: im Protokoll noch als
das eine, in der Objektliste schon als das andere. Was einen Zugang beschreibt,
steht deshalb hier und im Quelltext, nicht im Datensatz.
`test_lehrbestand.py` prüft die Gleichheit, damit sie nicht zurückfällt.

> **Nur für Entwicklung und Vorführung.** Diese Zugänge funktionieren
> ausschließlich im Entwicklungsmodus (`GP_AUTH_DEV_MODE=true`), in dem das
> Backend lokal ein Token ausstellt. In Produktion ist dieser Modus aus und die
> Route antwortet mit 404; dort meldet man sich über die zentrale
> Unternehmensidentität an. Die Zugänge haben **keine** Sonderrechte — sie
> tragen dieselben Rollen wie alle anderen im Bestand.

## Die elf Zugänge

| Kennung | Rolle | Geltungsbereich | Wofür sie im Vortrag steht |
|---|---|---|---|
| `governance` | Governance | unternehmensweit | entscheidet Gates, pflegt Matrix und Einstellungen, sieht alles |
| `auditor` | Auditor | unternehmensweit | sieht alles, ändert nichts — die reine Prüfsicht |
| `plattform` | Plattform | unternehmensweit | betreibt die Adapter, bestätigt vorgefundene Assets |
| `administrator` | App-Administrator | unternehmensweit | vergibt Rollen, sonst nichts |
| `prozessowner` | Prozess-Owner | Fachbereich Logistik | legt an, bewertet, erklärt, reicht Gates ein |
| `bereichsowner` | Prozess-Owner | nur Logistik **DE** | **dieselbe Rolle, engerer Bereich** |
| `prozessumsetzer` | Prozess-Umsetzer | Logistik DE | darf genau eine Sache: die lokale Abweichung |
| `toolowner` | Technischer Owner | Fachbereich Logistik | attestiert, verknüpft, meldet Zustände, kompensiert |
| `datenowner` | Datenobjekt-Owner | Fachbereich Logistik | ordnet Datenobjekte ein |
| `fremdowner` | Prozess-Owner | Fachbereich **Personal** | **dieselbe Rolle, fremder Bereich** |
| `ohnerolle` | — | — | angemeldet und trotzdem ohne Zugriff |

Zwei weitere Nutzer stehen im Bestand, sind aber **keine Zugänge**: der
`erstzugang` trägt App-Administrator und Governance zugleich (an ihm ließe sich
keine der beiden Rollen für sich zeigen), und `ausgeschieden` ist deaktiviert —
an ihm zeigt sich die Cockpit-Zeile „Prozesse ohne tragenden Owner".

## Was sich damit zeigen lässt

Fünf der sechs bereichsgebundenen Zugänge liegen **im selben Fachbereich**, der
Logistik; der sechste, `fremdowner`, sitzt bewusst daneben. Das ist Absicht:
verteilt man sie über verschiedene Bereiche, sieht jeder etwas anderes, und man
kann nicht unterscheiden, ob der Unterschied von der Rolle oder vom Bereich
kommt. Nebeneinander zeigen sie beide Hälften der Regel — gemessen am
Lehrbestand (`app.lehrbestand`), auf dem die Entwicklungsumgebung läuft:

| Zugang | Rolle × Bereich | Prozesse | Werkzeuge | Datenobjekte |
|---|---|---|---|---|
| `governance` · `auditor` · `plattform` | global lesend | 8 | 6 | 8 |
| `administrator` | App-Administrator, global | **0** | **0** | **0** |
| `prozessowner` | Prozess-Owner, ganze Logistik | 7 | 3 | 6 |
| `bereichsowner` | Prozess-Owner, nur DE | 2 | 1 | 4 |
| `prozessumsetzer` | Prozess-Umsetzer, DE | 2 | 1 | 4 |
| `toolowner` | Technischer Owner, ganze Logistik | 3 | 5 | 6 |
| `datenowner` | Datenobjekt-Owner, ganze Logistik | **0** | **0** | 6 |
| `fremdowner` | Prozess-Owner, Fachbereich Personal | 1 | 0 | 1 |
| `ohnerolle` | — | 0 | 0 | 0 |

### Ein Objekt, neun Sichten

Aussagekräftiger als die Listenlängen ist **ein** Objekt, aus jeder Sicht
aufgerufen. Gemessen am Prozessobjekt „Tier 2 — läuft ohne Gate, umgesetzt in
DE" (`GET /prozesse/{id}`):

| Zugang | Antwort | Rechte, die auf `true` stehen |
|---|---|---|
| `governance` | 200 | bearbeiten, bewerten, selbstverpflichten, gate_einreichen, umsetzung_pflegen |
| `prozessowner` | 200 | bearbeiten, bewerten, selbstverpflichten, gate_einreichen, umsetzung_pflegen |
| `bereichsowner` | 200 | umsetzung_pflegen |
| `prozessumsetzer` | 200 | umsetzung_pflegen |
| `auditor` | 200 | — keines |
| `toolowner` | **403** | — |
| `datenowner` | **403** | — |
| `fremdowner` | **403** | — |
| `ohnerolle` | **403** | — |

Zwei Dinge sind daran zu sehen. Erstens: wer nichts darf, bekommt **keine
Daten**, nicht bloß keine Schaltfläche — die vier Zeilen mit 403 kennen nicht
einmal den Namen des Objekts. Zweitens: wer lesen darf, sieht dasselbe Objekt,
aber eine andere Liste von Rechten. Das ist der Unterschied zwischen Sehen und
Dürfen, an einem einzigen Datensatz.

**Dieselbe Rolle, engerer Bereich.** `prozessowner` und `bereichsowner` tragen
dieselbe Rolle; sieben gegen zwei Prozessobjekte. Der Unterschied ist allein
der Bereich (P-App-3).

**Dieselbe Rolle, fremder Bereich.** `fremdowner` ist ebenfalls Prozess-Owner
und sieht von den acht Prozessobjekten genau eines — sein eigenes. Eine Rolle
allein trägt nichts.

**Derselbe Bereich, andere Rolle.** `datenowner` sitzt in derselben Logistik
wie `prozessowner` — und sieht null Prozessobjekte und null Werkzeuge. Ein
Bereich gehört einer Rolle, nicht einer Person. Bis E-57 war genau das falsch
umgesetzt (R-7): er hätte alles gesehen.

**Rolle ohne Fachsicht.** `administrator` vergibt Rollen und sieht sonst
nichts: drei Nullen. Wer Rechte verteilt, muss die Inhalte nicht kennen.

**Sehen ist nicht dürfen.** `prozessowner` und `toolowner` sehen dieselben
sechs Datenobjekte, dürfen daran aber Verschiedenes — und keiner von beiden
darf ihre Kategorie setzen; das kann nur `datenowner`. Die Schaltflächen
unterscheiden sich, die Listen nicht.

**Der Umsetzer hat genau einen Schreibweg.** `prozessumsetzer` sieht dieselben
zwei Prozessobjekte wie `bereichsowner`, findet aber keine Schaltfläche zum
Bearbeiten — nur das Feld für die lokale Abweichung. Die Oberfläche schreibt
dazu, warum.

**Der Auditor ist wirklich lesend.** `auditor` sieht jeden Bereich, jedes
Tool-Objekt und den vollständigen Nachweis — und findet in der ganzen Anwendung
keine einzige Schaltfläche, die etwas ändert. Der Server weist jede schreibende
Anfrage dieser Rolle zurück, unabhängig vom Objekt.

**Ohne Rolle bleibt es leer.** `ohnerolle` kommt bis zur Prozessliste und findet
dort nichts: keine Objekte, kein „Anlegen", ein Satz, der erklärt warum. Das ist
kein Fehler, sondern die Sichtbarkeitsregel aus Architektur 4.3.

**Eine Quelle gehört einer Stelle, keiner Person.** `datenowner` sieht die
sechs Datenobjekte der Logistik vollständig und klassifiziert sie;
`prozessowner` sieht dieselben sechs, aber nur, weil seine Prozesse und
Werkzeuge sie berühren. Im **Katalog** finden beide alle sieben Quellen des
Unternehmens, um sie als Input zu benennen — dort steht nur Name, Bereich,
Kategorie und Quellsystem. Das Detail einer fremden Quelle bleibt zu: wer sie
direkt aufruft, bekommt keine ausgegraute Anzeige, sondern gar keine Daten
(`docs/rollen-und-scopes.md`, Abschnitt 7).

Im großen Vorführbestand (`app.bestand`) gilt dasselbe Muster mit mehr
Objekten: `prozessowner` sieht dort 6 Prozessobjekte, 9 Werkzeuge und 11
Datenobjekte, `bereichsowner` 4 · 7 · 8, und der Katalog führt 87 Quellen.

## Wie die Oberfläche zu ihrem Wissen kommt

Die Regeln stehen ausschließlich auf dem Server. Er rechnet je Objekt aus, was
der Anfragende damit tun darf, und schreibt es als `rechte` an die Antwort:

```json
{ "id": "…", "name": "Bestellvorschlag Filiale",
  "rechte": { "bearbeiten": false, "bewerten": false,
              "selbstverpflichten": false, "gate_einreichen": false,
              "umsetzung_pflegen": true } }
```

Die Oberfläche baut die Regeln **nicht nach** — sie liest sie und blendet aus,
was nicht geht. Eine zweite Fassung derselben Logik im Frontend würde
auseinanderlaufen, und die eine, die zählt, wäre immer die andere.

Das ist eine **Auskunft, keine Sicherung**: jede schreibende Route prüft
unabhängig weiter (Architektur 10.2). Wer die API direkt anspricht, läuft in
dieselbe Prüfung wie zuvor.

Rein rollengebundene Rechte — Gate entscheiden, Technologiematrix pflegen,
Einstellungen ändern, Rollen vergeben — stehen nicht an den Objekten: sie
hängen an keinem. Die Oberfläche kennt die eigenen Rollen aus dem Profil.

Siehe `backend/app/services/rechte.py` und `docs/entscheidungen.md`, E-53.
