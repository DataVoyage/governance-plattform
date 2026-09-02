"""Vorschlaege und begruendete Abweichungen an der Bewertung

Revision ID: f3a91d6b84c2
Revises: c7e2b4a9d150
Create Date: 2026-09-02 09:20:00.000000

Leitdokument A.8.4 (Umsetzungsplan AP-4). Die Bewertung hat bisher nur
festgehalten, **was** geantwortet wurde. Ab hier haelt sie zusaetzlich fest,
**was die Datenlage zum selben Zeitpunkt hergab** und, wo beides auseinander
faellt, **warum**.

Beide Spalten sind JSON und werden mit einem leeren Objekt vorbelegt statt mit
``NULL``: „keine Abweichung" und „nicht erhoben" sind fuer die Auswertung
dasselbe, und ein leeres Objekt erspart jeder lesenden Stelle die
Fallunterscheidung. Bestandsbewertungen tragen damit ``{}`` — das ist richtig,
denn zu ihnen wurde nachweislich kein Vorschlag gerechnet.

Ohne die gespeicherten Vorschlaege liesse sich spaeter nicht unterscheiden, ob
jemand bewusst abgewichen ist oder ob sich die Daten seit der Bewertung
geaendert haben. Genau diese Unterscheidung traegt die Cockpit-Zeile
„Antwort widerspricht Datenlage".
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3a91d6b84c2"
down_revision: Union[str, Sequence[str], None] = "c7e2b4a9d150"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("bewertungen", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("vorschlaege", sa.JSON(), nullable=False, server_default="{}")
        )
        batch_op.add_column(
            sa.Column("abweichungen", sa.JSON(), nullable=False, server_default="{}")
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("bewertungen", schema=None) as batch_op:
        batch_op.drop_column("abweichungen")
        batch_op.drop_column("vorschlaege")
