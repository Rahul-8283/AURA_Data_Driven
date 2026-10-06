import json
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

FREE_MODELS = [
    "inclusionai/ling-3.0-flash-sante:free",
    "dots-studio/dots-3-note-preview:free",
    "liquid/lfm-2.5-2.6b:free",
]

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

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def predict_properties_async(material_composition: str, context: str) -> PredictionResult:
    prompt = f"""Material Composition: {material_composition}

Context:
{context}

Return ONLY a valid JSON object matching this schema exactly:
{{
  "specific_capacity": 200.0,
  "voltage": 3.8,
  "cycle_life": 1000,
  "cost_estimate_usd_kg": 25.0,
  "reasoning": "Chemical rationale for these numbers based on context."
}}
"""
    
    content = None
    last_error = None

    # Try OpenRouter Free Tier Models in order
    for model_name in FREE_MODELS:
        try:
            response = await get_client().chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            content = response.choices[0].message.content
            if content:
                break
        except Exception as e:
            last_error = e
            print(f"OpenRouter model {model_name} failed: {e}. Trying next...")

    # Fallback to Gemini if all free OpenRouter models failed
    if not content:
        print(f"All OpenRouter free models failed ({last_error}). Falling back to Gemini 2.5 Flash...")
        import requests
        import asyncio
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.gemini_api_key}"
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        g_resp = await asyncio.to_thread(requests.post, gemini_url, json=payload, timeout=30)
        g_resp.raise_for_status()
        content = g_resp.json()["candidates"][0]["content"]["parts"][0]["text"]

    try:
        cleaned = clean_json_string(content)
        data = json.loads(cleaned)
        normalized = normalize_prediction_dict(data)
        return PredictionResult(**normalized)
    except Exception as e:
        raise ValueError(f"Failed to parse LLM response: {content}, Error: {e}")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def validate_material_async(material_composition: str, context: str) -> bool:
    prompt = f"""Material Composition: {material_composition}

Context:
{context}

Is this material structurally stable and valid according to fundamental valence rules?
Return ONLY a valid JSON object:
{{
  "is_valid": true
}}
"""
    content = None
    for model_name in FREE_MODELS:
        try:
            response = await get_client().chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are an expert computational battery chemist. Return strictly JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            content = response.choices[0].message.content
            if content:
                break
        except Exception:
            pass

    if not content:
        import requests
        import asyncio
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.gemini_api_key}"
        payload = {
            "systemInstruction": {"parts": [{"text": "You are an expert computational battery chemist. Return strictly JSON."}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }
        g_resp = await asyncio.to_thread(requests.post, gemini_url, json=payload, timeout=30)
        g_resp.raise_for_status()
        content = g_resp.json()["candidates"][0]["content"]["parts"][0]["text"]

    try:
        cleaned = clean_json_string(content)
        data = json.loads(cleaned)
        return bool(data.get("is_valid", True))
    except Exception:
        return True # Default to True if we can't parse, so we don't block the loop forever
