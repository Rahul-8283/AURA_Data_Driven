import json
import requests
from typing import List
from app.core.config import settings
from app.models.graph import Triplet
import logging

logger = logging.getLogger(__name__)

def extract_triplets_from_text(text: str) -> List[Triplet]:
    """
    Extracts structured relationships from a chunk of text using OpenRouter (Claude 3 Haiku).
    Validates output using Pydantic Triplet model.
    """
    if not settings.OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY is not set in environment.")
        return []

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
You are an expert battery chemistry assistant. Extract specific entities and relationships from the text below.
Strictly return ONLY a valid JSON array of objects and nothing else. No markdown blocks, no conversational text.
Use ONLY these predicates: CONTAINS, CAN_BE_DOPED_WITH, EXHIBITS, SUFFERS_FROM, MITIGATES.
Subject and object labels must be one of: Element, Material, Property, DegradationMode.

Example Output:
[
  {{"subject_label": "Material", "subject": "NMC811", "predicate": "CAN_BE_DOPED_WITH", "object_label": "Element", "object": "Mg"}}
]

Text: {text}
"""
    free_models = [
        "inclusionai/ling-3.0-flash-sante:free",
        "dots-studio/dots-3-note-preview:free",
        "liquid/lfm-2.5-2.6b:free",
    ]
    raw_text = None
    last_err = None

    for model_name in free_models:
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1
        }
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            if raw_text:
                break
        except Exception as e:
            last_err = e
            logger.warning(f"OpenRouter model {model_name} extraction failed: {e}. Trying next...")

    if not raw_text:
        logger.warning(f"All OpenRouter models failed ({last_err}). Falling back to Gemini.")
        if not settings.gemini_api_key:
            logger.error("Gemini API key not set for fallback.")
            return []
            
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.gemini_api_key}"
        gemini_payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        try:
            g_resp = requests.post(gemini_url, json=gemini_payload, timeout=15)
            g_resp.raise_for_status()
            g_data = g_resp.json()
            raw_text = g_data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as gemini_e:
            logger.error(f"Gemini API fallback also failed: {gemini_e}")
            return []
            
    try:
        # Clean up in case LLM wraps in markdown
        if raw_text.startswith("```json"):
            raw_text = raw_text.split("```json")[1]
        elif raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            
        if raw_text.endswith("```"):
            raw_text = raw_text.rsplit("```", 1)[0]
            
        parsed_json = json.loads(raw_text.strip())
        triplets = []
        for item in parsed_json:
            try:
                triplet = Triplet(**item)
                triplets.append(triplet)
            except Exception as e:
                logger.warning(f"Failed to validate triplet {item}: {e}")
        return triplets
    except Exception as e:
        logger.error(f"Failed to parse or validate LLM output: {e}")
        return []
