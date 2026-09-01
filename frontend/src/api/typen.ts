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
