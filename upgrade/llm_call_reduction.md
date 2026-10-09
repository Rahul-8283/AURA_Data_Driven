# Cut LLM calls per discovery run from ~1,500 to ~45

## Context
A 20-generation run makes about 1,500 LLM calls (OpenRouter, Gemini fallback). OpenRouter's free tier allows 50 per day, so the run hits 429s and Gemini 429s too. When both fail, the predictor silently writes zero scores (`predictor.py:38-45`) and the GA evolves on garbage. Retries multiply the damage: openai SDK 3 attempts x tenacity 3 attempts. Goal: a full run fits comfortably inside the free quota, fails loudly instead of silently, and stops leaking the Gemini key.

Where the calls come from (per run):
- `extract_entities` LLM call inside every `retrieve_context`: ~760 (mutator 360 + predictor 400)
- per-child `validate_material_async` (`mutator.py:63-65`): 360+
- per-material `predict_properties_async` (`predictor.py:26-29`), all 20 re-predicted every generation including elites and repeats: 400
- planner 1, reporter 1

## Changes

1. **Deterministic entity extraction in the pipeline**: `app/services/retrieval/graph_search.py` (`extract_entities`, `get_graph_context`), `graph_rag.py` (`retrieve_context`).
   Add a param (e.g. `use_llm_entities: bool = False`) threaded from `retrieve_context`. Pipeline callers (mutator, predictor) derive entities from the composition via `BatteryMaterial.parse_string_to_dict` plus the existing `fallback_entities`. The chat endpoint keeps the LLM path. Saves ~760 calls.

2. **Batch prediction, one call per generation**: `app/services/llm/client.py` (new `predict_properties_batch_async`), `predictor.py`.
   Predictor skips compositions already in a module-level cache (`dict[str, PredictionResult]`, keyed by canonical composition string, which `serialize_to_string` already normalizes). Elites carry their prediction and skip. Novel compositions go to the LLM in one call that returns a JSON list. Reuse `normalize_prediction_dict` / `parse_llm_json` for each item. Items missing from the response fall back to the existing per-item `predict_properties_async`. Retrieval context for the batch: GraphRAG context for each composition (graph and vector only, no LLM). Saves ~380 calls.

3. **Batch validation with top-up**: `mutator.py`, `client.py` (new `validate_materials_batch_async`).
   Generate the needed children for the generation, validate them in one call, keep the valid ones, and repeat for the shortfall (bounded by the existing `max_attempts`). Cache verdicts by composition so repeats are free. On error, keep the existing "assume valid" behavior. Saves ~340 calls.

4. **Fail loudly on quota exhaustion**: `client.py`, `planner.py`.
   Set `max_retries=0` on `AsyncOpenAI` (`get_client`), and have tenacity stop immediately on a daily-limit 429 (message contains `free-models-per-day`) instead of retrying. Raise a clear `LLMQuotaExceeded` from the predictor path; `worker/tasks.py` marks the `ResearchTasks` row as `failed` with that message instead of saving zero-score candidates. Remove the silent zero-score fallback.

5. **Configurable GA size for testing**: `app/core/config.py`, `planner.py:94,140`, `mutator.py:31`.
   Add `GA_GENERATIONS` (default 20) and `GA_POPULATION_SIZE` (default 10) settings. Replace the hardcoded values. Target pop size 20 stays the default.

6. **Stop leaking the Gemini key**: `client.py:108,160,198`, `planner.py:71`, `graph_search.py:93`, `graph_rag.py:58`, `extractor.py:61`.
   Send the key via the `x-goog-api-key` header instead of `?key=` in the URL. Also stop writing `str(e)` into `mat["reasoning"]` / `SavedMaterials.reasoning`.

Expected call count per 20-generation run: planner 1 + validate batches ~20-25 + predict batches 20 + reporter 1 = about 45. A 5-generation test run is about 12.

## Notes
- Out of scope: OpenRouter credit purchase, key rotation (user actions).
- Commits (branch `feat/8`, no PR/merge), one per logical change, each ending with the Co-Authored-By trailer required by CLAUDE.md: (1) deterministic entities, (2) batch predict + cache, (3) batch validate, (4) fail-loud quota handling, (5) GA settings, (6) Gemini key header.

## Verification
- `pytest` in `backend/` (existing tests plus new unit tests: cache hit skips LLM, batch parse fallback to per-item, quota error marks the task failed, composition-derived entities).
- Mock the LLM client and count calls for a 3-generation run; assert the count is far below the old per-candidate total.
- Live: start FastAPI and Celery, set `GA_GENERATIONS=3`, run one prompt from the UI, confirm the worker log shows ~10 LLM requests and the task redirects to `/results/:taskId`.
- Check that no log line contains `key=` or the Gemini key.
