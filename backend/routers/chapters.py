from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import jobs, storage

router = APIRouter(prefix="/api/works/{work_id}/chapters", tags=["chapters"])


class ChapterUpdate(BaseModel):
    original: str
    translated: str
    new_title: str | None = None


@router.get("")
def list_chapters(work_id: str):
    try:
        return {"chapters": storage.get_chapter_list(work_id)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Work '{work_id}' not found.")


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
            work_id, chapter, body.original, body.translated, new_title=body.new_title
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if new_name != chapter:
        storage.rename_in_order(work_id, chapter, new_name)
    return {"filename": new_name}


@router.delete("/{chapter}")
def delete_chapter(work_id: str, chapter: str):
    try:
        storage.delete_chapter(work_id, chapter)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    storage.delete_from_order(work_id, chapter)
    return {"ok": True}


@router.post("/{chapter}/retranslate")
async def retranslate_chapter(work_id: str, chapter: str):
    """Retranslate an existing chapter in place. The old translation stays on
    disk (and visible in the viewer) until the new one is ready."""
    try:
        data = storage.get_chapter(work_id, chapter)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if not str(data.get("original") or "").strip():
        raise HTTPException(status_code=400, detail="Chapter has no original text to retranslate.")
    job = jobs.start_retranslate(work_id, chapter)
    return {"job_id": job.id}
