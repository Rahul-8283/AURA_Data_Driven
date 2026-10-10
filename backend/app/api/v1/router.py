from fastapi import APIRouter
from app.api.v1.endpoints import graph, health, rag, research

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(rag.router, prefix="/rag", tags=["RAG"])
api_router.include_router(research.router, prefix="/research", tags=["Research"])
api_router.include_router(graph.router, prefix="/graph", tags=["Graph"])
