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
  'app.farbschema': 'Darstellung',
  'app.farbschema.system': 'Auto',
  'app.farbschema.hell': 'Hell',
  'app.farbschema.dunkel': 'Dunkel',

  'stilprobe.titel': 'Stilprobe',
  'stilprobe.untertitel':
    'Alle Bausteine des Design-Systems „Klar" — lebende Dokumentation und Sichtprüfung in hell und dunkel.',
  'stilprobe.marke': 'Marke',
  'stilprobe.marke.klar': 'Klar',
  'stilprobe.marke.kaufland': 'Kaufland',
  'stilprobe.knoepfe': 'Knöpfe',
  'stilprobe.abzeichen': 'Abzeichen',
  'stilprobe.eingaben': 'Eingaben',
  'stilprobe.listen': 'Gruppierte Listen',
  'stilprobe.referenz': 'Referenz-Wähler',
  'stilprobe.zustaende': 'Hinweise und Zustände',
  'stilprobe.blatt': 'Blatt',
  'stilprobe.blattOeffnen': 'Blatt öffnen',
  'stilprobe.keineTreffer': 'Kein Eintrag gefunden',

  'anmeldung.titel': 'Anmeldung',
  'anmeldung.hinweis':
    'Die Anmeldung läuft ausschließlich über die zentrale Unternehmensidentität.',
  'anmeldung.entwicklungsmodus': 'Entwicklungsmodus: lokale Anmeldung',
  'anmeldung.kennung': 'Kennung',
  'anmeldung.name': 'Name',
  'anmeldung.namehilfe': 'Frei lassen — dann gilt die Kennung auch als Name.',
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
  'prozess.feld.inputDatenobjekte': 'Input — Datenobjekte',
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
  'prozess.umsetzungen.abweichungHilfe':
    'Was diese Landesorganisation anders macht. Freiwillig — leer heißt: wie der INT-Prozess.',
  'prozess.speichern': 'Speichern',
  'prozess.abbrechen': 'Abbrechen',
  'prozess.pflichtfeld': 'Pflichtfeld',
  'prozess.stellvertretungPflicht': 'Ohne Stellvertretung kann nicht gespeichert werden.',
  'prozess.feld.outputDatenobjekte': 'Output — Datenobjekte',
  'prozess.feld.vorgelagert': 'Vorgelagerte Prozesse',
  'prozess.feld.nachgelagert': 'Nachgelagerte Prozesse',
  'prozess.hilfe.inputDatenobjekte':
    'Referenz auf bestehende Datenobjekte, kein Freitext. Ihre Kategorie bestimmt die Bewertung mit.',
  'prozess.hilfe.outputDatenobjekte': 'Was dieser Prozess erzeugt oder fortschreibt.',
  'prozess.hilfe.vorgelagert': 'Wer liefert zu — als Referenz, damit die Kette auswertbar bleibt.',
  'prozess.hilfe.nachgelagert':
    'Wer konsumiert. Aus dieser Kante berechnet sich die Kritikalität dieses Prozesses.',
  'prozess.hilfe.supplier': 'Nur für Zulieferer außerhalb des Prozessregisters.',
  'prozess.hilfe.schritte': '5 bis 7 Schritte, Stichworte — eine Zeile je Schritt.',
  'prozess.hilfe.output':
    'Das Ergebnis in Worten; als Referenz gehört es in die Output-Datenobjekte.',
  'prozess.schritte.zaehler': 'Schritte',
  'prozess.schritte.warnung':
    'Mehr als sieben Schritte deuten auf die falsche Flughöhe. Verlinken Sie besser einen weiteren Prozess.',
  'prozess.suchen.datenobjekt': 'Datenobjekt suchen …',
  'prozess.suchen.prozess': 'Prozessobjekt suchen …',
  'prozess.keineTreffer': 'Kein Eintrag gefunden',
  'prozess.bearbeiten': 'Bearbeiten',
  'prozess.bearbeiten.titel': 'Prozessobjekt bearbeiten',
  'prozess.aktivieren': 'Aktivieren',
  'prozess.stilllegen': 'Stilllegen',
  'prozess.wiederaufnehmen': 'Wieder in Entwurf setzen',
  'prozess.gruppe.beteiligte': 'Verantwortung',
  'prozess.gruppe.sipoc': 'SIPOC — Grenzen und Schnittstellen',
  'prozess.gruppe.kette': 'Prozesskette',
  'prozess.gruppe.umsetzung': 'Umsetzung',
  'prozess.wirkung.titel': 'Wirkung',
  'prozess.wirkung.hinweis':
    'Abwärts: Was steht still, wenn dieser Prozess ausfällt. Aufwärts: Wer beliefert ihn.',
  'prozess.wirkung.abwaerts': 'Abwärts betroffen',
  'prozess.wirkung.aufwaerts': 'Aufwärts beteiligt',
  'prozess.wirkung.leer': 'Keine Kante erfasst.',
  'prozess.datenobjekte.leer': 'Noch kein Datenobjekt referenziert.',
  'prozess.herkunft.reichweite': 'Aus dem Kundenkreis',
  'prozess.herkunft.reichweiteUmsetzung':
    'Aus dem Kundenkreis, angehoben durch mehrere Umsetzungen',
  'prozess.herkunft.kritikalitaetEigen': 'Aus der eigenen Ausfallfolge',
  'prozess.herkunft.kritikalitaetKette': 'Aus der Prozesskette geerbt',
  'prozess.herkunft.mitbestimmung': 'Aus Datenkategorie und Bewertung',

  'kundenkreis.persoenlich': 'Persönlich',
  'kundenkreis.team': 'Team',
  'kundenkreis.bereich': 'Fachbereich',
  'kundenkreis.unternehmen': 'Unternehmen',
  'kundenkreis.extern': 'Extern',
  'reichweite.persoenlich': 'Persönlich',
  'reichweite.team': 'Team',
  'reichweite.bereich': 'Fachbereich',
  'reichweite.unternehmen': 'Unternehmen',
  'reichweite.extern': 'Extern',

  'kategorie.oeffentlich': 'Öffentlich',
  'kategorie.intern': 'Intern — geschäftlich',
  'kategorie.vertraulich': 'Intern — vertraulich',
  'kategorie.personenbezogen': 'Personenbezogen — allgemein',
  'kategorie.besondere_kategorie': 'Personenbezogen — besonders',

  'ausfallfolge.keine': 'Keine',
  'ausfallfolge.gering': 'Gering',
  'ausfallfolge.spuerbar': 'Spürbar',
  'ausfallfolge.kritisch': 'Kritisch',

  'status.entwurf': 'Entwurf',
  'status.aktiv': 'Aktiv',
  'status.freigabe_ausstehend': 'Freigabe ausstehend',
  'status.stillgelegt': 'Stillgelegt',
  'prozess.freigabeAusstehend':
    'Dieses Prozessobjekt läuft, ist aber für seine jetzige Einstufung nicht freigegeben: die Neubewertung hat es auf Tier 3 gehoben. Ein Gate-1-Vorgang liegt bereits vor. Nach der Freigabe und einer neuen Selbstverpflichtung lässt es sich wieder aktivieren.',

  'bewertung.titel': 'Bewertung',
  'bewertung.untertitel': 'Eine Frage je Schritt. Das Ergebnis erscheint am Ende.',
  'bewertung.starten': 'Bewertung durchführen',
  'bewertung.modus.frage': 'Wie möchten Sie den Baum durchlaufen?',
  'bewertung.modus.schnell': 'Schnell — endet beim ersten Tier-3-Treffer',
  'bewertung.modus.vollstaendig': 'Vollständig — alle sechs Schritte, mit K-Klassen',
  'bewertung.modus.schnell.kurz': 'Schnell',
  'bewertung.modus.vollstaendig.kurz': 'Vollständig',
  'bewertung.modus.schnell.folge':
    'Der Durchlauf endet, sobald eine Dimension Tier 3 erreicht. Sie erfahren das Tier, aber keine Maßnahmenklassen — die setzen das vollständige Profil voraus.',
  'bewertung.modus.vollstaendig.folge':
    'Alle sechs Dimensionen werden durchlaufen. Das Ergebnis nennt Tier, Profil und die ausgelösten Maßnahmenklassen mit ihren Auflagen.',
  'bewertung.modus.hinweis':
    'Die Wahl treffen Sie zu Beginn. Der Zwischenstand wird bewusst nicht angezeigt.',
  'bewertung.ja': 'Ja',
  'bewertung.nein': 'Nein',
  'bewertung.weiter': 'Weiter',
  'bewertung.zurueck': 'Zurück',
  'bewertung.abbrechen': 'Bewertung abbrechen',
  'bewertung.zurueckZurAuswahl': 'Von vorn beginnen',
  'bewertung.schritt': 'Schritt',
  'bewertung.von': 'von',
  'bewertung.fortschritt': 'Fortschritt im Bewertungsbaum',
  'bewertung.frage': 'Frage',
  'bewertung.ergebnis': 'Ergebnis',
  'bewertung.tier': 'Tier',
  'bewertung.profil': 'Profil',
  'bewertung.vorschlag': 'Vorschlag aus Ihren Daten:',
  'bewertung.vorschlag.offen':
    'Zu dieser Frage geben die vorhandenen Daten nichts her — sie ist zu erklären.',
  'bewertung.quelle.datenobjekt': 'Datenobjekt',
  'bewertung.quelle.tool': 'Tool-Objekt',
  'bewertung.quelle.prozess': 'Prozess',
  'bewertung.quelle.kette': 'Prozesskette',
  'bewertung.quelle.kundenkreis': 'Kundenkreis',
  'bewertung.abweichung.hinweis':
    'Ihre Antwort widerspricht dem, was aus den hinterlegten Daten hervorgeht. Das ist zulässig — es wird nur festgehalten, warum.',
  'bewertung.abweichung.feld': 'Begründung der Abweichung',
  'bewertung.abweichung.hilfe':
    'Ein Satz genügt. Er wird mit der Bewertung gespeichert und ist im Nachweis lesbar.',
  'bewertung.abweichungen': 'Begründete Abweichungen',
  'bewertung.abweichungen.hinweis':
    'Vorschlag und Antwort werden beide gespeichert, damit später nachvollziehbar bleibt, was entschieden wurde.',
  'bewertung.kKlassen': 'Ausgelöste Maßnahmenklassen',
  'bewertung.kKlassen.hinweis': 'Was dieser Prozess aufgrund seines Profils zu erfüllen hat.',
  'bewertung.kKlassen.leer': 'Aus diesem Profil folgt keine Maßnahmenklasse.',
  'bewertung.auflagen': 'Auflagen des erreichten Tiers',
  'bewertung.auflagen.hinweis': 'gilt einschließlich der Auflagen der darunterliegenden Tiers.',
  'bewertung.keineKKlassen':
    'Der schnelle Durchlauf endet vorzeitig und liefert deshalb keine K-Klassen.',
  'bewertung.speichern': 'Bewertung speichern',
  'bewertung.gespeichert': 'Die Bewertung wurde gespeichert.',
  'bewertung.abbruch.titel': 'Bewertung verwerfen?',
  'bewertung.abbruch.text': 'Die bisherigen Antworten werden nicht gespeichert.',
  'bewertung.abbruch.zaehler.eine': 'Eine Antwort geht verloren.',
  'bewertung.abbruch.zaehler': 'Antworten gehen verloren.',
  'bewertung.abbruch.weiterbewerten': 'Weiterbewerten',
  'bewertung.abbruch.verwerfen': 'Verwerfen',
  'bewertung.verboten.titel': 'Verbotene KI-Praxis',
  'bewertung.verboten.text':
    'Der Durchlauf hat einen nach EU AI Act verbotenen Tatbestand ergeben. Es wird keine Bewertung gespeichert; stattdessen entsteht ein Governance-Alarm.',
  'bewertung.verboten.weg':
    'Wenden Sie sich an Governance und Recht, bevor der Prozess weiterverfolgt wird.',
  'bewertung.verboten.alarm': 'Alarm auslösen',
  'bewertung.historie': 'Bewertungshistorie',
  'bewertung.bewertetAm': 'Bewertet am',
  'bewertung.massgeblich': 'Maßgeblich',
  'bewertung.historie.leer': 'Für diesen Prozess liegt noch keine Bewertung vor.',
  'bewertung.vollstaendig': 'vollständig',
  'bewertung.unvollstaendig': 'schnell',
  'bewertung.gueltigBis': 'Gültig bis',

  'nav.tools': 'Tool-Objekte',
  'nav.datenobjekte': 'Datenobjekte',

  'asset.tools.titel': 'Tool-Objekte',
  'asset.tools.leer': 'In Ihrem Bereich ist noch kein Tool-Objekt erfasst.',
  'asset.tools.neu': 'Tool-Objekt anlegen',
  'asset.datenobjekte.titel': 'Datenobjekte',
  'asset.datenobjekte.leer': 'In Ihrem Bereich ist noch kein Datenobjekt erfasst.',
  'asset.datenobjekte.neu': 'Datenobjekt anlegen',
  'asset.feld.name': 'Name',
  'asset.feld.beschreibung': 'Beschreibung',
  'asset.feld.technologie': 'Technologie',
  'asset.feld.kategorie': 'Kategorie',
  'asset.feld.herkunft': 'Herkunft',
  'asset.feld.status': 'Status',
  'asset.herkunft.importiert': 'Importiert',
  'asset.herkunft.manuell': 'Manuell',
  'asset.status.importiert_unbestaetigt': 'Importiert, unbestätigt',
  'asset.status.bestaetigt': 'Bestätigt',
  'asset.status.inaktiv': 'Inaktiv',
  'asset.bestaetigen': 'Bestätigen',
  'asset.bestaetigenHinweis':
    'Solange dieses Tool-Objekt unbestätigt ist, kann es nicht mit einem Prozess verknüpft werden — es würde sonst eine Klassifikation erben, bevor jemand geprüft hat, ob es das gemeinte Objekt ist.',
  'asset.importHinweis':
    'Dieser Datensatz stammt aus einem Import. Name und technische Metadaten sind am Ursprungssystem zu ändern; die Governance-Felder sind hier pflegbar.',
  'asset.geerbt.titel': 'Geerbte Klassifikation — Maximum aller Prozesskanten',
  'asset.geerbt.hinweis':
    'Ein Tool mit mehreren Prozesskanten trägt die höchste Einstufung aller Kanten; die schwächste Verknüpfung wäre sonst eine stille Umgehung.',
  'asset.geerbt.kritikalitaet': 'Kritikalität',
  'asset.geerbt.reichweite': 'Reichweite',
  'asset.geerbt.tier': 'Tier',
  'asset.geerbt.kKlassen': 'K-Klassen',
  'asset.prozesse.titel': 'Verknüpfte Prozessobjekte',
  'asset.prozesse.leer': 'Dieses Tool-Objekt hängt an keinem Prozess.',
  'asset.prozesse.verknuepfen': 'Mit Prozess verknüpfen',
  'asset.prozesse.loesen': 'Lösen',
  'asset.tools.amProzess': 'Verknüpfte Tool-Objekte',
  'asset.tools.amProzessLeer': 'An diesem Prozess hängt noch kein Tool-Objekt.',
  'asset.speichern': 'Speichern',
  'asset.kategorie.keine': 'Ohne Kategorie',
  'asset.feld.fachbereich': 'Fachbereich',
  'asset.feld.quellsystem': 'Quellsystem',
  'asset.quellsystem.leer': 'Kein Quellsystem angegeben',
  'asset.quellsystem.hilfe': 'Das System, in dem diese Daten entstehen — etwa „SAP HCM".',
  'asset.reifegrad1': 'Reifegrad 1 — Name, Kategorie, Fachbereich, Quellsystem',
  'asset.feld.gebenderProzess': 'Gebender Prozess',
  'asset.gebenderProzess.hilfe':
    'Der Prozess, der diese Daten erzeugt. Sein Fachbereich wird zur datenhaltenden Stelle — er wird nicht gewählt, er ergibt sich.',
  'asset.gebenderProzess.keiner': 'Kein Prozess erzeugt diese Quelle — sie wird nur genutzt.',
  'asset.fachbereich.hilfe':
    'Die datenhaltende Stelle. Sie bestimmt, wer die Quelle klassifiziert; wechseln kann sie nur die Governance.',
  'asset.anlegen.weg':
    'Eine Quelle bekommt ihren Fachbereich auf einem von zwei Wegen: vom gebenden Prozess oder von Ihnen als Datenobjekt-Owner.',
  'asset.anlegen.keinWeg':
    'Zum Anlegen einer Quelle braucht es einen Prozess, den Sie tragen, oder die Rolle Datenobjekt-Owner in einem Fachbereich.',
  'asset.reifegrad1.hinweis':
    'Mehr verlangt die Compliance-Funktion nicht. Schema und Kontrakt sind ein Upgrade, keine Eintrittshürde.',
  'asset.datenobjekte.hinweis':
    'Nicht Tools werden klassifiziert, sondern Quellen — Tools erben. Das macht die Arbeit endlich.',
  'asset.datenobjekte.ohneKategorie': 'Datenobjekte ohne Kategorie im Cockpit ansehen',
  'asset.kategorie.hilfe': 'Für die Frage „ist das personenbezogen" genügt die Kategorie.',
  'asset.kategorie.wirkungHinweis':
    'Vor dem Übernehmen zeigt die Anwendung, wen die Änderung trifft.',
  'kategorie.anker.oeffentlich': 'frei zugänglich',
  'kategorie.anker.intern': 'kein Personenbezug',
  'kategorie.anker.vertraulich': 'Geschäftsgeheimnis, Finanzen',
  'kategorie.anker.personenbezogen': 'Kontakt, Organisation',
  'kategorie.anker.besondere_kategorie': 'Entgelt, Gesundheit, Leistungsbewertung',
  'asset.verwendung.prozesse': 'Referenziert von Prozessobjekten',
  'asset.verwendung.hinweis':
    'Eine Änderung hier wirkt auf alle referenzierenden Objekte — sie muss nirgends nachgetragen werden.',
  'asset.verwendung.tools': 'Genutzt von Tool-Objekten',
  'asset.verwendung.keineProzesse': 'Kein Prozessobjekt referenziert dieses Datenobjekt.',
  'asset.verwendung.keineTools': 'Kein Tool-Objekt greift auf dieses Datenobjekt zu.',
  'asset.verwendung.alsInput': 'Input',
  'asset.verwendung.alsOutput': 'Output',
  'asset.verwendung.ueberProzess': 'Über den Prozess verbunden',
  'zugriffsart.lesen': 'Liest',
  'zugriffsart.schreiben': 'Schreibt',
  'zugriffsart.lesen_schreiben': 'Liest und schreibt',
  'asset.wirkung.titel': 'Wirkung der Umklassifizierung',
  'asset.wirkung.hinweis': 'Was diese Änderung berührt — vor der Entscheidung, nicht danach.',
  'asset.wirkung.von': 'Bisher',
  'asset.wirkung.nach': 'Künftig',
  'asset.wirkung.prozesse': 'Betroffene Prozessobjekte',
  'asset.wirkung.tools': 'Betroffene Tool-Objekte',
  'asset.wirkung.mitbestimmung': 'Neu mitbestimmungsrelevant',
  'asset.wirkung.mitbestimmungHinweis':
    'Prozessobjekte, die das Flag durch diese Änderung bekommen',
  'asset.wirkung.warnung':
    'Diese Änderung macht Prozesse mitbestimmungsrelevant. Die Bewertung ist dort zu erneuern.',
  'asset.wirkung.uebernehmen': 'Kategorie übernehmen',

  'tool.hinweis': 'Was ein Tool tut, sagt die Telemetrie. Was es bewirkt, sagt sein Owner.',
  'tool.feld.owner': 'Technischer Owner',
  'tool.feld.stellvertretung': 'Stellvertretung',
  'tool.feld.organisationseinheit': 'Organisationseinheit',
  'tool.einheit.hilfe':
    'Der Bereich, dem dieses Werkzeug gehört. Er entscheidet, wer es sehen und ändern darf — und lässt sich später nur von der Governance wechseln.',
  'tool.feld.lauftyp': 'Lauftyp',
  'tool.owner.hilfe': 'Adressat für Selbstverpflichtung und Lenkungsvorgänge.',
  'tool.lauftyp.hilfe':
    'Steuert technische Entscheidungen. Keine eigene Tier-Achse — nur ein Korrekturfaktor bei Grenzfällen.',
  'tool.lauftyp.interaktiv': 'Interaktiv — ein Mensch stößt es an',
  'tool.lauftyp.getriggert': 'Getriggert — ein Ereignis stößt es an',
  'tool.lauftyp.geplant': 'Geplant — unbeaufsichtigt nach Zeitplan',
  'tool.lauftyp.keiner': 'Nicht angegeben',
  'tool.technologie.keine': 'Nicht angegeben',
  'tool.stammdaten': 'Stammdaten',
  'tool.stammdaten.hinweis': 'Deklariert — das, was Telemetrie nicht kennt.',

  'tool.attest.titel': 'Attestierungen',
  'tool.attest.hinweis':
    'Drei Erklärungen, die Telemetrie nicht liefern kann. Sie werden mit Namen abgegeben, nicht als Formularfeld.',
  'tool.attest.frage1': 'Fließt das Ergebnis in eine Entscheidung über einzelne Personen?',
  'tool.attest.frage1.zusatz':
    'Auch mittelbar — etwa als Vorschlag, dem in der Regel gefolgt wird.',
  'tool.attest.frage2': 'Steht zwischen Output und Wirkung ein Mensch?',
  'tool.attest.frage2.zusatz':
    'Prüft jemand das Ergebnis, bevor es wirkt? Ohne Mensch dazwischen ist das Tool verändernd — auch bei reinem Lesen.',
  'tool.attest.frage3':
    'Werden Datenkategorien verarbeitet, die nicht aus klassifizierten Quellen stammen?',
  'tool.attest.frage3.zusatz':
    'Uploads, manuelle Eingaben, Zwischenablagen. Die wichtigste der drei Fragen — sie fängt die Lücke, die das Datenobjekt-Modell nicht schließen kann.',
  'tool.attest.abgeben': 'Erklärung abgeben',
  'tool.attest.erneuern': 'Erklärung erneuern',
  'tool.attest.offen': 'Noch nicht erklärt',
  'tool.attest.offenHinweis':
    'Ohne die drei Erklärungen ist keine Verknüpfung mit einem Prozessobjekt möglich.',
  'tool.attest.erklaertVon': 'Erklärt von',
  'tool.attest.erklaertAm': 'Erklärt am',
  'tool.attest.unbekannt': 'Unbekannt',

  'tool.wirkungsart': 'Wirkungsart',
  'tool.wirkungsart.veraendernd': 'Verändernd',
  'tool.wirkungsart.gestaltend': 'Gestaltend',
  'tool.wirkungsart.offen': 'Noch offen',
  'tool.wirkungsart.grund.schreibzugriff': 'Schreibt auf ein Datenobjekt — immer prüfpflichtig.',
  'tool.wirkungsart.grund.kein_mensch':
    'Kein Mensch zwischen Output und Wirkung — verändernd auch bei reinem Lesen.',
  'tool.wirkungsart.grund.nur_lesend': 'Nur lesende Zugriffe, und ein Mensch prüft das Ergebnis.',
  'tool.wirkungsart.grund.offen': 'Erst nach der zweiten Attestierung bestimmbar.',

  'tool.daten.titel': 'Genutzte Datenobjekte',
  'tool.daten.hinweis':
    'Nicht „das Tool hat Zugriff", sondern „das Tool liest dieses Objekt im Rahmen dieses Prozesses".',
  'tool.daten.leer': 'Dieses Tool-Objekt greift auf kein Datenobjekt zu.',
  'tool.daten.hinzufuegen': 'Datenobjekt verknüpfen',
  'tool.daten.zugriffsart': 'Zugriffsart',
  'tool.daten.zugriffsartHilfe':
    'Gilt für die nächste Verknüpfung. Schreibzugriff macht das Tool verändernd.',
  'tool.daten.entfernen': 'Verknüpfung entfernen',
  'tool.daten.ausserhalb': 'Außerhalb des Prozessrahmens',
  'tool.daten.ausserhalbHinweis':
    'Dieses Datenobjekt ist an keinem verknüpften Prozessobjekt deklariert. Zweckbindung nicht belegt.',
  'tool.daten.nurKategorie': 'Nicht deklariert',
  'tool.daten.nurKategorieHinweis':
    'Die Kategorie kommt im Prozessrahmen vor, dieses Objekt selbst aber nicht.',
  'tool.daten.ohneProzess':
    'Ohne Prozessverknüpfung gibt es keinen Rahmen, gegen den sich die Zweckbindung prüfen ließe.',
  'tool.daten.abweichungen':
    'Zweckbindung nicht belegt: {anzahl} genutzte Datenobjekte liegen außerhalb des Prozessrahmens.',

  'tool.prozesse.hinweis': 'Der Zweck, in dessen Rahmen dieses Tool arbeitet.',
  'tool.prozesse.geerbtVon': 'Beiträge der einzelnen Kanten',
  'tool.prozesse.massgeblich': 'Bestimmt das Maximum',
  'tool.tools.suche': 'Suchen',
  'tool.tools.platzhalter': 'Name oder Technologie …',
  'tool.attestierungFehlt': 'Attestierung fehlt',

  'nav.gates': 'Gates',

  'sv.titel': 'Selbstverpflichtung',
  'sv.untertitel.prozess':
    'Sechs konkrete Aussagen nach A.10.2 — jede einzeln zu bestätigen, jede im Nachhinein prüfbar.',
  'sv.untertitel.tool': 'Sechs konkrete Aussagen nach A.10.3 zum Betrieb dieses Tool-Objekts.',
  'sv.stand': 'Stand der Erklärung',
  'sv.aussagen': 'Aussagen',
  'sv.kurzform': 'Kurzform: bei Tier 1 wird nur der Kern verlangt (A.10.5).',
  'sv.vollform': 'Ab Tier 2 sind alle Aussagen zu bestätigen.',
  'sv.nochkeine': 'Noch keine Erklärung abgegeben.',
  'sv.abgegebenAm': 'Abgegeben am',
  'sv.gebundenAn': 'Gebunden an',
  'sv.gedeckt': 'Gültig',
  'sv.bestaetigen': 'Für ein weiteres Jahr bestätigen',
  'sv.kommentarZu': 'Kommentar hinzufügen',
  'sv.offen': 'Noch offen:',
  'sv.grund.keine.kurz': 'Fehlt',
  'sv.grund.unvollstaendig.kurz': 'Unvollständig',
  'sv.grund.alter_katalog.kurz': 'Alter Katalog',
  'sv.grund.profil_veraltet.kurz': 'Verfallen',
  'sv.grund.tier_gestiegen.kurz': 'Verfallen',
  'sv.grund.frist_abgelaufen.kurz': 'Abgelaufen',
  'sv.abgeben': 'Selbstverpflichtung abgeben',
  'sv.hinweis':
    'Jede Aussage ist einzeln zu bestätigen. Erst wenn alle bestätigt sind, gilt die Selbstverpflichtung als vollständig.',
  'sv.kommentar': 'Kommentar',
  'sv.speichern': 'Abgeben',
  'sv.status': 'Stand der Selbstverpflichtung',
  'sv.vollstaendig': 'Vollständig abgegeben',
  'sv.unvollstaendig': 'Unvollständig',
  'sv.keine': 'Für diesen Prozess liegt noch keine Selbstverpflichtung vor.',
  'sv.gueltigBis': 'Gültig bis',

  'gate.titel': 'Gate-Vorgänge',
  'gate.hinweis':
    'Gate 1 ist die Erstfreigabe ab Tier 3. Gate 2 verlangt einen der fünf abschließend genannten Auslöser aus A.11.',
  'gate.begruendungHilfe': 'Was hat sich geändert, und warum ist die Freigabe nötig?',
  'gate.ausloeser.neue_datenkategorie': 'Neue Datenkategorie',
  'gate.ausloeser.reichweitenerweiterung': 'Reichweitenerweiterung',
  'gate.ausloeser.neues_externes_ziel': 'Neues externes Ziel',
  'gate.ausloeser.ki_komponente_ergaenzt': 'KI-Komponente ergänzt',
  'gate.ausloeser.kritikalitaet_gestiegen': 'Kritikalität gestiegen',
  'gate.ablehnungBegruendung': 'Eine Ablehnung ist zu begründen.',
  'gate.leer': 'Für diesen Prozess gibt es noch keinen Gate-Vorgang.',
  'gate.einreichen': 'Gate einreichen',
  'gate.typ': 'Gate',
  'gate.typ.1': 'Gate 1 — Tier-3-Erstfreigabe',
  'gate.typ.2': 'Gate 2 — Rahmenverletzung',
  'gate.ausloeser': 'Auslöser',
  'gate.ausloeserPflicht':
    'Gate 2 verlangt genau einen der fünf im Leitdokument abschließend aufgezählten Auslöser.',
  'gate.begruendung': 'Begründung',
  'gate.status': 'Status',
  'gate.status.eingereicht': 'Eingereicht',
  'gate.status.in_pruefung': 'In Prüfung',
  'gate.status.freigegeben': 'Freigegeben',
  'gate.status.abgelehnt': 'Abgelehnt',
  'gate.entscheiden': 'Entscheiden',
  'gate.freigeben': 'Freigeben',
  'gate.ablehnen': 'Ablehnen',
  'gate.kommentar': 'Entscheidungskommentar',
  'gate.arbeitsvorrat': 'Offene Gate-Vorgänge',
  'gate.arbeitsvorratLeer': 'Es ist kein Gate-Vorgang offen.',
  'gate.arbeitsvorratHinweis': 'Was auf eine Entscheidung der Governance wartet.',
  'gate.prozess': 'Prozessobjekt',

  'nav.lenkung': 'Lenkung',

  'compliance.titel': 'Compliance-Zustand',
  'compliance.hinweis':
    'Jede Feststellung erzeugt einen neuen Eintrag; der aktuelle Zustand ist der oberste. Nichts wird überschrieben.',
  'compliance.leer': 'Für dieses Tool-Objekt ist noch kein Zustand erfasst.',
  'compliance.farbe': 'Zustand',
  'compliance.farbe.gruen': 'Grün',
  'compliance.farbe.gelb': 'Gelb',
  'compliance.farbe.rot': 'Rot — Rahmenüberschreitung',
  'compliance.begruendung': 'Begründung',
  'compliance.abweichung': 'Art der Abweichung',
  'compliance.melden': 'Zustand melden',
  'compliance.festgestelltAm': 'Festgestellt am',
  'compliance.rotHinweis':
    'Eine rote Meldung eröffnet automatisch einen Lenkungsvorgang in Eskalationsstufe 1 mit der tier-abhängigen Frist.',

  'lenkung.titel': 'Lenkungsvorgänge',
  'lenkung.leer': 'Es ist kein Lenkungsvorgang offen.',
  'lenkung.tool': 'Tool-Objekt',
  'lenkung.zumTool': 'Zum Tool-Objekt',
  'lenkung.stufe': 'Eskalationsstufe',
  'lenkung.stufeKurz': 'Stufe',
  'lenkung.frist': 'Frist',
  'lenkung.status': 'Status',
  'lenkung.status.offen': 'Offen',
  'lenkung.status.aufgeloest': 'Aufgelöst',
  'lenkung.status.abgebrochen': 'Abgebrochen',
  'lenkung.aufloesen': 'Auflösen',
  'lenkung.art': 'Auflösungsart',
  'lenkung.art.anpassen': 'Anpassen',
  'lenkung.art.rahmen_erweitern': 'Rahmen erweitern',
  'lenkung.art.stilllegen': 'Stilllegen',
  'lenkung.bewertung': 'Neue Bewertung',
  'lenkung.bewertungPflicht':
    'Der Vorgang schließt erst, wenn die neue Bewertung abgeschlossen ist.',
  'lenkung.kommentar': 'Kommentar',
  'lenkung.stufe3':
    'Stufe 3 kennzeichnet den Vorgang für eine technische Maßnahme. Der Zugriffsentzug erfolgt außerhalb dieser Anwendung.',

  'lenkung.hinweis':
    'Jede Rahmenüberschreitung bekommt eine Frist in Arbeitstagen und genau drei Wege hinaus (A.13.6).',
  'lenkung.leerHinweis': 'Alle Tool-Objekte in Ihrem Bereich bewegen sich im Rahmen.',
  'lenkung.schicht2':
    'Verstoß gegen ein organisationsweites Verbot: {verbot}. Solche Fälle beginnen ohne erste Stufe — es gibt nichts zu klären, nur abzustellen.',
  'lenkung.abgelaufen': 'Abgelaufen',
  'lenkung.abgelaufenSeit': 'seit {tage} Arbeitstagen',
  'lenkung.abgelaufenHeute': 'seit heute',
  'lenkung.arbeitstagRest': 'Arbeitstag verbleibt',
  'lenkung.arbeitstageRest': 'Arbeitstage verbleiben',
  'lenkung.art.anpassen.hinweis':
    'Das Tool wird in den Rahmen zurückgeführt. Der Zustand wird danach wieder grün.',
  'lenkung.art.rahmen_erweitern.hinweis':
    'Der Rahmen wird erweitert. Das verlangt eine neue Bewertung des betroffenen Prozessobjekts — wählen Sie sie unten aus.',
  'lenkung.art.stilllegen.hinweis':
    'Das Tool geht außer Betrieb. Das ist keine Rückkehr in den Rahmen: der Zustand bleibt rot.',
  'lenkung.bewertungFehlt':
    'Für dieses Tool-Objekt gibt es seit Eröffnung des Vorgangs keine neue Bewertung. Bewerten Sie das betroffene Prozessobjekt zuerst neu.',

  'rahmen.titel': 'Erlaubnisrahmen',
  'rahmen.hinweis':
    'Was dieses Tool darf, abgeleitet aus den Prozessobjekten und den Attestierungen — daneben, was tatsächlich erfasst ist (A.13.2).',
  'rahmen.eingehalten': 'Im Rahmen',
  'rahmen.abweichungen': '{anzahl} Abweichungen',
  'rahmen.abweichungen.eine': 'Eine Abweichung',
  'rahmen.erlaubt': 'Erlaubt',
  'rahmen.gemessen': 'Gemessen',
  'rahmen.ohneMessung': 'Nicht gemessen — abgeleitet',
  'rahmen.schicht2.erkannt': 'Aus den erfassten Daten erkannter Verstoß gegen Schicht 2:',
  'rahmen.element.datenobjekte': 'Datenobjekte',
  'rahmen.element.datenkategorie': 'Obergrenze der Datenkategorie',
  'rahmen.element.reichweite': 'Reichweite',
  'rahmen.element.externe_ziele': 'Externe Ziele',
  'rahmen.element.zugriffsart': 'Zugriffsart',
  'rahmen.element.ausfuehrungsart': 'Ausführungsart',
  'rahmen.element.ausfuehrungsidentitaet': 'Ausführungsidentität',
  'rahmen.abweichung.datenobjekte': 'Außerhalb des Rahmens genutzt: {werte}',
  'rahmen.abweichung.datenkategorie':
    'Das Tool verarbeitet eine höhere Kategorie, als der Rahmen deckt: {werte}',
  'rahmen.abweichung.reichweite': 'Außerhalb der geerbten Reichweite: {werte}',
  'rahmen.abweichung.externe_ziele': 'Nicht erklärtes Ziel: {werte}',
  'rahmen.abweichung.zugriffsart':
    'Schreibzugriff auf ein Datenobjekt, das kein Prozessergebnis ist: {werte}',
  'rahmen.abweichung.ausfuehrungsart': 'Diese Ausführungsart deckt die Attestierung nicht: {werte}',
  'rahmen.abweichung.ausfuehrungsidentitaet':
    'Diese Identität passt nicht zur Ausführungsart: {werte}',
  'rahmen.identitaet.persoenlich': 'Persönliche Identität',
  'rahmen.identitaet.benannter_dienst': 'Benannte Dienstidentität',
  'rahmen.identitaet.geteiltes_konto': 'Geteiltes Konto',

  'schicht2.identitaet_umgangen': 'Ausführung unter umgangener Unternehmensidentität',
  'schicht2.statische_zugangsdaten': 'Dauerhaft gültige Zugangsdaten im Tool hinterlegt',
  'schicht2.undeklarierte_quellen': 'Verarbeitung von Daten aus nicht deklarierten Quellen',
  'schicht2.entscheidung_ohne_mensch':
    'Automatisierte Entscheidung über einzelne Personen ohne Menschen dazwischen',
  'schicht2.daten_ins_offene_netz':
    'Übermittlung von Unternehmensdaten außerhalb der freigegebenen Infrastruktur',
  'schicht2.protokollierung_umgangen': 'Betrieb ohne oder mit abgeschalteter Protokollierung',

  'compliance.schicht2': 'Verstoß gegen Schicht 2',
  'compliance.schicht2.keiner': 'Keiner — Rahmenüberschreitung nach Schicht 1',
  'compliance.schicht2Hilfe':
    'Genau eines der sechs organisationsweiten Verbote aus A.13.2. Ein siebter, freier Grund ist nicht wählbar.',
  'compliance.schicht2Folge':
    'Dieser Vorgang beginnt unmittelbar in Eskalationsstufe 2: Die Führungskraft wird sofort informiert, und keine Bewertung schaltet den Fall frei.',

  'konfiguration.titel': 'Einstellungen',
  'konfiguration.hinweis':
    'Fristen, Schwellen und Vorlaufzeiten der Governance — änderbar im Betrieb, ohne Auslieferung.',
  'konfiguration.nurLesen':
    'Ansicht ohne Änderungsrecht: Governance-Einstellungen ändert die Governance-Rolle.',
  'konfiguration.nichtRueckwirkend':
    'Eine Änderung wirkt auf neue Vorgänge, nicht rückwirkend. Laufende Fristen bleiben, wie sie bei ihrer Eröffnung gerechnet wurden.',
  'konfiguration.sichern': 'Sichern',
  'konfiguration.gesichert': 'Gesichert',
  'konfiguration.gruppe.lenkung': 'Lenkungsfristen (A.13.5)',
  'konfiguration.gruppe.fristen': 'Gültigkeit und Erinnerung',
  'konfiguration.gruppe.schwellen': 'Schwellen',
  'konfiguration.lenkung_frist_tage_tier1': 'Stufe 1 bei Tier 1',
  'konfiguration.lenkung_frist_tage_tier2': 'Stufe 1 bei Tier 2',
  'konfiguration.lenkung_frist_tage_tier3': 'Stufe 1 bei Tier 3',
  'konfiguration.lenkung_nachfrist_tage_tier1': 'Nachfrist in Stufe 2 bei Tier 1',
  'konfiguration.lenkung_nachfrist_tage_tier2': 'Nachfrist in Stufe 2 bei Tier 2',
  'konfiguration.lenkung_nachfrist_tage_tier3': 'Nachfrist in Stufe 2 bei Tier 3',
  'konfiguration.selbstverpflichtung_gueltigkeit_tage': 'Gültigkeit einer Selbstverpflichtung',
  'konfiguration.selbstverpflichtung_erinnerung_vorlauf_tage': 'Vorlauf der Erinnerung',
  'konfiguration.bewertung_gueltigkeit_tage_tier3': 'Gültigkeit einer Bewertung ab Tier 3',
  'konfiguration.asset_inaktiv_tage': 'Ab wann ein Tool als inaktiv gilt',

  'prozess.ziele.titel': 'Erlaubte externe Ziele',
  'prozess.ziele.hinweis':
    'Der erklärte Rahmen nach A.13.2: wohin dieser Prozess übermitteln darf. Was hier nicht steht, ist nicht erlaubt.',
  'prozess.ziele.leer': 'Für diesen Prozess ist kein externes Ziel erklärt.',
  'prozess.ziele.neu': 'Ziel ergänzen',
  'prozess.ziele.hinzufuegen': 'Hinzufügen',
  'prozess.ziele.entfernen': 'Entfernen',
  'prozess.ziele.gateHinweis':
    'An einem aktiven Prozessobjekt löst ein neues Ziel Gate 2 aus (A.11) — der Vorgang entsteht beim Speichern von selbst.',

  'tool.feld.identitaet': 'Ausführungsidentität',
  'tool.identitaet.keine': 'Nicht erklärt',
  'tool.identitaet.hilfe':
    'Unter welcher Identität das Tool läuft. Ein geteiltes Konto ist organisationsweit verboten (A.13.2 Schicht 2).',
  'tool.feld.statischeZugangsdaten': 'Dauerhaft gültige Zugangsdaten hinterlegt',
  'tool.statischeZugangsdaten.hilfe':
    'Zugangsdaten, die im Tool stehen statt verwaltet zu werden. Ein Ja ist ein Verstoß gegen Schicht 2.',
  'tool.ziele.titel': 'Externe Ziele',
  'tool.ziele.hinweis':
    'Wohin dieses Tool tatsächlich übermittelt. Der Vergleich mit dem erklärten Rahmen steht weiter unten.',
  'tool.ziele.leer': 'Für dieses Tool-Objekt ist kein externes Ziel erfasst.',
  'tool.ziele.neu': 'Ziel erfassen',

  'nav.cockpit': 'Cockpit',

  'nav.klassen': 'Anforderungsklassen',
  'nav.konzept': 'Konzept',
  'nav.verwaltung': 'Verwaltung',
  'nav.nachweis': 'Nachweis',

  'konzept.titel': 'Konzept und Vorgehen',
  'konzept.hinweis':
    'Wie wir mit Citizen Development und Custom Code umgehen — die Begriffe, die Regeln und wie sie ineinandergreifen.',
  'konzept.ansicht': 'Ansicht',
  'konzept.ansicht.vortrag': 'Vortrag',
  'konzept.ansicht.dokument': 'Dokument',
  'konzept.zurueck': 'Zurück',
  'konzept.weiter': 'Weiter',
  'konzept.vollbild': 'Vollbild',
  'konzept.fortschritt': 'Fortschritt im Vortrag',
  'konzept.nurDeutsch':
    'Der Vortrag liegt bislang nur auf Deutsch vor. Die Anwendung selbst ist übersetzt.',

  // Was die Oberfläche sagt, wo eine Rolle etwas nicht darf. Eine fehlende
  // Schaltfläche erklärt sich nicht von selbst — und ein Formular, dessen
  // Speichern in einem 403 endet, ist eine vergeudete halbe Stunde.
  'rechte.prozess.nurLesen':
    'Sie sehen dieses Prozessobjekt, dürfen es aber nicht ändern. Schreiben darf der Prozess-Owner des zuständigen Bereichs oder die Governance-Rolle.',
  'rechte.prozess.nurUmsetzung':
    'Als Prozess-Umsetzer pflegen Sie die lokale Abweichung Ihrer Landesorganisation — und nur diese. Alles Übrige bleibt beim Prozessgeber.',
  'rechte.tool.nurLesen':
    'Sie sehen dieses Tool-Objekt, dürfen es aber nicht ändern. Schreiben darf sein technischer Owner, der Prozess-Owner einer verknüpften Kante oder die Governance-Rolle.',
  'rechte.datenobjekt.nurLesen':
    'Sie sehen dieses Datenobjekt, dürfen es aber nicht ändern. Stammdaten pflegt der Datenobjekt-Owner des Fachbereichs oder der Owner des gebenden Prozesses; die Kategorie setzt nur der Datenobjekt-Owner.',
  'rechte.datenobjekt.nurStammdaten':
    'Als Owner des gebenden Prozesses pflegen Sie Name, Beschreibung und Quellsystem. Die Kategorie setzt der Datenobjekt-Owner des Fachbereichs — sie wirkt in jeden Prozess, der diese Quelle nutzt.',
  'rechte.datenobjekt.ankerFest':
    'Der Fachbereich wandert nicht — ändern kann ihn nur die Governance.',
  'rechte.lenkung.nurLesen': 'Diesen Vorgang schließt der Betroffene oder die Governance-Rolle.',
  'rechte.liste.leer':
    'In Ihrem Geltungsbereich liegt nichts. Eine Rolle wirkt nie allein, sondern immer zusammen mit einem Bereich — beides vergibt der App-Administrator.',

  // Was die Oberfläche sagt, wenn eine Rolle etwas nicht darf. Eine fehlende
  // Schaltfläche erklärt sich nicht von selbst.

  'rolle.prozess_owner': 'Prozess-Owner',
  'rolle.prozess_umsetzer': 'Prozess-Umsetzer',
  'rolle.technischer_owner': 'Technischer Owner',
  'rolle.datenobjekt_owner': 'Datenobjekt-Owner',
  'rolle.governance': 'Governance',
  'rolle.plattform': 'Plattform',
  'rolle.auditor': 'Auditor',
  'rolle.app_administrator': 'App-Administrator',

  'verwaltung.titel': 'Verwaltung',
  'verwaltung.hinweis':
    'Nutzer und Rollen. Wer hier zuweist, vergibt jeden anderen Zugriff — sparsam sein.',
  'verwaltung.nurLesen':
    'Ansicht ohne Änderungsrecht: Nutzer und Rollen verwaltet der App-Administrator.',
  'verwaltung.nutzer': 'Nutzer',
  'verwaltung.nutzerHinweis': 'Name, Aktivstatus, Führungskraft und zugewiesene Rollen.',
  'verwaltung.suche': 'Nutzer suchen',
  'verwaltung.suchePlatzhalter': 'Name oder E-Mail',
  'verwaltung.keineTreffer': 'Kein Nutzer passt zu dieser Suche.',
  'verwaltung.aktiv': 'Aktiv',
  'verwaltung.inaktiv': 'Inaktiv',
  'verwaltung.aktivstatus': 'Aktiv',
  'verwaltung.fuehrungskraft': 'Führungskraft',
  'verwaltung.ohneFuehrungskraft': 'nicht hinterlegt',
  'verwaltung.fuehrungskraftHilfe':
    'Ab Eskalationsstufe 2 geht die Meldung eines Lenkungsvorgangs an sie (A.13.5).',
  'verwaltung.bestehende': 'Zugewiesene Rollen',
  'verwaltung.keineRolle': 'Diesem Nutzer ist noch keine Rolle zugewiesen.',
  'verwaltung.rolle': 'Rolle',
  'verwaltung.scopeTyp': 'Geltungsbereich',
  'verwaltung.scope.global': 'Unternehmensweit',
  'verwaltung.scope.fachbereich': 'Fachbereich',
  'verwaltung.scope.organisationseinheit': 'Organisationseinheit',
  'verwaltung.zuweisen': 'Rolle zuweisen',
  'verwaltung.entziehen': 'Entziehen',
  'verwaltung.wirkung':
    'Diese Zuweisung gibt zusätzlich Zugriff auf {prozesse} Prozessobjekte und {tools} Tool-Objekte ({scope}).',
  'verwaltung.wirkungBeispiele': 'Zum Beispiel',

  'nachweis.titel': 'Nachweis',
  'nachweis.hinweis':
    'Jede schreibende Aktion mit Zeitpunkt, Person und dem, was sich geändert hat (A.13.7).',
  'nachweis.art': 'Objektart',
  'nachweis.alleArten': 'Alle Objektarten',
  'nachweis.filterHinweis': 'Der Filter steht in der Adresse und ist damit teilbar.',
  'nachweis.eintraege': 'Änderungen',
  'nachweis.leer': 'Zu diesem Ausschnitt gibt es keinen Eintrag.',
  'nachweis.leerHinweis': 'Sobald jemand etwas ändert, steht es hier.',
  'nachweis.aktion.erstellt': 'Erstellt',
  'nachweis.aktion.geaendert': 'Geändert',
  'nachweis.aktion.geloescht': 'Gelöscht',
  'nachweis.art.prozessobjekte': 'Prozessobjekt',
  'nachweis.art.bewertungen': 'Bewertung',
  'nachweis.art.tool_objekte': 'Tool-Objekt',
  'nachweis.art.datenobjekte': 'Datenobjekt',
  'nachweis.art.selbstverpflichtungen': 'Selbstverpflichtung',
  'nachweis.art.gate_vorgaenge': 'Gate-Vorgang',
  'nachweis.art.lenkungsvorgaenge': 'Lenkungsvorgang',
  'nachweis.art.compliance_zustaende': 'Compliance-Zustand',
  'nachweis.art.rollenzuweisungen': 'Rollenzuweisung',
  'nachweis.art.konfiguration': 'Einstellung',

  'klassen.titel': 'Anforderungsklassen',
  'klassen.hinweis':
    'Was eine Bewertung auslöst — und ob die eingesetzte Technologie es tragen kann (A.9).',
  'klassen.ansicht': 'Ansicht',
  'klassen.ansicht.klassen': 'Klassen',
  'klassen.ansicht.matrix': 'Matrix',
  'klassen.katalog': 'K1 bis K10',
  'klassen.katalogHinweis':
    'Jede Klasse mit Name, Zweck und der Bedingung, unter der eine Bewertung sie auslöst.',
  'klassen.ausloeser': 'Ausgelöst',
  'klassen.matrix': 'Technologiematrix',
  'klassen.matrixHinweis':
    'Welche Technologie welche Klasse tragen kann. Ein Ausschluss ist keine Warnung, sondern ein Kriterium; ein kompensierbarer Fall verlangt eine dokumentierte Maßnahme (A.9.3).',
  'klassen.nurLesen': 'Ansicht ohne Änderungsrecht: die Matrix pflegt die Governance-Rolle.',
  'klassen.spalte.klasse': 'Anforderungsklasse',
  'klassen.bewertung.erfuellt': 'Erfüllt',
  'klassen.bewertung.kompensierbar': 'Kompensierbar',
  'klassen.bewertung.nicht_erfuellbar': 'Nicht erfüllbar',
  'klassen.feld.hinweis':
    'Dieses Feld entscheidet, ob ein Prozess mit dieser Technologie betrieben werden darf. Die Änderung wirkt sofort in allen Befunden.',
  'klassen.feld.bewertung': 'Bewertung',
  'klassen.feld.begruendung': 'Begründung',
  'klassen.feld.begruendungHilfe':
    'Pflicht — eine Farbe ohne Satz ist keine Entscheidungsgrundlage.',
  'klassen.feld.sichern': 'Feld sichern',

  'klassen.befund.titel': 'Anforderungsklassen und Technologie',
  'klassen.befund.hinweis':
    'Die Klassen, die dieses Tool über seine Prozesse erbt, gegen das, was seine Technologie tragen kann.',
  'klassen.befund.leer':
    'Dieses Tool-Objekt erbt noch keine Klassen — dafür braucht es eine Prozesskante mit Bewertung.',
  'klassen.befund.getragen': 'Alle getragen',
  'klassen.befund.offen': '{anzahl} offen',
  'klassen.befund.offen.eine': 'Eine offen',
  'klassen.befund.ausschluss': 'Ausschluss',
  'klassen.art.erfuellt': 'Erfüllt',
  'klassen.art.kompensiert': 'Kompensiert',
  'klassen.art.kompensation_fehlt': 'Maßnahme fehlt',
  'klassen.art.ausschluss': 'Ausschluss',
  'klassen.art.ungeprueft': 'Ungeprüft',
  'klassen.schritt.erfuellt': 'Nichts zu tun — die Technologie trägt diese Klasse.',
  'klassen.schritt.kompensiert': 'Erledigt: die kompensierende Maßnahme ist dokumentiert.',
  'klassen.schritt.kompensation_fehlt':
    'Zu tun: die kompensierende Maßnahme beschreiben, sonst bleibt der Befund offen.',
  'klassen.schritt.ausschluss':
    'Zu entscheiden: diese Technologie kann die Klasse nicht tragen. Entweder wechselt das Tool die Technologie, oder der Prozess wird ohne es betrieben.',
  'klassen.schritt.ungeprueft':
    'Zu tun: am Tool die Technologie hinterlegen — ohne sie gibt es nichts abzugleichen.',
  'klassen.massnahme': 'Maßnahme',
  'klassen.kompensieren': 'Maßnahme erfassen',
  'klassen.kompensationAendern': 'Maßnahme ändern',
  'klassen.kompensation.hinweis':
    'Die Technologie trägt diese Klasse nicht von allein. Halten Sie fest, was stattdessen geschieht.',
  'klassen.kompensation.feld': 'Kompensierende Maßnahme',
  'klassen.kompensation.feldHilfe':
    'Konkret genug, dass eine Prüfung sie nachvollziehen kann — „wird beachtet" ist keine Maßnahme.',
  'klassen.kompensation.sichern': 'Maßnahme sichern',
  'klassen.prozess.titel': 'Technologie und Anforderungsklassen',
  'klassen.prozess.hinweis':
    'Der Prozess hat selbst keine Technologie — er sieht die Befunde seiner Werkzeuge (A.9.3).',
  'klassen.prozess.leer': 'An diesem Prozessobjekt hängt noch kein Tool-Objekt.',
  'klassen.prozess.getragen': 'Alle ausgelösten Klassen sind getragen.',

  'cockpit.titel': 'Cockpit',
  'cockpit.hinweis':
    'Jede Zeile ist eine Handlungsaufforderung: ein Klick führt direkt in das Modul, in dem der Eintrag abgearbeitet wird.',
  'cockpit.leer': 'In Ihrem Bereich ist zu dieser Zeile nichts offen.',
  'cockpit.anzahl': 'Offen',
  'cockpit.oeffnen': 'Ansehen',
  'cockpit.zurueck': 'Zurück zur Übersicht',
  'cockpit.fachbereich': 'Fachbereich',
  'cockpit.alleFachbereiche': 'Alle Fachbereiche',
  'cockpit.eintrag': 'Eintrag',
  'cockpit.hinweisSpalte': 'Hinweis',
  'cockpit.ziel': 'Ziel',
  'cockpit.aggregat': 'Verteilung',
  'cockpit.filterHinweis':
    'Der Filter steht in der Adresse — diese Ansicht lässt sich so weitergeben. Rechte verleiht er keine.',
  'cockpit.gesamt': '{anzahl} offen',
  'cockpit.allesErledigt': 'Nichts offen',
  'cockpit.nichtsOffen': 'Nichts offen',
  'cockpit.leerHinweis': 'In Ihrem Bereich ist zu dieser Zeile nichts abzuarbeiten.',
  'cockpit.eintraege': 'Einzelfälle',
  'cockpit.modul.prozesse': 'Prozessobjekt',
  'cockpit.modul.tools': 'Tool-Objekt',
  'cockpit.modul.datenobjekte': 'Datenobjekt',
  'cockpit.modul.gates': 'Gate',
  'cockpit.modul.lenkung': 'Lenkung',
  'cockpit.verteilung.je_technologie': 'Tier-Verteilung je Technologie',
  'cockpit.verteilung.je_monat': 'Tier-Verteilung je Monat',
  'cockpit.verteilung.hinweis':
    'Die Farbe steht für die Einstufung, nicht für die Reihe. Jede Zahl steht am Balken.',
  'cockpit.verteilung.leer': 'Für diesen Ausschnitt gibt es noch keine Einstufungen.',
  'cockpit.verteilung.kategorie': 'Kategorie',
  'technologie.apps-script': 'Apps Script',
  'technologie.python-kubernetes': 'Python / Kubernetes',
  'technologie.bigquery-gcs': 'BigQuery / Cloud Storage',
  'technologie.appsheet': 'AppSheet',
  'technologie.unbekannt': 'Ohne Technologie',

  ja: 'Ja',
  nein: 'Nein',
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
  'app.farbschema': 'Apparence',
  'app.farbschema.system': 'Auto',
  'app.farbschema.hell': 'Clair',
  'app.farbschema.dunkel': 'Sombre',

  'stilprobe.titel': 'Échantillon de style',
  'stilprobe.untertitel':
    'Tous les éléments du système de design « Klar » — documentation vivante et contrôle visuel en clair et en sombre.',
  'stilprobe.marke': 'Marque',
  'stilprobe.marke.klar': 'Klar',
  'stilprobe.marke.kaufland': 'Kaufland',
  'stilprobe.knoepfe': 'Boutons',
  'stilprobe.abzeichen': 'Badges',
  'stilprobe.eingaben': 'Saisies',
  'stilprobe.listen': 'Listes groupées',
  'stilprobe.referenz': 'Sélecteur de référence',
  'stilprobe.zustaende': 'Messages et états',
  'stilprobe.blatt': 'Feuille',
  'stilprobe.blattOeffnen': 'Ouvrir la feuille',
  'stilprobe.keineTreffer': 'Aucune entrée trouvée',

  'anmeldung.titel': 'Connexion',
  'anmeldung.hinweis': "La connexion passe exclusivement par l'identité centrale de l'entreprise.",
  'anmeldung.entwicklungsmodus': 'Mode développement : connexion locale',
  'anmeldung.kennung': 'Identifiant',
  'anmeldung.name': 'Nom',
  'anmeldung.namehilfe': "Laisser vide — l'identifiant sert alors aussi de nom.",
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
  'prozess.feld.inputDatenobjekte': 'Entrée — objets de données',
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
  'prozess.umsetzungen.abweichungHilfe':
    'Ce que cette organisation nationale fait différemment. Facultatif — vide signifie : comme le processus INT.',
  'prozess.speichern': 'Enregistrer',
  'prozess.abbrechen': 'Annuler',
  'prozess.pflichtfeld': 'Champ obligatoire',
  'prozess.stellvertretungPflicht': 'Impossible d’enregistrer sans suppléance.',
  'prozess.feld.outputDatenobjekte': 'Sortie — objets de données',
  'prozess.feld.vorgelagert': 'Processus en amont',
  'prozess.feld.nachgelagert': 'Processus en aval',
  'prozess.hilfe.inputDatenobjekte':
    'Référence à des objets de données existants, pas de texte libre. Leur catégorie entre dans l’évaluation.',
  'prozess.hilfe.outputDatenobjekte': 'Ce que ce processus produit ou met à jour.',
  'prozess.hilfe.vorgelagert': 'Qui alimente — en référence, pour que la chaîne reste exploitable.',
  'prozess.hilfe.nachgelagert':
    'Qui consomme. La criticité de ce processus se calcule à partir de cette arête.',
  'prozess.hilfe.supplier': 'Uniquement pour des fournisseurs hors du registre des processus.',
  'prozess.hilfe.schritte': '5 à 7 étapes, mots-clés — une ligne par étape.',
  'prozess.hilfe.output':
    'Le résultat en mots ; en tant que référence, il appartient aux objets de données de sortie.',
  'prozess.schritte.zaehler': 'Étapes',
  'prozess.schritte.warnung':
    'Plus de sept étapes indiquent une altitude inadaptée. Reliez plutôt un autre processus.',
  'prozess.suchen.datenobjekt': 'Rechercher un objet de données …',
  'prozess.suchen.prozess': 'Rechercher un objet de processus …',
  'prozess.keineTreffer': 'Aucune entrée trouvée',
  'prozess.bearbeiten': 'Modifier',
  'prozess.bearbeiten.titel': 'Modifier l’objet de processus',
  'prozess.aktivieren': 'Activer',
  'prozess.stilllegen': 'Mettre hors service',
  'prozess.wiederaufnehmen': 'Repasser en brouillon',
  'prozess.gruppe.beteiligte': 'Responsabilité',
  'prozess.gruppe.sipoc': 'SIPOC — limites et interfaces',
  'prozess.gruppe.kette': 'Chaîne de processus',
  'prozess.gruppe.umsetzung': 'Mise en œuvre',
  'prozess.wirkung.titel': 'Impact',
  'prozess.wirkung.hinweis':
    'En aval : ce qui s’arrête si ce processus tombe. En amont : qui l’alimente.',
  'prozess.wirkung.abwaerts': 'Touchés en aval',
  'prozess.wirkung.aufwaerts': 'Impliqués en amont',
  'prozess.wirkung.leer': 'Aucune arête enregistrée.',
  'prozess.datenobjekte.leer': 'Aucun objet de données référencé.',
  'prozess.herkunft.reichweite': 'À partir du cercle de clients',
  'prozess.herkunft.reichweiteUmsetzung':
    'À partir du cercle de clients, relevé par plusieurs mises en œuvre',
  'prozess.herkunft.kritikalitaetEigen': 'À partir de la conséquence de panne',
  'prozess.herkunft.kritikalitaetKette': 'Hérité de la chaîne de processus',
  'prozess.herkunft.mitbestimmung': 'À partir de la catégorie de données et de l’évaluation',

  'kundenkreis.persoenlich': 'Personnel',
  'kundenkreis.team': 'Équipe',
  'kundenkreis.bereich': 'Domaine',
  'kundenkreis.unternehmen': 'Entreprise',
  'kundenkreis.extern': 'Externe',
  'reichweite.persoenlich': 'Personnel',
  'reichweite.team': 'Équipe',
  'reichweite.bereich': 'Domaine',
  'reichweite.unternehmen': 'Entreprise',
  'reichweite.extern': 'Externe',

  'kategorie.oeffentlich': 'Public',
  'kategorie.intern': 'Interne — professionnel',
  'kategorie.vertraulich': 'Interne — confidentiel',
  'kategorie.personenbezogen': 'Données personnelles — général',
  'kategorie.besondere_kategorie': 'Données personnelles — particulières',

  'ausfallfolge.keine': 'Aucune',
  'ausfallfolge.gering': 'Faible',
  'ausfallfolge.spuerbar': 'Sensible',
  'ausfallfolge.kritisch': 'Critique',

  'status.entwurf': 'Brouillon',
  'status.aktiv': 'Actif',
  'status.freigabe_ausstehend': 'Validation en attente',
  'status.stillgelegt': 'Désactivé',
  'prozess.freigabeAusstehend':
    "Cet objet de processus fonctionne, mais n'est pas validé pour son niveau actuel : la réévaluation l'a porté au niveau 3. Une procédure Gate 1 existe déjà. Après la validation et un nouvel engagement, il peut être réactivé.",

  'bewertung.titel': 'Évaluation',
  'bewertung.untertitel': 'Une question par étape. Le résultat apparaît à la fin.',
  'bewertung.starten': "Réaliser l'évaluation",
  'bewertung.modus.frage': "Comment souhaitez-vous parcourir l'arbre ?",
  'bewertung.modus.schnell': 'Rapide — s’arrête au premier résultat de niveau 3',
  'bewertung.modus.vollstaendig': 'Complet — les six étapes, avec les classes K',
  'bewertung.modus.schnell.kurz': 'Rapide',
  'bewertung.modus.vollstaendig.kurz': 'Complet',
  'bewertung.modus.schnell.folge':
    "Le parcours s'arrête dès qu'une dimension atteint le niveau 3. Vous obtenez le niveau, mais pas les classes de mesures : celles-ci supposent le profil complet.",
  'bewertung.modus.vollstaendig.folge':
    'Les six dimensions sont parcourues. Le résultat indique le niveau, le profil et les classes de mesures déclenchées avec leurs obligations.',
  'bewertung.modus.hinweis':
    "Le choix se fait au début. Le résultat intermédiaire n'est volontairement pas affiché.",
  'bewertung.ja': 'Oui',
  'bewertung.nein': 'Non',
  'bewertung.weiter': 'Continuer',
  'bewertung.zurueck': 'Retour',
  'bewertung.abbrechen': "Interrompre l'évaluation",
  'bewertung.zurueckZurAuswahl': 'Recommencer',
  'bewertung.schritt': 'Étape',
  'bewertung.von': 'sur',
  'bewertung.fortschritt': "Progression dans l'arbre d'évaluation",
  'bewertung.frage': 'Question',
  'bewertung.ergebnis': 'Résultat',
  'bewertung.tier': 'Niveau',
  'bewertung.profil': 'Profil',
  'bewertung.vorschlag': 'Proposition issue de vos données :',
  'bewertung.vorschlag.offen':
    'Les données disponibles ne disent rien sur cette question — elle est à expliquer.',
  'bewertung.quelle.datenobjekt': 'Objet de données',
  'bewertung.quelle.tool': 'Objet outil',
  'bewertung.quelle.prozess': 'Processus',
  'bewertung.quelle.kette': 'Chaîne de processus',
  'bewertung.quelle.kundenkreis': 'Cercle de clients',
  'bewertung.abweichung.hinweis':
    "Votre réponse contredit ce qui ressort des données enregistrées. C'est admis — seule la raison est consignée.",
  'bewertung.abweichung.feld': "Motif de l'écart",
  'bewertung.abweichung.hilfe':
    "Une phrase suffit. Elle est enregistrée avec l'évaluation et figure dans la piste d'audit.",
  'bewertung.abweichungen': 'Écarts motivés',
  'bewertung.abweichungen.hinweis':
    'La proposition et la réponse sont toutes deux enregistrées, afin que la décision reste traçable.',
  'bewertung.kKlassen': 'Classes de mesures déclenchées',
  'bewertung.kKlassen.hinweis': 'Ce que ce processus doit remplir au vu de son profil.',
  'bewertung.kKlassen.leer': 'Ce profil ne déclenche aucune classe de mesures.',
  'bewertung.auflagen': 'Obligations du niveau atteint',
  'bewertung.auflagen.hinweis': 'inclut les obligations des niveaux inférieurs.',
  'bewertung.keineKKlassen':
    'Le parcours rapide s’arrête plus tôt et ne fournit donc pas de classes K.',
  'bewertung.speichern': "Enregistrer l'évaluation",
  'bewertung.gespeichert': "L'évaluation a été enregistrée.",
  'bewertung.abbruch.titel': "Abandonner l'évaluation ?",
  'bewertung.abbruch.text': 'Les réponses données ne seront pas enregistrées.',
  'bewertung.abbruch.zaehler.eine': 'Une réponse sera perdue.',
  'bewertung.abbruch.zaehler': 'réponses seront perdues.',
  'bewertung.abbruch.weiterbewerten': "Poursuivre l'évaluation",
  'bewertung.abbruch.verwerfen': 'Abandonner',
  'bewertung.verboten.titel': 'Pratique d’IA interdite',
  'bewertung.verboten.text':
    "Le parcours a révélé une pratique interdite par le règlement européen sur l'IA. Aucune évaluation n'est enregistrée ; une alerte de gouvernance est créée à la place.",
  'bewertung.verboten.weg':
    'Adressez-vous à la gouvernance et au service juridique avant de poursuivre le processus.',
  'bewertung.verboten.alarm': "Déclencher l'alerte",
  'bewertung.historie': 'Historique des évaluations',
  'bewertung.bewertetAm': 'Évalué le',
  'bewertung.massgeblich': 'Applicable',
  'bewertung.historie.leer': "Aucune évaluation n'existe encore pour ce processus.",
  'bewertung.vollstaendig': 'complet',
  'bewertung.unvollstaendig': 'rapide',
  'bewertung.gueltigBis': "Valable jusqu'au",

  'nav.tools': 'Objets outils',
  'nav.datenobjekte': 'Objets de données',

  'asset.tools.titel': 'Objets outils',
  'asset.tools.leer': "Aucun objet outil n'est encore saisi dans votre domaine.",
  'asset.tools.neu': 'Créer un objet outil',
  'asset.datenobjekte.titel': 'Objets de données',
  'asset.datenobjekte.leer': "Aucun objet de données n'est encore saisi dans votre domaine.",
  'asset.datenobjekte.neu': 'Créer un objet de données',
  'asset.feld.name': 'Nom',
  'asset.feld.beschreibung': 'Description',
  'asset.feld.technologie': 'Technologie',
  'asset.feld.kategorie': 'Catégorie',
  'asset.feld.herkunft': 'Origine',
  'asset.feld.status': 'Statut',
  'asset.herkunft.importiert': 'Importé',
  'asset.herkunft.manuell': 'Manuel',
  'asset.status.importiert_unbestaetigt': 'Importé, non confirmé',
  'asset.status.bestaetigt': 'Confirmé',
  'asset.status.inaktiv': 'Inactif',
  'asset.bestaetigen': 'Confirmer',
  'asset.bestaetigenHinweis':
    "Tant que cet objet outil n'est pas confirmé, il ne peut pas être lié à un processus — il hériterait sinon d'une classification avant que quiconque ait vérifié qu'il s'agit bien de l'objet visé.",
  'asset.importHinweis':
    "Cet enregistrement provient d'un import. Le nom et les métadonnées techniques se modifient dans le système source ; les champs de gouvernance se gèrent ici.",
  'asset.geerbt.titel': 'Classification héritée — maximum de toutes les arêtes de processus',
  'asset.geerbt.hinweis':
    'Un outil relié à plusieurs processus porte la classification la plus élevée de toutes ses arêtes ; le lien le plus faible serait sinon un contournement silencieux.',
  'asset.geerbt.kritikalitaet': 'Criticité',
  'asset.geerbt.reichweite': 'Portée',
  'asset.geerbt.tier': 'Niveau',
  'asset.geerbt.kKlassen': 'Classes K',
  'asset.prozesse.titel': 'Objets de processus liés',
  'asset.prozesse.leer': "Cet objet outil n'est rattaché à aucun processus.",
  'asset.prozesse.verknuepfen': 'Lier à un processus',
  'asset.prozesse.loesen': 'Détacher',
  'asset.tools.amProzess': 'Objets outils liés',
  'asset.tools.amProzessLeer': "Aucun objet outil n'est encore rattaché à ce processus.",
  'asset.speichern': 'Enregistrer',
  'asset.kategorie.keine': 'Sans catégorie',
  'asset.feld.fachbereich': 'Domaine',
  'asset.feld.quellsystem': 'Système source',
  'asset.quellsystem.leer': 'Aucun système source indiqué',
  'asset.quellsystem.hilfe': 'Le système où naissent ces données — par exemple « SAP HCM ».',
  'asset.reifegrad1': 'Niveau 1 — nom, catégorie, domaine, système source',
  'asset.feld.gebenderProzess': 'Processus source',
  'asset.gebenderProzess.hilfe':
    'Le processus qui produit ces données. Son domaine devient le service détenteur — il ne se choisit pas, il découle.',
  'asset.gebenderProzess.keiner':
    "Aucun processus ne produit cette source — elle n'est qu'utilisée.",
  'asset.fachbereich.hilfe':
    'Le service détenteur. Il détermine qui classe la source ; seule la gouvernance peut le changer.',
  'asset.anlegen.weg':
    'Une source obtient son domaine de deux façons : par le processus source ou par vous, en tant que responsable des objets de données.',
  'asset.anlegen.keinWeg':
    'Pour créer une source, il faut un processus que vous portez ou le rôle de responsable des objets de données dans un domaine.',
  'asset.reifegrad1.hinweis':
    'La fonction de conformité n’exige rien de plus. Schéma et contrat sont une évolution, pas un préalable.',
  'asset.datenobjekte.hinweis':
    'Ce ne sont pas les outils qui sont classés, mais les sources — les outils héritent.',
  'asset.datenobjekte.ohneKategorie': 'Voir les objets de données sans catégorie dans le cockpit',
  'asset.kategorie.hilfe': 'Pour la question « est-ce personnel », la catégorie suffit.',
  'asset.kategorie.wirkungHinweis':
    'Avant validation, l’application montre qui est concerné par la modification.',
  'kategorie.anker.oeffentlich': 'librement accessible',
  'kategorie.anker.intern': 'sans données personnelles',
  'kategorie.anker.vertraulich': 'secret d’affaires, finances',
  'kategorie.anker.personenbezogen': 'contact, organisation',
  'kategorie.anker.besondere_kategorie': 'rémunération, santé, évaluation',
  'asset.verwendung.prozesse': 'Référencé par des objets de processus',
  'asset.verwendung.hinweis':
    'Une modification ici agit sur tous les objets référençants — rien à reporter ailleurs.',
  'asset.verwendung.tools': 'Utilisé par des objets outils',
  'asset.verwendung.keineProzesse': 'Aucun objet de processus ne référence cet objet de données.',
  'asset.verwendung.keineTools': 'Aucun objet outil n’accède à cet objet de données.',
  'asset.verwendung.alsInput': 'Entrée',
  'asset.verwendung.alsOutput': 'Sortie',
  'asset.verwendung.ueberProzess': 'Relié via le processus',
  'zugriffsart.lesen': 'Lit',
  'zugriffsart.schreiben': 'Écrit',
  'zugriffsart.lesen_schreiben': 'Lit et écrit',
  'asset.wirkung.titel': 'Impact de la reclassification',
  'asset.wirkung.hinweis': 'Ce que cette modification touche — avant la décision, pas après.',
  'asset.wirkung.von': 'Actuel',
  'asset.wirkung.nach': 'Futur',
  'asset.wirkung.prozesse': 'Objets de processus concernés',
  'asset.wirkung.tools': 'Objets outils concernés',
  'asset.wirkung.mitbestimmung': 'Nouvellement soumis à la cogestion',
  'asset.wirkung.mitbestimmungHinweis':
    'Objets de processus qui obtiennent le marqueur par cette modification',
  'asset.wirkung.warnung':
    'Cette modification rend des processus soumis à la cogestion. Leur évaluation est à renouveler.',
  'asset.wirkung.uebernehmen': 'Appliquer la catégorie',

  'tool.hinweis':
    'Ce que fait un outil, la télémétrie le sait. Ce qu’il produit comme effet, seul son responsable le déclare.',
  'tool.feld.owner': 'Responsable technique',
  'tool.feld.stellvertretung': 'Suppléance',
  'tool.feld.organisationseinheit': 'Unité organisationnelle',
  'tool.einheit.hilfe':
    'Le domaine auquel appartient cet outil. Il détermine qui peut le voir et le modifier — et seule la gouvernance peut le changer par la suite.',
  'tool.feld.lauftyp': 'Mode d’exécution',
  'tool.owner.hilfe': 'Destinataire de l’engagement et des procédures de pilotage.',
  'tool.lauftyp.hilfe':
    'Oriente les décisions techniques. Pas un axe de niveau à part entière — seulement un correctif dans les cas limites.',
  'tool.lauftyp.interaktiv': 'Interactif — déclenché par une personne',
  'tool.lauftyp.getriggert': 'Déclenché — par un événement',
  'tool.lauftyp.geplant': 'Planifié — sans surveillance, selon un horaire',
  'tool.lauftyp.keiner': 'Non renseigné',
  'tool.technologie.keine': 'Non renseignée',
  'tool.stammdaten': 'Données de base',
  'tool.stammdaten.hinweis': 'Déclaré — ce que la télémétrie ne connaît pas.',

  'tool.attest.titel': 'Attestations',
  'tool.attest.hinweis':
    'Trois déclarations que la télémétrie ne peut pas fournir. Elles sont faites au nom d’une personne, pas comme un simple champ.',
  'tool.attest.frage1': 'Le résultat alimente-t-il une décision concernant des personnes ?',
  'tool.attest.frage1.zusatz':
    'Y compris indirectement — par exemple comme proposition généralement suivie.',
  'tool.attest.frage2': 'Une personne s’interpose-t-elle entre la sortie et son effet ?',
  'tool.attest.frage2.zusatz':
    'Quelqu’un vérifie-t-il le résultat avant qu’il produise son effet ? Sans personne interposée, l’outil est transformateur — même en lecture seule.',
  'tool.attest.frage3':
    'Traite-t-on des catégories de données ne provenant pas de sources classifiées ?',
  'tool.attest.frage3.zusatz':
    'Téléversements, saisies manuelles, presse-papiers. La plus importante des trois — elle comble la lacune que le modèle d’objets de données ne peut pas fermer.',
  'tool.attest.abgeben': 'Faire la déclaration',
  'tool.attest.erneuern': 'Renouveler la déclaration',
  'tool.attest.offen': 'Pas encore déclaré',
  'tool.attest.offenHinweis':
    'Sans ces trois déclarations, aucun rattachement à un objet de processus n’est possible.',
  'tool.attest.erklaertVon': 'Déclaré par',
  'tool.attest.erklaertAm': 'Déclaré le',
  'tool.attest.unbekannt': 'Inconnu',

  'tool.wirkungsart': 'Type d’effet',
  'tool.wirkungsart.veraendernd': 'Transformateur',
  'tool.wirkungsart.gestaltend': 'Facilitateur',
  'tool.wirkungsart.offen': 'Encore indéterminé',
  'tool.wirkungsart.grund.schreibzugriff':
    'Écrit sur un objet de données — toujours soumis à contrôle.',
  'tool.wirkungsart.grund.kein_mensch':
    'Aucune personne entre la sortie et l’effet — transformateur même en lecture seule.',
  'tool.wirkungsart.grund.nur_lesend':
    'Accès en lecture seule, et une personne vérifie le résultat.',
  'tool.wirkungsart.grund.offen': 'Déterminable seulement après la deuxième attestation.',

  'tool.daten.titel': 'Objets de données utilisés',
  'tool.daten.hinweis':
    'Non pas « l’outil a un accès », mais « l’outil lit cet objet dans le cadre de ce processus ».',
  'tool.daten.leer': 'Cet objet outil n’accède à aucun objet de données.',
  'tool.daten.hinzufuegen': 'Rattacher un objet de données',
  'tool.daten.zugriffsart': 'Type d’accès',
  'tool.daten.zugriffsartHilfe':
    'Vaut pour le prochain rattachement. Un accès en écriture rend l’outil transformateur.',
  'tool.daten.entfernen': 'Retirer le rattachement',
  'tool.daten.ausserhalb': 'Hors du cadre du processus',
  'tool.daten.ausserhalbHinweis':
    'Cet objet de données n’est déclaré dans aucun processus rattaché. Limitation des finalités non établie.',
  'tool.daten.nurKategorie': 'Non déclaré',
  'tool.daten.nurKategorieHinweis':
    'La catégorie figure dans le cadre du processus, mais pas cet objet lui-même.',
  'tool.daten.ohneProzess':
    'Sans rattachement à un processus, il n’existe aucun cadre permettant de vérifier la limitation des finalités.',
  'tool.daten.abweichungen':
    'Limitation des finalités non établie : {anzahl} objets de données utilisés sont hors du cadre du processus.',

  'tool.prozesse.hinweis': 'La finalité dans le cadre de laquelle cet outil travaille.',
  'tool.prozesse.geerbtVon': 'Contribution de chaque arête',
  'tool.prozesse.massgeblich': 'Détermine le maximum',
  'tool.tools.suche': 'Rechercher',
  'tool.tools.platzhalter': 'Nom ou technologie …',
  'tool.attestierungFehlt': 'Attestation manquante',

  'nav.gates': 'Portes',

  'sv.titel': 'Engagement volontaire',
  'sv.untertitel.prozess':
    'Six affirmations concrètes selon A.10.2 — chacune à confirmer séparément, chacune vérifiable après coup.',
  'sv.untertitel.tool':
    "Six affirmations concrètes selon A.10.3 sur l'exploitation de cet objet outil.",
  'sv.stand': 'État de la déclaration',
  'sv.aussagen': 'Affirmations',
  'sv.kurzform': 'Forme courte : au niveau 1, seul le noyau est exigé (A.10.5).',
  'sv.vollform': 'À partir du niveau 2, toutes les affirmations sont à confirmer.',
  'sv.nochkeine': 'Aucune déclaration remise pour le moment.',
  'sv.abgegebenAm': 'Remis le',
  'sv.gebundenAn': 'Lié à',
  'sv.gedeckt': 'Valable',
  'sv.bestaetigen': 'Confirmer pour une année de plus',
  'sv.kommentarZu': 'Ajouter un commentaire',
  'sv.offen': 'Encore ouvert :',
  'sv.grund.keine.kurz': 'Manquant',
  'sv.grund.unvollstaendig.kurz': 'Incomplet',
  'sv.grund.alter_katalog.kurz': 'Ancien catalogue',
  'sv.grund.profil_veraltet.kurz': 'Caduc',
  'sv.grund.tier_gestiegen.kurz': 'Caduc',
  'sv.grund.frist_abgelaufen.kurz': 'Expiré',
  'sv.abgeben': "Remettre l'engagement",
  'sv.hinweis':
    "Chaque affirmation doit être confirmée séparément. L'engagement n'est complet que lorsque toutes le sont.",
  'sv.kommentar': 'Commentaire',
  'sv.speichern': 'Remettre',
  'sv.status': "État de l'engagement",
  'sv.vollstaendig': 'Remis intégralement',
  'sv.unvollstaendig': 'Incomplet',
  'sv.keine': "Aucun engagement n'existe encore pour ce processus.",
  'sv.gueltigBis': "Valable jusqu'au",

  'gate.titel': 'Procédures de porte',
  'gate.hinweis':
    "Le gate 1 est la première autorisation à partir du niveau 3. Le gate 2 exige l'un des cinq déclencheurs limitativement énumérés en A.11.",
  'gate.begruendungHilfe':
    "Qu'est-ce qui a changé, et pourquoi l'autorisation est-elle nécessaire ?",
  'gate.ausloeser.neue_datenkategorie': 'Nouvelle catégorie de données',
  'gate.ausloeser.reichweitenerweiterung': 'Extension de la portée',
  'gate.ausloeser.neues_externes_ziel': 'Nouvelle destination externe',
  'gate.ausloeser.ki_komponente_ergaenzt': 'Composant IA ajouté',
  'gate.ausloeser.kritikalitaet_gestiegen': 'Criticité accrue',
  'gate.ablehnungBegruendung': 'Un refus doit être motivé.',
  'gate.leer': 'Aucune procédure de porte pour ce processus.',
  'gate.einreichen': 'Soumettre une porte',
  'gate.typ': 'Porte',
  'gate.typ.1': 'Porte 1 — première autorisation de niveau 3',
  'gate.typ.2': 'Porte 2 — dépassement du cadre',
  'gate.ausloeser': 'Élément déclencheur',
  'gate.ausloeserPflicht':
    'La porte 2 exige exactement un des cinq déclencheurs énumérés de façon exhaustive.',
  'gate.begruendung': 'Justification',
  'gate.status': 'Statut',
  'gate.status.eingereicht': 'Soumise',
  'gate.status.in_pruefung': "En cours d'examen",
  'gate.status.freigegeben': 'Autorisée',
  'gate.status.abgelehnt': 'Refusée',
  'gate.entscheiden': 'Décider',
  'gate.freigeben': 'Autoriser',
  'gate.ablehnen': 'Refuser',
  'gate.kommentar': 'Commentaire de décision',
  'gate.arbeitsvorrat': 'Procédures de porte ouvertes',
  'gate.arbeitsvorratLeer': 'Aucune procédure de porte ouverte.',
  'gate.arbeitsvorratHinweis': 'Ce qui attend une décision de la gouvernance.',
  'gate.prozess': 'Objet de processus',

  'nav.lenkung': 'Pilotage',

  'compliance.titel': 'État de conformité',
  'compliance.hinweis':
    "Chaque constat crée une nouvelle entrée ; l'état actuel est celui du haut. Rien n'est écrasé.",
  'compliance.leer': "Aucun état n'est encore enregistré pour cet objet outil.",
  'compliance.farbe': 'État',
  'compliance.farbe.gruen': 'Vert',
  'compliance.farbe.gelb': 'Jaune',
  'compliance.farbe.rot': 'Rouge — dépassement du cadre',
  'compliance.begruendung': 'Justification',
  'compliance.abweichung': 'Type d’écart',
  'compliance.melden': 'Signaler un état',
  'compliance.festgestelltAm': 'Constaté le',
  'compliance.rotHinweis':
    "Un signalement rouge ouvre automatiquement une procédure de pilotage au niveau d'escalade 1, avec le délai lié au niveau.",

  'lenkung.titel': 'Procédures de pilotage',
  'lenkung.leer': 'Aucune procédure de pilotage ouverte.',
  'lenkung.tool': 'Objet outil',
  'lenkung.zumTool': "Vers l'objet outil",
  'lenkung.stufe': "Niveau d'escalade",
  'lenkung.stufeKurz': 'Niveau',
  'lenkung.frist': 'Délai',
  'lenkung.status': 'Statut',
  'lenkung.status.offen': 'Ouverte',
  'lenkung.status.aufgeloest': 'Résolue',
  'lenkung.status.abgebrochen': 'Annulée',
  'lenkung.aufloesen': 'Résoudre',
  'lenkung.art': 'Mode de résolution',
  'lenkung.art.anpassen': 'Adapter',
  'lenkung.art.rahmen_erweitern': 'Élargir le cadre',
  'lenkung.art.stilllegen': 'Mettre hors service',
  'lenkung.bewertung': 'Nouvelle évaluation',
  'lenkung.bewertungPflicht':
    "La procédure ne se clôt qu'une fois la nouvelle évaluation terminée.",
  'lenkung.kommentar': 'Commentaire',
  'lenkung.stufe3':
    'Le niveau 3 signale la procédure pour une mesure technique. Le retrait des accès a lieu en dehors de cette application.',

  'lenkung.hinweis':
    'Chaque dépassement du cadre reçoit un délai en jours ouvrés et exactement trois issues (A.13.6).',
  'lenkung.leerHinweis': 'Tous les objets outils de votre domaine restent dans le cadre.',
  'lenkung.schicht2':
    "Violation d'une interdiction valable pour toute l'organisation : {verbot}. Ces cas commencent sans premier niveau — il n'y a rien à clarifier, seulement à corriger.",
  'lenkung.abgelaufen': 'Échu',
  'lenkung.abgelaufenSeit': 'depuis {tage} jours ouvrés',
  'lenkung.abgelaufenHeute': "depuis aujourd'hui",
  'lenkung.arbeitstagRest': 'jour ouvré restant',
  'lenkung.arbeitstageRest': 'jours ouvrés restants',
  'lenkung.art.anpassen.hinweis':
    "L'outil est ramené dans le cadre. L'état repasse ensuite au vert.",
  'lenkung.art.rahmen_erweitern.hinweis':
    "Le cadre est élargi. Cela exige une nouvelle évaluation de l'objet processus concerné — choisissez-la ci-dessous.",
  'lenkung.art.stilllegen.hinweis':
    "L'outil est mis hors service. Ce n'est pas un retour dans le cadre : l'état reste rouge.",
  'lenkung.bewertungFehlt':
    "Aucune nouvelle évaluation n'existe pour cet objet outil depuis l'ouverture du dossier. Réévaluez d'abord l'objet processus concerné.",

  'rahmen.titel': "Cadre d'autorisation",
  'rahmen.hinweis':
    'Ce que cet outil a le droit de faire, déduit des objets processus et des attestations — et à côté, ce qui est réellement enregistré (A.13.2).',
  'rahmen.eingehalten': 'Dans le cadre',
  'rahmen.abweichungen': '{anzahl} écarts',
  'rahmen.abweichungen.eine': 'Un écart',
  'rahmen.erlaubt': 'Autorisé',
  'rahmen.gemessen': 'Mesuré',
  'rahmen.ohneMessung': 'Non mesuré — déduit',
  'rahmen.schicht2.erkannt':
    'Violation de la couche 2 détectée à partir des données enregistrées :',
  'rahmen.element.datenobjekte': 'Objets de données',
  'rahmen.element.datenkategorie': 'Catégorie de données maximale',
  'rahmen.element.reichweite': 'Portée',
  'rahmen.element.externe_ziele': 'Cibles externes',
  'rahmen.element.zugriffsart': "Type d'accès",
  'rahmen.element.ausfuehrungsart': "Mode d'exécution",
  'rahmen.element.ausfuehrungsidentitaet': "Identité d'exécution",
  'rahmen.abweichung.datenobjekte': 'Utilisé hors du cadre : {werte}',
  'rahmen.abweichung.datenkategorie':
    "L'outil traite une catégorie plus élevée que celle couverte par le cadre : {werte}",
  'rahmen.abweichung.reichweite': 'Hors de la portée héritée : {werte}',
  'rahmen.abweichung.externe_ziele': 'Cible non déclarée : {werte}',
  'rahmen.abweichung.zugriffsart':
    "Accès en écriture à un objet de données qui n'est pas un résultat de processus : {werte}",
  'rahmen.abweichung.ausfuehrungsart': "L'attestation ne couvre pas ce mode d'exécution : {werte}",
  'rahmen.abweichung.ausfuehrungsidentitaet':
    "Cette identité ne correspond pas au mode d'exécution : {werte}",
  'rahmen.identitaet.persoenlich': 'Identité personnelle',
  'rahmen.identitaet.benannter_dienst': 'Identité de service nommée',
  'rahmen.identitaet.geteiltes_konto': 'Compte partagé',

  'schicht2.identitaet_umgangen': "Exécution sous une identité d'entreprise contournée",
  'schicht2.statische_zugangsdaten': "Identifiants à validité permanente enregistrés dans l'outil",
  'schicht2.undeklarierte_quellen': 'Traitement de données issues de sources non déclarées',
  'schicht2.entscheidung_ohne_mensch':
    'Décision automatisée sur des personnes sans intervention humaine',
  'schicht2.daten_ins_offene_netz':
    "Transmission de données d'entreprise hors de l'infrastructure autorisée",
  'schicht2.protokollierung_umgangen':
    'Exploitation sans journalisation ou avec journalisation désactivée',

  'compliance.schicht2': 'Violation de la couche 2',
  'compliance.schicht2.keiner': 'Aucune — dépassement du cadre selon la couche 1',
  'compliance.schicht2Hilfe':
    "Exactement l'une des six interdictions valables pour toute l'organisation (A.13.2). Aucun septième motif libre n'est proposé.",
  'compliance.schicht2Folge':
    'Ce dossier commence directement au niveau 2 : le responsable hiérarchique est informé immédiatement, et aucune évaluation ne débloque le cas.',

  'konfiguration.titel': 'Paramètres',
  'konfiguration.hinweis':
    'Délais, seuils et préavis de la gouvernance — modifiables en exploitation, sans livraison.',
  'konfiguration.nurLesen':
    'Consultation sans droit de modification : les paramètres de gouvernance relèvent du rôle Gouvernance.',
  'konfiguration.nichtRueckwirkend':
    "Une modification vaut pour les nouveaux dossiers, sans effet rétroactif. Les délais en cours restent tels qu'ils ont été calculés à l'ouverture.",
  'konfiguration.sichern': 'Enregistrer',
  'konfiguration.gesichert': 'Enregistré',
  'konfiguration.gruppe.lenkung': 'Délais de pilotage (A.13.5)',
  'konfiguration.gruppe.fristen': 'Validité et rappel',
  'konfiguration.gruppe.schwellen': 'Seuils',
  'konfiguration.lenkung_frist_tage_tier1': 'Niveau 1 pour Tier 1',
  'konfiguration.lenkung_frist_tage_tier2': 'Niveau 1 pour Tier 2',
  'konfiguration.lenkung_frist_tage_tier3': 'Niveau 1 pour Tier 3',
  'konfiguration.lenkung_nachfrist_tage_tier1': 'Délai supplémentaire au niveau 2 pour Tier 1',
  'konfiguration.lenkung_nachfrist_tage_tier2': 'Délai supplémentaire au niveau 2 pour Tier 2',
  'konfiguration.lenkung_nachfrist_tage_tier3': 'Délai supplémentaire au niveau 2 pour Tier 3',
  'konfiguration.selbstverpflichtung_gueltigkeit_tage': "Validité d'un engagement",
  'konfiguration.selbstverpflichtung_erinnerung_vorlauf_tage': 'Préavis du rappel',
  'konfiguration.bewertung_gueltigkeit_tage_tier3': "Validité d'une évaluation à partir de Tier 3",
  'konfiguration.asset_inaktiv_tage': 'À partir de quand un outil est considéré inactif',

  'prozess.ziele.titel': 'Cibles externes autorisées',
  'prozess.ziele.hinweis':
    "Le cadre déclaré selon A.13.2 : vers où ce processus peut transmettre. Ce qui n'y figure pas n'est pas autorisé.",
  'prozess.ziele.leer': 'Aucune cible externe déclarée pour ce processus.',
  'prozess.ziele.neu': 'Ajouter une cible',
  'prozess.ziele.hinzufuegen': 'Ajouter',
  'prozess.ziele.entfernen': 'Retirer',
  'prozess.ziele.gateHinweis':
    "Sur un objet processus actif, une nouvelle cible déclenche la porte 2 (A.11) — le dossier naît de lui-même à l'enregistrement.",

  'tool.feld.identitaet': "Identité d'exécution",
  'tool.identitaet.keine': 'Non déclarée',
  'tool.identitaet.hilfe':
    "Sous quelle identité l'outil s'exécute. Un compte partagé est interdit dans toute l'organisation (A.13.2 couche 2).",
  'tool.feld.statischeZugangsdaten': 'Identifiants à validité permanente enregistrés',
  'tool.statischeZugangsdaten.hilfe':
    "Des identifiants inscrits dans l'outil au lieu d'être gérés. Un oui constitue une violation de la couche 2.",
  'tool.ziele.titel': 'Cibles externes',
  'tool.ziele.hinweis':
    'Vers où cet outil transmet réellement. La comparaison avec le cadre déclaré figure plus bas.',
  'tool.ziele.leer': 'Aucune cible externe enregistrée pour cet objet outil.',
  'tool.ziele.neu': 'Enregistrer une cible',

  'nav.cockpit': 'Cockpit',

  'nav.klassen': "Classes d'exigences",
  'nav.konzept': 'Concept',
  'nav.verwaltung': 'Administration',
  'nav.nachweis': 'Journal',

  'konzept.titel': 'Concept et démarche',
  'konzept.hinweis':
    'Comment nous traitons le citizen development et le code sur mesure — les notions, les règles et leur articulation.',
  'konzept.ansicht': 'Affichage',
  'konzept.ansicht.vortrag': 'Présentation',
  'konzept.ansicht.dokument': 'Document',
  'konzept.zurueck': 'Précédent',
  'konzept.weiter': 'Suivant',
  'konzept.vollbild': 'Plein écran',
  'konzept.fortschritt': 'Progression de la présentation',
  'konzept.nurDeutsch':
    "La présentation n'existe pour l'instant qu'en allemand. L'application elle-même est traduite.",

  'rechte.prozess.nurLesen':
    "Vous voyez cet objet de processus mais ne pouvez pas le modifier. L'écriture revient au propriétaire de processus du domaine concerné ou au rôle de gouvernance.",
  'rechte.prozess.nurUmsetzung':
    "En tant que responsable de mise en œuvre, vous gérez l'écart local de votre société nationale — et rien d'autre. Le reste appartient au domaine émetteur.",
  'rechte.tool.nurLesen':
    "Vous voyez cet objet outil mais ne pouvez pas le modifier. L'écriture revient à son propriétaire technique, au propriétaire d'un processus lié ou au rôle de gouvernance.",
  'rechte.datenobjekt.nurLesen':
    'Vous voyez cet objet de données sans pouvoir le modifier. Les données de base sont tenues par le responsable des objets de données du domaine ou par le responsable du processus source ; seul le premier fixe la catégorie.',
  'rechte.datenobjekt.nurStammdaten':
    'En tant que responsable du processus source, vous tenez le nom, la description et le système source. La catégorie est fixée par le responsable des objets de données du domaine — elle agit dans chaque processus qui utilise cette source.',
  'rechte.datenobjekt.ankerFest':
    'Le domaine ne change pas — seule la gouvernance peut le modifier.',
  'rechte.lenkung.nurLesen':
    'Ce dossier est clôturé par la personne concernée ou par le rôle de gouvernance.',
  'rechte.liste.leer':
    "Rien dans votre périmètre. Un rôle n'agit jamais seul : il vaut toujours pour un périmètre donné — les deux sont attribués par l'administrateur.",

  'rolle.prozess_owner': 'Responsable de processus',
  'rolle.prozess_umsetzer': 'Metteur en œuvre',
  'rolle.technischer_owner': 'Responsable technique',
  'rolle.datenobjekt_owner': 'Responsable des données',
  'rolle.governance': 'Gouvernance',
  'rolle.plattform': 'Plateforme',
  'rolle.auditor': 'Auditeur',
  'rolle.app_administrator': "Administrateur de l'application",

  'verwaltung.titel': 'Administration',
  'verwaltung.hinweis':
    'Utilisateurs et rôles. Qui attribue ici accorde tous les autres accès — soyez économe.',
  'verwaltung.nurLesen':
    "Consultation sans droit de modification : utilisateurs et rôles relèvent de l'administrateur.",
  'verwaltung.nutzer': 'Utilisateurs',
  'verwaltung.nutzerHinweis': 'Nom, statut, responsable hiérarchique et rôles attribués.',
  'verwaltung.suche': 'Rechercher un utilisateur',
  'verwaltung.suchePlatzhalter': 'Nom ou courriel',
  'verwaltung.keineTreffer': 'Aucun utilisateur ne correspond à cette recherche.',
  'verwaltung.aktiv': 'Actif',
  'verwaltung.inaktiv': 'Inactif',
  'verwaltung.aktivstatus': 'Actif',
  'verwaltung.fuehrungskraft': 'Responsable hiérarchique',
  'verwaltung.ohneFuehrungskraft': 'non renseigné',
  'verwaltung.fuehrungskraftHilfe':
    "À partir du niveau 2, le signalement d'un dossier de pilotage lui est adressé (A.13.5).",
  'verwaltung.bestehende': 'Rôles attribués',
  'verwaltung.keineRolle': "Aucun rôle n'est encore attribué à cet utilisateur.",
  'verwaltung.rolle': 'Rôle',
  'verwaltung.scopeTyp': 'Périmètre',
  'verwaltung.scope.global': "À l'échelle de l'entreprise",
  'verwaltung.scope.fachbereich': 'Domaine',
  'verwaltung.scope.organisationseinheit': 'Unité organisationnelle',
  'verwaltung.zuweisen': 'Attribuer le rôle',
  'verwaltung.entziehen': 'Retirer',
  'verwaltung.wirkung':
    'Cette attribution donne en plus accès à {prozesse} objets processus et {tools} objets outils ({scope}).',
  'verwaltung.wirkungBeispiele': 'Par exemple',

  'nachweis.titel': 'Journal',
  'nachweis.hinweis':
    'Chaque action modifiante avec sa date, son auteur et ce qui a changé (A.13.7).',
  'nachweis.art': "Type d'objet",
  'nachweis.alleArten': "Tous les types d'objets",
  'nachweis.filterHinweis': "Le filtre figure dans l'adresse et peut donc être partagé.",
  'nachweis.eintraege': 'Modifications',
  'nachweis.leer': 'Aucune entrée pour cet extrait.',
  'nachweis.leerHinweis': "Dès que quelqu'un modifie quelque chose, cela figure ici.",
  'nachweis.aktion.erstellt': 'Créé',
  'nachweis.aktion.geaendert': 'Modifié',
  'nachweis.aktion.geloescht': 'Supprimé',
  'nachweis.art.prozessobjekte': 'Objet processus',
  'nachweis.art.bewertungen': 'Évaluation',
  'nachweis.art.tool_objekte': 'Objet outil',
  'nachweis.art.datenobjekte': 'Objet de données',
  'nachweis.art.selbstverpflichtungen': 'Engagement',
  'nachweis.art.gate_vorgaenge': 'Dossier de porte',
  'nachweis.art.lenkungsvorgaenge': 'Dossier de pilotage',
  'nachweis.art.compliance_zustaende': 'État de conformité',
  'nachweis.art.rollenzuweisungen': 'Attribution de rôle',
  'nachweis.art.konfiguration': 'Paramètre',

  'klassen.titel': "Classes d'exigences",
  'klassen.hinweis':
    "Ce qu'une évaluation déclenche — et si la technologie employée peut le porter (A.9).",
  'klassen.ansicht': 'Vue',
  'klassen.ansicht.klassen': 'Classes',
  'klassen.ansicht.matrix': 'Matrice',
  'klassen.katalog': 'K1 à K10',
  'klassen.katalogHinweis':
    'Chaque classe avec son nom, son objet et la condition qui la déclenche.',
  'klassen.ausloeser': 'Déclenchée',
  'klassen.matrix': 'Matrice des technologies',
  'klassen.matrixHinweis':
    "Quelle technologie peut porter quelle classe. Une exclusion n'est pas un avertissement mais un critère ; un cas compensable exige une mesure documentée (A.9.3).",
  'klassen.nurLesen':
    'Consultation sans droit de modification : la matrice relève du rôle Gouvernance.',
  'klassen.spalte.klasse': "Classe d'exigences",
  'klassen.bewertung.erfuellt': 'Satisfaite',
  'klassen.bewertung.kompensierbar': 'Compensable',
  'klassen.bewertung.nicht_erfuellbar': 'Non satisfiable',
  'klassen.feld.hinweis':
    'Ce champ décide si un processus peut être exploité avec cette technologie. La modification agit immédiatement sur tous les constats.',
  'klassen.feld.bewertung': 'Évaluation',
  'klassen.feld.begruendung': 'Justification',
  'klassen.feld.begruendungHilfe':
    "Obligatoire — une couleur sans phrase n'est pas une base de décision.",
  'klassen.feld.sichern': 'Enregistrer le champ',

  'klassen.befund.titel': "Classes d'exigences et technologie",
  'klassen.befund.hinweis':
    'Les classes que cet outil hérite de ses processus, face à ce que sa technologie peut porter.',
  'klassen.befund.leer':
    "Cet objet outil n'hérite encore d'aucune classe — il lui faut un lien vers un processus évalué.",
  'klassen.befund.getragen': 'Toutes portées',
  'klassen.befund.offen': '{anzahl} en suspens',
  'klassen.befund.offen.eine': 'Un cas en suspens',
  'klassen.befund.ausschluss': 'Exclusion',
  'klassen.art.erfuellt': 'Satisfaite',
  'klassen.art.kompensiert': 'Compensée',
  'klassen.art.kompensation_fehlt': 'Mesure manquante',
  'klassen.art.ausschluss': 'Exclusion',
  'klassen.art.ungeprueft': 'Non vérifiée',
  'klassen.schritt.erfuellt': 'Rien à faire — la technologie porte cette classe.',
  'klassen.schritt.kompensiert': 'Terminé : la mesure compensatoire est documentée.',
  'klassen.schritt.kompensation_fehlt':
    'À faire : décrire la mesure compensatoire, sinon le constat reste ouvert.',
  'klassen.schritt.ausschluss':
    "À décider : cette technologie ne peut pas porter la classe. Soit l'outil change de technologie, soit le processus est exploité sans lui.",
  'klassen.schritt.ungeprueft':
    "À faire : renseigner la technologie sur l'outil — sans elle, il n'y a rien à comparer.",
  'klassen.massnahme': 'Mesure',
  'klassen.kompensieren': 'Saisir la mesure',
  'klassen.kompensationAendern': 'Modifier la mesure',
  'klassen.kompensation.hinweis':
    "La technologie ne porte pas cette classe d'elle-même. Notez ce qui se passe à la place.",
  'klassen.kompensation.feld': 'Mesure compensatoire',
  'klassen.kompensation.feldHilfe':
    "Assez concrète pour qu'un contrôle puisse la suivre — « on y fait attention » n'est pas une mesure.",
  'klassen.kompensation.sichern': 'Enregistrer la mesure',
  'klassen.prozess.titel': "Technologie et classes d'exigences",
  'klassen.prozess.hinweis':
    "Le processus n'a pas de technologie propre — il voit les constats de ses outils (A.9.3).",
  'klassen.prozess.leer': "Aucun objet outil n'est encore rattaché à cet objet processus.",
  'klassen.prozess.getragen': 'Toutes les classes déclenchées sont portées.',

  'cockpit.titel': 'Cockpit',
  'cockpit.hinweis':
    "Chaque ligne appelle une action : un clic mène directement au module où l'entrée se traite.",
  'cockpit.leer': "Rien n'est ouvert sur cette ligne dans votre domaine.",
  'cockpit.anzahl': 'Ouvert',
  'cockpit.oeffnen': 'Consulter',
  'cockpit.zurueck': "Retour à la vue d'ensemble",
  'cockpit.fachbereich': 'Domaine',
  'cockpit.alleFachbereiche': 'Tous les domaines',
  'cockpit.eintrag': 'Entrée',
  'cockpit.hinweisSpalte': 'Indication',
  'cockpit.ziel': 'Cible',
  'cockpit.aggregat': 'Répartition',
  'cockpit.filterHinweis':
    "Le filtre figure dans l'adresse — cette vue peut donc être transmise. Il ne confère aucun droit.",
  'cockpit.gesamt': '{anzahl} en suspens',
  'cockpit.allesErledigt': 'Rien en suspens',
  'cockpit.nichtsOffen': 'Rien en suspens',
  'cockpit.leerHinweis': 'Rien à traiter sur cette ligne dans votre domaine.',
  'cockpit.eintraege': 'Cas individuels',
  'cockpit.modul.prozesse': 'Objet processus',
  'cockpit.modul.tools': 'Objet outil',
  'cockpit.modul.datenobjekte': 'Objet de données',
  'cockpit.modul.gates': 'Porte',
  'cockpit.modul.lenkung': 'Pilotage',
  'cockpit.verteilung.je_technologie': 'Répartition des tiers par technologie',
  'cockpit.verteilung.je_monat': 'Répartition des tiers par mois',
  'cockpit.verteilung.hinweis':
    'La couleur désigne le niveau, pas la série. Chaque nombre figure sur la barre.',
  'cockpit.verteilung.leer': "Aucun classement pour cet extrait pour l'instant.",
  'cockpit.verteilung.kategorie': 'Catégorie',
  'technologie.apps-script': 'Apps Script',
  'technologie.python-kubernetes': 'Python / Kubernetes',
  'technologie.bigquery-gcs': 'BigQuery / Cloud Storage',
  'technologie.appsheet': 'AppSheet',
  'technologie.unbekannt': 'Sans technologie',

  ja: 'Oui',
  nein: 'Non',
};

export const KATALOG: Record<Sprache, Record<Schluessel, string>> = { de, fr };

export function uebersetze(sprache: Sprache, schluessel: Schluessel): string {
  return KATALOG[sprache][schluessel] ?? KATALOG[STANDARDSPRACHE][schluessel] ?? schluessel;
}
