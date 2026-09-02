"""Attestierungen, Lauftyp und Stellvertretung am Tool-Objekt

Revision ID: c7e2b4a9d150
Revises: a1c4e7b2f930
Create Date: 2026-09-01 22:10:00.000000

Leitdokument A.6 (Umsetzungsplan AP-3). Das Tool-Objekt ist bis hierher rein
maschinell gedacht gewesen; A.6 nennt aber ausdruecklich drei Erklaerungen,
die Telemetrie nicht liefern kann und die deshalb ein Mensch abgeben muss:

1. Fliesst das Ergebnis in eine Entscheidung ueber einzelne Personen?
2. Steht zwischen Output und Wirkung ein Mensch?
3. Werden Datenkategorien verarbeitet, die nicht aus klassifizierten Quellen
   stammen (Uploads, manuelle Eingaben, Zwischenablagen)?

Alle drei sind ``nullable``, und das ist die Aussage: ``NULL`` heisst
unbeantwortet und ist von einem erklaerten „Nein" zu unterscheiden. Bestehende
Tool-Objekte gelten damit als nicht attestiert — eine Vorbelegung mit ``False``
waere eine Erklaerung, die niemand abgegeben hat.

Dazu ``attestiert_am`` und ``attestiert_von_user_id``: A.6 verlangt die
Erklaerung „mit Namen, nicht als Formularfeld".

``lauftyp`` und ``stellvertretung_user_id`` vervollstaendigen die Feldliste aus
A.6 beziehungsweise Architektur 3.2.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c7e2b4a9d150"
down_revision: Union[str, Sequence[str], None] = "a1c4e7b2f930"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("tool_objekte", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("stellvertretung_user_id", postgresql.UUID(as_uuid=True), nullable=True)
        )
        batch_op.add_column(sa.Column("lauftyp", sa.String(length=24), nullable=True))
        batch_op.add_column(
            sa.Column("attest_entscheidung_ueber_personen", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(sa.Column("attest_mensch_dazwischen", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("attest_undeklarierte_quellen", sa.Boolean(), nullable=True))
        batch_op.add_column(
            sa.Column("attestiert_am", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("attestiert_von_user_id", postgresql.UUID(as_uuid=True), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_tool_stellvertretung", "users", ["stellvertretung_user_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_tool_attestiert_von", "users", ["attestiert_von_user_id"], ["id"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("tool_objekte", schema=None) as batch_op:
        batch_op.drop_constraint("fk_tool_attestiert_von", type_="foreignkey")
        batch_op.drop_constraint("fk_tool_stellvertretung", type_="foreignkey")
        batch_op.drop_column("attestiert_von_user_id")
        batch_op.drop_column("attestiert_am")
        batch_op.drop_column("attest_undeklarierte_quellen")
        batch_op.drop_column("attest_mensch_dazwischen")
        batch_op.drop_column("attest_entscheidung_ueber_personen")
        batch_op.drop_column("lauftyp")
        batch_op.drop_column("stellvertretung_user_id")
