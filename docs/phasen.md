# Phasenstand

Sieben Phasen, jede einzeln abnehmbar (Architektur 11). Eine Phase gilt erst als
abgeschlossen, wenn alle ihre Abnahmekriterien durch einen Test belegt sind.

Die Abnahmekriterien stammen aus dem internen Architekturdokument, das nicht in
diesem Repository liegt; sie sind unten je Phase im Wortlaut wiedergegeben.

## Woran eine Phase abgenommen wird

Die meisten Kriterien beginnen mit „ein *Rolle* kann". Das sind Aussagen über
einen **Menschen an einem Bildschirm**, nicht über eine Schnittstelle. Sie
wurden zunächst durch API-Tests belegt — und genau daran lag es, dass sieben
Phasen als abgeschlossen galten, während der Nutzerweg für die zentrale
Fähigkeit nie existierte (Befund B15).

Seit AP-10 gilt deshalb: **maßgeblich ist der Anwendervorgang.** Jedes
rollenbezogene Kriterium nennt unten die Vorgänge aus `docs/vorgaenge.md`, die
es über die Oberfläche zeigen; die technischen Tests stehen daneben und
belegen die Fachlogik dahinter. Wo kein Vorgang steht, ist das Kriterium
keine Aussage über eine Rolle — etwa der Bau der Images.

Die Zuordnung prüft sich selbst: `vorgaenge/katalog.vorgang.ts` hält jede hier
genannte Kennung gegen den Katalog. Ein Vorgang, der hier zitiert wird und dort
fehlt oder offen ist, bricht den Durchlauf; ein Kriterium ohne Vorgangsspalte
ebenfalls.

**Der Katalog ist größer als die sieben Phasen.** Die Bereiche V-KLA
(Anforderungsklassen) und V-ADM (Verwaltung) gehören zu keiner der
ursprünglichen Phasen — sie kamen mit den Arbeitspaketen AP-7 und AP-9, die
Lücken schließen, die der Phasenplan nicht kannte. Ihre Abnahme steht im
Umsetzungsplan, nicht hier.

Alle Tests — Backend und Oberfläche — laufen gegen dieselbe PostgreSQL wie
Entwicklung und Produktion. Geprüft wird lokal mit `./pruefen.sh`; eine
Pipeline gibt es bewusst nicht. Die Angaben zur Abdeckung je Phase beziehen
sich auf diesen Stand.

| Phase | Inhalt | Stand |
|---|---|---|
| 1 | Fundament | ✅ abgeschlossen |
| 2 | Bewertung | ✅ abgeschlossen |
| 3 | Asset-Management | ✅ abgeschlossen |
| 4 | Selbstverpflichtung und Gates | ✅ abgeschlossen |
| 5 | Compliance und Lenkung | ✅ abgeschlossen |
| 6 | Cockpit | ✅ abgeschlossen |
| 7 | Governance-Query-API | ✅ abgeschlossen |

---

## Phase 1 — Fundament

**Enthalten:** containerisierte Entwicklungsumgebung und reproduzierbarer
Build,
Datenmodell als Alembic-Migration einschließlich `change_log` und
`konfiguration`, Authentifizierung über die zentrale Unternehmensidentität,
Rollen- und Rechte-Grundgerüst, erster Import-Adapter (Fachbereiche,
Organisationseinheiten, Teams), Prozess-Modul ohne Bewertung,
Frontend-Grundgerüst mit Sprachpfad-Routing für Deutsch und Französisch.

**Nicht enthalten, wie vorgegeben:** Bewertung, Asset-Verknüpfung, Gates, Cockpit.

### Abnahmekriterien und Nachweis

| # | Kriterium | Vorgang über die Oberfläche | Technischer Nachweis |
|---|---|---|---|
| 1 | Anmeldung ausschließlich über die zentrale Identität; jede Route ohne Session liefert 401 | V-ANM-01, V-ANM-02, V-ANM-03 | `backend/tests/test_auth.py::test_ohne_session_liefert_jede_route_401` (über alle Routen parametrisiert), `test_dev_token_route_fehlt_ohne_entwicklungsmodus` |
| 2 | Import legt Fachbereiche, INT- und mindestens zwei LAND-Einheiten sowie Teams an; zweiter Lauf erzeugt keine Duplikate | V-INT-01, V-INT-02 | `backend/tests/test_import.py::test_import_legt_stammdaten_an`, `::test_zweiter_lauf_erzeugt_keine_duplikate` |
| 3 | Prozess-Owner legt ein Prozessobjekt mit allen zehn Feldern an; Speichern ohne Stellvertretung wird abgelehnt | V-PRO-01 bis V-PRO-11 | `backend/tests/test_prozess.py::test_owner_legt_prozess_mit_allen_zehn_feldern_an`, `::test_speichern_ohne_stellvertretung_wird_abgelehnt`, `frontend/e2e/phase1.spec.ts` |
| 4 | Ohne Rollenzuweisung im betroffenen Scope weder Ändern noch Löschen (Test je Rolle) | V-PRO-22, V-ADM-04, V-ADM-05, V-ADM-06 | `backend/tests/test_prozess.py::test_ohne_rolle_kein_anlegen_und_kein_aendern`, `::test_owner_eines_anderen_fachbereichs_darf_nicht_schreiben`, `::test_umsetzer_pflegt_nur_die_lokale_abweichung`, `::test_auditor_sieht_global_und_darf_nicht_schreiben` |
| 5 | Ein Prozessobjekt ist mit zwei LAND-Organisationseinheiten verknüpfbar | V-PRO-13, V-PRO-14, V-PRO-15 | `backend/tests/test_prozess.py::test_prozess_in_zwei_laendern_umsetzen`, `frontend/e2e/phase1.spec.ts` |
| 6 | Alle drei Images bauen gegen ein umkonfiguriertes Registry-Ziel, ohne Codeänderung | — kein Nutzerweg | `./pruefen.sh --images` baut Backend, Frontend und Sync-Worker gegen zwei verschiedene Registry-Ziele; der Unterschied liegt allein im Zielnamen |
| 7 | Sprachwechsel ändert die Anzeigesprache, nicht die sichtbaren Datensätze | V-ANM-04, V-ANM-05, V-ANM-06 | `frontend/tests/sprache.test.tsx::aendert beim Sprachwechsel die Anzeige, aber nicht die Datensaetze`, `frontend/e2e/phase1.spec.ts` |

### Abdeckung

- Backend: 99 % (Schwelle 90 %, erzwungen über `fail_under` in `pyproject.toml`)
- Frontend: 98 % Anweisungen (Schwelle 90 %, erzwungen über `vite.config.ts`)
- Abnahme: 31 Anwendervorgänge (V-ANM, V-PRO, V-INT-01/02), ausschließlich headless

---

## Phase 2 — Bewertung

**Enthalten:** der sechsstufige Entscheidungsbaum als geführter Wizard (ein
Schritt pro Bildschirm, zwei Antwortknöpfe), serverseitige Tier- und
K-Klassen-Ableitung, Versionierung der Bewertungen mit Historie am
Prozessobjekt.

**Nicht enthalten, wie vorgegeben:** Asset-Verknüpfung. Die K-Klassen-Anzeige
sagt, welche Klassen ausgelöst sind — nicht, ob ein konkretes Tool sie erfüllt.

### Abnahmekriterien und Nachweis

| # | Kriterium | Vorgang über die Oberfläche | Technischer Nachweis |
|---|---|---|---|
| 1 | Sechs Themenblöcke in der festgelegten Reihenfolge; Verifikation über alle Antwortkombinationen ergibt das tabellierte Tier | V-BEW-01, V-BEW-10 | `backend/tests/test_bewertung.py::test_bloecke_stehen_in_der_festgelegten_reihenfolge`, `::test_jede_antwortkombination_ergibt_das_tabellierte_tier` (4096 Kombinationen), `frontend/e2e/phase2.spec.ts` |
| 2 | Treffer auf „verbotene KI-Praxis" speichert keine Bewertung, sondern erzeugt einen Alarm | V-BEW-08 | `backend/tests/test_bewertung.py::test_verbotstatbestand_speichert_keine_bewertung`, `frontend/e2e/phase2.spec.ts` |
| 3 | Ein Durchlauf, und der ist vollständig: alle sechs Dimensionen und die ausgelösten K-Klassen, auch bei einem Tier-3-Treffer (E-64) | V-BEW-02, V-BEW-01 | `backend/tests/test_bewertung.py::test_ein_tier_3_treffer_beendet_den_durchlauf_nicht`, `::test_jede_gespeicherte_bewertung_traegt_ihre_k_klassen`, `frontend/e2e/phase2.spec.ts` |
| 4 | Neubewertung erzeugt einen neuen Datensatz; die vorherige bleibt einsehbar | V-BEW-11, V-BEW-12 | `backend/tests/test_bewertung.py::test_neubewertung_erzeugt_neuen_datensatz`, `frontend/tests/bewertung.test.tsx` |
| 5 | Profil `KI0-DS3-MB1-IT1-RG2-UR2` löst K1–K5, K7, K8, K9 aus — nicht K6, nicht K10 | V-BEW-06, V-BEW-07, V-KLA-01 | `backend/tests/test_bewertung.py::test_beispiel_aus_dem_leitdokument`, `frontend/e2e/phase2.spec.ts` |

### Hinweis zur Ableitung

Die konkreten Fragen des Baums und die Bedingungen der zehn Maßnahmenklassen
sind in `docs/entscheidungen.md` (E-7) festgehalten, weil das Leitdokument
diesem Repository nicht beiliegt. Es gibt genau **eine** Implementierung: der
Wizard, die Historie und später die Governance-Query-API rufen dieselben
Funktionen in `app/services/bewertung.py`.

### Abdeckung

- Backend: 99 % · Frontend: 98 % Anweisungen · Abnahme: 12 Anwendervorgänge (V-BEW)

---

## Phase 3 — Asset-Management

**Enthalten:** Verwaltung von Tool-Objekten und Datenobjekten, n:m-Verknüpfung
zu Prozessobjekten mit Anzeige der maximum-vererbten Klassifikation, Erweiterung
des Import-Adapters um die Typen `tool` und `datenobjekt`.

### Abnahmekriterien und Nachweis

| # | Kriterium | Vorgang über die Oberfläche | Technischer Nachweis |
|---|---|---|---|
| 1 | Importiertes Tool mit unbekannter `externe_id` erscheint als „importiert, unbestätigt" und ist erst nach manueller Bestätigung verknüpfbar | V-TOO-14, V-TOO-15 | `backend/tests/test_asset.py::test_importiertes_tool_ist_unbestaetigt_und_nicht_verknuepfbar`, `frontend/e2e/phase3.spec.ts` |
| 2 | Zweiter Import überschreibt die governance-seitig gesetzte Kategorie **nicht**, aktualisiert aber Name und technische Metadaten | V-INT-02, V-DAT-10 | `backend/tests/test_asset.py::test_zweiter_import_laesst_die_kategorie_unberuehrt`, `::test_importiertes_datenobjekt_behaelt_seine_kategorie` |
| 3 | Ein Tool an zwei Prozessen unterschiedlicher Kritikalität zeigt die höhere geerbte Einstufung | V-TOO-05, V-TOO-06, V-TOO-07 | `backend/tests/test_asset.py::test_tool_zeigt_die_hoechste_geerbte_einstufung`, `::test_tool_erbt_tier_und_k_klassen_der_bewertungen`, `frontend/e2e/phase3.spec.ts` |
| 4 | Eine Datenobjekt-Kategorisierung ist im verknüpften Prozessobjekt sichtbar, ohne dort erneut gepflegt zu werden | V-DAT-06, V-DAT-08, V-TOO-10 | `backend/tests/test_asset.py::test_kategorie_des_datenobjekts_wirkt_im_prozess`, `frontend/e2e/phase3.spec.ts` |

### Abdeckung

- Backend: 99 % · Frontend: 98 % Anweisungen · Abnahme: 30 Anwendervorgänge (V-TOO, V-DAT)

---

## Phase 4 — Selbstverpflichtung und Gates

**Enthalten:** Selbstverpflichtungs-Modul mit den strukturierten Checklisten aus
A.10.2 und A.10.3, Gate-Modul mit Einreichung, Governance-Entscheidung und
Historie, Erinnerungslogik für die jährliche Erneuerung ab Tier 3.

### Abnahmekriterien und Nachweis

| # | Kriterium | Vorgang über die Oberfläche | Technischer Nachweis |
|---|---|---|---|
| 1 | Ein Tier-3-Prozessobjekt wechselt ohne vollständig abgegebene Selbstverpflichtung nicht in den Status „aktiv" | V-SEL-01, V-SEL-02, V-SEL-05 | `backend/tests/test_gates.py::test_tier_3_wird_ohne_selbstverpflichtung_nicht_aktiv`, `::test_unvollstaendige_selbstverpflichtung_reicht_nicht`, `frontend/e2e/phase4.spec.ts` |
| 2 | Eine Gate-2-Einreichung ohne einen der fünf zulässigen Auslöser wird abgelehnt, bevor sie eingereicht werden kann | V-GAT-04, V-GAT-05 | `backend/tests/test_gates.py::test_gate_2_ohne_ausloeser_wird_abgelehnt`, `::test_gate_2_kennt_nur_die_fuenf_ausloeser`, `frontend/e2e/phase4.spec.ts` (Pflichtauswahl im Formular) |
| 3 | Nur die Governance-Rolle entscheidet; Prozess-Owner und Auditor erhalten 403 | V-GAT-02, V-GAT-03, V-GAT-06 | `backend/tests/test_gates.py::test_nur_governance_entscheidet`, `frontend/e2e/phase4.spec.ts` |
| 4 | 60 Tage vor Ablauf wird erinnert; nach Fristablauf erscheint der Datensatz im Cockpit-Filter | V-SEL-07, V-COC-01 | `backend/tests/test_gates.py::test_erinnerung_60_tage_vor_ablauf_und_ueberfaelligkeit`, `::test_erinnerung_geht_an_den_technischen_owner` |

### Hinweise

Der Vorlauf von 60 Tagen und die Gültigkeitsdauer stehen in der
`konfiguration`-Tabelle und sind von der Governance-Rolle im laufenden Betrieb
änderbar. Der Lauf ist idempotent und läuft als Kubernetes-`CronJob`
(`python -m app.jobs erinnerungen`); ein doppelt gestarteter Job mahnt nicht
doppelt.

Die Aktivierung eines Tier-3-Prozessobjekts verlangt zusätzlich die Erstfreigabe
durch Gate 1 — begründet in `docs/entscheidungen.md` (E-9).

### Abdeckung

- Backend: 99 % · Frontend: 98 % Anweisungen · Abnahme: 14 Anwendervorgänge (V-SEL, V-GAT)

---

## Phase 5 — Compliance und Lenkung

**Enthalten:** Compliance-Zustand als Zeitreihe je Tool-Objekt, gespeist aus
manuellen Meldungen; Lenkungs-Modul mit den drei Eskalationsstufen und den drei
Auflösungswegen aus A.13.5/A.13.6.

Automatisierte Telemetrie kommt erst mit künftigen Adaptern hinzu
(Architektur 7.4) — die Meldewege sind so gebaut, dass ein solcher Adapter
denselben Eintrag erzeugt wie eine Person.

### Abnahmekriterien und Nachweis

| # | Kriterium | Vorgang über die Oberfläche | Technischer Nachweis |
|---|---|---|---|
| 1 | Eine manuell erfasste Rahmenüberschreitung erzeugt automatisch einen Lenkungsvorgang in Stufe 1 mit der tier-abhängigen Frist | V-RAH-02, V-RAH-04, V-RAH-09 | `backend/tests/test_lenkung.py::test_rahmenueberschreitung_erzeugt_stufe_1_mit_tier_frist`, `::test_frist_haengt_am_tier`, `frontend/e2e/phase5.spec.ts` |
| 2 | Ein Vorgang ohne Auflösung wechselt nach Fristablauf automatisch in Stufe 2; die Führungskraft des betroffenen Owners wird benachrichtigt | V-RAH-05, V-ADM-01 | `backend/tests/test_lenkung.py::test_fristablauf_rueckt_in_stufe_2_und_informiert_die_fuehrungskraft`, `::test_eskalation_endet_bei_stufe_3` |
| 3 | Jede der drei Auflösungsarten ist eine eigene Aktion; „Rahmen erweitern" verlangt eine neue Bewertung und schließt erst nach deren Abschluss | V-RAH-06, V-RAH-07, V-RAH-08 | `backend/tests/test_lenkung.py::test_rahmen_erweitern_verlangt_eine_neue_bewertung`, `::test_anpassen_schliesst_und_setzt_gruen`, `::test_stilllegen_setzt_das_tool_inaktiv`, `frontend/e2e/phase5.spec.ts` |

### Hinweise

Die Eskalation läuft als Kubernetes-`CronJob` (`python -m app.jobs
eskalationen`) und ist idempotent. Stufe 3 kennzeichnet den Vorgang für eine
technische Maßnahme; der eigentliche Zugriffsentzug erfolgt außerhalb dieser
Anwendung, in der jeweiligen technischen Plattform.

„Anpassen" und „Rahmen erweitern" führen das Tool auf grün zurück,
„Stilllegen" nicht — ein stillgelegtes Tool ist nicht wieder konform, es ist
außer Betrieb.

### Abdeckung

- Backend: 99 % · Frontend: 98 % Anweisungen · Abnahme: 10 Anwendervorgänge (V-RAH)

---

## Phase 6 — Cockpit

**Enthalten:** die Zeilen aus Leitdokument A.14 als je eigene, aufrufbare
Ansicht, mit Filterung nach Fachbereich und unter Beachtung der
Sichtbarkeitsregel aus Architektur 4.3. Zehn waren es zunächst; die beiden
fehlenden — „Technologie erfüllt ausgelöste Anforderungsklasse nicht" und
„Alt-Anwendungen im Melde-/Blockierungspfad" (A.16) — sind mit AP-7 und AP-8
dazugekommen, dazu die zwei aus AP-4 und AP-5.

Jeder Eintrag trägt sein Zielmodul samt Filter mit sich — ein Klick landet
direkt dort, wo die Sache abgearbeitet wird, statt in einer allgemeinen Liste.

### Abnahmekriterien und Nachweis

| # | Kriterium | Vorgang über die Oberfläche | Technischer Nachweis |
|---|---|---|---|
| 1 | Jede in A.14 genannte Zeile ist als eigene, aufrufbare Ansicht vorhanden | V-COC-01, V-COC-02, V-COC-07 | `backend/tests/test_cockpit.py::test_jede_zeile_aus_a14_ist_aufrufbar`, `frontend/e2e/phase6.spec.ts` |
| 2 | Ein Klick auf einen Cockpit-Eintrag führt zum korrekt vorgefilterten Zielmodul | V-COC-03, V-COC-04 | `backend/tests/test_cockpit.py::test_eintraege_verweisen_auf_das_vorgefilterte_zielmodul`, `frontend/tests/cockpit.test.tsx`, `frontend/e2e/phase6.spec.ts` |
| 3 | Ein Nutzer mit LAND-Scope sieht nur Daten seines Bereichs; Governance sieht global | V-COC-05, V-COC-06 | `backend/tests/test_cockpit.py::test_land_scope_sieht_nur_den_eigenen_bereich`, `::test_ohne_rolle_ist_das_cockpit_leer`, `frontend/e2e/phase6.spec.ts` |

### Auslegungen

Zwei Zeilen aus A.14 brauchen eine Definition, weil das Datenmodell sie nicht
unmittelbar hergibt — beide sind in `docs/entscheidungen.md` (E-11 und E-12) begründet:

- **„Prozesse ohne Owner"** — das Feld ist Pflicht und nie leer; gemeint sind
  Prozesse, deren eingetragener Owner deaktiviert ist oder gar keine
  Prozess-Owner-Rolle hat.
- **„Widersprüche zwischen Erklärung und Telemetrie"** — solange keine
  Telemetrie-Adapter angebunden sind, ist der Widerspruch die Kombination aus
  bestätigter Aussage T1 („läuft im vorgesehenen Rahmen") und einem aktuellen
  Compliance-Zustand auf rot.

### Abdeckung

- Backend: 99 % · Frontend: 98 % Anweisungen · Abnahme: 10 Anwendervorgänge (V-COC)

---

## Phase 7 — Governance-Query-API

**Enthalten:** die vier Endpunkte aus Architektur 7.3 — drei Vollabfragen und
die Delta-Abfrage —, OpenAPI-dokumentiert, mit eigenem Authentifizierungsschema
für andockende Anwendungen (Service-Token, konsistent mit Architektur 10.3).

Die API liefert **nur Auskünfte**: sie provisioniert nichts, sie sagt nur, was
der aus dem Prozess abgeleitete Rahmen ist. Ein Test hält fest, dass sie
ausschließlich `GET` kennt.

### Abnahmekriterien und Nachweis

| # | Kriterium | Vorgang über die Oberfläche | Technischer Nachweis |
|---|---|---|---|
| 1 | Die Vollabfragen liefern exakt die Werte, die die Fachlogik aus Phase 2 auch im Wizard zeigt — keine zweite Implementierung | V-INT-03 | `backend/tests/test_query_api.py::test_tier_und_profil_entsprechen_dem_wizard`, `::test_k_klassen_entsprechen_dem_wizard`, `frontend/e2e/phase7.spec.ts` |
| 2 | Ein Aufruf ohne gültige Service-Authentifizierung wird abgewiesen | V-INT-04 | `backend/tests/test_query_api.py::test_ohne_service_token_wird_abgewiesen`, `::test_nutzer_token_genuegt_nicht`, `frontend/e2e/phase7.spec.ts` |
| 3 | Die automatisch erzeugte Dokumentation ist ohne Nacharbeit verständlich — geprüft durch eine Probeintegration mit Platzhalter-Client | V-INT-03 | `backend/tests/test_query_api.py::test_openapi_dokumentiert_die_vier_endpunkte`, `::test_probeintegration_mit_platzhalter_client`, `frontend/e2e/phase7.spec.ts` |
| 4 | `GET /changes?since={cursor}` liefert genau die seither entstandenen Einträge, in Reihenfolge, ohne Duplikate und ohne Lücken; derselbe Cursor liefert dasselbe Ergebnis | V-INT-05, V-INT-06 | `backend/tests/test_query_api.py::test_delta_liefert_lueckenlos_und_in_reihenfolge`, `::test_derselbe_cursor_liefert_dasselbe`, `frontend/e2e/phase7.spec.ts` |

### Hinweise

Der Cursor wird **einschließend** gelesen: der in einer Antwort gelieferte
`naechster_cursor` geht beim nächsten Lauf unverändert als `since` wieder
hinein. Wäre er ausschließend, würde genau dieser eine Eintrag übersprungen —
und die Lückenlosigkeit wäre dahin. Begründet in `docs/entscheidungen.md`
(E-14).

Für den erklärten Rahmen externer Ziele trägt das Prozessobjekt ein eigenes
Feld `erlaubte_externe_ziele`; ein neues Ziel dort löst Gate 2 aus (A.11).
Siehe `docs/entscheidungen.md` (E-13).

### Abdeckung

- Backend: 99 % · Frontend: 98 % Anweisungen · Abnahme: 6 Anwendervorgänge (V-INT)
