"""Compliance-Zustand und Lenkungs-Modul (Architektur 8.6, Leitdokument A.13).

Der Compliance-Zustand ist eine **Zeitreihe** je Tool-Objekt: jede Feststellung
erzeugt einen neuen Eintrag, der aktuelle Zustand ist immer der neueste. Nichts
wird ueberschrieben — sonst waere der Verlauf einer Abweichung nicht mehr
nachvollziehbar.

Eine Rahmenueberschreitung erzeugt automatisch einen Lenkungsvorgang in
Eskalationsstufe 1 mit der tier-abhaengigen Frist. Laeuft die Frist ab, ohne
dass der Zustand wieder gruen wird, rueckt der Vorgang in Stufe 2
(Benachrichtigung der Fuehrungskraft) und danach in Stufe 3 (Kennzeichnung fuer
eine technische Massnahme). Der eigentliche Zugriffsentzug erfolgt ausserhalb
dieser Anwendung, in der jeweiligen technischen Plattform.

Jede der drei zulaessigen Aufloesungen aus A.13.6 ist eine explizite Aktion,
keine Interpretation eines Freitextkommentars.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import Principal, verlange
from app.models.base import now_utc
from app.models.enums import (
    AssetStatus,
    Aufloesungsart,
    ComplianceFarbe,
    LenkungStatus,
    Schicht2Verbot,
)
from app.models.governance import (
    Benachrichtigung,
    Bewertung,
    ComplianceZustand,
    Lenkungsvorgang,
    ToolObjekt,
)
from app.models.organisation import User
from app.services import konfiguration
from app.services.asset import darf_tool_lesen, darf_tool_schreiben, erbe_klassifikation
from app.services.changelog import (
    protokolliere_aenderung,
    protokolliere_erstellung,
    snapshot,
)
from app.services.prozess import NichtGefunden, Ungueltig

#: Hoechste Eskalationsstufe: Kennzeichnung fuer eine technische Massnahme.
HOECHSTE_STUFE = 3

#: Namen der drei Aufloesungen fuer die Zeitreihe. Der Eintrag, den eine
#: Aufloesung hinterlaesst, steht spaeter auf dem Bildschirm — dort gehoert
#: kein technischer Schluessel hin.
AUFLOESUNG_TEXT: dict[str, str] = {
    Aufloesungsart.ANPASSEN: "angepasst",
    Aufloesungsart.RAHMEN_ERWEITERN: "Rahmen erweitert",
    Aufloesungsart.STILLLEGEN: "stillgelegt",
}

ANLASS_ESKALATION = "lenkungsvorgang_eskaliert"
ANLASS_LENKUNG_NEU = "lenkungsvorgang_eroeffnet"


def _als_utc(zeitpunkt: datetime | None) -> datetime | None:
    if zeitpunkt is None:
        return None
    return zeitpunkt if zeitpunkt.tzinfo is not None else zeitpunkt.replace(tzinfo=UTC)


# --- Compliance-Zustand ---------------------------------------------------


def aktueller_zustand(db: Session, tool_id: uuid.UUID) -> ComplianceZustand | None:
    """Der neueste Eintrag der Zeitreihe."""
    return db.execute(
        select(ComplianceZustand)
        .where(ComplianceZustand.tool_objekt_id == tool_id)
        .order_by(ComplianceZustand.festgestellt_am.desc(), ComplianceZustand.erstellt_am.desc())
        .limit(1)
    ).scalar_one_or_none()


def verlauf(db: Session, tool_id: uuid.UUID) -> list[ComplianceZustand]:
    return list(
        db.execute(
            select(ComplianceZustand)
            .where(ComplianceZustand.tool_objekt_id == tool_id)
            .order_by(
                ComplianceZustand.festgestellt_am.desc(), ComplianceZustand.erstellt_am.desc()
            )
        ).scalars()
    )


def melde_zustand(
    db: Session,
    principal: Principal,
    tool: ToolObjekt,
    *,
    farbe: ComplianceFarbe,
    begruendung: str = "",
    abweichung_art: str | None = None,
    schicht2_verbot: str | None = None,
    jetzt: datetime | None = None,
) -> tuple[ComplianceZustand, Lenkungsvorgang | None]:
    """Traegt einen Zustand in die Zeitreihe ein.

    Bei ``rot`` entsteht automatisch ein Lenkungsvorgang — in Stufe 1, oder bei
    einem Verstoss gegen Schicht 2 unmittelbar in Stufe 2 (A.13.5: „Bei
    Verletzung von Schicht 2 entfaellt Stufe 1"). Ist fuer dieses Tool schon
    einer offen, wird er nicht verdoppelt: eine zweite Meldung derselben
    Abweichung ist dieselbe Abweichung. Ein Schicht-2-Verstoss hebt einen
    laufenden Stufe-1-Vorgang aber sofort auf Stufe 2 — sonst haette die
    Reihenfolge der Meldungen ueber die Schwere entschieden.
    """
    verlange(
        darf_tool_schreiben(db, principal, tool),
        "Compliance-Meldungen erfasst der technische Owner oder die Governance-Rolle",
    )
    if schicht2_verbot is not None and schicht2_verbot not in set(Schicht2Verbot):
        raise Ungueltig(f"Unzulässiges Schicht-2-Verbot: {schicht2_verbot}")
    if schicht2_verbot is not None and farbe != ComplianceFarbe.ROT:
        raise Ungueltig(
            "Ein Verstoß gegen Schicht 2 ist kein gelber Befund — er ist rot, "
            "weil ihn keine Bewertung freischaltet"
        )
    zeitpunkt = jetzt or now_utc()
    zustand = ComplianceZustand(
        tool_objekt_id=tool.id,
        farbe=farbe,
        begruendung=begruendung,
        abweichung_art=abweichung_art,
        schicht2_verbot=schicht2_verbot,
        festgestellt_am=zeitpunkt,
        festgestellt_von=principal.user_id,
    )
    db.add(zustand)
    db.flush()
    protokolliere_erstellung(db, zustand, akteur_user_id=principal.user_id)

    if farbe != ComplianceFarbe.ROT:
        return zustand, None
    stufe = 2 if schicht2_verbot is not None else 1
    bestehend = offener_vorgang(db, tool.id)
    if bestehend is not None:
        if stufe > bestehend.eskalationsstufe:
            _hebe_auf_stufe(db, principal, bestehend, tool, zustand, zeitpunkt)
        return zustand, bestehend
    return zustand, _eroeffne_lenkungsvorgang(db, principal, tool, zustand, zeitpunkt, stufe=stufe)


def _hebe_auf_stufe(
    db: Session,
    principal: Principal,
    vorgang: Lenkungsvorgang,
    tool: ToolObjekt,
    zustand: ComplianceZustand,
    zeitpunkt: datetime,
) -> None:
    """Hebt einen laufenden Vorgang wegen eines Schicht-2-Verstosses auf Stufe 2."""
    vorher = snapshot(vorgang)
    vorgang.eskalationsstufe = 2
    vorgang.schicht2_verbot = zustand.schicht2_verbot
    vorgang.frist = frist_fuer(db, tool, zeitpunkt, stufe=2)
    db.flush()
    protokolliere_aenderung(
        db,
        vorgang,
        vorher,
        akteur_user_id=principal.user_id,
        beschreibung="Verstoß gegen Schicht 2 — Stufe 1 entfällt",
    )
    empfaenger = _eskalationsempfaenger(db, vorgang)
    if empfaenger is not None:
        _benachrichtige(
            db,
            vorgang,
            empfaenger,
            ANLASS_ESKALATION,
            "Lenkungsvorgang in Eskalationsstufe 2",
            "Für das Tool-Objekt wurde ein Verstoß gegen ein organisationsweites "
            "Verbot gemeldet. Solche Fälle beginnen ohne erste Stufe.",
        )


# --- Lenkungsvorgang ------------------------------------------------------


def arbeitstage_addieren(ab: datetime, tage: int) -> datetime:
    """Zaehlt ``tage`` Arbeitstage ab ``ab``, Samstag und Sonntag uebersprungen.

    A.13.5 rechnet in Arbeitstagen, nicht in Kalendertagen. Der Unterschied ist
    kein Detail: fuenf Kalendertage ueber ein Wochenende sind drei Arbeitstage,
    und eine Frist, die am Samstag ablaeuft, laeuft praktisch am Freitag ab.

    Feiertage bleiben aussen vor. Ein Feiertagskalender ist landesabhaengig,
    und die Anwendung laeuft in mehreren Laendern — eine halbe Loesung waere
    hier schlechter als eine erklaerte Vereinfachung. Ein Vorgang gewinnt
    dadurch hoechstens einen Tag; die Fristen sind nicht auf den Tag genau
    gedacht, sondern als Eskalationsdruck.
    """
    zeitpunkt = ab
    verbleibend = max(0, tage)
    while verbleibend > 0:
        zeitpunkt += timedelta(days=1)
        if zeitpunkt.weekday() < 5:
            verbleibend -= 1
    return zeitpunkt


def frist_fuer(db: Session, tool: ToolObjekt, ab: datetime, stufe: int = 1) -> datetime:
    """Tier- und stufenabhaengige Frist (A.13.5), Tier aus der Vererbung."""
    tier = erbe_klassifikation(tool).tier or 1
    return arbeitstage_addieren(ab, konfiguration.lenkungsfrist_tage(db, tier, stufe))


def _betroffener_owner(tool: ToolObjekt) -> uuid.UUID | None:
    if tool.technischer_owner_user_id is not None:
        return tool.technischer_owner_user_id
    for prozess in tool.prozessobjekte:
        return prozess.owner_user_id
    return None


def _eroeffne_lenkungsvorgang(
    db: Session,
    principal: Principal,
    tool: ToolObjekt,
    zustand: ComplianceZustand,
    zeitpunkt: datetime,
    *,
    stufe: int = 1,
) -> Lenkungsvorgang:
    vorgang = Lenkungsvorgang(
        tool_objekt_id=tool.id,
        compliance_zustand_id=zustand.id,
        eskalationsstufe=stufe,
        schicht2_verbot=zustand.schicht2_verbot,
        frist=frist_fuer(db, tool, zeitpunkt, stufe=stufe),
        zugewiesen_an=_betroffener_owner(tool),
        status=LenkungStatus.OFFEN,
        beschreibung=zustand.begruendung,
    )
    db.add(vorgang)
    db.flush()
    protokolliere_erstellung(db, vorgang, akteur_user_id=principal.user_id)
    if vorgang.zugewiesen_an is not None:
        _benachrichtige(
            db,
            vorgang,
            vorgang.zugewiesen_an,
            ANLASS_LENKUNG_NEU,
            "Rahmenüberschreitung festgestellt",
            "Für ein von Ihnen verantwortetes Tool-Objekt wurde eine "
            f"Rahmenüberschreitung erfasst. Frist: {vorgang.frist.date().isoformat()}.",
        )
    # Stufe 2 heisst nach A.13.5: die Fuehrungskraft ist informiert. Wer dort
    # beginnt, muss sie deshalb sofort erreichen und nicht erst beim naechsten
    # Fristablauf.
    if stufe >= 2:
        empfaenger = _eskalationsempfaenger(db, vorgang)
        if empfaenger is not None:
            _benachrichtige(
                db,
                vorgang,
                empfaenger,
                ANLASS_ESKALATION,
                "Lenkungsvorgang in Eskalationsstufe 2",
                "Für das Tool-Objekt wurde ein Verstoß gegen ein organisationsweites "
                "Verbot gemeldet. Solche Fälle beginnen ohne erste Stufe.",
            )
    return vorgang


def _benachrichtige(
    db: Session,
    vorgang: Lenkungsvorgang,
    empfaenger: uuid.UUID,
    anlass: str,
    betreff: str,
    text: str,
) -> Benachrichtigung:
    nachricht = Benachrichtigung(
        empfaenger_user_id=empfaenger,
        anlass=anlass,
        betreff=betreff,
        text=text,
        entity_type="lenkungsvorgaenge",
        entity_id=vorgang.id,
    )
    db.add(nachricht)
    db.flush()
    return nachricht


def hole(db: Session, vorgang_id: uuid.UUID) -> Lenkungsvorgang:
    vorgang = db.get(Lenkungsvorgang, vorgang_id)
    if vorgang is None:
        raise NichtGefunden("Lenkungsvorgang nicht gefunden")
    return vorgang


def offener_vorgang(db: Session, tool_id: uuid.UUID) -> Lenkungsvorgang | None:
    return db.execute(
        select(Lenkungsvorgang)
        .where(
            Lenkungsvorgang.tool_objekt_id == tool_id,
            Lenkungsvorgang.status == LenkungStatus.OFFEN,
        )
        .limit(1)
    ).scalar_one_or_none()


def liste(
    db: Session,
    principal: Principal,
    *,
    nur_offen: bool = True,
    eskalationsstufe: int | None = None,
) -> list[Lenkungsvorgang]:
    """Die im Bereich des Nutzers sichtbaren Vorgaenge (Architektur 4.3)."""
    stmt = select(Lenkungsvorgang)
    if nur_offen:
        stmt = stmt.where(Lenkungsvorgang.status == LenkungStatus.OFFEN)
    if eskalationsstufe is not None:
        stmt = stmt.where(Lenkungsvorgang.eskalationsstufe == eskalationsstufe)
    vorgaenge = db.execute(stmt.order_by(Lenkungsvorgang.frist)).scalars()

    sichtbar: list[Lenkungsvorgang] = []
    for vorgang in vorgaenge:
        tool = db.get(ToolObjekt, vorgang.tool_objekt_id)
        if tool is None:
            continue
        if darf_tool_lesen(db, principal, tool) or vorgang.zugewiesen_an == principal.user_id:
            sichtbar.append(vorgang)
    return sichtbar


def eskaliere_faellige(db: Session, jetzt: datetime | None = None) -> list[Lenkungsvorgang]:
    """Rueckt jeden offenen Vorgang weiter, dessen Frist verstrichen ist.

    Stufe 2 benachrichtigt die Fuehrungskraft des betroffenen Owners und laeuft
    nur noch die **Nachfrist** — nicht noch einmal die volle Tier-Frist. Stufe 3
    kennzeichnet den Vorgang fuer eine technische Massnahme; dort gibt es keine
    Frist mehr, weil nichts mehr abzuwarten ist. In Stufe 3 wird nicht weiter
    gerueckt — hoeher geht es in dieser Anwendung nicht.
    """
    zeitpunkt = jetzt or datetime.now(UTC)
    offene = db.execute(
        select(Lenkungsvorgang).where(Lenkungsvorgang.status == LenkungStatus.OFFEN)
    ).scalars()

    gerueckt: list[Lenkungsvorgang] = []
    for vorgang in offene:
        frist = _als_utc(vorgang.frist)
        if frist is None or frist > zeitpunkt or vorgang.eskalationsstufe >= HOECHSTE_STUFE:
            continue
        vorher = snapshot(vorgang)
        vorgang.eskalationsstufe += 1
        tool = db.get(ToolObjekt, vorgang.tool_objekt_id)
        if tool is not None and vorgang.eskalationsstufe < HOECHSTE_STUFE:
            vorgang.frist = frist_fuer(db, tool, zeitpunkt, stufe=vorgang.eskalationsstufe)
        db.flush()
        protokolliere_aenderung(db, vorgang, vorher, beschreibung="Automatische Eskalation")

        empfaenger = _eskalationsempfaenger(db, vorgang)
        if empfaenger is not None:
            _benachrichtige(
                db,
                vorgang,
                empfaenger,
                ANLASS_ESKALATION,
                f"Lenkungsvorgang in Eskalationsstufe {vorgang.eskalationsstufe}",
                "Die Frist ist ohne Auflösung verstrichen. "
                + (
                    "Der Vorgang ist für eine technische Maßnahme gekennzeichnet."
                    if vorgang.eskalationsstufe >= HOECHSTE_STUFE
                    else "Die Führungskraft des betroffenen Owners ist informiert."
                ),
            )
        gerueckt.append(vorgang)
    return gerueckt


def _eskalationsempfaenger(db: Session, vorgang: Lenkungsvorgang) -> uuid.UUID | None:
    """Ab Stufe 2 geht die Meldung an die Fuehrungskraft (Leitdokument A.13.5).

    Ist keine Fuehrungskraft hinterlegt, bleibt der betroffene Owner der
    Empfaenger — eine Eskalation ins Leere waere schlechter als eine an den
    ohnehin Zustaendigen.
    """
    if vorgang.zugewiesen_an is None:
        return None
    owner = db.get(User, vorgang.zugewiesen_an)
    if owner is None:
        return None
    return owner.fuehrungskraft_user_id or owner.id


# --- Aufloesung (Leitdokument A.13.6) ------------------------------------


def loese_auf(
    db: Session,
    principal: Principal,
    vorgang: Lenkungsvorgang,
    *,
    art: Aufloesungsart,
    bewertung_id: uuid.UUID | None = None,
    kommentar: str = "",
    jetzt: datetime | None = None,
) -> Lenkungsvorgang:
    """Schliesst einen Vorgang auf genau einem der drei zulaessigen Wege."""
    tool = db.get(ToolObjekt, vorgang.tool_objekt_id)
    if tool is None:
        raise NichtGefunden("Tool-Objekt nicht gefunden")
    verlange(
        darf_tool_schreiben(db, principal, tool)
        or vorgang.zugewiesen_an == principal.user_id
        or principal.ist_governance,
        "Lenkungsvorgänge bearbeitet der Betroffene oder die Governance-Rolle",
    )
    if vorgang.status != LenkungStatus.OFFEN:
        raise Ungueltig("Dieser Lenkungsvorgang ist bereits abgeschlossen")

    zeitpunkt = jetzt or now_utc()
    vorher = snapshot(vorgang)

    if art == Aufloesungsart.RAHMEN_ERWEITERN:
        bewertung = _pruefe_neue_bewertung(db, vorgang, bewertung_id)
        vorgang.aufloesung_bewertung_id = bewertung.id
    elif art == Aufloesungsart.STILLLEGEN:
        tool_vorher = snapshot(tool)
        tool.status = AssetStatus.INAKTIV
        db.flush()
        protokolliere_aenderung(db, tool, tool_vorher, akteur_user_id=principal.user_id)

    vorgang.aufloesungsart = art
    vorgang.status = LenkungStatus.AUFGELOEST
    vorgang.aufgeloest_am = zeitpunkt
    if kommentar:
        vorgang.beschreibung = f"{vorgang.beschreibung}\n{kommentar}".strip()
    db.flush()
    protokolliere_aenderung(db, vorgang, vorher, akteur_user_id=principal.user_id)

    # Anpassen und Rahmen erweitern fuehren das Tool zurueck auf gruen;
    # Stilllegen nicht — ein stillgelegtes Tool ist nicht "wieder konform",
    # es ist ausser Betrieb.
    if art in (Aufloesungsart.ANPASSEN, Aufloesungsart.RAHMEN_ERWEITERN):
        zustand = ComplianceZustand(
            tool_objekt_id=tool.id,
            farbe=ComplianceFarbe.GRUEN,
            begruendung=f"Lenkungsvorgang aufgelöst: {AUFLOESUNG_TEXT[art]}",
            festgestellt_am=zeitpunkt,
            festgestellt_von=principal.user_id,
        )
        db.add(zustand)
        db.flush()
        protokolliere_erstellung(db, zustand, akteur_user_id=principal.user_id)
    return vorgang


def _pruefe_neue_bewertung(
    db: Session, vorgang: Lenkungsvorgang, bewertung_id: uuid.UUID | None
) -> Bewertung:
    """`Rahmen erweitern` schliesst erst nach einer neuen Bewertung.

    Verlangt wird eine Bewertung, die **nach** der Eroeffnung des Vorgangs
    entstanden ist — eine aeltere wuerde den erweiterten Rahmen nicht abbilden.
    """
    if bewertung_id is None:
        raise Ungueltig(
            "'Rahmen erweitern' verlangt eine neue Bewertung; der Vorgang schließt "
            "erst nach deren Abschluss"
        )
    bewertung = db.get(Bewertung, bewertung_id)
    if bewertung is None:
        raise Ungueltig("Die angegebene Bewertung existiert nicht")
    bewertet_am = _als_utc(bewertung.bewertet_am)
    eroeffnet_am = _als_utc(vorgang.erstellt_am)
    if bewertet_am is not None and eroeffnet_am is not None and bewertet_am < eroeffnet_am:
        raise Ungueltig(
            "Die angegebene Bewertung stammt von vor der Eröffnung des Lenkungsvorgangs"
        )
    return bewertung


def brich_ab(
    db: Session, principal: Principal, vorgang: Lenkungsvorgang, kommentar: str = ""
) -> Lenkungsvorgang:
    """Abbruch durch die Governance-Rolle, etwa bei einer Fehlmeldung."""
    verlange(principal.ist_governance, "Abbrechen darf ausschließlich die Governance-Rolle")
    if vorgang.status != LenkungStatus.OFFEN:
        raise Ungueltig("Dieser Lenkungsvorgang ist bereits abgeschlossen")
    vorher = snapshot(vorgang)
    vorgang.status = LenkungStatus.ABGEBROCHEN
    vorgang.aufgeloest_am = now_utc()
    if kommentar:
        vorgang.beschreibung = f"{vorgang.beschreibung}\n{kommentar}".strip()
    db.flush()
    protokolliere_aenderung(db, vorgang, vorher, akteur_user_id=principal.user_id)
    return vorgang
