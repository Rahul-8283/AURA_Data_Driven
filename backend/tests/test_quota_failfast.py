import pytest
import requests
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.nodes import mutator
from app.agents.nodes.mutator import mutator_node
from app.services.llm import client
from app.services.llm.client import predict_properties_batch_async
from app.services.llm.errors import LLMQuotaExceeded, LLMUnavailableError
from worker.tasks import mark_task_failed

DAILY_QUOTA_ERROR = RuntimeError(
    "Error code: 429 - {'error': {'message': 'Rate limit exceeded: free-models-per-day. "
    "Add 10 credits to unlock 1000 free model requests per day'}}"
)


class FakeCompletions:
    def __init__(self, error: Exception):
        self.error = error
        self.calls = 0

    async def create(self, **_kwargs):
        self.calls += 1
        raise self.error


class FakeClient:
    def __init__(self, completions: FakeCompletions):
        self.chat = SimpleNamespace(completions=completions)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False


def _gemini_429():
    response = MagicMock(status_code=429)
    failing = MagicMock()
    failing.raise_for_status.side_effect = requests.HTTPError("429 Client Error", response=response)
    return failing


@pytest.mark.asyncio
async def test_daily_quota_with_gemini_down_raises_quota_error_without_retry():
    completions = FakeCompletions(DAILY_QUOTA_ERROR)
    with patch.object(client, "get_client", return_value=FakeClient(completions)), \
         patch.object(client.requests, "post", return_value=_gemini_429()):
        with pytest.raises(LLMQuotaExceeded) as excinfo:
            await predict_properties_batch_async([("LiNi0.5Mn0.5O2", "ctx")])

    assert completions.calls == 1
    assert "daily reset" in str(excinfo.value)
    assert "key=" not in str(excinfo.value)


@pytest.mark.asyncio
async def test_transient_failure_with_gemini_down_is_not_a_quota_error():
    completions = FakeCompletions(RuntimeError("connection reset"))
    with patch.object(client, "get_client", return_value=FakeClient(completions)), \
         patch.object(client.requests, "post", return_value=_gemini_429()):
        with pytest.raises(LLMUnavailableError) as excinfo:
            await predict_properties_batch_async([("LiNi0.5Mn0.5O2", "ctx")])

    assert not isinstance(excinfo.value, LLMQuotaExceeded)
    assert completions.calls == 3


@pytest.mark.asyncio
@patch.object(mutator.GraphRAGService, "retrieve_context", new_callable=AsyncMock, return_value="ctx")
@patch("app.agents.nodes.mutator.validate_materials_batch_async", new_callable=AsyncMock,
       side_effect=LLMQuotaExceeded("quota spent"))
async def test_mutator_does_not_swallow_quota_errors(_validate, _ctx):
    state = {
        "current_population": [{"id": "s", "composition": "LiNi0.5Mn0.5O2", "fitness": 1.0}],
        "excluded_elements": [],
        "current_generation": 0,
        "logs": [],
    }
    with pytest.raises(LLMQuotaExceeded):
        await mutator_node(state)


@patch("worker.tasks.supabase_client")
def test_quota_failure_is_persisted_with_the_quota_message(mock_supabase):
    mark_task_failed("task-1", LLMQuotaExceeded("quota spent, wait for reset"))

    update = mock_supabase.table.return_value.update.call_args.args[0]
    assert update["status"] == "failed"
    assert update["result_json"] == {"error": "quota spent, wait for reset"}


@patch("worker.tasks.supabase_client")
def test_unexpected_failure_persists_generic_message_only(mock_supabase):
    mark_task_failed("task-2", ValueError("secret-bearing details"))

    update = mock_supabase.table.return_value.update.call_args.args[0]
    assert "secret-bearing details" not in update["result_json"]["error"]
    assert "ValueError" in update["result_json"]["error"]
