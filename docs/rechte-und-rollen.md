# Rechte bis ins Frontend — Spezifikation

**Gegenstand:** Das Rechtemodell reicht heute bis an die API und endet dort. Diese
Spezifikation beschreibt, wie es bis an die Oberfläche durchgereicht wird, ohne die
Durchsetzung dorthin zu verlagern.

**Vorgesehen in:** AP-11 · **Vorgänge:** V-RCH-01 bis V-RCH-08

---

## 1. Der Leitsatz

> Eine Aktion, die der Server ablehnen würde, wird gar nicht erst als bedienbar
> angeboten. Und eine Sperre, die wirkt, sagt auch, warum sie wirkt.

Das ist kein Sicherheitsziel — die Anwendung ist heute sicher. Es ist ein Ziel der
Bedienbarkeit und der Ehrlichkeit: Wer ein Formular ausfüllt und beim Speichern
erfährt, dass er es nie durfte, hat Arbeit verloren und eine Antwort bekommen, die
ihm niemand vorher gegeben hat.

## 2. Was heute schon steht

Das Rechtemodell selbst ist tragfähig und braucht keine Änderung.

| Ebene | Zustand | Beleg |
|---|---|---|
| Modell | Rolle × Bereich orthogonal, 8 Rollen, 3 Scope-Typen, Zuweisung als Tripel | `core/permissions.py:3-4`, `models/organisation.py:87-99` |
| Bereichsauflösung | Fachbereichs-Zuweisung deckt die darunterliegenden Organisationseinheiten | `core/permissions.py:74-79` |
| Rollenprüfung | rund 41 `verlange(...)`-Aufrufe über 11 Dateien | `services/*.py`, `api/routers/*.py` |
| Objektbezogene Rechte | sechs `darf_*`-Funktionen — nicht „darf Tools bearbeiten", sondern „darf *dieses* Tool bearbeiten" | `services/asset.py:253-316`, `services/prozess.py:114-143` |
| Scope-Filterung im Lesepfad | wer nicht global sieht, bekommt nur seine Bereiche | `services/prozess.py:84-115`, `services/asset.py:236-301` |
| Fehlerabbildung | `Verboten` → HTTP 403, zentral | `main.py:72` |
| Abdeckung | 40 Testfälle zu Verboten/403 in 12 Testdateien | `backend/tests/` |

**Der Server bleibt die einzige Instanz, die entscheidet.** Alles Folgende ist
Auskunft über seine Entscheidung, nie ein Ersatz für sie.

## 3. Wo die Kette bricht

**3.1 — `hatRolle` wirft den Bereich weg.** Das Profil liefert den Scope bereits
vollständig aus: `RollenzuweisungAus` trägt `scope_typ` und `scope_id`
(`schemas/organisation.py:84-92`), und der Frontend-Typ `Rollenzuweisung` hat beide
Felder (`api/typen.ts:21-27`). Nur die Auswertung ignoriert sie:

```ts
// zustand/Sitzung.tsx:97
hatRolle = (rolle) => (profil?.rollen ?? []).some((z) => z.rolle === rolle)
```

Damit lässt sich „ist Prozess-Owner" beantworten, aber nicht „ist Prozess-Owner
*für diesen Bereich*" — die halbe Aussage des Modells geht auf den letzten Metern
verloren. **Die Daten sind da; es fehlt die Frage.**

**3.2 — Die Rolle wird kaum gefragt.** `hatRolle` steht an sechs Stellen, davon
eine fachlich: `Gates.tsx:61` (`darfEntscheiden`). Der Rest ist die Definition
selbst. Dazu filtert `Layout.tsx:102` zwei Navigationspunkte; der Kommentar dort
nennt das zurecht Komfort, nicht Absicherung.

**3.3 — Die Objekte tragen kein Recht.** Kein Aus-Schema hat ein Feld dazu.
`ToolDetail.tsx` rendert die Eingaben unbedingt; ob der Nutzer sie speichern darf,
zeigt sich erst an der Antwort.

**Praktische Folge:** Wo jemand lesen, aber nicht schreiben darf — Auditor
grundsätzlich, oder ein Nutzer mit Leserecht auf ein fremdes Objekt im eigenen
Bereich — zeigt die Oberfläche Eingabefelder und quittiert das Speichern mit einer
generischen Fehlermeldung aus `ApiFehler`.

## 4. Das Muster, an das angedockt wird

Der Mechanismus existiert bereits und ist erprobt: `ToolDetail.tsx:223` und
`DatenobjektDetail.tsx:113` werten ein serverseitiges Feld
**`schreibgeschuetzte_felder`** aus und sperren die betroffenen Eingaben.

Heute trägt es eine andere Bedeutung — „dieses Feld kommt aus dem Import" (A.17:
keine manuelle Pflege dessen, was Telemetrie liefert). Diese Spezifikation erfindet
deshalb nichts Neues, sondern gibt demselben Kanal einen zweiten Absender.

**Die beiden Sperrgründe müssen unterscheidbar bleiben.** „Das pflegt das
Ursprungssystem" und „das darfst du nicht" sind verschiedene Aussagen und führen zu
verschiedenen nächsten Schritten. Eine Oberfläche, die beides gleich aussehen
lässt, schickt Leute an die falsche Stelle.

## 5. Der Entwurf

### 5.1 Ein Recht ist eine Erlaubnis mit einem Satz

Gemeinsames Fragment in `schemas/rechte.py`:

```python
class RechtAus(BaseModel):
    """Ob eine Aktion erlaubt ist — und wenn nicht, warum nicht.

    Der Grund ist kein Beiwerk. Eine Sperre ohne Begruendung ist fuer den
    Betroffenen nicht von einem Fehler zu unterscheiden.
    """

    erlaubt: bool
    #: Leer, solange erlaubt. Sonst der Satz, der am gesperrten Feld steht.
    grund: str = ""
```

Je Objekt ein eigenes, benanntes Rechtebündel — explizit statt generisch, weil die
möglichen Aktionen je Objekt verschieden sind und eine Wörterbuchspalte niemandem
sagt, welche Schlüssel es gibt:

| Objekt | Rechte | Quelle im Backend |
|---|---|---|
| Prozessobjekt | `bearbeiten`, `aktivieren`, `bewerten` | `prozess.darf_schreiben`, `prozess.darf_umsetzung_bearbeiten` |
| Tool-Objekt | `bearbeiten`, `loeschen`, `verknuepfen`, `attestieren` | `asset.darf_tool_schreiben` |
| Datenobjekt | `bearbeiten`, `umklassifizieren` | `asset.darf_datenobjekt_schreiben` |
| Gate-Vorgang | `einreichen`, `entscheiden` | `gate`-Rollenprüfungen |
| Lenkungsvorgang | `aufloesen`, `abbrechen` | `lenkung`-Rollenprüfungen |
| Klassenbefund | `kompensieren` | `klassen.setze_kompensation` |
| Matrixfeld | `bearbeiten` | `klassen.setze_feld` |
| Konfiguration | `bearbeiten` | `integration`-Router |

**Die Rechte werden aus den vorhandenen Funktionen berechnet, nicht neben ihnen.**
Es entsteht keine zweite Wahrheit — `rechte_fuer(...)` ruft genau die Prüfung auf,
die der Schreibpfad auch aufruft. Alles andere würde über kurz oder lang
auseinanderlaufen, und die Anzeige würde etwas versprechen, das die Durchsetzung
nicht hält.

### 5.2 `hatRolle` bekommt den Bereich zurück

```ts
hatRolle(rolle, { organisationseinheitId?, fachbereichId? })
```

Dieselbe Auflösung wie `Principal.hat_rolle` (`core/permissions.py:61-80`): global
zählt immer, Organisationseinheit zählt bei Gleichheit, Fachbereich zählt für die
darunterliegenden Einheiten. Ohne Bereichsangabe bleibt das heutige Verhalten
erhalten, damit die sechs vorhandenen Aufrufstellen unverändert weiterlaufen.

Diese Funktion ist **für Navigation und Grobstruktur** gedacht. Für die Frage, ob
ein einzelnes Objekt bearbeitbar ist, gilt weiterhin: das Objekt fragen, nicht die
Rolle.

### 5.3 Die Oberfläche sperrt, statt zu scheitern

- Der vorhandene `gesperrt`-Pfad bekommt neben der Feldliste einen zweiten Grund
  und den zugehörigen Satz.
- Ein gesperrtes Feld ist sichtbar, aber nicht bedienbar — nicht ausgeblendet.
  Wer nicht sieht, was es gibt, kann nicht danach fragen.
- Aktionsknöpfe (Gate entscheiden, Vorgang auflösen, Kompensation erfassen)
  erscheinen nur, wenn das jeweilige Objektrecht sie trägt.
- Der Sperrgrund steht am Feld, nicht in einem Sammelhinweis am Seitenkopf.

### 5.4 Was ausdrücklich nicht getan wird

- **Keine Durchsetzung im Frontend.** Fällt ein Recht-Feld weg oder ist es falsch,
  hält weiterhin der Server. Die Oberfläche darf großzügiger irren, nie strenger
  wirken als sie darf — deshalb ist der Vorgabewert bei fehlender Angabe
  „bedienbar", nicht „gesperrt".
- **Keine neuen Rollen, keine Änderung an A.15.**
- **Kein Umbau der Scope-Auflösung.** Sie stimmt.
- **Kein Ausblenden von Objekten.** Was der Lesepfad ausliefert, bleibt sichtbar.

## 6. Abzuleitende Prüfungen

### 6.1 Die tragende Prüfung: Anzeige und Durchsetzung dürfen nicht auseinanderlaufen

Dies ist der Kern und folgt einem Muster, das im Repo schon steht: So wie ein Test
die Lesefassung der Auslöserbedingungen gegen `leite_k_klassen_ab` hält
(`services/klassen.py:54-56`), hält dieser Test die ausgelieferte Erlaubnis gegen
die tatsächliche Antwort.

Für jede schreibende Route eine Zeile in einer Zuordnungstabelle
`Route → Objektrecht`, und darüber ein Test, der für **jede Rolle** beides prüft:

- `rechte.X.erlaubt == false` ⟹ die Route antwortet mit **403**
- `rechte.X.erlaubt == true` ⟹ die Route antwortet **nicht** mit 403

Eine Route ohne Eintrag in der Tabelle lässt den Test fehlschlagen. Damit kann eine
neue schreibende Route nicht hinzukommen, ohne dass jemand ihr Recht benennt.

### 6.2 Backend-Einheitentests

| Prüfung | Erwartung |
|---|---|
| `rechte_fuer(...)` ruft dieselbe Funktion wie der Schreibpfad | keine zweite Rechtequelle |
| Auditor auf jedem Objekttyp | jedes schreibende Recht `erlaubt = false`, `grund` gesetzt |
| Prozess-Owner auf eigenem und fremdem Bereich | im eigenen erlaubt, im fremden nicht |
| Fachbereichs-Zuweisung auf Objekt einer darunterliegenden Organisationseinheit | erlaubt |
| Zwei Zuweisungen desselben Nutzers in verschiedenen Bereichen | je Objekt getrennt bewertet |
| Jedes verweigerte Recht | `grund` ist nicht leer |
| Recht entzogen, Objekt erneut geladen | Erlaubnis kippt ohne neue Anmeldung |

### 6.3 Frontend-Tests

| Prüfung | Erwartung |
|---|---|
| Objekt ohne Bearbeitungsrecht | Eingaben sichtbar, aber nicht bedienbar |
| Gesperrtes Feld | der Grund steht am Feld |
| Sperre aus Herkunft vs. Sperre aus Recht | unterscheidbarer Text |
| Objekt mit Bearbeitungsrecht | keine Sperre, keine Hinweiszeile |
| Fehlendes Rechte-Feld in der Antwort | bedienbar (großzügiger Vorgabewert) |
| `hatRolle` mit Bereich | global, Fachbereich und Organisationseinheit lösen wie im Backend auf |

### 6.4 Anwendervorgänge

Acht Vorgänge, spezifiziert in `docs/vorgaenge.md` unter **V-RCH**, hinterlegt und
bis zur Umsetzung übersprungen in `frontend/vorgaenge/rechte.vorgang.ts`.

Der wichtigste ist **V-RCH-07**: zwei Rollen in verschiedenen Bereichen in
derselben Sitzung. Er ist der einzige, der die Orthogonalität von Rolle und Bereich
über die Oberfläche belegt — bis heute ist sie nur im Backend geprüft.

## 7. Vorgeschlagene Entscheidungen

Aufzunehmen in `docs/entscheidungen.md`, sobald AP-11 umgesetzt wird:

- **E-48 — Das Recht steht am Objekt, nicht in der Rolle des Betrachters.**
  Warum `rechte` je ausgeliefertem Objekt und nicht als Rollenliste im Profil: Die
  Rolle allein beantwortet die Frage nicht, weil jedes `darf_*` zusätzlich das
  Objekt kennt.
- **E-49 — Die Anzeige berechnet kein Recht, sie fragt dasselbe wie der
  Schreibpfad.** Keine zweite Rechtequelle; die Prüfung aus 6.1 hält beide
  zusammen.
- **E-50 — Fehlt die Angabe, ist bedienbar der Vorgabewert.** Die Oberfläche darf
  nie strenger wirken als der Server entscheidet; sonst sperrt ein Anzeigefehler
  Leute aus, die berechtigt sind.
- **E-51 — Gesperrt wird sichtbar, nicht unsichtbar.** Ein ausgeblendetes Feld ist
  nicht erklärbar; ein gesperrtes mit Grund ist es.
- **E-52 — Herkunftssperre und Rechtesperre werden getrennt benannt.** Sie führen
  zu verschiedenen nächsten Schritten.

## 8. Zuschnitt

Ein Arbeitspaket, in dieser Reihenfolge:

1. `RechtAus` und die Rechtebündel je Objekt, aus den vorhandenen `darf_*`
   berechnet
2. Die Zuordnungstabelle `Route → Objektrecht` und die Prüfung aus 6.1 —
   **vor** der Oberfläche, damit die Tabelle die Arbeit anleitet statt sie
   nachträglich zu dokumentieren
3. `hatRolle` mit Bereich
4. Der `gesperrt`-Pfad mit zweitem Grund; Aktionsknöpfe an den Objektrechten
5. Die acht Vorgänge scharfschalten

Der Aufwand liegt im zweiten Schritt, nicht im ersten oder vierten: Die
Rechtefunktionen existieren, der Sperrmechanismus existiert. Was fehlt, ist die
vollständige Zuordnung — und die ist genau das, was den Nutzen trägt.
