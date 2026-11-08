"""Server-side auto-translate loop (scrape next N, start jobs).

One run per work. In-flight LLM jobs are not cancelled when auto stops.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

from . import jobs, storage
from .scrape import AgeGateError, ScrapeError, scrape

MAX_RUNNING = 10
GAP_SEC = 2.0


@dataclass
class AutoRun:
    work_id: str
    started: int = 0
    limit: int = 1
    running: bool = False
    current_url: str = ""
    message: str = ""
    task: Optional[asyncio.Task] = field(default=None, repr=False)


_runs: dict[str, AutoRun] = {}


def snapshot(work_id: str) -> dict:
    progress = storage.load_auto_progress(work_id)
    run = _runs.get(work_id)
    return {
        **progress,
        "running": bool(run and run.running),
        "started": run.started if run else 0,
        "limit": run.limit if run else None,
        "currentUrl": run.current_url if run else "",
        "message": run.message if run else "",
    }


def start(work_id: str, count: int) -> dict:
    storage._resolve_work_name(work_id)
    progress = storage.load_auto_progress(work_id)
    next_url = str(progress.get("nextUrl") or "").strip()
    if not next_url:
        raise ValueError("no next chapter URL")
    existing = _runs.get(work_id)
    if existing and existing.running:
        raise ValueError("auto-translate already running")
    n = max(1, int(count))
    run = AutoRun(
        work_id=work_id,
        limit=n,
        running=True,
        current_url=next_url,
        message="",
    )
    run.task = asyncio.get_running_loop().create_task(_loop(run))
    _runs[work_id] = run
    return snapshot(work_id)


def stop(work_id: str) -> dict:
    storage._resolve_work_name(work_id)
    run = _runs.get(work_id)
    if run and run.running:
        run.running = False
        run.message = "已停止"
        if run.task is not None:
            run.task.cancel()
    return snapshot(work_id)


async def _loop(run: AutoRun) -> None:
    try:
        while run.running:
            while run.running and jobs.running_total() >= MAX_RUNNING:
                await asyncio.sleep(0.5)
            if not run.running:
                break
            progress = storage.load_auto_progress(run.work_id)
            url = str(progress.get("nextUrl") or "").strip()
            source = str(progress.get("source") or "novel18")
            if not url:
                run.running = False
                run.message = "已结束（空页）"
                break
            run.current_url = url
            try:
                scraped = await asyncio.to_thread(scrape, source, url)
            except asyncio.CancelledError:
                raise
            except (AgeGateError, ScrapeError, ValueError) as e:
                run.running = False
                run.message = str(e)
                break
            except Exception as e:
                run.running = False
                run.message = str(e)
                break
            if scraped.get("empty"):
                run.running = False
                run.message = "已结束（空页）"
                break
            text = f"{scraped.get('title') or ''}\n\n{scraped.get('body') or ''}".strip()
            if not text:
                run.running = False
                run.message = "已结束（空页）"
                break
            jobs.start(run.work_id, text)
            run.started += 1
            next_url = str(scraped.get("next_url") or "")
            storage.save_auto_progress(run.work_id, source, url, next_url)
            if run.limit is not None and run.started >= run.limit:
                run.running = False
                run.message = f"已结束（{run.started} 章）"
                break
            if not next_url:
                run.running = False
                run.message = "已结束（空页）"
                break
            await asyncio.sleep(GAP_SEC)
    except asyncio.CancelledError:
        run.running = False
        if not run.message:
            run.message = "已停止"
    except Exception as e:
        run.running = False
        run.message = str(e)
