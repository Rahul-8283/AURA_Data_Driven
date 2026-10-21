import json
import requests
from typing import List
from app.core.config import settings
from app.models.graph import Triplet
from app.services.llm.errors import LLMQuotaExceeded, LLMUnavailableError, is_daily_quota_error
import logging

logger = logging.getLogger(__name__)

def extract_triplets_from_text(text: str) -> List[Triplet]:
    """
    Extracts structured relationships from a block of text using OpenRouter, falling back to Gemini.
    Validates output using the Pydantic Triplet model.

    Raises LLMQuotaExceeded when the OpenRouter daily quota is spent and Gemini also fails, and
    LLMUnavailableError when no provider answers. An empty list therefore always means the model
    answered and found nothing, never that the call failed.
    """
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
    # OpenRouter's Free Models Router auto-selects a live free model per
    # request, avoiding hardcoded ":free" slugs that 404 once OpenRouter
    # rotates its free-tier catalog.
    payload = {
        "model": "openrouter/free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    raw_text = None
    quota_spent = False
    if settings.OPENROUTER_API_KEY:
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            if resp.status_code == 429 and is_daily_quota_error(resp.text):
                quota_spent = True
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"OpenRouter free router extraction failed ({type(e).__name__})")
    else:
        logger.warning("OPENROUTER_API_KEY is not set; using Gemini only.")

    if not raw_text:
        logger.warning("Falling back to Gemini.")
        gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        gemini_payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        try:
            if not settings.gemini_api_key:
                raise LLMUnavailableError("Gemini API key not set for fallback.")
            g_resp = requests.post(
                gemini_url, json=gemini_payload,
                headers={"x-goog-api-key": settings.gemini_api_key}, timeout=15,
            )
            g_resp.raise_for_status()
            g_data = g_resp.json()
            raw_text = g_data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as gemini_e:
            # Report the exception type only; request error text can embed the URL.
            logger.error(f"Gemini API fallback also failed ({type(gemini_e).__name__})")
            if quota_spent:
                raise LLMQuotaExceeded(
                    "OpenRouter's free-model daily quota is used up and the Gemini fallback also failed."
                ) from None
            raise LLMUnavailableError("No LLM provider could extract triplets.") from None

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
