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
    jetzt: datetime | None = None,
) -> tuple[ComplianceZustand, Lenkungsvorgang | None]:
    """Traegt einen Zustand in die Zeitreihe ein.

    Bei ``rot`` entsteht automatisch ein Lenkungsvorgang in Stufe 1 — es sei
    denn, fuer dieses Tool ist bereits einer offen: eine zweite Meldung
    derselben Abweichung soll den Vorgang nicht verdoppeln.
    """
    verlange(
        darf_tool_schreiben(db, principal, tool),
        "Compliance-Meldungen erfasst der technische Owner oder die Governance-Rolle",
    )
    zeitpunkt = jetzt or now_utc()
    zustand = ComplianceZustand(
        tool_objekt_id=tool.id,
        farbe=farbe,
        begruendung=begruendung,
        abweichung_art=abweichung_art,
        festgestellt_am=zeitpunkt,
        festgestellt_von=principal.user_id,
    )
    db.add(zustand)
    db.flush()
    protokolliere_erstellung(db, zustand, akteur_user_id=principal.user_id)

    if farbe != ComplianceFarbe.ROT:
        return zustand, None
    bestehend = offener_vorgang(db, tool.id)
    if bestehend is not None:
        return zustand, bestehend
    return zustand, _eroeffne_lenkungsvorgang(db, principal, tool, zustand, zeitpunkt)


# --- Lenkungsvorgang ------------------------------------------------------


def frist_fuer(db: Session, tool: ToolObjekt, ab: datetime) -> datetime:
    """Tier-abhaengige Frist (Leitdokument A.13.5), Tier aus der Vererbung."""
    tier = erbe_klassifikation(tool).tier or 1
    return ab + timedelta(days=konfiguration.lenkungsfrist_tage(db, tier))


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
) -> Lenkungsvorgang:
    vorgang = Lenkungsvorgang(
        tool_objekt_id=tool.id,
        compliance_zustand_id=zustand.id,
        eskalationsstufe=1,
        frist=frist_fuer(db, tool, zeitpunkt),
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
            "Rahmenueberschreitung festgestellt",
            "Fuer ein von Ihnen verantwortetes Tool-Objekt wurde eine "
            f"Rahmenueberschreitung erfasst. Frist: {vorgang.frist.date().isoformat()}.",
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

    Stufe 2 benachrichtigt die Fuehrungskraft des betroffenen Owners; Stufe 3
    kennzeichnet den Vorgang fuer eine technische Massnahme. In Stufe 3 wird
    nicht weiter gerueckt — hoeher geht es in dieser Anwendung nicht.
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
        if tool is not None:
            vorgang.frist = frist_fuer(db, tool, zeitpunkt)
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
                "Die Frist ist ohne Aufloesung verstrichen. "
                + (
                    "Der Vorgang ist fuer eine technische Massnahme gekennzeichnet."
                    if vorgang.eskalationsstufe >= HOECHSTE_STUFE
                    else "Die Fuehrungskraft des betroffenen Owners ist informiert."
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
        "Lenkungsvorgaenge bearbeitet der Betroffene oder die Governance-Rolle",
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
            begruendung=f"Lenkungsvorgang aufgeloest: {art.value}",
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
            "'Rahmen erweitern' verlangt eine neue Bewertung; der Vorgang schliesst "
            "erst nach deren Abschluss"
        )
    bewertung = db.get(Bewertung, bewertung_id)
    if bewertung is None:
        raise Ungueltig("Die angegebene Bewertung existiert nicht")
    bewertet_am = _als_utc(bewertung.bewertet_am)
    eroeffnet_am = _als_utc(vorgang.erstellt_am)
    if bewertet_am is not None and eroeffnet_am is not None and bewertet_am < eroeffnet_am:
        raise Ungueltig(
            "Die angegebene Bewertung stammt von vor der Eroeffnung des Lenkungsvorgangs"
        )
    return bewertung


def brich_ab(
    db: Session, principal: Principal, vorgang: Lenkungsvorgang, kommentar: str = ""
) -> Lenkungsvorgang:
    """Abbruch durch die Governance-Rolle, etwa bei einer Fehlmeldung."""
    verlange(principal.ist_governance, "Abbrechen darf ausschliesslich die Governance-Rolle")
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
