import asyncio
import logging
import time
import requests
from app.core.config import settings
from app.services.retrieval.graph_search import get_graph_context
from app.services.retrieval.vector_search import get_vector_context
from app.db.chroma_client import init_literature_collection

logger = logging.getLogger(__name__)

RAG_FORMATTING_PROMPT = """
You are a materials science AI assistant specialized in battery research.
Your goal is to answer the user's question: "{query}" using the provided context.

Context:
{combined_context}

Guidelines:
1. Synthesize the findings from the structural graph rules and literature database into a single, cohesive, professional response.
2. Do NOT use headers like "=== STRUCTURAL GRAPH RULES ===" or "=== LITERATURE EVIDENCE ===". 
3. Reformat raw relations and text snippets into natural, fluent scientific explanations.
4. Keep the output extremely clean, readable, and professional. Start answering directly.
"""

def reformat_with_llm(query: str, combined_context: str) -> str:
    prompt = RAG_FORMATTING_PROMPT.format(query=query, combined_context=combined_context)
    
    # Try OpenRouter Free Models
    if settings.OPENROUTER_API_KEY:
        free_models = [
            "inclusionai/ling-3.0-flash-sante:free",
            "dots-studio/dots-3-note-preview:free",
            "liquid/lfm-2.5-2.6b:free",
        ]
        for model_name in free_models:
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2
                    },
                    timeout=15
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"].strip()
                if content:
                    return content
            except Exception as e:
                logger.warning(f"OpenRouter model {model_name} formatting failed: {e}. Trying next...")
            
    # Try Gemini fallback
    if settings.gemini_api_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.gemini_api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            response = requests.post(url, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            logger.error(f"Gemini formatting failed: {e}")
            
    # Return raw combined context if all LLM formatting fails
    return combined_context

class GraphRAGService:
    @staticmethod
    async def retrieve_context(query: str, summarize: bool = False) -> str:
        """
        Orchestrates the GraphRAG pipeline by concurrently fetching semantic
        evidence from ChromaDB and structural rules from Neo4j, then processes
        the fused, section-demarcated context. With summarize=True the context is
        rewritten by an LLM into prose (used by the chat endpoint only).
        """
        started = time.perf_counter()
        # Ensure ChromaDB collection is loaded. 
        try:
            collection = await asyncio.to_thread(init_literature_collection)
        except Exception as e:
            logger.error(f"Failed to load Chroma collection: {e}")
            collection = None
        
        # Fire both I/O bound database queries simultaneously
        graph_task = get_graph_context(query)
        
        if collection:
            vector_task = get_vector_context(collection, query, n_results=5)
        else:
            async def fallback_vector():
                return "Error retrieving literature data (ChromaDB connection failed)."
            vector_task = fallback_vector()
        
        # Wait for both to resolve concurrently
        try:
            graph_results, vector_results = await asyncio.gather(graph_task, vector_task)
        except Exception as e:
            logger.error(f"Failed to gather RAG context concurrently: {e}")
            graph_results = "Error retrieving graph data."
            vector_results = "Error retrieving literature data."
            
        # Safely truncate vector results
        words = vector_results.split()
        if len(words) > 3000:
            logger.warning(f"Vector context exceeded 3000 words ({len(words)} words). Truncating.")
            vector_results = " ".join(words[:3000]) + "\n\n[...Truncated for length...]"
            
        combined_context = f"""
=== STRUCTURAL GRAPH RULES (Absolute Truths) ===
{graph_results}

=== LITERATURE EVIDENCE (Contextual Findings) ===
{vector_results}
"""
        combined_context = combined_context.strip()
        logger.info(f"GraphRAG retrieval took {time.perf_counter() - started:.2f}s")
        if not summarize:
            return combined_context
        return await asyncio.to_thread(reformat_with_llm, query, combined_context)
