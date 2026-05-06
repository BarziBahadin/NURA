"""Add suggestions department.

Revision ID: 20260506_009
Revises: 20260504_008
Create Date: 2026-05-06
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260506_009"
down_revision: Union[str, None] = "20260504_008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO support_departments (code, name, description)
        VALUES ('suggestions', 'Suggestions', 'Customer suggestions, recommendations and general feedback')
        ON CONFLICT (code) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM support_departments WHERE code = 'suggestions'")
