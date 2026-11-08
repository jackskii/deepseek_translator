"""In-memory store and lifecycle for background translation jobs.

A job runs the LLM translation independently of any client connection, so
the chapter file is saved even if the user navigates away. The frontend
polls job status (no SSE streaming).

This module is the only place that touches the chapter file and the order
list during a job. The LLM client only talks to the model; the routers only
validate input and call `start` / `start_retranslate` / `cancel`.
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from . import llm, storage

# First failure immediately retries the same job. Second failure sticks.
MAX_TRIES = 2


@dataclass
class Job:
    id: str
    work_id: str
    input_text: str
    created_at: str  # human-readable timestamp for display
    is_retranslate: bool = False
    filename: Optional[str] = None  # chapter file this job owns
    status: str = "running"  # running | done | error | cancelled
    added_names: int = 0
    error: Optional[str] = None
    task: Optional[asyncio.Task] = None


# Module-level job store. uvicorn runs a single process, so this is fine.
_jobs: dict[str, Job] = {}


def _new_id() -> str:
    """Microsecond timestamp: unique AND sortable (newest first = string desc).
    Doubles as the order-list entry id."""
    return datetime.now().strftime("%Y%m%d%H%M%S%f")


def get_job(job_id: str) -> Optional[Job]:
    return _jobs.get(job_id)


def running_counts_by_work() -> dict[str, int]:
    counts: dict[str, int] = {}
    for j in _jobs.values():
        if j.status == "running":
            counts[j.work_id] = counts.get(j.work_id, 0) + 1
    return counts


def running_total() -> int:
    return sum(1 for j in _jobs.values() if j.status == "running")


def list_jobs(work_id: str) -> list[dict]:
    out: list[dict] = []
    for j in _jobs.values():
        if j.work_id != work_id:
            continue
        out.append(
            {
                "id": j.id,
                "status": j.status,
                "filename": j.filename,
                "is_retranslate": j.is_retranslate,
                "created_at": j.created_at,
                "input_text": j.input_text,
                "error": j.error,
            }
        )
    out.sort(key=lambda e: e["id"], reverse=True)
    return out


def start(work_id: str, input_text: str) -> Job:
    """Reserve a timestamp-named chapter file with a pending order entry,
    then kick off the background translation. Raises if the file cannot be
    reserved (the caller returns the error to the client)."""
    job_id = _new_id()
    filename = storage.reserve_pending_chapter(work_id, job_id, input_text)
    job = Job(
        id=job_id,
        work_id=work_id,
        input_text=input_text,
        created_at=datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
        is_retranslate=False,
        filename=filename,
    )
    _jobs[job_id] = job
    job.task = asyncio.create_task(_run(job))
    return job


def start_retranslate(work_id: str, filename: str) -> Job:
    """Retranslate an existing chapter in place. Reuses the chapter's
    existing order-entry id so its position (and id) are preserved across
    retranslates. The old translation stays on disk until the new one lands."""
    entry_id = storage.get_entry_id_by_filename(work_id, filename)
    storage.set_status_by_filename(work_id, filename, "retranslating")
    data = storage.get_chapter(work_id, filename)
    original = data.get("original", "")
    job = Job(
        id=entry_id or _new_id(),
        work_id=work_id,
        input_text=original,
        created_at=datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
        is_retranslate=True,
        filename=filename,
    )
    _jobs[job.id] = job
    job.task = asyncio.create_task(_run(job))
    return job


def cancel(work_id: str, job_id: str) -> bool:
    """Cancel a running job and clean up disk once.

    - New task: delete the reserved timestamp file and its order entry.
    - Retranslate: the chapter file still has the old translation; just
      flip the entry back to done (or failed if the file is empty).
    Returns False if there is no matching running job.
    """
    job = _jobs.get(job_id)
    if not job or job.work_id != work_id or job.status != "running":
        return False
    if job.task is not None:
        job.task.cancel()
    job.status = "cancelled"
    if job.is_retranslate:
        storage.set_status_by_filename(
            work_id, job.filename, "done" if _has_translation(work_id, job.filename) else "failed"
        )
    else:
        storage.delete_chapter(work_id, job.filename)
        storage.cancel_order_entry(work_id, job_id)
    return True


def _has_translation(work_id: str, filename: str) -> bool:
    try:
        data = storage.get_chapter(work_id, filename)
    except FileNotFoundError:
        return False
    return bool(str(data.get("translated") or "").strip())


async def _run(job: Job) -> None:
    """Run the LLM translation to completion and persist the result.

    On success: write the translation into the job's file, rename a new
    task's file to the translation title, and mark the order entry done.
    On exception: retry immediately (same job, same file), up to MAX_TRIES
    total attempts. After that, leave the old translation (retranslate) or
    the empty reserved file (new task) in place; get_chapter_list reports
    it as failed.
    """
    last_error: Optional[str] = None
    for attempt in range(1, MAX_TRIES + 1):
        try:
            translation, names = await llm.translate(job.work_id, job.input_text)
        except asyncio.CancelledError:
            job.status = "cancelled"
            raise
        except Exception as e:
            last_error = str(e)
            job.error = last_error
            if attempt >= MAX_TRIES:
                job.status = "error"
                return
            continue

        job.added_names = len(names)
        job.error = None
        _finish(job, translation)
        job.status = "done"
        return

    job.status = "error"
    job.error = last_error


def _finish(job: Job, translation: str) -> None:
    """Write the translation to the job's file and update the order entry."""
    storage.save_chapter_at(job.work_id, job.filename, job.input_text, translation)
    if job.is_retranslate:
        # Retranslate keeps the filename; status reflects the file's content.
        storage.set_status_by_filename(
            job.work_id, job.filename, "done" if (translation or "").strip() else "failed"
        )
    else:
        # New task: rename the timestamp file to the translation title.
        if (translation or "").strip():
            job.filename = storage.rename_chapter_to_title(
                job.work_id, job.filename, translation
            )
        storage.complete_order_entry(
            job.work_id, job.id, job.filename,
            status="done" if (translation or "").strip() else "failed",
        )
