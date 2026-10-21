import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from main import app

client = TestClient(app)


@pytest.fixture
def signed_in():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("method,path", [
    ("post", "/api/v1/ingestion/sync"),
    ("get", "/api/v1/ingestion/status/abc"),
    ("get", "/api/v1/ingestion/stats"),
    ("post", "/api/v1/test-celery"),
    ("get", "/api/v1/task/abc"),
])
def test_protected_routes_reject_anonymous_requests(method, path):
    kwargs = {"json": {"query": "lithium dendrite"}} if method == "post" and "sync" in path else {}

    response = getattr(client, method)(path, **kwargs)

    assert response.status_code in (401, 403)


def test_liveness_probe_stays_public():
    assert client.get("/api/v1/health").status_code == 200


@pytest.mark.parametrize("payload", [
    {"query": "lithium", "sources": ["myspace"]},
    {"query": "x" * 201},
    {"query": "   "},
    {"query": "lithium", "sources": []},
    {"query": "lithium", "max_results": 500},
])
def test_sync_rejects_invalid_requests(signed_in, payload):
    with patch("worker.tasks.harvest_and_ingest_task.apply_async") as mock_task:
        response = client.post("/api/v1/ingestion/sync", json=payload)

    assert response.status_code == 422
    mock_task.assert_not_called()


def test_sync_normalizes_query_and_expands_sources(signed_in):
    with patch("worker.tasks.harvest_and_ingest_task.apply_async") as mock_task:
        mock_task.return_value = MagicMock(id="t-1")
        client.post("/api/v1/ingestion/sync", json={"query": "  solid   state  ", "sources": ["arxiv", "arxiv"]})
        client.post("/api/v1/ingestion/sync", json={"query": "solid state", "sources": ["pubmed", "all"]})

    first, second = (call.kwargs["args"] for call in mock_task.call_args_list)
    assert first == ["solid state", ["arxiv"], 10]
    assert second[1] == ["arxiv", "wikipedia", "crossref", "pubmed"]


@pytest.mark.parametrize("iterations", [0, 21, 100000])
def test_test_celery_bounds_iterations(signed_in, iterations):
    with patch("app.api.v1.endpoints.health.test_dummy_task.delay") as mock_delay:
        response = client.post(f"/api/v1/test-celery?iterations={iterations}")

    assert response.status_code == 422
    mock_delay.assert_not_called()


def test_test_celery_accepts_a_small_job(signed_in):
    with patch("app.api.v1.endpoints.health.test_dummy_task.delay", return_value=MagicMock(id="t-9")):
        response = client.post("/api/v1/test-celery?iterations=3")

    assert response.status_code == 200
    assert response.json() == {"task_id": "t-9"}


def test_db_health_does_not_leak_connection_details():
    with patch("app.api.v1.endpoints.health.neo4j_conn.verify_connectivity", return_value=False), \
         patch("app.api.v1.endpoints.health.chroma_client.heartbeat", side_effect=Exception("host=db.internal.example password=hunter2")), \
         patch("app.api.v1.endpoints.health.supabase_client.auth.get_session", side_effect=Exception("https://secret.supabase.co")):
        body = client.get("/api/v1/health/db").json()

    assert body == {"neo4j": "disconnected", "chroma": "disconnected", "supabase": "disconnected"}


def test_rag_error_response_hides_internal_message():
    with patch("app.api.v1.endpoints.rag.GraphRAGService.retrieve_context", new_callable=AsyncMock,
               side_effect=RuntimeError("bolt://secret-host:7687 refused")):
        response = client.post("/api/v1/rag/query", json={"prompt": "doping Al"})

    assert response.status_code == 500
    assert "secret-host" not in response.text


def test_research_start_is_refused_when_the_task_row_cannot_be_created(signed_in):
    failing_table = MagicMock()
    failing_table.insert.return_value.execute.side_effect = RuntimeError("db down")
    with patch("app.api.v1.endpoints.research.supabase_client.table", return_value=failing_table), \
         patch("app.api.v1.endpoints.research.run_discovery_loop.apply_async") as mock_run:
        response = client.post("/api/v1/research/start", json={"prompt": "cobalt-free cathode"})

    assert response.status_code == 503
    mock_run.assert_not_called()
