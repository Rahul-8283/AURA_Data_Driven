import uuid
from typing import List, Optional
from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.celery_app import celery_app
from app.db.chroma_client import init_literature_collection
from app.db.neo4j_client import neo4j_conn
from worker.tasks import harvest_and_ingest_task

router = APIRouter()

class IngestionSyncRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Target battery research topic to harvest")
    sources: Optional[List[str]] = Field(
        default=["arxiv", "wikipedia", "crossref", "pubmed"],
        description="List of sources: arxiv, wikipedia, crossref, pubmed, or all"
    )
    max_results: int = Field(default=10, ge=1, le=50, description="Max results per source")

@router.post("/sync", status_code=202)
async def trigger_literature_sync(request: IngestionSyncRequest):
    """
    Trigger an asynchronous harvesting & ingestion run across chosen
    literature sources. Runs out-of-band in Celery without blocking user requests.
    """
    task_id = str(uuid.uuid4())
    sources = request.sources or ["arxiv", "wikipedia", "crossref", "pubmed"]
    if "all" in sources:
        sources = ["arxiv", "wikipedia", "crossref", "pubmed"]

    task = harvest_and_ingest_task.apply_async(
        args=[request.query, sources, request.max_results],
        task_id=task_id
    )
    return {
        "task_id": task.id,
        "status": "started",
        "query": request.query,
        "sources": sources,
        "message": "Harvesting task initiated in background worker."
    }

@router.get("/status/{task_id}")
async def get_sync_status(task_id: str):
    """
    Poll the live state of an ingestion task.
    """
    task_result = AsyncResult(task_id, app=celery_app)

    if task_result.state == "PENDING":
        return {
            "status": "Pending",
            "stage": "queued",
            "message": "Task is queued in background worker...",
            "papers_found": 0,
            "new_papers_indexed": 0,
        }
    elif task_result.state == "PROGRESS":
        meta = task_result.info or {}
        return {
            "status": "In Progress",
            "stage": meta.get("stage", "harvesting"),
            "message": meta.get("message", "Processing literature..."),
            "papers_found": meta.get("papers_found", 0),
            "new_papers_indexed": meta.get("new_papers_indexed", 0),
        }
    elif task_result.state == "SUCCESS":
        result = task_result.result or {}
        return {
            "status": "Complete",
            "stage": "complete",
            "message": result.get("message", "Harvesting complete."),
            "query": result.get("query", ""),
            "sources": result.get("sources", []),
            "papers_found": result.get("papers_found", 0),
            "new_papers_indexed": result.get("new_papers_indexed", 0),
        }
    elif task_result.state == "FAILURE":
        return {
            "status": "Failed",
            "stage": "failed",
            "message": "Harvesting task encountered an error.",
            "error": str(task_result.info)
        }
    else:
        return {"status": task_result.state}

@router.get("/stats")
async def get_knowledge_stats():
    """
    Get high-level statistics for ChromaDB vectors and Neo4j knowledge graph.
    """
    chroma_count = 0
    neo4j_nodes = 0
    neo4j_relationships = 0

    try:
        collection = init_literature_collection()
        chroma_count = collection.count()
    except Exception as e:
        chroma_count = 0

    try:
        with neo4j_conn.get_session() as session:
            node_res = session.run("MATCH (n) RETURN count(n) AS cnt")
            rec = node_res.single()
            if rec:
                neo4j_nodes = rec["cnt"]

            rel_res = session.run("MATCH ()-[r]->() RETURN count(r) AS cnt")
            rel_rec = rel_res.single()
            if rel_rec:
                neo4j_relationships = rel_rec["cnt"]
    except Exception:
        pass

    return {
        "chroma_literature_chunks": chroma_count,
        "neo4j_nodes": neo4j_nodes,
        "neo4j_relationships": neo4j_relationships,
        "supported_sources": ["arXiv", "Wikipedia", "Crossref", "PubMed (NCBI)"]
    }
