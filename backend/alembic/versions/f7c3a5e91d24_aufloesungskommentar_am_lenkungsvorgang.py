"""Aufloesungskommentar als eigenes Feld am Lenkungsvorgang

Revision ID: f7c3a5e91d24
Revises: e1b6f3d27a94
Create Date: 2026-09-04 13:10:00.000000

Leitdokument A.13.6 und E-63. Der Kommentar beim Aufloesen eines
Lenkungsvorgangs wurde bisher an ``beschreibung`` angehaengt — an das Feld
also, in dem die **Feststellung** steht. Danach las sich der Befund als
„Zugriff auf ein Datenobjekt, das der Prozess nicht erklaert. Behoben am
Dienstag", und es war nicht mehr zu trennen, was gemeldet und was erwidert
worden war.

Das sind zwei Aussagen von zwei Menschen zu zwei Zeitpunkten. Sie bekommen
zwei Felder. Die Feststellung gehoert dem, der gemeldet hat, und aendert sich
nicht mehr.

Bestehende Vorgaenge bleiben, wie sie sind: was dort schon in ``beschreibung``
steht, laesst sich nachtraeglich nicht verlaesslich trennen — ein Kommentar
hatte kein Trennzeichen, das ihn eindeutig markiert. Der Verlauf im
Aenderungsprotokoll zeigt beides weiterhin getrennt.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f7c3a5e91d24"
down_revision: Union[str, Sequence[str], None] = "e1b6f3d27a94"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "lenkungsvorgaenge",
        sa.Column("aufloesungskommentar", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Der Kommentar geht verloren. Ihn zurueck in ``beschreibung`` zu schreiben
    # waere schlimmer als ihn zu verlieren: es stellte genau die Vermischung
    # wieder her, wegen der es dieses Feld gibt.
    op.drop_column("lenkungsvorgaenge", "aufloesungskommentar")
