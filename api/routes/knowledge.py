import logging
import os
import subprocess

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile

from core.auth import verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


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
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Supported: {list(ALLOWED_EXTENSIONS)}",
        )

    save_path = f"/app/handbook/{file.filename}"
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    background_tasks.add_task(run_ingestion)
    return {
        "message": f"Uploaded: {file.filename}. Ingestion started in background.",
        "filename": file.filename,
    }


@router.post("/knowledge/ingest")
async def trigger_ingestion(
    background_tasks: BackgroundTasks, _: None = Depends(verify_api_key)
):
    background_tasks.add_task(run_ingestion)
    return {"message": "Ingestion triggered in background"}
