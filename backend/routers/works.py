from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import storage

router = APIRouter(prefix="/api/works", tags=["works"])


class WorkCreate(BaseModel):
    name: str


@router.get("")
def list_works():
    return {"works": storage.get_works()}


@router.post("", status_code=201)
def create_work(body: WorkCreate):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Work name cannot be empty.")
    work_id = storage.create_work(name)
    return {"id": work_id, "name": name}


@router.delete("/{work_id}")
def delete_work(work_id: str):
    try:
        storage.delete_work(work_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Work '{work_id}' not found.")
    return {"ok": True}
