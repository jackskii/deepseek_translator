from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import storage

router = APIRouter(prefix="/api/works/{work_id}/terms", tags=["terms"])
universal_router = APIRouter(prefix="/api/universal-terms", tags=["universal-terms"])


class TermCreate(BaseModel):
    original: str
    translation: str


class TermUpdate(BaseModel):
    translation: str
    # If the original key changed, supply the new one here.
    new_original: str | None = None


@router.get("")
def list_terms(work_id: str):
    try:
        return {"terms": storage.load_macro(work_id)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Work '{work_id}' not found.")


@router.post("", status_code=201)
def add_term(work_id: str, body: TermCreate):
    o = body.original.strip()
    t = body.translation.strip()
    if not o or not t:
        raise HTTPException(status_code=400, detail="Both fields are required.")
    data = storage.load_macro(work_id)
    data[o] = t
    storage.save_macro(work_id, data)
    return {"ok": True}


@router.put("/{original}")
def update_term(work_id: str, original: str, body: TermUpdate):
    data = storage.load_macro(work_id)
    if original not in data:
        raise HTTPException(status_code=404, detail=f"Term '{original}' not found.")
    new_o = (body.new_original or original).strip()
    del data[original]
    data[new_o] = body.translation.strip()
    storage.save_macro(work_id, data)
    return {"ok": True}


@router.delete("/{original}")
def delete_term(work_id: str, original: str):
    data = storage.load_macro(work_id)
    if original not in data:
        raise HTTPException(status_code=404, detail=f"Term '{original}' not found.")
    del data[original]
    storage.save_macro(work_id, data)
    return {"ok": True}


@universal_router.get("")
def list_universal_terms():
    return {"terms": storage.load_universal_macro()}


@universal_router.post("", status_code=201)
def add_universal_term(body: TermCreate):
    o = body.original.strip()
    t = body.translation.strip()
    if not o or not t:
        raise HTTPException(status_code=400, detail="Both fields are required.")
    data = storage.load_universal_macro()
    data[o] = t
    storage.save_universal_macro(data)
    return {"ok": True}


@universal_router.put("/{original}")
def update_universal_term(original: str, body: TermUpdate):
    data = storage.load_universal_macro()
    if original not in data:
        raise HTTPException(status_code=404, detail=f"Term '{original}' not found.")
    new_o = (body.new_original or original).strip()
    del data[original]
    data[new_o] = body.translation.strip()
    storage.save_universal_macro(data)
    return {"ok": True}


@universal_router.delete("/{original}")
def delete_universal_term(original: str):
    data = storage.load_universal_macro()
    if original not in data:
        raise HTTPException(status_code=404, detail=f"Term '{original}' not found.")
    del data[original]
    storage.save_universal_macro(data)
    return {"ok": True}
