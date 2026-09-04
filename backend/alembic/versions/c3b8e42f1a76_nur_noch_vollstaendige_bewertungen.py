"""Nur noch vollstaendige Bewertungen

Revision ID: c3b8e42f1a76
Revises: f7c3a5e91d24
Create Date: 2026-09-04 15:40:00.000000

Leitdokument A.8.5 und E-64. Der Bewertungsbaum kannte eine schnelle Variante,
die beim ersten Tier-3-Treffer abbrach. Sie hinterliess eine Bewertung, in der
die nicht durchlaufenen Dimensionen auf null standen und **keine** K-Klasse
ausgeloest war — obwohl das Tier stimmte.

Das war nicht nur ungenau, sondern gefaehrlich: eine solche Bewertung konnte
eine vollstaendige ablösen. Aus acht Anforderungsklassen wurde dann keine, ohne
dass jemand etwas geloescht haette. Nachgelagerte Pruefungen — die Aktivierung
ab Tier 3, die Selbstverpflichtung, die Aufloesung eines Lenkungsvorgangs durch
Rahmenerweiterung — stuetzten sich danach auf Antworten, die nie gegeben wurden.

Es gibt jetzt einen Ausgang. Die Spalte ``vollstaendig`` entfaellt; sie waere
ab hier immer wahr. Der Abbruch bei einem Verbotstatbestand (A.8.5, Schritt 1b)
bleibt unberuehrt: dort entsteht ueberhaupt keine Bewertung, sondern ein
Governance-Alarm.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3b8e42f1a76"
down_revision: Union[str, Sequence[str], None] = "f7c3a5e91d24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("bewertungen", "vollstaendig")


def downgrade() -> None:
    """Downgrade schema."""
    # Zurueck stehen alle Bewertungen als vollstaendig da. Das ist richtig: die
    # unvollstaendigen von frueher waren der Fehler, nicht der Normalfall.
    op.add_column(
        "bewertungen",
        sa.Column("vollstaendig", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
