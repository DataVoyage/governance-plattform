"""Selbstverpflichtung, Gates und die vier Prozessstatus.

Am Ende dieses Schritts trägt der Bestand jeden Status genau einmal:

* **aktiv** — der Tier-2-Prozess und die Kette
* **entwurf** — der Prozess ohne Bewertung
* **freigabe_ausstehend** — der Tier-3-Prozess, nachdem eine Neubewertung ihn
  im laufenden Betrieb gehoben hat (E-60)
* **stillgelegt** — das Mittelglied der Kette, abgelöst

Dazu jede Gate-Art: eine erteilte Gate-1-Freigabe, ein offener Gate-1-Vorgang
aus dem Aufstieg, und ein offener Gate-2-Vorgang aus einem neu erklärten Ziel.
"""

from __future__ import annotations

from app.bestand.kontext import Kontext
from app.models.enums import (
    Gate2Ausloeser,
    GateStatus,
    GateTyp,
    SelbstverpflichtungTyp,
)
from app.schemas.prozess import ProzessAendern
from app.services import gate
from app.services import prozess as prozess_service
from app.services import selbstverpflichtung as verpflichtung

#: Prozesse, die in Betrieb gehen. „unbewertet" fehlt mit Absicht: ohne
#: Bewertung gibt es keine Aktivierung (A.8), und der Entwurf ist ein Zustand,
#: den der Bestand zeigen muss.
AKTIVIERT: tuple[str, ...] = ("kette1", "kette2", "kette3", "tier3", "tier2", "fremd", "tier1")


def _aussagen(typ: SelbstverpflichtungTyp, tier: int | None) -> dict:
    """Bestätigt jede bei diesem Tier verlangte Aussage (A.10.5)."""
    return {
        aussage.id: {"bestaetigt": True, "kommentar": "Im Lehrbestand bestätigt."}
        for aussage in verpflichtung.verlangte_aussagen(typ, tier)
    }


def lebenszyklus(kontext: Kontext) -> None:
    """Erklären, freigeben, in Betrieb nehmen — als ein Vorgang.

    Die drei Schritte stehen bewusst in **einem** Block: A.10.5 macht die
    vollständige Selbstverpflichtung und die Freigabe durch Gate 1 zur
    Bedingung der Aktivierung, und die Anwendung prüft das beim Statuswechsel.
    """
    governance = kontext.wer("governance")
    for nummer, schluessel in enumerate(AKTIVIERT):
        prozess = kontext.prozess(schluessel)
        bewertung = kontext.bewertungen[schluessel]
        eintrag = next(e for e in _prozesse() if e.schluessel == schluessel)
        akteur = kontext.wer(eintrag.owner)

        with kontext.aktion(vor_tagen=300 - nummer * 2, stunde=11):
            verpflichtung.abgeben(
                kontext.db,
                akteur,
                typ=SelbstverpflichtungTyp.PROZESSEIGNER,
                prozess=prozess,
                aussagen=_aussagen(SelbstverpflichtungTyp.PROZESSEIGNER, bewertung.tier),
            )
            if bewertung.tier >= 3:
                vorgang = gate.einreichen(
                    kontext.db,
                    akteur,
                    prozess,
                    gate_typ=GateTyp.GATE_1,
                    begruendung=f"Erstfreigabe nach Tier {bewertung.tier}.",
                )
                gate.entscheiden(
                    kontext.db,
                    governance,
                    vorgang,
                    status=GateStatus.FREIGEGEBEN,
                    kommentar="Freigegeben; die Auflagen aus dem Tier sind umgesetzt.",
                )
            prozess_service.aendern(kontext.db, akteur, prozess, ProzessAendern(status="aktiv"))

    # Das Mittelglied wird abgelöst — der vierte Status, und zugleich der
    # Beleg, dass eine Stilllegung die Kette nicht zerreisst.
    with kontext.aktion(vor_tagen=280, stunde=13):
        prozess_service.aendern(
            kontext.db,
            kontext.wer("prozessowner"),
            kontext.prozess("kette2"),
            ProzessAendern(status="stillgelegt"),
        )


def aufstieg(kontext: Kontext) -> None:
    """Ein laufender Prozess steigt auf Tier 3 und verliert seine Freigabe.

    Der Fall aus E-60: „läuft" und „darf laufen" sind zwei Aussagen. Der
    Tier-2-Prozess nimmt eine höhere Datenkategorie auf, die Neubewertung hebt
    ihn — und der Gate-1-Vorgang entsteht von selbst.
    """
    from app.bestand.bewertungen import antworten_aus_profil
    from app.services import ableitung
    from app.services import bewertung as bewertung_service

    prozess = kontext.prozess("tier2")
    with kontext.aktion(vor_tagen=120, stunde=9):
        prozess_service.aendern(
            kontext.db,
            kontext.wer("prozessowner"),
            prozess,
            ProzessAendern(
                input_datenobjekt_ids=[
                    kontext.datenobjekt("intern").id,
                    kontext.datenobjekt("besondere").id,
                ]
            ),
        )
    profil = {
        "ki": 0,
        "ds": 3,
        "mb": 2,
        "it": 2,
        "rg": 0,
        "ur": ableitung.leite_kritikalitaet_ab(prozess),
    }
    antworten = antworten_aus_profil(profil)
    with kontext.aktion(vor_tagen=118, stunde=10):
        bewertung_service.speichere(
            kontext.db,
            kontext.wer("prozessowner"),
            prozess,
            antworten,
            begruendungen=dict.fromkeys(
                antworten,
                "Die Auswertung erfolgt seit der Umstellung je Fahrerin und Fahrer.",
            ),
        )


def gate2(kontext: Kontext) -> None:
    """Ein neu erklärtes externes Ziel am laufenden Prozess.

    Der dritte Gate-2-Auslöser meldet sich selbst (A.11): wer am aktiven
    Prozessobjekt ein Ziel ergänzt, erzeugt den Vorgang beim Speichern.
    """
    with kontext.aktion(vor_tagen=60, stunde=14):
        prozess_service.aendern(
            kontext.db,
            kontext.wer("prozessowner"),
            kontext.prozess("kette3"),
            ProzessAendern(
                erlaubte_externe_ziele=["https://zoll.beispiel-ag.de/anmeldung"],
            ),
        )
    # Sicherheitshalber ausdrücklich: entstand der Vorgang nicht von selbst,
    # fehlt dem Bestand ein Fall, und das soll auffallen.
    offen = gate.offener_vorgang(kontext.db, kontext.prozess("kette3").id, GateTyp.GATE_2)
    if offen is None:
        with kontext.aktion(vor_tagen=59, stunde=9):
            gate.einreichen(
                kontext.db,
                kontext.wer("prozessowner"),
                kontext.prozess("kette3"),
                gate_typ=GateTyp.GATE_2,
                ausloeser=Gate2Ausloeser.NEUES_EXTERNES_ZIEL,
                begruendung="Neues externes Ziel erklärt.",
            )


def _prozesse():
    from app.lehrbestand.prozesse import PROZESSE

    return PROZESSE
