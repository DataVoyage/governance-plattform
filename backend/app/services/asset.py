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

from sqlalchemy import ColumnElement, false, or_, select
from sqlalchemy.orm import Session

from app.core.permissions import Principal, Verboten, verlange
from app.models.base import now_utc
from app.models.enums import (
    REICHWEITE_ORDNUNG,
    SCHREIBENDE_ZUGRIFFSARTEN,
    AssetStatus,
    Datenkategorie,
    Herkunft,
    Rolle,
    ScopeTyp,
    Wirkungsart,
    Zugriffsart,
)
from app.models.governance import (
    Datenobjekt,
    Prozessobjekt,
    ToolDatenobjekt,
    ToolObjekt,
    prozess_input_datenobjekte,
    prozess_output_datenobjekte,
    prozess_tool,
)
from app.models.organisation import Fachbereich, Organisationseinheit
from app.services import ableitung
from app.services.changelog import (
    protokolliere_aenderung,
    protokolliere_erstellung,
    protokolliere_kante,
    protokolliere_loeschung,
    snapshot,
)
from app.services.prozess import (
    NichtGefunden,
    Ungueltig,
    eigene_prozess_bedingung,
    erlaubte_org_ids,
    neueste_bewertung,
)
from app.services.prozess import (
    darf_schreiben as darf_prozess_schreiben,
)
from app.services.prozess import (
    sichtbarkeitsbedingung as prozess_sichtbarkeitsbedingung,
)

#: Felder, die bei einem importierten Datensatz nur am Ursprungssystem
#: geaendert werden koennen (Architektur 8.3).
STAMMDATENFELDER: frozenset[str] = frozenset({"name", "metadaten", "technologie"})


# --- Vererbung (Leitdokument A.4.4) --------------------------------------


@dataclass
class Kantenbeitrag:
    """Was eine einzelne Prozesskante zum Erbe beitraegt.

    Ohne diese Aufschluesselung ist das Maximum eine Zahl ohne Adresse: der
    technische Owner sieht „Tier 3", aber nicht, welcher Prozess sie
    verantwortet — und damit auch nicht, wo er ansetzen muesste.
    """

    prozess_id: uuid.UUID
    name: str
    kritikalitaet: int = 0
    reichweite: str | None = None
    tier: int | None = None
    mitbestimmung_flag: bool = False
    k_klassen: list[str] = field(default_factory=list)
    #: Diese Kante bestimmt das geerbte Maximum in mindestens einem Feld.
    massgeblich: bool = False


@dataclass
class GeerbteKlassifikation:
    """Was ein Tool-Objekt aus seinen Prozesskanten erbt — immer das Maximum."""

    kritikalitaet: int = 0
    reichweite: str | None = None
    tier: int | None = None
    mitbestimmung_flag: bool = False
    k_klassen: list[str] = field(default_factory=list)
    quelle_prozess_ids: list[uuid.UUID] = field(default_factory=list)
    beitraege: list[Kantenbeitrag] = field(default_factory=list)


def erbe_klassifikation(tool: ToolObjekt) -> GeerbteKlassifikation:
    """Maximum ueber alle verknuepften Prozessobjekte.

    Ein Tool mit mehreren Prozesskanten traegt die hoechste Einstufung aller
    Kanten — sonst waere die schwaechste Verknuepfung eine stille Umgehung.
    Jede Kante wird zusaetzlich einzeln ausgewiesen und die massgebliche
    markiert (Leitdokument A.4.4: das Maximum bleibt nachvollziehbar).
    """
    ergebnis = GeerbteKlassifikation()
    k_klassen: set[str] = set()
    for prozess in tool.prozessobjekte:
        bewertung = neueste_bewertung(prozess)
        beitrag = Kantenbeitrag(
            prozess_id=prozess.id,
            name=prozess.name,
            kritikalitaet=prozess.kritikalitaet,
            reichweite=prozess.reichweite,
            tier=bewertung.tier if bewertung is not None else None,
            mitbestimmung_flag=prozess.mitbestimmung_flag,
            k_klassen=sorted(
                bewertung.ausgeloeste_k_klassen if bewertung is not None else [],
                key=lambda k: int(k[1:]),
            ),
        )
        ergebnis.beitraege.append(beitrag)
        ergebnis.quelle_prozess_ids.append(prozess.id)
        ergebnis.kritikalitaet = max(ergebnis.kritikalitaet, prozess.kritikalitaet)
        ergebnis.mitbestimmung_flag = ergebnis.mitbestimmung_flag or prozess.mitbestimmung_flag
        if prozess.reichweite is not None and (
            ergebnis.reichweite is None
            or REICHWEITE_ORDNUNG[prozess.reichweite] > REICHWEITE_ORDNUNG[ergebnis.reichweite]
        ):
            ergebnis.reichweite = prozess.reichweite
        if bewertung is not None:
            ergebnis.tier = max(ergebnis.tier or 0, bewertung.tier)
            k_klassen.update(bewertung.ausgeloeste_k_klassen)
    ergebnis.k_klassen = sorted(k_klassen, key=lambda k: int(k[1:]))
    for beitrag in ergebnis.beitraege:
        beitrag.massgeblich = (
            beitrag.kritikalitaet == ergebnis.kritikalitaet
            or (beitrag.reichweite is not None and beitrag.reichweite == ergebnis.reichweite)
            or (beitrag.tier is not None and beitrag.tier == ergebnis.tier)
        )
    return ergebnis


# --- Attestierungen und Wirkungsart (Leitdokument A.6) -------------------

#: Die drei Erklaerungen, die Telemetrie nicht liefern kann.
ATTESTIERUNGSFELDER: tuple[str, ...] = (
    "attest_entscheidung_ueber_personen",
    "attest_mensch_dazwischen",
    "attest_undeklarierte_quellen",
)


def attestierung_vollstaendig(tool: ToolObjekt) -> bool:
    """Alle drei Fragen beantwortet? ``None`` ist keine Antwort."""
    return all(getattr(tool, feld) is not None for feld in ATTESTIERUNGSFELDER)


@dataclass
class WirkungsartBefund:
    """Ergebnis der Triage aus A.6, samt dem Signal, das sie traegt."""

    art: Wirkungsart | None = None
    #: ``schreibzugriff`` | ``kein_mensch`` | ``nur_lesend`` | ``offen``
    grund: str = "offen"


def bestimme_wirkungsart(db: Session, tool: ToolObjekt) -> WirkungsartBefund:
    """Veraendert das Tool den Prozessausgang, oder gestaltet es nur?

    A.6 stellt drei Signale nebeneinander: Schreibzugriff macht ein Tool immer
    veraendernd; fehlt ein Mensch zwischen Output und Wirkung, ist es das auch
    bei reinem Lesen. Der umgekehrte Schluss braucht Attestierung 2 — ohne sie
    bleibt die Frage offen, statt „gestaltend" zu behaupten.
    """
    schreibend = any(
        kante.zugriffsart in SCHREIBENDE_ZUGRIFFSARTEN
        for kante in datenobjekte_eines_tools(db, tool.id)
    )
    if schreibend:
        return WirkungsartBefund(Wirkungsart.VERAENDERND, "schreibzugriff")
    if tool.attest_mensch_dazwischen is False:
        return WirkungsartBefund(Wirkungsart.VERAENDERND, "kein_mensch")
    if tool.attest_mensch_dazwischen is None:
        return WirkungsartBefund(None, "offen")
    return WirkungsartBefund(Wirkungsart.GESTALTEND, "nur_lesend")


def attestiere(
    db: Session, principal: Principal, tool: ToolObjekt, antworten: dict[str, Any]
) -> ToolObjekt:
    """Nimmt die drei Erklaerungen entgegen — mit Namen und Zeitpunkt.

    A.6 verlangt die Attestierung ausdruecklich „mit Namen, nicht als
    Formularfeld". Wer erklaert hat und wann, setzt deshalb der Server; die
    Oberflaeche kann es nicht mitschicken.
    """
    verlange(
        darf_tool_schreiben(db, principal, tool),
        "Attestieren darf der technische Owner des Tools oder die Governance",
    )
    vorher = snapshot(tool)
    for feld in ATTESTIERUNGSFELDER:
        setattr(tool, feld, antworten[feld])
    tool.attestiert_am = now_utc()
    tool.attestiert_von_user_id = principal.user_id
    db.flush()
    protokolliere_aenderung(
        db,
        tool,
        vorher,
        akteur_user_id=principal.user_id,
        beschreibung="Attestierungen nach A.6 erklaert",
    )
    # Attestierung 1 ist eine der beiden Quellen fuer die zweite Haelfte der
    # Mitbestimmungsregel (A.5) — jede Prozesskante wird deshalb neu abgeleitet.
    for prozess in tool.prozessobjekte:
        ableitung.aktualisiere_kette(prozess)
    db.flush()
    return tool


# --- Sichtbarkeit ---------------------------------------------------------


def tool_sichtbarkeitsbedingung(db: Session, principal: Principal) -> ColumnElement[bool] | None:
    """Eigene Tool-Objekte, plus die an einem selbst verantworteten Prozess.

    „Eigen" heisst: technischer Owner an der Einheit des Tools, oder
    persoenlich als Owner beziehungsweise Stellvertretung eingetragen. Der
    zweite Weg ist die Prozesskante — der Prozess-Owner muss sehen, womit sein
    Prozess umgesetzt wird, sonst kann er den Erlaubnisrahmen nicht beurteilen
    (A.13.2). Beide Wege sind rollenscharf (R-7).
    """
    if principal.sieht_global:
        return None
    org_ids = erlaubte_org_ids(db, principal, Rolle.TECHNISCHER_OWNER)
    ueber_prozess = select(prozess_tool.c.tool_objekt_id).where(
        prozess_tool.c.prozessobjekt_id.in_(
            select(Prozessobjekt.id).where(eigene_prozess_bedingung(db, principal))
        )
    )
    return or_(
        ToolObjekt.organisationseinheit_id.in_(org_ids) if org_ids else false(),
        ToolObjekt.technischer_owner_user_id == principal.user_id,
        ToolObjekt.stellvertretung_user_id == principal.user_id,
        ToolObjekt.id.in_(ueber_prozess),
    )


def darf_tool_lesen(db: Session, principal: Principal, tool: ToolObjekt) -> bool:
    """Dieselbe Bedingung wie die Liste, am Einzelstueck (E-54)."""
    bedingung = tool_sichtbarkeitsbedingung(db, principal)
    if bedingung is None:
        return True
    return (
        db.execute(
            select(ToolObjekt.id).where(ToolObjekt.id == tool.id, bedingung)
        ).scalar_one_or_none()
        is not None
    )


def darf_tool_schreiben(db: Session, principal: Principal, tool: ToolObjekt) -> bool:
    """Technischer Owner des Tools, seine Stellvertretung, oder die Governance.

    Der Prozess-Owner einer Kante steht hier bewusst **nicht**: das Tool gehoert
    ihm nicht. Er darf die Kante an seinem Prozess setzen und loesen — dafuer
    gibt es ``darf_tool_verknuepfen`` —, aber nicht die Technologie aendern und
    erst recht nicht attestieren: A.10.3 verlangt die Erklaerung persoenlich
    vom Entwickler, und eine Erklaerung, die ein anderer abgeben kann, ist
    keine (docs/rollen-und-scopes.md, Abschnitt 5).
    """
    if principal.ist_governance:
        return True
    if tool.technischer_owner_user_id == principal.user_id:
        return True
    if tool.stellvertretung_user_id == principal.user_id:
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
    return False


def darf_tool_verknuepfen(db: Session, principal: Principal, tool: ToolObjekt) -> bool:
    """Kanten setzen und loesen — beide Enden zaehlen.

    Eine Verknuepfung hat zwei Seiten: den Prozess und das Tool. Wer eine davon
    verantwortet, darf sie knuepfen (A.4.4). Deshalb hier zusaetzlich der
    Prozess-Owner eines bereits verknuepften Prozesses — und nur hier.
    """
    if darf_tool_schreiben(db, principal, tool):
        return True
    return any(
        darf_prozess_schreiben(db, principal, p.prozessgeber_org_id) for p in tool.prozessobjekte
    )


# --- Datenobjekte: Sicht und Schreibrecht (docs/rollen-und-scopes.md, 7) ---
#
# Ein Datenobjekt ist eine Quelle, kein Werk. Es hat genau einen Anker — den
# Fachbereich als datenhaltende Stelle — und keine Person. Wer es sieht, sieht
# es ueber diesen Anker (als Datenobjekt-Owner) oder ueber eine Referenz (der
# eigene Prozess nutzt es, das eigene Tool greift darauf zu). Wer es schreibt,
# ist nach Feld verschieden: die Kategorie wirkt in jeden referenzierenden
# Prozess, deshalb setzt sie nur die Stelle, die die Daten haelt.
#
# Alle Regeln stehen hier und nur hier. Die Sichtbedingung ist SQL, damit die
# Liste filtert; das Einzelstueck wird gegen dieselbe Bedingung geprueft, damit
# Liste und Direktaufruf nie auseinanderlaufen (E-54).


def datenobjekt_owner_fachbereiche(principal: Principal) -> set[uuid.UUID]:
    """Die Fachbereiche, in denen der Principal Datenobjekt-Owner ist.

    Nur Fachbereichs-Scopes zaehlen — eine Quelle gehoert einer Stelle, nicht
    einer Landesorganisation; die Rollenvergabe lehnt Einheiten fuer diese
    Rolle ab (R-11). Und nur *diese* Rolle zaehlt: ein Prozess-Umsetzer im
    selben Fachbereich hat den Bereich, aber nicht dieses Recht.
    """
    return {
        z.scope_id
        for z in principal.zuweisungen
        if z.rolle == Rolle.DATENOBJEKT_OWNER
        and z.scope_typ == ScopeTyp.FACHBEREICH
        and z.scope_id is not None
    }


def datenobjekt_sichtbarkeitsbedingung(
    db: Session, principal: Principal
) -> ColumnElement[bool] | None:
    """Eigener Fachbereich als Datenobjekt-Owner, oder ueber eine Referenz.

    Die Referenz laeuft ueber die Sichtregeln der anderen Objekte: was an einem
    sichtbaren Prozess als Input oder Output haengt, was ein sichtbares Tool
    liest oder schreibt. Ein Prozess-Owner sieht also die Quellen, die seine
    Prozesse beruehren — nicht die uebrigen seines Fachbereichs, denn dafuer
    gibt es keinen Grund. Ohne Fachbereich (vorgefunden, unbestaetigt) bleibt
    ein Datenobjekt den globalen Rollen vorbehalten.
    """
    if principal.sieht_global:
        return None
    eigene = datenobjekt_owner_fachbereiche(principal)
    sichtbare_prozesse = select(Prozessobjekt.id).where(
        prozess_sichtbarkeitsbedingung(db, principal)
    )
    ueber_input = select(prozess_input_datenobjekte.c.datenobjekt_id).where(
        prozess_input_datenobjekte.c.prozessobjekt_id.in_(sichtbare_prozesse)
    )
    ueber_output = select(prozess_output_datenobjekte.c.datenobjekt_id).where(
        prozess_output_datenobjekte.c.prozessobjekt_id.in_(sichtbare_prozesse)
    )
    sichtbare_tools = select(ToolObjekt.id).where(tool_sichtbarkeitsbedingung(db, principal))
    ueber_tool = select(ToolDatenobjekt.datenobjekt_id).where(
        ToolDatenobjekt.tool_objekt_id.in_(sichtbare_tools)
    )
    return or_(
        Datenobjekt.fachbereich_id.in_(eigene) if eigene else False,
        Datenobjekt.id.in_(ueber_input),
        Datenobjekt.id.in_(ueber_output),
        Datenobjekt.id.in_(ueber_tool),
    )


def darf_datenobjekt_lesen(db: Session, principal: Principal, datenobjekt: Datenobjekt) -> bool:
    """Dieselbe Bedingung wie die Liste, am Einzelstueck — wortwoertlich dieselbe."""
    bedingung = datenobjekt_sichtbarkeitsbedingung(db, principal)
    if bedingung is None:
        return True
    treffer = db.execute(
        select(Datenobjekt.id).where(Datenobjekt.id == datenobjekt.id, bedingung)
    ).scalar_one_or_none()
    return treffer is not None


def ist_datenobjekt_owner(principal: Principal, datenobjekt: Datenobjekt) -> bool:
    return (
        datenobjekt.fachbereich_id is not None
        and datenobjekt.fachbereich_id in datenobjekt_owner_fachbereiche(principal)
    )


def traegt_gebenden_prozess(db: Session, principal: Principal, datenobjekt: Datenobjekt) -> bool:
    """Der gebende Prozess ist der, der die Daten erzeugt — er hat sie als Output.

    Kein eigenes Feld: er ergibt sich aus den Kanten (P1). Wer ihn traegt, darf
    die Stammdaten der Quelle pflegen, denn er verantwortet, was dort entsteht.
    """
    return any(
        darf_prozess_schreiben(db, principal, p.prozessgeber_org_id)
        for p in datenobjekt.output_von_prozessen
    )


def darf_datenobjekt_schreiben(db: Session, principal: Principal, datenobjekt: Datenobjekt) -> bool:
    """Stammdaten — Name, Beschreibung, Quellsystem (7.4)."""
    if principal.ist_governance:
        return True
    if ist_datenobjekt_owner(principal, datenobjekt):
        return True
    return traegt_gebenden_prozess(db, principal, datenobjekt)


def darf_datenobjekt_kategorisieren(principal: Principal, datenobjekt: Datenobjekt) -> bool:
    """Die Kategorie setzt die Stelle, die die Daten haelt — nicht die, die sie erzeugt."""
    return principal.ist_governance or ist_datenobjekt_owner(principal, datenobjekt)


def darf_datenobjekt_anker_aendern(principal: Principal, datenobjekt: Datenobjekt) -> bool:
    """Ein Anker wandert nicht — ausser durch die Governance, oder durch die
    Plattform bei einem vorgefundenen Objekt, das noch keinen hat."""
    if principal.ist_governance:
        return True
    return principal.ist_plattform and datenobjekt.status == AssetStatus.IMPORTIERT_UNBESTAETIGT


def darf_datenobjekt_bestaetigen(principal: Principal, datenobjekt: Datenobjekt) -> bool:
    return (
        principal.ist_governance
        or principal.ist_plattform
        or ist_datenobjekt_owner(principal, datenobjekt)
    )


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


def hole_datenobjekt_sichtbar(
    db: Session, principal: Principal, datenobjekt_id: uuid.UUID
) -> Datenobjekt:
    """Wie ``hole_datenobjekt``, aber nur im eigenen Bereich.

    Kein 404-Verstecken: die Existenz ist unkritisch, der Inhalt nicht —
    dieselbe Linie wie bei Prozess- und Tool-Objekten.
    """
    datenobjekt = hole_datenobjekt(db, datenobjekt_id)
    if not darf_datenobjekt_lesen(db, principal, datenobjekt):
        raise Verboten("Datenobjekt liegt außerhalb des eigenen Bereichs")
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


def liste_datenobjekt_katalog(db: Session, principal: Principal) -> list[Datenobjekt]:
    """Jede bestaetigte, zugeordnete Quelle — fuer die Auswahl, nicht fuer die Pflege.

    Ohne den Katalog koennte ein Prozess-Owner im Vertrieb die
    Personalstammdaten nicht als Input waehlen, und genau diese
    bereichsuebergreifende Wiederverwendung ist der Sinn von A.7. Wer keine
    Rolle hat, bekommt auch ihn nicht.
    """
    verlange(bool(principal.rollen), "Der Katalog steht nur Rollentraegern offen")
    stmt = (
        select(Datenobjekt)
        .where(
            Datenobjekt.status == AssetStatus.BESTAETIGT,
            Datenobjekt.fachbereich_id.is_not(None),
        )
        .order_by(Datenobjekt.name)
    )
    return list(db.execute(stmt).scalars())


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
    """Anlegen entscheidet der **Anker**, nie die Nutzlast.

    Bis AP-13 wurde das Objekt erst aus den uebergebenen Werten gebaut und dann
    gefragt, ob es geschrieben werden darf. Wer sich selbst als technischen
    Owner eintrug, erfuellte damit die Bedingung, die er gerade erst gesetzt
    hatte — jeder Angemeldete konnte so ein Tool-Objekt anlegen, attestieren
    und an einen fremden Prozess haengen (E-58, R-16). Eine Angabe des
    Antragstellers darf nie die Erlaubnis begruenden, ueber die sie entscheidet.

    Deshalb zwei Aenderungen: die Einheit ist Pflicht, und geprueft wird die
    Rolle **an dieser Einheit**. Wen der Anlegende als Owner eintraegt, ist
    danach eine Angabe wie jede andere.
    """
    org_id = werte.get("organisationseinheit_id")
    if org_id is None:
        raise Ungueltig(
            "Ein Tool-Objekt gehoert einer Organisationseinheit: ohne sie gehoerte es "
            "niemandem und waere nur den global lesenden Rollen sichtbar"
        )
    einheit = db.get(Organisationseinheit, org_id)
    if einheit is None:
        raise Ungueltig("Organisationseinheit existiert nicht")
    verlange(
        principal.ist_governance
        or principal.hat_rolle(
            Rolle.TECHNISCHER_OWNER,
            organisationseinheit_id=org_id,
            fachbereich_id=einheit.fachbereich_id,
        ),
        "Tool-Objekte legt der technische Owner dieser Einheit oder die Governance an",
    )
    tool = ToolObjekt(herkunft=Herkunft.MANUELL, status=AssetStatus.BESTAETIGT, **werte)
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
    """Anlegen heisst: einen Fachbereich bekommen. Zwei Wege, kein dritter (7.2).

    Ueber den gebenden Prozess: der Fachbereich ist der des Prozessgebers, das
    Datenobjekt haengt als Output daran, und anlegen darf, wer den Prozess
    schreiben darf. Oder ueber den Fachbereich selbst: dann muss der Anlegende
    dessen Datenobjekt-Owner sein. Ein manuelles Datenobjekt ohne Fachbereich
    gibt es nicht — es gehoerte niemandem und waere nur global sichtbar.
    """
    werte = dict(werte)
    prozess_id = werte.pop("prozessobjekt_id", None)
    gebender: Prozessobjekt | None = None
    if prozess_id is not None:
        gebender = db.get(Prozessobjekt, prozess_id)
        if gebender is None:
            raise Ungueltig("Der gebende Prozess existiert nicht")
        verlange(
            darf_prozess_schreiben(db, principal, gebender.prozessgeber_org_id),
            "Als Output anlegen darf nur der Prozess-Owner des gebenden Prozesses",
        )
        werte["fachbereich_id"] = db.execute(
            select(Organisationseinheit.fachbereich_id).where(
                Organisationseinheit.id == gebender.prozessgeber_org_id
            )
        ).scalar_one()
    if werte.get("fachbereich_id") is None:
        raise Ungueltig(
            "Ein Datenobjekt gehoert einem Fachbereich: entweder den gebenden Prozess "
            "nennen oder den Fachbereich, dessen Datenobjekt-Owner Sie sind"
        )
    if db.get(Fachbereich, werte["fachbereich_id"]) is None:
        raise Ungueltig("Fachbereich existiert nicht")
    datenobjekt = Datenobjekt(herkunft=Herkunft.MANUELL, status=AssetStatus.BESTAETIGT, **werte)
    if gebender is None:
        verlange(
            principal.ist_governance or ist_datenobjekt_owner(principal, datenobjekt),
            "Datenobjekte legt der Datenobjekt-Owner des Fachbereichs, der Owner des "
            "gebenden Prozesses oder die Governance an",
        )
    db.add(datenobjekt)
    db.flush()
    protokolliere_erstellung(db, datenobjekt, akteur_user_id=principal.user_id)
    if gebender is not None:
        gebender.output_datenobjekte.append(datenobjekt)
        db.flush()
        aktualisiere_abhaengige_prozesse(db, datenobjekt)
    return datenobjekt


def aendere_datenobjekt(
    db: Session, principal: Principal, datenobjekt: Datenobjekt, werte: dict[str, Any]
) -> Datenobjekt:
    # Je Feld ein eigenes Recht (7.4) — die Kategorie wirkt in jeden Prozess,
    # der Anker traegt jede Berechtigung; beides darf nicht, wer nur pflegt.
    if "kategorie" in werte:
        verlange(
            darf_datenobjekt_kategorisieren(principal, datenobjekt),
            "Die Kategorie setzt der Datenobjekt-Owner des Fachbereichs oder die Governance",
        )
    if "fachbereich_id" in werte:
        verlange(
            darf_datenobjekt_anker_aendern(principal, datenobjekt),
            "Den Fachbereich eines Datenobjekts aendert nur die Governance",
        )
        if werte["fachbereich_id"] is None:
            raise Ungueltig("Ein Datenobjekt gehoert einem Fachbereich; ohne geht es nicht")
        if db.get(Fachbereich, werte["fachbereich_id"]) is None:
            raise Ungueltig("Fachbereich existiert nicht")
    if set(werte) - {"kategorie", "fachbereich_id"}:
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
        darf_datenobjekt_bestaetigen(principal, datenobjekt),
        "Bestaetigen darf der Datenobjekt-Owner, die Plattform oder die Governance-Rolle",
    )
    if datenobjekt.fachbereich_id is None:
        raise Ungueltig(
            "Bestaetigen heisst zuordnen: erst den Fachbereich setzen, dann bestaetigen"
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
    if not attestierung_vollstaendig(tool):
        raise Ungueltig(
            "Die drei Attestierungen nach A.6 sind vor der ersten "
            "Prozessverknuepfung zu erklaeren — sie tragen die Triage "
            "veraendert oder gestaltet, die aus der Verknuepfung allein "
            "nicht ablesbar ist"
        )
    if prozess in tool.prozessobjekte:
        raise Ungueltig("Diese Verknuepfung besteht bereits")
    tool.prozessobjekte.append(prozess)
    db.flush()
    protokolliere_kante(
        db,
        tool,
        vorher=None,
        nachher={"prozessobjekt_id": prozess.id},
        akteur_user_id=principal.user_id,
        beschreibung=f"Verknuepft mit Prozessobjekt {prozess.id}",
    )
    # Attestierung 1 wirkt auf das Mitbestimmungsflag des Prozesses (A.5).
    ableitung.aktualisiere_kette(prozess)
    db.flush()
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
    tool.prozessobjekte.remove(prozess)
    db.flush()
    protokolliere_kante(
        db,
        tool,
        vorher={"prozessobjekt_id": prozess.id},
        nachher=None,
        akteur_user_id=principal.user_id,
        beschreibung=f"Geloest von Prozessobjekt {prozess.id}",
    )
    ableitung.aktualisiere_kette(prozess)
    db.flush()
    return tool


def verknuepfe_tool_mit_datenobjekt(
    db: Session,
    principal: Principal,
    tool: ToolObjekt,
    datenobjekt: Datenobjekt,
    zugriffsart: Zugriffsart,
) -> ToolDatenobjekt:
    verlange(
        darf_tool_verknuepfen(db, principal, tool),
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
    protokolliere_kante(
        db,
        tool,
        vorher=None,
        nachher={"datenobjekt_id": datenobjekt.id, "zugriffsart": zugriffsart},
        akteur_user_id=principal.user_id,
        beschreibung=f"Nutzt Datenobjekt {datenobjekt.id} ({zugriffsart})",
    )
    return kante


def aendere_zugriffsart(
    db: Session,
    principal: Principal,
    tool: ToolObjekt,
    datenobjekt_id: uuid.UUID,
    zugriffsart: Zugriffsart,
) -> ToolDatenobjekt:
    """Die Zugriffsart einer bestehenden Kante korrigieren.

    Sie steuert die Triage aus A.6 — ein Wechsel von „liest" auf „schreibt"
    macht ein Tool veraendernd. Deshalb eine eigene, protokollierte Aktion und
    kein Loeschen mit Neuanlage.
    """
    verlange(
        darf_tool_verknuepfen(db, principal, tool),
        "Keine Schreibberechtigung fuer dieses Tool-Objekt",
    )
    kante = db.get(ToolDatenobjekt, (tool.id, datenobjekt_id))
    if kante is None:
        raise NichtGefunden("Diese Verknuepfung besteht nicht")
    bisher = kante.zugriffsart
    kante.zugriffsart = zugriffsart
    db.flush()
    protokolliere_kante(
        db,
        tool,
        vorher={"datenobjekt_id": datenobjekt_id, "zugriffsart": bisher},
        nachher={"datenobjekt_id": datenobjekt_id, "zugriffsart": zugriffsart},
        akteur_user_id=principal.user_id,
        beschreibung=(f"Zugriffsart auf Datenobjekt {datenobjekt_id}: {bisher} -> {zugriffsart}"),
    )
    return kante


def loese_tool_von_datenobjekt(
    db: Session, principal: Principal, tool: ToolObjekt, datenobjekt_id: uuid.UUID
) -> None:
    verlange(
        darf_tool_verknuepfen(db, principal, tool),
        "Keine Schreibberechtigung fuer dieses Tool-Objekt",
    )
    kante = db.get(ToolDatenobjekt, (tool.id, datenobjekt_id))
    if kante is None:
        raise NichtGefunden("Diese Verknuepfung besteht nicht")
    vorher = {"datenobjekt_id": datenobjekt_id, "zugriffsart": kante.zugriffsart}
    db.delete(kante)
    db.flush()
    protokolliere_kante(
        db,
        tool,
        vorher=vorher,
        nachher=None,
        akteur_user_id=principal.user_id,
        beschreibung=f"Nutzt Datenobjekt {datenobjekt_id} nicht mehr",
    )


def datenobjekte_eines_tools(db: Session, tool_id: uuid.UUID) -> list[ToolDatenobjekt]:
    return list(
        db.execute(
            select(ToolDatenobjekt).where(ToolDatenobjekt.tool_objekt_id == tool_id)
        ).scalars()
    )


# --- Zweckbindung (Leitdokument A.4.6) -----------------------------------


@dataclass
class Datennutzung:
    """Eine Tool-Datenobjekt-Kante, gepruft gegen den Prozessrahmen."""

    datenobjekt_id: uuid.UUID
    name: str
    kategorie: Datenkategorie | None
    zugriffsart: Zugriffsart
    #: Das Datenobjekt ist an mindestens einem verknuepften Prozess deklariert.
    im_prozessrahmen: bool = False
    #: Seine Kategorie kommt im Rahmen wenigstens vor — der schwaechere Test.
    kategorie_gedeckt: bool = False


def pruefe_zweckbindung(db: Session, tool: ToolObjekt) -> list[Datennutzung]:
    """„Tool liest Datenobjekt D im Rahmen von Prozess P" — oder eben nicht.

    A.4.6 nennt das den Vorteil, der Compliance am meisten wert ist: nutzt ein
    Tool ein Datenobjekt, das der zugeordnete Prozess nicht abdeckt, ist das
    eine erkennbare Abweichung statt eines Befunds, den erst jemand entdecken
    muss. Geprueft wird zweistufig — zuerst das Datenobjekt selbst, dann als
    schwaecherer Test seine Kategorie. Ein Tool ohne Prozesskante hat gar
    keinen Rahmen; dann ist beides unerfuellt.
    """
    rahmen_ids: set[uuid.UUID] = set()
    rahmen_kategorien: set[str] = set()
    for prozess in tool.prozessobjekte:
        for datenobjekt in [*prozess.input_datenobjekte, *prozess.output_datenobjekte]:
            rahmen_ids.add(datenobjekt.id)
            if datenobjekt.kategorie is not None:
                rahmen_kategorien.add(datenobjekt.kategorie)

    befunde: list[Datennutzung] = []
    for kante in datenobjekte_eines_tools(db, tool.id):
        datenobjekt = db.get(Datenobjekt, kante.datenobjekt_id)
        if datenobjekt is None:
            continue
        im_rahmen = datenobjekt.id in rahmen_ids
        befunde.append(
            Datennutzung(
                datenobjekt_id=datenobjekt.id,
                name=datenobjekt.name,
                kategorie=datenobjekt.kategorie,
                zugriffsart=kante.zugriffsart,
                im_prozessrahmen=im_rahmen,
                kategorie_gedeckt=im_rahmen
                or (
                    datenobjekt.kategorie is not None and datenobjekt.kategorie in rahmen_kategorien
                ),
            )
        )
    return sorted(befunde, key=lambda b: b.name)


def entferne_tool(db: Session, principal: Principal, tool: ToolObjekt) -> None:
    verlange(principal.ist_governance, "Tool-Objekte entfernt ausschliesslich die Governance-Rolle")
    protokolliere_loeschung(db, tool, akteur_user_id=principal.user_id)
    for kante in datenobjekte_eines_tools(db, tool.id):
        db.delete(kante)
    tool.prozessobjekte.clear()
    db.delete(tool)
    db.flush()


# --- Wirkung einer Umklassifizierung (Leitdokument A.4.5, A.4.7) ---------


def wirkung_der_kategorie(
    db: Session, datenobjekt: Datenobjekt, kategorie_neu: Datenkategorie | None
) -> dict:
    """Was eine Umklassifizierung beruehrt — als Abfrage, nicht als Studie.

    Das Leitdokument nennt genau diesen Fall: HR stuft „Entgeltdaten" hoeher
    ein, und die Frage ist, wer davon betroffen ist. Ohne Referenzen waere das
    eine organisationsweite Nacherfassung; mit Referenzen ist es diese Abfrage.

    Beantwortet wird, was heute berechenbar ist: die referenzierenden Prozesse
    mit ihrem kuenftigen Mitbestimmungsflag und die Tool-Objekte, die das
    Datenobjekt nutzen oder ueber einen Prozess erben. Die Tier-Folge einer
    Kategorieaenderung kommt erst, wenn die Bewertung ihre DS-Dimension aus den
    Kategorien ableitet (Umsetzungsplan AP-4).
    """
    from app.services import ableitung

    prozesse = {
        prozess.id: prozess
        for prozess in [*datenobjekt.input_fuer_prozesse, *datenobjekt.output_von_prozessen]
    }

    vorher = datenobjekt.kategorie
    prozessbericht: list[dict] = []
    tools: dict[uuid.UUID, dict] = {}
    try:
        datenobjekt.kategorie = kategorie_neu
        for prozess in prozesse.values():
            prozessbericht.append(
                {
                    "id": prozess.id,
                    "name": prozess.name,
                    "tier": (lambda b: b.tier if b else None)(neueste_bewertung(prozess)),
                    "mitbestimmung_flag": prozess.mitbestimmung_flag,
                    "mitbestimmung_flag_neu": ableitung.leite_mitbestimmung_ab(prozess),
                    "als_input": any(d.id == datenobjekt.id for d in prozess.input_datenobjekte),
                    "als_output": any(d.id == datenobjekt.id for d in prozess.output_datenobjekte),
                }
            )
            for tool in prozess.tool_objekte:
                tools.setdefault(tool.id, {"id": tool.id, "name": tool.name, "ueber_prozess": True})
    finally:
        datenobjekt.kategorie = vorher

    for kante in db.execute(
        select(ToolDatenobjekt).where(ToolDatenobjekt.datenobjekt_id == datenobjekt.id)
    ).scalars():
        tool = db.get(ToolObjekt, kante.tool_objekt_id)
        if tool is None:
            continue
        eintrag = tools.setdefault(tool.id, {"id": tool.id, "name": tool.name})
        eintrag["zugriffsart"] = kante.zugriffsart

    return {
        "kategorie_alt": vorher,
        "kategorie_neu": kategorie_neu,
        "prozesse": sorted(prozessbericht, key=lambda p: p["name"]),
        "tools": sorted(tools.values(), key=lambda t: t["name"]),
        "mitbestimmung_neu": sum(
            1 for p in prozessbericht if p["mitbestimmung_flag_neu"] and not p["mitbestimmung_flag"]
        ),
    }
