"""calibrate stage a threshold from labeled set

Revision ID: ad5fbc05deea
Revises: 5aa5fce960f1
Create Date: 2026-07-30 15:56:45.913967

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad5fbc05deea'
down_revision: Union[str, Sequence[str], None] = '5aa5fce960f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    # scripts/calibrate_thresholds.py against tests/data/semantic_pairs.json (24 labeled
    # pairs): threshold sweep 0.80-0.98 found 0.89 as the best F1 (0.85) among thresholds
    # with zero missed meaning-alterations. Stage B stays at its placeholder (0.85) —
    # calibrating it requires live, billable LLM calls that weren't run yet.
    conn.execute(sa.text("UPDATE validation_configs SET active = 0 WHERE version = 1"))
    conn.execute(
        sa.text(
            "INSERT INTO validation_configs (version, stage_a_threshold, stage_b_threshold, active) "
            "VALUES (2, 0.89, 0.85, 1)"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM validation_configs WHERE version = 2"))
    conn.execute(sa.text("UPDATE validation_configs SET active = 1 WHERE version = 1"))
