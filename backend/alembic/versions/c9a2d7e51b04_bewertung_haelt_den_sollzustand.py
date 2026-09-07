"""Die Bewertung haelt den Sollzustand, nicht das lebende Prozessobjekt

Revision ID: c9a2d7e51b04
Revises: b8e4f19c26a3
Create Date: 2026-09-07 16:00:00.000000

Leitdokument A.13.1 und A.8.4 (Umsetzungsplan AP-19, E-67/E-69/E-70).

Der Erlaubnisrahmen las die erlaubte Reichweite bisher vom **lebenden**
Prozessobjekt. Eine zweite Umsetzung hob damit die Reichweite ueber den
Nachtlauf, und der Rahmen des Tools weitete sich von selbst — ohne Bewertung
und ohne Gate 2. A.13.1 verlangt das Gegenteil: Der Rahmen kommt aus der
Prozess*bewertung*. Dafuer muss die Bewertung die erklaerte Erwartung
mitfuehren, aus der sie gerechnet wurde.

``reichweite`` und ``ausfallfolge`` frieren genau diese beiden Erwartungen
ein. ``ur_kette`` und ``tier_herkunft`` halten fest, was die abhaengige
Prozesskette beigetragen hat und woher das Tier stammt — ein Tier oberhalb des
eigenen Profils muss sagen koennen, warum.

``ueberholt_am`` und ``ueberholt_grund`` kennzeichnen eine Bewertung, deren
Tier sich durch eine Aenderung an der Datenlage verschoben hat. Die Bewertung
wird dabei **nicht** umgeschrieben: A.13.7 verlangt eine lueckenlose Historie,
und eine rueckwirkend veraenderte Bewertung waere keine.

Alle Spalten sind nullable beziehungsweise mit Vorgabewert versehen. Bestehende
Bewertungen bleiben unangetastet und gelten weiter; sie tragen keine
eingefrorene Erwartung, und die Vererbung faellt fuer sie auf das lebende Feld
zurueck, bis sie erneuert werden.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9a2d7e51b04"
down_revision: Union[str, Sequence[str], None] = "b8e4f19c26a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("bewertungen", sa.Column("reichweite", sa.String(length=24), nullable=True))
    op.add_column("bewertungen", sa.Column("ausfallfolge", sa.String(length=24), nullable=True))
    op.add_column(
        "bewertungen", sa.Column("ur_kette", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "bewertungen",
        sa.Column("tier_herkunft", sa.String(length=16), nullable=False, server_default="profil"),
    )
    op.add_column(
        "bewertungen", sa.Column("ueberholt_am", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "bewertungen", sa.Column("ueberholt_grund", sa.Text(), nullable=False, server_default="")
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("bewertungen", "ueberholt_grund")
    op.drop_column("bewertungen", "ueberholt_am")
    op.drop_column("bewertungen", "tier_herkunft")
    op.drop_column("bewertungen", "ur_kette")
    op.drop_column("bewertungen", "ausfallfolge")
    op.drop_column("bewertungen", "reichweite")
