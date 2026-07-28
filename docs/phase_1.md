# Phase 1: Project Setup & Core Infrastructure (Detailed Implementation Plan)

## 1. Objective and Scope
The goal of Phase 1 is to establish the complete backend foundation for **AURA (Autonomous Unified Research Assistant)**. By the end of this phase, the application must be able to boot up, connect to all three databases (Supabase/PostgreSQL, ChromaDB, Neo4j), and successfully initialize the Celery worker with Redis for handling asynchronous AI tasks. No UI or agent logic will be built in this phase; the focus is strictly on robust plumbing, logging, and infrastructure configuration.

---

## 2. Directory Structure Setup
Begin by establishing a scalable, modular architecture for the FastAPI application. We will strictly adhere to separation of concerns.

```text
backend/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── health.py
│   │   │   │   ├── auth.py
│   │   │   │   └── research.py
│   │   │   └── router.py
│   ├── core/
│   │   ├── config.py          # Pydantic BaseSettings for env vars
│   │   ├── security.py        # Supabase JWT validation
│   │   ├── celery_app.py      # Celery worker configuration
│   ├── db/
│   │   ├── supabase.py        # Supabase client initialization
│   │   ├── neo4j_client.py    # Neo4j driver wrapper
│   │   ├── chroma_client.py   # Persistent ChromaDB client
│   ├── models/                # SQLAlchemy ORM models (if used directly)
│   ├── schemas/               # Pydantic validation schemas (Input/Output)
│   ├── services/              # Business logic (where LangGraph will live later)
│   └── main.py                # FastAPI entry point
├── worker/
│   └── tasks.py               # Celery task definitions
├── .env                       # Environment variables
├── requirements.txt
└── README.md
```

---

## 3. Configuration Management (`app/core/config.py`)
To prevent random `os.getenv` calls scattered throughout the code, we will use `pydantic-settings` to strictly type and validate all required environment variables on startup.

### Implementation Steps:
1. Create `Settings` class inheriting from `pydantic_settings.BaseSettings`.
2. Define the following strict fields:
   - **FastAPI:** `PROJECT_NAME`, `API_V1_STR`
   - **Supabase:** `SUPABASE_URL`, `SUPABASE_KEY`
   - **ChromaDB:** `CHROMA_PERSIST_DIRECTORY` (e.g., `./chroma_data`)
   - **Neo4j:** `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`
   - **Redis/Celery:** `REDIS_URL` (e.g., `redis://localhost:6379/0`)
3. If any field is missing during startup, the application should crash immediately with a clear error message.

---

## 4. Database Clients Initialization

### 4.1 Supabase Configuration (`app/db/supabase.py`)
- Import `create_client` from the `supabase` python package.
- Initialize the client as a singleton using the config variables.
- Write a `get_supabase_client()` dependency function to be injected into FastAPI routes.
- **Goal:** Allow the backend to verify user JWTs and potentially interact with the `ResearchTasks` relational table.

### 4.2 ChromaDB Configuration (`app/db/chroma_client.py`)
- Import `chromadb`.
- Initialize `PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)`.
- It is critical to use the **PersistentClient**, not the EphemeralClient, so that battery literature embeddings are saved to the local disk.
- Write a helper function `get_chroma_collection(name: str)` that performs `get_or_create_collection`.

### 4.3 Neo4j Configuration (`app/db/neo4j_client.py`)
- Import `GraphDatabase` from the `neo4j` package.
- Build a `Neo4jConnection` class that manages the driver lifecycle (opening and closing connections).
- Write a `verify_connectivity()` method that runs a simple `RETURN 1` cypher query to ensure the database is reachable on boot.

---

## 5. Asynchronous Task Queue Setup (Celery + Redis)

Since the Genetic Algorithm will take minutes to run, it cannot block the HTTP requests.

### 5.1 Celery App Initialization (`app/core/celery_app.py`)
- Instantiate the Celery app:
  ```python
  from celery import Celery
  from app.core.config import settings
  
  celery_app = Celery(
      "aura_worker",
      broker=settings.REDIS_URL,
      backend=settings.REDIS_URL
  )
  
  # Configure serialization
  celery_app.conf.update(
      task_serializer='json',
      accept_content=['json'],
      result_serializer='json',
      timezone='UTC',
      enable_utc=True,
  )
  ```

### 5.2 Initial Task Definitions (`worker/tasks.py`)
- Create a dummy background task to verify the worker pipeline is functioning.
  ```python
  from app.core.celery_app import celery_app
  import time
  
  @celery_app.task(bind=True, name="test_dummy_task")
  def test_dummy_task(self, iterations: int):
      for i in range(iterations):
          time.sleep(1)
          # Update internal state for frontend polling
          self.update_state(state='PROGRESS', meta={'current': i, 'total': iterations})
      return {"status": "Complete", "result": f"Processed {iterations} items."}
  ```

---

## 6. FastAPI Core Integration (`app/main.py`)

### 6.1 Server Instantiation
- Update the existing `main.py` to utilize the new modular router architecture.
- Include the `APIRouter` from `app/api/v1/router.py`.
- Configure `CORSMiddleware` to strictly allow requests from the React frontend port (usually `http://localhost:5173`).

### 6.2 Health Check & Verification Endpoints (`app/api/v1/endpoints/health.py`)
Build extensive health checks to confirm infrastructure is ready before taking user traffic.
- **`GET /health`**: Returns basic up-status.
- **`GET /health/db`**: Attempts to ping Supabase, Neo4j, and ChromaDB. Returns detailed JSON status for each.
- **`POST /test-celery`**: Triggers the `test_dummy_task` and returns the `task_id`.
- **`GET /task/{task_id}`**: Retrieves the live status of the Celery task from Redis.

---

## 7. Execution and Verification Checklist
Before concluding Phase 1, the following must be verified via terminal:
1. `redis-server` must be running locally.
2. The Celery worker must boot successfully via `celery -A app.core.celery_app worker --loglevel=info`.
3. The FastAPI server must start via `uvicorn app.main:app --reload`.
4. Hitting `POST /test-celery` should successfully dispatch a job to the Celery worker window.
5. Hitting `GET /health/db` should show `status: connected` for Neo4j and ChromaDB.

*Once this phase is signed off, the backend is robust enough to begin handling actual users and GraphRAG processing in the subsequent phases.*
