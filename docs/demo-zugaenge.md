# Zugänge für Vorführung und Entwicklung

Der Beispielbestand legt zehn Zugänge an — einen je Rolle, dazu die beiden
Fälle, an denen sich der Unterschied zeigt: **dieselbe Rolle mit zwei
Geltungsbereichen**, und ein Zugang **ganz ohne Rolle**.

Sie tragen keinen erfundenen Personennamen, sondern die Bezeichnung ihrer
Zugangsart. Kennung und Name sind dasselbe eine Wort — vor Publikum soll das in
zwei Sekunden getippt sein.

```bash
docker compose exec backend python -m app.bestand --leeren
```

> **Nur für Entwicklung und Vorführung.** Diese Zugänge funktionieren
> ausschließlich im Entwicklungsmodus (`GP_AUTH_DEV_MODE=true`), in dem das
> Backend lokal ein Token ausstellt. In Produktion ist dieser Modus aus und die
> Route antwortet mit 404; dort meldet man sich über die zentrale
> Unternehmensidentität an. Die Zugänge haben **keine** Sonderrechte — sie
> tragen dieselben Rollen wie alle anderen im Bestand.

## Die zehn Zugänge

In der Anmeldemaske in beide Felder dasselbe Wort eintragen.

| Kennung | Rolle | Geltungsbereich | Wofür sie im Vortrag steht |
|---|---|---|---|
| `governance` | Governance | unternehmensweit | entscheidet Gates, pflegt Matrix und Einstellungen, sieht alles |
| `auditor` | Auditor | unternehmensweit | sieht alles, ändert nichts — die reine Prüfsicht |
| `plattform` | Plattform | unternehmensweit | betreibt die Adapter, bestätigt vorgefundene Assets |
| `administrator` | App-Administrator | unternehmensweit | vergibt Rollen, sonst nichts |
| `prozessowner` | Prozess-Owner | Fachbereich Vertrieb | legt an, bewertet, erklärt, reicht Gates ein |
| `bereichsowner` | Prozess-Owner | nur Einheit Logistik INT | **dieselbe Rolle, engerer Bereich** |
| `prozessumsetzer` | Prozess-Umsetzer | Einheit Vertrieb DE | darf genau eine Sache: die lokale Abweichung |
| `toolowner` | Technischer Owner | Fachbereich Logistik | attestiert, verknüpft, meldet Zustände, kompensiert |
| `datenowner` | Datenobjekt-Owner | Fachbereich Personal | ordnet Datenobjekte ein |
| `ohnerolle` | — | — | angemeldet und trotzdem ohne Zugriff |

## Was sich damit zeigen lässt

**Eine Rolle wirkt nie allein.** `prozessowner` und `bereichsowner` tragen
dieselbe Rolle. Der eine sieht und ändert den ganzen Vertrieb, der andere
ausschließlich die Prozessobjekte der Einheit *Logistik International*. Die
Berechtigung entsteht aus **Rolle × Bereich** (P-App-3) — das ist an keiner
anderen Stelle so schnell zu zeigen.

**Der Umsetzer hat genau einen Schreibweg.** `prozessumsetzer` sieht die
Prozessobjekte seiner Landesorganisation, findet aber keine Schaltfläche zum
Bearbeiten — nur das Feld für die lokale Abweichung. Die Oberfläche schreibt
dazu, warum.

**Der Auditor ist wirklich lesend.** `auditor` sieht jeden Bereich, jedes
Tool-Objekt und den vollständigen Nachweis — und findet in der ganzen Anwendung
keine einzige Schaltfläche, die etwas ändert.

**Ohne Rolle bleibt es leer.** `ohnerolle` kommt bis zur Prozessliste und findet
dort nichts: keine Objekte, kein „Anlegen", ein Satz, der erklärt warum. Das ist
kein Fehler, sondern die Sichtbarkeitsregel aus Architektur 4.3.

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
