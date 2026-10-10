import logging
import json
import requests
from datetime import datetime
from app.agents.state import ResearchState
from app.core.config import settings
from app.services.ga.material import BatteryMaterial
from app.services.llm.errors import LLMQuotaExceeded, is_daily_quota_error

logger = logging.getLogger(__name__)

PLANNER_PROMPT = """
You are the chief planning agent for an autonomous battery material discovery system.
The user will provide a high-level goal. You must extract the exact numerical targets.

Extract:
1. "target_properties": numeric targets for specific capacity, voltage, cycle life, and cost. (e.g., {{"capacity_gt": 250, "cost_lt": 50, "voltage_gt": 3.7}}). Use keys ending in _gt or _lt where appropriate.
2. "base_material_class": The family of material (e.g., "NMC_Cathode", "Solid_State_Electrolyte").
3. "excluded_elements": List of elements explicitly excluded (e.g., ["Co"] to force cobalt-free).

User Prompt: {user_prompt}

You MUST return ONLY valid JSON matching this schema exactly. No other text, no markdown block.
{{
  "target_properties": {{}},
  "base_material_class": "",
  "excluded_elements": []
}}
"""

def parse_llm_json(response_text: str) -> dict:
    """Helper to clean and parse LLM JSON responses."""
    cleaned = response_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return json.loads(cleaned.strip())

def call_openrouter(prompt: str) -> dict:
    """Call OpenRouter via its Free Models Router, which auto-selects a live
    free model per request instead of a hardcoded slug that can 404 once
    OpenRouter rotates its free-tier catalog."""
    api_key = settings.OPENROUTER_API_KEY or getattr(settings, "openrouter_api_key", None)
    if not api_key:
        raise ValueError("OpenRouter API key missing")

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openrouter/free",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        },
        timeout=15
    )
    if response.status_code == 429 and is_daily_quota_error(response.text):
        raise LLMQuotaExceeded("OpenRouter free-model daily quota exhausted.")
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return parse_llm_json(content)

def call_gemini_fallback(prompt: str) -> dict:
    """Fallback to Gemini 2.5 Flash."""
    if not settings.gemini_api_key:
        raise ValueError("Gemini API key missing")
        
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    response = requests.post(url, json=payload, headers={"x-goog-api-key": settings.gemini_api_key}, timeout=15)
    response.raise_for_status()
    
    data = response.json()
    if 'candidates' in data and data['candidates']:
        content = data['candidates'][0]['content']['parts'][0]['text']
        return parse_llm_json(content)
    else:
        raise ValueError("No candidates found in Gemini response.")

SEED_FORMULAS = [
    "LiNi0.334Co0.333Mn0.333O2",  # NMC111
    "LiNi0.5Co0.2Mn0.3O2",        # NMC532
    "LiNi0.6Co0.2Mn0.2O2",        # NMC622
    "LiNi0.8Co0.1Mn0.1O2",        # NMC811
    "LiNi0.5Mn0.5O2",             # Co-free
    "LiNi0.8Mn0.1Al0.1O2",        # Co-free
]
def build_seed_population(excluded_elements: list) -> list:
    """Seed the GA with baseline layered oxides that contain no excluded element."""
    excluded = {e.strip().capitalize() for e in excluded_elements}
    allowed = [
        f for f in SEED_FORMULAS
        if not excluded & set(BatteryMaterial.parse_string_to_dict(f))
    ] or ["LiNi0.5Mn0.5O2"]
    return [
        {"id": f"seed_{i}", "composition": allowed[i % len(allowed)], "fitness": 0.0}
        for i in range(settings.GA_SEED_POPULATION)
    ]

def planner_node(state: ResearchState) -> ResearchState:
    """
    Planner Node:
    Translates user prompt into rigid numerical constraints and initializes GA loop.
    """
    prompt = PLANNER_PROMPT.format(user_prompt=state["user_prompt"])
    
    try:
        # Try OpenRouter First
        parsed_data = call_openrouter(prompt)
        state["logs"].append(f"[{datetime.utcnow().isoformat()}] Planner successfully extracted constraints using OpenRouter.")
    except Exception as e:
        logger.warning(f"OpenRouter extraction failed: {e}. Falling back to Gemini.")
        try:
            parsed_data = call_gemini_fallback(prompt)
            state["logs"].append(f"[{datetime.utcnow().isoformat()}] Planner successfully extracted constraints using Gemini Fallback.")
        except Exception as gemini_err:
            logger.error(f"Gemini Fallback failed: {gemini_err}")
            if isinstance(e, LLMQuotaExceeded):
                raise LLMQuotaExceeded(
                    "OpenRouter's free-model daily quota is used up and the Gemini fallback also failed. "
                    "Wait for the daily reset at 00:00 UTC or add OpenRouter credits."
                ) from None
            state["logs"].append(f"[{datetime.utcnow().isoformat()}] ERROR: All LLM parsers failed. Proceeding with empty constraints.")
            parsed_data = {
                "target_properties": {},
                "base_material_class": "Unknown",
                "excluded_elements": []
            }
            
    # Update state with parsed data
    state["target_properties"] = parsed_data.get("target_properties", {})
    state["base_material_class"] = parsed_data.get("base_material_class", "")
    state["excluded_elements"] = parsed_data.get("excluded_elements", [])
    
    # Initialize GA Variables
    state["current_generation"] = 0
    state["max_generations"] = settings.GA_GENERATIONS
    
    state["current_population"] = build_seed_population(state["excluded_elements"])

    state["logs"].append(f"[{datetime.utcnow().isoformat()}] Population seeded with {len(state['current_population'])} baseline materials. Ready for generation 0.")
    
    return state
