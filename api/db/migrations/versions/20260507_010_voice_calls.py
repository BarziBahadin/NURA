"""Add self-hosted voice call tracking.

Revision ID: 20260507_010
Revises: 20260506_009
Create Date: 2026-05-07
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260507_010"
down_revision: Union[str, None] = "20260506_009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS voice_calls (
            id SERIAL PRIMARY KEY,
            call_id TEXT UNIQUE NOT NULL,
            session_id TEXT NOT NULL,
            customer_id TEXT,
            channel TEXT NOT NULL DEFAULT 'web',
            room_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'requested'
                CHECK (status IN ('requested','accepted','active','ended','missed','cancelled')),
            requested_at TIMESTAMPTZ DEFAULT NOW(),
            accepted_at TIMESTAMPTZ,
            ended_at TIMESTAMPTZ,
            accepted_by TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        )
    """)
    op.execute("ALTER TABLE voice_calls ADD COLUMN IF NOT EXISTS room_name TEXT")
    op.execute("ALTER TABLE voice_calls ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE voice_calls ALTER COLUMN room_name DROP NOT NULL")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'voice_calls' AND column_name = 'join_url'
            ) THEN
                ALTER TABLE voice_calls ALTER COLUMN join_url DROP NOT NULL;
            END IF;
        END $$;
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_voice_calls_status_created ON voice_calls(status, requested_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_voice_calls_session ON voice_calls(session_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_voice_calls_session")
    op.execute("DROP INDEX IF EXISTS idx_voice_calls_status_created")
    op.execute("DROP TABLE IF EXISTS voice_calls")
