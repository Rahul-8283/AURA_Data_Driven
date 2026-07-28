# Phase 5: GraphRAG Engine Integration (Detailed Implementation Plan)

## 1. Objective and Scope
Phase 5 is where the magic happens. We will fuse the semantic, unstructured data from ChromaDB (Phase 3) with the structural, hard-rule data from Neo4j (Phase 4). The resulting **GraphRAG Engine** will be the central source of truth for the Genetic Algorithm to validate its mutations and for the LLM to base its property predictions on.

---

## 2. Graph Retrieval Logic (`app/services/retrieval/graph_search.py`)

### 2.1 Entity Extraction from Query
When a validation query comes in (e.g., *"Is Mg doping effective for NMC cathodes?"*), we first need to extract the target entities from the query to search Neo4j.
- Use a lightweight LLM call or simple regex to extract the entities: `["Mg", "NMC"]`.

### 2.2 Cypher Graph Traversal
Write a function that takes these entities and pulls a subgraph of their relationships.
- **1-Hop & 2-Hop Search:**
```cypher
MATCH (n)
WHERE n.name IN $entities
MATCH p=(n)-[*1..2]-(m)
RETURN p LIMIT 50
```
- Parse the resulting Neo4j paths into readable text sentences (e.g., *"NMC CAN_BE_DOPED_WITH Mg. Mg MITIGATES Cation Mixing."*).

---

## 3. Vector Retrieval Logic (`app/services/retrieval/vector_search.py`)
- Reuse the function built in Phase 3.
- Take the exact same user query and run a cosine similarity search against ChromaDB to return the top 5 most relevant text chunks (e.g., paragraphs from papers detailing specific Mg doping experiments).

---

## 4. Context Aggregation & Fusion (`app/services/retrieval/graph_rag.py`)

### 4.1 The Fusion Engine
Create a unified `GraphRAGService` class that orchestrates both retrievers concurrently (using `asyncio.gather` for speed).

```python
async def retrieve_context(query: str):
    # Run both searches in parallel
    graph_context_task = get_graph_context(query)
    vector_context_task = get_vector_context(query)
    
    graph_results, vector_results = await asyncio.gather(graph_context_task, vector_context_task)
    
    # Format and combine
    combined_context = f"""
    --- STRUCTURAL RULES (From Knowledge Graph) ---
    {graph_results}
    
    --- LITERATURE EVIDENCE (From Vector DB) ---
    {vector_results}
    """
    return combined_context
```

### 4.2 Deduplication and Re-ranking (Optional but Recommended)
- If the context window gets too large, implement a basic reranker or deduplicator to remove overlapping information between the graph sentences and vector chunks.

---

## 5. Building the Validation API (`app/api/v1/endpoints/rag.py`)

To make the GraphRAG usable by the future LangGraph agents, expose it as an internal service or a REST endpoint (for testing).
- Create a `POST /api/v1/rag/query` endpoint that takes a prompt and returns the fused context.

---

## 6. Execution and Verification Checklist
1. Formulate a complex chemical question: *"What happens to the thermal stability of LCO when doped with Aluminum?"*
2. Execute the `retrieve_context` function.
3. Verify that the output clearly contains:
   - **Graph context:** `LCO CAN_BE_DOPED_WITH Al.`
   - **Vector context:** Paragraphs from papers discussing Al-doped LiCoO2 thermal properties.
4. Verify that the execution time is under 2 seconds (critical for looping inside a Genetic Algorithm).
