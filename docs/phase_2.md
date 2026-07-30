# Phase 2: Knowledge Graph Construction (Detailed Implementation Plan)

## 1. Objective and Scope
While Phase 1 captured unstructured semantic text, Phase 2 focuses entirely on capturing **structured chemical rules**. We will extract specific entities (elements, materials, properties) and their definitive relationships from the battery literature and store them in Neo4j. This forms the rigid "graph" half of our GraphRAG engine, which is absolutely crucial for preventing the Genetic Algorithm from making physically impossible mutations that sound plausible to an LLM.

---

## 2. Neo4j Schema & Constraint Design

Before extracting data, we must define strict constraints in our Neo4j database to ensure data integrity and prevent duplicated nodes when multiple papers mention the same element.

### 2.1 Node Labels & Properties
- `Element`: The atomic building blocks (e.g., Li, Ni, Co, Mn, O, Mg, Al).
  - Properties: `symbol` (String, Unique), `name` (String), `group` (Integer).
- `Material`: The complex battery compounds (e.g., LCO, NMC811, LFP).
  - Properties: `name` (String, Unique), `class` (String: cathode/anode/electrolyte).
- `Property`: The electrochemical behaviors (e.g., High Capacity, Low Voltage, Poor Stability).
  - Properties: `name` (String, Unique).
- `DegradationMode`: Failure mechanisms (e.g., Cation Mixing, Phase Transition, Microcracking).
  - Properties: `name` (String, Unique).

### 2.2 Approved Relationship Types
To keep the graph queryable, we strictly enforce a limited ontology of edges:
- `(Material)-[:CONTAINS]->(Element)`: Defines the base stoichiometry.
- `(Material)-[:CAN_BE_DOPED_WITH]->(Element)`: Defines viable dopants.
- `(Material)-[:EXHIBITS]->(Property)`: Links a material to its observed performance.
- `(Material)-[:SUFFERS_FROM]->(DegradationMode)`: Links a material to its known flaws.
- `(Element)-[:MITIGATES]->(DegradationMode)`: Defines how an element acts as a fix.

### 2.3 Indexing Setup Script (`app/db/neo4j_setup.py`)
Write a dedicated script that executes upon server startup to create unique constraints.
```cypher
// Ensure idempotency using IF NOT EXISTS
CREATE CONSTRAINT element_symbol IF NOT EXISTS FOR (e:Element) REQUIRE e.symbol IS UNIQUE;
CREATE CONSTRAINT material_name IF NOT EXISTS FOR (m:Material) REQUIRE m.name IS UNIQUE;
CREATE CONSTRAINT property_name IF NOT EXISTS FOR (p:Property) REQUIRE p.name IS UNIQUE;
CREATE CONSTRAINT degradation_name IF NOT EXISTS FOR (d:DegradationMode) REQUIRE d.name IS UNIQUE;
```

---

## 3. Entity & Relationship Extraction Pipeline

### 3.1 LLM-Based Extraction Service (`app/services/graph/extractor.py`)
Standard NLP tools (like Spacy or NLTK) fail at parsing complex battery chemistry. We will use a lightweight, highly-instructed LLM call (via OpenRouter using a fast model like Claude 3 Haiku) to parse chunks of text and extract JSON tuples.

- **Prompt Engineering:** Instruct the LLM to identify specific entities and relationships from a text chunk and return a strict JSON array of triplets.
- Provide few-shot examples in the prompt to ensure the LLM maps terms strictly to our approved ontology.
  - *Example Text:* "We found that adding trace amounts of Magnesium to NMC811 significantly reduced cation mixing during high voltage cycling."
  - *Expected Output:*
    ```json
    [
      {"subject_label": "Material", "subject": "NMC811", "predicate": "CAN_BE_DOPED_WITH", "object_label": "Element", "object": "Mg"},
      {"subject_label": "Element", "subject": "Mg", "predicate": "MITIGATES", "object_label": "DegradationMode", "object": "Cation Mixing"},
      {"subject_label": "Material", "subject": "NMC811", "predicate": "SUFFERS_FROM", "object_label": "DegradationMode", "object": "Cation Mixing"}
    ]
    ```

### 3.2 Processing the ChromaDB Chunks
- Create a background task that iterates through the text chunks generated and stored in Phase 1.
- Pass each chunk to the LLM extraction service concurrently (batching 10 at a time).
- Validate the resulting JSON using Pydantic. If the LLM hallucinates an unapproved `predicate`, log a warning and discard the triplet.

---

## 4. Neo4j Data Ingestion

### 4.1 Cypher Merge Logic (`app/services/graph/ingestion.py`)
We must use the `MERGE` clause (not `CREATE`) to avoid duplicating nodes and edges when multiple papers mention the exact same facts.

- Build a generic, safe function to execute Cypher queries dynamically based on the validated Pydantic triplets.
```python
def merge_relationship(tx, subject_label, subject_val, predicate, object_label, object_val):
    # Using parameterized queries prevents Cypher injection and improves performance
    query = f"""
    MERGE (s:{subject_label} {{name: $subject_val}})
    MERGE (o:{object_label} {{name: $object_val}})
    MERGE (s)-[:{predicate}]->(o)
    """
    tx.run(query, subject_val=subject_val, object_val=object_val)
```
- Wrap multiple `merge_relationship` calls inside a single database transaction `session.execute_write()` to massively speed up insertion times.

---

## 5. Pre-populating Known Baselines (The Ground Truth)

Relying solely on LLM extraction from text can be noisy. The LLM might extract "Lithium is a transition metal" if a paper has a typo.
- Create a `data/seed_graph.json` file containing hardcoded, indisputable battery physics.
  - Elements: Li, Ni, Co, Mn, O, Mg, Al, Zr with their correct periodic groups.
  - Core Materials: Base compositions for LCO, NMC111, NMC532, NMC811, LFP.
  - Known Degradations: Cation mixing occurs between Ni and Li.
- Write a startup script (`app.scripts.seed_neo4j`) to ingest this seed data into Neo4j *before* extracting from literature. This guarantees a foundational ground-truth for the validation agent that cannot be overwritten by noisy extraction.

---

## 6. Execution and Verification Checklist

To successfully close out Phase 2, verify the following:
1. **Database Connection:** Verify Neo4j is running (via Docker or local install) and accessible on `bolt://localhost:7687`. Check the FASTAPI logs to ensure the driver connects on boot.
2. **Schema Verification:** Run the constraint initialization script. Open the Neo4j Browser (`http://localhost:7474`) and run `SHOW CONSTRAINTS` to ensure they are active.
3. **Seed Data:** Run the `seed_neo4j` script. Visually verify the core nodes and relationships in the Neo4j Bloom/Browser UI. Ensure elements like 'Li' and 'Ni' exist and are connected correctly.
4. **Extraction Test:** Process a small batch (e.g., 50 chunks) of the papers ingested in Phase 1 through the LLM extractor.
5. **Graph Integrity:** Query Neo4j to verify that novel edges (e.g., `[:CAN_BE_DOPED_WITH]`) are correctly attached to the core materials without creating duplicate nodes for "NMC811".
6. **Error Handling:** Ensure the pipeline does not crash if the LLM returns malformed JSON, but gracefully logs the error and moves to the next chunk.
