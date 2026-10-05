from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
import uuid
from celery.result import AsyncResult
from worker.tasks import run_discovery_loop

router = APIRouter()

class ResearchRequest(BaseModel):
    prompt: str

@router.post("/start")
async def start_research(request: ResearchRequest):
    task_id = str(uuid.uuid4())
    # Fire off the Celery task
    task = run_discovery_loop.apply_async(
        args=[request.prompt, task_id],
        task_id=task_id
    )
    return {"task_id": task.id, "status": "started"}

@router.get("/status/{task_id}")
async def get_research_status(task_id: str):
    task_result = AsyncResult(task_id)
    
    if task_result.state == 'PENDING':
        return {"status": "Pending...", "generation": 0, "best_score": 0.0}
    elif task_result.state == 'PROGRESS':
        meta = task_result.info
        return {
            "status": meta.get("message", "In Progress..."),
            "generation": meta.get("generation", 0),
            "best_score": meta.get("best_score", 0.0)
        }
    elif task_result.state == 'SUCCESS':
        return {
            "status": "Complete", 
            "generation": 20, 
            "best_score": 0.0,
            "results": task_result.result.get("results", [])
        }
    elif task_result.state == 'FAILURE':
        return {"status": "Failed", "error": str(task_result.info)}
    else:
        return {"status": task_result.state}
