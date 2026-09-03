"""Asset-Management-Modul, HTTP-Schicht (Architektur 8.3).

Zwei Ansichten auf dieselben Daten: aus Prozesssicht (welche Tools haengen an
diesem Prozess) und aus Asset-Sicht (an welchen Prozessen haengt dieses Tool,
mit der jeweils hoechsten geerbten Klassifikation).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status
from sqlalchemy.orm import Session

from app.api.deps import AktuellerNutzer, DbSession
from app.core.permissions import Principal
from app.models.enums import AssetStatus, Datenkategorie, Herkunft
from app.models.governance import Datenobjekt, ToolObjekt
from app.schemas.asset import (
    AttestierungAendern,
    DatennutzungAus,
    DatenobjektAendern,
    DatenobjektAnlegen,
    DatenobjektAus,
    DatenobjektrechteAus,
    DatenobjektVerknuepfung,
    GeerbtAus,
    KantenbeitragAus,
    ProzessVerknuepfung,
    ToolAendern,
    ToolAnlegen,
    ToolAus,
    ToolDatenobjektAus,
    ToolrechteAus,
    WirkungAus,
    ZugriffsartAendern,
)
from app.schemas.rahmen import RahmenAus, RahmenElementAus
from app.services import asset as asset_service
from app.services import prozess as prozess_service
from app.services import rahmen as rahmen_service
from app.services import rechte as rechte_service

router = APIRouter(tags=["Assets"])


def _tool_aus(db: Session, principal: Principal, tool: ToolObjekt) -> ToolAus:
    geerbt = asset_service.erbe_klassifikation(tool)
    befund = asset_service.bestimme_wirkungsart(db, tool)
    return ToolAus(
        id=tool.id,
        name=tool.name,
        beschreibung=tool.beschreibung,
        technologie=tool.technologie,
        kategorie=tool.kategorie,
        technischer_owner_user_id=tool.technischer_owner_user_id,
        stellvertretung_user_id=tool.stellvertretung_user_id,
        organisationseinheit_id=tool.organisationseinheit_id,
        lauftyp=tool.lauftyp,
        ausfuehrungsidentitaet=tool.ausfuehrungsidentitaet,
        statische_zugangsdaten=tool.statische_zugangsdaten,
        externe_ziele=list(tool.externe_ziele or []),
        herkunft=tool.herkunft,
        quelle=tool.quelle,
        externe_id=tool.externe_id,
        status=tool.status,
        metadaten=tool.metadaten,
        letzte_aktivitaet_am=tool.letzte_aktivitaet_am,
        prozessobjekt_ids=[p.id for p in tool.prozessobjekte],
        geerbt=GeerbtAus(
            **{
                **vars(geerbt),
                "beitraege": [KantenbeitragAus(**vars(b)) for b in geerbt.beitraege],
            }
        ),
        attest_entscheidung_ueber_personen=tool.attest_entscheidung_ueber_personen,
        attest_mensch_dazwischen=tool.attest_mensch_dazwischen,
        attest_undeklarierte_quellen=tool.attest_undeklarierte_quellen,
        attestiert_am=tool.attestiert_am,
        attestiert_von_user_id=tool.attestiert_von_user_id,
        attestierung_vollstaendig=asset_service.attestierung_vollstaendig(tool),
        wirkungsart=befund.art,
        wirkungsart_grund=befund.grund,
        schreibgeschuetzte_felder=_gesperrt(tool),
        rechte=ToolrechteAus(**vars(rechte_service.fuer_tool(db, principal, tool))),
    )


def _gesperrt(objekt) -> list[str]:
    if objekt.herkunft != Herkunft.IMPORTIERT:
        return []
    return sorted(f for f in asset_service.STAMMDATENFELDER if hasattr(objekt, f))


def _datenobjekt_aus(db: Session, principal: Principal, datenobjekt: Datenobjekt) -> DatenobjektAus:
    ausgabe = DatenobjektAus.model_validate(datenobjekt)
    ausgabe.schreibgeschuetzte_felder = _gesperrt(datenobjekt)
    ausgabe.rechte = DatenobjektrechteAus(
        **vars(rechte_service.fuer_datenobjekt(db, principal, datenobjekt))
    )
    return ausgabe


# --- Tool-Objekte ---------------------------------------------------------


@router.get("/tools", response_model=list[ToolAus])
def liste_tools(
    principal: AktuellerNutzer,
    db: DbSession,
    status_filter: AssetStatus | None = None,
    ohne_prozess: bool = False,
) -> list[ToolAus]:
    treffer = asset_service.liste_tools(
        db, principal, status=status_filter, ohne_prozess=ohne_prozess
    )
    return [_tool_aus(db, principal, t) for t in treffer]


@router.post("/tools", response_model=ToolAus, status_code=status.HTTP_201_CREATED)
def lege_tool_an(daten: ToolAnlegen, principal: AktuellerNutzer, db: DbSession) -> ToolAus:
    return _tool_aus(db, principal, asset_service.lege_tool_an(db, principal, daten.model_dump()))


@router.get("/tools/{tool_id}", response_model=ToolAus)
def tool_detail(tool_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> ToolAus:
    return _tool_aus(db, principal, asset_service.hole_tool_sichtbar(db, principal, tool_id))


@router.patch("/tools/{tool_id}", response_model=ToolAus)
def aendere_tool(
    tool_id: uuid.UUID, daten: ToolAendern, principal: AktuellerNutzer, db: DbSession
) -> ToolAus:
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    return _tool_aus(
        db,
        principal,
        asset_service.aendere_tool(db, principal, tool, daten.model_dump(exclude_unset=True)),
    )


@router.post("/tools/{tool_id}/bestaetigung", response_model=ToolAus)
def bestaetige_tool(tool_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> ToolAus:
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    return _tool_aus(db, principal, asset_service.bestaetige_tool(db, principal, tool))


@router.delete("/tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
def entferne_tool(tool_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> None:
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    asset_service.entferne_tool(db, principal, tool)


@router.post(
    "/tools/{tool_id}/prozesse", response_model=ToolAus, status_code=status.HTTP_201_CREATED
)
def verknuepfe_prozess(
    tool_id: uuid.UUID,
    daten: ProzessVerknuepfung,
    principal: AktuellerNutzer,
    db: DbSession,
) -> ToolAus:
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    prozess = prozess_service.hole_sichtbar(db, principal, daten.prozessobjekt_id)
    return _tool_aus(
        db, principal, asset_service.verknuepfe_tool_mit_prozess(db, principal, tool, prozess)
    )


@router.delete("/tools/{tool_id}/prozesse/{prozess_id}", response_model=ToolAus)
def loese_prozess(
    tool_id: uuid.UUID, prozess_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession
) -> ToolAus:
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    prozess = prozess_service.hole_sichtbar(db, principal, prozess_id)
    return _tool_aus(
        db, principal, asset_service.loese_tool_von_prozess(db, principal, tool, prozess)
    )


@router.put("/tools/{tool_id}/attestierungen", response_model=ToolAus)
def attestiere_tool(
    tool_id: uuid.UUID,
    daten: AttestierungAendern,
    principal: AktuellerNutzer,
    db: DbSession,
) -> ToolAus:
    """Die drei Erklaerungen aus Leitdokument A.6.

    Zeitpunkt und Person setzt der Server: A.6 verlangt die Attestierung „mit
    Namen, nicht als Formularfeld", und ein mitgeschicktes Datum waere kein
    Nachweis.
    """
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    return _tool_aus(
        db, principal, asset_service.attestiere(db, principal, tool, daten.model_dump())
    )


@router.get("/tools/{tool_id}/erlaubnisrahmen", response_model=RahmenAus)
def erlaubnisrahmen(tool_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> RahmenAus:
    """Die sieben Elemente aus A.13.2 Schicht 1, je mit ihrer Messung.

    Die Query-API liefert dieselben Werte fuer andockende Anwendungen, aber nur
    die erlaubte Seite. Hier steht die gemessene daneben, weil hier jemand
    sitzt, der eine Abweichung abstellen kann.
    """
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    befund = rahmen_service.erlaubnisrahmen(db, tool)
    return RahmenAus(
        elemente=[
            RahmenElementAus(
                schluessel=element.schluessel,
                erlaubt=list(element.erlaubt),
                gemessen=list(element.gemessen),
                abweichung=list(element.abweichung),
                messbar=element.messbar,
                eingehalten=element.eingehalten,
            )
            for element in befund.elemente
        ],
        tier=befund.tier,
        quelle_prozess_ids=befund.quelle_prozess_ids,
        eingehalten=befund.eingehalten,
        schicht2_befunde=rahmen_service.pruefe_schicht2(tool),
    )


@router.get("/tools/{tool_id}/datenobjekte", response_model=list[DatennutzungAus])
def datenobjekte_eines_tools(tool_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession) -> list:
    """Genutzte Datenobjekte samt Zweckbindungspruefung (Leitdokument A.4.6)."""
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    return asset_service.pruefe_zweckbindung(db, tool)


@router.post(
    "/tools/{tool_id}/datenobjekte",
    response_model=ToolDatenobjektAus,
    status_code=status.HTTP_201_CREATED,
)
def verknuepfe_datenobjekt(
    tool_id: uuid.UUID,
    daten: DatenobjektVerknuepfung,
    principal: AktuellerNutzer,
    db: DbSession,
):
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    datenobjekt = asset_service.hole_datenobjekt(db, daten.datenobjekt_id)
    return asset_service.verknuepfe_tool_mit_datenobjekt(
        db, principal, tool, datenobjekt, daten.zugriffsart
    )


@router.patch("/tools/{tool_id}/datenobjekte/{datenobjekt_id}", response_model=ToolDatenobjektAus)
def aendere_zugriffsart(
    tool_id: uuid.UUID,
    datenobjekt_id: uuid.UUID,
    daten: ZugriffsartAendern,
    principal: AktuellerNutzer,
    db: DbSession,
):
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    return asset_service.aendere_zugriffsart(db, principal, tool, datenobjekt_id, daten.zugriffsart)


@router.delete(
    "/tools/{tool_id}/datenobjekte/{datenobjekt_id}", status_code=status.HTTP_204_NO_CONTENT
)
def loese_datenobjekt(
    tool_id: uuid.UUID,
    datenobjekt_id: uuid.UUID,
    principal: AktuellerNutzer,
    db: DbSession,
) -> None:
    tool = asset_service.hole_tool_sichtbar(db, principal, tool_id)
    asset_service.loese_tool_von_datenobjekt(db, principal, tool, datenobjekt_id)


# --- Datenobjekte ---------------------------------------------------------


@router.get("/datenobjekte", response_model=list[DatenobjektAus])
def liste_datenobjekte(
    principal: AktuellerNutzer,
    db: DbSession,
    ohne_kategorie: bool = False,
    status_filter: AssetStatus | None = None,
) -> list[DatenobjektAus]:
    treffer = asset_service.liste_datenobjekte(
        db, principal, ohne_kategorie=ohne_kategorie, status=status_filter
    )
    return [_datenobjekt_aus(db, principal, d) for d in treffer]


@router.post("/datenobjekte", response_model=DatenobjektAus, status_code=status.HTTP_201_CREATED)
def lege_datenobjekt_an(
    daten: DatenobjektAnlegen, principal: AktuellerNutzer, db: DbSession
) -> DatenobjektAus:
    return _datenobjekt_aus(
        db, principal, asset_service.lege_datenobjekt_an(db, principal, daten.model_dump())
    )


@router.get("/datenobjekte/{datenobjekt_id}", response_model=DatenobjektAus)
def datenobjekt_detail(
    datenobjekt_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession
) -> DatenobjektAus:
    # Der Principal wird jetzt gebraucht: die Antwort traegt, was er mit
    # diesem Datenobjekt tun darf.
    return _datenobjekt_aus(db, principal, asset_service.hole_datenobjekt(db, datenobjekt_id))


@router.patch("/datenobjekte/{datenobjekt_id}", response_model=DatenobjektAus)
def aendere_datenobjekt(
    datenobjekt_id: uuid.UUID,
    daten: DatenobjektAendern,
    principal: AktuellerNutzer,
    db: DbSession,
) -> DatenobjektAus:
    datenobjekt = asset_service.hole_datenobjekt(db, datenobjekt_id)
    return _datenobjekt_aus(
        db,
        principal,
        asset_service.aendere_datenobjekt(
            db, principal, datenobjekt, daten.model_dump(exclude_unset=True)
        ),
    )


@router.post("/datenobjekte/{datenobjekt_id}/bestaetigung", response_model=DatenobjektAus)
def bestaetige_datenobjekt(
    datenobjekt_id: uuid.UUID, principal: AktuellerNutzer, db: DbSession
) -> DatenobjektAus:
    datenobjekt = asset_service.hole_datenobjekt(db, datenobjekt_id)
    return _datenobjekt_aus(
        db, principal, asset_service.bestaetige_datenobjekt(db, principal, datenobjekt)
    )


@router.get("/datenobjekte/{datenobjekt_id}/wirkung", response_model=WirkungAus)
def wirkung_einer_umklassifizierung(
    datenobjekt_id: uuid.UUID,
    principal: AktuellerNutzer,
    db: DbSession,
    kategorie: Datenkategorie | None = None,
) -> WirkungAus:
    """Wer waere von einer neuen Kategorie betroffen (Leitdokument A.4.7)?

    Ohne ``kategorie`` beschreibt die Antwort den heutigen Stand — dieselbe
    Abfrage dient damit auch als Rueckwaertssicht auf ein Datenobjekt.
    """
    del principal
    datenobjekt = asset_service.hole_datenobjekt(db, datenobjekt_id)
    return WirkungAus(**asset_service.wirkung_der_kategorie(db, datenobjekt, kategorie))
