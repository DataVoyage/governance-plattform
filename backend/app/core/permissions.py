"""Rolle-x-Bereich-Autorisierung (Architektur Abschnitt 5).

Rollen und Bereiche sind orthogonal (P-App-3): eine Berechtigung entsteht nie
aus einer Rolle allein, sondern immer aus der Kombination von Rolle und Scope.
Diese Modul enthaelt reine Logik ohne HTTP- oder Datenbankkenntnis; die
FastAPI-Abhaengigkeiten in ``app.api.deps`` setzen sie um.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.models.enums import Rolle, ScopeTyp

#: Rollen, die bereichsuebergreifend lesen duerfen (Architektur 4.3).
GLOBAL_LESEND: frozenset[Rolle] = frozenset(
    {Rolle.GOVERNANCE, Rolle.AUDITOR, Rolle.PLATTFORM, Rolle.APP_ADMINISTRATOR}
)

#: Ausschliesslich lesende Rollen — nie schreibberechtigt.
NUR_LESEND: frozenset[Rolle] = frozenset({Rolle.AUDITOR})


@dataclass(frozen=True)
class Zuweisung:
    rolle: Rolle
    scope_typ: ScopeTyp
    scope_id: uuid.UUID | None = None


@dataclass
class Principal:
    """Der angemeldete Nutzer mit seinen Rollenzuweisungen."""

    user_id: uuid.UUID
    email: str
    name: str
    zuweisungen: list[Zuweisung] = field(default_factory=list)

    # --- Grundfragen ---------------------------------------------------

    @property
    def rollen(self) -> set[Rolle]:
        return {z.rolle for z in self.zuweisungen}

    def hat_rolle(
        self,
        rolle: Rolle,
        *,
        organisationseinheit_id: uuid.UUID | None = None,
        fachbereich_id: uuid.UUID | None = None,
    ) -> bool:
        """Prueft eine Rolle, optional eingeschraenkt auf einen Bereich.

        Ohne Bereichsangabe genuegt irgendeine Zuweisung dieser Rolle. Mit
        Bereichsangabe zaehlt eine Zuweisung, wenn sie global ist, auf genau
        diese Organisationseinheit zeigt, oder auf den Fachbereich, zu dem die
        Organisationseinheit gehoert.
        """
        for z in self.zuweisungen:
            if z.rolle != rolle:
                continue
            if z.scope_typ == ScopeTyp.GLOBAL:
                return True
            if organisationseinheit_id is None and fachbereich_id is None:
                return True
            if (
                z.scope_typ == ScopeTyp.ORGANISATIONSEINHEIT
                and organisationseinheit_id is not None
                and z.scope_id == organisationseinheit_id
            ):
                return True
            if (
                z.scope_typ == ScopeTyp.FACHBEREICH
                and fachbereich_id is not None
                and z.scope_id == fachbereich_id
            ):
                return True
        return False

    def hat_eine_rolle(self, *rollen: Rolle, **scope: uuid.UUID | None) -> bool:
        return any(self.hat_rolle(r, **scope) for r in rollen)

    # --- Abgeleitete Kurzformen ----------------------------------------

    @property
    def ist_governance(self) -> bool:
        return self.hat_rolle(Rolle.GOVERNANCE)

    @property
    def ist_auditor(self) -> bool:
        return self.hat_rolle(Rolle.AUDITOR)

    @property
    def ist_plattform(self) -> bool:
        return self.hat_rolle(Rolle.PLATTFORM)

    @property
    def ist_administrator(self) -> bool:
        return self.hat_rolle(Rolle.APP_ADMINISTRATOR)

    @property
    def sieht_global(self) -> bool:
        """Governance- und Auditor-Rollen sehen bereichsuebergreifend (4.3)."""
        return bool(self.rollen & GLOBAL_LESEND)

    @property
    def scope_organisationseinheiten(self) -> set[uuid.UUID]:
        return {
            z.scope_id
            for z in self.zuweisungen
            if z.scope_typ == ScopeTyp.ORGANISATIONSEINHEIT and z.scope_id is not None
        }

    @property
    def scope_fachbereiche(self) -> set[uuid.UUID]:
        return {
            z.scope_id
            for z in self.zuweisungen
            if z.scope_typ == ScopeTyp.FACHBEREICH and z.scope_id is not None
        }


class Verboten(Exception):
    """Die Aktion ist fuer diesen Principal in diesem Bereich nicht erlaubt."""

    def __init__(self, detail: str = "Keine Berechtigung fuer diese Aktion") -> None:
        super().__init__(detail)
        self.detail = detail


def verlange(bedingung: bool, detail: str = "Keine Berechtigung fuer diese Aktion") -> None:
    if not bedingung:
        raise Verboten(detail)
