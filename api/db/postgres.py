import logging
from typing import Optional

import asyncpg

from config import settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            min_size=2,
            max_size=10,
        )
    return _pool


async def close_db_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def init_db() -> None:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        logger.info("PostgreSQL connection established")
        if not settings.db_auto_init:
            await conn.fetchval("SELECT 1")
            logger.info("DB_AUTO_INIT disabled; skipping startup schema creation")
            return

        # conversation_logs — add source column if this is an older schema
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_logs (
                id           SERIAL PRIMARY KEY,
                session_id   TEXT NOT NULL,
                customer_id  TEXT,
                channel      TEXT,
                customer_message TEXT,
                agent_response   TEXT,
                confidence   FLOAT,
                escalated    BOOLEAN DEFAULT FALSE,
                source       TEXT,
                created_at   TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            ALTER TABLE conversation_logs
            ADD COLUMN IF NOT EXISTS source TEXT
        """)

        # tree_clicks — kept for backwards compat
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tree_clicks (
                id          SERIAL PRIMARY KEY,
                session_id  TEXT,
                customer_id TEXT,
                topic_id    TEXT NOT NULL,
                topic_label TEXT NOT NULL,
                article_id  INT,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # widget_events — every button press in the chat widget
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS widget_events (
                id          SERIAL PRIMARY KEY,
                session_id  TEXT,
                customer_id TEXT,
                event_type  TEXT NOT NULL,
                label       TEXT,
                meta        TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # chat_turns — every individual turn, any role/source
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_turns (
                id          SERIAL PRIMARY KEY,
                session_id  TEXT NOT NULL,
                customer_id TEXT,
                channel     TEXT,
                role        TEXT NOT NULL,
                message     TEXT NOT NULL,
                source      TEXT NOT NULL,
                confidence  FLOAT,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_ct_session  ON chat_turns(session_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_ct_created  ON chat_turns(created_at)")

        # sessions — durable copy of live Redis session state
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id     TEXT PRIMARY KEY,
                customer_id    TEXT NOT NULL,
                channel        TEXT NOT NULL,
                status         TEXT NOT NULL,
                history        JSONB NOT NULL DEFAULT '[]'::jsonb,
                failure_count  INT NOT NULL DEFAULT 0,
                negative_score INT NOT NULL DEFAULT 0,
                metadata       JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at     TIMESTAMPTZ NOT NULL,
                updated_at     TIMESTAMPTZ NOT NULL
            )
        """)

        # security_logs — auth failures and rate limit hits
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS security_logs (
                id          SERIAL PRIMARY KEY,
                event_type  TEXT NOT NULL,
                detail      TEXT,
                ip          TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_audit_logs (
                id          SERIAL PRIMARY KEY,
                actor       TEXT,
                action      TEXT NOT NULL,
                target      TEXT,
                detail      TEXT,
                ip          TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # message_feedback — per-turn thumbs up/down from customers
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS message_feedback (
                id          SERIAL PRIMARY KEY,
                session_id  TEXT NOT NULL,
                customer_id TEXT,
                channel     TEXT,
                turn_id     TEXT,
                score       TEXT NOT NULL,
                source      TEXT,
                reason      TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # session_outcomes — detailed resolution records filled by agent on close
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS session_outcomes (
                id                          SERIAL PRIMARY KEY,
                session_id                  TEXT NOT NULL UNIQUE,
                status                      TEXT,
                issue_category              TEXT,
                root_cause                  TEXT,
                handoff_reason              TEXT,
                resolution_notes            TEXT,
                resolved_by                 TEXT,
                accepted_at                 TIMESTAMPTZ,
                resolved_at                 TIMESTAMPTZ,
                first_agent_response_at     TIMESTAMPTZ,
                time_to_accept_seconds      FLOAT,
                time_to_resolution_seconds  FLOAT,
                created_at                  TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            ALTER TABLE session_outcomes
            ADD COLUMN IF NOT EXISTS handoff_reason TEXT
        """)

        # message_insights — async intent/sentiment classification per customer turn
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS message_insights (
                id                SERIAL PRIMARY KEY,
                session_id        TEXT NOT NULL,
                customer_id       TEXT,
                channel           TEXT,
                message_text      TEXT NOT NULL,
                language          TEXT,
                intent            TEXT,
                sub_intent        TEXT,
                sentiment         TEXT,
                confidence_bucket TEXT,
                is_knowledge_gap  BOOLEAN DEFAULT FALSE,
                gap_reason        TEXT,
                created_at        TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # knowledge_gap_reviews — admin workflow for turning failed answers into curated knowledge
        await conn.execute("""
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

        # support_departments / support_cases — back-office ticket workflow
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS support_departments (
                id          SERIAL PRIMARY KEY,
                code        TEXT UNIQUE NOT NULL,
                name        TEXT NOT NULL,
                description TEXT,
                is_active   BOOLEAN NOT NULL DEFAULT TRUE,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            INSERT INTO support_departments (code, name, description)
            VALUES
                ('general', 'General Support', 'Default queue for uncategorized customer issues'),
                ('technical', 'Technical Support', 'Connectivity, coverage, device and service issues'),
                ('billing', 'Billing', 'Invoices, payments, packages and account balance'),
                ('complaints', 'Complaints', 'Formal complaints, escalations and service quality'),
                ('sales', 'Sales', 'New subscriptions, upgrades and offers')
            ON CONFLICT (code) DO NOTHING
        """)
        await conn.execute("CREATE SEQUENCE IF NOT EXISTS support_case_number_seq")
        await conn.execute("""
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
                sla_status     TEXT NOT NULL DEFAULT 'ok'
                               CHECK (sla_status IN ('ok','at_risk','breached')),
                sla_warned_at   TIMESTAMPTZ,
                sla_breached_at TIMESTAMPTZ,
                resolved_at    TIMESTAMPTZ,
                created_by     TEXT,
                updated_by     TEXT,
                created_at     TIMESTAMPTZ DEFAULT NOW(),
                updated_at     TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            ALTER TABLE support_cases
            ADD COLUMN IF NOT EXISTS sla_status TEXT NOT NULL DEFAULT 'ok'
                CHECK (sla_status IN ('ok','at_risk','breached'))
        """)
        await conn.execute("ALTER TABLE support_cases ADD COLUMN IF NOT EXISTS sla_warned_at TIMESTAMPTZ")
        await conn.execute("ALTER TABLE support_cases ADD COLUMN IF NOT EXISTS sla_breached_at TIMESTAMPTZ")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS support_case_activity (
                id          SERIAL PRIMARY KEY,
                case_id     INT NOT NULL REFERENCES support_cases(id) ON DELETE CASCADE,
                actor       TEXT,
                action      TEXT NOT NULL,
                field_name  TEXT,
                old_value   TEXT,
                new_value   TEXT,
                note        TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # llm_usage_logs — token and cost tracking per OpenAI call
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_usage_logs (
                id               SERIAL PRIMARY KEY,
                session_id       TEXT,
                model            TEXT NOT NULL,
                operation        TEXT NOT NULL,
                prompt_tokens    INT DEFAULT 0,
                completion_tokens INT DEFAULT 0,
                total_tokens     INT DEFAULT 0,
                estimated_cost   FLOAT DEFAULT 0.0,
                created_at       TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_message_stats (
                day DATE PRIMARY KEY,
                messages INT NOT NULL DEFAULT 0,
                sessions INT NOT NULL DEFAULT 0,
                escalations INT NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_cost_stats (
                day DATE PRIMARY KEY,
                total_tokens INT NOT NULL DEFAULT 0,
                estimated_cost FLOAT NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_handoff_stats (
                day DATE NOT NULL,
                handoff_reason TEXT NOT NULL,
                count INT NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (day, handoff_reason)
            )
        """)

        await conn.execute("CREATE INDEX IF NOT EXISTS idx_cl_created  ON conversation_logs(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_cl_session   ON conversation_logs(session_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_cl_created_session ON conversation_logs(created_at, session_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_cl_source_created ON conversation_logs(source, created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_tc_topic    ON tree_clicks(topic_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_tc_created  ON tree_clicks(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_we_type     ON widget_events(event_type)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_we_created  ON widget_events(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status  ON sessions(status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_channel ON sessions(channel)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_sl_created  ON security_logs(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_mf_session  ON message_feedback(session_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_mf_created  ON message_feedback(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_so_session  ON session_outcomes(session_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_so_created_status ON session_outcomes(created_at, status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_mi_session  ON message_insights(session_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_mi_intent   ON message_insights(intent)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_mi_created  ON message_insights(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_mi_created_intent ON message_insights(created_at, intent)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_kgr_status_created ON knowledge_gap_reviews(status, created_at DESC)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_kgr_intent ON knowledge_gap_reviews(intent)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_status_priority ON support_cases(status, priority)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_owner ON support_cases(owner)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_department ON support_cases(department)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_session ON support_cases(session_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_sla_due ON support_cases(sla_due_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_sla_status ON support_cases(sla_status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_case_activity_case_created ON support_case_activity(case_id, created_at DESC)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_lu_session  ON llm_usage_logs(session_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_lu_created  ON llm_usage_logs(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_lu_created_operation ON llm_usage_logs(created_at, operation)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON admin_audit_logs(created_at)")
