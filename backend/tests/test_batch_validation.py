import random
import pytest
from unittest.mock import AsyncMock, patch

from app.agents.nodes import mutator
from app.agents.nodes.mutator import mutator_node, VERDICT_CACHE, TARGET_POPULATION

SEEDS = [
    "LiNi0.334Co0.333Mn0.333O2",
    "LiNi0.5Co0.2Mn0.3O2",
    "LiNi0.6Co0.2Mn0.2O2",
    "LiNi0.8Co0.1Mn0.1O2",
    "LiNi0.5Mn0.5O2",
    "LiNi0.8Mn0.1Al0.1O2",
]


@pytest.fixture(autouse=True)
def clear_cache():
    VERDICT_CACHE.clear()
    random.seed(7)
    yield
    VERDICT_CACHE.clear()


def _state():
    pop = [{"id": f"s{i}", "composition": c, "fitness": float(10 - i)} for i, c in enumerate(SEEDS)]
    return {
        "current_population": pop,
        "excluded_elements": [],
        "current_generation": 0,
        "logs": [],
    }


def _accept_all(items):
    return {c: True for c, _ in items}


@pytest.mark.asyncio
@patch.object(mutator.GraphRAGService, "retrieve_context", new_callable=AsyncMock, return_value="ctx")
@patch("app.agents.nodes.mutator.validate_materials_batch_async", new_callable=AsyncMock)
async def test_pool_is_validated_in_one_batch_call(mock_validate, _ctx):
    mock_validate.side_effect = _accept_all

    state = await mutator_node(_state())

    assert mock_validate.await_count == 1
    assert len(state["current_population"]) == TARGET_POPULATION
    assert state["current_generation"] == 1


@pytest.mark.asyncio
@patch.object(mutator.GraphRAGService, "retrieve_context", new_callable=AsyncMock, return_value="ctx")
@patch("app.agents.nodes.mutator.validate_materials_batch_async", new_callable=AsyncMock)
async def test_rejected_children_are_dropped_and_top_up_is_bounded(mock_validate, _ctx):
    # Reject every child in the first pool; accept everything in any later round.
    calls = {"n": 0}

    def reject_first(items):
        calls["n"] += 1
        verdict = calls["n"] > 1
        return {c: verdict for c, _ in items}

    mock_validate.side_effect = reject_first

    state = await mutator_node(_state())

    assert mock_validate.await_count <= mutator.MAX_VALIDATION_ROUNDS
    assert len(state["current_population"]) == TARGET_POPULATION
    assert len({m["composition"] for m in state["current_population"]}) == TARGET_POPULATION


@pytest.mark.asyncio
@patch.object(mutator.GraphRAGService, "retrieve_context", new_callable=AsyncMock, return_value="ctx")
@patch("app.agents.nodes.mutator.validate_materials_batch_async", new_callable=AsyncMock)
async def test_verdicts_are_cached_across_generations(mock_validate, _ctx):
    mock_validate.side_effect = _accept_all

    state = await mutator_node(_state())
    checked = [c for c, _ in mock_validate.await_args.args[0]]
    assert all(c in VERDICT_CACHE for c in checked)

    await mutator_node(state)
    second_call_items = [c for c, _ in mock_validate.await_args.args[0]]
    assert not set(second_call_items) & set(checked)


@pytest.mark.asyncio
@patch.object(mutator.GraphRAGService, "retrieve_context", new_callable=AsyncMock, return_value="ctx")
@patch("app.agents.nodes.mutator.validate_materials_batch_async", new_callable=AsyncMock, side_effect=RuntimeError("LLM down"))
async def test_validation_error_accepts_pool_unverified(_validate, _ctx):
    state = await mutator_node(_state())

    assert len(state["current_population"]) == TARGET_POPULATION
    assert not VERDICT_CACHE
