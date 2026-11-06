import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import storage, jobs

router = APIRouter(prefix="/api/works/{work_id}/chapters", tags=["chapters"])


class ChapterUpdate(BaseModel):
    original: str
    translated: str
    new_title: str | None = None


class ChapterCreate(BaseModel):
    original: str
    translated: str
    title: str | None = None

@router.post("", status_code=201)
def create_chapter(work_id: str, body: ChapterCreate):
    """Save a new chapter (used by the Stop button to save partial translations)."""
    filename = storage.save_chapter(
        work_id,
        body.original,
        body.translated,
        title=body.title,
    )
    # Add a done entry at the top so the new chapter shows up in the sidebar.
    try:
        work_dir = storage._work_dir_or_404(work_id)
        entry_id = storage._mtime_id(work_dir / filename)
        storage.add_order_entry(work_id, entry_id)
        storage.complete_order_entry(work_id, entry_id, filename)
    except Exception:
        pass
    return {"filename": filename}


@router.get("")
def list_chapters(work_id: str):
    try:
        return {"chapters": storage.get_chapter_list(work_id)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Work '{work_id}' not found.")

class ChapterOrder(BaseModel):
    order: list[str]


@router.put("/order")
def set_chapter_order(work_id: str, body: ChapterOrder):
    """Persist an explicit order (list of entry ids) from drag-to-reorder."""
    try:
        storage.save_chapter_order_by_ids(work_id, body.order)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ok": True}

@router.get("/{chapter}")
def get_chapter(work_id: str, chapter: str):
    try:
        data = storage.get_chapter(work_id, chapter)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return data

@router.put("/{chapter}")
def update_chapter(work_id: str, chapter: str, body: ChapterUpdate):
    try:
        new_name = storage.update_chapter(
            work_id,
            chapter,
            body.original,
            body.translated,
            new_title=body.new_title,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if new_name != chapter:
        try:
            storage.rename_in_order(work_id, chapter, new_name)
        except Exception:
            pass
    return {"filename": new_name}

@router.delete("/{chapter}")
def delete_chapter(work_id: str, chapter: str):
    try:
        storage.delete_chapter(work_id, chapter)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    try:
        storage.delete_from_order(work_id, chapter)
    except Exception:
        pass
    return {"ok": True}


@router.post("/{chapter}/retranslate")
async def retranslate_chapter(work_id: str, chapter: str):
    """Retranslate an existing chapter using its original text. The chapter
    file is replaced in place with a temp (empty-translation) placeholder
    while the job runs; on completion the job overwrites the same filename
    with the new translation, preserving its order in the list."""
    try:
        data = storage.get_chapter(work_id, chapter)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    original = data.get("original", "")
    if not original.strip():
        raise HTTPException(status_code=400, detail="Chapter has no original text to retranslate.")
    # Overwrite in place with a temp placeholder (empty translation).
    storage.save_chapter_at(work_id, chapter, original, "")
    # Mark the order entry as retranslating so the sidebar shows a spinner,
    # and reuse its id for the retranslate job so the chapter keeps the same
    # id across original translation and retranslates.
    entry_id = None
    try:
        entry_id = storage.get_entry_id_by_filename(work_id, chapter)
        if entry_id:
            storage.set_status_by_filename(work_id, chapter, "retranslating")
    except Exception:
        pass
    job = jobs.create_job(work_id, original, target_filename=chapter, job_id=entry_id)
    job.task = asyncio.create_task(jobs.run_job(job))
    return {"job_id": job.id}
