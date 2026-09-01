/** Vertragsformen der Backend-API (OpenAPI, Architektur 6.2). */

export type Kundenkreis = 'persoenlich' | 'team' | 'bereich' | 'unternehmen' | 'extern';
export type Ausfallfolge = 'keine' | 'gering' | 'spuerbar' | 'kritisch';
export type ProzessStatus = 'entwurf' | 'aktiv' | 'stillgelegt';
export type Ebene = 'INT' | 'LAND';

export interface Rollenzuweisung {
  id: string;
  user_id: string;
  rolle: string;
  scope_typ: 'global' | 'fachbereich' | 'organisationseinheit';
  scope_id: string | null;
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
}

export interface Umsetzung {
  id: string;
  prozessobjekt_id: string;
  land_org_id: string;
  lokale_abweichung: string | null;
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
  input_datenobjekt_ids: string[];
  output_datenobjekt_ids: string[];
  vorgelagert_ids: string[];
  nachgelagert_ids: string[];
  umsetzungen: Umsetzung[];
  tool_objekt_ids: string[];
  tier: number | null;
  ausgeloeste_k_klassen: string[];
  bewertung_gueltig_bis: string | null;
}

export interface ProzessEingabe {
  name: string;
  owner_user_id: string;
  stellvertretung_user_id: string;
  prozessgeber_org_id: string;
  supplier: string;
  input_datenobjekt_ids: string[];
  process_steps: string;
  output: string;
  customer: Kundenkreis;
  ausfallfolge: Ausfallfolge;
  umsetzung_land_org_ids?: string[];
}

// --- Bewertung (Phase 2) ---------------------------------------------------

export type BewertungsModus = 'schnell' | 'vollstaendig';

export interface Frage {
  id: string;
  text: string;
  block: string;
  block_titel: string;
  nummer: number;
  anzahl_bloecke: number;
}

export interface Ergebnis {
  tier: number;
  profil: Record<string, number>;
  ausgeloeste_k_klassen: string[];
  vollstaendig: boolean;
}

export interface WizardSchritt {
  naechste_frage: Frage | null;
  abgeschlossen: boolean;
  verboten: boolean;
  vollstaendig: boolean;
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
  vollstaendig: boolean;
  ausgeloeste_k_klassen: string[];
  antworten: Record<string, boolean>;
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
  | 'oeffentlich'
  | 'intern'
  | 'vertraulich'
  | 'personenbezogen'
  | 'mitarbeiterbezogen'
  | 'besondere_kategorie';

export interface Geerbt {
  kritikalitaet: number;
  reichweite: string | null;
  tier: number | null;
  mitbestimmung_flag: boolean;
  k_klassen: string[];
  quelle_prozess_ids: string[];
}

export interface ToolObjekt {
  id: string;
  name: string;
  beschreibung: string;
  technologie: string | null;
  kategorie: string | null;
  technischer_owner_user_id: string | null;
  organisationseinheit_id: string | null;
  herkunft: Herkunft;
  quelle: string | null;
  externe_id: string | null;
  status: AssetStatus;
  metadaten: Record<string, unknown>;
  letzte_aktivitaet_am: string | null;
  prozessobjekt_ids: string[];
  geerbt: Geerbt;
  schreibgeschuetzte_felder: string[];
}

export interface DatenObjekt {
  id: string;
  name: string;
  beschreibung: string;
  kategorie: Datenkategorie | null;
  owner_user_id: string | null;
  fachbereich_id: string | null;
  herkunft: Herkunft;
  quelle: string | null;
  externe_id: string | null;
  status: AssetStatus;
  metadaten: Record<string, unknown>;
  schreibgeschuetzte_felder: string[];
}

// --- Selbstverpflichtung und Gates (Phase 4) -------------------------------

export type SelbstverpflichtungTyp = 'prozesseigner' | 'technischer_owner';
export type GateTyp = '1' | '2';
export type GateStatus = 'eingereicht' | 'in_pruefung' | 'freigegeben' | 'abgelehnt';

export interface Aussage {
  id: string;
  text: string;
}

export interface Katalog {
  typ: SelbstverpflichtungTyp;
  aussagen: Aussage[];
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
  abgegeben_von: string;
  abgegeben_am: string;
  gueltig_bis: string | null;
  erinnerung_gesendet_am: string | null;
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
export type LenkungStatus = 'offen' | 'aufgeloest' | 'abgebrochen';
export type Aufloesungsart = 'anpassen' | 'rahmen_erweitern' | 'stilllegen';

export interface ComplianceZustand {
  id: string;
  tool_objekt_id: string;
  farbe: ComplianceFarbe;
  begruendung: string;
  abweichung_art: string | null;
  festgestellt_am: string;
  festgestellt_von: string | null;
}

export interface Lenkungsvorgang {
  id: string;
  tool_objekt_id: string;
  compliance_zustand_id: string | null;
  eskalationsstufe: number;
  frist: string;
  zugewiesen_an: string | null;
  status: LenkungStatus;
  aufloesungsart: Aufloesungsart | null;
  aufloesung_bewertung_id: string | null;
  aufgeloest_am: string | null;
  beschreibung: string;
  erstellt_am: string;
}

export interface Meldung {
  zustand: ComplianceZustand;
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
