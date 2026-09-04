"""Alle sechs Verbote der Schicht 2 stehen am Tool-Objekt

Revision ID: a5d1f78b2c40
Revises: c3b8e42f1a76
Create Date: 2026-09-04 16:20:00.000000

Leitdokument A.13.2 und E-64. Vier der sechs Verbote las die Anwendung aus den
Daten des Tool-Objekts; die beiden anderen — umgangene Protokollierung und
Daten im offenen Netz — waren nur ueber eine Meldung erfassbar, in der jemand
das Verbot aus einer Liste auswaehlte.

Damit war dieselbe Tatsache je nach Verbot einmal eine Eigenschaft des
Werkzeugs und einmal eine Behauptung in einem Vorgang. Pruefen liess sich nur
die eine Haelfte: ein Werkzeug konnte gruen werden, obwohl die Protokollierung
weiterhin umgangen wurde, denn davon stand in seinen Daten nichts.

Beide werden jetzt am Werkzeug erklaert, wie die drei Attestierungen aus A.6.
``None`` heisst unbeantwortet, ``True`` ist der Verstoss. Danach misst
``pruefe_schicht2`` alle sechs, und die Meldung braucht keine Auswahlliste mehr.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a5d1f78b2c40"
down_revision: Union[str, Sequence[str], None] = "c3b8e42f1a76"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    for spalte in ("protokollierung_umgangen", "daten_ins_offene_netz"):
        op.add_column("tool_objekte", sa.Column(spalte, sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    for spalte in ("daten_ins_offene_netz", "protokollierung_umgangen"):
        op.drop_column("tool_objekte", spalte)
