import uuid
from datetime import datetime, timezone

from celery.result import AsyncResult
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.celery_app import celery_app
from app.core.security import get_current_user
from app.db.supabase import supabase_client
from worker.tasks import run_discovery_loop

router = APIRouter()

class ResearchRequest(BaseModel):
    prompt: str

@router.post("/start", status_code=202)
async def start_research(request: ResearchRequest, user=Depends(get_current_user)):
    task_id = str(uuid.uuid4())

    try:
        supabase_client.table("ResearchTasks").insert({
            "id": task_id,
            "user_id": user.id,
            "prompt": request.prompt,
            "status": "processing",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        # Non-fatal: the discovery loop still runs even if the row can't be
        # pre-created; the reporter's UPDATE will simply be a no-op.
        pass

    task = run_discovery_loop.apply_async(
        args=[request.prompt, task_id, user.id],
        task_id=task_id
    )
    return {"task_id": task.id, "status": "started"}

@router.get("/status/{task_id}")
async def get_research_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)

    if task_result.state == 'PENDING':
        return {"status": "Pending...", "generation": 0, "best_score": 0.0}
    elif task_result.state == 'PROGRESS':
        meta = task_result.info or {}
        return {
            "status": meta.get("message", "In Progress..."),
            "generation": meta.get("generation", 0),
            "best_score": meta.get("best_score", 0.0)
        }
    elif task_result.state == 'SUCCESS':
        result = task_result.result or {}
        candidates = result.get("results", [])
        best_score = round(candidates[0].get("fitness", 0.0), 2) if candidates else 0.0
        return {
            "status": "Complete",
            "generation": result.get("generation", 0),
            "best_score": best_score,
            "results": candidates,
            "executive_summary": result.get("executive_summary", "")
        }
    elif task_result.state == 'FAILURE':
        return {"status": "Failed", "error": str(task_result.info)}
    else:
        return {"status": task_result.state}
