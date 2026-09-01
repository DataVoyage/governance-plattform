"""Gate-Modul (Architektur 8.5, Leitdokument A.11).

Einreichung durch den Prozess- oder technischen Owner, Entscheidung
ausschliesslich durch die Governance-Rolle. Gate 2 verlangt die Angabe, welcher
der fuenf abschliessend aufgezaehlten Ausloeser vorliegt — ein sechster, freier
Grund ist nicht waehlbar, weil die Liste im Leitdokument bewusst abschliessend
ist.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import Principal, verlange
from app.models.base import now_utc
from app.models.enums import Gate2Ausloeser, GateStatus, GateTyp
from app.models.governance import GateVorgang, Prozessobjekt
from app.services.changelog import protokolliere_aenderung, protokolliere_erstellung, snapshot
from app.services.prozess import NichtGefunden, Ungueltig, darf_lesen, darf_schreiben

#: Status, aus denen heraus noch entschieden werden kann.
OFFENE_STATUS = (GateStatus.EINGEREICHT, GateStatus.IN_PRUEFUNG)


def einreichen(
    db: Session,
    principal: Principal,
    prozess: Prozessobjekt,
    *,
    gate_typ: GateTyp,
    ausloeser: str | None = None,
    begruendung: str = "",
) -> GateVorgang:
    verlange(
        darf_schreiben(db, principal, prozess.prozessgeber_org_id),
        "Gate-Vorgaenge reicht der Prozess- oder technische Owner ein",
    )
    if gate_typ == GateTyp.GATE_2:
        if ausloeser is None:
            raise Ungueltig(
                "Gate 2 verlangt die Angabe, welcher der fuenf Ausloeser aus A.11 vorliegt"
            )
        if ausloeser not in set(Gate2Ausloeser):
            raise Ungueltig(f"Unzulaessiger Gate-2-Ausloeser: {ausloeser}")
    elif ausloeser is not None:
        raise Ungueltig("Gate 1 kennt keinen Ausloeser — es ist die Tier-3-Erstfreigabe")

    if offener_vorgang(db, prozess.id, gate_typ) is not None:
        raise Ungueltig("Fuer diesen Prozess ist bereits ein Gate dieses Typs offen")

    vorgang = GateVorgang(
        prozessobjekt_id=prozess.id,
        gate_typ=gate_typ,
        ausloeser=ausloeser,
        begruendung=begruendung,
        status=GateStatus.EINGEREICHT,
        eingereicht_von=principal.user_id,
    )
    db.add(vorgang)
    db.flush()
    protokolliere_erstellung(db, vorgang, akteur_user_id=principal.user_id)
    return vorgang


def entscheiden(
    db: Session,
    principal: Principal,
    vorgang: GateVorgang,
    *,
    status: GateStatus,
    kommentar: str = "",
) -> GateVorgang:
    """Nur die Governance-Rolle entscheidet (Matrix 5.3)."""
    verlange(
        principal.ist_governance, "Gate-Vorgaenge entscheidet ausschliesslich die Governance-Rolle"
    )
    if status not in (GateStatus.FREIGEGEBEN, GateStatus.ABGELEHNT, GateStatus.IN_PRUEFUNG):
        raise Ungueltig("Unzulaessiger Zielstatus fuer eine Gate-Entscheidung")
    if vorgang.status not in OFFENE_STATUS:
        raise Ungueltig("Dieser Gate-Vorgang ist bereits entschieden")

    vorher = snapshot(vorgang)
    vorgang.status = status
    vorgang.entscheidungskommentar = kommentar
    if status in (GateStatus.FREIGEGEBEN, GateStatus.ABGELEHNT):
        vorgang.entschieden_von = principal.user_id
        vorgang.entschieden_am = now_utc()
    db.flush()
    protokolliere_aenderung(db, vorgang, vorher, akteur_user_id=principal.user_id)
    return vorgang


def hole(db: Session, vorgang_id: uuid.UUID) -> GateVorgang:
    vorgang = db.get(GateVorgang, vorgang_id)
    if vorgang is None:
        raise NichtGefunden("Gate-Vorgang nicht gefunden")
    return vorgang


def offener_vorgang(db: Session, prozess_id: uuid.UUID, gate_typ: GateTyp) -> GateVorgang | None:
    return db.execute(
        select(GateVorgang)
        .where(
            GateVorgang.prozessobjekt_id == prozess_id,
            GateVorgang.gate_typ == gate_typ,
            GateVorgang.status.in_(OFFENE_STATUS),
        )
        .limit(1)
    ).scalar_one_or_none()


def historie(db: Session, prozess_id: uuid.UUID) -> list[GateVorgang]:
    return list(
        db.execute(
            select(GateVorgang)
            .where(GateVorgang.prozessobjekt_id == prozess_id)
            .order_by(GateVorgang.erstellt_am.desc())
        ).scalars()
    )


def ist_freigegeben(db: Session, prozess_id: uuid.UUID, gate_typ: GateTyp) -> bool:
    return (
        db.execute(
            select(GateVorgang)
            .where(
                GateVorgang.prozessobjekt_id == prozess_id,
                GateVorgang.gate_typ == gate_typ,
                GateVorgang.status == GateStatus.FREIGEGEBEN,
            )
            .limit(1)
        ).scalar_one_or_none()
        is not None
    )


def offene_vorgaenge(db: Session, principal: Principal) -> list[GateVorgang]:
    """Alle offenen Vorgaenge im Bereich des Nutzers — Arbeitsvorrat der Governance."""
    vorgaenge = db.execute(
        select(GateVorgang).where(GateVorgang.status.in_(OFFENE_STATUS))
    ).scalars()
    sichtbar: list[GateVorgang] = []
    for vorgang in vorgaenge:
        prozess = db.get(Prozessobjekt, vorgang.prozessobjekt_id)
        if prozess is not None and darf_lesen(db, principal, prozess):
            sichtbar.append(vorgang)
    return sichtbar
