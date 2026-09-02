"""Prozess-Modul (Architektur 8.1) — Geschaeftslogik ohne HTTP-Kenntnis."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.orm import Session

from app.core.permissions import Principal, Verboten, verlange
from app.models.enums import Ebene, ProzessStatus, Rolle
from app.models.governance import Datenobjekt, Prozessobjekt, ProzessUmsetzung
from app.models.organisation import Organisationseinheit
from app.schemas.prozess import (
    HOECHSTZAHL_SCHRITTE,
    ProzessAendern,
    ProzessAnlegen,
    ProzessAus,
    UmsetzungAus,
)
from app.services import ableitung
from app.services.changelog import (
    protokolliere_aenderung,
    protokolliere_erstellung,
    protokolliere_loeschung,
    snapshot,
)


class NichtGefunden(Exception):
    def __init__(self, detail: str = "Objekt nicht gefunden") -> None:
        super().__init__(detail)
        self.detail = detail


class Ungueltig(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def zaehle_schritte(process_steps: str) -> int:
    """Schritte der P-Spalte zaehlen (Leitdokument A.5).

    Getrennt wird an Zeilenumbruch oder Semikolon — beides schreibt jemand, der
    Schritte auflistet, ohne es als Syntax zu empfinden.
    """
    roh = process_steps.replace(";", "\n").splitlines()
    return len([teil for teil in (t.strip() for t in roh) if teil])


def _pruefe_zyklenfrei(prozess: Prozessobjekt) -> None:
    """Die Prozesskette muss azyklisch bleiben.

    Technisch ist sie n:m und liesse einen Zyklus zu; fachlich waere er
    unsinnig — ein Prozess kann sich nicht selbst beliefern — und wuerde jede
    Aussage ueber Kritikalitaet und Wirkung entwerten (Leitdokument A.4.2).
    """
    gesehen: set[uuid.UUID] = set()
    stapel = list(prozess.nachgelagert)
    while stapel:
        aktuell = stapel.pop()
        if aktuell.id == prozess.id:
            raise Ungueltig(
                "Diese Verknuepfung erzeugt einen Kreis in der Prozesskette; "
                "ein Prozess kann sich nicht selbst beliefern"
            )
        if aktuell.id in gesehen:
            continue
        gesehen.add(aktuell.id)
        stapel.extend(aktuell.nachgelagert)


# --- Sichtbarkeit (Architektur 4.3) --------------------------------------


def erlaubte_org_ids(db: Session, principal: Principal) -> set[uuid.UUID]:
    """Alle Organisationseinheiten im Bereich des Nutzers.

    Ein Scope auf einen Fachbereich schliesst dessen INT- und LAND-Einheiten
    ein; ein Scope auf eine Einheit nur diese.
    """
    ids = set(principal.scope_organisationseinheiten)
    fachbereiche = principal.scope_fachbereiche
    if fachbereiche:
        treffer = db.execute(
            select(Organisationseinheit.id).where(
                Organisationseinheit.fachbereich_id.in_(fachbereiche)
            )
        ).scalars()
        ids.update(treffer)
    return ids


def sichtbarkeitsbedingung(db: Session, principal: Principal) -> ColumnElement[bool] | None:
    """SQL-Bedingung fuer die sichtbaren Prozessobjekte, oder None fuer alle."""
    if principal.sieht_global:
        return None
    org_ids = erlaubte_org_ids(db, principal)
    umsetzung_ids = (
        select(ProzessUmsetzung.prozessobjekt_id).where(ProzessUmsetzung.land_org_id.in_(org_ids))
        if org_ids
        else select(ProzessUmsetzung.prozessobjekt_id).where(False)
    )
    return or_(
        Prozessobjekt.prozessgeber_org_id.in_(org_ids) if org_ids else False,
        Prozessobjekt.id.in_(umsetzung_ids),
        Prozessobjekt.owner_user_id == principal.user_id,
        Prozessobjekt.stellvertretung_user_id == principal.user_id,
    )


def darf_lesen(db: Session, principal: Principal, prozess: Prozessobjekt) -> bool:
    if principal.sieht_global:
        return True
    if principal.user_id in (prozess.owner_user_id, prozess.stellvertretung_user_id):
        return True
    org_ids = erlaubte_org_ids(db, principal)
    if prozess.prozessgeber_org_id in org_ids:
        return True
    return any(u.land_org_id in org_ids for u in prozess.umsetzungen)


def _fachbereich_von_org(db: Session, org_id: uuid.UUID) -> uuid.UUID | None:
    return db.execute(
        select(Organisationseinheit.fachbereich_id).where(Organisationseinheit.id == org_id)
    ).scalar_one_or_none()


def darf_schreiben(db: Session, principal: Principal, prozessgeber_org_id: uuid.UUID) -> bool:
    """Anlegen und Aendern: Prozess-Owner im eigenen Scope oder Governance."""
    if principal.ist_governance:
        return True
    fachbereich_id = _fachbereich_von_org(db, prozessgeber_org_id)
    return principal.hat_rolle(
        Rolle.PROZESS_OWNER,
        organisationseinheit_id=prozessgeber_org_id,
        fachbereich_id=fachbereich_id,
    )


def darf_umsetzung_bearbeiten(db: Session, principal: Principal, land_org_id: uuid.UUID) -> bool:
    """Prozess-Umsetzer darf ausschliesslich die lokale Abweichung pflegen."""
    if principal.ist_governance:
        return True
    fachbereich_id = _fachbereich_von_org(db, land_org_id)
    return principal.hat_eine_rolle(
        Rolle.PROZESS_UMSETZER,
        Rolle.PROZESS_OWNER,
        organisationseinheit_id=land_org_id,
        fachbereich_id=fachbereich_id,
    )


# --- Lesen ----------------------------------------------------------------


def hole(db: Session, prozess_id: uuid.UUID) -> Prozessobjekt:
    prozess = db.get(Prozessobjekt, prozess_id)
    if prozess is None:
        raise NichtGefunden("Prozessobjekt nicht gefunden")
    return prozess


def hole_sichtbar(db: Session, principal: Principal, prozess_id: uuid.UUID) -> Prozessobjekt:
    prozess = hole(db, prozess_id)
    if not darf_lesen(db, principal, prozess):
        # Kein 404-Verstecken: die Existenz ist unkritisch, der Inhalt nicht.
        raise Verboten("Prozessobjekt liegt außerhalb des eigenen Bereichs")
    return prozess


def liste(
    db: Session,
    principal: Principal,
    *,
    fachbereich_id: uuid.UUID | None = None,
    status: ProzessStatus | None = None,
) -> list[Prozessobjekt]:
    stmt = select(Prozessobjekt)
    bedingung = sichtbarkeitsbedingung(db, principal)
    if bedingung is not None:
        stmt = stmt.where(bedingung)
    if fachbereich_id is not None:
        org_ids = select(Organisationseinheit.id).where(
            Organisationseinheit.fachbereich_id == fachbereich_id
        )
        stmt = stmt.where(Prozessobjekt.prozessgeber_org_id.in_(org_ids))
    if status is not None:
        stmt = stmt.where(Prozessobjekt.status == status)
    return list(db.execute(stmt.order_by(Prozessobjekt.name)).scalars())


def neueste_bewertung(prozess: Prozessobjekt):
    """Die juengste Bewertung, oder None — vorherige bleiben erhalten."""
    if not prozess.bewertungen:
        return None
    return max(prozess.bewertungen, key=lambda b: b.bewertet_am)


def zu_schema(prozess: Prozessobjekt) -> ProzessAus:
    bewertung = neueste_bewertung(prozess)
    return ProzessAus(
        id=prozess.id,
        name=prozess.name,
        owner_user_id=prozess.owner_user_id,
        stellvertretung_user_id=prozess.stellvertretung_user_id,
        prozessgeber_org_id=prozess.prozessgeber_org_id,
        supplier=prozess.supplier,
        process_steps=prozess.process_steps,
        output=prozess.output,
        customer=prozess.customer,
        ausfallfolge=prozess.ausfallfolge,
        status=prozess.status,
        erlaubte_externe_ziele=list(prozess.erlaubte_externe_ziele or []),
        erstellt_am=prozess.erstellt_am,
        geaendert_am=prozess.geaendert_am,
        reichweite=prozess.reichweite,
        kritikalitaet=prozess.kritikalitaet,
        mitbestimmung_flag=prozess.mitbestimmung_flag,
        schritt_anzahl=zaehle_schritte(prozess.process_steps),
        schritte_zu_viele=zaehle_schritte(prozess.process_steps) > HOECHSTZAHL_SCHRITTE,
        input_datenobjekt_ids=[d.id for d in prozess.input_datenobjekte],
        output_datenobjekt_ids=[d.id for d in prozess.output_datenobjekte],
        vorgelagert_ids=[p.id for p in prozess.vorgelagert],
        nachgelagert_ids=[p.id for p in prozess.nachgelagert],
        umsetzungen=[UmsetzungAus.model_validate(u) for u in prozess.umsetzungen],
        tool_objekt_ids=[t.id for t in prozess.tool_objekte],
        tier=bewertung.tier if bewertung else None,
        ausgeloeste_k_klassen=list(bewertung.ausgeloeste_k_klassen) if bewertung else [],
        bewertung_gueltig_bis=bewertung.gueltig_bis if bewertung else None,
    )


# --- Schreiben ------------------------------------------------------------


def _lade_datenobjekte(db: Session, ids: Sequence[uuid.UUID]) -> list[Datenobjekt]:
    if not ids:
        return []
    objekte = list(db.execute(select(Datenobjekt).where(Datenobjekt.id.in_(ids))).scalars())
    if len(objekte) != len(set(ids)):
        raise Ungueltig("Mindestens ein referenziertes Datenobjekt existiert nicht")
    return objekte


def _lade_prozesse(db: Session, ids: Sequence[uuid.UUID]) -> list[Prozessobjekt]:
    if not ids:
        return []
    objekte = list(db.execute(select(Prozessobjekt).where(Prozessobjekt.id.in_(ids))).scalars())
    if len(objekte) != len(set(ids)):
        raise Ungueltig("Mindestens ein referenziertes Prozessobjekt existiert nicht")
    return objekte


def _pruefe_land_org(db: Session, org_id: uuid.UUID) -> Organisationseinheit:
    org = db.get(Organisationseinheit, org_id)
    if org is None:
        raise Ungueltig("Organisationseinheit existiert nicht")
    if org.ebene != Ebene.LAND:
        raise Ungueltig("Eine Umsetzung verweist immer auf eine LAND-Organisationseinheit")
    return org


def anlegen(db: Session, principal: Principal, daten: ProzessAnlegen) -> Prozessobjekt:
    prozessgeber = db.get(Organisationseinheit, daten.prozessgeber_org_id)
    if prozessgeber is None:
        raise Ungueltig("Prozessgeber-Organisationseinheit existiert nicht")
    if prozessgeber.ebene != Ebene.INT:
        raise Ungueltig("Der Prozessgeber ist immer eine INT-Organisationseinheit")
    verlange(
        darf_schreiben(db, principal, daten.prozessgeber_org_id),
        "Prozessobjekte legt nur ein Prozess-Owner im eigenen Bereich an",
    )

    prozess = Prozessobjekt(
        name=daten.name,
        owner_user_id=daten.owner_user_id,
        stellvertretung_user_id=daten.stellvertretung_user_id,
        prozessgeber_org_id=daten.prozessgeber_org_id,
        supplier=daten.supplier,
        process_steps=daten.process_steps,
        output=daten.output,
        customer=daten.customer,
        ausfallfolge=daten.ausfallfolge,
        status=ProzessStatus.ENTWURF,
        erlaubte_externe_ziele=list(daten.erlaubte_externe_ziele),
    )
    prozess.input_datenobjekte = _lade_datenobjekte(db, daten.input_datenobjekt_ids)
    prozess.output_datenobjekte = _lade_datenobjekte(db, daten.output_datenobjekt_ids)
    prozess.vorgelagert = _lade_prozesse(db, daten.vorgelagert_ids)
    prozess.nachgelagert = _lade_prozesse(db, daten.nachgelagert_ids)
    _pruefe_zyklenfrei(prozess)
    db.add(prozess)
    db.flush()

    for land_org_id in dict.fromkeys(daten.umsetzung_land_org_ids):
        _pruefe_land_org(db, land_org_id)
        db.add(ProzessUmsetzung(prozessobjekt_id=prozess.id, land_org_id=land_org_id))
    db.flush()
    db.refresh(prozess)

    for betroffen in ableitung.aktualisiere_kette(prozess):
        if betroffen.id != prozess.id:
            db.flush()
    db.flush()
    protokolliere_erstellung(db, prozess, akteur_user_id=principal.user_id)
    return prozess


def pruefe_aktivierung(db: Session, prozess: Prozessobjekt) -> None:
    """Torwaechter fuer den Wechsel nach ``aktiv`` (Leitdokument A.10.5, A.11).

    Ab Tier 3 haengen zwei Bedingungen an der Aktivierung: eine vollstaendige,
    gueltige Selbstverpflichtung des Prozesseigners und die Erstfreigabe durch
    Gate 1. Beide werden hier geprueft und nicht in der Oberflaeche, damit ein
    direkter API-Aufruf sie nicht umgehen kann.

    Die Importe stehen bewusst in der Funktion: Selbstverpflichtungs- und
    Gate-Modul bauen ihrerseits auf diesem Modul auf.
    """
    from app.models.enums import GateTyp
    from app.services import gate, selbstverpflichtung

    bewertung = neueste_bewertung(prozess)
    if bewertung is None:
        raise Ungueltig("Ein Prozessobjekt wird erst nach einer Bewertung aktiv (Leitdokument A.8)")
    if bewertung.tier < 3:
        return
    if not selbstverpflichtung.ist_gedeckt(db, prozess):
        raise Ungueltig(
            "Ab Tier 3 wird ein Prozessobjekt erst nach vollständig abgegebener "
            "Selbstverpflichtung aktiv"
        )
    if not gate.ist_freigegeben(db, prozess.id, GateTyp.GATE_1):
        raise Ungueltig(
            "Ab Tier 3 wird ein Prozessobjekt erst nach der Erstfreigabe durch Gate 1 aktiv"
        )


def aendern(
    db: Session, principal: Principal, prozess: Prozessobjekt, daten: ProzessAendern
) -> Prozessobjekt:
    verlange(
        darf_schreiben(db, principal, prozess.prozessgeber_org_id),
        "Prozessobjekte ändert nur ein Prozess-Owner im eigenen Bereich",
    )
    vorher = snapshot(prozess)
    werte = daten.model_dump(exclude_unset=True)

    if "prozessgeber_org_id" in werte:
        neu = db.get(Organisationseinheit, werte["prozessgeber_org_id"])
        if neu is None or neu.ebene != Ebene.INT:
            raise Ungueltig("Der Prozessgeber ist immer eine INT-Organisationseinheit")
        verlange(
            darf_schreiben(db, principal, werte["prozessgeber_org_id"]),
            "Der neue Prozessgeber liegt außerhalb des eigenen Bereichs",
        )
    if "input_datenobjekt_ids" in werte:
        prozess.input_datenobjekte = _lade_datenobjekte(db, werte.pop("input_datenobjekt_ids"))
    if "output_datenobjekt_ids" in werte:
        prozess.output_datenobjekte = _lade_datenobjekte(db, werte.pop("output_datenobjekt_ids"))
    if "vorgelagert_ids" in werte:
        prozess.vorgelagert = _lade_prozesse(db, werte.pop("vorgelagert_ids"))
    if "nachgelagert_ids" in werte:
        prozess.nachgelagert = _lade_prozesse(db, werte.pop("nachgelagert_ids"))
    if {"vorgelagert_ids", "nachgelagert_ids"} & set(daten.model_dump(exclude_unset=True)):
        _pruefe_zyklenfrei(prozess)
    if werte.get("status") == ProzessStatus.AKTIV and prozess.status != ProzessStatus.AKTIV:
        pruefe_aktivierung(db, prozess)

    # Vor dem Setzen vergleichen: danach waere nicht mehr erkennbar, welches
    # Ziel neu ist (Leitdokument A.11, Ausloeser „neues externes Ziel").
    bisherige_ziele = set(prozess.erlaubte_externe_ziele or [])
    neue_ziele = [
        ziel for ziel in werte.get("erlaubte_externe_ziele") or [] if ziel not in bisherige_ziele
    ]

    for feld, wert in werte.items():
        setattr(prozess, feld, wert)
    db.flush()

    ableitung.aktualisiere_kette(prozess)
    db.flush()
    protokolliere_aenderung(db, prozess, vorher, akteur_user_id=principal.user_id)

    if neue_ziele:
        from app.services import gate

        gate.wegen_neuem_externen_ziel(db, principal, prozess, neue_ziele)
    return prozess


def umsetzung_anlegen(
    db: Session,
    principal: Principal,
    prozess: Prozessobjekt,
    land_org_id: uuid.UUID,
    lokale_abweichung: str | None = None,
) -> ProzessUmsetzung:
    verlange(
        darf_schreiben(db, principal, prozess.prozessgeber_org_id)
        or darf_umsetzung_bearbeiten(db, principal, land_org_id),
        "Keine Berechtigung für diese Umsetzung",
    )
    _pruefe_land_org(db, land_org_id)
    if any(u.land_org_id == land_org_id for u in prozess.umsetzungen):
        raise Ungueltig("Diese Umsetzung besteht bereits")
    umsetzung = ProzessUmsetzung(
        prozessobjekt_id=prozess.id,
        land_org_id=land_org_id,
        lokale_abweichung=lokale_abweichung,
    )
    db.add(umsetzung)
    db.flush()
    db.refresh(prozess)
    ableitung.aktualisiere_kette(prozess)
    db.flush()
    protokolliere_erstellung(db, umsetzung, akteur_user_id=principal.user_id)
    return umsetzung


def umsetzung_aendern(
    db: Session,
    principal: Principal,
    umsetzung: ProzessUmsetzung,
    lokale_abweichung: str | None,
) -> ProzessUmsetzung:
    """Der Prozess-Umsetzer darf hier — und nur hier — schreiben (Matrix 5.3)."""
    verlange(
        darf_umsetzung_bearbeiten(db, principal, umsetzung.land_org_id),
        "Nur der Umsetzer dieser Landesorganisation pflegt die lokale Abweichung",
    )
    vorher = snapshot(umsetzung)
    umsetzung.lokale_abweichung = lokale_abweichung
    db.flush()
    protokolliere_aenderung(db, umsetzung, vorher, akteur_user_id=principal.user_id)
    return umsetzung


def umsetzung_entfernen(
    db: Session, principal: Principal, prozess: Prozessobjekt, umsetzung: ProzessUmsetzung
) -> None:
    verlange(
        darf_schreiben(db, principal, prozess.prozessgeber_org_id),
        "Umsetzungen entfernt nur der Prozess-Owner oder die Governance-Rolle",
    )
    protokolliere_loeschung(db, umsetzung, akteur_user_id=principal.user_id)
    db.delete(umsetzung)
    db.flush()
    db.refresh(prozess)
    ableitung.aktualisiere_kette(prozess)
    db.flush()
