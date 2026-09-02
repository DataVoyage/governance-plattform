"""Technologiematrix und Kompensationen

Revision ID: c2e8b7d41f05
Revises: a9f4c1e73b28
Create Date: 2026-09-02 18:10:00.000000

Leitdokument A.9.3 und Teil C.1 (Umsetzungsplan AP-7). Die Anwendung endete
bisher bei den K-Codes und machte die zweite Uebersetzungsstufe aus A.9.1
nicht: sie sagte, welche Klassen ausgeloest sind, aber nicht, ob die gewaehlte
Technologie sie tragen kann. Damit fehlte die Entscheidung, auf die das
Bewertungsmodell zulaeuft.

``technologie_bewertungen`` ist die Matrix Technologie x Klasse. Sie liegt als
Stammdaten in der Datenbank und nicht als Konstante im Code, weil sie eine
Entscheidungsgrundlage ist: eine, die nur mit einer Auslieferung aenderbar
waere, veraltet zwischen zwei Releases. Die Standardbelegung legt
``services/klassen.initialisiere`` beim ersten Zugriff an — die Migration
schafft nur den Platz dafuer, damit die fachliche Belegung an einer Stelle
steht und nicht in zwei.

``kompensationen`` haelt die dokumentierte Massnahme zu einer kompensierbaren
Klasse fest. Ohne sie bleibt der Befund offen: „kompensierende Massnahme
erforderlich" ist eine Aufgabe, und eine Aufgabe ohne Beschreibung ist nicht
pruefbar.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c2e8b7d41f05"
down_revision: Union[str, Sequence[str], None] = "a9f4c1e73b28"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "technologie_bewertungen",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("technologie", sa.String(length=64), nullable=False),
        sa.Column("k_klasse", sa.String(length=8), nullable=False),
        sa.Column("bewertung", sa.String(length=24), nullable=False),
        sa.Column("begruendung", sa.Text(), nullable=False, server_default=""),
        sa.Column("geaendert_von", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("erstellt_am", sa.DateTime(timezone=True), nullable=False),
        sa.Column("geaendert_am", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["geaendert_von"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("technologie", "k_klasse", name="uq_technologie_klasse"),
    )
    op.create_table(
        "kompensationen",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tool_objekt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("k_klasse", sa.String(length=8), nullable=False),
        sa.Column("massnahme", sa.Text(), nullable=False),
        sa.Column("erfasst_von", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("erfasst_am", sa.DateTime(timezone=True), nullable=False),
        sa.Column("erstellt_am", sa.DateTime(timezone=True), nullable=False),
        sa.Column("geaendert_am", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tool_objekt_id"], ["tool_objekte.id"]),
        sa.ForeignKeyConstraint(["erfasst_von"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tool_objekt_id", "k_klasse", name="uq_kompensation_tool_klasse"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("kompensationen")
    op.drop_table("technologie_bewertungen")
