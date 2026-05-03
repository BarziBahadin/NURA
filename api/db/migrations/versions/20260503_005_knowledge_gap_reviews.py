"""Knowledge gap review workflow.

Revision ID: 20260503_005
Revises: 20260503_004
Create Date: 2026-05-03
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260503_005"
down_revision: Union[str, None] = "20260503_004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_gap_reviews (
            id                SERIAL PRIMARY KEY,
            insight_id        INT UNIQUE REFERENCES message_insights(id) ON DELETE SET NULL,
            session_id        TEXT NOT NULL,
            customer_id       TEXT,
            channel           TEXT,
            customer_message  TEXT NOT NULL,
            intent            TEXT,
            sub_intent        TEXT,
            gap_reason        TEXT,
            status            TEXT NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending','drafted','approved','rejected','resolved')),
            proposed_answer   TEXT,
            approved_answer   TEXT,
            notes             TEXT,
            reviewed_by       TEXT,
            reviewed_at       TIMESTAMPTZ,
            created_at        TIMESTAMPTZ DEFAULT NOW(),
            updated_at        TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_kgr_status_created ON knowledge_gap_reviews(status, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_kgr_intent ON knowledge_gap_reviews(intent)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_kgr_intent")
    op.execute("DROP INDEX IF EXISTS idx_kgr_status_created")
    op.execute("DROP TABLE IF EXISTS knowledge_gap_reviews")
