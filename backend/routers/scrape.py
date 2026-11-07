import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.scrape import AgeGateError, ScrapeError, scrape

router = APIRouter(prefix="/api/scrape", tags=["scrape"])


class ScrapeRequest(BaseModel):
    source: str
    url: str


@router.post("")
async def scrape_chapter(body: ScrapeRequest):
    source = (body.source or "").strip()
    url = (body.url or "").strip()
    if not source or not url:
        raise HTTPException(status_code=400, detail="source and url are required.")
    try:
        return await asyncio.to_thread(scrape, source, url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except (AgeGateError, ScrapeError) as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
