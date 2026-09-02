"""Selbstverpflichtungs-Modul (Architektur 8.4, Leitdokument A.10).

Die Aussagen aus A.10.2 und A.10.3 sind strukturierte Checkboxen, nicht
Freitext: jede nummerierte Aussage ist ein eigener Wahrheitswert mit optionalem
Kommentar. Ein Freitextfeld waere weder auswertbar noch pruefbar — und genau
die Auswertbarkeit traegt Cockpit und Lenkung.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import Principal, verlange
from app.models.base import now_utc
from app.models.enums import SelbstverpflichtungTyp
from app.models.governance import Prozessobjekt, Selbstverpflichtung, ToolObjekt
from app.services import konfiguration
from app.services.asset import darf_tool_schreiben
from app.services.changelog import protokolliere_erstellung
from app.services.prozess import NichtGefunden, Ungueltig, darf_schreiben


@dataclass(frozen=True)
class Aussage:
    """Eine nummerierte Aussage aus A.10.2 beziehungsweise A.10.3.

    ``ab_tier`` traegt die Kurzform aus A.10.5: bei Tier 1 werden nur die
    Aussagen mit ``ab_tier == 1`` verlangt. Die Auswahl ist nicht willkuerlich,
    sondern folgt den Dimensionen — was ein Tier-1-Objekt gar nicht ausloesen
    kann, wird von ihm auch nicht erklaert.
    """

    id: str
    text: str
    ab_tier: int = 1


#: Version des Katalogs. Wird an jeder Erklaerung mitgespeichert, damit eine
#: nach altem Wortlaut abgegebene Erklaerung als solche erkennbar bleibt und
#: nicht stillschweigend als Zustimmung zu einem anderen Text gilt (E-32).
KATALOG_VERSION = 2


#: Leitdokument A.10.2 — Selbstverpflichtung des Prozesseigners.
#:
#: A.10.4 verlangt „spezifisch statt pauschal": jede Aussage muss im Nachhinein
#: pruefbar sein. Formulierungen wie „nach bestem Wissen" sind damit
#: ausgeschlossen — sie sind nicht widerlegbar und deshalb wertlos.
AUSSAGEN_PROZESSEIGNER: tuple[Aussage, ...] = (
    Aussage(
        "PE1",
        "Der Zweck dieses Prozessobjekts ist vollständig und abschließend beschrieben; "
        "das Ergebnis wird zu keinem anderen Zweck verwendet.",
    ),
    Aussage(
        "PE2",
        "Die referenzierten Datenobjekte decken alle im Prozess verarbeiteten Daten ab; "
        "weitere Quellen werden nicht genutzt.",
    ),
    Aussage(
        "PE3",
        "Der Empfängerkreis des Ergebnisses ist vollständig angegeben; eine Weitergabe "
        "darüber hinaus findet nicht statt.",
        ab_tier=2,
    ),
    Aussage(
        "PE4",
        "Das Ergebnis wird nicht zur Bewertung, Steuerung oder Kontrolle einzelner "
        "Beschäftigter verwendet.",
        ab_tier=2,
    ),
    Aussage(
        "PE5",
        "Die Nachweis- und Aufbewahrungspflichten dieses Prozessobjekts sind vollständig "
        "angegeben.",
        ab_tier=2,
    ),
    Aussage(
        "PE6",
        "Eine Änderung des Zwecks wird angezeigt, bevor sie wirksam wird.",
    ),
)

#: Leitdokument A.10.3 — Selbstverpflichtung des technischen Owners.
#:
#: Die Verbote aus A.13.2 Schicht 2 — umgangene Unternehmensidentität, statische
#: Zugangsdaten — standen hier zwischenzeitlich als Aussagen T2 und T3. Sie
#: gehören nicht hierher: der Erlaubnisrahmen verbietet sie organisationsweit,
#: und ein Verbot, das durch keine Bewertung freischaltbar ist, wird nicht
#: erklärt, sondern durchgesetzt (siehe AP-6).
AUSSAGEN_TECHNISCHER_OWNER: tuple[Aussage, ...] = (
    Aussage(
        "TO1",
        "Die aus der Bewertung ausgelösten Anforderungsklassen sind für dieses "
        "Tool-Objekt umgesetzt.",
    ),
    Aussage(
        "TO2",
        "Es werden keine undeklarierten Datenquellen verarbeitet — keine Uploads, "
        "manuellen Eingaben oder Zwischenablagen außerhalb der verknüpften Datenobjekte.",
    ),
    Aussage(
        "TO3",
        "Das Tool-Objekt läuft im erklärten Rahmen: nur die freigegebenen Datenobjekte, "
        "die freigegebene Reichweite, die freigegebenen externen Ziele.",
    ),
    Aussage(
        "TO4",
        "Zugriffe dieses Tool-Objekts sind nachvollziehbar protokolliert.",
        ab_tier=2,
    ),
    Aussage(
        "TO5",
        "Abhängigkeiten und Betriebsverantwortung sind dokumentiert.",
        ab_tier=2,
    ),
    Aussage(
        "TO6",
        "Eine Stellvertretung für den technischen Betrieb ist benannt und über ihre "
        "Rolle informiert.",
    ),
)

KATALOG: dict[SelbstverpflichtungTyp, tuple[Aussage, ...]] = {
    SelbstverpflichtungTyp.PROZESSEIGNER: AUSSAGEN_PROZESSEIGNER,
    SelbstverpflichtungTyp.TECHNISCHER_OWNER: AUSSAGEN_TECHNISCHER_OWNER,
}

#: Aussage, mit der der technische Owner den Rahmen als eingehalten erklaert.
#: Das Cockpit haelt sie gegen den gemessenen Zustand (Zeile „Widersprueche").
AUSSAGE_RAHMEN_EINGEHALTEN = "TO3"


def verlangte_aussagen(typ: SelbstverpflichtungTyp, tier: int | None) -> tuple[Aussage, ...]:
    """Die Aussagen, die bei diesem Tier zu erklaeren sind (A.10.5).

    Ohne Bewertung gilt die Kurzform: es gibt noch keine Einstufung, die mehr
    rechtfertigen wuerde. Ab Tier 2 wird der ganze Katalog verlangt.
    """
    stufe = tier if tier is not None else 1
    return tuple(a for a in KATALOG[typ] if a.ab_tier <= max(stufe, 1))


def pruefe_aussagen(typ: SelbstverpflichtungTyp, aussagen: dict[str, dict]) -> None:
    erwartet = {a.id for a in KATALOG[typ]}
    unbekannt = sorted(set(aussagen) - erwartet)
    if unbekannt:
        raise Ungueltig(f"Unbekannte Aussagen für diesen Typ: {', '.join(unbekannt)}")


def ist_vollstaendig(
    typ: SelbstverpflichtungTyp, aussagen: dict[str, dict], tier: int | None = None
) -> bool:
    """Vollstaendig heisst: jede **verlangte** Aussage ist bestaetigt.

    Verlangt wird bei Tier 1 nur die Kurzform. Eine Tier-1-Erklaerung ist also
    vollstaendig, obwohl sie drei Aussagen nicht enthaelt — genau das meint
    A.10.5. Wer mehr erklaert, als verlangt ist, wird nicht daran gehindert;
    zusaetzliche Bestaetigungen werden mitgespeichert.
    """
    return all(
        bool(aussagen.get(a.id, {}).get("bestaetigt", False)) for a in verlangte_aussagen(typ, tier)
    )


def gueltig_bis(db: Session, tier: int | None, ab: datetime) -> datetime | None:
    """Ab Tier 3 gilt die jaehrliche Erneuerungspflicht (Leitdokument A.10.5)."""
    if tier is None or tier < 3:
        return None
    return ab + timedelta(days=konfiguration.lies_int(db, "selbstverpflichtung_gueltigkeit_tage"))


def abgeben(
    db: Session,
    principal: Principal,
    *,
    typ: SelbstverpflichtungTyp,
    prozess: Prozessobjekt | None = None,
    tool: ToolObjekt | None = None,
    aussagen: dict[str, dict],
) -> Selbstverpflichtung:
    """Nimmt eine Selbstverpflichtung entgegen; frueherer Stand bleibt erhalten."""
    if typ == SelbstverpflichtungTyp.PROZESSEIGNER:
        if prozess is None:
            raise Ungueltig("Eine Prozesseigner-Selbstverpflichtung braucht ein Prozessobjekt")
        verlange(
            darf_schreiben(db, principal, prozess.prozessgeber_org_id),
            "Die Selbstverpflichtung gibt der Prozesseigner ab",
        )
    else:
        if tool is None:
            raise Ungueltig("Eine Owner-Selbstverpflichtung braucht ein Tool-Objekt")
        verlange(
            darf_tool_schreiben(db, principal, tool),
            "Die Selbstverpflichtung gibt der technische Owner ab",
        )

    pruefe_aussagen(typ, aussagen)
    zeitpunkt = now_utc()
    tier = _tier_des_ziels(prozess, tool)
    eintrag = Selbstverpflichtung(
        typ=typ,
        prozessobjekt_id=prozess.id if prozess is not None else None,
        tool_objekt_id=tool.id if tool is not None else None,
        aussagen=aussagen,
        vollstaendig=ist_vollstaendig(typ, aussagen, tier),
        katalog_version=KATALOG_VERSION,
        tier_bei_abgabe=tier,
        bewertung_id=_bewertung_id(prozess),
        abgegeben_von=principal.user_id,
        abgegeben_am=zeitpunkt,
        gueltig_bis=gueltig_bis(db, tier, zeitpunkt),
    )
    db.add(eintrag)
    db.flush()
    protokolliere_erstellung(db, eintrag, akteur_user_id=principal.user_id)
    return eintrag


def bestaetige(
    db: Session, principal: Principal, eintrag: Selbstverpflichtung
) -> Selbstverpflichtung:
    """Die Jahresbestaetigung ab Tier 3 — ein Klick, kein neuer Durchgang.

    Erzeugt einen neuen Eintrag mit denselben Aussagen und frischem Datum. Die
    Historie bleibt damit lueckenlos: es ist ablesbar, wann wer welche
    Erklaerung bestaetigt hat, und der frueherer Stand wird nicht ueberschrieben.

    Bestaetigen laesst sich nur, was noch traegt. Haengt die Erklaerung an einer
    ueberholten Bewertung oder an einem alten Katalog, waere ein Klick zu
    wenig — dann ist sie neu abzugeben (A.10.4).
    """
    prozess, tool = _ziel(db, eintrag)
    stand = deckung(db, eintrag, prozess=prozess, tool=tool, nur_frist=True)
    if not stand.gedeckt:
        raise Ungueltig(
            "Diese Erklärung lässt sich nicht per Bestätigung verlängern, sondern ist neu "
            f"abzugeben. {stand.grundtext}"
        )
    return abgeben(
        db,
        principal,
        typ=eintrag.typ,
        prozess=prozess,
        tool=tool,
        aussagen=dict(eintrag.aussagen),
    )


def _ziel(
    db: Session, eintrag: Selbstverpflichtung
) -> tuple[Prozessobjekt | None, ToolObjekt | None]:
    prozess = (
        db.get(Prozessobjekt, eintrag.prozessobjekt_id)
        if eintrag.prozessobjekt_id is not None
        else None
    )
    tool = (
        db.get(ToolObjekt, eintrag.tool_objekt_id) if eintrag.tool_objekt_id is not None else None
    )
    return prozess, tool


def _bewertung_id(prozess: Prozessobjekt | None) -> uuid.UUID | None:
    """Die Bewertung, an die eine Prozesseigner-Erklaerung gebunden wird (A.10.4).

    Tool-Objekte bekommen keine Bindung: ihr Tier ist geerbt und kann aus
    mehreren Prozessen stammen: eine einzelne Bewertungs-ID waere willkuerlich.
    Bei ihnen traegt ``tier_bei_abgabe`` dieselbe Aufgabe.
    """
    from app.services.prozess import neueste_bewertung

    if prozess is None:
        return None
    bewertung = neueste_bewertung(prozess)
    return bewertung.id if bewertung is not None else None


def _tier_des_ziels(prozess: Prozessobjekt | None, tool: ToolObjekt | None) -> int | None:
    from app.services.asset import erbe_klassifikation
    from app.services.prozess import neueste_bewertung

    if prozess is not None:
        bewertung = neueste_bewertung(prozess)
        return bewertung.tier if bewertung is not None else None
    if tool is not None:
        return erbe_klassifikation(tool).tier
    return None


def hole(db: Session, eintrag_id: uuid.UUID) -> Selbstverpflichtung:
    eintrag = db.get(Selbstverpflichtung, eintrag_id)
    if eintrag is None:
        raise NichtGefunden("Selbstverpflichtung nicht gefunden")
    return eintrag


def aktuelle_fuer_prozess(db: Session, prozess_id: uuid.UUID) -> Selbstverpflichtung | None:
    return db.execute(
        select(Selbstverpflichtung)
        .where(Selbstverpflichtung.prozessobjekt_id == prozess_id)
        .order_by(Selbstverpflichtung.abgegeben_am.desc())
        .limit(1)
    ).scalar_one_or_none()


def aktuelle_fuer_tool(db: Session, tool_id: uuid.UUID) -> Selbstverpflichtung | None:
    return db.execute(
        select(Selbstverpflichtung)
        .where(Selbstverpflichtung.tool_objekt_id == tool_id)
        .order_by(Selbstverpflichtung.abgegeben_am.desc())
        .limit(1)
    ).scalar_one_or_none()


def historie_fuer_prozess(db: Session, prozess_id: uuid.UUID) -> list[Selbstverpflichtung]:
    return list(
        db.execute(
            select(Selbstverpflichtung)
            .where(Selbstverpflichtung.prozessobjekt_id == prozess_id)
            .order_by(Selbstverpflichtung.abgegeben_am.desc())
        ).scalars()
    )


def ist_abgelaufen(eintrag: Selbstverpflichtung, jetzt: datetime | None = None) -> bool:
    if eintrag.gueltig_bis is None:
        return False
    zeitpunkt = jetzt or datetime.now(UTC)
    frist = eintrag.gueltig_bis
    if frist.tzinfo is None:
        frist = frist.replace(tzinfo=UTC)
    return frist < zeitpunkt


#: Die Gruende, aus denen eine Erklaerung nicht traegt — je ein Satz, der sagt,
#: was zu tun ist. Die Oberflaeche zeigt ihn wortgleich an.
GRUNDTEXTE: dict[str, str] = {
    "": "Die Erklärung liegt vor und trägt.",
    "keine": "Für dieses Objekt liegt noch keine Selbstverpflichtung vor.",
    "unvollstaendig": "Nicht alle verlangten Aussagen sind bestätigt.",
    "alter_katalog": (
        "Die Erklärung wurde nach einem früheren Aussagenkatalog abgegeben und ist "
        "nach dem heutigen Wortlaut neu abzugeben."
    ),
    "profil_veraltet": (
        "Die Erklärung hängt an einer überholten Bewertung. Nach A.10.4 verfällt sie "
        "mit dem Profil und ist neu abzugeben."
    ),
    "tier_gestiegen": (
        "Das geerbte Tier ist seit der Erklärung gestiegen; sie deckt weniger ab, "
        "als jetzt verlangt wird."
    ),
    "frist_abgelaufen": "Die Jahresfrist ist verstrichen; eine Bestätigung genügt.",
}


@dataclass(frozen=True)
class Deckung:
    """Traegt eine Erklaerung — und wenn nicht, woran es liegt."""

    gedeckt: bool
    grund: str = ""

    @property
    def grundtext(self) -> str:
        return GRUNDTEXTE.get(self.grund, self.grund)


def deckung(
    db: Session,
    eintrag: Selbstverpflichtung | None,
    *,
    prozess: Prozessobjekt | None = None,
    tool: ToolObjekt | None = None,
    jetzt: datetime | None = None,
    nur_frist: bool = False,
) -> Deckung:
    """Prueft eine Erklaerung gegen den heutigen Stand des Objekts.

    A.10.4 bindet die Erklaerung an die Profilversion: aendert sich das Profil,
    verfaellt sie automatisch. Diese Bindung ist der eigentliche Zweck der
    Selbstverpflichtung — eine Erklaerung, die eine Neubewertung ueberlebt,
    bezieht sich auf einen Sachverhalt, den es nicht mehr gibt.

    Mit ``nur_frist`` bleibt die Fristpruefung aussen vor. Das braucht die
    Jahresbestaetigung: dort ist die abgelaufene Frist gerade der Anlass und
    kein Hindernis.
    """
    if eintrag is None:
        return Deckung(False, "keine")
    if not eintrag.vollstaendig:
        return Deckung(False, "unvollstaendig")
    if (eintrag.katalog_version or 1) < KATALOG_VERSION:
        return Deckung(False, "alter_katalog")

    if prozess is not None:
        from app.services.prozess import neueste_bewertung

        aktuell = neueste_bewertung(prozess)
        if aktuell is not None and eintrag.bewertung_id != aktuell.id:
            return Deckung(False, "profil_veraltet")
    elif tool is not None:
        from app.services.asset import erbe_klassifikation

        geerbt = erbe_klassifikation(tool).tier
        if geerbt is not None and geerbt > (eintrag.tier_bei_abgabe or 0):
            return Deckung(False, "tier_gestiegen")

    if not nur_frist and ist_abgelaufen(eintrag, jetzt):
        return Deckung(False, "frist_abgelaufen")
    return Deckung(True)


def deckung_fuer_prozess(
    db: Session, prozess: Prozessobjekt, jetzt: datetime | None = None
) -> Deckung:
    return deckung(db, aktuelle_fuer_prozess(db, prozess.id), prozess=prozess, jetzt=jetzt)


def deckung_fuer_tool(db: Session, tool: ToolObjekt, jetzt: datetime | None = None) -> Deckung:
    return deckung(db, aktuelle_fuer_tool(db, tool.id), tool=tool, jetzt=jetzt)


def ist_gedeckt(db: Session, prozess: Prozessobjekt, jetzt: datetime | None = None) -> bool:
    """Liegt eine vollstaendige, gebundene und nicht abgelaufene Erklaerung vor?"""
    return deckung_fuer_prozess(db, prozess, jetzt).gedeckt
