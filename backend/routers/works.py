import asyncio
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from ..services import auto_run, jobs, storage
from ..services.scrape import AgeGateError, ScrapeError, scrape_work

router = APIRouter(prefix="/api/works", tags=["works"])


@router.get("")
def list_works():
    works = storage.get_works()
    counts = jobs.running_counts_by_work()
    for w in works:
        w["runningCount"] = counts.get(w["id"], 0)
    return {"works": works, "deleted": storage.list_deleted_works()}


def _work_exists_http(name: str) -> HTTPException:
    for e in storage.list_deleted_works():
        if str(e.get("name") or "") == name:
            return HTTPException(
                status_code=409,
                detail="Work already exists. Restore the deleted copy instead.",
            )
    return HTTPException(status_code=409, detail="Work already exists.")


class WorkCreateFromUrl(BaseModel):
    source: str = "novel18"
    url: str


@router.post("/from-url", status_code=201)
async def create_work_from_url(body: WorkCreateFromUrl):
    source = (body.source or "novel18").strip() or "novel18"
    url = (body.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required.")
    try:
        info = await asyncio.to_thread(scrape_work, source, url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except (AgeGateError, ScrapeError) as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    name = str(info.get("title") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Could not read work title from URL.")
    try:
        work_id = storage.create_work(name)
    except FileExistsError:
        raise _work_exists_http(name)
    progress = storage.save_auto_progress(
        work_id,
        source,
        "",
        str(info.get("first_chapter_url") or ""),
        work_url=str(info.get("work_url") or ""),
    )
    return {
        "id": work_id,
        "name": name,
        "source": progress["source"],
        "workUrl": progress["workUrl"],
        "nextUrl": progress["nextUrl"],
    }


@router.delete("/{work_id}")
async def delete_work(work_id: str):
    try:
        auto_run.stop(work_id)
    except FileNotFoundError:
        pass
    try:
        storage.delete_work(work_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Work '{work_id}' not found.")
    return {"ok": True}


@router.post("/{work_id}/restore")
def restore_work(work_id: str):
    try:
        return storage.restore_work(work_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{work_id}/purge")
def purge_work(work_id: str):
    try:
        storage.purge_work(work_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ok": True}


class AutoStart(BaseModel):
    count: int = 1


@router.get("/{work_id}/auto")
def get_auto_progress(work_id: str):
    try:
        return auto_run.snapshot(work_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Work '{work_id}' not found.")


@router.post("/{work_id}/auto/start")
async def start_auto(work_id: str, body: AutoStart):
    try:
        return auto_run.start(work_id, body.count)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Work '{work_id}' not found.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{work_id}/auto/stop")
async def stop_auto(work_id: str):
    try:
        return auto_run.stop(work_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Work '{work_id}' not found.")


@router.post("/{work_id}/last-read")
def post_last_read(work_id: str):
    try:
        return storage.touch_last_read(work_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Work '{work_id}' not found.")


class FinishedBody(BaseModel):
    finished: bool


@router.put("/{work_id}/finished")
def put_finished(work_id: str, body: FinishedBody):
    try:
        return storage.set_finished(work_id, body.finished)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Work '{work_id}' not found.")


@router.get("/{work_id}/export")
def export_work(work_id: str, start: int | None = None, end: int | None = None):
    try:
        book_title, data = storage.export_translated_epub(work_id, start, end)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    encoded = quote(f"{book_title}.epub")
    return Response(
        content=data,
        media_type="application/epub+zip",
        headers={
            "Content-Disposition": f"attachment; filename=\"export.epub\"; filename*=UTF-8''{encoded}",
        },
    )
