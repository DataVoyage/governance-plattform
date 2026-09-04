/** Vertragsformen der Backend-API (OpenAPI, Architektur 6.2). */

export type Kundenkreis = 'persoenlich' | 'team' | 'bereich' | 'unternehmen' | 'extern';
export type Ausfallfolge = 'keine' | 'gering' | 'spuerbar' | 'kritisch';
/**
 * Vier Zustände, und der vierte ist der wichtigste: `freigabe_ausstehend`
 * heißt **läuft, ist aber für seine jetzige Einstufung nicht freigegeben** —
 * anders als `entwurf`, das „noch nie in Betrieb" heißt (E-60).
 */
export type ProzessStatus = 'entwurf' | 'aktiv' | 'freigabe_ausstehend' | 'stillgelegt';
export type Ebene = 'INT' | 'LAND';

/** Die acht Rollen aus Leitdokument A.15. */
export type Rolle =
  | 'prozess_owner'
  | 'prozess_umsetzer'
  | 'technischer_owner'
  | 'datenobjekt_owner'
  | 'governance'
  | 'plattform'
  | 'auditor'
  | 'app_administrator';

export type ScopeTyp = 'global' | 'fachbereich' | 'organisationseinheit';

export interface Rollenzuweisung {
  id: string;
  user_id: string;
  rolle: Rolle;
  scope_typ: ScopeTyp;
  scope_id: string | null;
}

/** Wer eine Rolle in einem Bereich trägt — Kennung und Name, sonst nichts. */
export interface Person {
  id: string;
  name: string;
}

export interface Profil {
  id: string;
  email: string;
  name: string;
  rollen: Rollenzuweisung[];
}

export interface Fachbereich {
  id: string;
  name: string;
  code: string;
}

export interface Organisationseinheit {
  id: string;
  fachbereich_id: string;
  ebene: Ebene;
  land_code: string | null;
}

export interface Nutzer {
  id: string;
  email: string;
  name: string;
  ist_aktiv: boolean;
  /** Ab Eskalationsstufe 2 geht die Meldung an sie (A.13.5). */
  fuehrungskraft_user_id: string | null;
}

export interface Umsetzung {
  id: string;
  prozessobjekt_id: string;
  land_org_id: string;
  lokale_abweichung: string | null;
}

/**
 * Was der Angemeldete mit **diesem** Objekt tun darf.
 *
 * Der Server rechnet es aus und schreibt es an die Antwort; die Oberfläche
 * baut die Regeln nicht nach. Eine Auskunft, keine Sicherung — jede
 * schreibende Route prüft unabhängig noch einmal (Architektur 10.2).
 */
export interface Prozessrechte {
  bearbeiten: boolean;
  bewerten: boolean;
  selbstverpflichten: boolean;
  gate_einreichen: boolean;
  umsetzung_pflegen: boolean;
}

export interface Toolrechte {
  bearbeiten: boolean;
  attestieren: boolean;
  verknuepfen: boolean;
  zustand_melden: boolean;
  kompensieren: boolean;
  selbstverpflichten: boolean;
  bestaetigen: boolean;
}

export interface Datenobjektrechte {
  /** Name, Beschreibung, Quellsystem. */
  bearbeiten: boolean;
  /** Die Kategorie — nur der Datenobjekt-Owner des Fachbereichs. */
  kategorisieren: boolean;
  /** Den Fachbereich wechseln — nur die Governance. */
  anker_aendern: boolean;
  bestaetigen: boolean;
}

export interface Lenkungsrechte {
  aufloesen: boolean;
  abbrechen: boolean;
}

export interface Prozess {
  id: string;
  name: string;
  owner_user_id: string;
  stellvertretung_user_id: string;
  prozessgeber_org_id: string;
  supplier: string;
  process_steps: string;
  output: string;
  customer: Kundenkreis;
  ausfallfolge: Ausfallfolge;
  status: ProzessStatus;
  reichweite: string | null;
  kritikalitaet: number;
  mitbestimmung_flag: boolean;
  schritt_anzahl: number;
  schritte_zu_viele: boolean;
  input_datenobjekt_ids: string[];
  output_datenobjekt_ids: string[];
  vorgelagert_ids: string[];
  nachgelagert_ids: string[];
  erlaubte_externe_ziele: string[];
  umsetzungen: Umsetzung[];
  tool_objekt_ids: string[];
  tier: number | null;
  ausgeloeste_k_klassen: string[];
  bewertung_gueltig_bis: string | null;
  rechte: Prozessrechte;
}

export interface ProzessEingabe {
  name: string;
  owner_user_id: string;
  stellvertretung_user_id: string;
  prozessgeber_org_id: string;
  supplier: string;
  input_datenobjekt_ids: string[];
  output_datenobjekt_ids: string[];
  process_steps: string;
  output: string;
  customer: Kundenkreis;
  ausfallfolge: Ausfallfolge;
  vorgelagert_ids?: string[];
  nachgelagert_ids?: string[];
  umsetzung_land_org_ids?: string[];
  /** Der erklärte Rahmen nach A.13.2 Schicht 1 — kein SIPOC-Feld. */
  erlaubte_externe_ziele?: string[];
}

// --- Bewertung (Phase 2) ---------------------------------------------------

/** Ein Grund für einen Vorschlag, in der Sprache des Objekts, aus dem er stammt. */
export interface Beleg {
  text: string;
  quelle: string;
}

export interface Frage {
  id: string;
  text: string;
  block: string;
  block_titel: string;
  nummer: number;
  anzahl_bloecke: number;
  /** Dreiwertig: `null` heißt „die Daten geben nichts her" (Leitdokument A.8.4). */
  vorschlag: boolean | null;
  belege: Beleg[];
}

export interface KKlasse {
  kennung: string;
  name: string;
  erklaerung: string;
}

export interface Ergebnis {
  tier: number;
  profil: Record<string, number>;
  ausgeloeste_k_klassen: string[];
  klassen: KKlasse[];
  auflagen: string[];
}

export interface WizardSchritt {
  naechste_frage: Frage | null;
  abgeschlossen: boolean;
  verboten: boolean;
  vorschau: Ergebnis | null;
}

export interface Bewertung {
  id: string;
  prozessobjekt_id: string;
  ki_stufe: number;
  ds_stufe: number;
  mb_stufe: number;
  it_stufe: number;
  rg_stufe: number;
  ur_stufe: number;
  tier: number;
  gesperrt: boolean;
  ausgeloeste_k_klassen: string[];
  antworten: Record<string, boolean>;
  vorschlaege: Record<string, boolean>;
  abweichungen: Record<string, string>;
  bewertet_von: string;
  bewertet_am: string;
  gueltig_bis: string | null;
}

export interface Alarm {
  id: string;
  typ: string;
  prozessobjekt_id: string | null;
  beschreibung: string;
  ausgeloest_von: string;
  quittiert: boolean;
  erstellt_am: string;
}

export interface BewertungAbschluss {
  bewertung: Bewertung | null;
  alarm: Alarm | null;
}

// --- Assets (Phase 3) ------------------------------------------------------

export type Herkunft = 'importiert' | 'manuell';
export type AssetStatus = 'importiert_unbestaetigt' | 'bestaetigt' | 'inaktiv';
export type Datenkategorie =
  'oeffentlich' | 'intern' | 'vertraulich' | 'personenbezogen' | 'besondere_kategorie';

export interface Geerbt {
  kritikalitaet: number;
  reichweite: string | null;
  tier: number | null;
  mitbestimmung_flag: boolean;
  k_klassen: string[];
  quelle_prozess_ids: string[];
  beitraege: Kantenbeitrag[];
}

/** Was eine einzelne Prozesskante zum geerbten Maximum beiträgt (A.4.4). */
export interface Kantenbeitrag {
  prozess_id: string;
  name: string;
  kritikalitaet: number;
  reichweite: string | null;
  tier: number | null;
  mitbestimmung_flag: boolean;
  k_klassen: string[];
  massgeblich: boolean;
}

/** Wie ein Tool angestoßen wird (Leitdokument A.6). */
export type Lauftyp = 'interaktiv' | 'getriggert' | 'geplant';

/** Unter welcher Identität ein Tool läuft (A.13.2 Schicht 1, Element 7). */
export type Ausfuehrungsidentitaet = 'persoenlich' | 'benannter_dienst' | 'geteiltes_konto';

/** Die Triage aus A.6: verändert das Tool den Prozessausgang oder gestaltet es? */
export type Wirkungsart = 'veraendernd' | 'gestaltend';

export interface ToolObjekt {
  id: string;
  name: string;
  beschreibung: string;
  technologie: string | null;
  kategorie: string | null;
  technischer_owner_user_id: string | null;
  stellvertretung_user_id: string | null;
  organisationseinheit_id: string | null;
  lauftyp: Lauftyp | null;
  ausfuehrungsidentitaet: Ausfuehrungsidentitaet | null;
  statische_zugangsdaten: boolean | null;
  /** Die beiden Verbote, die in der Zielplattform geschehen (E-64). */
  protokollierung_umgangen: boolean | null;
  daten_ins_offene_netz: boolean | null;
  externe_ziele: string[];
  herkunft: Herkunft;
  quelle: string | null;
  externe_id: string | null;
  status: AssetStatus;
  metadaten: Record<string, unknown>;
  letzte_aktivitaet_am: string | null;
  prozessobjekt_ids: string[];
  geerbt: Geerbt;
  /** `null` heißt unbeantwortet — und ist kein erklärtes „Nein". */
  attest_entscheidung_ueber_personen: boolean | null;
  attest_mensch_dazwischen: boolean | null;
  attest_undeklarierte_quellen: boolean | null;
  attestiert_am: string | null;
  attestiert_von_user_id: string | null;
  /** Wer erklärt hat, im Klartext — A.6 verlangt die Erklärung mit Namen. */
  attestiert_von_name: string | null;
  attestierung_vollstaendig: boolean;
  wirkungsart: Wirkungsart | null;
  wirkungsart_grund: 'schreibzugriff' | 'kein_mensch' | 'nur_lesend' | 'offen';
  schreibgeschuetzte_felder: string[];
  rechte: Toolrechte;
}

/** Was die Oberfläche beim Anlegen und Ändern eines Tool-Objekts schickt. */
export interface ToolEingabe {
  name: string;
  beschreibung?: string;
  technologie?: string | null;
  kategorie?: string | null;
  technischer_owner_user_id?: string | null;
  stellvertretung_user_id?: string | null;
  organisationseinheit_id?: string | null;
  lauftyp?: Lauftyp | null;
  ausfuehrungsidentitaet?: Ausfuehrungsidentitaet | null;
  statische_zugangsdaten?: boolean | null;
  protokollierung_umgangen?: boolean | null;
  daten_ins_offene_netz?: boolean | null;
  externe_ziele?: string[];
}

/** Eine Datenkante des Tools, geprüft gegen den Prozessrahmen (A.4.6). */
export interface Datennutzung {
  datenobjekt_id: string;
  name: string;
  kategorie: Datenkategorie | null;
  zugriffsart: Zugriffsart;
  im_prozessrahmen: boolean;
  kategorie_gedeckt: boolean;
}

/** Die drei Erklärungen aus A.6 — alle drei zusammen, nie einzeln. */
export interface Attestierung {
  attest_entscheidung_ueber_personen: boolean;
  attest_mensch_dazwischen: boolean;
  attest_undeklarierte_quellen: boolean;
}

export interface DatenObjekt {
  id: string;
  name: string;
  beschreibung: string;
  kategorie: Datenkategorie | null;
  fachbereich_id: string | null;
  quellsystem: string | null;
  herkunft: Herkunft;
  quelle: string | null;
  externe_id: string | null;
  status: AssetStatus;
  metadaten: Record<string, unknown>;
  schreibgeschuetzte_felder: string[];
  rechte: Datenobjektrechte;
}

/**
 * Die vier Felder der Stufe 1 (A.7) jeder bestätigten Quelle — zum Auswählen,
 * nicht zum Pflegen. Was hier nicht steht, liefert der Server auch nicht
 * (docs/rollen-und-scopes.md, 7.3).
 */
export interface DatenobjektKatalog {
  id: string;
  name: string;
  fachbereich_id: string | null;
  kategorie: Datenkategorie | null;
  quellsystem: string | null;
}

// --- Selbstverpflichtung und Gates (Phase 4) -------------------------------

export type SelbstverpflichtungTyp = 'prozesseigner' | 'technischer_owner';
export type GateTyp = '1' | '2';
export type GateStatus = 'eingereicht' | 'in_pruefung' | 'freigegeben' | 'abgelehnt';

export interface Aussage {
  id: string;
  text: string;
  /** Ab welchem Tier die Aussage verlangt wird — 1 heißt: auch in der Kurzform (A.10.5). */
  ab_tier: number;
}

export interface Katalog {
  typ: SelbstverpflichtungTyp;
  aussagen: Aussage[];
  version: number;
}

export interface AussageEingabe {
  bestaetigt: boolean;
  kommentar: string;
}

export interface Selbstverpflichtung {
  id: string;
  typ: SelbstverpflichtungTyp;
  prozessobjekt_id: string | null;
  tool_objekt_id: string | null;
  aussagen: Record<string, AussageEingabe>;
  vollstaendig: boolean;
  katalog_version: number;
  bewertung_id: string | null;
  tier_bei_abgabe: number | null;
  abgegeben_von: string;
  abgegeben_am: string;
  gueltig_bis: string | null;
  erinnerung_gesendet_am: string | null;
}

/** Trägt die aktuelle Erklärung eines Objekts — und wenn nicht, warum. */
export interface Deckung {
  gedeckt: boolean;
  grund: string;
  grundtext: string;
  verlangte_aussagen: string[];
  tier: number | null;
  aktuelle: Selbstverpflichtung | null;
}

export interface GateVorgang {
  id: string;
  prozessobjekt_id: string;
  gate_typ: GateTyp;
  ausloeser: string | null;
  begruendung: string;
  status: GateStatus;
  eingereicht_von: string;
  entschieden_von: string | null;
  entscheidungskommentar: string;
  entschieden_am: string | null;
  erstellt_am: string;
}

// --- Compliance und Lenkung (Phase 5) --------------------------------------

export type ComplianceFarbe = 'gruen' | 'gelb' | 'rot';

/**
 * Die sechs organisationsweiten Verbote aus A.13.2 Schicht 2.
 *
 * Abschließend wie die Gate-2-Auslöser: eine Liste, die um einen freien Grund
 * ergänzt werden kann, ist keine Liste mehr.
 */
export type Schicht2Verbot =
  | 'identitaet_umgangen'
  | 'statische_zugangsdaten'
  | 'undeklarierte_quellen'
  | 'entscheidung_ohne_mensch'
  | 'daten_ins_offene_netz'
  | 'protokollierung_umgangen';

/** Ein Element des Erlaubnisrahmens: erlaubt, gemessen, abweichend. */
export interface RahmenElement {
  schluessel: string;
  erlaubt: string[];
  gemessen: string[];
  abweichung: string[];
  /** Falsch, wo es zu diesem Element keine Messung gibt (Reichweite). */
  messbar: boolean;
  eingehalten: boolean;
}

export interface Rahmen {
  elemente: RahmenElement[];
  tier: number | null;
  quelle_prozess_ids: string[];
  eingehalten: boolean;
  schicht2_befunde: Schicht2Verbot[];
}

export interface Schicht2VerbotEintrag {
  schluessel: Schicht2Verbot;
  automatisch_erkennbar: boolean;
}

/** Wie eine Technologie eine Anforderungsklasse abdeckt (A.9.3). */
export type Klassenbewertung = 'erfuellt' | 'kompensierbar' | 'nicht_erfuellbar';

/**
 * Was der Abgleich Klasse gegen Technologie ergeben hat.
 *
 * `ungeprueft` ist eine eigene Art und kein stiller Erfolg: eine Klasse ohne
 * Matrixeintrag ist nicht abgedeckt, sondern unbeantwortet.
 */
export type Befundart =
  'erfuellt' | 'kompensiert' | 'kompensation_fehlt' | 'ausschluss' | 'ungeprueft';

/** Eine Anforderungsklasse mit Name, Zweck und Auslöserbedingung (A.9.2). */
export interface Anforderungsklasse {
  schluessel: string;
  name: string;
  zweck: string;
  ausloeser: string;
}

export interface Technologie {
  schluessel: string;
  name: string;
}

export interface Matrixfeld {
  technologie: string;
  k_klasse: string;
  bewertung: Klassenbewertung;
  begruendung: string;
  geaendert_am: string | null;
}

export interface Befund {
  tool_id: string;
  tool_name: string;
  technologie: string | null;
  k_klasse: string;
  art: Befundart;
  begruendung: string;
  massnahme: string;
  offen: boolean;
}

export interface Toolbefund {
  tool_id: string;
  tool_name: string;
  technologie: string | null;
  k_klassen: string[];
  befunde: Befund[];
  ausschluss: boolean;
  offen: number;
}

/** Eine Rolle mit dem Satz, was sie darf (Leitdokument A.15). */
export interface RolleErklaert {
  schluessel: Rolle;
  erklaerung: string;
}

/**
 * „Diese Zuweisung gibt Zugriff auf N Prozessobjekte."
 *
 * Der Name unterscheidet sich bewusst von `Wirkung`: dort geht es um die
 * Folgen einer Umklassifizierung, hier um die einer Rollenzuweisung.
 */
export interface Rollenwirkung {
  rolle: Rolle;
  scope_typ: ScopeTyp;
  scope_name: string;
  prozessobjekte: number;
  tool_objekte: number;
  beispiele: string[];
}

export interface Feldaenderung {
  feld: string;
  vorher: string;
  nachher: string;
}

/** Ein Eintrag des Änderungsprotokolls, lesbar aufbereitet (A.13.7). */
export interface Nachweiseintrag {
  cursor: number;
  entity_type: string;
  entity_id: string;
  aktion: string;
  zeitpunkt: string;
  akteur: string;
  gegenstand: string;
  aenderungen: Feldaenderung[];
}

/** Eine Governance-Einstellung aus Architektur 6.6. */
export interface Einstellung {
  schluessel: string;
  wert: string;
  beschreibung: string;
}
export type LenkungStatus = 'offen' | 'aufgeloest' | 'abgebrochen';
export type Aufloesungsart = 'anpassen' | 'rahmen_erweitern' | 'stilllegen';

export interface ComplianceZustand {
  id: string;
  tool_objekt_id: string;
  farbe: ComplianceFarbe;
  begruendung: string;
  abweichung_art: string | null;
  schicht2_verbot: Schicht2Verbot | null;
  festgestellt_am: string;
  festgestellt_von: string | null;
}

export interface Lenkungsvorgang {
  id: string;
  tool_objekt_id: string;
  compliance_zustand_id: string | null;
  eskalationsstufe: number;
  schicht2_verbot: Schicht2Verbot | null;
  frist: string;
  zugewiesen_an: string | null;
  status: LenkungStatus;
  aufloesungsart: Aufloesungsart | null;
  aufloesung_bewertung_id: string | null;
  aufgeloest_am: string | null;
  /** Was festgestellt wurde — gehört dem Melder und ändert sich nicht. */
  beschreibung: string;
  /** Was der Auflösende dazu sagt. Getrennt von der Feststellung (E-63). */
  aufloesungskommentar: string;
  /** Was die Anwendung am Werkzeug gerade selbst misst. Leer heißt: nichts. */
  offene_abweichungen: string[];
  erstellt_am: string;
  rechte: Lenkungsrechte;
}

/** Der gerechnete Zustand eines Werkzeugs, mit seiner Zeitreihe (E-64). */
export interface Compliance {
  farbe: ComplianceFarbe;
  /** Was die Anwendung gerade selbst sieht; leer heißt: nichts. */
  offene_abweichungen: string[];
  verlauf: ComplianceZustand[];
}

export interface Meldung {
  /** Fehlt, wenn nichts passiert ist: dann lief schon ein ungeklärter Vorgang. */
  zustand: ComplianceZustand | null;
  lenkungsvorgang: Lenkungsvorgang | null;
}

// --- Cockpit (Phase 6) -----------------------------------------------------

export interface CockpitEintrag {
  id: string;
  titel: string;
  hinweis: string;
  ziel_modul: string;
  ziel_filter: Record<string, string>;
}

export interface CockpitZeilenkopf {
  schluessel: string;
  titel: string;
  beschreibung: string;
  anzahl: number;
  aggregat: Record<string, Record<string, Record<string, number>>> | null;
}

export interface CockpitZeile extends CockpitZeilenkopf {
  eintraege: CockpitEintrag[];
}

// --- Wirkung einer Umklassifizierung (Leitdokument A.4.7) ------------------

/** Wie ein Tool ein Datenobjekt anfasst (Leitdokument A.6). */
export type Zugriffsart = 'lesen' | 'schreiben' | 'lesen_schreiben';

export interface WirkungProzess {
  id: string;
  name: string;
  tier: number | null;
  mitbestimmung_flag: boolean;
  mitbestimmung_flag_neu: boolean;
  als_input: boolean;
  als_output: boolean;
}

export interface WirkungTool {
  id: string;
  name: string;
  zugriffsart: Zugriffsart | null;
  ueber_prozess: boolean;
}

export interface Wirkung {
  kategorie_alt: Datenkategorie | null;
  kategorie_neu: Datenkategorie | null;
  prozesse: WirkungProzess[];
  tools: WirkungTool[];
  mitbestimmung_neu: number;
}
