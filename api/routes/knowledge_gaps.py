from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from core.auth import get_admin_identity, require_roles
from core.orchestrator import invalidate_gap_cache
from db.postgres import get_db_pool

router = APIRouter()

VALID_STATUSES = {"pending", "drafted", "approved", "rejected", "resolved"}


class ReviewUpdateBody(BaseModel):
    proposed_answer: Optional[str] = Field(default=None, max_length=6000)
    approved_answer: Optional[str] = Field(default=None, max_length=6000)
    notes: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[str] = None


class ReviewActionBody(BaseModel):
    answer: Optional[str] = Field(default=None, max_length=6000)
    notes: Optional[str] = Field(default=None, max_length=2000)


async def _audit(conn, request: Request, action: str, target: str, detail: str = "") -> None:
    actor = ((await get_admin_identity(request)) or {}).get("sub", "unknown")
    ip = request.client.host if request.client else ""
    await conn.execute(
        "INSERT INTO admin_audit_logs (actor, action, target, detail, ip) VALUES ($1,$2,$3,$4,$5)",
        actor, action, target, detail, ip,
    )


async def _sync_new_gaps(conn) -> int:
    result = await conn.execute(
        """
        INSERT INTO knowledge_gap_reviews (
            insight_id, session_id, customer_id, channel, customer_message,
            intent, sub_intent, gap_reason, created_at, updated_at
        )
        SELECT
            mi.id, mi.session_id, mi.customer_id, mi.channel, mi.message_text,
            mi.intent, mi.sub_intent, mi.gap_reason, mi.created_at, NOW()
        FROM message_insights mi
        LEFT JOIN knowledge_gap_reviews kgr ON kgr.insight_id = mi.id
        WHERE mi.is_knowledge_gap = TRUE
          AND kgr.id IS NULL
        """
    )
    return int(result.split()[-1])


def _row_to_review(row) -> dict:
    return {
        "id": row["id"],
        "insight_id": row["insight_id"],
        "session_id": row["session_id"],
        "customer_id": row["customer_id"],
        "channel": row["channel"],
        "customer_message": row["customer_message"],
        "intent": row["intent"],
        "sub_intent": row["sub_intent"],
        "gap_reason": row["gap_reason"],
        "status": row["status"],
        "proposed_answer": row["proposed_answer"],
        "approved_answer": row["approved_answer"],
        "notes": row["notes"],
        "reviewed_by": row["reviewed_by"],
        "reviewed_at": row["reviewed_at"].isoformat() if row["reviewed_at"] else None,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


@router.get("/knowledge-gaps", dependencies=[Depends(require_roles("admin"))])
async def list_gap_reviews(
    status: str = Query(default="pending"),
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    if status != "all" and status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        synced = await _sync_new_gaps(conn)

        where = []
        params = []
        if status != "all":
            params.append(status)
            where.append(f"status = ${len(params)}")
        if q:
            params.append(f"%{q}%")
            where.append(
                f"(customer_message ILIKE ${len(params)} OR intent ILIKE ${len(params)} OR gap_reason ILIKE ${len(params)})"
            )
        where_sql = " AND ".join(where) if where else "TRUE"
        params.extend([limit, offset])
        limit_pos = len(params) - 1
        offset_pos = len(params)

        total = await conn.fetchval(f"SELECT COUNT(*) FROM knowledge_gap_reviews WHERE {where_sql}", *params[:-2])
        rows = await conn.fetch(
            f"""
            SELECT *
            FROM knowledge_gap_reviews
            WHERE {where_sql}
            ORDER BY
              CASE status
                WHEN 'pending' THEN 0
                WHEN 'drafted' THEN 1
                WHEN 'approved' THEN 2
                WHEN 'resolved' THEN 3
                ELSE 4
              END,
              created_at DESC
            LIMIT ${limit_pos} OFFSET ${offset_pos}
            """,
            *params,
        )

        counts_rows = await conn.fetch(
            "SELECT status, COUNT(*) AS count FROM knowledge_gap_reviews GROUP BY status"
        )

    counts = {s: 0 for s in VALID_STATUSES}
    counts.update({r["status"]: r["count"] for r in counts_rows})
    return {
        "reviews": [_row_to_review(r) for r in rows],
        "total": total or 0,
        "counts": counts,
        "synced": synced,
    }


@router.patch("/knowledge-gaps/{review_id}", dependencies=[Depends(require_roles("admin"))])
async def update_gap_review(review_id: int, body: ReviewUpdateBody, request: Request):
    if body.status is not None and body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")

    actor = ((await get_admin_identity(request)) or {}).get("sub", "unknown")
    updates = []
    params = []
    for field in ("proposed_answer", "approved_answer", "notes", "status"):
        value = getattr(body, field)
        if value is not None:
            params.append(value)
            updates.append(f"{field} = ${len(params)}")
    if not updates:
        raise HTTPException(status_code=400, detail="No changes provided")

    params.append(actor)
    updates.append(f"reviewed_by = ${len(params)}")
    updates.append("reviewed_at = NOW()")
    updates.append("updated_at = NOW()")
    params.append(review_id)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE knowledge_gap_reviews SET {', '.join(updates)} WHERE id = ${len(params)} RETURNING *",
            *params,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Review not found")
        await _audit(conn, request, "knowledge_gap_updated", str(review_id), body.status or "")
    return {"review": _row_to_review(row)}


@router.post("/knowledge-gaps/{review_id}/approve", dependencies=[Depends(require_roles("admin"))])
async def approve_gap_review(review_id: int, body: ReviewActionBody, request: Request):
    actor = ((await get_admin_identity(request)) or {}).get("sub", "unknown")
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        current = await conn.fetchrow("SELECT * FROM knowledge_gap_reviews WHERE id = $1", review_id)
        if not current:
            raise HTTPException(status_code=404, detail="Review not found")
        answer = (body.answer or current["proposed_answer"] or current["approved_answer"] or "").strip()
        if not answer:
            raise HTTPException(status_code=400, detail="Approved answer is required")

        row = await conn.fetchrow(
            """
            UPDATE knowledge_gap_reviews
            SET status = 'approved',
                approved_answer = $1,
                notes = COALESCE($2, notes),
                reviewed_by = $3,
                reviewed_at = NOW(),
                updated_at = NOW()
            WHERE id = $4
            RETURNING *
            """,
            answer, body.notes, actor, review_id,
        )
        await _audit(conn, request, "knowledge_gap_approved", str(review_id), current["intent"] or "")
    invalidate_gap_cache()
    return {"review": _row_to_review(row)}


@router.post("/knowledge-gaps/{review_id}/resolve", dependencies=[Depends(require_roles("admin"))])
async def resolve_gap_review(review_id: int, body: ReviewActionBody, request: Request):
    actor = ((await get_admin_identity(request)) or {}).get("sub", "unknown")
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE knowledge_gap_reviews
            SET status = 'resolved',
                notes = COALESCE($1, notes),
                reviewed_by = $2,
                reviewed_at = NOW(),
                updated_at = NOW()
            WHERE id = $3
            RETURNING *
            """,
            body.notes, actor, review_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Review not found")
        await _audit(conn, request, "knowledge_gap_resolved", str(review_id), row["intent"] or "")
    invalidate_gap_cache()
    return {"review": _row_to_review(row)}


@router.post("/knowledge-gaps/{review_id}/reject", dependencies=[Depends(require_roles("admin"))])
async def reject_gap_review(review_id: int, body: ReviewActionBody, request: Request):
    actor = ((await get_admin_identity(request)) or {}).get("sub", "unknown")
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE knowledge_gap_reviews
            SET status = 'rejected',
                notes = COALESCE($1, notes),
                reviewed_by = $2,
                reviewed_at = NOW(),
                updated_at = NOW()
            WHERE id = $3
            RETURNING *
            """,
            body.notes, actor, review_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Review not found")
        await _audit(conn, request, "knowledge_gap_rejected", str(review_id), row["intent"] or "")
    return {"review": _row_to_review(row)}
