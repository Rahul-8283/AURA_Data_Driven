import random
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.nodes import mutator, predictor
from app.agents.nodes.predictor import predictor_node
from app.agents.state import init_research_state
from app.agents.workflow import recursion_limit
from app.core.config import Settings, settings
from app.scripts import simulate_discovery_run as simulator
from app.services.cache import TTLCache, clear_llm_caches
from app.services.llm.client import PredictionResult
from worker.tasks import harvest_and_ingest_task, process_chroma_chunks_task

PRED = PredictionResult(specific_capacity=200.0, voltage=3.8, cycle_life=1000, cost_estimate_usd_kg=25.0, reasoning="t")


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


# --- TTLCache --------------------------------------------------------------------------------

def test_entries_expire_after_the_ttl():
    clock = FakeClock()
    cache = TTLCache(max_entries=10, ttl_seconds=60, clock=clock)
    cache["a"] = 1

    clock.now = 59
    assert cache.get("a") == 1
    clock.now = 60
    assert cache.get("a") is None and "a" not in cache and len(cache) == 0


def test_least_recently_used_entry_is_evicted_past_the_limit():
    cache = TTLCache(max_entries=2, ttl_seconds=60, clock=FakeClock())
    cache["a"], cache["b"] = 1, 2
    assert cache["a"] == 1  # touch a, so b is now the oldest
    cache["c"] = 3

    assert set(cache) == {"a", "c"}


def test_behaves_like_the_dict_it_replaces():
    cache = TTLCache(max_entries=10, ttl_seconds=60, clock=FakeClock())
    cache.update({"a": 1, "b": 2})

    assert len(cache) == 2 and "a" in cache and cache.get("zzz", "default") == "default" and bool(cache)
    cache.clear()
    assert not cache and len(cache) == 0


# --- caches no longer serve stale or evicted results -----------------------------------------

def state_for(compositions):
    return {
        "current_population": [{"id": str(i), "composition": c, "fitness": 0.0} for i, c in enumerate(compositions)],
        "target_properties": {}, "best_candidates": [], "generation_history": [],
        "current_generation": 1, "logs": [],
    }


@pytest.mark.asyncio
async def test_a_predictor_cache_smaller_than_the_population_does_not_lose_results(monkeypatch):
    monkeypatch.setattr(predictor, "PREDICTION_CACHE", TTLCache(max_entries=2, ttl_seconds=60))
    formulas = ["LiNi0.5Mn0.5O2", "LiNi0.6Mn0.4O2", "LiNi0.7Mn0.3O2", "LiNi0.8Mn0.2O2", "LiNi0.9Mn0.1O2"]

    with patch.object(predictor.GraphRAGService, "retrieve_context", new_callable=AsyncMock, return_value="ctx"), \
         patch("app.agents.nodes.predictor.predict_properties_batch_async", new_callable=AsyncMock,
               side_effect=lambda items: {c: PRED for c, _ in items}):
        result = await predictor_node(state_for(formulas))

    assert all(m["specific_capacity"] == 200.0 for m in result["current_population"])


@pytest.mark.asyncio
async def test_expired_predictions_are_recomputed(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(predictor, "PREDICTION_CACHE", TTLCache(max_entries=10, ttl_seconds=60, clock=clock))

    with patch.object(predictor.GraphRAGService, "retrieve_context", new_callable=AsyncMock, return_value="ctx"), \
         patch("app.agents.nodes.predictor.predict_properties_batch_async", new_callable=AsyncMock,
               side_effect=lambda items: {c: PRED for c, _ in items}) as batch:
        await predictor_node(state_for(["LiNi0.5Mn0.5O2"]))
        await predictor_node(state_for(["LiNi0.5Mn0.5O2"]))
        assert batch.await_count == 1
        clock.now = 61
        await predictor_node(state_for(["LiNi0.5Mn0.5O2"]))

    assert batch.await_count == 2


def test_clearing_drops_every_registered_llm_cache():
    predictor.PREDICTION_CACHE["x"] = PRED
    mutator.VERDICT_CACHE["x"] = True

    clear_llm_caches()

    assert "x" not in predictor.PREDICTION_CACHE and "x" not in mutator.VERDICT_CACHE


# --- ingestion invalidates caches only when the knowledge base actually changed ---------------

def test_indexing_new_literature_clears_the_llm_caches():
    from tests.test_ingestion_pipeline import FakeCollection, fake_harvester, make_doc, run_harvest
    with patch("worker.tasks.clear_llm_caches") as clear:
        run_harvest(FakeCollection(), {"arxiv": fake_harvester([make_doc("Mg-doped NMC811 cathodes", "arxiv:1")])}, sources=["arxiv"])

    clear.assert_called_once()


def test_a_harvest_that_finds_nothing_new_leaves_the_caches_alone():
    from tests.test_ingestion_pipeline import FakeCollection, fake_harvester, run_harvest
    with patch("worker.tasks.clear_llm_caches") as clear:
        run_harvest(FakeCollection(), {"arxiv": fake_harvester([])}, sources=["arxiv"])

    clear.assert_not_called()


def test_extracting_new_graph_facts_clears_the_llm_caches():
    from tests.test_ingestion_pipeline import TRIPLET, run_extraction, seeded_collection
    with patch("worker.tasks.clear_llm_caches") as clear:
        run_extraction(seeded_collection(2), lambda text: [TRIPLET])

    clear.assert_called_once()


# --- recursion limit scales with the run -----------------------------------------------------

@pytest.mark.parametrize("generations", [1, 20, 98, 100, 500])
def test_recursion_limit_always_covers_a_full_run(generations):
    assert recursion_limit(generations) >= 2 * generations + 2


@pytest.mark.asyncio
async def test_a_hundred_generation_run_completes(monkeypatch):
    """Needed the GA round-trip fix and a recursion limit above the old fixed 200."""
    monkeypatch.setattr(settings, "GA_GENERATIONS", 100)
    random.seed(3)
    clear_llm_caches()
    simulator.calls.clear()

    final = await simulator._run_graph(init_research_state("t", "cobalt-free cathode", "u"), live=False)

    assert final["current_generation"] == 100
    assert sum(simulator.calls.values()) == 202  # planner + validate and predict per generation + summary


# --- smaller fixes ---------------------------------------------------------------------------

def test_timestamps_are_timezone_aware():
    from datetime import timezone
    state = init_research_state("t", "prompt", "u")

    assert state["start_time"].tzinfo is timezone.utc
    assert "+00:00" in state["logs"][0]


def test_the_unused_huggingface_key_is_optional(monkeypatch):
    # Importing main runs load_dotenv(), so a developer's real key may be in the environment.
    for name in ("HF_API_key", "HF_API_KEY", "hf_api_key"):
        monkeypatch.delenv(name, raising=False)
    config = Settings(
        _env_file=None, SUPABASE_URL="x", SUPABASE_SERVICE_ROLE_KEY="x", SUPABASE_JWT_SECRET="x",
        CHROMA_DATABASE="x", gemini_api_key="x", NEO4J_URI="x", NEO4J_USERNAME="x", NEO4J_PASSWORD="x",
        REDIS_URL="redis://x",
    )

    if config.HF_API_key is not None:  # not an assert: a failure must never print a real key
        pytest.fail("HF_API_key should default to None when unset")
