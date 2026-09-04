"""Freigabe ausstehend als vierter Prozessstatus

Revision ID: e1b6f3d27a94
Revises: d4f7a2c19e60
Create Date: 2026-09-04 11:40:00.000000

Leitdokument A.11 und E-60. ``pruefe_aktivierung`` haengt am Statuswechsel:
wer schon aktiv ist, kommt nie wieder daran vorbei. Ein Prozessobjekt konnte
damit von Tier 1 auf Tier 3 wechseln und ohne Gate weiterlaufen.

Der naheliegende Weg — zurueck in den Entwurf — waere falsch gewesen: der
Prozess laeuft ja. „Entwurf" heisst „noch nie in Betrieb", und im Cockpit wie
in jedem Filter verschmilzt er dann mit echten Neuanlagen. Das eine wird gerade
gebaut, das andere laeuft ohne Deckung, und nur das zweite ist dringend.

Deshalb ein vierter Wert. Die Spalte ist eine ``String``-Spalte ohne
Datenbank-Enum, der Wert braucht also keine Typaenderung — diese Migration
schafft nichts als einen Ort, an dem die Entscheidung nachlesbar ist, und
haelt die Kette der Fassungen vollstaendig.
"""

from typing import Sequence, Union

revision: str = "e1b6f3d27a94"
down_revision: Union[str, Sequence[str], None] = "d4f7a2c19e60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Kein Schemaeingriff noetig: ``prozessobjekte.status`` ist String(24), und
    # „freigabe_ausstehend" passt hinein. Die Gueltigkeit der Werte prueft die
    # Anwendung ueber ``ProzessStatus``, nicht die Datenbank.


def downgrade() -> None:
    """Downgrade schema."""
    # Zurueck bleibt nur, den vierten Wert auf den dritten abzubilden: ein
    # Prozess ohne Freigabe ist unter den alten drei Werten am ehesten ein
    # Entwurf — mit genau dem Verlust an Aussage, dessentwegen es den vierten
    # Wert gibt.
    from alembic import op
    import sqlalchemy as sa

    op.execute(
        sa.text(
            "UPDATE prozessobjekte SET status = 'entwurf' "
            "WHERE status = 'freigabe_ausstehend'"
        )
    )
