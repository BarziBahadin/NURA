import logging
import os
import subprocess
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile

from core.auth import verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
HANDBOOK_DIR = Path("/app/handbook")
MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def run_ingestion():
    try:
        result = subprocess.run(
            ["python", "/app/ingestion/ingest.py"],
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ},
        )
        logger.info(f"Ingestion stdout: {result.stdout}")
        if result.returncode != 0:
            logger.error(f"Ingestion stderr: {result.stderr}")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")


@router.post("/knowledge/upload")
async def upload_handbook(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    _: None = Depends(verify_api_key),
):
    original_name = file.filename or ""
    safe_name = Path(original_name).name
    ext = Path(safe_name).suffix.lower()
    if not safe_name or safe_name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Supported: {list(ALLOWED_EXTENSIONS)}",
        )

    HANDBOOK_DIR.mkdir(parents=True, exist_ok=True)
    save_path = (HANDBOOK_DIR / safe_name).resolve()
    if HANDBOOK_DIR.resolve() not in save_path.parents:
        raise HTTPException(status_code=400, detail="Invalid upload path")

    total = 0
    with open(save_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                save_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File too large")
            f.write(chunk)

    background_tasks.add_task(run_ingestion)
    return {
        "message": f"Uploaded: {safe_name}. Ingestion started in background.",
        "filename": safe_name,
    }


@router.post("/knowledge/ingest")
async def trigger_ingestion(
    background_tasks: BackgroundTasks, _: None = Depends(verify_api_key)
):
    background_tasks.add_task(run_ingestion)
    return {"message": "Ingestion triggered in background"}
