/**
 * V-RCH — Rechte im Blick.
 *
 * Spezifiziert in `docs/rechte-und-rollen.md`, vorgesehen in AP-11. Die
 * Vorgaenge sind hier hinterlegt, aber noch ohne Durchlauf: `vorgang()` meldet
 * sie damit als uebersprungen und nennt dabei das Arbeitspaket und das
 * erwartete Ergebnis. So steht die Luecke mit Adresse im Bericht, statt
 * unsichtbar zu bleiben — genau das, wofuer der Katalog gedacht ist.
 *
 * Beim Scharfschalten bekommt jeder Aufruf seinen Lauf und der Stand in
 * `docs/vorgaenge.md` wechselt auf „erfuellt". Beides zusammen, sonst schlaegt
 * die Selbstpruefung in `katalog.vorgang.ts` fehl.
 */

import { vorgang } from './hilfen';

// Der Auditor ist die Rolle, an der sich der Unterschied am schaerfsten zeigt:
// er darf alles sehen und nichts schreiben (NUR_LESEND in permissions.py).
vorgang('V-RCH-01');
vorgang('V-RCH-02');

// Lesen ja, schreiben nein — der Fall, der heute erst beim Speichern auffaellt.
vorgang('V-RCH-03');
vorgang('V-RCH-04');

vorgang('V-RCH-05');

// Herkunftssperre und Rechtesperre duerfen nicht gleich aussehen (E-52).
vorgang('V-RCH-06');

// Der wichtigste Vorgang: Rolle und Bereich sind orthogonal (P-App-3). Bis
// heute belegt das nur der Backend-Test, nie die Oberflaeche.
vorgang('V-RCH-07');

vorgang('V-RCH-08');
