import os
import uuid

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.auth import has_admin_access
from core.session_manager import get_session

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

UPLOAD_DIR = "/app/uploads"
MAX_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf"}


def _check_session_auth(request: Request, session) -> None:
    import hmac
    if has_admin_access(request):
        return
    supplied = request.query_params.get("session_token") or request.headers.get("X-Session-Token", "")
    expected = session.metadata.get("customer_token", "")
    if not expected or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/upload")
@limiter.limit("20/minute")
async def upload_file(request: Request, file: UploadFile, session_id: str = ""):
    if not session_id and not has_admin_access(request):
        raise HTTPException(status_code=400, detail="session_id is required")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="File type not allowed")

    contents = await file.read(MAX_SIZE + 1)
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 5 MB)")

    safe_name = os.path.basename(file.filename or "upload")
    filename = f"{uuid.uuid4().hex}_{safe_name}"
    dest_dir = os.path.join(UPLOAD_DIR, session_id or "admin")
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)

    with open(dest_path, "wb") as f:
        f.write(contents)

    url = f"/v1/uploads/{session_id or 'admin'}/{filename}"
    return {"url": url, "filename": filename, "content_type": file.content_type}


@router.get("/uploads/{session_id}/{filename}")
async def serve_file(session_id: str, filename: str, request: Request):
    if not has_admin_access(request):
        session = await get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        _check_session_auth(request, session)

    path = os.path.join(UPLOAD_DIR, session_id, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path)
