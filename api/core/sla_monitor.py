import asyncio
import logging

from db.postgres import get_db_pool

logger = logging.getLogger(__name__)

ACTIVE_CASE_STATUSES = ("open", "pending", "in_progress", "waiting_customer", "escalated")


async def run_sla_monitor(interval_seconds: int = 60) -> None:
    logger.info("SLA monitor started")
    while True:
        try:
            await check_case_slas()
        except asyncio.CancelledError:
            logger.info("SLA monitor cancelled")
            raise
        except Exception as exc:
            logger.exception(f"SLA monitor error: {exc}")
        await asyncio.sleep(interval_seconds)


async def check_case_slas() -> dict:
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        breached = await conn.fetch(
            """
            UPDATE support_cases
            SET sla_status = 'breached',
                sla_breached_at = COALESCE(sla_breached_at, NOW()),
                updated_at = NOW(),
                updated_by = 'sla-monitor'
            WHERE status = ANY($1::text[])
              AND sla_due_at IS NOT NULL
              AND sla_due_at < NOW()
              AND sla_status != 'breached'
            RETURNING id, case_number, sla_due_at
            """,
            list(ACTIVE_CASE_STATUSES),
        )

        for row in breached:
            await conn.execute(
                """
                INSERT INTO support_case_activity (case_id, actor, action, field_name, old_value, new_value, note)
                VALUES ($1,'sla-monitor','sla_breached','sla_status',NULL,'breached',$2)
                """,
                row["id"], f"SLA breached for {row['case_number']}",
            )

        at_risk = await conn.fetch(
            """
            UPDATE support_cases
            SET sla_status = 'at_risk',
                sla_warned_at = COALESCE(sla_warned_at, NOW()),
                updated_at = NOW(),
                updated_by = 'sla-monitor'
            WHERE status = ANY($1::text[])
              AND sla_due_at IS NOT NULL
              AND sla_due_at >= NOW()
              AND sla_due_at <= NOW() + INTERVAL '2 hours'
              AND sla_status = 'ok'
            RETURNING id, case_number, sla_due_at
            """,
            list(ACTIVE_CASE_STATUSES),
        )

        for row in at_risk:
            await conn.execute(
                """
                INSERT INTO support_case_activity (case_id, actor, action, field_name, old_value, new_value, note)
                VALUES ($1,'sla-monitor','sla_at_risk','sla_status','ok','at_risk',$2)
                """,
                row["id"], f"SLA approaching for {row['case_number']}",
            )

    return {"breached": len(breached), "at_risk": len(at_risk)}
