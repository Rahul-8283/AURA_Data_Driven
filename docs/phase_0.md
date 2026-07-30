# Phase 0: Full-Stack Scaffolding & Setup

## Part 1: Backend Setup

## 1. Objective and Scope
The goal of Phase 0 is to establish the complete backend foundation for **AURA (Autonomous Unified Research Assistant)**. By the end of this phase, the application must be able to boot up, connect to all three databases (Supabase/PostgreSQL, ChromaDB, Neo4j), and successfully initialize the Celery worker with Redis for handling asynchronous AI tasks. No UI or agent logic will be built in this phase; the focus is strictly on robust plumbing, logging, and infrastructure configuration.

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

## 7. Execution and Verification Checklist (Backend)
Before concluding Part 1, the following must be verified via terminal:
1. `redis-server` must be running locally.
2. The Celery worker must boot successfully via `celery -A app.core.celery_app worker --loglevel=info`.
3. The FastAPI server must start via `uvicorn app.main:app --reload`.
4. Hitting `POST /test-celery` should successfully dispatch a job to the Celery worker window.
5. Hitting `GET /health/db` should show `status: connected` for Neo4j and ChromaDB.

---

## Part 2: Frontend & Auth Setup

## 1. Objective and Scope
The goal of Part 2 is to build the frontend architecture, establish secure user authentication via Supabase, and create the foundational dashboard where researchers will submit their battery material requirements. By the end of this phase, a user should be able to sign up, log in, view a protected dashboard, and submit a form that successfully communicates securely with the FastAPI backend.

---

## 2. Supabase Authentication Setup (Frontend)

### 2.1 Initialization (`src/lib/supabase.ts`)
We will use the official `@supabase/supabase-js` client.
```typescript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error("Missing Supabase environment variables")
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

### 2.2 Auth Context Provider (`src/contexts/AuthContext.tsx`)
Create a React Context to manage the user session globally.
- Implement `useEffect` to listen to `supabase.auth.onAuthStateChange`.
- Export custom hook `useAuth()` exposing `user`, `session`, and `isLoading`.

### 2.3 Login & Registration UI (`src/pages/Auth/`)
- **Login Component:** Use TailwindCSS for a modern, glassmorphic design. Include email/password fields and OAuth buttons (Google/GitHub if desired).
- **Signup Component:** Standard email registration flow.
- Add `framer-motion` for smooth page transitions between Login and Signup.

---

## 3. Global State Management (Zustand)

### 3.1 Store Definition (`src/store/useResearchStore.ts`)
Create a Zustand store to handle the state of the active research task.
```typescript
import { create } from 'zustand'

interface ResearchState {
  currentTaskId: string | null;
  taskStatus: 'idle' | 'processing' | 'completed' | 'error';
  progress: number;
  logs: string[];
  setTaskId: (id: string) => void;
  updateStatus: (status: any, progress: number) => void;
  addLog: (log: string) => void;
  reset: () => void;
}

export const useResearchStore = create<ResearchState>((set) => ({
  currentTaskId: null,
  taskStatus: 'idle',
  progress: 0,
  logs: [],
  setTaskId: (id) => set({ currentTaskId: id, taskStatus: 'processing' }),
  updateStatus: (status, progress) => set({ taskStatus: status, progress }),
  addLog: (log) => set((state) => ({ logs: [...state.logs, log] })),
  reset: () => set({ currentTaskId: null, taskStatus: 'idle', progress: 0, logs: [] }),
}))
```

---

## 4. Protected Routing (`src/App.tsx`)

Implement `react-router-dom` with route guards.
- Wrap the `<Dashboard />` route in a `<ProtectedRoute>` component that checks `useAuth().session`. If null, redirect to `/login`.
- Define routes:
  - `/` -> Landing Page
  - `/login` -> Auth Page
  - `/dashboard` -> Main Application Interface
  - `/results/:taskId` -> Research Output View

---

## 5. Main Dashboard UI (`src/pages/Dashboard/`)

### 5.1 Sidebar Layout (`src/components/Layout/Sidebar.tsx`)
- Use `lucide-react` for icons (e.g., Home, History, Settings).
- Provide navigation to past research runs (fetching from Supabase database).

### 5.2 Research Input Form (`src/components/Dashboard/RequirementForm.tsx`)
This is the core interaction point.
- **Form Fields:**
  - `Base Component Type`: Dropdown (Cathode, Anode, Solid Electrolyte).
  - `Target Capacity`: Number input (mAh/g).
  - `Target Cycle Life`: Number input.
  - `Custom Instructions`: Textarea (e.g., "Must avoid Cobalt due to cost constraints").
- **Validation:** Use `react-hook-form` and `zod` to validate inputs before submission.

---

## 6. Frontend-Backend Secure Integration

### 6.1 Axios Interceptor Setup (`src/lib/api.ts`)
To securely communicate with FastAPI, we must attach the Supabase JWT token to every request.
```typescript
import axios from 'axios';
import { supabase } from './supabase';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
});

api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession();
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  return config;
});

export default api;
```

### 6.2 FastAPI JWT Validation (Backend)
- In the FastAPI backend (`app/core/security.py`), implement a dependency to decode and verify the JWT sent from the React frontend.
- Ensure the JWT is signed with the `SUPABASE_JWT_SECRET`.
- Apply this dependency to the `POST /api/v1/research/start` endpoint.

---

## 7. Execution and Verification Checklist (Frontend)
1. User can successfully sign up and log in via the React frontend.
2. The user is redirected to `/dashboard` upon successful login.
3. The JWT token is visible in local storage or memory.
4. Submitting the Research Input Form successfully triggers the `axios` POST request to the backend.
5. The backend validates the JWT and rejects unauthorized requests with a 401 error.
6. The Zustand store successfully updates to `processing` state upon receiving a dummy `task_id` from the backend.
