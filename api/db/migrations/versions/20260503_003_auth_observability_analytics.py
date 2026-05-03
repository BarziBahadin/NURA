"""Auth audit and analytics hardening indexes.

Revision ID: 20260503_003
Revises: 20260430_002
Create Date: 2026-05-03
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260503_003"
down_revision: Union[str, None] = "20260430_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS admin_audit_logs (
            id SERIAL PRIMARY KEY,
            actor TEXT,
            action TEXT NOT NULL,
            target TEXT,
            detail TEXT,
            ip TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS daily_message_stats (
            day DATE PRIMARY KEY,
            messages INT NOT NULL DEFAULT 0,
            sessions INT NOT NULL DEFAULT 0,
            escalations INT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS daily_cost_stats (
            day DATE PRIMARY KEY,
            total_tokens INT NOT NULL DEFAULT 0,
            estimated_cost FLOAT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS daily_handoff_stats (
            day DATE NOT NULL,
            handoff_reason TEXT NOT NULL,
            count INT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (day, handoff_reason)
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_cl_created_session ON conversation_logs(created_at, session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cl_source_created ON conversation_logs(source, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_so_created_status ON session_outcomes(created_at, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mi_created_intent ON message_insights(created_at, intent)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_lu_created_operation ON llm_usage_logs(created_at, operation)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON admin_audit_logs(created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS daily_handoff_stats")
    op.execute("DROP TABLE IF EXISTS daily_cost_stats")
    op.execute("DROP TABLE IF EXISTS daily_message_stats")
    op.execute("DROP TABLE IF EXISTS admin_audit_logs")
