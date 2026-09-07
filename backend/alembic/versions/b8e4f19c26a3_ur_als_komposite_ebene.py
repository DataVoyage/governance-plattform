"""UR als komposite Ebene aus Reichweite und Ausfallfolge

Revision ID: b8e4f19c26a3
Revises: a5d1f78b2c40
Create Date: 2026-09-07 10:00:00.000000

Leitdokument A.8.4 (Umsetzungsplan AP-19, E-66). Das unternehmerische Risiko
war bisher eine einzelne Aussage, erhoben ueber drei Fragen des Bewertungsbaums
— deren richtige Antwort die Anwendung bereits kannte und daneben als Vorschlag
stellte. Es besteht tatsaechlich aus zwei erklaerten Erwartungen des
Prozess-Owners: der erlaubten Reichweite und der Ausfallfolge. Keiner der
beiden Werte traegt allein.

``ur_komposition`` ist die Tabelle Ausfallfolge x Reichweite. Sie liegt wie die
Technologiematrix als Stammdaten in der Datenbank und nicht als Konstante im
Code, weil sie eine Bewertungsgrundlage ist: eine, die nur mit einer
Auslieferung aenderbar waere, veraltet zwischen zwei Releases. Die
Standardbelegung legt ``services/risiko.initialisiere`` beim ersten Zugriff an
— die Migration schafft nur den Platz dafuer, damit die fachliche Belegung an
einer Stelle steht und nicht in zwei.

Die Migration ist reine Erweiterung: kein Bestandsfeld wird angefasst, keine
Bewertung umgeschrieben. Bereits gespeicherte ``ur_stufe``-Werte bleiben, wie
sie erhoben wurden — eine rueckwirkende Neuberechnung waere eine stille
Aenderung an abgeschlossenen Bewertungen und wuerde die Historie unbrauchbar
machen (A.13.7). Neu gerechnet wird erst bei der naechsten Bewertung.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b8e4f19c26a3"
down_revision: Union[str, Sequence[str], None] = "a5d1f78b2c40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "ur_komposition",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ausfallfolge", sa.String(length=24), nullable=False),
        sa.Column("reichweite", sa.String(length=24), nullable=False),
        sa.Column("stufe", sa.Integer(), nullable=False),
        sa.Column("begruendung", sa.Text(), nullable=False, server_default=""),
        sa.Column("geaendert_von", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("erstellt_am", sa.DateTime(timezone=True), nullable=False),
        sa.Column("geaendert_am", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["geaendert_von"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ausfallfolge", "reichweite", name="uq_ur_komposition_paarung"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("ur_komposition")
