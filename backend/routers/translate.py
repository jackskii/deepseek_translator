from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import jobs

router = APIRouter(prefix="/api/works/{work_id}/translate", tags=["translate"])


class TranslateRequest(BaseModel):
    input_text: str
    title: str | None = None  # unused by the async flow; kept for compatibility


@router.post("")
async def translate(work_id: str, body: TranslateRequest):
    """Start a background translation job. Returns {job_id} immediately; the
    job keeps running (and saves the chapter file) even if the client
    disconnects. Poll GET /jobs/{job_id} for status."""
    if not body.input_text.strip():
        raise HTTPException(status_code=400, detail="input_text cannot be empty.")
    try:
        job = jobs.start(work_id, body.input_text)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"job_id": job.id}


@router.post("/jobs/{job_id}/cancel")
def cancel_job_endpoint(work_id: str, job_id: str):
    if not jobs.cancel(work_id, job_id):
        raise HTTPException(status_code=404, detail="Job not found.")
    return {"ok": True}


@router.get("/jobs/{job_id}")
def job_status(work_id: str, job_id: str):
    """Lightweight status poll (used by the frontend global watcher to detect
    completion when the user is on another page)."""
    job = jobs.get_job(job_id)
    if not job or job.work_id != work_id:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {
        "status": job.status,
        "filename": job.filename,
        "added_names": job.added_names,
        "error": job.error,
        "created_at": job.created_at,
    }
