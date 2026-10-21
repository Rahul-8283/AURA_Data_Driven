# Technical Requirements Document (TRD)
**Product Name:** AURA (Autonomous Unified Research Assistant for Battery Materials Discovery)  
**Version:** 1.0  
**Architecture:** Asynchronous Multi-Agent Microservice  

---

## 1. System Architecture Overview

AURA operates on a decoupled architecture, separating the interactive UI from the heavy, long-running AI orchestration engine.

### 1.1 Technology Stack
- **Frontend:** React (Vite), TailwindCSS, Zustand (State), Recharts (Graphs), react-force-graph-2d (Graph Visualization).
- **Backend API:** FastAPI (Python).
- **AI Orchestration:** LangGraph (Multi-agent workflows).
- **Task Queue & Broker:** Celery workers backed by Redis.
- **Auth & Relational DB:** Supabase (PostgreSQL, Authentication, Buckets).
- **Knowledge Graph:** Neo4j (Nodes & Edges).
- **Vector Database:** pgvector in Supabase Postgres (`literature_chunks`, HNSW cosine index).
- **LLM Engine:** OpenRouter (OpenAI-compatible API routing).
- **Embeddings:** fastembed, computed locally (`all-MiniLM-L6-v2`, 384-dim).

---

## 2. Core Data Pipelines

### 2.1 Asynchronous Task Execution Flow
Due to the long-running nature of the Genetic Algorithm and LLM prediction loops, the system cannot operate on standard synchronous HTTP requests.
1. **Frontend Request:** React sends a `POST /api/v1/research/start` with the battery requirements.
2. **FastAPI Handling:** FastAPI receives the payload, enqueues a background task in **Celery (via Redis)**, and immediately returns a `task_id` (HTTP 202 Accepted).
3. **Task Processing:** The Celery worker picks up the task and initializes the **LangGraph** orchestrator.
4. **Polling/WebSockets:** The Frontend polls `GET /api/v1/research/status/{task_id}` (or connects via WebSockets) to get live generation updates from the Celery worker state.

### 2.2 LangGraph Multi-Agent Workflow
LangGraph manages the state of the Genetic Algorithm across multiple specialized agents:
- **Planner Agent:** Breaks down the user requirement into a mathematical fitness function.
- **Literature Agent:** Chunks battery papers, generates embeddings locally (`all-MiniLM-L6-v2`), and stores them in pgvector. Populates structural rules into Neo4j.
- **GA Mutation Agent:** Selects parent materials and applies crossover/doping/substitution rules.
- **Validation Agent (GraphRAG):** Queries pgvector and Neo4j to ensure the mutated material doesn't violate known chemical stability rules (e.g., impossible oxidation states).
- **Prediction Agent:** Constructs a prompt containing the valid mutation and relevant GraphRAG context. Sends to **OpenRouter** (e.g., Claude 3.5 Sonnet) to predict Capacity, Voltage, and Cost.
- **Report Agent:** Ranks the final population and formats the output into a structured JSON/Markdown report.

---

## 3. Database Schema & Storage

### 3.1 Supabase (PostgreSQL) - Relational Data
Used for application state, user management, and history.
- **Users Table:** Managed by Supabase Auth.
- **ResearchTasks Table:** `id`, `user_id`, `prompt`, `status` (pending, processing, completed), `created_at`.
- **SavedMaterials Table:** `id`, `user_id`, `composition`, `predicted_capacity`, `predicted_cost`, `reasoning`.

### 3.2 Neo4j - Knowledge Graph
Used for hard chemical rules and relationships.
- **Nodes:** `Element` (e.g., Lithium, Cobalt), `Material` (e.g., LCO, NMC811), `Property` (e.g., High Capacity), `DegradationMode` (e.g., Cation Mixing).
- **Edges:** `[:CONTAINS]`, `[:CAN_BE_DOPED_WITH]`, `[:SUFFERS_FROM]`, `[:PREVENTED_BY]`.

### 3.3 pgvector - Vector Storage
Used for semantic context retrieval.
- **Table:** `literature_chunks` in the Supabase project, with `embedding vector(384)`.
- **Data:** Chunked text from research papers embedded into dense vectors, with DOI and title fingerprint for de-duplication.
- **Persistence:** Supabase Postgres, so it survives restarts and is shared by the API and the worker.

---

## 4. API Endpoints (Conceptual)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/research/start` | Initiates a new battery discovery task. Returns `{ task_id: string }`. |
| `GET` | `/api/v1/research/status/{task_id}` | Returns the current state of the GA loop (e.g., `Generation 4/20`). |
| `GET` | `/api/v1/research/results/{task_id}` | Returns the final JSON payload containing the ranked materials and GraphRAG reasoning. |
| `GET` | `/api/v1/graph/nodes` | Fetches a simplified view of the Neo4j graph for rendering in `react-force-graph-2d`. |

---

## 5. Security & Environment Constraints
- **API Keys:** All OpenRouter, Hugging Face, and Supabase keys must be loaded via `.env` files and never exposed to the frontend.
- **CORS:** FastAPI must be configured to strictly accept cross-origin requests only from the deployed Vercel frontend domain.
- **Rate Limiting:** Both OpenRouter and Hugging Face API rate limits must be handled inside the Celery worker using exponential backoff to prevent task failures during heavy GraphRAG generations.
