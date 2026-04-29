"""Add durable sessions table.

Revision ID: 20260430_002
Revises: 20260430_001
Create Date: 2026-04-30
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260430_002"
down_revision: Union[str, None] = "20260430_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            channel TEXT NOT NULL,
            status TEXT NOT NULL,
            history JSONB NOT NULL DEFAULT '[]'::jsonb,
            failure_count INT NOT NULL DEFAULT 0,
            negative_score INT NOT NULL DEFAULT 0,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_channel ON sessions(channel)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sessions")
