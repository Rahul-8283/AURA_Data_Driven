import json
import requests
from typing import List
from app.core.config import settings
from app.models.graph import Triplet
import logging

logger = logging.getLogger(__name__)

def extract_triplets_from_text(text: str) -> List[Triplet]:
    """
    Extracts structured relationships from a chunk of text using Gemini API.
    Validates output using Pydantic Triplet model.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.gemini_api_key}"
    
    prompt = f"""
You are an expert battery chemistry assistant. Extract specific entities and relationships from the text below.
Strictly adhere to this JSON format and use ONLY these predicates: CONTAINS, CAN_BE_DOPED_WITH, EXHIBITS, SUFFERS_FROM, MITIGATES.
Subject and object labels must be one of: Element, Material, Property, DegradationMode.

Example Output:
[
  {{"subject_label": "Material", "subject": "NMC811", "predicate": "CAN_BE_DOPED_WITH", "object_label": "Element", "object": "Mg"}}
]

Text: {text}
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json"
        }
    }
    
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
        
        parsed_json = json.loads(raw_text)
        triplets = []
        for item in parsed_json:
            try:
                triplet = Triplet(**item)
                triplets.append(triplet)
            except Exception as e:
                logger.warning(f"Failed to validate triplet {item}: {e}")
        return triplets
    except Exception as e:
        logger.error(f"Gemini API extraction failed: {e}")
        return []
