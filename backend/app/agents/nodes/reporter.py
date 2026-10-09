import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.agents.state import ResearchState
from app.db.supabase import supabase_client
from app.services.llm.client import summarize_report_async

logger = logging.getLogger(__name__)


def _persist_results(
    task_id: str,
    user_id: str,
    best_candidates: List[Dict[str, Any]],
    summary: str,
) -> None:
    """
    Synchronous Supabase writes, run off the event loop via asyncio.to_thread.
    Updates the ResearchTasks row created at task start, then records each
    top candidate in SavedMaterials for the user's dashboard history.
    """
    supabase_client.table("ResearchTasks").update({
        "status": "completed",
        "result_json": {
            "top_candidates": best_candidates,
            "executive_summary": summary,
        },
    }).eq("id", task_id).execute()

    if not best_candidates:
        return

    rows = [
        {
            "task_id": task_id,
            "user_id": user_id,
            "composition": mat.get("composition"),
            "predicted_capacity": mat.get("specific_capacity"),
            "predicted_cost": mat.get("cost_estimate_usd_kg"),
            "reasoning": mat.get("reasoning"),
        }
        for mat in best_candidates
    ]
    supabase_client.table("SavedMaterials").insert(rows).execute()


async def reporter_node(state: ResearchState) -> ResearchState:
    """
    Phase 8: Reporter Node Logic
    Final node in the LangGraph workflow. Aggregates the hall-of-fame
    candidates, writes an LLM executive summary, and persists the final
    report to Supabase (ResearchTasks + SavedMaterials).
    """
    best_candidates = state.get("best_candidates", [])[:5]
    user_prompt = state.get("user_prompt", "")
    task_id = state.get("task_id", "")
    user_id = state.get("user_id", "default_user")

    try:
        summary = await summarize_report_async(user_prompt, best_candidates)
    except Exception as e:
        logger.error(f"Executive summary generation failed: {e}")
        summary = (
            "An automated executive summary could not be generated for this run. "
            f"The evolutionary search still completed and surfaced {len(best_candidates)} candidate(s)."
        )

    state["final_summary"] = summary
    state.setdefault("logs", []).append(
        f"[{datetime.now(timezone.utc).isoformat()}] Reporter: Generated executive summary."
    )

    try:
        await asyncio.to_thread(_persist_results, task_id, user_id, best_candidates, summary)
        state.setdefault("logs", []).append(
            f"[{datetime.now(timezone.utc).isoformat()}] Reporter: Persisted results to Supabase."
        )
    except Exception as e:
        logger.error(f"Supabase persistence failed for task {task_id}: {e}")
        state.setdefault("logs", []).append(
            f"[{datetime.now(timezone.utc).isoformat()}] Reporter: Supabase persistence failed: {e}"
        )

    return state
