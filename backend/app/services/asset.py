"""Asset-Management-Modul (Architektur 8.3).

Tool-Objekt und Datenobjekt bleiben getrennte Entitaeten mit getrennten
Owner-Konzepten und getrennten Lebenszyklen (Architektur 3.3). Zwei Regeln
dieses Moduls tragen die Phase:

* Ein importierter Datensatz ist in den governance-relevanten Feldern
  (Kategorie, Klassifikation) editierbar und in den stammdatenbezogenen
  (Name, technische Metadaten) schreibgeschuetzt — eine Aenderung dort muesste
  am Ursprungssystem erfolgen und wuerde beim naechsten Sync ohnehin
  ueberschrieben.
* Ein Tool erbt von jedem verknuepften Prozess dessen Einstufung; gilt immer
  das Maximum (Leitdokument A.4.4).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.orm import Session

from app.core.permissions import Principal, Verboten, verlange
from app.models.enums import (
    REICHWEITE_ORDNUNG,
    AssetStatus,
    Herkunft,
    Rolle,
    Zugriffsart,
)
from app.models.governance import (
    Datenobjekt,
    Prozessobjekt,
    ToolDatenobjekt,
    ToolObjekt,
    prozess_tool,
)
from app.models.organisation import Organisationseinheit
from app.services import ableitung
from app.services.changelog import (
    protokolliere_aenderung,
    protokolliere_erstellung,
    protokolliere_loeschung,
    snapshot,
)
from app.services.prozess import (
    NichtGefunden,
    Ungueltig,
    erlaubte_org_ids,
    neueste_bewertung,
)
from app.services.prozess import (
    darf_lesen as darf_prozess_lesen,
)
from app.services.prozess import (
    darf_schreiben as darf_prozess_schreiben,
)

#: Felder, die bei einem importierten Datensatz nur am Ursprungssystem
#: geaendert werden koennen (Architektur 8.3).
STAMMDATENFELDER: frozenset[str] = frozenset({"name", "metadaten", "technologie"})


# --- Vererbung (Leitdokument A.4.4) --------------------------------------


@dataclass
class GeerbteKlassifikation:
    """Was ein Tool-Objekt aus seinen Prozesskanten erbt — immer das Maximum."""

    kritikalitaet: int = 0
    reichweite: str | None = None
    tier: int | None = None
    mitbestimmung_flag: bool = False
    k_klassen: list[str] = field(default_factory=list)
    quelle_prozess_ids: list[uuid.UUID] = field(default_factory=list)


def erbe_klassifikation(tool: ToolObjekt) -> GeerbteKlassifikation:
    """Maximum ueber alle verknuepften Prozessobjekte.

    Ein Tool mit mehreren Prozesskanten traegt die hoechste Einstufung aller
    Kanten — sonst waere die schwaechste Verknuepfung eine stille Umgehung.
    """
    ergebnis = GeerbteKlassifikation()
    k_klassen: set[str] = set()
    for prozess in tool.prozessobjekte:
        ergebnis.quelle_prozess_ids.append(prozess.id)
        ergebnis.kritikalitaet = max(ergebnis.kritikalitaet, prozess.kritikalitaet)
        ergebnis.mitbestimmung_flag = ergebnis.mitbestimmung_flag or prozess.mitbestimmung_flag
        if prozess.reichweite is not None and (
            ergebnis.reichweite is None
            or REICHWEITE_ORDNUNG[prozess.reichweite] > REICHWEITE_ORDNUNG[ergebnis.reichweite]
        ):
            ergebnis.reichweite = prozess.reichweite
        bewertung = neueste_bewertung(prozess)
        if bewertung is not None:
            ergebnis.tier = max(ergebnis.tier or 0, bewertung.tier)
            k_klassen.update(bewertung.ausgeloeste_k_klassen)
    ergebnis.k_klassen = sorted(k_klassen, key=lambda k: int(k[1:]))
    return ergebnis


# --- Sichtbarkeit ---------------------------------------------------------


def tool_sichtbarkeitsbedingung(db: Session, principal: Principal) -> ColumnElement[bool] | None:
    if principal.sieht_global:
        return None
    org_ids = erlaubte_org_ids(db, principal)
    ueber_prozess = select(prozess_tool.c.tool_objekt_id).join(
        Prozessobjekt, Prozessobjekt.id == prozess_tool.c.prozessobjekt_id
    )
    if org_ids:
        ueber_prozess = ueber_prozess.where(Prozessobjekt.prozessgeber_org_id.in_(org_ids))
    else:
        ueber_prozess = ueber_prozess.where(Prozessobjekt.owner_user_id == principal.user_id)
    return or_(
        ToolObjekt.organisationseinheit_id.in_(org_ids) if org_ids else False,
        ToolObjekt.technischer_owner_user_id == principal.user_id,
        ToolObjekt.id.in_(ueber_prozess),
    )


def darf_tool_lesen(db: Session, principal: Principal, tool: ToolObjekt) -> bool:
    if principal.sieht_global:
        return True
    if tool.technischer_owner_user_id == principal.user_id:
        return True
    if tool.organisationseinheit_id in erlaubte_org_ids(db, principal):
        return True
    return any(darf_prozess_lesen(db, principal, p) for p in tool.prozessobjekte)


def darf_tool_schreiben(db: Session, principal: Principal, tool: ToolObjekt) -> bool:
    """Technischer Owner des Tools, Prozess-Owner einer Kante, oder Governance."""
    if principal.ist_governance:
        return True
    if tool.technischer_owner_user_id == principal.user_id:
        return True
    if tool.organisationseinheit_id is not None:
        fachbereich_id = db.execute(
            select(Organisationseinheit.fachbereich_id).where(
                Organisationseinheit.id == tool.organisationseinheit_id
            )
        ).scalar_one_or_none()
        if principal.hat_rolle(
            Rolle.TECHNISCHER_OWNER,
            organisationseinheit_id=tool.organisationseinheit_id,
            fachbereich_id=fachbereich_id,
        ):
            return True
    return any(
        darf_prozess_schreiben(db, principal, p.prozessgeber_org_id) for p in tool.prozessobjekte
    )


def datenobjekt_sichtbarkeitsbedingung(
    db: Session, principal: Principal
) -> ColumnElement[bool] | None:
    """Datenobjekte sind bereichsweit sichtbar, nicht einheitenscharf.

    Ein Datenobjekt wird einmal klassifiziert und von vielen Tool-Objekten
    referenziert (Leitdokument A.4.5); eine engere Sicht wuerde genau diese
    Wiederverwendung behindern. Ein Datenobjekt **ohne** Fachbereich ist
    dagegen niemandem zugeordnet und bleibt den global lesenden Rollen und
    seinem Owner vorbehalten — sonst waere es fuer jeden Angemeldeten sichtbar
    und die Sichtbarkeitsregel aus Architektur 4.3 ausgehebelt.
    """
    if principal.sieht_global:
        return None
    fachbereiche = set(principal.scope_fachbereiche)
    org_ids = principal.scope_organisationseinheiten
    if org_ids:
        fachbereiche.update(
            db.execute(
                select(Organisationseinheit.fachbereich_id).where(
                    Organisationseinheit.id.in_(org_ids)
                )
            ).scalars()
        )
    return or_(
        Datenobjekt.fachbereich_id.in_(fachbereiche) if fachbereiche else False,
        Datenobjekt.owner_user_id == principal.user_id,
    )


def darf_datenobjekt_schreiben(db: Session, principal: Principal, datenobjekt: Datenobjekt) -> bool:
    if principal.ist_governance:
        return True
    if datenobjekt.owner_user_id == principal.user_id:
        return True
    del db
    return principal.hat_rolle(Rolle.DATENOBJEKT_OWNER, fachbereich_id=datenobjekt.fachbereich_id)


# --- Lesen ----------------------------------------------------------------


def hole_tool(db: Session, tool_id: uuid.UUID) -> ToolObjekt:
    tool = db.get(ToolObjekt, tool_id)
    if tool is None:
        raise NichtGefunden("Tool-Objekt nicht gefunden")
    return tool


def hole_tool_sichtbar(db: Session, principal: Principal, tool_id: uuid.UUID) -> ToolObjekt:
    tool = hole_tool(db, tool_id)
    if not darf_tool_lesen(db, principal, tool):
        raise Verboten("Tool-Objekt liegt ausserhalb des eigenen Bereichs")
    return tool


def hole_datenobjekt(db: Session, datenobjekt_id: uuid.UUID) -> Datenobjekt:
    datenobjekt = db.get(Datenobjekt, datenobjekt_id)
    if datenobjekt is None:
        raise NichtGefunden("Datenobjekt nicht gefunden")
    return datenobjekt


def liste_tools(
    db: Session,
    principal: Principal,
    *,
    status: AssetStatus | None = None,
    ohne_prozess: bool = False,
) -> list[ToolObjekt]:
    stmt = select(ToolObjekt)
    bedingung = tool_sichtbarkeitsbedingung(db, principal)
    if bedingung is not None:
        stmt = stmt.where(bedingung)
    if status is not None:
        stmt = stmt.where(ToolObjekt.status == status)
    if ohne_prozess:
        stmt = stmt.where(~ToolObjekt.id.in_(select(prozess_tool.c.tool_objekt_id)))
    return list(db.execute(stmt.order_by(ToolObjekt.name)).scalars())


def liste_datenobjekte(
    db: Session,
    principal: Principal,
    *,
    ohne_kategorie: bool = False,
    status: AssetStatus | None = None,
) -> list[Datenobjekt]:
    stmt = select(Datenobjekt)
    bedingung = datenobjekt_sichtbarkeitsbedingung(db, principal)
    if bedingung is not None:
        stmt = stmt.where(bedingung)
    if ohne_kategorie:
        stmt = stmt.where(Datenobjekt.kategorie.is_(None))
    if status is not None:
        stmt = stmt.where(Datenobjekt.status == status)
    return list(db.execute(stmt.order_by(Datenobjekt.name)).scalars())


# --- Schreiben ------------------------------------------------------------


def _pruefe_stammdatenfelder(objekt: Any, werte: dict[str, Any]) -> None:
    if objekt.herkunft != Herkunft.IMPORTIERT:
        return
    gesperrt = sorted(set(werte) & STAMMDATENFELDER)
    if gesperrt:
        raise Ungueltig(
            "Bei importierten Datensaetzen sind diese Felder am Ursprungssystem zu "
            f"aendern: {', '.join(gesperrt)}"
        )


def lege_tool_an(db: Session, principal: Principal, werte: dict[str, Any]) -> ToolObjekt:
    org_id = werte.get("organisationseinheit_id")
    if org_id is not None and db.get(Organisationseinheit, org_id) is None:
        raise Ungueltig("Organisationseinheit existiert nicht")
    tool = ToolObjekt(herkunft=Herkunft.MANUELL, status=AssetStatus.BESTAETIGT, **werte)
    verlange(
        darf_tool_schreiben(db, principal, tool),
        "Tool-Objekte legt der technische Owner im eigenen Bereich oder die Governance an",
    )
    db.add(tool)
    db.flush()
    protokolliere_erstellung(db, tool, akteur_user_id=principal.user_id)
    return tool


def aendere_tool(
    db: Session, principal: Principal, tool: ToolObjekt, werte: dict[str, Any]
) -> ToolObjekt:
    verlange(
        darf_tool_schreiben(db, principal, tool),
        "Keine Schreibberechtigung fuer dieses Tool-Objekt",
    )
    _pruefe_stammdatenfelder(tool, werte)
    vorher = snapshot(tool)
    for feld, wert in werte.items():
        setattr(tool, feld, wert)
    db.flush()
    protokolliere_aenderung(db, tool, vorher, akteur_user_id=principal.user_id)
    return tool


def bestaetige_tool(db: Session, principal: Principal, tool: ToolObjekt) -> ToolObjekt:
    """Hebt einen importierten Entwurf in den bestaetigten Zustand.

    Erst danach ist eine Verknuepfung mit einem Prozessobjekt moeglich — ein
    unbestaetigtes Tool wuerde sonst eine Klassifikation erben, bevor jemand
    geprueft hat, ob es ueberhaupt das gemeinte Objekt ist (Architektur 7.2).
    """
    verlange(
        darf_tool_schreiben(db, principal, tool) or principal.ist_plattform,
        "Bestaetigen darf der technische Owner oder die Governance-Rolle",
    )
    vorher = snapshot(tool)
    tool.status = AssetStatus.BESTAETIGT
    db.flush()
    protokolliere_aenderung(db, tool, vorher, akteur_user_id=principal.user_id)
    return tool


def lege_datenobjekt_an(db: Session, principal: Principal, werte: dict[str, Any]) -> Datenobjekt:
    datenobjekt = Datenobjekt(herkunft=Herkunft.MANUELL, status=AssetStatus.BESTAETIGT, **werte)
    verlange(
        darf_datenobjekt_schreiben(db, principal, datenobjekt),
        "Datenobjekte legt der Datenobjekt-Owner des Fachbereichs oder die Governance an",
    )
    db.add(datenobjekt)
    db.flush()
    protokolliere_erstellung(db, datenobjekt, akteur_user_id=principal.user_id)
    return datenobjekt


def aendere_datenobjekt(
    db: Session, principal: Principal, datenobjekt: Datenobjekt, werte: dict[str, Any]
) -> Datenobjekt:
    verlange(
        darf_datenobjekt_schreiben(db, principal, datenobjekt),
        "Keine Schreibberechtigung fuer dieses Datenobjekt",
    )
    _pruefe_stammdatenfelder(datenobjekt, werte)
    vorher = snapshot(datenobjekt)
    for feld, wert in werte.items():
        setattr(datenobjekt, feld, wert)
    db.flush()
    protokolliere_aenderung(db, datenobjekt, vorher, akteur_user_id=principal.user_id)
    # Die Kategorie wirkt auf die Ableitungen jedes verknuepften Prozesses
    # (Leitdokument P5): dort wird sie nicht erneut gepflegt, sondern gelesen.
    if "kategorie" in werte:
        aktualisiere_abhaengige_prozesse(db, datenobjekt)
    return datenobjekt


def aktualisiere_abhaengige_prozesse(db: Session, datenobjekt: Datenobjekt) -> list[Prozessobjekt]:
    betroffen: dict[uuid.UUID, Prozessobjekt] = {}
    for prozess in [*datenobjekt.input_fuer_prozesse, *datenobjekt.output_von_prozessen]:
        for weiterer in ableitung.aktualisiere_kette(prozess):
            betroffen[weiterer.id] = weiterer
    db.flush()
    return list(betroffen.values())


def bestaetige_datenobjekt(
    db: Session, principal: Principal, datenobjekt: Datenobjekt
) -> Datenobjekt:
    verlange(
        darf_datenobjekt_schreiben(db, principal, datenobjekt) or principal.ist_plattform,
        "Bestaetigen darf der Datenobjekt-Owner oder die Governance-Rolle",
    )
    vorher = snapshot(datenobjekt)
    datenobjekt.status = AssetStatus.BESTAETIGT
    db.flush()
    protokolliere_aenderung(db, datenobjekt, vorher, akteur_user_id=principal.user_id)
    return datenobjekt


# --- Verknuepfungen -------------------------------------------------------


def verknuepfe_tool_mit_prozess(
    db: Session, principal: Principal, tool: ToolObjekt, prozess: Prozessobjekt
) -> ToolObjekt:
    verlange(
        darf_prozess_schreiben(db, principal, prozess.prozessgeber_org_id)
        or darf_tool_schreiben(db, principal, tool),
        "Verknuepfen darf der Prozess-Owner oder der technische Owner des Tools",
    )
    if tool.status == AssetStatus.IMPORTIERT_UNBESTAETIGT:
        raise Ungueltig(
            "Ein importiertes, noch nicht bestaetigtes Tool-Objekt ist nicht "
            "verknuepfbar — es wuerde sonst eine Klassifikation erben, bevor "
            "jemand geprueft hat, ob es das gemeinte Objekt ist"
        )
    if prozess in tool.prozessobjekte:
        raise Ungueltig("Diese Verknuepfung besteht bereits")
    vorher = snapshot(tool)
    tool.prozessobjekte.append(prozess)
    db.flush()
    protokolliere_aenderung(
        db,
        tool,
        vorher,
        akteur_user_id=principal.user_id,
        beschreibung=f"Verknuepft mit Prozessobjekt {prozess.id}",
    )
    return tool


def loese_tool_von_prozess(
    db: Session, principal: Principal, tool: ToolObjekt, prozess: Prozessobjekt
) -> ToolObjekt:
    verlange(
        darf_prozess_schreiben(db, principal, prozess.prozessgeber_org_id)
        or darf_tool_schreiben(db, principal, tool),
        "Loesen darf der Prozess-Owner oder der technische Owner des Tools",
    )
    if prozess not in tool.prozessobjekte:
        raise NichtGefunden("Diese Verknuepfung besteht nicht")
    vorher = snapshot(tool)
    tool.prozessobjekte.remove(prozess)
    db.flush()
    protokolliere_aenderung(
        db,
        tool,
        vorher,
        akteur_user_id=principal.user_id,
        beschreibung=f"Geloest von Prozessobjekt {prozess.id}",
    )
    return tool


def verknuepfe_tool_mit_datenobjekt(
    db: Session,
    principal: Principal,
    tool: ToolObjekt,
    datenobjekt: Datenobjekt,
    zugriffsart: Zugriffsart,
) -> ToolDatenobjekt:
    verlange(
        darf_tool_schreiben(db, principal, tool),
        "Keine Schreibberechtigung fuer dieses Tool-Objekt",
    )
    bestehend = db.get(ToolDatenobjekt, (tool.id, datenobjekt.id))
    if bestehend is not None:
        raise Ungueltig("Diese Verknuepfung besteht bereits")
    kante = ToolDatenobjekt(
        tool_objekt_id=tool.id, datenobjekt_id=datenobjekt.id, zugriffsart=zugriffsart
    )
    db.add(kante)
    db.flush()
    return kante


def datenobjekte_eines_tools(db: Session, tool_id: uuid.UUID) -> list[ToolDatenobjekt]:
    return list(
        db.execute(
            select(ToolDatenobjekt).where(ToolDatenobjekt.tool_objekt_id == tool_id)
        ).scalars()
    )


def entferne_tool(db: Session, principal: Principal, tool: ToolObjekt) -> None:
    verlange(principal.ist_governance, "Tool-Objekte entfernt ausschliesslich die Governance-Rolle")
    protokolliere_loeschung(db, tool, akteur_user_id=principal.user_id)
    for kante in datenobjekte_eines_tools(db, tool.id):
        db.delete(kante)
    tool.prozessobjekte.clear()
    db.delete(tool)
    db.flush()
