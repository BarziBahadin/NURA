"""Support case workflow.

Revision ID: 20260504_006
Revises: 20260503_005
Create Date: 2026-05-04
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260504_006"
down_revision: Union[str, None] = "20260503_005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS support_departments (
            id          SERIAL PRIMARY KEY,
            code        TEXT UNIQUE NOT NULL,
            name        TEXT NOT NULL,
            description TEXT,
            is_active   BOOLEAN NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("""
        INSERT INTO support_departments (code, name, description)
        VALUES
            ('general', 'General Support', 'Default queue for uncategorized customer issues'),
            ('technical', 'Technical Support', 'Connectivity, coverage, device and service issues'),
            ('billing', 'Billing', 'Invoices, payments, packages and account balance'),
            ('complaints', 'Complaints', 'Formal complaints, escalations and service quality'),
            ('sales', 'Sales', 'New subscriptions, upgrades and offers')
        ON CONFLICT (code) DO NOTHING
    """)
    op.execute("CREATE SEQUENCE IF NOT EXISTS support_case_number_seq")

    op.execute("""
        CREATE TABLE IF NOT EXISTS support_cases (
            id             SERIAL PRIMARY KEY,
            case_number    TEXT UNIQUE NOT NULL,
            session_id     TEXT,
            customer_id    TEXT,
            channel        TEXT,
            title          TEXT NOT NULL,
            description    TEXT NOT NULL DEFAULT '',
            department     TEXT NOT NULL DEFAULT 'general',
            status         TEXT NOT NULL DEFAULT 'open'
                           CHECK (status IN ('open','pending','in_progress','waiting_customer','escalated','resolved','closed')),
            priority       TEXT NOT NULL DEFAULT 'normal'
                           CHECK (priority IN ('low','normal','high','urgent')),
            owner          TEXT,
            tags           TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            internal_notes TEXT NOT NULL DEFAULT '',
            source         TEXT NOT NULL DEFAULT 'manual',
            sla_due_at     TIMESTAMPTZ,
            first_response_due_at TIMESTAMPTZ,
            resolved_at    TIMESTAMPTZ,
            created_by     TEXT,
            updated_by     TEXT,
            created_at     TIMESTAMPTZ DEFAULT NOW(),
            updated_at     TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_cases_status_priority ON support_cases(status, priority)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cases_owner ON support_cases(owner)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cases_department ON support_cases(department)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cases_session ON support_cases(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cases_sla_due ON support_cases(sla_due_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_cases_sla_due")
    op.execute("DROP INDEX IF EXISTS idx_cases_session")
    op.execute("DROP INDEX IF EXISTS idx_cases_department")
    op.execute("DROP INDEX IF EXISTS idx_cases_owner")
    op.execute("DROP INDEX IF EXISTS idx_cases_status_priority")
    op.execute("DROP TABLE IF EXISTS support_cases")
    op.execute("DROP SEQUENCE IF EXISTS support_case_number_seq")
    op.execute("DROP TABLE IF EXISTS support_departments")
