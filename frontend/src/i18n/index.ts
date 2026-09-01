/**
 * Uebersetzungen als versionierte Textbausteine im Repository (Architektur 9.2).
 *
 * Bewusst keine Konfiguration: Uebersetzungen aendern sich mit Releases, nicht
 * im laufenden Betrieb durch die Governance-Rolle.
 */

export const SPRACHEN = ['de', 'fr'] as const;
export type Sprache = (typeof SPRACHEN)[number];
export const STANDARDSPRACHE: Sprache = 'de';

export function istSprache(wert: string | undefined): wert is Sprache {
  return typeof wert === 'string' && (SPRACHEN as readonly string[]).includes(wert);
}

const de = {
  'app.titel': 'Governance-Plattform',
  'app.abmelden': 'Abmelden',
  'app.sprache': 'Sprache',
  'app.laden': 'Wird geladen …',
  'app.fehler': 'Es ist ein Fehler aufgetreten',
  'app.nichtGefunden': 'Diese Seite gibt es nicht',
  'app.zurueck': 'Zurück',

  'anmeldung.titel': 'Anmeldung',
  'anmeldung.hinweis':
    'Die Anmeldung läuft ausschließlich über die zentrale Unternehmensidentität.',
  'anmeldung.entwicklungsmodus': 'Entwicklungsmodus: lokale Anmeldung',
  'anmeldung.kennung': 'Kennung',
  'anmeldung.name': 'Name',
  'anmeldung.absenden': 'Anmelden',

  'nav.prozesse': 'Prozesse',
  'nav.konfiguration': 'Einstellungen',

  'prozess.liste.titel': 'Prozessobjekte',
  'prozess.liste.leer': 'In Ihrem Bereich ist noch kein Prozessobjekt erfasst.',
  'prozess.liste.neu': 'Prozessobjekt anlegen',
  'prozess.feld.name': 'Name',
  'prozess.feld.owner': 'Prozess-Owner',
  'prozess.feld.stellvertretung': 'Stellvertretung',
  'prozess.feld.prozessgeber': 'Prozessgeber (INT)',
  'prozess.feld.supplier': 'Lieferant',
  'prozess.feld.inputDatenobjekte': 'Input-Datenobjekte',
  'prozess.feld.processSteps': 'Prozessschritte',
  'prozess.feld.output': 'Ergebnis',
  'prozess.feld.customer': 'Kundenkreis',
  'prozess.feld.ausfallfolge': 'Ausfallfolge',
  'prozess.feld.status': 'Status',
  'prozess.abgeleitet.titel': 'Abgeleitet — nicht eingebbar',
  'prozess.abgeleitet.hinweis':
    'Diese Werte berechnet der Server aus den erfassten Angaben und der Prozesskette.',
  'prozess.feld.reichweite': 'Reichweite',
  'prozess.feld.kritikalitaet': 'Kritikalität',
  'prozess.feld.mitbestimmung': 'Mitbestimmung berührt',
  'prozess.umsetzungen.titel': 'Umsetzende Landesorganisationen',
  'prozess.umsetzungen.leer': 'Noch keine Umsetzung erfasst.',
  'prozess.umsetzungen.abweichung': 'Lokale Abweichung',
  'prozess.speichern': 'Speichern',
  'prozess.abbrechen': 'Abbrechen',
  'prozess.pflichtfeld': 'Pflichtfeld',
  'prozess.stellvertretungPflicht': 'Ohne Stellvertretung kann nicht gespeichert werden.',

  'kundenkreis.persoenlich': 'Persönlich',
  'kundenkreis.team': 'Team',
  'kundenkreis.bereich': 'Fachbereich',
  'kundenkreis.unternehmen': 'Unternehmen',
  'kundenkreis.extern': 'Extern',

  'ausfallfolge.keine': 'Keine',
  'ausfallfolge.gering': 'Gering',
  'ausfallfolge.spuerbar': 'Spürbar',
  'ausfallfolge.kritisch': 'Kritisch',

  'status.entwurf': 'Entwurf',
  'status.aktiv': 'Aktiv',
  'status.stillgelegt': 'Stillgelegt',

  'ja': 'Ja',
  'nein': 'Nein',
} as const;

export type Schluessel = keyof typeof de;

const fr: Record<Schluessel, string> = {
  'app.titel': 'Plateforme de gouvernance',
  'app.abmelden': 'Se déconnecter',
  'app.sprache': 'Langue',
  'app.laden': 'Chargement …',
  'app.fehler': 'Une erreur est survenue',
  'app.nichtGefunden': "Cette page n'existe pas",
  'app.zurueck': 'Retour',

  'anmeldung.titel': 'Connexion',
  'anmeldung.hinweis':
    "La connexion passe exclusivement par l'identité centrale de l'entreprise.",
  'anmeldung.entwicklungsmodus': 'Mode développement : connexion locale',
  'anmeldung.kennung': 'Identifiant',
  'anmeldung.name': 'Nom',
  'anmeldung.absenden': 'Se connecter',

  'nav.prozesse': 'Processus',
  'nav.konfiguration': 'Paramètres',

  'prozess.liste.titel': 'Objets de processus',
  'prozess.liste.leer': "Aucun objet de processus n'est encore saisi dans votre domaine.",
  'prozess.liste.neu': 'Créer un objet de processus',
  'prozess.feld.name': 'Nom',
  'prozess.feld.owner': 'Responsable du processus',
  'prozess.feld.stellvertretung': 'Suppléance',
  'prozess.feld.prozessgeber': 'Émetteur du processus (INT)',
  'prozess.feld.supplier': 'Fournisseur',
  'prozess.feld.inputDatenobjekte': "Objets de données en entrée",
  'prozess.feld.processSteps': 'Étapes du processus',
  'prozess.feld.output': 'Résultat',
  'prozess.feld.customer': 'Cercle de clients',
  'prozess.feld.ausfallfolge': 'Conséquence de la défaillance',
  'prozess.feld.status': 'Statut',
  'prozess.abgeleitet.titel': 'Dérivé — non saisissable',
  'prozess.abgeleitet.hinweis':
    'Le serveur calcule ces valeurs à partir des données saisies et de la chaîne de processus.',
  'prozess.feld.reichweite': 'Portée',
  'prozess.feld.kritikalitaet': 'Criticité',
  'prozess.feld.mitbestimmung': 'Cogestion concernée',
  'prozess.umsetzungen.titel': 'Organisations nationales de mise en œuvre',
  'prozess.umsetzungen.leer': 'Aucune mise en œuvre enregistrée.',
  'prozess.umsetzungen.abweichung': 'Écart local',
  'prozess.speichern': 'Enregistrer',
  'prozess.abbrechen': 'Annuler',
  'prozess.pflichtfeld': 'Champ obligatoire',
  'prozess.stellvertretungPflicht': 'Impossible d’enregistrer sans suppléance.',

  'kundenkreis.persoenlich': 'Personnel',
  'kundenkreis.team': 'Équipe',
  'kundenkreis.bereich': 'Domaine',
  'kundenkreis.unternehmen': 'Entreprise',
  'kundenkreis.extern': 'Externe',

  'ausfallfolge.keine': 'Aucune',
  'ausfallfolge.gering': 'Faible',
  'ausfallfolge.spuerbar': 'Sensible',
  'ausfallfolge.kritisch': 'Critique',

  'status.entwurf': 'Brouillon',
  'status.aktiv': 'Actif',
  'status.stillgelegt': 'Désactivé',

  'ja': 'Oui',
  'nein': 'Non',
};

export const KATALOG: Record<Sprache, Record<Schluessel, string>> = { de, fr };

export function uebersetze(sprache: Sprache, schluessel: Schluessel): string {
  return KATALOG[sprache][schluessel] ?? KATALOG[STANDARDSPRACHE][schluessel] ?? schluessel;
}
