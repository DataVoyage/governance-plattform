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
