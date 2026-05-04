from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from core.auth import get_admin_identity, require_roles, verify_api_key
from core.session_manager import get_session
from db.postgres import get_db_pool

router = APIRouter()

CASE_STATUSES = {"open", "pending", "in_progress", "waiting_customer", "escalated", "resolved", "closed"}
CASE_PRIORITIES = {"low", "normal", "high", "urgent"}
SLA_HOURS = {"low": 72, "normal": 24, "high": 8, "urgent": 2}
FIRST_RESPONSE_HOURS = {"low": 24, "normal": 8, "high": 2, "urgent": 0.5}


class CaseCreateBody(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(default="", max_length=5000)
    session_id: Optional[str] = Field(default=None, max_length=128)
    customer_id: Optional[str] = Field(default=None, max_length=128)
    channel: str = Field(default="web", max_length=32)
    department: str = Field(default="general", max_length=64)
    priority: str = Field(default="normal", max_length=32)
    owner: Optional[str] = Field(default=None, max_length=128)
    tags: list[str] = Field(default_factory=list, max_length=12)
    internal_notes: str = Field(default="", max_length=5000)


class CaseUpdateBody(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    department: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default=None, max_length=32)
    priority: Optional[str] = Field(default=None, max_length=32)
    owner: Optional[str] = Field(default=None, max_length=128)
    tags: Optional[list[str]] = Field(default=None, max_length=12)
    internal_notes: Optional[str] = Field(default=None, max_length=5000)


class CaseFromSessionBody(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    department: str = Field(default="general", max_length=64)
    priority: str = Field(default="normal", max_length=32)
    owner: Optional[str] = Field(default=None, max_length=128)
    internal_notes: str = Field(default="", max_length=5000)


class CaseNoteBody(BaseModel):
    note: str = Field(..., min_length=1, max_length=5000)


def _actor(request: Request) -> str:
    identity = get_admin_identity(request) or {}
    return identity.get("sub", "api_key")


def _ip(request: Request) -> str:
    return request.client.host if request.client else ""


def _validate_status(status: str) -> None:
    if status not in CASE_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid case status")


def _validate_priority(priority: str) -> None:
    if priority not in CASE_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid case priority")


async def _validate_department(conn, department: str) -> None:
    exists = await conn.fetchval(
        "SELECT 1 FROM support_departments WHERE code = $1 AND is_active = TRUE",
        department,
    )
    if not exists:
        raise HTTPException(status_code=400, detail="Invalid department")


async def _audit(conn, request: Request, action: str, target: str, detail: str = "") -> None:
    await conn.execute(
        "INSERT INTO admin_audit_logs (actor, action, target, detail, ip) VALUES ($1,$2,$3,$4,$5)",
        _actor(request), action, target, detail, _ip(request),
    )


def _sla_due(priority: str) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    return (
        now + timedelta(hours=FIRST_RESPONSE_HOURS.get(priority, 8)),
        now + timedelta(hours=SLA_HOURS.get(priority, 24)),
    )


def _row_to_case(row) -> dict:
    data = dict(row)
    for key in (
        "created_at", "updated_at", "sla_due_at", "first_response_due_at",
        "sla_warned_at", "sla_breached_at", "resolved_at",
    ):
        if data.get(key):
            data[key] = data[key].isoformat()
    return data


def _row_to_activity(row) -> dict:
    data = dict(row)
    if data.get("created_at"):
        data["created_at"] = data["created_at"].isoformat()
    return data


async def _next_case_number(conn) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    seq = await conn.fetchval("SELECT nextval('support_case_number_seq')")
    return f"NURA-{today}-{int(seq):05d}"


async def _log_case_activity(
    conn,
    case_id: int,
    actor: str,
    action: str,
    field_name: str = "",
    old_value: str = "",
    new_value: str = "",
    note: str = "",
) -> None:
    await conn.execute(
        """
        INSERT INTO support_case_activity (case_id, actor, action, field_name, old_value, new_value, note)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        """,
        case_id, actor, action, field_name or None, old_value or None, new_value or None, note or None,
    )


def _case_text_from_session(session) -> tuple[str, str]:
    customer_turns = [t for t in session.history if t.role == "customer" and t.message]
    latest_customer = customer_turns[-1].message if customer_turns else ""
    title = latest_customer[:120] if latest_customer else f"Case from session {session.session_id[:8]}"
    description = "\n".join(
        f"{t.role}: {t.message}" for t in session.history[-12:] if getattr(t, "message", "")
    )
    return title, description


async def ensure_case_for_session(
    session,
    reason: str = "handoff",
    priority: str = "normal",
    department: str = "general",
    owner: str | None = None,
    actor: str = "system",
) -> dict | None:
    """Create one active support case for a session if no open case exists."""
    _validate_priority(priority)
    title, description = _case_text_from_session(session)
    first_response_due_at, sla_due_at = _sla_due(priority)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await _validate_department(conn, department)
        existing = await conn.fetchrow(
            "SELECT * FROM support_cases WHERE session_id = $1 AND status NOT IN ('resolved','closed') ORDER BY created_at DESC LIMIT 1",
            session.session_id,
        )
        if existing:
            await _log_case_activity(
                conn, existing["id"], actor, "handoff_linked", note=f"Handoff reason: {reason}"
            )
            return _row_to_case(existing)

        case_number = await _next_case_number(conn)
        row = await conn.fetchrow(
            """
            INSERT INTO support_cases (
                case_number, session_id, customer_id, channel, title, description,
                department, priority, owner, tags, internal_notes, source,
                first_response_due_at, sla_due_at, sla_status, created_by, updated_by
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,'handoff',$12,$13,'ok',$14,$14)
            RETURNING *
            """,
            case_number, session.session_id, session.customer_id, session.channel, title,
            description, department, priority, owner, [reason], f"Auto-created from handoff: {reason}",
            first_response_due_at, sla_due_at, actor,
        )
        await _log_case_activity(
            conn, row["id"], actor, "created", note=f"Auto-created from handoff: {reason}"
        )
        return _row_to_case(row)


@router.get("/departments", dependencies=[Depends(verify_api_key)])
async def list_departments():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT code, name, description FROM support_departments WHERE is_active = TRUE ORDER BY name"
        )
    return {"departments": [dict(r) for r in rows]}


@router.get("/cases", dependencies=[Depends(verify_api_key)])
async def list_cases(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    department: Optional[str] = None,
    owner: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    conditions = ["1=1"]
    params: list = []

    def add(condition: str, value):
        params.append(value)
        conditions.append(condition.format(len(params)))

    if status and status != "all":
        _validate_status(status)
        add("status = ${}", status)
    if priority and priority != "all":
        _validate_priority(priority)
        add("priority = ${}", priority)
    if department and department != "all":
        add("department = ${}", department)
    if owner:
        add("owner = ${}", owner)
    if q:
        params.append(f"%{q}%")
        idx = len(params)
        conditions.append(
            f"(case_number ILIKE ${idx} OR title ILIKE ${idx} OR description ILIKE ${idx} "
            f"OR customer_id ILIKE ${idx} OR session_id ILIKE ${idx})"
        )

    where = " AND ".join(conditions)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval(f"SELECT COUNT(*) FROM support_cases WHERE {where}", *params)
        rows = await conn.fetch(
            f"""
            SELECT *
            FROM support_cases
            WHERE {where}
            ORDER BY
                CASE WHEN status IN ('resolved','closed') THEN 1 ELSE 0 END,
                CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,
                COALESCE(sla_due_at, created_at) ASC,
                updated_at DESC
            LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
            """,
            *params, limit, offset,
        )
        stats_rows = await conn.fetch("SELECT status, COUNT(*) AS count FROM support_cases GROUP BY status")
        overdue = await conn.fetchval(
            "SELECT COUNT(*) FROM support_cases WHERE status NOT IN ('resolved','closed') AND sla_due_at < NOW()"
        )
        at_risk = await conn.fetchval(
            "SELECT COUNT(*) FROM support_cases WHERE status NOT IN ('resolved','closed') AND sla_status = 'at_risk'"
        )
        breached = await conn.fetchval(
            "SELECT COUNT(*) FROM support_cases WHERE status NOT IN ('resolved','closed') AND sla_status = 'breached'"
        )
    return {
        "total": total,
        "offset": offset,
        "cases": [_row_to_case(r) for r in rows],
        "stats": {r["status"]: r["count"] for r in stats_rows},
        "overdue": overdue or 0,
        "at_risk": at_risk or 0,
        "breached": breached or 0,
    }


@router.post("/cases", dependencies=[Depends(require_roles("admin", "agent"))])
async def create_case(body: CaseCreateBody, request: Request):
    _validate_priority(body.priority)
    tags = [t.strip()[:48] for t in body.tags if t.strip()][:12]
    first_response_due_at, sla_due_at = _sla_due(body.priority)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await _validate_department(conn, body.department)
        case_number = await _next_case_number(conn)
        row = await conn.fetchrow(
            """
            INSERT INTO support_cases (
                case_number, session_id, customer_id, channel, title, description,
                department, priority, owner, tags, internal_notes, source,
                first_response_due_at, sla_due_at, sla_status, created_by, updated_by
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,'manual',$12,$13,'ok',$14,$14)
            RETURNING *
            """,
            case_number, body.session_id, body.customer_id, body.channel, body.title,
            body.description, body.department, body.priority, body.owner, tags,
            body.internal_notes, first_response_due_at, sla_due_at, _actor(request),
        )
        await _log_case_activity(conn, row["id"], _actor(request), "created", note="Manual case created")
        if body.internal_notes:
            await _log_case_activity(conn, row["id"], _actor(request), "note_added", note=body.internal_notes)
        await _audit(conn, request, "case_created", case_number, body.priority)
    return _row_to_case(row)


@router.post("/cases/from-session/{session_id}", dependencies=[Depends(require_roles("admin", "agent"))])
async def create_case_from_session(session_id: str, body: CaseFromSessionBody, request: Request):
    _validate_priority(body.priority)
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    generated_title, description = _case_text_from_session(session)
    title = body.title or generated_title
    first_response_due_at, sla_due_at = _sla_due(body.priority)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await _validate_department(conn, body.department)
        existing = await conn.fetchrow(
            "SELECT * FROM support_cases WHERE session_id = $1 AND status NOT IN ('resolved','closed') ORDER BY created_at DESC LIMIT 1",
            session_id,
        )
        if existing:
            await _log_case_activity(conn, existing["id"], _actor(request), "session_case_reused", note=session_id)
            return _row_to_case(existing)
        case_number = await _next_case_number(conn)
        row = await conn.fetchrow(
            """
            INSERT INTO support_cases (
                case_number, session_id, customer_id, channel, title, description,
                department, priority, owner, tags, internal_notes, source,
                first_response_due_at, sla_due_at, sla_status, created_by, updated_by
            )
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,'session',$12,$13,'ok',$14,$14)
            RETURNING *
            """,
            case_number, session.session_id, session.customer_id, session.channel, title,
            description, body.department, body.priority, body.owner,
            [session.status.value], body.internal_notes, first_response_due_at, sla_due_at,
            _actor(request),
        )
        await _log_case_activity(conn, row["id"], _actor(request), "created", note=f"Created from session {session_id}")
        if body.internal_notes:
            await _log_case_activity(conn, row["id"], _actor(request), "note_added", note=body.internal_notes)
        await _audit(conn, request, "case_created_from_session", case_number, session_id)
    return _row_to_case(row)


@router.get("/cases/stats", dependencies=[Depends(verify_api_key)])
async def case_stats():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        status_rows = await conn.fetch("SELECT status, COUNT(*) AS count FROM support_cases GROUP BY status")
        dept_rows = await conn.fetch("SELECT department, COUNT(*) AS count FROM support_cases GROUP BY department ORDER BY count DESC")
        priority_rows = await conn.fetch("SELECT priority, COUNT(*) AS count FROM support_cases GROUP BY priority")
        overdue = await conn.fetchval(
            "SELECT COUNT(*) FROM support_cases WHERE status NOT IN ('resolved','closed') AND sla_due_at < NOW()"
        )
        at_risk = await conn.fetchval(
            "SELECT COUNT(*) FROM support_cases WHERE status NOT IN ('resolved','closed') AND sla_status = 'at_risk'"
        )
        breached = await conn.fetchval(
            "SELECT COUNT(*) FROM support_cases WHERE status NOT IN ('resolved','closed') AND sla_status = 'breached'"
        )
        avg_resolution = await conn.fetchval(
            """
            SELECT ROUND(AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)))::numeric, 1)
            FROM support_cases
            WHERE resolved_at IS NOT NULL
            """
        )
    return {
        "by_status": {r["status"]: r["count"] for r in status_rows},
        "by_department": [dict(r) for r in dept_rows],
        "by_priority": {r["priority"]: r["count"] for r in priority_rows},
        "overdue": overdue or 0,
        "at_risk": at_risk or 0,
        "breached": breached or 0,
        "avg_resolution_seconds": float(avg_resolution or 0),
    }


@router.get("/cases/{case_id}/activity", dependencies=[Depends(verify_api_key)])
async def case_activity(case_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT 1 FROM support_cases WHERE id = $1", case_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Case not found")
        rows = await conn.fetch(
            """
            SELECT id, case_id, actor, action, field_name, old_value, new_value, note, created_at
            FROM support_case_activity
            WHERE case_id = $1
            ORDER BY created_at DESC, id DESC
            """,
            case_id,
        )
    return {"activity": [_row_to_activity(r) for r in rows]}


@router.post("/cases/{case_id}/notes", dependencies=[Depends(require_roles("admin", "agent"))])
async def add_case_note(case_id: int, body: CaseNoteBody, request: Request):
    actor = _actor(request)
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE support_cases
            SET internal_notes = CASE
                    WHEN internal_notes = '' THEN $1
                    ELSE internal_notes || E'\n\n' || $1
                END,
                updated_by = $2,
                updated_at = NOW()
            WHERE id = $3
            RETURNING *
            """,
            body.note, actor, case_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Case not found")
        await _log_case_activity(conn, case_id, actor, "note_added", note=body.note)
        await _audit(conn, request, "case_note_added", row["case_number"], "")
    return _row_to_case(row)


@router.patch("/cases/{case_id}", dependencies=[Depends(require_roles("admin", "agent"))])
async def update_case(case_id: int, body: CaseUpdateBody, request: Request):
    updates = []
    params: list = []

    def set_field(name: str, value):
        params.append(value)
        updates.append(f"{name} = ${len(params)}")

    if body.title is not None:
        set_field("title", body.title)
    if body.description is not None:
        set_field("description", body.description)
    if body.department is not None:
        set_field("department", body.department)
    if body.status is not None:
        _validate_status(body.status)
        set_field("status", body.status)
        if body.status in ("resolved", "closed"):
            set_field("resolved_at", datetime.now(timezone.utc))
    if body.priority is not None:
        _validate_priority(body.priority)
        first_response_due_at, sla_due_at = _sla_due(body.priority)
        set_field("priority", body.priority)
        set_field("first_response_due_at", first_response_due_at)
        set_field("sla_due_at", sla_due_at)
        set_field("sla_status", "ok")
        set_field("sla_warned_at", None)
        set_field("sla_breached_at", None)
    if body.owner is not None:
        set_field("owner", body.owner or None)
    if body.tags is not None:
        set_field("tags", [t.strip()[:48] for t in body.tags if t.strip()][:12])
    if body.internal_notes is not None:
        set_field("internal_notes", body.internal_notes)

    if not updates:
        raise HTTPException(status_code=400, detail="No changes supplied")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if body.department is not None:
            await _validate_department(conn, body.department)
        before = await conn.fetchrow("SELECT * FROM support_cases WHERE id = $1", case_id)
        if not before:
            raise HTTPException(status_code=404, detail="Case not found")
        set_field("updated_by", _actor(request))
        updates.append("updated_at = NOW()")
        params.append(case_id)
        row = await conn.fetchrow(
            f"UPDATE support_cases SET {', '.join(updates)} WHERE id = ${len(params)} RETURNING *",
            *params,
        )
        actor = _actor(request)
        tracked_fields = ("title", "description", "department", "status", "priority", "owner", "internal_notes")
        for field in tracked_fields:
            old = before[field]
            new = row[field]
            if old != new:
                await _log_case_activity(
                    conn, row["id"], actor, "field_changed", field, str(old or ""), str(new or "")
                )
        if body.tags is not None and list(before["tags"] or []) != list(row["tags"] or []):
            await _log_case_activity(
                conn, row["id"], actor, "field_changed", "tags",
                ", ".join(before["tags"] or []), ", ".join(row["tags"] or [])
            )
        await _audit(conn, request, "case_updated", row["case_number"], body.status or body.priority or "")
    return _row_to_case(row)
