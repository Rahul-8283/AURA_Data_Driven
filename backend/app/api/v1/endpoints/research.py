import logging
import uuid
from datetime import datetime, timezone

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.celery_app import celery_app
from app.core.security import get_current_user
from app.db.supabase import supabase_client
from worker.tasks import run_discovery_loop

logger = logging.getLogger(__name__)

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
        # Without the row the reporter's UPDATE is a no-op and its SavedMaterials
        # insert violates the task_id foreign key, so the run would burn LLM quota
        # and leave nothing for the user. Refuse to start it.
        logger.exception("Could not create ResearchTasks row for task %s", task_id)
        raise HTTPException(status_code=503, detail="Could not record the research task. Please try again.")

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
            "executive_summary": result.get("executive_summary", ""),
            "generation_history": result.get("generation_history", [])
        }
    elif task_result.state == 'FAILURE':
        return {"status": "Failed", "error": str(task_result.info)}
    else:
        return {"status": task_result.state}
