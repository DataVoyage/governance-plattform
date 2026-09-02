"""Nutzer, Rollen und Nachweis (Architektur 5.3, Leitdokument A.15, A.13.7).

Dieses Modul macht die Anwendung selbsttragend: Rollen wurden bisher nur ueber
die API vergeben, und der Nachweis war nur ueber die Datenbank zu lesen. Beides
ist Verwaltungsarbeit, die jemand ohne Datenbankzugang tun koennen muss.

Zwei Regeln tragen es:

* **Wer eine Rolle vergibt, sieht vorher ihre Wirkung.** „Prozess-Owner auf
  FIN-INT" sagt niemandem, wie viel Zugriff das ist. Die Vorschau rechnet es
  aus, bevor entschieden wird.
* **Der Nachweis ist Lesestoff, kein Rohdatenauszug.** Wer eine Aenderung
  sucht, will wissen, **was** sich geaendert hat — nicht zwei JSON-Objekte
  nebeneinander.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import Principal, Zuweisung, verlange
from app.models.audit import ChangeLog
from app.models.enums import Rolle, ScopeTyp
from app.models.governance import Prozessobjekt, ToolObjekt
from app.models.organisation import Fachbereich, Organisationseinheit, Rollenzuweisung, User
from app.services import asset as asset_service
from app.services import prozess as prozess_service
from app.services.prozess import NichtGefunden

#: Was eine Rolle darf, in einem Satz (Leitdokument A.15).
#:
#: Die Liste ist die Lesefassung der Berechtigungsmatrix aus Architektur 5.3.
#: Sie steht hier und nicht in der Uebersetzungsdatei, weil sie fachlicher
#: Inhalt ist: wer eine Rolle vergibt, entscheidet ueber Zugriff und soll dabei
#: nicht raten muessen, was der Name bedeutet.
ROLLENERKLAERUNG: dict[str, str] = {
    Rolle.PROZESS_OWNER: (
        "Legt Prozessobjekte im eigenen Bereich an, hält sie aktuell und gibt die "
        "Selbstverpflichtung nach A.10.2 ab. Verantwortet, was der Prozess tut."
    ),
    Rolle.PROZESS_UMSETZER: (
        "Pflegt die lokale Abweichung an einer Umsetzung — und nur diese. Der "
        "Prozess selbst gehört ihm nicht."
    ),
    Rolle.TECHNISCHER_OWNER: (
        "Verantwortet Betrieb und Änderungen eines Tool-Objekts, gibt die drei "
        "Attestierungen nach A.6 ab und meldet Compliance-Zustände."
    ),
    Rolle.DATENOBJEKT_OWNER: (
        "Pflegt Datenobjekte mitsamt ihrer Kategorie. Eine Umklassifizierung "
        "wirkt in jeden Prozess, der das Objekt referenziert."
    ),
    Rolle.GOVERNANCE: (
        "Entscheidet Gates, pflegt Technologiematrix und Einstellungen, bearbeitet "
        "Lenkungsvorgänge. Sieht bereichsübergreifend."
    ),
    Rolle.PLATTFORM: (
        "Betreibt die Adapter, die Assets aus den Quellsystemen einspielen. Kein "
        "fachlicher Zugriff auf Bewertungen oder Gates."
    ),
    Rolle.AUDITOR: (
        "Liest bereichsübergreifend mit, einschließlich des Nachweises. Ändert nichts."
    ),
    Rolle.APP_ADMINISTRATOR: (
        "Verwaltet Nutzer und Rollen. Vergibt damit jeden anderen Zugriff — die "
        "Rolle, die man am sparsamsten vergibt."
    ),
}


def darf_verwalten(principal: Principal) -> bool:
    return principal.ist_administrator


def alle_rollen() -> list[dict]:
    return [
        {"schluessel": rolle, "erklaerung": ROLLENERKLAERUNG[rolle]} for rolle in ROLLENERKLAERUNG
    ]


# --- Wirkungsvorschau -----------------------------------------------------


@dataclass
class Wirkung:
    """Was eine Zuweisung an Sichtbarkeit eroeffnen wuerde.

    Gerechnet wird ueber genau dieselben Sichtbarkeitsfunktionen, die spaeter
    auch greifen — eine zweite, naeherungsweise Rechnung waere eine Vorschau
    auf etwas anderes als das Ergebnis.
    """

    rolle: str
    scope_typ: str
    scope_name: str = ""
    prozessobjekte: int = 0
    tool_objekte: int = 0
    #: Namen der ersten Treffer, damit die Zahl greifbar wird.
    beispiele: list[str] = field(default_factory=list)


def _scope_name(db: Session, scope_typ: str, scope_id: uuid.UUID | None) -> str:
    if scope_typ == ScopeTyp.GLOBAL:
        return "unternehmensweit"
    if scope_id is None:
        return ""
    if scope_typ == ScopeTyp.FACHBEREICH:
        bereich = db.get(Fachbereich, scope_id)
        return bereich.name if bereich else ""
    einheit = db.get(Organisationseinheit, scope_id)
    if einheit is None:
        return ""
    bereich = db.get(Fachbereich, einheit.fachbereich_id)
    teile = [bereich.name if bereich else "", einheit.ebene, einheit.land_code or ""]
    return " · ".join(t for t in teile if t)


def wirkung(
    db: Session,
    principal: Principal,
    *,
    user_id: uuid.UUID,
    rolle: Rolle,
    scope_typ: ScopeTyp,
    scope_id: uuid.UUID | None,
) -> Wirkung:
    """„Diese Zuweisung gibt Zugriff auf N Prozessobjekte."

    Gezaehlt wird, was die Zuweisung **hinzufuegt** — nicht, was der Nutzer
    danach insgesamt saehe. Wer ein Prozessobjekt selbst verantwortet, sieht es
    ohnehin; es der Rolle zuzuschlagen wuerde die Vorschau aufblasen und die
    Entscheidung verfaelschen, um die es geht.

    Beide Seiten rechnen auf einem **gedachten** Principal und ueber genau
    dieselben Sichtbarkeitsfunktionen, die spaeter auch greifen: einmal mit der
    Zuweisung, einmal ohne. Eine zweite, naeherungsweise Rechnung waere eine
    Vorschau auf etwas anderes als das Ergebnis.
    """
    verlange(darf_verwalten(principal), "Rollen verwaltet nur der App-Administrator")
    if db.get(User, user_id) is None:
        raise NichtGefunden("Nutzer nicht gefunden")

    def sicht(zuweisungen: list[Zuweisung]) -> tuple[set[uuid.UUID], set[uuid.UUID], dict]:
        gedacht = Principal(user_id=user_id, email="", name="", zuweisungen=zuweisungen)
        prozesse = prozess_service.liste(db, gedacht)
        tools = asset_service.liste_tools(db, gedacht)
        return (
            {p.id for p in prozesse},
            {t.id for t in tools},
            {p.id: p.name for p in prozesse},
        )

    mit_prozessen, mit_tools, namen = sicht([Zuweisung(rolle, scope_typ, scope_id)])
    ohne_prozesse, ohne_tools, _ = sicht([])

    neue_prozesse = mit_prozessen - ohne_prozesse
    return Wirkung(
        rolle=rolle,
        scope_typ=scope_typ,
        scope_name=_scope_name(db, scope_typ, scope_id),
        prozessobjekte=len(neue_prozesse),
        tool_objekte=len(mit_tools - ohne_tools),
        beispiele=sorted(namen[kennung] for kennung in neue_prozesse)[:3],
    )


# --- Nachweis (Leitdokument A.13.7) --------------------------------------


@dataclass
class Feldaenderung:
    feld: str
    vorher: str
    nachher: str


@dataclass
class Nachweiseintrag:
    """Ein Eintrag des Aenderungsprotokolls, lesbar aufbereitet."""

    cursor: int
    entity_type: str
    entity_id: uuid.UUID
    aktion: str
    zeitpunkt: str
    akteur: str
    #: Der Name des betroffenen Objekts, soweit es noch existiert.
    gegenstand: str = ""
    aenderungen: list[Feldaenderung] = field(default_factory=list)


#: Felder, die in jedem Snapshot stehen und nichts erklaeren.
UNINTERESSANT: frozenset[str] = frozenset({"erstellt_am", "geaendert_am", "id"})


#: Felder, die auf ein anderes Objekt zeigen und keine Person benennen.
#:
#: Sie stuenden als UUID auf dem Bildschirm und sagten niemandem etwas — den
#: Gegenstand nennt ohnehin die Ueberschrift. Personenfelder bleiben, weil sie
#: sich zu einem Namen aufloesen lassen und die Frage „wer" beantworten.
def _ist_fremdschluessel(feld: str) -> bool:
    return feld.endswith("_id") and not feld.endswith("_user_id")


#: Felder, die auf eine Person zeigen — sie werden zum Namen aufgeloest.
def _ist_person(feld: str) -> bool:
    return feld.endswith("_user_id") or feld in {
        "festgestellt_von",
        "eingereicht_von",
        "entschieden_von",
        "abgegeben_von",
        "erfasst_von",
        "bewertet_von",
        "ausgeloest_von",
        "geaendert_von",
    }


def _als_text(wert: object, namen: dict[str, str] | None = None) -> str:
    if wert is None or wert == "":
        return "—"
    if isinstance(wert, bool):
        return "ja" if wert else "nein"
    if isinstance(wert, list | dict):
        return ", ".join(str(w) for w in wert) if wert else "—"
    text = str(wert)
    if namen is not None and text in namen:
        return namen[text]
    # Zeitstempel auf die Minute: Mikrosekunden beantworten keine Frage, die
    # eine Pruefung stellt.
    if len(text) >= 19 and text[4] == "-" and text[10] == "T":
        return text[:16].replace("T", " ")
    return text


def _gegenstand(db: Session, eintrag: ChangeLog) -> str:
    modelle = {
        "prozessobjekte": Prozessobjekt,
        "tool_objekte": ToolObjekt,
        "users": User,
    }
    modell = modelle.get(eintrag.entity_type)
    if modell is None:
        return ""
    objekt = db.get(modell, eintrag.entity_id)
    return getattr(objekt, "name", "") if objekt is not None else ""


def nachweis(
    db: Session,
    principal: Principal,
    *,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[Nachweiseintrag]:
    """Das Aenderungsprotokoll als Lesestoff (A.13.7).

    Sichtbar fuer die bereichsuebergreifend lesenden Rollen und den
    App-Administrator. Der Nachweis ist der Ort, an dem eine Pruefung eine
    einzelne Handlung wiederfindet; ihn nach Bereichen zu schneiden wuerde
    genau das verhindern.
    """
    verlange(
        principal.sieht_global or principal.ist_administrator,
        "Den Nachweis lesen die Auditor- und Governance-Rolle sowie der App-Administrator",
    )
    stmt = select(ChangeLog)
    if entity_type is not None:
        stmt = stmt.where(ChangeLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(ChangeLog.entity_id == entity_id)
    eintraege = list(
        db.execute(stmt.order_by(ChangeLog.cursor.desc()).limit(max(1, min(500, limit)))).scalars()
    )

    # Alle Personen auf einmal holen: die Akteure und jede Person, auf die ein
    # Feld zeigt. Eine UUID auf dem Bildschirm beantwortet die Frage „wer"
    # nicht (dritter Grundsatz des Design-Systems).
    personen: set[str] = {str(e.akteur_user_id) for e in eintraege if e.akteur_user_id}
    for eintrag in eintraege:
        for stand in (eintrag.vorher or {}, eintrag.nachher or {}):
            for feld, wert in stand.items():
                if _ist_person(feld) and isinstance(wert, str):
                    personen.add(wert)

    namen = {
        str(u.id): u.name for u in db.execute(select(User).where(User.id.in_(personen))).scalars()
    }

    ergebnis: list[Nachweiseintrag] = []
    for eintrag in eintraege:
        vorher = eintrag.vorher or {}
        nachher = eintrag.nachher or {}
        felder = [
            feld
            for feld in sorted((set(vorher) | set(nachher)) - UNINTERESSANT)
            if not _ist_fremdschluessel(feld)
        ]
        aenderungen = [
            Feldaenderung(
                feld=feld,
                vorher=_als_text(vorher.get(feld), namen),
                nachher=_als_text(nachher.get(feld), namen),
            )
            for feld in felder
            if vorher.get(feld) != nachher.get(feld)
        ]
        ergebnis.append(
            Nachweiseintrag(
                cursor=eintrag.cursor,
                entity_type=eintrag.entity_type,
                entity_id=eintrag.entity_id,
                aktion=eintrag.aktion,
                zeitpunkt=eintrag.zeitpunkt.isoformat(),
                akteur=namen.get(str(eintrag.akteur_user_id), "")
                or eintrag.akteur_beschreibung
                or "System",
                gegenstand=_gegenstand(db, eintrag),
                aenderungen=aenderungen,
            )
        )
    return ergebnis


# --- Nutzerpflege ---------------------------------------------------------


def aendere_user(
    db: Session,
    principal: Principal,
    user: User,
    *,
    ist_aktiv: bool | None = None,
    fuehrungskraft_user_id: uuid.UUID | None = None,
    fuehrungskraft_setzen: bool = False,
) -> User:
    """Aktivstatus und Fuehrungskraft — beide mit Wirkung im Betrieb.

    Die Fuehrungskraft ist keine Stammdatenzierde: ab Eskalationsstufe 2 geht
    die Meldung an sie (A.13.5). Ohne einen Weg, sie zu setzen, laeuft die
    Eskalation an den Betroffenen selbst zurueck.
    """
    verlange(darf_verwalten(principal), "Nutzer verwaltet nur der App-Administrator")
    from app.services.changelog import protokolliere_aenderung, snapshot

    vorher = snapshot(user)
    if ist_aktiv is not None:
        user.ist_aktiv = ist_aktiv
    if fuehrungskraft_setzen:
        if fuehrungskraft_user_id == user.id:
            raise prozess_service.Ungueltig(
                "Niemand ist seine eigene Führungskraft — die Eskalation liefe im Kreis"
            )
        if fuehrungskraft_user_id is not None and db.get(User, fuehrungskraft_user_id) is None:
            raise NichtGefunden("Die angegebene Führungskraft existiert nicht")
        user.fuehrungskraft_user_id = fuehrungskraft_user_id
    db.flush()
    protokolliere_aenderung(db, user, vorher, akteur_user_id=principal.user_id)
    return user


def rollen_eines_nutzers(db: Session, user_id: uuid.UUID) -> list[Rollenzuweisung]:
    return list(
        db.execute(select(Rollenzuweisung).where(Rollenzuweisung.user_id == user_id)).scalars()
    )
