import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from config import settings
from core.auth import get_admin_identity, has_admin_access, require_roles, verify_api_key, verify_session_access
from core.session_manager import (
    get_customer_token,
    get_or_create_session,
    get_session,
    publish_session_event,
    save_session,
)
from db.postgres import get_db_pool

router = APIRouter()


class VoiceRequestBody(BaseModel):
    session_id: Optional[str] = None
    customer_id: str = Field(default="anonymous", max_length=128)
    channel: str = Field(default="web", max_length=32)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _livekit_token(room_name: str, identity: str, name: str, role: str) -> str:
    now = int(time.time())
    payload = {
        "iss": settings.livekit_api_key,
        "sub": identity,
        "name": name,
        "nbf": now - 10,
        "exp": now + settings.livekit_token_ttl_seconds,
        "video": {
            "room": room_name,
            "roomJoin": True,
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": True,
            "canPublishSources": ["microphone"],
            "roomAdmin": role == "agent",
        },
        "metadata": json.dumps({"role": role}, separators=(",", ":")),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join([
        _b64(json.dumps(header, separators=(",", ":")).encode()),
        _b64(json.dumps(payload, separators=(",", ":")).encode()),
    ])
    sig = hmac.new(settings.livekit_api_secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(sig)}"


def _safe_room_name(call_id: str) -> str:
    seed = re.sub(r"[^A-Za-z0-9-]", "", call_id)
    return f"nura-voice-{seed}"


def _row_to_call(row) -> dict:
    data = dict(row)
    data.pop("join_url", None)
    data["provider"] = "livekit"
    for key in ("requested_at", "accepted_at", "ended_at"):
        if data.get(key):
            data[key] = data[key].isoformat()
    return data


def _livekit_server_url(request: Request) -> str:
    configured = (settings.livekit_url or "").strip()
    if configured and configured.lower() not in {"auto", "dynamic", "request"}:
        if "://" not in configured:
            configured = f"ws://{configured}"
        if configured.startswith("http://"):
            return "ws://" + configured[len("http://"):]
        if configured.startswith("https://"):
            return "wss://" + configured[len("https://"):]
        return configured

    # In auto mode, return a browser-facing URL based on how this API was
    # reached. This avoids stale LAN IPs when a laptop moves networks.
    forwarded_proto = request.headers.get("X-Forwarded-Proto", request.url.scheme)
    ws_scheme = "wss" if forwarded_proto.split(",")[0].strip() == "https" else "ws"

    host = (request.headers.get("X-Forwarded-Host") or request.headers.get("Host") or "localhost").split(",")[0].strip()
    if host.startswith("[") and "]" in host:
        hostname = host[: host.index("]") + 1]
    else:
        hostname = host.rsplit(":", 1)[0]

    if hostname in {"localhost", "127.0.0.1", "::1"} and settings.livekit_node_ip:
        hostname = settings.livekit_node_ip

    livekit_port = 7443 if ws_scheme == "wss" else 7880
    return f"{ws_scheme}://{hostname}:{livekit_port}"


def _with_token(call: dict, role: str, identity: str, name: str, server_url: str) -> dict:
    return {
        **call,
        "server_url": server_url,
        "livekit_token": _livekit_token(call["room_name"], identity, name, role),
    }


@router.post("/voice/request")
async def request_voice_call(body: VoiceRequestBody, request: Request):
    if not settings.voice_call_enabled:
        raise HTTPException(status_code=503, detail="Voice calls are disabled")

    session = await get_or_create_session(body.session_id, body.customer_id, body.channel)
    if body.session_id and session.session_id == body.session_id:
        await verify_session_access(request, session)

    session_token = get_customer_token(session)
    await save_session(session)

    pool = await get_db_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            """
            SELECT * FROM voice_calls
            WHERE session_id = $1 AND status IN ('requested','accepted','active')
            ORDER BY requested_at DESC
            LIMIT 1
            """,
            session.session_id,
        )
        if existing:
            call = _row_to_call(existing)
        else:
            call_id = secrets.token_urlsafe(12)
            room_name = _safe_room_name(call_id)
            row = await conn.fetchrow(
                """
                INSERT INTO voice_calls
                  (call_id, session_id, customer_id, channel, room_name, status)
                VALUES ($1,$2,$3,$4,$5,'requested')
                RETURNING *
                """,
                call_id,
                session.session_id,
                session.customer_id,
                session.channel,
                room_name,
            )
            call = _row_to_call(row)
            await publish_session_event(session.session_id, {
                "type": "voice_call_requested",
                "call": call,
            })

    return {
        **_with_token(call, "customer", f"customer-{session.session_id}", "Customer", _livekit_server_url(request)),
        "session_token": session_token,
    }


@router.get("/voice/calls", dependencies=[Depends(verify_api_key)])
async def list_voice_calls(request: Request, status: str = "requested,accepted,active", limit: int = 50):
    statuses = [s.strip() for s in status.split(",") if s.strip()]
    if not statuses:
        statuses = ["requested", "accepted", "active"]
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM voice_calls
            WHERE status = ANY($1::text[])
            ORDER BY requested_at DESC
            LIMIT $2
            """,
            statuses,
            max(1, min(limit, 200)),
        )
    return {"calls": [_row_to_call(r) for r in rows], "server_url": _livekit_server_url(request)}


@router.post("/voice/clear-failed", dependencies=[Depends(require_roles("admin", "agent"))])
async def clear_failed_voice_calls():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            UPDATE voice_calls
            SET status = 'cancelled', ended_at = COALESCE(ended_at, $1)
            WHERE status IN ('requested','accepted','active')
            RETURNING *
            """,
            datetime.now(timezone.utc),
        )
    calls = [_row_to_call(r) for r in rows]
    for call in calls:
        await publish_session_event(call["session_id"], {
            "type": "voice_call_ended",
            "call": call,
        })
    return {"ok": True, "cleared": len(calls), "calls": calls}


@router.post("/voice/{call_id}/cancel", dependencies=[Depends(require_roles("admin", "agent"))])
async def cancel_voice_call(call_id: str):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE voice_calls
            SET status = 'cancelled', ended_at = COALESCE(ended_at, $2)
            WHERE call_id = $1 AND status IN ('requested','accepted','active')
            RETURNING *
            """,
            call_id,
            datetime.now(timezone.utc),
        )
    if not row:
        raise HTTPException(status_code=404, detail="Voice call not found")
    call = _row_to_call(row)
    await publish_session_event(row["session_id"], {
        "type": "voice_call_ended",
        "call": call,
    })
    return call


@router.post("/voice/{call_id}/accept", dependencies=[Depends(require_roles("admin", "agent"))])
async def accept_voice_call(call_id: str, request: Request):
    identity = await get_admin_identity(request) or {}
    accepted_by = identity.get("sub") or "agent"
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE voice_calls
            SET status = 'accepted', accepted_at = COALESCE(accepted_at, $2), accepted_by = COALESCE(accepted_by, $3)
            WHERE call_id = $1 AND status IN ('requested','accepted','active')
            RETURNING *
            """,
            call_id,
            datetime.now(timezone.utc),
            accepted_by,
        )
    if not row:
        raise HTTPException(status_code=404, detail="Voice call not found")
    call = _row_to_call(row)
    call_with_token = _with_token(call, "agent", f"agent-{accepted_by}", accepted_by, _livekit_server_url(request))
    await publish_session_event(row["session_id"], {
        "type": "voice_call_accepted",
        "call": call,
    })
    return call_with_token


@router.post("/voice/{call_id}/end")
async def end_voice_call(call_id: str, request: Request):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT * FROM voice_calls WHERE call_id = $1",
            call_id,
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Voice call not found")

        if not await has_admin_access(request):
            session = await get_session(existing["session_id"])
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            await verify_session_access(request, session)

        row = await conn.fetchrow(
            """
            UPDATE voice_calls
            SET status = 'ended', ended_at = COALESCE(ended_at, $2)
            WHERE call_id = $1
            RETURNING *
            """,
            call_id,
            datetime.now(timezone.utc),
        )
    call = _row_to_call(row)
    await publish_session_event(row["session_id"], {
        "type": "voice_call_ended",
        "call": call,
    })
    return call
