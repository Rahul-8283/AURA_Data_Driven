import json
import pytest
from unittest.mock import AsyncMock, patch

from app.agents.nodes import predictor
from app.agents.nodes.predictor import predictor_node, PREDICTION_CACHE
from app.services.llm.client import PredictionResult, predict_properties_batch_async

PRED = PredictionResult(specific_capacity=200.0, voltage=3.8, cycle_life=1000,
                        cost_estimate_usd_kg=25.0, reasoning="test")


@pytest.fixture(autouse=True)
def clear_cache():
    PREDICTION_CACHE.clear()
    yield
    PREDICTION_CACHE.clear()


def _state(compositions):
    return {
        "current_population": [{"id": str(i), "composition": c, "fitness": 0.0} for i, c in enumerate(compositions)],
        "target_properties": {},
        "best_candidates": [],
        "generation_history": [],
        "current_generation": 1,
        "logs": [],
    }


@pytest.mark.asyncio
@patch.object(predictor.GraphRAGService, "retrieve_context", new_callable=AsyncMock, return_value="ctx")
@patch("app.agents.nodes.predictor.predict_properties_batch_async", new_callable=AsyncMock)
async def test_one_batch_call_for_all_unique_novel_compositions(mock_batch, _ctx):
    mock_batch.side_effect = lambda items: {c: PRED for c, _ in items}

    state = await predictor_node(_state(["LiNi0.8Co0.1Mn0.1O2", "LiNi0.5Mn0.5O2", "LiNi0.8Co0.1Mn0.1O2"]))

    assert mock_batch.await_count == 1
    assert len(mock_batch.await_args.args[0]) == 2
    assert all(m["specific_capacity"] == 200.0 for m in state["current_population"])


@pytest.mark.asyncio
@patch.object(predictor.GraphRAGService, "retrieve_context", new_callable=AsyncMock, return_value="ctx")
@patch("app.agents.nodes.predictor.predict_properties_batch_async", new_callable=AsyncMock)
async def test_cached_compositions_make_no_llm_call(mock_batch, _ctx):
    PREDICTION_CACHE["LiNi0.5Mn0.5O2"] = PRED

    state = await predictor_node(_state(["LiNi0.5Mn0.5O2"]))

    mock_batch.assert_not_awaited()
    assert state["current_population"][0]["voltage"] == 3.8


@pytest.mark.asyncio
@patch.object(predictor.GraphRAGService, "retrieve_context", new_callable=AsyncMock, return_value="ctx")
@patch("app.agents.nodes.predictor.predict_properties_batch_async", new_callable=AsyncMock)
async def test_missing_items_are_retried_once_in_a_batch(mock_batch, _ctx):
    mock_batch.side_effect = [
        {"LiNi0.5Mn0.5O2": PRED},
        {"LiNi0.8Co0.1Mn0.1O2": PRED},
    ]

    await predictor_node(_state(["LiNi0.5Mn0.5O2", "LiNi0.8Co0.1Mn0.1O2"]))

    assert mock_batch.await_count == 2
    retry_items = mock_batch.await_args_list[1].args[0]
    assert [c for c, _ in retry_items] == ["LiNi0.8Co0.1Mn0.1O2"]


@pytest.mark.asyncio
@patch.object(predictor.GraphRAGService, "retrieve_context", new_callable=AsyncMock, return_value="ctx")
@patch("app.agents.nodes.predictor.predict_properties_batch_async", new_callable=AsyncMock, return_value={})
async def test_still_missing_after_retry_fails_loudly(_batch, _ctx):
    with pytest.raises(ValueError, match="LLM returned no prediction"):
        await predictor_node(_state(["LiNi0.5Mn0.5O2"]))
    assert "LiNi0.5Mn0.5O2" not in PREDICTION_CACHE


@pytest.mark.asyncio
@patch("app.services.llm.client._generate_text", new_callable=AsyncMock)
async def test_batch_response_maps_by_index_to_composition(mock_generate):
    mock_generate.return_value = json.dumps([
        {"index": 1, "specific_capacity": 180.0, "voltage": 3.7, "cycle_life": 900,
         "cost_estimate_usd_kg": 30.0, "reasoning": "second"},
        {"index": 0, "specific_capacity": 210.0, "voltage": 3.9, "cycle_life": 1200,
         "cost_estimate_usd_kg": 28.0, "reasoning": "first"},
    ])

    results = await predict_properties_batch_async([("LiNi0.8Co0.1Mn0.1O2", "a"), ("LiNi0.5Mn0.5O2", "b")])

    assert results["LiNi0.8Co0.1Mn0.1O2"].specific_capacity == 210.0
    assert results["LiNi0.5Mn0.5O2"].specific_capacity == 180.0
