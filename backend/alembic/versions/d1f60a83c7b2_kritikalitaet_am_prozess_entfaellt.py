"""Die abgeleitete Kritikalitaet am Prozessobjekt entfaellt

Revision ID: d1f60a83c7b2
Revises: c9a2d7e51b04
Create Date: 2026-09-07 20:00:00.000000

Leitdokument A.4.2 und A.8.4 (Umsetzungsplan AP-19, E-67, E-72).

``prozessobjekte.kritikalitaet`` hielt die eigene Ausfallfolge, hochgezogen auf
das Maximum der Prozesskette. Seit AP-19 wirkt der Kettenanteil ausschliesslich
am Tier, und zwar ueber das **komposite** UR der Nachfolger
(``services/risiko.ur_der_kette``). Damit stand hier eine zweite Aussage ueber
dieselbe Kette neben der, die zaehlt — und beide laufen auseinander: die rohe
Ausfallfolge kennt die Reichweite nicht, das komposite UR schon. Ein Nachfolger
mit kritischem Ausfall, der nur eine Person betrifft, hob die Kritikalitaet auf
3 und das Tier um nichts.

Gelesen hat das Feld zuletzt niemand mehr ausser der Anzeige: Der
Erlaubnisrahmen und die Vererbung ans Werkzeug nehmen ``bewertung.ur_stufe``,
das Cockpit liest die Kettenzeile ueber ``bewertung.tier_herkunft``. Ein Wert,
den die Anwendung pflegt, anzeigt und nicht mehr benutzt, ist genau die zweite
Ebene, die AP-19 aufgeloest hat (Konzept, Abschnitt 3).

Die Kritikalitaet am **Werkzeug** (``tool_objekte``) bleibt unberuehrt — sie
kommt aus der Bewertung und wird gebraucht.

Der Rueckweg stellt die Spalte mit ihrem Vorgabewert wieder her. Er kann sie
nicht neu berechnen: Die Rechnung dafuer gibt es nicht mehr, und ein
Nachtlauf ueber ``aktualisiere_ableitungen`` wuerde sie auch nicht mehr fuellen.
Wer wirklich zurueckmuss, spielt einen Snapshot ein.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1f60a83c7b2"
down_revision: Union[str, Sequence[str], None] = "c9a2d7e51b04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("prozessobjekte", "kritikalitaet")


def downgrade() -> None:
    op.add_column(
        "prozessobjekte",
        sa.Column("kritikalitaet", sa.Integer(), nullable=False, server_default="0"),
    )
