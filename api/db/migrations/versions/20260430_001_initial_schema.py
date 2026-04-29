"""Initial NURA reporting and support schema.

Revision ID: 20260430_001
Revises: None
Create Date: 2026-04-30
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260430_001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS conversation_logs (
            id SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL,
            customer_id TEXT,
            channel TEXT,
            customer_message TEXT,
            agent_response TEXT,
            confidence FLOAT,
            escalated BOOLEAN DEFAULT FALSE,
            source TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("ALTER TABLE conversation_logs ADD COLUMN IF NOT EXISTS source TEXT")

    op.execute("""
        CREATE TABLE IF NOT EXISTS tree_clicks (
            id SERIAL PRIMARY KEY,
            session_id TEXT,
            customer_id TEXT,
            topic_id TEXT NOT NULL,
            topic_label TEXT NOT NULL,
            article_id INT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS widget_events (
            id SERIAL PRIMARY KEY,
            session_id TEXT,
            customer_id TEXT,
            event_type TEXT NOT NULL,
            label TEXT,
            meta TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_turns (
            id SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL,
            customer_id TEXT,
            channel TEXT,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            source TEXT NOT NULL,
            confidence FLOAT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS security_logs (
            id SERIAL PRIMARY KEY,
            event_type TEXT NOT NULL,
            detail TEXT,
            ip TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_logs (
            id SERIAL PRIMARY KEY,
            filename TEXT,
            chunks_stored INT DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS message_feedback (
            id SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL,
            customer_id TEXT,
            channel TEXT,
            turn_id TEXT,
            score TEXT NOT NULL,
            source TEXT,
            reason TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS session_outcomes (
            id SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL UNIQUE,
            status TEXT,
            issue_category TEXT,
            root_cause TEXT,
            handoff_reason TEXT,
            resolution_notes TEXT,
            resolved_by TEXT,
            accepted_at TIMESTAMPTZ,
            resolved_at TIMESTAMPTZ,
            first_agent_response_at TIMESTAMPTZ,
            time_to_accept_seconds FLOAT,
            time_to_resolution_seconds FLOAT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("ALTER TABLE session_outcomes ADD COLUMN IF NOT EXISTS handoff_reason TEXT")

    op.execute("""
        CREATE TABLE IF NOT EXISTS message_insights (
            id SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL,
            customer_id TEXT,
            channel TEXT,
            message_text TEXT NOT NULL,
            language TEXT,
            intent TEXT,
            sub_intent TEXT,
            sentiment TEXT,
            confidence_bucket TEXT,
            is_knowledge_gap BOOLEAN DEFAULT FALSE,
            gap_reason TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS llm_usage_logs (
            id SERIAL PRIMARY KEY,
            session_id TEXT,
            model TEXT NOT NULL,
            operation TEXT NOT NULL,
            prompt_tokens INT DEFAULT 0,
            completion_tokens INT DEFAULT 0,
            total_tokens INT DEFAULT 0,
            estimated_cost FLOAT DEFAULT 0.0,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_cl_created ON conversation_logs(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cl_session ON conversation_logs(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tc_topic ON tree_clicks(topic_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tc_created ON tree_clicks(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_we_type ON widget_events(event_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_we_created ON widget_events(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ct_session ON chat_turns(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ct_created ON chat_turns(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sl_created ON security_logs(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mf_session ON message_feedback(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mf_created ON message_feedback(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_so_session ON session_outcomes(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mi_session ON message_insights(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mi_intent ON message_insights(intent)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mi_created ON message_insights(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_lu_session ON llm_usage_logs(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_lu_created ON llm_usage_logs(created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS llm_usage_logs")
    op.execute("DROP TABLE IF EXISTS message_insights")
    op.execute("DROP TABLE IF EXISTS session_outcomes")
    op.execute("DROP TABLE IF EXISTS message_feedback")
    op.execute("DROP TABLE IF EXISTS ingestion_logs")
    op.execute("DROP TABLE IF EXISTS security_logs")
    op.execute("DROP TABLE IF EXISTS chat_turns")
    op.execute("DROP TABLE IF EXISTS widget_events")
    op.execute("DROP TABLE IF EXISTS tree_clicks")
    op.execute("DROP TABLE IF EXISTS conversation_logs")
