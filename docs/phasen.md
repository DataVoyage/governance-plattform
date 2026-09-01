# Phasenstand

Sieben Phasen, jede einzeln abnehmbar (Architektur 11). Eine Phase gilt erst als
abgeschlossen, wenn alle ihre Abnahmekriterien durch einen Test belegt sind.

| Phase | Inhalt | Stand |
|---|---|---|
| 1 | Fundament | ✅ abgeschlossen |
| 2 | Bewertung | ✅ abgeschlossen |
| 3 | Asset-Management | ⏳ offen |
| 4 | Selbstverpflichtung und Gates | ⏳ offen |
| 5 | Compliance und Lenkung | ⏳ offen |
| 6 | Cockpit | ⏳ offen |
| 7 | Governance-Query-API | ⏳ offen |

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
sind in `docs/entscheidungen.md` (E-8) festgehalten, weil das Leitdokument
diesem Repository nicht beiliegt. Es gibt genau **eine** Implementierung: der
Wizard, die Historie und später die Governance-Query-API rufen dieselben
Funktionen in `app/services/bewertung.py`.

### Abdeckung

- Backend: 98 % · Frontend: 99 % Anweisungen · sechs Playwright-Läufe, headless
