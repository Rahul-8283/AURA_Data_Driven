import asyncio
import logging
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.core.security import get_current_user
from app.db.literature_store import get_literature_store
from app.services.llm.client import INSUFFICIENT_EVIDENCE, answer_question_async
from app.services.llm.errors import LLMQuotaExceeded, LLMUnavailableError
from app.services.rate_limit import daily_limiter
from app.services.retrieval.graph_search import fallback_entities, fetch_graph_rules

logger = logging.getLogger(__name__)

router = APIRouter()

TOP_K = 5
MAX_RULES = 8
SNIPPET_CHARS = 240
NO_EVIDENCE_ANSWER = (
    "I couldn't find enough evidence in the indexed literature or the knowledge graph to answer that. "
    "Harvest papers on this topic from the Evidence tab, or switch to Discover to search for candidate materials."
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 3:
            raise ValueError("question must contain at least 3 characters")
        return value


class Source(BaseModel):
    id: str
    title: str
    doi: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None
    snippet: str
    distance: float


class AskResponse(BaseModel):
    answer: str
    grounded: bool
    sources: List[Source]
    graph_rules: List[str]
    remaining_today: Optional[int] = None


def group_sources(chunks: List[Dict]) -> Tuple[List[Source], List[Dict]]:
    """Several chunks of one paper become one numbered source. Chunks arrive nearest first, so a
    source keeps its best chunk as the snippet and numbering follows relevance."""
    sources: Dict[str, Source] = {}
    passages: List[Dict] = []
    for chunk in chunks:
        meta = chunk.get("metadata") or {}
        key = meta.get("doi") or meta.get("title") or chunk["content"][:60]
        if key not in sources:
            sources[key] = Source(
                id=f"S{len(sources) + 1}",
                title=meta.get("title") or "Untitled",
                doi=meta.get("doi") or None,
                url=meta.get("url") or None,
                source=meta.get("source"),
                snippet=chunk["content"][:SNIPPET_CHARS],
                distance=round(chunk["distance"], 3),
            )
        passages.append({"label": sources[key].id, "title": sources[key].title, "text": chunk["content"]})
    return list(sources.values()), passages


@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest, user=Depends(get_current_user)):
    """Answer a battery question from the harvested literature and the knowledge graph only.

    No evidence means no LLM call and no spent quota. Entities for the graph lookup come from the
    seed vocabulary rather than an LLM, so a question costs at most one LLM request."""
    try:
        chunks = await asyncio.to_thread(get_literature_store().search, request.question, TOP_K)
    except Exception:
        logger.exception("Literature search failed")
        raise HTTPException(status_code=503, detail="Literature search is unavailable right now.")
    relevant = [chunk for chunk in chunks if chunk["distance"] <= settings.ASK_MAX_DISTANCE]

    rules: List[str] = []
    entities = fallback_entities(request.question)
    if entities:
        try:
            rules = (await fetch_graph_rules(entities))[:MAX_RULES]
        except Exception:
            logger.exception("Graph rule lookup failed; answering from literature only")

    if not relevant and not rules:
        return AskResponse(answer=NO_EVIDENCE_ANSWER, grounded=False, sources=[], graph_rules=[])

    allowed, remaining = await asyncio.to_thread(daily_limiter.consume, str(user.id), settings.ASK_DAILY_LIMIT)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"You have used today's {settings.ASK_DAILY_LIMIT} answers. Try again tomorrow, or use Discover.",
        )

    sources, passages = group_sources(relevant)
    try:
        answer = await answer_question_async(request.question, passages, rules)
    except LLMQuotaExceeded as e:
        raise HTTPException(status_code=503, detail=str(e)) from None
    except LLMUnavailableError:
        raise HTTPException(status_code=503, detail="The language model is unavailable right now. Please try again.") from None

    if not answer or INSUFFICIENT_EVIDENCE in answer:
        return AskResponse(answer=NO_EVIDENCE_ANSWER, grounded=False, sources=[], graph_rules=[], remaining_today=remaining)
    return AskResponse(answer=answer, grounded=True, sources=sources, graph_rules=rules, remaining_today=remaining)
