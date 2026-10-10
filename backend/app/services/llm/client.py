import asyncio
import json
import requests
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

def get_client() -> AsyncOpenAI:
    # Built per call: each Celery task runs its own event loop, so a shared client would hold a closed loop.
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY or "missing-key",
    )

class PredictionResult(BaseModel):
    specific_capacity: float = Field(..., description="Estimated capacity in mAh/g")
    voltage: float = Field(..., description="Nominal voltage in V")
    cycle_life: int = Field(..., description="Estimated cycles to 80% retention")
    cost_estimate_usd_kg: float = Field(..., description="Estimated material cost per kg")
    reasoning: str = Field(..., description="A 2-sentence chemical explanation for these numbers based ONLY on the context.")

SYSTEM_PROMPT = """You are an expert computational battery chemist. You do not hallucinate.
Estimate the specific capacity (mAh/g), nominal voltage (V), cycle life, and cost impact of the provided battery material composition.
You MUST base your prediction primarily on the provided GraphRAG literature context. If the context states that Al doping reduces capacity but increases thermal stability, your numerical predictions MUST reflect a drop in capacity and a rise in cycle life compared to standard baselines.
"""

MAX_BATCH_CONTEXT_CHARS = 1000

async def call_openrouter_free(messages: list[dict], temperature: float) -> str | None:
    """Single call to OpenRouter's Free Models Router (model="openrouter/free"),
    which auto-selects a live free model per request instead of a hardcoded
    slug that 404s once OpenRouter rotates its free-tier catalog.

    Uses `async with` so the underlying httpx client is always closed instead
    of being garbage-collected later on a possibly-closed event loop (which
    surfaced as 'AsyncHttpxClientWrapper' object has no attribute '_state').
    """
    try:
        async with get_client() as client:
            response = await client.chat.completions.create(
                model="openrouter/free",
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content
    except Exception as e:
        print(f"OpenRouter free-router call failed: {e}")
        return None

async def _generate_text(system: str, prompt: str, temperature: float, json_mode: bool = False) -> str:
    content = await call_openrouter_free(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
    )
    if content:
        return content

    print("OpenRouter free router failed. Falling back to Gemini 2.5 Flash...")
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.gemini_api_key}"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": prompt}]}],
    }
    if json_mode:
        payload["generationConfig"] = {"responseMimeType": "application/json"}
    g_resp = await asyncio.to_thread(requests.post, gemini_url, json=payload, timeout=30)
    g_resp.raise_for_status()
    return g_resp.json()["candidates"][0]["content"]["parts"][0]["text"]

def clean_json_string(raw: str) -> str:
    cleaned = raw.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0]
    return cleaned.strip()

def normalize_prediction_dict(data: dict) -> dict:
    normalized = {}
    normalized["specific_capacity"] = float(
        data.get("specific_capacity") or data.get("specific_capacity_mAh_g") or data.get("capacity") or 200.0
    )
    normalized["voltage"] = float(
        data.get("voltage") or data.get("nominal_voltage_V") or data.get("nominal_voltage") or 3.8
    )
    normalized["cycle_life"] = int(
        data.get("cycle_life") or data.get("cycle_life_cycles") or data.get("cycles") or 1000
    )
    cost = data.get("cost_estimate_usd_kg") or data.get("cost") or data.get("cost_estimate") or data.get("cost_usd_kg")
    if isinstance(cost, (int, float)):
        normalized["cost_estimate_usd_kg"] = float(cost)
    else:
        normalized["cost_estimate_usd_kg"] = 25.0

    normalized["reasoning"] = str(
        data.get("reasoning") or data.get("cost_impact") or data.get("explanation") or "Predicted based on material composition and literature context."
    )
    return normalized

def _truncate_context(context: str) -> str:
    if len(context) <= MAX_BATCH_CONTEXT_CHARS:
        return context
    return context[:MAX_BATCH_CONTEXT_CHARS] + " [...]"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def predict_properties_batch_async(items: list[tuple[str, str]]) -> dict[str, PredictionResult]:
    """One LLM call predicting properties for many (composition, context) pairs.
    Results are keyed by the composition string; the model answers by index so
    it cannot drop or rename a material. Indexes it omits are simply absent."""
    blocks = "\n\n".join(
        f"### Material index {i}\nComposition: {composition}\nContext:\n{_truncate_context(context)}"
        for i, (composition, context) in enumerate(items)
    )
    prompt = f"""{blocks}

Predict the properties of EVERY material above. Return ONLY a valid JSON array with one object per material:
[
  {{"index": 0, "specific_capacity": 200.0, "voltage": 3.8, "cycle_life": 1000, "cost_estimate_usd_kg": 25.0, "reasoning": "Chemical rationale based on context."}}
]
"""
    content = await _generate_text(SYSTEM_PROMPT, prompt, temperature=0.1, json_mode=True)

    try:
        parsed = json.loads(clean_json_string(content))
        results: dict[str, PredictionResult] = {}
        for item in parsed:
            index = int(item["index"])
            if not 0 <= index < len(items):
                continue
            composition = items[index][0]
            results[composition] = PredictionResult(**normalize_prediction_dict(item))
        return results
    except Exception as e:
        raise ValueError(f"Failed to parse LLM batch response: {content}, Error: {e}")

SUMMARY_SYSTEM_PROMPT = """You are writing the executive summary for a battery material discovery report.
Review the user's initial request and the top 5 materials the AI discovered.
Write a highly professional, 3-paragraph summary explaining the evolutionary path taken, why these specific
materials outcompete standard baselines, and what their primary trade-offs are based on their predicted properties.
Write plain prose only, no markdown headers or bullet points."""

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def summarize_report_async(user_prompt: str, top_candidates: list[dict]) -> str:
    candidates_text = "\n".join(
        f"- {c.get('composition')}: capacity={c.get('specific_capacity')} mAh/g, "
        f"voltage={c.get('voltage')} V, cycle_life={c.get('cycle_life')}, "
        f"cost=${c.get('cost_estimate_usd_kg')}/kg, fitness={c.get('fitness')}, "
        f"reasoning={c.get('reasoning')}"
        for c in top_candidates
    )
    prompt = f"""User's original request: {user_prompt}

Top 5 discovered materials:
{candidates_text}

Write the 3-paragraph executive summary now."""

    content = await _generate_text(SUMMARY_SYSTEM_PROMPT, prompt, temperature=0.3)

    if not content:
        raise ValueError("No executive summary content returned from any LLM provider.")

    return content.strip()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def validate_materials_batch_async(items: list[tuple[str, str]]) -> dict[str, bool]:
    """Batched chemical validity check. Returns composition -> is_valid. Indexes the
    model omits or cannot parse are absent; the caller treats them as valid so an
    unparseable answer never blocks the GA."""
    blocks = "\n\n".join(
        f"### Candidate index {i}\nComposition: {composition}\nContext:\n{_truncate_context(context)}"
        for i, (composition, context) in enumerate(items)
    )
    prompt = f"""{blocks}

For EACH candidate above, decide whether it is structurally stable and valid according to fundamental valence rules.
Return ONLY a valid JSON array with one object per candidate:
[
  {{"index": 0, "is_valid": true}}
]
"""
    content = await _generate_text(
        "You are an expert computational battery chemist. Return strictly JSON.",
        prompt,
        temperature=0.0,
        json_mode=True,
    )

    try:
        parsed = json.loads(clean_json_string(content))
        verdicts: dict[str, bool] = {}
        for item in parsed:
            index = int(item["index"])
            if 0 <= index < len(items):
                verdicts[items[index][0]] = bool(item.get("is_valid", True))
        return verdicts
    except Exception:
        return {}
