from fastapi import APIRouter

from ..services import jobs

router = APIRouter(prefix="/api/works/{work_id}/translate", tags=["translate"])


@router.get("/jobs")
def list_jobs(work_id: str):
    return {"jobs": jobs.list_jobs(work_id)}
