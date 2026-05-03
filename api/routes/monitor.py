from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query

from core.auth import require_roles
from core.session_manager import get_all_sessions
from db.postgres import get_db_pool
from models.session import SessionStatus

router = APIRouter()


@router.get("/monitor/stats/realtime", dependencies=[Depends(require_roles("admin"))])
async def realtime_stats():
    all_sessions = await get_all_sessions()
    active_count = sum(1 for s in all_sessions if s.status == SessionStatus.active)
    pending_count = sum(1 for s in all_sessions if s.status == SessionStatus.pending_handoff)
    human_count = sum(1 for s in all_sessions if s.status == SessionStatus.human_active)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        messages_last_hour = await conn.fetchval(
            "SELECT COUNT(*) FROM conversation_logs WHERE created_at > NOW() - INTERVAL '1 hour'"
        ) or 0
        cost_today = await conn.fetchval(
            "SELECT COALESCE(SUM(estimated_cost), 0) FROM llm_usage_logs "
            "WHERE created_at >= CURRENT_DATE"
        ) or 0.0
        total_today = await conn.fetchval(
            "SELECT COUNT(*) FROM session_outcomes WHERE created_at >= CURRENT_DATE"
        ) or 0
        escalated_today = await conn.fetchval(
            "SELECT COUNT(*) FROM session_outcomes "
            "WHERE created_at >= CURRENT_DATE AND handoff_reason IS NOT NULL AND handoff_reason != ''"
        ) or 0

    escalation_rate = round(escalated_today / total_today * 100) if total_today > 0 else 0

    return {
        "active_sessions": active_count,
        "pending_handoff": pending_count,
        "human_active": human_count,
        "messages_last_hour": messages_last_hour,
        "cost_today_usd": round(float(cost_today), 4),
        "escalation_rate_today_pct": escalation_rate,
    }


@router.get("/monitor/sessions/live", dependencies=[Depends(require_roles("admin"))])
async def live_sessions():
    all_sessions = await get_all_sessions()
    live = [
        s for s in all_sessions
        if s.status in (SessionStatus.active, SessionStatus.pending_handoff, SessionStatus.human_active)
    ]
    live.sort(key=lambda s: s.updated_at, reverse=True)
    return {
        "total": len(live),
        "sessions": [
            {
                "session_id": s.session_id,
                "customer_id": s.customer_id,
                "channel": s.channel,
                "status": s.status.value,
                "message_count": len(s.history),
                "last_activity": s.updated_at,
                "assigned_to": s.metadata.get("assigned_agent", ""),
                "handoff_reason": s.metadata.get("handoff_reason", ""),
            }
            for s in live
        ],
    }


@router.get("/monitor/audit-log", dependencies=[Depends(require_roles("admin"))])
async def audit_log(
    actor: Optional[str] = None,
    action: Optional[str] = None,
    from_date: Optional[str] = Query(default=None, alias="from"),
    to_date: Optional[str] = Query(default=None, alias="to"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    conditions = ["1=1"]
    params: list = []
    i = 1

    if actor:
        conditions.append(f"actor = ${i}")
        params.append(actor)
        i += 1
    if action:
        conditions.append(f"action = ${i}")
        params.append(action)
        i += 1
    if from_date:
        conditions.append(f"created_at >= ${i}")
        params.append(from_date)
        i += 1
    if to_date:
        conditions.append(f"created_at <= ${i}")
        params.append(to_date)
        i += 1

    where = " AND ".join(conditions)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval(f"SELECT COUNT(*) FROM admin_audit_logs WHERE {where}", *params)
        rows = await conn.fetch(
            f"SELECT id, actor, action, target, detail, ip, created_at "
            f"FROM admin_audit_logs WHERE {where} "
            f"ORDER BY created_at DESC LIMIT ${i} OFFSET ${i+1}",
            *params, limit, offset,
        )
    return {
        "total": total,
        "offset": offset,
        "entries": [dict(r) for r in rows],
    }


@router.get("/monitor/activity", dependencies=[Depends(require_roles("admin"))])
async def activity_feed(
    limit: int = Query(default=100, ge=1, le=500),
    since: Optional[str] = None,
):
    pool = await get_db_pool()
    since_ts = since or "1970-01-01T00:00:00+00:00"

    async with pool.acquire() as conn:
        audit_rows = await conn.fetch(
            "SELECT actor, action, target, detail, created_at "
            "FROM admin_audit_logs WHERE created_at > $1 ORDER BY created_at DESC LIMIT $2",
            since_ts, limit,
        )
        conv_rows = await conn.fetch(
            "SELECT session_id, customer_id, channel, source, confidence, created_at "
            "FROM conversation_logs WHERE created_at > $1 ORDER BY created_at DESC LIMIT $2",
            since_ts, limit,
        )
        outcome_rows = await conn.fetch(
            "SELECT session_id, status, handoff_reason, resolved_by, created_at "
            "FROM session_outcomes WHERE created_at > $1 ORDER BY created_at DESC LIMIT $2",
            since_ts, limit,
        )
        llm_rows = await conn.fetch(
            "SELECT operation, total_tokens, estimated_cost, created_at "
            "FROM llm_usage_logs WHERE created_at > $1 ORDER BY created_at DESC LIMIT $2",
            since_ts, limit,
        )

    events = []

    for r in audit_rows:
        events.append({
            "type": "admin_action",
            "actor": r["actor"],
            "description": f"{r['action']} → {r['target'] or ''} {r['detail'] or ''}".strip(),
            "channel": None,
            "session_id": None,
            "created_at": r["created_at"].isoformat(),
        })

    for r in conv_rows:
        events.append({
            "type": "message",
            "actor": r["customer_id"],
            "description": f"Message via {r['source'] or 'unknown'} (confidence {round((r['confidence'] or 0) * 100)}%)",
            "channel": r["channel"],
            "session_id": r["session_id"],
            "created_at": r["created_at"].isoformat(),
        })

    for r in outcome_rows:
        escalated = bool(r["handoff_reason"])
        events.append({
            "type": "escalation" if escalated else "resolved",
            "actor": r["resolved_by"] or "",
            "description": f"Session {r['status']}" + (f" — {r['handoff_reason']}" if escalated else ""),
            "channel": None,
            "session_id": r["session_id"],
            "created_at": r["created_at"].isoformat(),
        })

    for r in llm_rows:
        events.append({
            "type": "llm_call",
            "actor": "llm",
            "description": f"{r['operation']} — {r['total_tokens']} tokens (${round(float(r['estimated_cost'] or 0), 5)})",
            "channel": None,
            "session_id": None,
            "created_at": r["created_at"].isoformat(),
        })

    events.sort(key=lambda e: e["created_at"], reverse=True)
    return {"events": events[:limit]}
