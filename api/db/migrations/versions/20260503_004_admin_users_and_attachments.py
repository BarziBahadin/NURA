"""Admin users table for DB-based multi-user auth.

Revision ID: 20260503_004
Revises: 20260503_003
Create Date: 2026-05-03
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260503_004"
down_revision: Union[str, None] = "20260503_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id           SERIAL PRIMARY KEY,
            username     VARCHAR(128) UNIQUE NOT NULL,
            password_hash VARCHAR(256) NOT NULL,
            role         VARCHAR(32)  NOT NULL DEFAULT 'agent'
                         CHECK (role IN ('admin','agent','viewer')),
            display_name VARCHAR(128),
            is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
            created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            last_login   TIMESTAMPTZ,
            created_by   VARCHAR(128)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_admin_users_username ON admin_users(username)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_admin_users_username")
    op.execute("DROP TABLE IF EXISTS admin_users")
