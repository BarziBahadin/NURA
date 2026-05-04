"""Support case SLA state.

Revision ID: 20260504_008
Revises: 20260504_007
Create Date: 2026-05-04
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260504_008"
down_revision: Union[str, None] = "20260504_007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE support_cases
        ADD COLUMN IF NOT EXISTS sla_status TEXT NOT NULL DEFAULT 'ok'
            CHECK (sla_status IN ('ok','at_risk','breached'))
    """)
    op.execute("ALTER TABLE support_cases ADD COLUMN IF NOT EXISTS sla_warned_at TIMESTAMPTZ")
    op.execute("ALTER TABLE support_cases ADD COLUMN IF NOT EXISTS sla_breached_at TIMESTAMPTZ")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cases_sla_status ON support_cases(sla_status)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_cases_sla_status")
    op.execute("ALTER TABLE support_cases DROP COLUMN IF EXISTS sla_breached_at")
    op.execute("ALTER TABLE support_cases DROP COLUMN IF EXISTS sla_warned_at")
    op.execute("ALTER TABLE support_cases DROP COLUMN IF EXISTS sla_status")
