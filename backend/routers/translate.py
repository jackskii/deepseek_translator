import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import jobs, storage

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

    job = jobs.create_job(work_id, body.input_text)
    # Create the pending order-list entry immediately so the sidebar shows the
    # task at the top (newest first) while it translates.
    try:
        storage.add_order_entry(work_id, job.id)
    except Exception:
        pass
    job.task = asyncio.create_task(jobs.run_job(job))
    return {"job_id": job.id}


@router.post("/jobs/{job_id}/cancel")
def cancel_job_endpoint(work_id: str, job_id: str):
    job = jobs.get_job(job_id)
    if not job or job.work_id != work_id:
        raise HTTPException(status_code=404, detail="Job not found.")
    jobs.cancel_job(job_id)
    try:
        if job.target_filename:
            # Retranslate cancel: the chapter file still exists; restore done.
            storage.set_status_by_filename(work_id, job.target_filename, "done")
        else:
            storage.cancel_order_entry(work_id, job_id)
    except Exception:
        pass
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
