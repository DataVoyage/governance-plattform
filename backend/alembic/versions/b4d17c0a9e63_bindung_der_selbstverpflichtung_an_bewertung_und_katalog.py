"""Bindung der Selbstverpflichtung an Bewertung, Tier und Katalogfassung

Revision ID: b4d17c0a9e63
Revises: f3a91d6b84c2
Create Date: 2026-09-02 11:40:00.000000

Leitdokument A.10.4 (Umsetzungsplan AP-5). Die Gueltigkeit einer
Selbstverpflichtung hing bisher allein am Zeitablauf. A.10.4 verlangt mehr:
„an die Profilversion gebunden — aendert sich das Profil, verfaellt die
Erklaerung automatisch". Eine Erklaerung, die eine Neubewertung ueberlebt,
bezieht sich auf einen Sachverhalt, den es nicht mehr gibt.

Drei Spalten tragen das:

* ``bewertung_id`` bindet die Prozesseigner-Erklaerung an genau die Bewertung,
  zu der sie abgegeben wurde.
* ``tier_bei_abgabe`` traegt dieselbe Aufgabe fuer Tool-Objekte, deren Tier
  geerbt ist und aus mehreren Prozessen stammen kann; ausserdem bestimmt es,
  welche Aussagen nach der Kurzform-Regel A.10.5 ueberhaupt verlangt waren.
* ``katalog_version`` haelt fest, gegen welchen Wortlaut erklaert wurde.

**Bestandsdaten werden nicht umgeschrieben.** Vorhandene Erklaerungen bekommen
``katalog_version = 1`` und behalten ihre Aussagen mit den alten Kennungen
(``P1``…``P6``, ``T1``…``T6``). Sie bleiben in der Historie lesbar, zaehlen
aber nicht mehr als Deckung: der alte Katalog sagte nachweislich etwas anderes
als A.10.2/A.10.3, und eine Zustimmung zu Text A ist keine Zustimmung zu Text B
(siehe ``docs/entscheidungen.md``, E-32). Wer betroffen ist, sieht das im
Cockpit und gibt die Erklaerung nach dem heutigen Wortlaut neu ab.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b4d17c0a9e63"
down_revision: Union[str, Sequence[str], None] = "f3a91d6b84c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("selbstverpflichtungen", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("katalog_version", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.add_column(
            sa.Column("bewertung_id", postgresql.UUID(as_uuid=True), nullable=True)
        )
        batch_op.add_column(sa.Column("tier_bei_abgabe", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_selbstverpflichtung_bewertung", "bewertungen", ["bewertung_id"], ["id"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("selbstverpflichtungen", schema=None) as batch_op:
        batch_op.drop_constraint("fk_selbstverpflichtung_bewertung", type_="foreignkey")
        batch_op.drop_column("tier_bei_abgabe")
        batch_op.drop_column("bewertung_id")
        batch_op.drop_column("katalog_version")
