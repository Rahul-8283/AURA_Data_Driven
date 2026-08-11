from fastapi import APIRouter, HTTPException
from app.db.neo4j_client import neo4j_conn
from app.db.chroma_client import chroma_client
from app.db.supabase import supabase_client
from worker.tasks import test_dummy_task
from app.core.celery_app import celery_app
from celery.result import AsyncResult

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok"}

@router.get("/health/db")
async def db_health_check():
    """Detailed health check for databases."""
    status = {}
    
    # Check Neo4j
    neo4j_ok = neo4j_conn.verify_connectivity()
    status["neo4j"] = "connected" if neo4j_ok else "disconnected"
    
    # Check ChromaDB
    try:
        chroma_client.heartbeat()
        status["chroma"] = "connected"
    except Exception as e:
        status["chroma"] = f"disconnected: {e}"
        
    # Check Supabase
    try:
        # Just getting the client implies init worked, but we can try a basic auth call
        # or checking the session, or checking if it's initialized
        res = supabase_client.auth.get_session()
        status["supabase"] = "connected"
    except Exception as e:
        status["supabase"] = f"disconnected: {e}"

    return status

@router.post("/test-celery")
async def trigger_test_celery(iterations: int = 5):
    """Trigger a dummy Celery task."""
    task = test_dummy_task.delay(iterations)
    return {"task_id": task.id}

@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Retrieve the live status of the Celery task."""
    task_result = AsyncResult(task_id, app=celery_app)
    result = {
        "task_id": task_id,
        "task_status": task_result.status,
        "task_result": task_result.result
    }
    return result
