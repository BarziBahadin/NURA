"""Add admin user token version.

Revision ID: 20260513_010
Revises: 20260506_009
Create Date: 2026-05-13
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260513_010"
down_revision: Union[str, None] = "20260506_009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE admin_users
        ADD COLUMN IF NOT EXISTS token_version INT NOT NULL DEFAULT 0
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE admin_users
        DROP COLUMN IF EXISTS token_version
    """)
