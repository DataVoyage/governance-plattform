"""Governance-Query-API (Architektur 7.3) — Auskunft, keine Aktion.

Diese Schicht liefert **nur Auskuenfte**: sie provisioniert nichts, sie sagt
nur, was der aus dem Prozess abgeleitete Rahmen ist. Jede
Provisionierungsentscheidung bleibt bei der andockenden Anwendung.

Alle Werte kommen aus derselben Fachlogik, die auch der Wizard und die Historie
benutzen — es gibt bewusst keine zweite, abweichende Implementierung der Tier-
und K-Klassen-Ableitung.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.governance import Prozessobjekt, ToolObjekt
from app.services import bewertung as bewertung_service
from app.services import changelog
from app.services.asset import erbe_klassifikation
from app.services.prozess import NichtGefunden, neueste_bewertung

#: Vertragsnamen der Entitaeten in der Delta-Abfrage -> Tabellenname.
ENTITAETEN: dict[str, str] = {
    "prozess": "prozessobjekte",
    "tool": "tool_objekte",
    "datenobjekt": "datenobjekte",
    "bewertung": "bewertungen",
    "compliance_zustand": "compliance_zustaende",
}
TABELLE_ZU_VERTRAG = {v: k for k, v in ENTITAETEN.items()}


def _hole_prozess(db: Session, prozess_id: uuid.UUID) -> Prozessobjekt:
    prozess = db.get(Prozessobjekt, prozess_id)
    if prozess is None:
        raise NichtGefunden("Prozessobjekt nicht gefunden")
    return prozess


def _hole_tool(db: Session, tool_id: uuid.UUID) -> ToolObjekt:
    tool = db.get(ToolObjekt, tool_id)
    if tool is None:
        raise NichtGefunden("Tool-Objekt nicht gefunden")
    return tool


def tier_und_profil(db: Session, prozess_id: uuid.UUID) -> dict:
    """Tier und Sechser-Profil der neuesten Bewertung."""
    prozess = _hole_prozess(db, prozess_id)
    bewertung = neueste_bewertung(prozess)
    if bewertung is None:
        raise NichtGefunden("Fuer dieses Prozessobjekt liegt keine Bewertung vor")
    return {
        "tier": bewertung.tier,
        "profil": {
            "ki": bewertung.ki_stufe,
            "ds": bewertung.ds_stufe,
            "mb": bewertung.mb_stufe,
            "it": bewertung.it_stufe,
            "rg": bewertung.rg_stufe,
            "ur": bewertung.ur_stufe,
        },
    }


def k_klassen(db: Session, prozess_id: uuid.UUID) -> dict:
    """Die ausgeloesten Massnahmenklassen.

    Sie werden hier aus dem gespeicherten Profil neu abgeleitet statt aus dem
    Datensatz gelesen: so kann eine Bewertung, die im schnellen Modus ohne
    K-Klassen gespeichert wurde, trotzdem beantwortet werden — und beide Wege
    benutzen dieselbe Funktion.
    """
    profil = tier_und_profil(db, prozess_id)["profil"]
    return {"ausgeloest": bewertung_service.leite_k_klassen_ab(profil)}


def erlaubnisrahmen(db: Session, tool_id: uuid.UUID) -> dict:
    """Schicht 1 aus Leitdokument A.13.2: was dieses Tool-Objekt darf.

    Der Rahmen ist die Vereinigung ueber alle Prozesskanten — bei der
    Reichweite gilt, wie ueberall, das Maximum (A.4.4).
    """
    tool = _hole_tool(db, tool_id)
    datenobjekte: dict[uuid.UUID, str] = {}
    externe_ziele: list[str] = []
    for prozess in tool.prozessobjekte:
        for datenobjekt in [*prozess.input_datenobjekte, *prozess.output_datenobjekte]:
            datenobjekte[datenobjekt.id] = datenobjekt.name
        for ziel in prozess.erlaubte_externe_ziele or []:
            if ziel not in externe_ziele:
                externe_ziele.append(ziel)

    geerbt = erbe_klassifikation(tool)
    return {
        "erlaubte_datenobjekte": [
            {"id": str(kennung), "name": name} for kennung, name in datenobjekte.items()
        ],
        "erlaubte_reichweite": geerbt.reichweite,
        "erlaubte_externe_ziele": sorted(externe_ziele),
        "tier": geerbt.tier,
        "quelle_prozess_ids": [str(k) for k in geerbt.quelle_prozess_ids],
    }


def aenderungen(
    db: Session, *, since: int = 0, entity_types: list[str] | None = None, limit: int = 500
) -> dict:
    """Delta-Abfrage auf dem ``change_log`` (Architektur 7.3).

    Der Cursor ist die Sequenznummer, keine Zeitangabe — robust gegen
    Uhrzeitverschiebungen zwischen Systemen, und einschliessend gelesen:
    ``naechster_cursor`` aus der Antwort geht beim naechsten Lauf unveraendert
    als ``since`` wieder hinein. Derselbe Wert liefert bei unveraenderter
    Datenlage dasselbe Ergebnis.
    """
    tabellen = None
    if entity_types:
        unbekannt = sorted(set(entity_types) - set(ENTITAETEN))
        if unbekannt:
            raise NichtGefunden(f"Unbekannter entity_type: {', '.join(unbekannt)}")
        tabellen = [ENTITAETEN[t] for t in entity_types]

    eintraege = changelog.eintraege_ab(db, ab_cursor=since, entity_types=tabellen, limit=limit)
    changes = [
        {
            "entity_type": TABELLE_ZU_VERTRAG.get(e.entity_type, e.entity_type),
            "entity_id": str(e.entity_id),
            "aktion": e.aktion,
            "zeitpunkt": e.zeitpunkt.isoformat(),
            "cursor": e.cursor,
        }
        for e in eintraege
    ]
    naechster = changes[-1]["cursor"] + 1 if changes else since
    return {"changes": changes, "naechster_cursor": naechster}
