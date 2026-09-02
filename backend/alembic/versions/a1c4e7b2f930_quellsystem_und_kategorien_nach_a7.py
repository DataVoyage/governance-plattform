"""Quellsystem am Datenobjekt, Kategorien auf die fuenf aus A.7

Revision ID: a1c4e7b2f930
Revises: dbc373281ae4
Create Date: 2026-09-01 20:55:00.000000

Zwei Aenderungen am Datenobjekt (Umsetzungsplan AP-2):

1. ``quellsystem`` als eigenes Feld. Reifegrad 1 aus Leitdokument A.7 verlangt
   Name, Kategorie, Owner **und Quellsystem**; bisher gab es nur ``quelle``,
   und das ist die Sync-Quelle des Imports, nicht die fachliche Herkunft.

2. Die Kategorie ``mitarbeiterbezogen`` entfaellt. A.7 schliesst sie
   ausdruecklich aus: Mitbestimmungsrelevanz haengt am Verwendungszweck, nicht
   an der Datenart, und gehoert deshalb in das abgeleitete Flag. Bestehende
   Datensaetze wandern nach ``personenbezogen`` — die naechstliegende Kategorie
   nach A.7, die den Personenbezug erhaelt, ohne eine besondere Kategorie zu
   behaupten. Wo daraus eine zu niedrige Einstufung wird, faellt das im Cockpit
   auf; eine automatische Hochstufung waere die schlechtere Annahme.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1c4e7b2f930"
down_revision: Union[str, Sequence[str], None] = "dbc373281ae4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("datenobjekte", schema=None) as batch_op:
        batch_op.add_column(sa.Column("quellsystem", sa.String(length=255), nullable=True))

    op.execute(
        sa.text(
            "UPDATE datenobjekte SET kategorie = 'personenbezogen' "
            "WHERE kategorie = 'mitarbeiterbezogen'"
        )
    )


def downgrade() -> None:
    """Downgrade schema.

    Die umgezogenen Kategorien bleiben bei ``personenbezogen``: welche Zeilen
    vorher ``mitarbeiterbezogen`` trugen, ist nach dem Upgrade nicht mehr
    unterscheidbar. Ein Ratewert waere schlechter als der ehrliche Verzicht.
    """
    with op.batch_alter_table("datenobjekte", schema=None) as batch_op:
        batch_op.drop_column("quellsystem")
