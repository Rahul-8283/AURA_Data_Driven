# AURA – Autonomous Unified Research Assistant for Battery Materials Discovery

Multi-agent system that evolves battery cathode/anode/electrolyte compositions: a deterministic Genetic Algorithm proposes candidates, GraphRAG (Neo4j + ChromaDB) validates chemistry, an LLM predicts properties, and a report ranks the results. Specs live in `docs/` (PRD, TRD, GA) and the build plan in `phases/phase_0.md` – `phase_8.md`. Read the relevant phase file before implementing or changing a stage.

## Stack
- **Frontend** (`frontend/`): React 19 + Vite + TypeScript, TailwindCSS v4, Zustand, Recharts, react-force-graph-2d, Framer Motion, Supabase JS (auth).
- **Backend** (`backend/`): FastAPI, LangGraph, Celery + Redis, Supabase (Postgres/Auth), Neo4j, ChromaDB (local persistent `./chroma_data`).
- **AI**: OpenRouter (LLM), Hugging Face Inference API `all-MiniLM-L6-v2` (embeddings).

## Commands
Backend (run from `backend/`; imports are rooted there: `from app...`, `from worker...`):
- `uvicorn main:app --reload --port 8000`
- `celery -A app.core.celery_app.celery_app worker --loglevel=info`
- `docker compose up -d redis` (local Redis)
- `pytest`

Frontend (run from `frontend/`):
- `npm run dev` · `npm run build` (`tsc -b && vite build`) · `npm run lint`

## Architecture
- Long-running work is async: `POST /api/v1/research/start` enqueues a Celery task and returns a `task_id`; the frontend polls `GET /api/v1/research/status/{task_id}`; results at `.../results/{task_id}`.
- LangGraph pipeline (`app/agents/`): planner → mutator (GA) → validator (GraphRAG) → predictor (LLM) → fitness/loop → reporter. State is `ResearchState` in `app/agents/state.py`; graph is wired in `app/agents/workflow.py`.
- Services in `app/services/`: `ingestion`, `embeddings.py`, `retrieval` (vector, graph, `graph_rag.py` fusion), `graph` (extractor, Neo4j ingestion), `ga` (material, operators, population, fitness), `llm` (OpenRouter client).
- DB clients in `app/db/`; settings in `app/core/config.py` (pydantic-settings, reads `backend/.env`; see `.env.example`).
- Supabase tables: `ResearchTasks`, `SavedMaterials`, plus `chat_messages` used by the chat UI.
- Neo4j: nodes `Element`, `Material`, `Property`, `DegradationMode`; edges `CONTAINS`, `CAN_BE_DOPED_WITH`, `SUFFERS_FROM`, `PREVENTED_BY`.
- ChromaDB collections: `battery_literature`, `material_properties`.

## GA Invariants (do not break – see `docs/GA.md`, `phases/phase_5.md`)
- Transition-metal/octahedral-site fractions always sum to exactly 1.0; no negative coefficients.
- Lithium and oxygen stoichiometry stay fixed during mutation.
- Operator mix: 40% doping (0.01–0.05), 40% substitution, 20% crossover; tournament selection (size 3); elitism keeps top candidates unchanged.
- User-excluded elements must never enter a genome.
- Canonical formula order: Li first, metals alphabetical, O last (dedupes identical compounds).
- Chemistry rules come from the GA and GraphRAG, never from unconstrained LLM generation.

## Conventions
- Secrets (OpenRouter, HF, Supabase service key, Neo4j) live only in backend `.env`; never expose to the frontend or commit them.
- CORS is restricted to the known frontend origins (localhost:5173 in dev, the Vercel domain in prod).
- OpenRouter/HF calls inside Celery use retries with exponential backoff (tenacity).
- Python: type-hinted, Pydantic for I/O schemas, business logic in `services/`, thin endpoints.
- Frontend: strict TypeScript (no `any`), ESLint must pass, shared state in Zustand, auth via `AuthContext`.

## Git Workflow
After completing each phase or task the user specifies:
1. Stage and commit all changes using the conventional commit format: `feat:`, `fix:`, `chore:`, `refactor:`, `docs:`, `test:`.
2. Keep commit messages short and precise — only describe what was actually changed, nothing extra.
3. Always add Claude as co-author by appending this trailer to every commit message:
   ```
   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
   ```
4. Push to the branch the user specifies (e.g. `git push origin <branch>`). Create it if it doesn't exist (`git checkout -b <branch>`). Never open a PR or merge unless asked.

Example commit:
```
feat: add GA mutation operators and population seeding
```
