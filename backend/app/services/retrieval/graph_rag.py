import asyncio
import logging
from app.services.retrieval.graph_search import get_graph_context
from app.services.retrieval.vector_search import get_vector_context
from app.db.chroma_client import init_literature_collection

logger = logging.getLogger(__name__)

class GraphRAGService:
    @staticmethod
    async def retrieve_context(query: str) -> str:
        """
        Orchestrates the GraphRAG pipeline by concurrently fetching semantic
        evidence from ChromaDB and structural rules from Neo4j.
        """
        # Ensure ChromaDB collection is loaded. 
        # Using to_thread because ChromaDB initializations can sometimes block.
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
        
        # Wait for both to resolve concurrently using asyncio.gather
        try:
            graph_results, vector_results = await asyncio.gather(graph_task, vector_task)
        except Exception as e:
            logger.error(f"Failed to gather RAG context concurrently: {e}")
            graph_results = "Error retrieving graph data."
            vector_results = "Error retrieving literature data."
            
        # Safely truncate vector results if it exceeds word limit to protect LLM context windows
        words = vector_results.split()
        if len(words) > 3000:
            logger.warning(f"Vector context exceeded 3000 words ({len(words)} words). Truncating.")
            vector_results = " ".join(words[:3000]) + "\n\n[...Truncated for length...]"
            
        # Format and combine into a strict template for the LLM
        combined_context = f"""
=== STRUCTURAL GRAPH RULES (Absolute Truths) ===
{graph_results}

=== LITERATURE EVIDENCE (Contextual Findings) ===
{vector_results}
"""
        return combined_context.strip()
