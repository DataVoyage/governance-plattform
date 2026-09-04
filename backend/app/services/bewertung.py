"""Bewertungs-Modul (Architektur 8.2) — Baumdurchlauf, Tier und K-Klassen.

Es gibt genau eine Implementierung dieser Logik. Der Wizard in der Oberflaeche,
die Historie und spaeter die Governance-Query-API (Architektur 7.3) fragen alle
dieselben Funktionen — eine zweite, abweichende Berechnung waere der sicherste
Weg zu widerspruechlichen Auskuenften.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import Principal, verlange
from app.models.base import now_utc
from app.models.enums import AlarmTyp, ProzessStatus
from app.models.governance import Alarm, Bewertung, Prozessobjekt
from app.services import ableitung, konfiguration, vorschlag
from app.services.bewertungsbaum import (
    BAUM,
    FRAGE_JE_ID,
    KI_VERBOTEN,
    Block,
    Frage,
    Themenblock,
)
from app.services.changelog import protokolliere_erstellung
from app.services.prozess import Ungueltig, darf_schreiben


@dataclass
class Baumstand:
    """Zwischenstand eines Durchlaufs — bewusst ohne Tier-Anzeige.

    Der Wizard zeigt den Zwischenstand nicht an, um vorzeitige Selbstzensur der
    Antworten zu vermeiden (Architektur 8.2). Deshalb traegt dieses Objekt zwar
    die ermittelten Stufen, wird aber erst nach Abschluss nach aussen gegeben.
    """

    stufen: dict[Block, int] = field(default_factory=dict)
    naechste_frage: Frage | None = None
    abgeschlossen: bool = False
    verboten: bool = False


def _werte_block_aus(
    themenblock: Themenblock, antworten: dict[str, bool]
) -> tuple[int | None, Frage | None, bool]:
    """Liefert ``(stufe, offene_frage, verboten)`` fuer einen Themenblock."""
    tentativ = 0
    for frage in themenblock.fragen:
        if frage.id not in antworten:
            return None, frage, False
        antwort = antworten[frage.id]
        if frage.abbruch_bei_nein:
            if not antwort:
                return 0, None, False
            tentativ = frage.stufe_bei_ja
            continue
        if antwort:
            return frage.stufe_bei_ja, None, frage.verbot_bei_ja
    return tentativ, None, False


def durchlaufe(antworten: dict[str, bool]) -> Baumstand:
    """Fuehrt den Baum bis zur naechsten offenen Frage oder bis zum Ende.

    Der Durchlauf ist zustandslos: aus denselben Antworten folgt immer derselbe
    Stand. Damit braucht der Wizard keine serverseitige Sitzung, und die
    Reihenfolge bleibt trotzdem serverseitig festgelegt.

    Es gibt **einen** Ausgang. Bis E-64 kannte der Baum eine schnelle Variante,
    die beim ersten Tier-3-Treffer abbrach; sie hinterliess eine Bewertung ohne
    K-Klassen und mit Nullen in den nicht durchlaufenen Dimensionen. Eine solche
    Bewertung konnte eine vollstaendige verdraengen und dabei still loeschen,
    was schon beantwortet war. Der Zeitgewinn war ein Scheingewinn: was die
    Anwendung ableiten kann, schlaegt sie ohnehin vor (A.8.4).
    """
    stand = Baumstand()
    for themenblock in BAUM:
        stufe, offene_frage, verboten = _werte_block_aus(themenblock, antworten)
        if verboten:
            stand.stufen[themenblock.block] = KI_VERBOTEN
            stand.verboten = True
            stand.abgeschlossen = True
            return stand
        if offene_frage is not None:
            stand.naechste_frage = offene_frage
            return stand
        assert stufe is not None
        stand.stufen[themenblock.block] = stufe
    stand.abgeschlossen = True
    return stand


def profil(stand: Baumstand) -> dict[str, int]:
    """Das Sechser-Profil; nicht durchlaufene Bloecke stehen auf 0."""
    return {block.value: stand.stufen.get(block, 0) for block in Block}


def tier(stand: Baumstand) -> int:
    """Tier 1 bis 3 als hoechste erreichte Stufe, mindestens 1."""
    if stand.verboten:
        return 3
    erreicht = [s for s in stand.stufen.values() if s > 0]
    return max(1, min(3, max(erreicht, default=1)))


# --- K-Klassen (Leitdokument A.9.2) --------------------------------------
#
# Jede Klasse haengt an genau einer nachvollziehbaren Bedingung ueber dem
# Profil. Die Ableitung ist reine Rechnung ohne Datenbankzugriff, damit sie an
# jeder Stelle — Wizard, Historie, Query-API — identisch ist.

K_KLASSEN_BESCHREIBUNG: dict[str, str] = {
    "K1": "Dokumentationspflicht des Prozessobjekts",
    "K2": "Selbstverpflichtung des Prozesseigners",
    "K3": "Benannter technischer Owner mit Betriebsverantwortung",
    "K4": "Datenschutz-Folgenabschätzung",
    "K5": "Zugriffs- und Rechtekonzept",
    "K6": "KI-Transparenz und -Dokumentation nach EU AI Act",
    "K7": "Mitbestimmungsverfahren einleiten",
    "K8": "Regulatorischer Nachweis und Aufbewahrung",
    "K9": "Notfall- und Wiederanlaufkonzept",
    "K10": "Gate-2-Pflicht vor Inbetriebnahme",
}

#: Je Klasse ein Satz, der sagt, was zu tun ist — nicht, was die Bedingung war.
#: Eine Ergebnisseite, die nur „K4" anzeigt, verlagert die Uebersetzungsarbeit
#: auf den Leser; genau das soll sie nicht (Architektur 9.1).
K_KLASSEN_ERKLAERUNG: dict[str, str] = {
    "K1": (
        "Das Prozessobjekt ist mit Zweck, Ablauf und beteiligten Daten im Verzeichnis "
        "zu führen und aktuell zu halten."
    ),
    "K2": (
        "Der Prozesseigner gibt die Selbstverpflichtung nach A.10.2 ab und bestätigt sie jährlich."
    ),
    "K3": (
        "Für den Betrieb ist ein technischer Owner namentlich zu benennen, der die "
        "Verfügbarkeit und die Änderungen verantwortet."
    ),
    "K4": (
        "Vor der Inbetriebnahme ist eine Datenschutz-Folgenabschätzung nach Art. 35 "
        "DSGVO durchzuführen und mit dem Datenschutzbeauftragten abzustimmen."
    ),
    "K5": (
        "Wer auf welche Daten zugreifen darf, ist schriftlich festzulegen und "
        "mindestens jährlich zu überprüfen."
    ),
    "K6": (
        "Der KI-Einsatz ist nach EU AI Act zu dokumentieren; Betroffene sind über "
        "die Beteiligung eines KI-Systems zu informieren."
    ),
    "K7": (
        "Der Betriebsrat ist vor der Inbetriebnahme zu beteiligen; ohne abgeschlossenes "
        "Verfahren darf der Prozess nicht produktiv gehen."
    ),
    "K8": (
        "Ergebnisse und Änderungen sind revisionssicher aufzubewahren und der "
        "internen Revision auf Anforderung vorzulegen."
    ),
    "K9": (
        "Für den Ausfall ist ein Wiederanlaufplan zu hinterlegen und die zulässige "
        "Ausfallzeit zu benennen."
    ),
    "K10": (
        "Vor der Inbetriebnahme ist Gate 2 zu durchlaufen; die Freigabe erteilt die "
        "Governance-Rolle."
    ),
}


#: Die Auflagen je Tier aus Leitdokument A.8.6. Sie gelten kumulativ: Tier 3
#: traegt auch die Auflagen von Tier 2 und 1.
#:
#: Anders als die K-Klassen haengen sie nicht am Profil, sondern allein am
#: erreichten Tier. Beide stehen auf der Ergebnisseite nebeneinander, weil sie
#: verschiedene Fragen beantworten: die K-Klassen sagen, **was** dieser Prozess
#: wegen seiner Eigenschaften braucht, die Auflagen sagen, **wie streng** er
#: insgesamt gefuehrt wird.
TIER_AUFLAGEN: dict[int, tuple[str, ...]] = {
    1: (
        "Registrierung im Verzeichnis der Prozessobjekte.",
        "Selbstverpflichtung des Prozesseigners, jährlich zu bestätigen.",
        "Änderungen am Prozessobjekt werden protokolliert.",
    ),
    2: (
        "Benannter technischer Owner mit Betriebsverantwortung.",
        "Zugriffs- und Rechtekonzept, mindestens jährlich überprüft.",
        "Aufnahme in die regelmäßige Governance-Durchsicht.",
    ),
    3: (
        "Die Bewertung verfällt nach einem Jahr und ist zu erneuern.",
        "Freigabe durch die Governance-Rolle vor der Inbetriebnahme.",
        "Laufende Beobachtung im Cockpit; Abweichungen lösen einen Lenkungsvorgang aus.",
    ),
}


def auflagen(tier_wert: int) -> list[str]:
    """Die kumulierten Auflagen bis zum erreichten Tier."""
    return [satz for stufe in range(1, tier_wert + 1) for satz in TIER_AUFLAGEN.get(stufe, ())]


def leite_k_klassen_ab(werte: dict[str, int]) -> list[str]:
    """Leitet die ausgeloesten Massnahmenklassen aus dem Profil ab."""
    ki = werte.get("ki", 0)
    ds = werte.get("ds", 0)
    mb = werte.get("mb", 0)
    it = werte.get("it", 0)
    rg = werte.get("rg", 0)
    ur = werte.get("ur", 0)
    hoechste = max(ki, ds, mb, it, rg, ur)

    bedingungen: dict[str, bool] = {
        # Grundpflichten: gelten ab dem ersten Tier.
        "K1": True,
        "K2": True,
        # Ab Tier 2 braucht der Betrieb einen benannten Verantwortlichen.
        "K3": hoechste >= 2,
        "K4": ds >= 3,
        "K5": ds >= 2 or it >= 2,
        "K6": ki >= 1,
        "K7": mb >= 1,
        "K8": rg >= 2,
        "K9": ur >= 2,
        # Gate 2 vor Inbetriebnahme: nur bei hoechster Stufe in KI,
        # IT-Sicherheit oder unternehmerischem Risiko.
        "K10": ki >= 3 or it >= 3 or ur >= 3,
    }
    return [klasse for klasse, ausgeloest in bedingungen.items() if ausgeloest]


# --- Persistenz -----------------------------------------------------------


def pruefe_antworten(antworten: dict[str, bool]) -> None:
    unbekannt = sorted(set(antworten) - set(FRAGE_JE_ID))
    if unbekannt:
        raise Ungueltig(f"Unbekannte Frage-IDs: {', '.join(unbekannt)}")


def pruefe_begruendungen(
    vorschlaege: dict[str, vorschlag.Vorschlag],
    antworten: dict[str, bool],
    begruendungen: dict[str, str],
) -> dict[str, str]:
    """Jede Abweichung vom Vorschlag braucht einen Satz — sonst kein Schritt.

    Die Pruefung sitzt bewusst schon im Wizard-Schritt und nicht erst beim
    Speichern. Wer erst am Ende erfaehrt, dass Frage 2b eine Begruendung
    braucht, muesste sich an eine Entscheidung von vor fuenf Bildschirmen
    erinnern.

    Zurueck kommen die Begruendungen, die tatsaechlich zu einer Abweichung
    gehoeren. Ein Satz zu einer Frage, die am Ende doch nicht abweicht — etwa
    weil die Antwort zurueckgenommen wurde —, wird nicht mitgespeichert: er
    wuerde eine Abweichung dokumentieren, die es nicht gibt.
    """
    behalten: dict[str, str] = {}
    fehlend: list[str] = []
    for abweichung in vorschlag.abweichungen(vorschlaege, antworten):
        text = (begruendungen.get(abweichung.frage_id) or "").strip()
        if not text:
            fehlend.append(abweichung.frage_id)
        else:
            behalten[abweichung.frage_id] = text
    if fehlend:
        raise Ungueltig(
            "Die Antwort weicht vom abgeleiteten Vorschlag ab. Bitte begründen Sie das "
            f"für {'Frage' if len(fehlend) == 1 else 'die Fragen'} {', '.join(sorted(fehlend))}."
        )
    return behalten


def darf_bewerten(db: Session, principal: Principal, prozess: Prozessobjekt) -> bool:
    """Bewerten darf der Prozess-Owner im eigenen Bereich oder die Governance.

    Der Prozess-Umsetzer ist hier bewusst aussen vor (Matrix 5.3): er pflegt
    die lokale Abweichung, aber die Bewertung bleibt beim Prozessgeber.
    """
    return darf_schreiben(db, principal, prozess.prozessgeber_org_id)


def gueltig_bis(db: Session, tier_wert: int, ab: datetime) -> datetime | None:
    """Ab Tier 3 gilt die jaehrliche Erneuerungspflicht (Leitdokument A.10.5)."""
    if tier_wert < 3:
        return None
    tage = konfiguration.lies_int(db, "bewertung_gueltigkeit_tage_tier3")
    return ab + timedelta(days=tage)


def speichere(
    db: Session,
    principal: Principal,
    prozess: Prozessobjekt,
    antworten: dict[str, bool],
    begruendungen: dict[str, str] | None = None,
) -> Bewertung | Alarm:
    """Schliesst einen Durchlauf ab und legt eine neue Bewertung an.

    Bei einem Treffer auf den Verbotstatbestand (Schritt 1b) wird **keine**
    Bewertung gespeichert, sondern ein Governance-Alarm erzeugt — das
    Prozessobjekt bleibt damit unbewertet und faellt im Cockpit auf.
    """
    verlange(
        darf_bewerten(db, principal, prozess),
        "Bewerten darf der Prozess-Owner im eigenen Bereich oder die Governance-Rolle",
    )
    pruefe_antworten(antworten)
    vorschlaege = vorschlag.fuer_prozess(prozess)
    abweichende = pruefe_begruendungen(vorschlaege, antworten, begruendungen or {})
    stand = durchlaufe(antworten)
    if not stand.abgeschlossen:
        raise Ungueltig(
            f"Der Baumdurchlauf ist nicht abgeschlossen; offen ist Frage "
            f"{stand.naechste_frage.id if stand.naechste_frage else '?'}"
        )

    if stand.verboten:
        alarm = Alarm(
            typ=AlarmTyp.KI_VERBOTSTATBESTAND,
            prozessobjekt_id=prozess.id,
            beschreibung=(
                "Der Bewertungsdurchlauf hat einen nach EU AI Act verbotenen "
                "Tatbestand ergeben (Schritt 1b). Es wurde keine Bewertung "
                "gespeichert."
            ),
            ausgeloest_von=principal.user_id,
        )
        db.add(alarm)
        db.flush()
        protokolliere_erstellung(db, alarm, akteur_user_id=principal.user_id)
        return alarm

    werte = profil(stand)
    tier_wert = tier(stand)
    zeitpunkt = now_utc()
    bewertung = Bewertung(
        prozessobjekt_id=prozess.id,
        ki_stufe=werte["ki"],
        ds_stufe=werte["ds"],
        mb_stufe=werte["mb"],
        it_stufe=werte["it"],
        rg_stufe=werte["rg"],
        ur_stufe=werte["ur"],
        tier=tier_wert,
        gesperrt=False,
        ausgeloeste_k_klassen=leite_k_klassen_ab(werte),
        antworten=dict(antworten),
        vorschlaege=vorschlag.werte(vorschlaege),
        abweichungen=abweichende,
        bewertet_von=principal.user_id,
        bewertet_am=zeitpunkt,
        gueltig_bis=gueltig_bis(db, tier_wert, zeitpunkt),
    )
    db.add(bewertung)
    db.flush()
    db.refresh(prozess)
    ableitung.aktualisiere_kette(prozess)
    _pruefe_freigabe_nach_neubewertung(db, principal, prozess, tier_wert)
    db.flush()
    protokolliere_erstellung(db, bewertung, akteur_user_id=principal.user_id)
    return bewertung


def _pruefe_freigabe_nach_neubewertung(
    db: Session, principal: Principal, prozess: Prozessobjekt, tier_wert: int
) -> None:
    """Steigt ein laufender Prozess auf Tier 3, entfaellt seine Freigabe.

    ``pruefe_aktivierung`` haengt am Statuswechsel — wer schon aktiv ist, kommt
    nie wieder daran vorbei. Ein Prozess konnte damit von Tier 1 auf Tier 3
    wechseln und ohne Gate weiterlaufen (E-60). Gate 1 ist die
    Tier-3-Erstfreigabe (A.11); dass sie spaeter faellig wird als ueblich,
    aendert nichts daran, dass sie faellig ist.

    Der Vorgang entsteht hier von selbst — dieselbe Bauart wie beim dritten
    Gate-2-Ausloeser (A.11): wer die Bewertung abgibt, meldet damit den Anlass.
    Ihn zusaetzlich zum Einreichen aufzufordern hiesse, ihm die Regel
    aufzubuerden, die die Anwendung kennt.

    Unterhalb von Tier 3 passiert nichts: A.11 sieht fuer Tier 1 und 2
    ausdruecklich kein Gate vor, und einen laufenden Prozess dafuer anzuhalten
    waere eine Bremse, die das Konzept nicht will.
    """
    from app.models.enums import GateTyp
    from app.services import gate

    if prozess.status != ProzessStatus.AKTIV or tier_wert < 3:
        return
    if gate.ist_freigegeben(db, prozess.id, GateTyp.GATE_1):
        # Schon freigegeben: die Freigabe gilt dem Rahmen, nicht dem Stand
        # (A.11, Envelope-Modell). Die Selbstverpflichtung ist trotzdem neu
        # abzugeben — sie haengt an der Bewertung (A.10.4).
        return
    prozess.status = ProzessStatus.FREIGABE_AUSSTEHEND
    db.flush()
    if gate.offener_vorgang(db, prozess.id, GateTyp.GATE_1) is None:
        gate.einreichen(
            db,
            principal,
            prozess,
            gate_typ=GateTyp.GATE_1,
            begruendung=(
                f"Automatisch: die Neubewertung hebt den laufenden Prozess auf Tier "
                f"{tier_wert}. Die Erstfreigabe nach A.11 steht damit aus."
            ),
        )


def historie(db: Session, prozess_id: uuid.UUID) -> list[Bewertung]:
    """Alle Bewertungen, neueste zuerst — vorherige bleiben unveraendert."""
    return list(
        db.execute(
            select(Bewertung)
            .where(Bewertung.prozessobjekt_id == prozess_id)
            .order_by(Bewertung.bewertet_am.desc(), Bewertung.erstellt_am.desc())
        ).scalars()
    )


def aktuelle(db: Session, prozess_id: uuid.UUID) -> Bewertung | None:
    treffer = historie(db, prozess_id)
    return treffer[0] if treffer else None


def ist_abgelaufen(bewertung: Bewertung, jetzt: datetime | None = None) -> bool:
    if bewertung.gueltig_bis is None:
        return False
    zeitpunkt = jetzt or datetime.now(UTC)
    frist = bewertung.gueltig_bis
    if frist.tzinfo is None:
        frist = frist.replace(tzinfo=UTC)
    return frist < zeitpunkt
