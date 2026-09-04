"""Aufbauschritt 7: was sich nach der Bewertung noch geaendert hat.

Der interessanteste Zustand einer Governance-Anwendung ist nicht der saubere,
sondern der veraltete: eine Bewertung, die stimmte, und eine Datenlage, die
sich seither bewegt hat. A.8.4 unterscheidet drei Faelle, und das Cockpit nennt
sie beim Namen — aber nur, wenn es sie gibt. Hier entstehen sie: ein
umklassifiziertes Datenobjekt, eine gestiegene Ausfallfolge, eine neue
Attestierung. Alles unauffaellige Vorgaenge, jeder fuer sich richtig.

Dazu der Weg der Alt-Anwendungen aus A.16: bestaetigen, zuordnen, bewerten. Wer
ihn hinter sich hat, verschwindet aus dem Meldepfad; wer stehen bleibt, bleibt
sichtbar.
"""

from __future__ import annotations

from app.bestand.bewertungen import KATALOG
from app.bestand.kontext import Kontext
from app.bestand.prozesse import handelnder
from app.models.enums import Ausfallfolge, Datenkategorie, Zugriffsart
from app.schemas.prozess import ProzessAendern
from app.services import asset, erinnerung
from app.services import prozess as prozess_service


def datenlage_hat_sich_bewegt(kontext: Kontext) -> None:
    """Drei Aenderungen, die alte Bewertungsantworten ueberholen."""
    db = kontext.db

    # Auf den Fotos der Regalpflege sind regelmaessig Beschaeftigte zu sehen.
    # Die Stammdatenpflege ordnet das Datenobjekt nachtraeglich ein.
    with kontext.aktion(58, stunde=9):
        asset.aendere_datenobjekt(
            db,
            kontext.wer("teichmann"),
            kontext.datenobjekt("filialfotos"),
            {
                "kategorie": Datenkategorie.PERSONENBEZOGEN,
                "beschreibung": "Fotodokumentation der Flächenkontrolle. Auf den "
                "Aufnahmen sind regelmäßig Beschäftigte zu erkennen.",
            },
        )

    # Der Besuchsbericht ist Teil des Jahresgesprächs geworden; ein Ausfall
    # bleibt nicht mehr folgenlos.
    with kontext.aktion(52, stunde=10):
        prozess_service.aendern(
            db,
            kontext.wer(handelnder(kontext, KATALOG["filialbesuche"])),
            kontext.prozess("filialbesuche"),
            ProzessAendern(ausfallfolge=Ausfallfolge.GERING),
        )

    # Die Auditmappe verschickt die Nachverfolgung inzwischen selbsttätig.
    with kontext.aktion(46, stunde=11):
        asset.attestiere(
            db,
            kontext.wer("straub"),
            kontext.tool("auditmappe"),
            {
                "attest_entscheidung_ueber_personen": False,
                "attest_mensch_dazwischen": False,
                "attest_undeklarierte_quellen": False,
            },
        )


def neues_externes_ziel(kontext: Kontext) -> None:
    """Ein ergaenztes Ziel meldet sein Gate selbst (A.11, dritter Ausloeser)."""
    prozess = kontext.prozess("kundenkartenprogramm")
    ziele = [*prozess.erlaubte_externe_ziele, "auskunftsportal.betroffenenrechte.de"]
    with kontext.aktion(16, stunde=10):
        prozess_service.aendern(
            kontext.db,
            kontext.wer(handelnder(kontext, KATALOG["kundenkartenprogramm"])),
            prozess,
            ProzessAendern(erlaubte_externe_ziele=ziele),
        )


#: Was aus den vorgefundenen Anwendungen geworden ist (A.16).
#: Schluessel der externen Kennung auf ``(bestaetigt, Prozessobjekt)``.
ALTANWENDUNGEN: tuple[tuple[str, str, str | None, str], ...] = (
    # Weg zu Ende gegangen: bestaetigt, zugeordnet, ueber den Prozess bewertet.
    ("Wareneingangsabgleich (Altbestand)", "pohl", "wareneingang", "logistik"),
    # Zugeordnet, aber der Prozess ist noch nicht bewertet.
    ("Lieferantenanfragen-Formular", "vogler", "retourensteuerung-nonfood", "einkauf-nonfood"),
    # Bestaetigt, aber noch keinem Prozessobjekt zugeordnet.
    ("Personalkostenhochrechnung", "albrecht", None, "personal"),
)


def altanwendungen(kontext: Kontext) -> None:
    """Fuehrt einen Teil der vorgefundenen Anwendungen in den Rahmen."""
    db = kontext.db
    for name, owner, prozess_schluessel, bereich in ALTANWENDUNGEN:
        tool = _tool_nach_name(kontext, name)
        if tool is None:
            continue
        # Eine vorgefundene Anwendung gehoert zunaechst niemandem: kein
        # technischer Owner, keine Organisationseinheit. Schreiben darf auf sie
        # deshalb nur die Governance-Rolle — sie ordnet zu, danach uebernimmt
        # der Benannte. Genau diese Reihenfolge verlangt A.16.
        with kontext.aktion(120, stunde=9):
            asset.aendere_tool(
                db,
                kontext.wer("renner"),
                tool,
                {
                    "technischer_owner_user_id": kontext.person(owner).id,
                    "organisationseinheit_id": kontext.einheit(bereich).id,
                    "kategorie": "Auswertung",
                },
            )
            asset.bestaetige_tool(db, kontext.wer("renner"), tool)
        if prozess_schluessel is None:
            continue
        with kontext.aktion(115, stunde=10):
            asset.attestiere(
                db,
                kontext.wer(owner),
                tool,
                {
                    "attest_entscheidung_ueber_personen": False,
                    "attest_mensch_dazwischen": True,
                    "attest_undeklarierte_quellen": False,
                },
            )
        with kontext.aktion(112, stunde=11):
            asset.verknuepfe_tool_mit_prozess(
                db, kontext.wer(owner), tool, kontext.prozess(prozess_schluessel)
            )
            if prozess_schluessel == "wareneingang":
                asset.verknuepfe_tool_mit_datenobjekt(
                    db,
                    kontext.wer(owner),
                    tool,
                    kontext.datenobjekt("wareneingangsavise"),
                    Zugriffsart.LESEN,
                )


def _tool_nach_name(kontext: Kontext, name: str):
    from sqlalchemy import select

    from app.models.governance import ToolObjekt

    return kontext.db.execute(
        select(ToolObjekt).where(ToolObjekt.name == name)
    ).scalar_one_or_none()


def erinnerungen(kontext: Kontext) -> None:
    """Der geplante Lauf, der an ablaufende Erklaerungen erinnert (A.8.4).

    Er laeuft ohne Rueckdatierung: die Erinnerungen von heute sind die, die
    heute faellig sind. Genau so steht es im Posteingang der Betroffenen.
    """
    erinnerung.lauf(kontext.db)


def aufstieg_im_betrieb(kontext: Kontext) -> None:
    """Ein laufender Prozess steigt auf Tier 3 — und verliert damit seine Freigabe.

    Der haeufigste Weg dorthin ist kein Formfehler, sondern Alltag: der Prozess
    nimmt eine hoehere Datenkategorie auf, und die Neubewertung hebt ihn. Bis
    E-60 lief er danach unveraendert weiter, weil ``pruefe_aktivierung`` am
    Statuswechsel haengt und er den schon hinter sich hatte.

    Jetzt faellt er auf ``freigabe_ausstehend``, und der Gate-1-Vorgang
    entsteht von selbst. Der Bestand muss diesen Zustand zeigen: er ist der
    einzige, an dem sichtbar wird, dass „laeuft" und „darf laufen" zwei
    verschiedene Aussagen sind.
    """
    from dataclasses import replace

    from app.bestand.bewertungen import EINSTUFUNGEN, _speichere

    einstufung = next(e for e in EINSTUFUNGEN if e.prozess == "lieferantenbewertung-food")
    # Die Bewertung greift inzwischen auf die Laborbefunde der Eigenmarke zu
    # und entscheidet ueber Listung und Auslistung — aus einer Kennzahl ist
    # eine Entscheidung mit Folgen geworden.
    with kontext.aktion(24, stunde=9):
        prozess_service.aendern(
            kontext.db,
            kontext.wer(handelnder(kontext, KATALOG["lieferantenbewertung-food"])),
            kontext.prozess("lieferantenbewertung-food"),
            ProzessAendern(
                ausfallfolge=Ausfallfolge.KRITISCH,
                output="Listungsentscheidung je Lieferant, mit Auslistungsvorschlag",
            ),
        )
    # Die neue Datenlage widerspricht den alten Antworten — der Vorschlagsdienst
    # merkt das, und jede Abweichung ist zu begruenden (A.8.4). Genau dafuer
    # gibt es die Begruendung: sie steht danach in der Bewertung.
    begruendung = (
        "Die Abschriften werden seit der Umstellung je erfassender Person "
        "ausgewertet und im Zielgespräch besprochen."
    )
    _speichere(
        kontext,
        replace(
            einstufung,
            ds=3,
            mb=2,
            erneuert_vor=None,
            begruendungen={
                f"{block}{frage}": begruendung for block in range(1, 7) for frage in ("a", "b", "c")
            },
        ),
        vor_tagen=22,
    )
