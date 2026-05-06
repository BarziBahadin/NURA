from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from core.auth import get_admin_identity, require_roles, verify_api_key
from db.postgres import get_db_pool

router = APIRouter()


class CannedReplyBody(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=4000)
    category: str = Field(default="", max_length=100)
    language: str = Field(default="ar", max_length=10)
    sort_order: int = Field(default=0)


@router.get("/canned-replies", dependencies=[Depends(verify_api_key)])
async def list_canned_replies():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, title, body, category, language, sort_order, created_by, updated_by, created_at, updated_at
            FROM canned_replies
            ORDER BY sort_order ASC, created_at ASC
            """
        )
    return {"replies": [dict(r) for r in rows]}


@router.post("/canned-replies", dependencies=[Depends(require_roles("admin"))])
async def create_canned_reply(body: CannedReplyBody, request: Request):
    actor = ((await get_admin_identity(request)) or {}).get("sub", "admin")
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO canned_replies (title, body, category, language, sort_order, created_by, updated_by)
            VALUES ($1, $2, $3, $4, $5, $6, $6)
            RETURNING id, title, body, category, language, sort_order, created_by, updated_by, created_at, updated_at
            """,
            body.title, body.body, body.category, body.language, body.sort_order, actor,
        )
    return dict(row)


@router.put("/canned-replies/{reply_id}", dependencies=[Depends(require_roles("admin"))])
async def update_canned_reply(reply_id: int, body: CannedReplyBody, request: Request):
    actor = ((await get_admin_identity(request)) or {}).get("sub", "admin")
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE canned_replies
            SET title=$2, body=$3, category=$4, language=$5, sort_order=$6,
                updated_by=$7, updated_at=NOW()
            WHERE id=$1
            RETURNING id, title, body, category, language, sort_order, created_by, updated_by, created_at, updated_at
            """,
            reply_id, body.title, body.body, body.category, body.language, body.sort_order, actor,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Canned reply not found")
    return dict(row)


@router.delete("/canned-replies/{reply_id}", dependencies=[Depends(require_roles("admin"))])
async def delete_canned_reply(reply_id: int):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM canned_replies WHERE id=$1", reply_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Canned reply not found")
    return {"ok": True}
