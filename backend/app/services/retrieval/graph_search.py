import json
import logging
import asyncio
import requests
from typing import List
from app.core.config import settings
from app.db.neo4j_client import neo4j_conn

logger = logging.getLogger(__name__)

async def extract_entities(query: str) -> List[str]:
    """
    Uses an LLM (OpenRouter) to perform Named Entity Recognition (NER) on the query,
    extracting battery materials, elements, and degradation modes.
    """
    if not settings.OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set. Cannot extract entities for graph search.")
        return []

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
    payload = {
        "model": "anthropic/claude-3-haiku",
        "messages": [{"role": "user", "content": prompt}],
    }
    
    try:
        # Run synchronous requests in a thread pool so it doesn't block the async loop
        resp = await asyncio.to_thread(requests.post, url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        raw_text = data["choices"][0]["message"]["content"]
        
        # Clean up in case Claude wraps in markdown
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
        logger.error(f"Failed to extract entities from query: {e}")
        return []


def _run_cypher_search(tx, entities: List[str]):
    # Matches paths up to 2 hops involving the extracted entities
    # Accounts for the fact that Elements use 'symbol' while Materials use 'name'
    query = """
    MATCH (n)
    WHERE n.name IN $entities OR n.symbol IN $entities
    MATCH p=(n)-[*1..2]-(m)
    WITH p, [x IN nodes(p) WHERE x.name IN $entities OR x.symbol IN $entities] as matched
    WHERE size(matched) >= 1
    RETURN p LIMIT 20
    """
    result = tx.run(query, entities=entities)
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
