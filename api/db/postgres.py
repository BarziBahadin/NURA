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


async def init_db() -> None:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        logger.info("PostgreSQL connection established")

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

        await conn.execute("CREATE INDEX IF NOT EXISTS idx_cl_created  ON conversation_logs(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_tc_topic    ON tree_clicks(topic_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_tc_created  ON tree_clicks(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_we_type     ON widget_events(event_type)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_we_created  ON widget_events(created_at)")
