import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.retrieval.graph_rag import GraphRAGService, reformat_with_llm

logger = logging.getLogger(__name__)

router = APIRouter()

class RAGRequest(BaseModel):
    prompt: str

class RAGResponse(BaseModel):
    context: str
    raw_context: str

@router.post("/query", response_model=RAGResponse)
async def query_rag(request: RAGRequest):
    """
    Accepts a user query, triggers the hybrid GraphRAG engine,
    and returns the fused semantic and structural context.
    """
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
    try:
        raw_context = await GraphRAGService.retrieve_context(request.prompt)
        context = await asyncio.to_thread(reformat_with_llm, request.prompt, raw_context)
        return RAGResponse(context=context, raw_context=raw_context)
    except Exception:
        logger.exception("RAG query failed")
        raise HTTPException(status_code=500, detail="Failed to retrieve context")
