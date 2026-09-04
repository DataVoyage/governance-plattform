"""Der kleine Bestand: jede Funktion genau einmal, und nichts sonst.

`app.bestand` baut ein ganzes Unternehmen — zehn Fachbereiche, siebzig
Menschen, hundert Vorgänge. Das ist richtig, um die Anwendung zu **beurteilen**:
eine Liste mit drei Einträgen und ein Diagramm aus einem Balken sagen nichts
darüber, ob sie trägt.

Zum **Entwickeln und Prüfen** ist er zu voll. Wer sehen will, ob eine Rolle
richtig greift, sucht sich in sechsundfünfzig Prozessobjekten den einen
heraus, an dem es sich zeigt — und übersieht dabei, dass die Zahl daneben
falsch ist.

Deshalb dieser zweite Bestand. Er hat **alles einmal**: jede Rolle, jeden
Geltungsbereich, jeden Status, jede Datenkategorie, jeden Zustand des
Erlaubnisrahmens, jede Gate-Art, eine Prozesskette, eine Mehrfachumsetzung.
Nichts davon zweimal.

**Die Namen sagen, wofür ein Objekt da ist.** „Tier 3 — Freigabe ausstehend"
ist kein Handelsprozess; es ist der Fall, den man sehen will. Das ist die
bewusste Gegenentscheidung zu `app.bestand`, wo jeder Name aus der Fachwelt
kommt und kein Datensatz verrät, dass er erfunden ist. Beide Regeln haben
denselben Grund: ein Bestand soll sagen, wofür er da ist.

Aufruf:

```
python -m app.lehrbestand --leeren
```
"""
