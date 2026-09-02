/**
 * Sprechende Bezeichnungen statt technischer Schluessel.
 *
 * Grundsatz 3 des Design-Systems: Nie ein technischer Schluessel im Sichtfeld.
 * Eine Organisationseinheit heisst „Finance — Land DE", nicht `a3f19c2b`.
 */

import type { Fachbereich, Organisationseinheit } from '@/api/typen';

export function orgBezeichnung(
  einheit: Organisationseinheit | undefined,
  fachbereiche: Fachbereich[],
): string {
  if (einheit === undefined) return '—';
  const fachbereich = fachbereiche.find((f) => f.id === einheit.fachbereich_id);
  const ebene = einheit.ebene === 'LAND' ? `Land ${einheit.land_code ?? '?'}` : 'INT';
  return fachbereich === undefined ? ebene : `${fachbereich.name} — ${ebene}`;
}
