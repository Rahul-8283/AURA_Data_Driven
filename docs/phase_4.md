# Phase 4: Knowledge Graph Construction (Detailed Implementation Plan)

## 1. Objective and Scope
While Phase 3 captures unstructured semantic text, Phase 4 focuses on capturing **structured chemical rules**. We will extract specific entities (elements, materials, properties) and their relationships from the battery literature and store them in Neo4j. This forms the graph half of our GraphRAG engine, crucial for preventing the Genetic Algorithm from making physically impossible mutations.

---

## 2. Neo4j Schema Design

Before extracting data, we must define strict constraints in our Neo4j database to ensure data integrity.

### 2.1 Node Labels
- `Element`: (e.g., Li, Ni, Co, Mn, O, Mg). Properties: `symbol`, `name`, `group`.
- `Material`: (e.g., LCO, NMC811, LFP). Properties: `name`, `class` (cathode/anode).
- `Property`: (e.g., High Capacity, Low Voltage, Poor Stability). Properties: `name`.
- `DegradationMode`: (e.g., Cation Mixing, Phase Transition). Properties: `name`.

### 2.2 Relationship Types
- `(Material)-[:CONTAINS]->(Element)`
- `(Material)-[:CAN_BE_DOPED_WITH]->(Element)`
- `(Material)-[:EXHIBITS]->(Property)`
- `(Material)-[:SUFFERS_FROM]->(DegradationMode)`
- `(Element)-[:MITIGATES]->(DegradationMode)`

### 2.3 Indexing Setup (`app/db/neo4j_setup.py`)
Write a script that executes upon startup to create unique constraints.
```cypher
CREATE CONSTRAINT element_symbol IF NOT EXISTS FOR (e:Element) REQUIRE e.symbol IS UNIQUE;
CREATE CONSTRAINT material_name IF NOT EXISTS FOR (m:Material) REQUIRE m.name IS UNIQUE;
```

---

## 3. Entity & Relationship Extraction Pipeline

### 3.1 LLM-Based Extraction Service (`app/services/graph/extractor.py`)
Standard NLP (like Spacy) is poor at complex chemistry. We will use a lightweight prompt to an LLM via OpenRouter (e.g., GPT-4o-mini or Claude Haiku) to parse chunks of text and extract JSON tuples.

- **Prompt Design:** Instruct the LLM to identify specific entities and relationships from a text chunk and return a strict JSON array of triplets: `[{"subject": "NMC811", "predicate": "SUFFERS_FROM", "object": "Cation Mixing"}]`.

### 3.2 Processing the Chunks
- Iterate through the text chunks generated in Phase 3.
- Pass each chunk to the LLM extraction service.
- Parse the resulting JSON triplets.

---

## 4. Neo4j Data Ingestion

### 4.1 Cypher Merge Logic (`app/services/graph/ingestion.py`)
We must use `MERGE` (not `CREATE`) to avoid duplicating nodes and edges when multiple papers mention the same facts.

- Build a generic function to execute Cypher queries dynamically based on the extracted triplets.
```python
def merge_relationship(tx, subject_label, subject_val, predicate, object_label, object_val):
    query = f"""
    MERGE (s:{subject_label} {{name: $subject_val}})
    MERGE (o:{object_label} {{name: $object_val}})
    MERGE (s)-[:{predicate}]->(o)
    """
    tx.run(query, subject_val=subject_val, object_val=object_val)
```
- Implement batch transaction processing to speed up insertion.

---

## 5. Pre-populating Known Baselines
Relying solely on LLM extraction from text can be noisy.
- Create a `seed_data.json` file containing hardcoded, indisputable battery physics (e.g., Lithium is Group 1, NMC contains Ni/Mn/Co, Cation mixing occurs between Ni and Li).
- Write a startup script to ingest this seed data into Neo4j before extracting from literature. This guarantees a foundational ground-truth for the validation agent.

---

## 6. Execution and Verification Checklist
1. Verify Neo4j is running (via Docker or local install) and accessible on `bolt://localhost:7687`.
2. Run the constraint initialization script and verify in the Neo4j Browser that constraints exist.
3. Run the seed data script and visually verify the core nodes and relationships in the Neo4j Bloom/Browser UI.
4. Process 5 sample battery papers through the LLM extractor and verify that novel edges (e.g., `[:CAN_BE_DOPED_WITH]`) are correctly attached to the core materials.
