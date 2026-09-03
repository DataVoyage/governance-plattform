"""Datenobjekt gehoert dem Fachbereich, nicht einer Person

Revision ID: d4f7a2c19e60
Revises: c2e8b7d41f05
Create Date: 2026-09-03 14:20:00.000000

docs/rollen-und-scopes.md, Abschnitt 7, und E-55. Das Datenobjekt trug einen
persoenlichen Owner, und die Oberflaeche bot dazu ein Dropdown mit allen
Nutzernamen — unter einer Hilfe, die von der „datenhaltenden Stelle" sprach.
Beides zugleich ging nicht: eine Quelle gehoert einem Fachbereich, und wer sie
klassifiziert, ist der Datenobjekt-Owner dieses Fachbereichs — eine Rolle,
keine Eigenschaft des Objekts.

Die Spalte faellt weg. Wer bisher ueber ``owner_user_id`` schreiben durfte,
darf es jetzt ueber seine Rolle im Fachbereich oder als Owner des gebenden
Prozesses; die Sichtregel laeuft ueber Fachbereich und Referenzen. Die
Rueckmigration legt die Spalte leer wieder an — die Zuordnung zu Personen ist
nicht rekonstruierbar und soll es auch nicht sein.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4f7a2c19e60"
down_revision: Union[str, Sequence[str], None] = "c2e8b7d41f05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("datenobjekte_owner_user_id_fkey", "datenobjekte", type_="foreignkey")
    op.drop_column("datenobjekte", "owner_user_id")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "datenobjekte",
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "datenobjekte_owner_user_id_fkey", "datenobjekte", "users", ["owner_user_id"], ["id"]
    )
