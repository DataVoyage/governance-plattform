"""Compliance-Zustände, ein Lenkungsvorgang, eine Kompensation, Schicht 2.

Damit trägt der Bestand jeden Zustand aus A.13.3 genau einmal — grün, gelb
(nicht zugeordnet, ergibt sich aus dem Werkzeug ohne Prozesskante) und rot —
und beide Wege in den Lenkungsprozess: die reguläre Stufe 1 aus einer roten
Meldung, und den unmittelbaren Sprung auf Stufe 2 bei einem Schicht-2-Verstoß
(A.13.5).
"""

from __future__ import annotations

from app.bestand.kontext import Kontext
from app.models.enums import (
    Ausfuehrungsidentitaet,
    Befundart,
    ComplianceFarbe,
    Schicht2Verbot,
)
from app.services import klassen, lenkung


def baue(kontext: Kontext) -> None:
    """Meldet die Zustände und erzeugt die beiden Lenkungswege."""
    toolowner = kontext.wer("toolowner")

    # Grün: der unauffällige Fall. Er kostet nichts und erzeugt keinen Vorgang.
    with kontext.aktion(vor_tagen=90, stunde=9):
        lenkung.melde_zustand(
            kontext.db,
            toolowner,
            kontext.tool("im_rahmen"),
            farbe=ComplianceFarbe.GRUEN,
            begruendung="Rahmen eingehalten; keine Abweichung gemessen.",
        )

    # Rot aus einer Rahmenabweichung: Stufe 1, mit Frist nach Tier.
    with kontext.aktion(vor_tagen=30, stunde=10):
        lenkung.melde_zustand(
            kontext.db,
            toolowner,
            kontext.tool("ausserhalb"),
            farbe=ComplianceFarbe.ROT,
            begruendung="Zugriff auf ein Datenobjekt, das der Prozess nicht erklärt.",
            abweichung_art="datenobjekte",
        )

    # Schicht 2: die Ausführungsidentität ist ein geteiltes Konto. Das ist
    # organisationsweit verboten und lässt sich durch keine Bewertung
    # freischalten — deshalb entfällt die erste Eskalationsstufe (A.13.5).
    with kontext.aktion(vor_tagen=20, stunde=11):
        asset_werte = {"ausfuehrungsidentitaet": Ausfuehrungsidentitaet.GETEILTES_KONTO}
        from app.services import asset

        asset.aendere_tool(kontext.db, toolowner, kontext.tool("zwei_kanten"), asset_werte)
        lenkung.melde_zustand(
            kontext.db,
            toolowner,
            kontext.tool("zwei_kanten"),
            farbe=ComplianceFarbe.ROT,
            begruendung="Läuft unter einem geteilten Konto.",
            schicht2_verbot=Schicht2Verbot.IDENTITAET_UMGANGEN,
        )

    # Eine dokumentierte Kompensation: der Weg aus A.9.3, wenn eine Technologie
    # eine ausgeloeste Klasse nur mit Zusatzmassnahme traegt. Welche Klasse das
    # ist, sagt der Befund — fest eintragen hiesse, die Matrix zu erraten.
    befund = klassen.pruefe_tool(kontext.db, kontext.tool("ausserhalb"))
    offen = [b for b in befund.befunde if b.art == Befundart.KOMPENSATION_FEHLT]
    if offen:
        with kontext.aktion(vor_tagen=15, stunde=14):
            klassen.setze_kompensation(
                kontext.db,
                toolowner,
                kontext.tool("ausserhalb"),
                offen[0].k_klasse,
                massnahme=(
                    "Zusätzliche Protokollauswertung; der Zugriff wird wöchentlich "
                    "gegen den erklärten Rahmen abgeglichen."
                ),
            )
