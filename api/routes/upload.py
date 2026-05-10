import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings
from core.auth import has_admin_access, verify_session_access
from core.observability import record_event, record_failure
from core.session_manager import get_session

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

UPLOAD_DIR = "/app/uploads"
MAX_SIZE = 5 * 1024 * 1024  # 5 MB
FILE_TOKEN_TTL_SECONDS = 15 * 60
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf"}


def _detect_mime(data: bytes) -> str | None:
    if data[:3] == b'\xff\xd8\xff':
        return "image/jpeg"
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return "image/png"
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return "image/gif"
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return "image/webp"
    if data[:4] == b'%PDF':
        return "application/pdf"
    return None


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def _upload_hmac_key() -> bytes:
    return hashlib.sha256(b"nura:upload-token:" + settings.admin_secret_key.encode()).digest()


def _sign_file_token(session_id: str, filename: str) -> str:
    payload = {
        "sid": session_id,
        "fn": filename,
        "exp": int(time.time()) + FILE_TOKEN_TTL_SECONDS,
    }
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(_upload_hmac_key(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(sig)}"


def _verify_file_token(token: str, session_id: str, filename: str) -> bool:
    if not token or "." not in token:
        return False
    body, sig = token.rsplit(".", 1)
    expected = _b64(hmac.new(_upload_hmac_key(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        return False
    try:
        payload = json.loads(_unb64(body))
    except Exception:
        return False
    if int(payload.get("exp", 0)) < int(time.time()):
        return False
    return payload.get("sid") == session_id and payload.get("fn") == filename


def _safe_segment(value: str, field: str) -> str:
    clean = os.path.basename(value or "")
    if not clean or clean != value:
        raise HTTPException(status_code=400, detail=f"Invalid {field}")
    return clean


def _upload_path(session_id: str, filename: str) -> tuple[str, str]:
    safe_session = _safe_segment(session_id, "session_id")
    safe_filename = _safe_segment(filename, "filename")
    root = os.path.abspath(os.path.join(UPLOAD_DIR, safe_session))
    path = os.path.abspath(os.path.join(root, safe_filename))
    if os.path.commonpath([root, path]) != root:
        raise HTTPException(status_code=400, detail="Invalid upload path")
    return root, path


@router.post("/upload")
@limiter.limit("20/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = Form(default=""),
):
    session_id = session_id or request.query_params.get("session_id", "")
    if not session_id and not await has_admin_access(request):
        raise HTTPException(status_code=400, detail="session_id is required")

    session = None
    if session_id:
        session = await get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        await verify_session_access(request, session)

    contents = await file.read(MAX_SIZE + 1)
    if len(contents) > MAX_SIZE:
        record_failure("uploads", reason="size")
        raise HTTPException(status_code=413, detail="File too large (max 5 MB)")

    actual_mime = _detect_mime(contents)
    if actual_mime not in ALLOWED_TYPES:
        record_failure("uploads", reason="content_type", content_type=file.content_type)
        raise HTTPException(status_code=415, detail="File type not allowed")

    safe_name = os.path.basename(file.filename or "upload")
    filename = f"{uuid.uuid4().hex}_{safe_name}"
    dest_dir, dest_path = _upload_path(session_id or "admin", filename)
    os.makedirs(dest_dir, exist_ok=True)

    with open(dest_path, "wb") as f:
        f.write(contents)

    path_url = f"/v1/uploads/{session_id or 'admin'}/{filename}"
    url = str(request.base_url).rstrip("/") + path_url
    if session_id:
        url += "?" + urlencode({"file_token": _sign_file_token(session_id, filename)})
    record_event("uploads.completed", channel=session.channel if session else "admin", content_type=actual_mime)
    return {"url": url, "filename": filename, "content_type": actual_mime}


@router.get("/uploads/{session_id}/{filename}")
async def serve_file(session_id: str, filename: str, request: Request):
    _, path = _upload_path(session_id, filename)
    file_token = request.query_params.get("file_token", "")
    if not _verify_file_token(file_token, session_id, filename) and not await has_admin_access(request):
        session = await get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        await verify_session_access(request, session)

    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path)
