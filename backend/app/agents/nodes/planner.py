import logging
import json
import requests
from datetime import datetime
from app.agents.state import ResearchState
from app.core.config import settings

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
    """Attempt to call OpenRouter using free models."""
    api_key = settings.OPENROUTER_API_KEY or getattr(settings, "openrouter_api_key", None)
    if not api_key:
        raise ValueError("OpenRouter API key missing")
        
    free_models = [
        "inclusionai/ling-3.0-flash-sante:free",
        "dots-studio/dots-3-note-preview:free",
        "liquid/lfm-2.5-2.6b:free",
    ]
    last_err = None
    for model_name in free_models:
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1
                },
                timeout=15
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return parse_llm_json(content)
        except Exception as e:
            last_err = e
            logger.warning(f"Planner OpenRouter model {model_name} failed: {e}. Trying next...")
            
    raise ValueError(f"All OpenRouter free models failed: {last_err}")

def call_gemini_fallback(prompt: str) -> dict:
    """Fallback to Gemini 2.5 Flash."""
    if not settings.gemini_api_key:
        raise ValueError("Gemini API key missing")
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.gemini_api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    response = requests.post(url, json=payload, timeout=15)
    response.raise_for_status()
    
    data = response.json()
    if 'candidates' in data and data['candidates']:
        content = data['candidates'][0]['content']['parts'][0]['text']
        return parse_llm_json(content)
    else:
        raise ValueError("No candidates found in Gemini response.")

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
    state["max_generations"] = 20
    
    # Generate Dummy Seed Materials
    base_class = state["base_material_class"] or "Material"
    state["current_population"] = [
        {"id": f"seed_{i}", "composition": f"Baseline_{base_class}_Var{i}", "fitness": 0.0}
        for i in range(10)
    ]
    
    state["logs"].append(f"[{datetime.utcnow().isoformat()}] Population seeded with 10 variations. Ready for generation 0.")
    
    return state
