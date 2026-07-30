"""seed default rubric and validation config

Revision ID: 5aa5fce960f1
Revises: 561e220c9434
Create Date: 2026-07-30 15:37:38.718544

"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5aa5fce960f1'
down_revision: Union[str, Sequence[str], None] = '561e220c9434'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEFAULT_WEIGHTS = {
    "grammar": 0.30,
    "readability": 0.20,
    "passive_voice": 0.15,
    "redundancy": 0.15,
    "ai_phrasing": 0.20,
}


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO rubric_versions (version, weights, threshold, active) "
            "VALUES (1, :weights, 0.75, 1)"
        ),
        {"weights": json.dumps(_DEFAULT_WEIGHTS)},
    )
    conn.execute(
        sa.text(
            "INSERT INTO validation_configs (version, stage_a_threshold, stage_b_threshold, active) "
            "VALUES (1, 0.90, 0.85, 1)"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM rubric_versions WHERE version = 1"))
    conn.execute(sa.text("DELETE FROM validation_configs WHERE version = 1"))
