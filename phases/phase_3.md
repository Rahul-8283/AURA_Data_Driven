# Phase 3: GraphRAG Engine Integration (Detailed Implementation Plan)

## 1. Objective and Scope
Phase 3 is the critical integration step where the entire retrieval architecture comes together. We will build the **GraphRAG Engine**, a specialized service that fuses the semantic, unstructured contextual data from ChromaDB (built in Phase 1) with the structural, hard-rule factual data from Neo4j (built in Phase 2). This hybrid engine acts as the central source of truth for the Genetic Algorithm to validate its mutations and for the LLM to base its property predictions on later in the pipeline.

---

## 2. Graph Retrieval Logic (`app/services/retrieval/graph_search.py`)

### 2.1 Entity Extraction from Query
When a validation or context query comes in (e.g., *"Is Mg doping effective for NMC cathodes to prevent cation mixing?"*), we cannot just throw this string into Neo4j. We must extract the target entities first.
- Utilize a lightweight, fast LLM call (e.g., Claude Haiku or GPT-4o-mini) with a prompt strictly designed for Named Entity Recognition (NER).
- **Prompt Logic:** "Identify the battery materials, elements, and degradation modes in the following query. Return a JSON list of strings."
- Extract entities: `["Mg", "NMC", "cation mixing"]`.
- Implement a fallback regex or dictionary lookup against the `seed_graph.json` elements if the LLM call fails or times out.

### 2.2 Cypher Graph Traversal
Write a Python function that takes these extracted entities and pulls a highly relevant subgraph of their relationships.
- **Variable-Hop Search:** We want to find how these entities relate to each other, even if they aren't directly connected (e.g., finding the path from Mg to Cation Mixing).
```cypher
// Cypher query to find paths connecting the extracted entities
MATCH (n)
WHERE n.name IN $entities
MATCH p=(n)-[*1..2]-(m)
// Filter out excessively dense hub nodes if necessary
WITH p, [x in nodes(p) WHERE x.name IN $entities] as matched
WHERE size(matched) >= 1
RETURN p LIMIT 50
```
- **Path Serialization:** The raw Neo4j JSON response is unreadable to an LLM. Implement a parser that converts the Cypher paths into readable text sentences (e.g., *"NMC CAN_BE_DOPED_WITH Mg. Mg MITIGATES Cation Mixing."*).

---

## 3. Vector Retrieval Logic (`app/services/retrieval/vector_search.py`)

### 3.1 Unstructured Context Fetching
- Reuse the `search_literature` function built in Phase 1.
- Take the exact same raw user query and run a cosine similarity search against the ChromaDB `battery_literature` collection.
- Request the top 5 to 7 most relevant text chunks (e.g., paragraphs from papers detailing specific Mg doping experiments).
- Extract the metadata (Paper Title, DOI) so that we can provide citations in the final output.

---

## 4. Context Aggregation & Fusion (`app/services/retrieval/graph_rag.py`)

### 4.1 The Concurrent Fusion Engine
Because retrieval speed is critical when running inside a multi-generation Genetic Algorithm loop, we cannot run these searches sequentially. Create a unified `GraphRAGService` class that orchestrates both retrievers concurrently.

```python
import asyncio
from app.services.retrieval.graph_search import get_graph_context
from app.services.retrieval.vector_search import get_vector_context

class GraphRAGService:
    @staticmethod
    async def retrieve_context(query: str):
        # Fire both I/O bound database queries simultaneously
        graph_task = get_graph_context(query)
        vector_task = get_vector_context(query)
        
        # Wait for both to resolve
        graph_results, vector_results = await asyncio.gather(graph_task, vector_task)
        
        # Format and combine into a strict template
        combined_context = f"""
        === STRUCTURAL GRAPH RULES (Absolute Truths) ===
        {graph_results}
        
        === LITERATURE EVIDENCE (Contextual Findings) ===
        {vector_results}
        """
        return combined_context
```

### 4.2 Deduplication and Re-ranking (Optimization)
- If the context window gets too large, implement a basic text deduplicator. If a sentence in the vector DB exactly matches the logic of a graph rule, keep the graph rule (as it is more concise) and trim the vector context.
- Implement a maximum token limit checker before returning the `combined_context` to prevent blowing up the downstream OpenRouter API limits.

---

## 5. Building the Internal RAG API (`app/api/v1/endpoints/rag.py`)

To make the GraphRAG usable by the frontend dashboard (for manual queries) and testable via Postman/cURL, expose it as a REST endpoint.
- Create a `POST /api/v1/rag/query` endpoint that accepts a `{"prompt": "string"}` payload.
- Return a structured JSON response containing the fused context, the specific Neo4j paths triggered, and the metadata citations from ChromaDB.

---

## 6. Execution and Verification Checklist

To sign off on Phase 3, you must thoroughly verify the hybrid engine:
1. **Unit Testing:** Write a Pytest that mocks the ChromaDB and Neo4j responses to ensure the `retrieve_context` aggregator correctly formats the outputs.
2. **Live Query Test:** Use the Swagger UI (`/docs`) to hit the `POST /api/v1/rag/query` endpoint with a complex chemical question: *"What happens to the thermal stability of LCO when doped with Aluminum?"*
3. **Response Verification:** Check the JSON response payload. It MUST clearly demarcate the structured Graph output (e.g., `LCO CAN_BE_DOPED_WITH Al`) from the unstructured Vector output (e.g., paper paragraphs discussing Al-doped LiCoO2).
4. **Performance Profiling:** Add time-tracking logs to `retrieve_context`. Ensure that thanks to `asyncio.gather`, the entire function executes and returns data in under 1.5 seconds. This speed is non-negotiable for the Genetic Algorithm.
5. **Citation Check:** Verify that the vector chunks returned include the attached DOI/Title metadata so the frontend can display proper evidence links.
