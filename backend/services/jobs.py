"""In-memory store for background translation jobs.

A job runs the LLM translation independently of any client connection, so
the chapter file is saved even if the user navigates away. The frontend
polls job status (no SSE streaming).
"""
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from . import llm


@dataclass
class Job:
    id: str
    work_name: str
    input_text: str
    created_at: str  # timestamp matching save_chapter's format
    status: str = "running"  # running | done | error | cancelled
    filename: Optional[str] = None
    added_names: int = 0
    error: Optional[str] = None
    task: Optional[asyncio.Task] = None
    target_filename: Optional[str] = None  # set for retranslate; overwrite in place


# Module-level job store. uvicorn runs a single process, so this is fine.
_jobs: dict[str, Job] = {}


def create_job(
    work_name: str,
    input_text: str,
    target_filename: Optional[str] = None,
    job_id: Optional[str] = None,
) -> Job:
    # Microsecond timestamp: unique AND sortable (newest first = string desc).
    # Doubles as the order-list entry id. For retranslate, the caller passes
    # the existing entry's id so the chapter keeps the same id across
    # original translation and all retranslates.
    if job_id is None:
        job_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    job = Job(
        id=job_id,
        work_name=work_name,
        input_text=input_text,
        created_at=datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
        target_filename=target_filename,
    )
    _jobs[job_id] = job
    return job


def get_job(job_id: str) -> Optional[Job]:
    return _jobs.get(job_id)


def cancel_job(job_id: str) -> bool:
    job = _jobs.get(job_id)
    if not job or job.status != "running":
        return False
    if job.task is not None:
        job.task.cancel()
    job.status = "cancelled"
    return True


async def run_job(job: Job) -> None:
    """Run the LLM translation to completion. The chapter file is saved by
    llm.stream_translation_with_title on the 'done' event. Reasoning and
    content chunks are discarded (no streaming)."""
    from . import storage
    try:
        async for kind, chunk in llm.stream_translation_with_title(
            job.work_name, job.input_text, None,
            target_filename=job.target_filename,
        ):
            if kind == "done":
                try:
                    info = json.loads(chunk)
                except Exception:
                    info = {}
                job.filename = info.get("filename")
                job.added_names = info.get("added_names", 0)
                job.status = "done"
                # Update the order-list entry. For a normal translation the entry
                # was created at task-creation time (id == job.id); fill it in.
                # For a retranslate (target_filename set) the entry already
                # exists for the chapter file; just flip its status to done.
                try:
                    if job.target_filename:
                        storage.set_status_by_filename(
                            job.work_name, job.target_filename, "done"
                        )
                    elif job.filename:
                        storage.complete_order_entry(
                            job.work_name, job.id, job.filename
                        )
                        # If complete didn't find the entry (e.g. order file was
                        # reset), fall back to adding it at top.
                        entries = storage._read_order(job.work_name)
                        if not any(e["id"] == job.id for e in entries):
                            storage.add_order_entry(job.work_name, job.id)
                            storage.complete_order_entry(
                                job.work_name, job.id, job.filename
                            )
                    else:
                        storage.cancel_order_entry(job.work_name, job.id)
                except Exception:
                    pass
    except asyncio.CancelledError:
        job.status = "cancelled"
        try:
            if job.target_filename:
                storage.set_status_by_filename(
                    job.work_name, job.target_filename, "done"
                )
            else:
                storage.cancel_order_entry(job.work_name, job.id)
        except Exception:
            pass
        raise
    except Exception as e:
        job.status = "error"
        job.error = str(e)
        try:
            if job.target_filename:
                storage.set_status_by_filename(
                    job.work_name, job.target_filename, "done"
                )
            else:
                storage.cancel_order_entry(job.work_name, job.id)
        except Exception:
            pass
