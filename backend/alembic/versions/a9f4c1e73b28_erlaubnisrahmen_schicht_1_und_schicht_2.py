"""Erlaubnisrahmen: fehlende Elemente aus Schicht 1 und die Verbote aus Schicht 2

Revision ID: a9f4c1e73b28
Revises: b4d17c0a9e63
Create Date: 2026-09-02 15:20:00.000000

Leitdokument A.13.2 (Umsetzungsplan AP-6). Der Erlaubnisrahmen war zu drei
Siebteln umgesetzt: erlaubte Datenobjekte, Reichweite und externe Ziele liessen
sich ableiten, die uebrigen vier Elemente nicht. Zwei davon brauchen kein neues
Feld — die Obergrenze der Datenkategorie und die erlaubte Zugriffsart stehen
bereits in den verknuepften Datenobjekten und in der Output-Kante des Prozesses.
Die anderen beiden brauchen eines, weil ihnen das **gemessene** Gegenstueck
fehlte:

* ``ausfuehrungsidentitaet`` — unter welcher Identitaet das Tool laeuft. Der
  Rahmen leitet die erlaubte Identitaet aus der Ausfuehrungsart ab; ohne die
  tatsaechliche liesse sich nur behaupten, nicht pruefen.
* ``externe_ziele`` — wohin das Tool uebermittelt. Gegenstueck zu
  ``prozessobjekte.erlaubte_externe_ziele``: der Prozess erklaert, was erlaubt
  ist, das Tool traegt, was geschieht.

``statische_zugangsdaten`` und ``schicht2_verbot`` tragen Schicht 2. Diese sechs
Verbote sind durch keine Prozessbewertung freischaltbar, weshalb A.13.5 bei
ihnen die erste Eskalationsstufe streicht. Damit ein Vorgang spaeter noch
erklaerbar ist, muss an ihm stehen, *warum* er in Stufe 2 begonnen hat — sonst
sieht er aus wie ein eskalierter Stufe-1-Fall.

Alle Spalten sind nullable: ``NULL`` heisst unbeantwortet und ist von einem
erklaerten „Nein" zu unterscheiden. Bestandsdaten bleiben unangetastet.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a9f4c1e73b28"
down_revision: Union[str, Sequence[str], None] = "b4d17c0a9e63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("tool_objekte", schema=None) as batch_op:
        batch_op.add_column(sa.Column("ausfuehrungsidentitaet", sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column("statische_zugangsdaten", sa.Boolean(), nullable=True))
        batch_op.add_column(
            sa.Column("externe_ziele", sa.JSON(), nullable=False, server_default="[]")
        )
    with op.batch_alter_table("compliance_zustaende", schema=None) as batch_op:
        batch_op.add_column(sa.Column("schicht2_verbot", sa.String(length=48), nullable=True))
    with op.batch_alter_table("lenkungsvorgaenge", schema=None) as batch_op:
        batch_op.add_column(sa.Column("schicht2_verbot", sa.String(length=48), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("lenkungsvorgaenge", schema=None) as batch_op:
        batch_op.drop_column("schicht2_verbot")
    with op.batch_alter_table("compliance_zustaende", schema=None) as batch_op:
        batch_op.drop_column("schicht2_verbot")
    with op.batch_alter_table("tool_objekte", schema=None) as batch_op:
        batch_op.drop_column("externe_ziele")
        batch_op.drop_column("statische_zugangsdaten")
        batch_op.drop_column("ausfuehrungsidentitaet")
