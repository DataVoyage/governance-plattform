/**
 * V-TIE — Tier, komposites Risiko und Prozesskette.
 *
 * Spezifiziert in `docs/tier-als-lenkungsobjekt.md`, vorgesehen in AP-19. Noch
 * ohne Durchlauf: `vorgang()` meldet sie als uebersprungen und nennt dabei das
 * Arbeitspaket und das erwartete Ergebnis. So steht die Luecke mit Adresse im
 * Bericht, statt unsichtbar zu bleiben.
 *
 * Beim Scharfschalten bekommt jeder Aufruf seinen Lauf und der Stand in
 * `docs/vorgaenge.md` wechselt auf „erfuellt" — beides zusammen, sonst schlaegt
 * die Selbstpruefung in `katalog.vorgang.ts` fehl.
 */

import { vorgang } from './hilfen';

// Die erklaerte Erwartung ist der Ursprung, die Ableitung nur ihre Vorauswahl.
vorgang('V-TIE-01');
vorgang('V-TIE-02');

// Der tragende Vorgang der UR-Achse: von einer Rechnung gibt es keine
// Abweichung. Wer die Stufe aendern will, aendert die Erwartung (P1, E-65).
vorgang('V-TIE-03');

vorgang('V-TIE-04');

// Die Kette wirkt — und sie wirkt transitiv ueber die gesamte Abhaengigkeit.
vorgang('V-TIE-05');
vorgang('V-TIE-06');

// ... aber nur, wenn sich das Tier tatsaechlich aendert. Sonst stuerbe
// Agilitaet an Wartezeiten (P4, E-69).
vorgang('V-TIE-07');

// Der Erlaubnisrahmen folgt der Bewertung, nicht dem lebenden Feld (A.13.1).
vorgang('V-TIE-08');
