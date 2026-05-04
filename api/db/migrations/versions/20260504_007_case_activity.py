"""Support case activity timeline.

Revision ID: 20260504_007
Revises: 20260504_006
Create Date: 2026-05-04
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260504_007"
down_revision: Union[str, None] = "20260504_006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS support_case_activity (
            id          SERIAL PRIMARY KEY,
            case_id     INT NOT NULL REFERENCES support_cases(id) ON DELETE CASCADE,
            actor       TEXT,
            action      TEXT NOT NULL,
            field_name  TEXT,
            old_value   TEXT,
            new_value   TEXT,
            note        TEXT,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_case_activity_case_created ON support_case_activity(case_id, created_at DESC)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_case_activity_case_created")
    op.execute("DROP TABLE IF EXISTS support_case_activity")
