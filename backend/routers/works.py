from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from ..services import jobs, storage

router = APIRouter(prefix="/api/works", tags=["works"])


class WorkCreate(BaseModel):
    name: str


@router.get("")
def list_works():
    works = storage.get_works()
    counts = jobs.running_counts_by_work()
    for w in works:
        w["runningCount"] = counts.get(w["id"], 0)
    return {"works": works}


@router.post("", status_code=201)
def create_work(body: WorkCreate):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Work name cannot be empty.")
    try:
        work_id = storage.create_work(name)
    except FileExistsError:
        raise HTTPException(status_code=409, detail="Work already exists.")
    return {"id": work_id, "name": name}


@router.delete("/{work_id}")
def delete_work(work_id: str):
    try:
        storage.delete_work(work_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Work '{work_id}' not found.")
    return {"ok": True}


class AutoProgress(BaseModel):
    source: str = "novel18"
    lastUrl: str = ""
    nextUrl: str = ""


@router.get("/{work_id}/auto")
def get_auto_progress(work_id: str):
    try:
        return storage.load_auto_progress(work_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Work '{work_id}' not found.")


@router.put("/{work_id}/auto")
def put_auto_progress(work_id: str, body: AutoProgress):
    try:
        return storage.save_auto_progress(work_id, body.source, body.lastUrl, body.nextUrl)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Work '{work_id}' not found.")


@router.post("/{work_id}/last-read")
def post_last_read(work_id: str):
    try:
        return storage.touch_last_read(work_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Work '{work_id}' not found.")


@router.get("/{work_id}/export")
def export_work(work_id: str):
    try:
        work_name, data = storage.export_translated_epub(work_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Work '{work_id}' not found.")
    encoded = quote(f"{work_name}.epub")
    return Response(
        content=data,
        media_type="application/epub+zip",
        headers={
            "Content-Disposition": f"attachment; filename=\"export.epub\"; filename*=UTF-8''{encoded}",
        },
    )
