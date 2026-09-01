# Phasenstand

Sieben Phasen, jede einzeln abnehmbar (Architektur 11). Eine Phase gilt erst als
abgeschlossen, wenn alle ihre Abnahmekriterien durch einen Test belegt sind.

Die Abnahmekriterien stammen aus dem internen Architekturdokument, das nicht in
diesem Repository liegt; sie sind unten je Phase im Wortlaut wiedergegeben.

Alle Tests — Backend, Oberfläche und Pipeline — laufen gegen dieselbe
PostgreSQL wie Entwicklung und Produktion. Die Angaben zur Abdeckung je Phase
beziehen sich auf diesen Stand.

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

**Enthalten:** containerisierte Entwicklungsumgebung und CI/CD-Pipeline,
Datenmodell als Alembic-Migration einschließlich `change_log` und
`konfiguration`, Authentifizierung über die zentrale Unternehmensidentität,
Rollen- und Rechte-Grundgerüst, erster Import-Adapter (Fachbereiche,
Organisationseinheiten, Teams), Prozess-Modul ohne Bewertung,
Frontend-Grundgerüst mit Sprachpfad-Routing für Deutsch und Französisch.

**Nicht enthalten, wie vorgegeben:** Bewertung, Asset-Verknüpfung, Gates, Cockpit.

### Abnahmekriterien und Nachweis

| # | Kriterium | Nachweis |
|---|---|---|
| 1 | Anmeldung ausschließlich über die zentrale Identität; jede Route ohne Session liefert 401 | `backend/tests/test_auth.py::test_ohne_session_liefert_jede_route_401` (über alle Routen parametrisiert), `test_dev_token_route_fehlt_ohne_entwicklungsmodus` |
| 2 | Import legt Fachbereiche, INT- und mindestens zwei LAND-Einheiten sowie Teams an; zweiter Lauf erzeugt keine Duplikate | `backend/tests/test_import.py::test_import_legt_stammdaten_an`, `::test_zweiter_lauf_erzeugt_keine_duplikate` |
| 3 | Prozess-Owner legt ein Prozessobjekt mit allen zehn Feldern an; Speichern ohne Stellvertretung wird abgelehnt | `backend/tests/test_prozess.py::test_owner_legt_prozess_mit_allen_zehn_feldern_an`, `::test_speichern_ohne_stellvertretung_wird_abgelehnt`, `frontend/e2e/phase1.spec.ts` |
| 4 | Ohne Rollenzuweisung im betroffenen Scope weder Ändern noch Löschen (Test je Rolle) | `backend/tests/test_prozess.py::test_ohne_rolle_kein_anlegen_und_kein_aendern`, `::test_owner_eines_anderen_fachbereichs_darf_nicht_schreiben`, `::test_umsetzer_pflegt_nur_die_lokale_abweichung`, `::test_auditor_sieht_global_und_darf_nicht_schreiben` |
| 5 | Ein Prozessobjekt ist mit zwei LAND-Organisationseinheiten verknüpfbar | `backend/tests/test_prozess.py::test_prozess_in_zwei_laendern_umsetzen`, `frontend/e2e/phase1.spec.ts` |
| 6 | Alle drei Images bauen gegen ein umkonfiguriertes Registry-Ziel, ohne Codeänderung | `.github/workflows/ci.yml`, Job `images` mit Matrix über zwei Registry-Ziele |
| 7 | Sprachwechsel ändert die Anzeigesprache, nicht die sichtbaren Datensätze | `frontend/tests/sprache.test.tsx::aendert beim Sprachwechsel die Anzeige, aber nicht die Datensaetze`, `frontend/e2e/phase1.spec.ts` |

### Abdeckung

- Backend: 97 % (Schwelle 90 %, erzwungen über `fail_under` in `pyproject.toml`)
- Frontend: 99 % Anweisungen (Schwelle 90 %, erzwungen über `vite.config.ts`)
- Oberfläche: drei Playwright-Läufe, ausschließlich headless

---

## Phase 2 — Bewertung

**Enthalten:** der sechsstufige Entscheidungsbaum als geführter Wizard (ein
Schritt pro Bildschirm, zwei Antwortknöpfe), serverseitige Tier- und
K-Klassen-Ableitung, Versionierung der Bewertungen mit Historie am
Prozessobjekt.

**Nicht enthalten, wie vorgegeben:** Asset-Verknüpfung. Die K-Klassen-Anzeige
sagt, welche Klassen ausgelöst sind — nicht, ob ein konkretes Tool sie erfüllt.

### Abnahmekriterien und Nachweis

| # | Kriterium | Nachweis |
|---|---|---|
| 1 | Sechs Themenblöcke in der festgelegten Reihenfolge; Verifikation über alle Antwortkombinationen ergibt das tabellierte Tier | `backend/tests/test_bewertung.py::test_bloecke_stehen_in_der_festgelegten_reihenfolge`, `::test_jede_antwortkombination_ergibt_das_tabellierte_tier` (4096 Kombinationen), `frontend/e2e/phase2.spec.ts` |
| 2 | Treffer auf „verbotene KI-Praxis" speichert keine Bewertung, sondern erzeugt einen Alarm | `backend/tests/test_bewertung.py::test_verbotstatbestand_speichert_keine_bewertung`, `frontend/e2e/phase2.spec.ts` |
| 3 | Schnelle Variante endet beim ersten Tier-3-Treffer; vollständige liefert das ganze Profil | `backend/tests/test_bewertung.py::test_schnelle_variante_endet_beim_ersten_tier_3_treffer`, `::test_vollstaendige_variante_liefert_das_ganze_profil`, `frontend/e2e/phase2.spec.ts` |
| 4 | Neubewertung erzeugt einen neuen Datensatz; die vorherige bleibt einsehbar | `backend/tests/test_bewertung.py::test_neubewertung_erzeugt_neuen_datensatz`, `frontend/tests/bewertung.test.tsx` |
| 5 | Profil `KI0-DS3-MB1-IT1-RG2-UR2` löst K1–K5, K7, K8, K9 aus — nicht K6, nicht K10 | `backend/tests/test_bewertung.py::test_beispiel_aus_dem_leitdokument`, `frontend/e2e/phase2.spec.ts` |

### Hinweis zur Ableitung

Die konkreten Fragen des Baums und die Bedingungen der zehn Maßnahmenklassen
sind in `docs/entscheidungen.md` (E-7) festgehalten, weil das Leitdokument
diesem Repository nicht beiliegt. Es gibt genau **eine** Implementierung: der
Wizard, die Historie und später die Governance-Query-API rufen dieselben
Funktionen in `app/services/bewertung.py`.

### Abdeckung

- Backend: 98 % · Frontend: 99 % Anweisungen · sechs Playwright-Läufe, headless

---

## Phase 3 — Asset-Management

**Enthalten:** Verwaltung von Tool-Objekten und Datenobjekten, n:m-Verknüpfung
zu Prozessobjekten mit Anzeige der maximum-vererbten Klassifikation, Erweiterung
des Import-Adapters um die Typen `tool` und `datenobjekt`.

### Abnahmekriterien und Nachweis

| # | Kriterium | Nachweis |
|---|---|---|
| 1 | Importiertes Tool mit unbekannter `externe_id` erscheint als „importiert, unbestätigt" und ist erst nach manueller Bestätigung verknüpfbar | `backend/tests/test_asset.py::test_importiertes_tool_ist_unbestaetigt_und_nicht_verknuepfbar`, `frontend/e2e/phase3.spec.ts` |
| 2 | Zweiter Import überschreibt die governance-seitig gesetzte Kategorie **nicht**, aktualisiert aber Name und technische Metadaten | `backend/tests/test_asset.py::test_zweiter_import_laesst_die_kategorie_unberuehrt`, `::test_importiertes_datenobjekt_behaelt_seine_kategorie` |
| 3 | Ein Tool an zwei Prozessen unterschiedlicher Kritikalität zeigt die höhere geerbte Einstufung | `backend/tests/test_asset.py::test_tool_zeigt_die_hoechste_geerbte_einstufung`, `::test_tool_erbt_tier_und_k_klassen_der_bewertungen`, `frontend/e2e/phase3.spec.ts` |
| 4 | Eine Datenobjekt-Kategorisierung ist im verknüpften Prozessobjekt sichtbar, ohne dort erneut gepflegt zu werden | `backend/tests/test_asset.py::test_kategorie_des_datenobjekts_wirkt_im_prozess`, `frontend/e2e/phase3.spec.ts` |

### Abdeckung

- Backend: 98 % · Frontend: 99 % Anweisungen · neun Playwright-Läufe, headless

---

## Phase 4 — Selbstverpflichtung und Gates

**Enthalten:** Selbstverpflichtungs-Modul mit den strukturierten Checklisten aus
A.10.2 und A.10.3, Gate-Modul mit Einreichung, Governance-Entscheidung und
Historie, Erinnerungslogik für die jährliche Erneuerung ab Tier 3.

### Abnahmekriterien und Nachweis

| # | Kriterium | Nachweis |
|---|---|---|
| 1 | Ein Tier-3-Prozessobjekt wechselt ohne vollständig abgegebene Selbstverpflichtung nicht in den Status „aktiv" | `backend/tests/test_gates.py::test_tier_3_wird_ohne_selbstverpflichtung_nicht_aktiv`, `::test_unvollstaendige_selbstverpflichtung_reicht_nicht`, `frontend/e2e/phase4.spec.ts` |
| 2 | Eine Gate-2-Einreichung ohne einen der fünf zulässigen Auslöser wird abgelehnt, bevor sie eingereicht werden kann | `backend/tests/test_gates.py::test_gate_2_ohne_ausloeser_wird_abgelehnt`, `::test_gate_2_kennt_nur_die_fuenf_ausloeser`, `frontend/e2e/phase4.spec.ts` (Pflichtauswahl im Formular) |
| 3 | Nur die Governance-Rolle entscheidet; Prozess-Owner und Auditor erhalten 403 | `backend/tests/test_gates.py::test_nur_governance_entscheidet`, `frontend/e2e/phase4.spec.ts` |
| 4 | 60 Tage vor Ablauf wird erinnert; nach Fristablauf erscheint der Datensatz im Cockpit-Filter (hier als Datenzustand geprüft) | `backend/tests/test_gates.py::test_erinnerung_60_tage_vor_ablauf_und_ueberfaelligkeit`, `::test_erinnerung_geht_an_den_technischen_owner` |

### Hinweise

Der Vorlauf von 60 Tagen und die Gültigkeitsdauer stehen in der
`konfiguration`-Tabelle und sind von der Governance-Rolle im laufenden Betrieb
änderbar. Der Lauf ist idempotent und läuft als Kubernetes-`CronJob`
(`python -m app.jobs erinnerungen`); ein doppelt gestarteter Job mahnt nicht
doppelt.

Die Aktivierung eines Tier-3-Prozessobjekts verlangt zusätzlich die Erstfreigabe
durch Gate 1 — begründet in `docs/entscheidungen.md` (E-9).

### Abdeckung

- Backend: 98 % · Frontend: 99 % Anweisungen · zwölf Playwright-Läufe, headless

---

## Phase 5 — Compliance und Lenkung

**Enthalten:** Compliance-Zustand als Zeitreihe je Tool-Objekt, gespeist aus
manuellen Meldungen; Lenkungs-Modul mit den drei Eskalationsstufen und den drei
Auflösungswegen aus A.13.5/A.13.6.

Automatisierte Telemetrie kommt erst mit künftigen Adaptern hinzu
(Architektur 7.4) — die Meldewege sind so gebaut, dass ein solcher Adapter
denselben Eintrag erzeugt wie eine Person.

### Abnahmekriterien und Nachweis

| # | Kriterium | Nachweis |
|---|---|---|
| 1 | Eine manuell erfasste Rahmenüberschreitung erzeugt automatisch einen Lenkungsvorgang in Stufe 1 mit der tier-abhängigen Frist | `backend/tests/test_lenkung.py::test_rahmenueberschreitung_erzeugt_stufe_1_mit_tier_frist`, `::test_frist_haengt_am_tier`, `frontend/e2e/phase5.spec.ts` |
| 2 | Ein Vorgang ohne Auflösung wechselt nach Fristablauf automatisch in Stufe 2; die Führungskraft des betroffenen Owners wird benachrichtigt | `backend/tests/test_lenkung.py::test_fristablauf_rueckt_in_stufe_2_und_informiert_die_fuehrungskraft`, `::test_eskalation_endet_bei_stufe_3` |
| 3 | Jede der drei Auflösungsarten ist eine eigene Aktion; „Rahmen erweitern" verlangt eine neue Bewertung und schließt erst nach deren Abschluss | `backend/tests/test_lenkung.py::test_rahmen_erweitern_verlangt_eine_neue_bewertung`, `::test_anpassen_schliesst_und_setzt_gruen`, `::test_stilllegen_setzt_das_tool_inaktiv`, `frontend/e2e/phase5.spec.ts` |

### Hinweise

Die Eskalation läuft als Kubernetes-`CronJob` (`python -m app.jobs
eskalationen`) und ist idempotent. Stufe 3 kennzeichnet den Vorgang für eine
technische Maßnahme; der eigentliche Zugriffsentzug erfolgt außerhalb dieser
Anwendung, in der jeweiligen technischen Plattform.

„Anpassen" und „Rahmen erweitern" führen das Tool auf grün zurück,
„Stilllegen" nicht — ein stillgelegtes Tool ist nicht wieder konform, es ist
außer Betrieb.

### Abdeckung

- Backend: 98 % · Frontend: 99 % Anweisungen · fünfzehn Playwright-Läufe, headless

---

## Phase 6 — Cockpit

**Enthalten:** die zehn Zeilen aus Leitdokument A.14 als je eigene, aufrufbare
Ansicht, mit Filterung nach Fachbereich und unter Beachtung der
Sichtbarkeitsregel aus Architektur 4.3.

Jeder Eintrag trägt sein Zielmodul samt Filter mit sich — ein Klick landet
direkt dort, wo die Sache abgearbeitet wird, statt in einer allgemeinen Liste.

### Abnahmekriterien und Nachweis

| # | Kriterium | Nachweis |
|---|---|---|
| 1 | Jede in A.14 genannte Zeile ist als eigene, aufrufbare Ansicht vorhanden | `backend/tests/test_cockpit.py::test_jede_zeile_aus_a14_ist_aufrufbar`, `frontend/e2e/phase6.spec.ts` |
| 2 | Ein Klick auf einen Cockpit-Eintrag führt zum korrekt vorgefilterten Zielmodul | `backend/tests/test_cockpit.py::test_eintraege_verweisen_auf_das_vorgefilterte_zielmodul`, `frontend/tests/cockpit.test.tsx`, `frontend/e2e/phase6.spec.ts` |
| 3 | Ein Nutzer mit LAND-Scope sieht nur Daten seines Bereichs; Governance sieht global | `backend/tests/test_cockpit.py::test_land_scope_sieht_nur_den_eigenen_bereich`, `::test_ohne_rolle_ist_das_cockpit_leer`, `frontend/e2e/phase6.spec.ts` |

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

- Backend: 98 % · Frontend: 99 % Anweisungen · achtzehn Playwright-Läufe, headless

---

## Phase 7 — Governance-Query-API

**Enthalten:** die vier Endpunkte aus Architektur 7.3 — drei Vollabfragen und
die Delta-Abfrage —, OpenAPI-dokumentiert, mit eigenem Authentifizierungsschema
für andockende Anwendungen (Service-Token, konsistent mit Architektur 10.3).

Die API liefert **nur Auskünfte**: sie provisioniert nichts, sie sagt nur, was
der aus dem Prozess abgeleitete Rahmen ist. Ein Test hält fest, dass sie
ausschließlich `GET` kennt.

### Abnahmekriterien und Nachweis

| # | Kriterium | Nachweis |
|---|---|---|
| 1 | Die Vollabfragen liefern exakt die Werte, die die Fachlogik aus Phase 2 auch im Wizard zeigt — keine zweite Implementierung | `backend/tests/test_query_api.py::test_tier_und_profil_entsprechen_dem_wizard`, `::test_k_klassen_entsprechen_dem_wizard`, `frontend/e2e/phase7.spec.ts` |
| 2 | Ein Aufruf ohne gültige Service-Authentifizierung wird abgewiesen | `backend/tests/test_query_api.py::test_ohne_service_token_wird_abgewiesen`, `::test_nutzer_token_genuegt_nicht`, `frontend/e2e/phase7.spec.ts` |
| 3 | Die automatisch erzeugte Dokumentation ist ohne Nacharbeit verständlich — geprüft durch eine Probeintegration mit Platzhalter-Client | `backend/tests/test_query_api.py::test_openapi_dokumentiert_die_vier_endpunkte`, `::test_probeintegration_mit_platzhalter_client`, `frontend/e2e/phase7.spec.ts` |
| 4 | `GET /changes?since={cursor}` liefert genau die seither entstandenen Einträge, in Reihenfolge, ohne Duplikate und ohne Lücken; derselbe Cursor liefert dasselbe Ergebnis | `backend/tests/test_query_api.py::test_delta_liefert_lueckenlos_und_in_reihenfolge`, `::test_derselbe_cursor_liefert_dasselbe`, `frontend/e2e/phase7.spec.ts` |

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

- Backend: 99 % · Frontend: 99 % Anweisungen · zweiundzwanzig Playwright-Läufe, headless
