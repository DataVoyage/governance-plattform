"""Anforderungsklassen und Technologiematrix (Leitdokument A.9, Teil C.1).

A.9.1 beschreibt zwei Uebersetzungsstufen: vom Profil zu den Anforderungsklassen
und von den Klassen zu einer Entscheidung ueber die eingesetzte Technologie. Die
erste macht ``services/bewertung.py``; dieses Modul macht die zweite.

Der Abgleich ist der Punkt, auf den das ganze Bewertungsmodell zulaeuft. A.9.3:
„Ein ❌ bei einer ausgeloesten Klasse = Ausschlusskriterium; ein ⚠️ =
kompensierende Massnahme erforderlich." Ohne ihn sagt die Anwendung, welche
Klassen ausgeloest sind, aber nicht, ob die gewaehlte Technologie sie tragen
kann — und damit fehlt die Entscheidung.

Die Matrix liegt als **gepflegte Stammdaten** in der Datenbank, nicht als
Konstante im Code: sie ist eine Entscheidungsgrundlage, und eine, die nur mit
einer Auslieferung aenderbar waere, veraltet zwischen zwei Releases. Die
Standardbelegung steht hier und wird beim Start angelegt, wenn ein Feld fehlt.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import Principal, verlange
from app.models.base import now_utc
from app.models.enums import Befundart, Klassenbewertung
from app.models.governance import (
    Kompensation,
    Prozessobjekt,
    Technologiebewertung,
    ToolObjekt,
)
from app.services import bewertung as bewertung_service
from app.services.asset import darf_tool_schreiben, erbe_klassifikation
from app.services.changelog import protokolliere_aenderung, protokolliere_erstellung, snapshot
from app.services.prozess import NichtGefunden, Ungueltig

#: Die Technologien, die diese Anwendung kennt. Sie stehen hier und nicht in
#: der Oberflaeche, damit Tool-Auswahl und Matrix dieselbe Liste benutzen.
TECHNOLOGIEN: dict[str, str] = {
    "apps-script": "Apps Script",
    "python-kubernetes": "Python / Kubernetes",
    "bigquery-gcs": "BigQuery / Cloud Storage",
    "appsheet": "AppSheet",
}

#: Woran eine Klasse haengt — in Worten, nicht als Formel. A.9.2 verlangt zu
#: jeder Klasse Name, Zweck und **Ausloeserbedingung**; die ersten beiden
#: stehen in ``bewertung.py``, die dritte hier. Sie ist die Lesefassung von
#: ``bewertung.leite_k_klassen_ab`` und wird von einem Test dagegen gehalten.
AUSLOESERBEDINGUNG: dict[str, str] = {
    "K1": "Immer — jedes bewertete Prozessobjekt trägt sie.",
    "K2": "Immer — jedes bewertete Prozessobjekt trägt sie.",
    "K3": "Sobald irgendeine Dimension Stufe 2 oder höher erreicht.",
    "K4": "Datenschutz-Stufe 3.",
    "K5": "Datenschutz-Stufe 2 oder IT-Sicherheits-Stufe 2 und höher.",
    "K6": "KI-Stufe 1 und höher — sobald überhaupt KI beteiligt ist.",
    "K7": "Mitbestimmungs-Stufe 1 und höher.",
    "K8": "Regulatorik-Stufe 2 und höher.",
    "K9": "Unternehmerisches-Risiko-Stufe 2 und höher.",
    "K10": "KI-, IT-Sicherheits- oder Risiko-Stufe 3.",
}

#: Die Standardbelegung der Matrix (Leitdokument Teil C.1).
#:
#: Sieben der zehn Klassen sind **organisatorisch** — Dokumentation,
#: Selbstverpflichtung, benannter Owner, Folgenabschaetzung, KI-Transparenz,
#: Mitbestimmung und Gate 2 haengen nicht an der Plattform. Keine Technologie
#: hindert jemanden daran, den Betriebsrat zu beteiligen. Sie stehen deshalb
#: ueberall auf ``erfuellt``, und das ist keine Nachlaessigkeit, sondern die
#: Aussage: hier entscheidet die Organisation, nicht das Werkzeug.
#:
#: Die drei technischen Klassen unterscheiden sich: das Zugriffs- und
#: Rechtekonzept (K5), die revisionssichere Aufbewahrung (K8) und das
#: Wiederanlaufkonzept (K9).
STANDARDMATRIX: dict[str, dict[str, tuple[str, str]]] = {
    "apps-script": {
        "K5": (
            Klassenbewertung.KOMPENSIERBAR,
            "Ein Skript läuft unter der Identität dessen, der es startet; ein "
            "eigenes Rechtekonzept hat es nicht. Kompensierbar über die Rechte "
            "der angesprochenen Ablagen.",
        ),
        "K8": (
            Klassenbewertung.KOMPENSIERBAR,
            "Die Ausführungsprotokolle sind zeitlich begrenzt und nicht "
            "revisionssicher. Kompensierbar über eine Ausleitung in ein "
            "aufbewahrungspflichtiges System.",
        ),
        "K9": (
            Klassenbewertung.NICHT_ERFUELLBAR,
            "Ein Skript in der Ablage einer Person hat weder Ausweichbetrieb "
            "noch zugesagte Wiederanlaufzeit. Ein Wiederanlaufkonzept lässt "
            "sich darauf nicht aufsetzen.",
        ),
    },
    "python-kubernetes": {},
    "bigquery-gcs": {
        "K9": (
            Klassenbewertung.KOMPENSIERBAR,
            "Der Speicher ist hochverfügbar, die Auswertungslogik aber nicht "
            "Teil eines Wiederanlaufplans. Kompensierbar über einen "
            "dokumentierten Wiederherstellungsweg der Abfragen.",
        ),
    },
    "appsheet": {
        "K5": (
            Klassenbewertung.NICHT_ERFUELLBAR,
            "Die Plattform kennt nur ihr eigenes Freigabemodell. Ein "
            "abgestuftes, jährlich überprüfbares Rechtekonzept lässt sich "
            "darin nicht abbilden.",
        ),
        "K8": (
            Klassenbewertung.KOMPENSIERBAR,
            "Änderungen sind nachvollziehbar, aber nicht aufbewahrungssicher. "
            "Kompensierbar über einen regelmäßigen Export.",
        ),
        "K9": (
            Klassenbewertung.NICHT_ERFUELLBAR,
            "Für die Anwendung gibt es keinen Ausweichbetrieb und keine "
            "zugesagte Wiederanlaufzeit.",
        ),
    },
}

#: Standardsatz fuer die organisatorischen Klassen, die jede Technologie traegt.
ERFUELLT_BEGRUENDUNG = (
    "Organisatorische Anforderung — sie hängt an der Organisation, nicht an der Technologie."
)


def alle_klassen() -> list[dict]:
    """K1 bis K10 mit Name, Zweck und Ausloeserbedingung (Leitdokument A.9.2)."""
    return [
        {
            "schluessel": schluessel,
            "name": bewertung_service.K_KLASSEN_BESCHREIBUNG[schluessel],
            "zweck": bewertung_service.K_KLASSEN_ERKLAERUNG[schluessel],
            "ausloeser": AUSLOESERBEDINGUNG[schluessel],
        }
        for schluessel in bewertung_service.K_KLASSEN_BESCHREIBUNG
    ]


# --- Matrix ---------------------------------------------------------------


def initialisiere(db: Session) -> int:
    """Legt fehlende Matrixfelder mit der Standardbelegung an. Idempotent."""
    vorhanden = {
        (e.technologie, e.k_klasse) for e in db.execute(select(Technologiebewertung)).scalars()
    }
    neu = 0
    for technologie in TECHNOLOGIEN:
        abweichend = STANDARDMATRIX.get(technologie, {})
        for klasse in bewertung_service.K_KLASSEN_BESCHREIBUNG:
            if (technologie, klasse) in vorhanden:
                continue
            wert, begruendung = abweichend.get(
                klasse, (Klassenbewertung.ERFUELLT, ERFUELLT_BEGRUENDUNG)
            )
            db.add(
                Technologiebewertung(
                    technologie=technologie,
                    k_klasse=klasse,
                    bewertung=wert,
                    begruendung=begruendung,
                )
            )
            neu += 1
    if neu:
        db.flush()
    return neu


def matrix(db: Session) -> list[Technologiebewertung]:
    """Die vollstaendige Matrix, nach Technologie und Klasse geordnet."""
    initialisiere(db)
    eintraege = list(db.execute(select(Technologiebewertung)).scalars())
    reihenfolge = list(bewertung_service.K_KLASSEN_BESCHREIBUNG)
    return sorted(
        eintraege,
        key=lambda e: (
            list(TECHNOLOGIEN).index(e.technologie) if e.technologie in TECHNOLOGIEN else 99,
            reihenfolge.index(e.k_klasse) if e.k_klasse in reihenfolge else 99,
        ),
    )


def feld(db: Session, technologie: str, k_klasse: str) -> Technologiebewertung | None:
    return db.execute(
        select(Technologiebewertung).where(
            Technologiebewertung.technologie == technologie,
            Technologiebewertung.k_klasse == k_klasse,
        )
    ).scalar_one_or_none()


def setze_feld(
    db: Session,
    principal: Principal,
    technologie: str,
    k_klasse: str,
    *,
    bewertung: Klassenbewertung,
    begruendung: str,
) -> Technologiebewertung:
    """Aendert ein Matrixfeld — ausschliesslich die Governance-Rolle.

    Die Begruendung ist Pflicht. Ein Feld der Matrix entscheidet darueber, ob
    ein Prozess mit einer Technologie betrieben werden darf; wer das aendert,
    schuldet den Satz, warum.
    """
    verlange(principal.ist_governance, "Die Technologiematrix pflegt die Governance-Rolle")
    if k_klasse not in bewertung_service.K_KLASSEN_BESCHREIBUNG:
        raise NichtGefunden(f"Unbekannte Anforderungsklasse: {k_klasse}")
    if technologie not in TECHNOLOGIEN:
        raise NichtGefunden(f"Unbekannte Technologie: {technologie}")
    if not begruendung.strip():
        raise Ungueltig(
            "Ein Matrixfeld ist zu begründen — es entscheidet, ob ein Prozess "
            "mit dieser Technologie betrieben werden darf"
        )

    initialisiere(db)
    eintrag = feld(db, technologie, k_klasse)
    if eintrag is None:  # pragma: no cover — initialisiere legt jedes Feld an
        raise NichtGefunden("Matrixfeld nicht gefunden")
    vorher = snapshot(eintrag)
    eintrag.bewertung = bewertung
    eintrag.begruendung = begruendung
    eintrag.geaendert_von = principal.user_id
    db.flush()
    protokolliere_aenderung(db, eintrag, vorher, akteur_user_id=principal.user_id)
    return eintrag


# --- Abgleich (Leitdokument A.9.3) ---------------------------------------


@dataclass(frozen=True)
class Befund:
    """Eine ausgeloeste Klasse gegen die Technologie eines Tool-Objekts.

    ``schritt`` sagt, was zu tun ist — nicht, was der Fall ist. Eine Karte, die
    nur „K5 ❌" zeigt, verlagert die Uebersetzungsarbeit auf den Leser.
    """

    tool_id: uuid.UUID
    tool_name: str
    technologie: str | None
    k_klasse: str
    art: Befundart
    begruendung: str = ""
    massnahme: str = ""

    @property
    def offen(self) -> bool:
        return self.art in (
            Befundart.AUSSCHLUSS,
            Befundart.KOMPENSATION_FEHLT,
            Befundart.UNGEPRUEFT,
        )


@dataclass
class Toolbefund:
    """Alle Befunde eines Tool-Objekts, samt seiner ausgeloesten Klassen."""

    tool_id: uuid.UUID
    tool_name: str
    technologie: str | None
    k_klassen: list[str] = field(default_factory=list)
    befunde: list[Befund] = field(default_factory=list)

    @property
    def ausschluss(self) -> bool:
        return any(b.art == Befundart.AUSSCHLUSS for b in self.befunde)

    @property
    def offen(self) -> int:
        return sum(1 for b in self.befunde if b.offen)


def kompensationen(db: Session, tool_id: uuid.UUID) -> dict[str, Kompensation]:
    return {
        k.k_klasse: k
        for k in db.execute(
            select(Kompensation).where(Kompensation.tool_objekt_id == tool_id)
        ).scalars()
    }


def pruefe_tool(db: Session, tool: ToolObjekt) -> Toolbefund:
    """Die ausgeloesten Klassen des Tools gegen seine Technologie (A.9.3).

    Ausgeloest sind die Klassen, die das Tool ueber seine Prozesskanten erbt —
    das Maximum ueber alle Kanten (A.4.4). Ohne Prozesskante gibt es nichts
    abzugleichen; ohne hinterlegte Technologie ist jede Klasse ``ungeprueft``,
    denn eine fehlende Angabe ist kein Nachweis.
    """
    initialisiere(db)
    geerbt = erbe_klassifikation(tool)
    ergebnis = Toolbefund(
        tool_id=tool.id,
        tool_name=tool.name,
        technologie=tool.technologie,
        k_klassen=list(geerbt.k_klassen),
    )
    if not geerbt.k_klassen:
        return ergebnis

    vorhandene = kompensationen(db, tool.id)
    for klasse in geerbt.k_klassen:
        eintrag = None if tool.technologie is None else feld(db, tool.technologie, klasse)
        if eintrag is None:
            ergebnis.befunde.append(
                Befund(
                    tool_id=tool.id,
                    tool_name=tool.name,
                    technologie=tool.technologie,
                    k_klasse=klasse,
                    art=Befundart.UNGEPRUEFT,
                )
            )
            continue
        if eintrag.bewertung == Klassenbewertung.ERFUELLT:
            art = Befundart.ERFUELLT
        elif eintrag.bewertung == Klassenbewertung.NICHT_ERFUELLBAR:
            art = Befundart.AUSSCHLUSS
        else:
            art = Befundart.KOMPENSIERT if klasse in vorhandene else Befundart.KOMPENSATION_FEHLT
        ergebnis.befunde.append(
            Befund(
                tool_id=tool.id,
                tool_name=tool.name,
                technologie=tool.technologie,
                k_klasse=klasse,
                art=art,
                begruendung=eintrag.begruendung,
                massnahme=vorhandene[klasse].massnahme if klasse in vorhandene else "",
            )
        )
    return ergebnis


def pruefe_prozess(db: Session, prozess: Prozessobjekt) -> list[Toolbefund]:
    """Der Abgleich fuer jedes Tool am Prozessobjekt.

    Der Prozess hat selbst keine Technologie; er sieht die Befunde seiner Tools.
    Genau so ist die Frage gestellt: „darf dieser Prozess mit diesen Werkzeugen
    betrieben werden?"
    """
    return [pruefe_tool(db, tool) for tool in prozess.tool_objekte]


def setze_kompensation(
    db: Session,
    principal: Principal,
    tool: ToolObjekt,
    k_klasse: str,
    massnahme: str,
) -> Kompensation:
    """Haelt die kompensierende Massnahme zu einer Klasse fest (A.9.3).

    Nur wo die Matrix ``kompensierbar`` sagt: bei ``erfuellt`` gibt es nichts
    zu kompensieren, bei ``nicht_erfuellbar`` ist der Fall ein Ausschluss —
    eine Kompensation dort waere eine Umgehung des Kriteriums.
    """
    verlange(
        darf_tool_schreiben(db, principal, tool),
        "Kompensationen erfasst der technische Owner oder die Governance-Rolle",
    )
    if not massnahme.strip():
        raise Ungueltig("Eine Kompensation ohne Beschreibung ist keine — der Befund bliebe offen")
    initialisiere(db)
    eintrag = None if tool.technologie is None else feld(db, tool.technologie, k_klasse)
    if eintrag is None:
        raise NichtGefunden("Für diese Technologie und Klasse gibt es kein Matrixfeld")
    if eintrag.bewertung != Klassenbewertung.KOMPENSIERBAR:
        raise Ungueltig(
            "Nur ein kompensierbarer Befund lässt sich kompensieren; ein "
            "Ausschluss ist keiner, und Erfülltes braucht keinen"
        )

    bestehend = kompensationen(db, tool.id).get(k_klasse)
    if bestehend is not None:
        vorher = snapshot(bestehend)
        bestehend.massnahme = massnahme
        bestehend.erfasst_von = principal.user_id
        bestehend.erfasst_am = now_utc()
        db.flush()
        protokolliere_aenderung(db, bestehend, vorher, akteur_user_id=principal.user_id)
        return bestehend

    neu = Kompensation(
        tool_objekt_id=tool.id,
        k_klasse=k_klasse,
        massnahme=massnahme,
        erfasst_von=principal.user_id,
        erfasst_am=now_utc(),
    )
    db.add(neu)
    db.flush()
    protokolliere_erstellung(db, neu, akteur_user_id=principal.user_id)
    return neu
