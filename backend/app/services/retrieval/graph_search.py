import json
import logging
import os
import re
import asyncio
import requests
from typing import List
from app.core.config import settings
from app.db.neo4j_client import neo4j_conn

logger = logging.getLogger(__name__)

SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "seed_graph.json")

def _load_seed_vocabulary() -> dict:
    """Entity names known from the ground-truth seed graph, used when the LLM is unavailable."""
    vocab = {"Element": set(), "Other": set()}
    try:
        with open(SEED_PATH, "r", encoding="utf-8") as f:
            for t in json.load(f):
                for label, name in ((t["subject_label"], t["subject"]), (t["object_label"], t["object"])):
                    vocab["Element" if label == "Element" else "Other"].add(name)
    except Exception as e:
        logger.warning(f"Could not load seed vocabulary: {e}")
    return vocab

def fallback_entities(query: str) -> List[str]:
    """Dictionary/regex entity lookup against the seed graph."""
    vocab = _load_seed_vocabulary()
    found = []
    lowered = query.lower()
    remaining = query
    for name in vocab["Other"]:
        pattern = rf"(?<![A-Za-z0-9]){re.escape(name.lower())}(?![A-Za-z0-9])"
        if re.search(pattern, lowered):
            found.append(name)
            remaining = re.sub(pattern, " ", remaining, flags=re.IGNORECASE)
    # Element symbols are case-sensitive; only read them from tokens that are whole formulas (Mg, LiNi0.8Co0.1O2)
    for token in re.findall(r"[A-Za-z0-9.]+", remaining):
        if re.fullmatch(r"(?:[A-Z][a-z]?\d*\.?\d*)+", token):
            for symbol in re.findall(r"[A-Z][a-z]?", token):
                if symbol in vocab["Element"] and symbol not in found:
                    found.append(symbol)
    return found

async def extract_entities(query: str) -> List[str]:
    """
    Uses an LLM (OpenRouter) to perform Named Entity Recognition (NER) on the query,
    extracting battery materials, elements, and degradation modes.
    """
    if not settings.OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set. Using seed-graph dictionary lookup.")
        return fallback_entities(query)

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
Identify the battery materials, elements, and degradation modes in the following query.
Return ONLY a raw JSON list of strings representing the entities. Do not include markdown or explanations.

Example Output:
["Mg", "NMC", "cation mixing"]

Query: {query}
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
            resp = await asyncio.to_thread(requests.post, url, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            if raw_text:
                break
        except Exception as e:
            last_err = e
            logger.warning(f"OpenRouter model {model_name} failed: {e}. Trying next...")

    if not raw_text:
        logger.warning(f"All OpenRouter models failed ({last_err}). Falling back to Gemini.")
        if not settings.gemini_api_key:
            logger.error("Gemini API key not set for fallback.")
            return fallback_entities(query)
            
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.gemini_api_key}"
        gemini_payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        try:
            g_resp = await asyncio.to_thread(requests.post, gemini_url, json=gemini_payload, timeout=15)
            g_resp.raise_for_status()
            g_data = g_resp.json()
            raw_text = g_data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as gemini_e:
            logger.error(f"Gemini API fallback also failed: {gemini_e}")
            return fallback_entities(query)
            
    try:
        # Clean up in case LLM wraps in markdown
        if raw_text.startswith("```json"):
            raw_text = raw_text.split("```json")[1]
        elif raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            
        if raw_text.endswith("```"):
            raw_text = raw_text.rsplit("```", 1)[0]
            
        entities = json.loads(raw_text.strip())
        if isinstance(entities, list):
            return [str(e) for e in entities]
        return []
    except Exception as e:
        logger.error(f"Failed to parse or validate LLM output: {e}")
        return []


def _run_cypher_search(tx, entities: List[str]):
    # Matches paths up to 2 hops involving the extracted entities
    # Accounts for the fact that Elements use 'symbol' while Materials use 'name'
    query = """
    MATCH (n)
    WHERE toLower(n.name) IN $entities OR toLower(n.symbol) IN $entities
    MATCH p=(n)-[*1..2]-(m)
    WITH p, [x IN nodes(p) WHERE toLower(x.name) IN $entities OR toLower(x.symbol) IN $entities] as matched
    WHERE size(matched) >= 1
    RETURN p LIMIT 20
    """
    result = tx.run(query, entities=[e.lower() for e in entities])
    return [record["p"] for record in result]


async def get_graph_context(query: str) -> str:
    """
    Orchestrates the entity extraction and Neo4j path traversal.
    Formats the paths into human-readable sentences.
    """
    entities = await extract_entities(query)
    
    if not entities:
        return "No chemical entities identified for structural search."
        
    try:
        def fetch_paths():
            with neo4j_conn.get_session() as session:
                return session.execute_read(_run_cypher_search, entities)
                
        paths = await asyncio.to_thread(fetch_paths)
    except Exception as e:
        logger.error(f"Graph traversal failed: {e}")
        return "Graph retrieval error."

    if not paths:
        return f"No established structural rules found for entities: {', '.join(entities)}."

    context_lines = []
    for path in paths:
        # Reconstruct path logically: start_node -> relationship -> end_node
        rels = path.relationships
        
        sentence_parts = []
        for rel in rels:
            start_name = rel.start_node.get("name") or rel.start_node.get("symbol") or "Unknown"
            end_name = rel.end_node.get("name") or rel.end_node.get("symbol") or "Unknown"
            rel_type = rel.type
            
            sentence_parts.append(f"{start_name} {rel_type} {end_name}")
            
        context_lines.append(" AND ".join(sentence_parts))
    
    # Deduplicate identical logical lines
    unique_lines = list(set(context_lines))
    
    formatted_context = ""
    for idx, line in enumerate(unique_lines):
        formatted_context += f"[{idx + 1}] {line}.\n"
        
    return formatted_context.strip()
