from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.retrieval.graph_rag import GraphRAGService

router = APIRouter()

class RAGRequest(BaseModel):
    prompt: str

class RAGResponse(BaseModel):
    context: str

@router.post("/query", response_model=RAGResponse)
async def query_rag(request: RAGRequest):
    """
    Accepts a user query, triggers the hybrid GraphRAG engine,
    and returns the fused semantic and structural context.
    """
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
    try:
        context = await GraphRAGService.retrieve_context(request.prompt)
        return RAGResponse(context=context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
