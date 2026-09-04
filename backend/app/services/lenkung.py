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
from app.services import rahmen as rahmen_service
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


def _schlusstext(art: str, kommentar: str) -> str:
    """Was am Werkzeug stehenbleibt, wenn ein Vorgang schliesst.

    Beides gehoert hinein: **wie** geschlossen wurde und **warum**. Wer spaeter
    die Zeitreihe eines Werkzeugs liest, soll den Vorgang nicht erst aufschlagen
    muessen, um zu erfahren, was aus ihm geworden ist (E-64).
    """
    text = f"Lenkungsvorgang {art}"
    return f"{text} — {kommentar.strip()}" if kommentar.strip() else text


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


def gemessene_farbe(db: Session, tool: ToolObjekt) -> ComplianceFarbe:
    """Die Farbe nach A.13.3 — gerechnet, nicht gewaehlt.

    Bis E-64 hat ein Mensch sie ausgesucht. Das war die falsche Frage: die
    Anwendung misst den Erlaubnisrahmen und vier der sechs Verbote selbst, und
    eine Auswahlliste lud nur dazu ein, etwas anderes einzutragen, als der
    Sachstand hergibt. Was sie weiss, fragt sie nicht.

    * **rot** — eine Abweichung steht, gemessen oder als offener Vorgang.
    * **gelb** — das Werkzeug haengt an keinem Prozessobjekt. Es erbt nichts,
      also gibt es nichts, wogegen zu pruefen waere (A.13.3, „nicht
      zugeordnet"); das ist kein Befund, aber auch keine Unbedenklichkeit.
    * **gruen** — zugeordnet, im Rahmen, kein Verbot, kein offener Vorgang.
    """
    if rahmen_service.pruefe_schicht2(tool):
        return ComplianceFarbe.ROT
    if offener_vorgang(db, tool.id) is not None:
        return ComplianceFarbe.ROT
    # Die Reihenfolge ist der Punkt: ein Werkzeug ohne Prozesskante wird
    # **nicht** am Rahmen gemessen. Der Rahmen entsteht aus dem, was seine
    # Prozessobjekte erklaeren — ohne Kante erklaert niemand etwas, und jede
    # genutzte Quelle staende als Abweichung da. Rot waere dann kein Befund,
    # sondern eine Verwechslung von „unzulaessig" mit „unbekannt".
    if not tool.prozessobjekte:
        return ComplianceFarbe.GELB
    if not rahmen_service.erlaubnisrahmen(db, tool).eingehalten:
        return ComplianceFarbe.ROT
    return ComplianceFarbe.GRUEN


def melde_abweichung(
    db: Session,
    principal: Principal,
    tool: ToolObjekt,
    *,
    begruendung: str,
    jetzt: datetime | None = None,
) -> tuple[ComplianceZustand | None, Lenkungsvorgang]:
    """Der eine Knopf: „Compliance-Abweichung melden" (E-64).

    Gemeldet wird **eine Abweichung**, nichts sonst. Es gibt keine Farbe zu
    waehlen, kein Verbot zu benennen und keine Abweichungsart einzutragen: die
    Farbe ist rot, weil eine Abweichung gemeldet wurde, und ob ein Verbot aus
    Schicht 2 daran haengt, sieht die Anwendung selbst.

    Der Aufruf ist **idempotent**. Laeuft fuer dieses Werkzeug schon ein
    ungeklaerter Vorgang, passiert nichts — dieselbe Abweichung zweimal zu
    melden ist dieselbe Abweichung, und ein zweiter Vorgang mit eigener Frist
    waere eine Verdopplung ohne Anlass. Zurueck kommt dann der laufende
    Vorgang und kein neuer Zustand.

    Der Beitrag des Menschen ist der **Grund**: was er beobachtet hat. Zwei der
    sechs Verbote aus A.13.2 sieht die Anwendung nicht, und was in der
    Zielplattform geschieht, sieht sie nie. Dafuer gibt es dieses eine Feld.
    """
    verlange(
        darf_tool_schreiben(db, principal, tool),
        "Compliance-Meldungen erfasst der technische Owner oder die Governance-Rolle",
    )
    bestehend = offener_vorgang(db, tool.id)
    if bestehend is not None:
        return None, bestehend

    zeitpunkt = jetzt or now_utc()
    # Was die Anwendung selbst sieht, traegt sie an der Meldung nach: bei einem
    # Verstoss gegen Schicht 2 entfaellt die erste Stufe (A.13.5).
    verbote = rahmen_service.pruefe_schicht2(tool)
    verletzt = rahmen_service.erlaubnisrahmen(db, tool).verletzte_elemente
    zustand = _trage_zustand_ein(
        db,
        tool,
        farbe=ComplianceFarbe.ROT,
        begruendung=begruendung,
        abweichung_art=verletzt[0] if verletzt else None,
        schicht2_verbot=verbote[0] if verbote else None,
        zeitpunkt=zeitpunkt,
        akteur_user_id=principal.user_id,
    )
    stufe = 2 if verbote else 1
    vorgang = _eroeffne_lenkungsvorgang(db, principal, tool, zustand, zeitpunkt, stufe=stufe)
    return zustand, vorgang


def _trage_zustand_ein(
    db: Session,
    tool: ToolObjekt,
    *,
    farbe: ComplianceFarbe,
    begruendung: str,
    abweichung_art: str | None = None,
    schicht2_verbot: str | None = None,
    zeitpunkt: datetime,
    akteur_user_id: uuid.UUID | None,
) -> ComplianceZustand:
    """Der **einzige** Weg zu einem Eintrag in der Zeitreihe.

    Hier steht die Farbregel aus A.13.3, und zwar genau einmal. Bis E-63 gab es
    zwei Wege zu einem Zustand — die Meldung und die Aufloesung eines
    Lenkungsvorgangs —, und nur der erste pruefte. Ein aufgeloester Vorgang
    schrieb gruen, auch wenn ein Verbot aus Schicht 2 stand. Eine Regel, die
    ein zweiter Weg umgeht, ist keine Regel.
    """
    if schicht2_verbot is not None and schicht2_verbot not in set(Schicht2Verbot):
        raise Ungueltig(f"Unzulässiges Schicht-2-Verbot: {schicht2_verbot}")
    if schicht2_verbot is not None and farbe != ComplianceFarbe.ROT:
        raise Ungueltig(
            "Ein Verstoß gegen Schicht 2 ist kein gelber Befund — er ist rot, "
            "weil ihn keine Bewertung freischaltet"
        )
    if farbe != ComplianceFarbe.ROT:
        # Dieselbe Regel, gemessen statt mitgeteilt. Oben greift sie nur, wenn
        # der Meldende das Verbot selbst danebenschreibt; steht es in den
        # Daten, gilt sie auch ohne Hinweis — sonst waere sie wieder eine
        # Regel mit einem Weg daran vorbei. Gelb ist dabei kein milderer Fall
        # als Gruen: „beobachtet, noch nicht belegt" ist eine Aussage ueber
        # etwas Ungeklaertes, und ein Verbot in den Daten ist geklaert.
        stehende = rahmen_service.pruefe_schicht2(tool)
        if stehende:
            raise Ungueltig(
                f"„{farbe}“ ist nicht meldbar, solange ein Verbot aus Schicht 2 "
                "steht: " + ", ".join(sorted(stehende)) + ". Es ist rot, weil es "
                "keine Bewertung freischaltet"
            )
    zustand = ComplianceZustand(
        tool_objekt_id=tool.id,
        farbe=farbe,
        begruendung=begruendung,
        abweichung_art=abweichung_art,
        schicht2_verbot=schicht2_verbot,
        festgestellt_am=zeitpunkt,
        festgestellt_von=akteur_user_id,
    )
    db.add(zustand)
    db.flush()
    protokolliere_erstellung(db, zustand, akteur_user_id=akteur_user_id)
    return zustand


def _hebe_auf_stufe(
    db: Session,
    vorgang: Lenkungsvorgang,
    tool: ToolObjekt,
    verbot: str,
    zeitpunkt: datetime,
    akteur_user_id: uuid.UUID | None = None,
) -> None:
    """Hebt einen laufenden Vorgang wegen eines Schicht-2-Verstosses auf Stufe 2.

    Ausgeloest wird das seit E-64 von der **Messung**, nicht von einer zweiten
    Meldung: wer ein Verbot benennen musste, damit die Stufe stimmt, konnte es
    auch weglassen. Der geplante Lauf sieht nach, was in den Daten steht.
    """
    vorher = snapshot(vorgang)
    vorgang.eskalationsstufe = 2
    vorgang.schicht2_verbot = verbot
    vorgang.frist = frist_fuer(db, tool, zeitpunkt, stufe=2)
    db.flush()
    protokolliere_aenderung(
        db,
        vorgang,
        vorher,
        akteur_user_id=akteur_user_id,
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
        tool = db.get(ToolObjekt, vorgang.tool_objekt_id)
        # A.13.5: bei einem Verstoss gegen Schicht 2 entfaellt die erste Stufe.
        # Steht ein Verbot erst seit einer spaeteren Aenderung in den Daten,
        # faellt es hier auf — vorher brauchte es dafuer eine zweite Meldung.
        if tool is not None and vorgang.eskalationsstufe < 2:
            verbote = rahmen_service.pruefe_schicht2(tool)
            if verbote:
                _hebe_auf_stufe(db, vorgang, tool, verbote[0], zeitpunkt)
                gerueckt.append(vorgang)
                continue
        frist = _als_utc(vorgang.frist)
        if frist is None or frist > zeitpunkt or vorgang.eskalationsstufe >= HOECHSTE_STUFE:
            continue
        vorher = snapshot(vorgang)
        vorgang.eskalationsstufe += 1
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

    # Anpassen und Rahmen erweitern fuehren das Tool zurueck auf gruen;
    # Stilllegen nicht — ein stillgelegtes Tool ist nicht "wieder konform",
    # es ist ausser Betrieb. Deshalb wird auch nur bei den ersten beiden
    # nachgemessen: sie behaupten, die Abweichung sei weg.
    if art in (Aufloesungsart.ANPASSEN, Aufloesungsart.RAHMEN_ERWEITERN):
        _verlange_abweichungsfrei(db, tool, art)

    vorgang.aufloesungsart = art
    vorgang.status = LenkungStatus.AUFGELOEST
    vorgang.aufgeloest_am = zeitpunkt
    # Der Befund ist die Feststellung des einen, der Kommentar die Erklaerung
    # des anderen. Bis E-63 landete der Kommentar in ``beschreibung`` — danach
    # stand am Objekt nicht mehr, was eigentlich festgestellt worden war.
    if kommentar:
        vorgang.aufloesungskommentar = kommentar.strip()
    db.flush()
    protokolliere_aenderung(db, vorgang, vorher, akteur_user_id=principal.user_id)

    # Jeder der drei Wege hinterlaesst einen Eintrag am Werkzeug — auch das
    # Stilllegen. Es ist keine Rueckkehr in den Rahmen, also bleibt es rot;
    # aber es ist ein Abschluss, und der gehoert in die Zeitreihe.
    _trage_zustand_ein(
        db,
        tool,
        farbe=(
            ComplianceFarbe.GRUEN
            if art in (Aufloesungsart.ANPASSEN, Aufloesungsart.RAHMEN_ERWEITERN)
            else ComplianceFarbe.ROT
        ),
        begruendung=_schlusstext(f"aufgelöst: {AUFLOESUNG_TEXT[art]}", kommentar),
        zeitpunkt=zeitpunkt,
        akteur_user_id=principal.user_id,
    )
    return vorgang


def offene_abweichungen(db: Session, tool: ToolObjekt) -> list[str]:
    """Was die Anwendung an diesem Werkzeug gerade selbst sieht.

    Dieselbe Messung, die eine Aufloesung als „angepasst" verlangt. Sie steht
    auch an der Ausgabe, damit die Oberflaeche vorher sagen kann, was noch
    aussteht — ein Riegel, den man erst nach dem Klicken bemerkt, erklaert
    nichts.
    """
    verbote = rahmen_service.pruefe_schicht2(tool)
    rahmen = rahmen_service.erlaubnisrahmen(db, tool)
    return [*(f"Verbot {v}" for v in sorted(verbote)), *rahmen.verletzte_elemente]


def _verlange_abweichungsfrei(db: Session, tool: ToolObjekt, art: Aufloesungsart) -> None:
    """„Angepasst" ist eine pruefbare Aussage — also wird sie geprueft.

    Bis E-63 genuegte das Anklicken: der Vorgang schloss, das Tool-Objekt wurde
    gruen, und ob sich am Werkzeug etwas geaendert hatte, sah niemand nach. Ein
    Zustand, der aus einer Behauptung folgt statt aus einer Messung, traegt die
    Anwendung nicht — er beschreibt nur, was jemand angeklickt hat.

    Beide Wege werden gemessen, nicht nur der eine. „Rahmen erweitern" verlangt
    zwar schon eine neue Bewertung; ob diese Bewertung den Zugriff tatsaechlich
    deckt, sagt aber erst der Rahmen. Wer nicht anpassen **kann**, hat den
    dritten Weg: Stilllegen schliesst immer.

    Entscheidend ist, was hier **nicht** geprueft wird. Zwei der sechs Verbote
    aus A.13.2 sieht diese Anwendung nicht — sie werden gemeldet, nicht
    gemessen (``AUTOMATISCH_ERKENNBAR``). Fuer sie bleibt „angepasst" eine
    Aussage des Menschen, und das ist richtig so: die Anwendung hat kein
    Signal, dem sie widersprechen koennte. Der Riegel greift nur dort, wo sie
    selbst etwas sieht. Sie verweigert also nicht die Behauptung, sondern den
    Widerspruch zur eigenen Messung.
    """
    steht = offene_abweichungen(db, tool)
    if not steht:
        return
    offen = ", ".join(steht)
    weg = AUFLOESUNG_TEXT[art].capitalize()
    raise Ungueltig(
        f"„{weg}“ setzt voraus, dass die Abweichung behoben ist; gemessen steht "
        f"sie noch: {offen}. Solange sie steht, bleibt Stilllegen — oder der "
        "Vorgang bleibt offen, bis das Werkzeug wirklich angepasst ist."
    )


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
    tool = db.get(ToolObjekt, vorgang.tool_objekt_id)
    zeitpunkt = now_utc()
    vorher = snapshot(vorgang)
    vorgang.status = LenkungStatus.ABGEBROCHEN
    vorgang.aufgeloest_am = zeitpunkt
    if kommentar:
        vorgang.aufloesungskommentar = kommentar.strip()
    db.flush()
    protokolliere_aenderung(db, vorgang, vorher, akteur_user_id=principal.user_id)
    if tool is not None:
        # Eine Fehlmeldung heisst: es gab nie eine Abweichung. Welche Farbe
        # danach gilt, sagt die Messung — nicht der Abbrechende (E-64).
        _trage_zustand_ein(
            db,
            tool,
            farbe=gemessene_farbe(db, tool),
            begruendung=_schlusstext("abgebrochen — Fehlmeldung", kommentar),
            zeitpunkt=zeitpunkt,
            akteur_user_id=principal.user_id,
        )
    return vorgang
