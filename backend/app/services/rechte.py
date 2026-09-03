"""Was der Anmeldende mit einem einzelnen Objekt tun darf (Architektur 5.2).

Die Oberflaeche darf nicht raten. Bis hierher zeigte sie jedem alles, liess
alles bearbeiten und lieferte den Bescheid erst beim Speichern als 403 — der
Anwender erfuhr also erst nach getaner Arbeit, dass er sie nicht tun durfte.

Die naheliegende Abhilfe waere gewesen, die Regeln im Frontend nachzubauen. Das
waere die zweite Fassung derselben Logik geworden, und zwei Fassungen laufen
auseinander; die eine, die zaehlt, ist immer die andere. Deshalb steht die
Antwort hier: **der Server rechnet, was erlaubt ist, und schreibt es an das
Objekt.** Die Oberflaeche liest es und blendet aus, was nicht geht.

Die Pruefung beim Schreiben bleibt davon unberuehrt. Diese Angaben sind eine
Auskunft, keine Sicherung — wer die API direkt anspricht, laeuft in dieselbe
Pruefung wie zuvor (Architektur 10.2).

**Was hier steht und was nicht.** Hier stehen die Rechte, die vom Objekt
abhaengen: ob jemand *dieses* Prozessobjekt bearbeiten darf, haengt an dessen
Prozessgeber. Rein rollengebundene Rechte — Gate entscheiden, Matrix pflegen,
Einstellungen aendern — stehen nicht hier: sie haengen an keinem Objekt, und
die Oberflaeche kennt die eigenen Rollen ohnehin aus dem Profil.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.permissions import Principal
from app.models.enums import AssetStatus
from app.models.governance import Datenobjekt, Lenkungsvorgang, Prozessobjekt, ToolObjekt
from app.services import asset as asset_service
from app.services import bewertung as bewertung_service
from app.services import prozess as prozess_service


@dataclass(frozen=True)
class Prozessrechte:
    """Was an einem Prozessobjekt moeglich ist."""

    #: Stammdaten aendern, Status wechseln, Kanten pflegen.
    bearbeiten: bool = False
    #: Den Bewertungsbaum durchlaufen (A.8).
    bewerten: bool = False
    #: Die Selbstverpflichtung des Prozesseigners abgeben (A.10.2).
    selbstverpflichten: bool = False
    #: Einen Gate-Vorgang einreichen (A.11).
    gate_einreichen: bool = False
    #: Mindestens eine Umsetzung pflegen — der einzige Schreibweg des
    #: Prozess-Umsetzers (Matrix 5.3).
    umsetzung_pflegen: bool = False


@dataclass(frozen=True)
class Toolrechte:
    """Was an einem Tool-Objekt moeglich ist."""

    bearbeiten: bool = False
    #: Die drei Erklaerungen nach A.6 abgeben.
    attestieren: bool = False
    #: Prozess- und Datenobjektkanten setzen und loesen.
    verknuepfen: bool = False
    #: Einen Compliance-Zustand melden (A.13.3).
    zustand_melden: bool = False
    #: Kompensierende Massnahmen dokumentieren (A.9.3).
    kompensieren: bool = False
    #: Die Selbstverpflichtung des technischen Owners abgeben (A.10.3).
    selbstverpflichten: bool = False
    #: Ein importiertes Objekt bestaetigen (Architektur 7.2).
    bestaetigen: bool = False


@dataclass(frozen=True)
class Datenobjektrechte:
    bearbeiten: bool = False
    bestaetigen: bool = False


@dataclass(frozen=True)
class Lenkungsrechte:
    """Wer den Vorgang schliessen darf (A.13.6)."""

    aufloesen: bool = False
    #: Abbrechen ist der Weg fuer eine Fehlmeldung — nur die Governance.
    abbrechen: bool = False


def fuer_prozess(db: Session, principal: Principal, prozess: Prozessobjekt) -> Prozessrechte:
    schreiben = prozess_service.darf_schreiben(db, principal, prozess.prozessgeber_org_id)
    umsetzung = any(
        prozess_service.darf_umsetzung_bearbeiten(db, principal, u.land_org_id)
        for u in prozess.umsetzungen
    )
    return Prozessrechte(
        bearbeiten=schreiben,
        bewerten=bewertung_service.darf_bewerten(db, principal, prozess),
        selbstverpflichten=schreiben,
        gate_einreichen=schreiben,
        umsetzung_pflegen=umsetzung,
    )


def fuer_tool(db: Session, principal: Principal, tool: ToolObjekt) -> Toolrechte:
    schreiben = asset_service.darf_tool_schreiben(db, principal, tool)
    return Toolrechte(
        bearbeiten=schreiben,
        attestieren=schreiben,
        verknuepfen=schreiben,
        zustand_melden=schreiben,
        kompensieren=schreiben,
        selbstverpflichten=schreiben,
        bestaetigen=(schreiben or principal.ist_plattform)
        and tool.status == AssetStatus.IMPORTIERT_UNBESTAETIGT,
    )


def fuer_datenobjekt(
    db: Session, principal: Principal, datenobjekt: Datenobjekt
) -> Datenobjektrechte:
    schreiben = asset_service.darf_datenobjekt_schreiben(db, principal, datenobjekt)
    return Datenobjektrechte(
        bearbeiten=schreiben,
        bestaetigen=(schreiben or principal.ist_plattform)
        and datenobjekt.status == AssetStatus.IMPORTIERT_UNBESTAETIGT,
    )


def fuer_lenkungsvorgang(
    db: Session, principal: Principal, vorgang: Lenkungsvorgang
) -> Lenkungsrechte:
    tool = db.get(ToolObjekt, vorgang.tool_objekt_id)
    darf = (
        tool is not None and asset_service.darf_tool_schreiben(db, principal, tool)
    ) or vorgang.zugewiesen_an == principal.user_id
    return Lenkungsrechte(
        aufloesen=darf or principal.ist_governance,
        abbrechen=principal.ist_governance,
    )
