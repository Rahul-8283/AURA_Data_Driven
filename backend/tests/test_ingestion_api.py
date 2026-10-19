import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_sync_endpoint_triggers_celery_task():
    with patch("worker.tasks.harvest_and_ingest_task.apply_async") as mock_task:
        mock_res = MagicMock()
        mock_res.id = "mock-task-id-1234"
        mock_task.return_value = mock_res

        resp = client.post("/api/v1/ingestion/sync", json={
            "query": "lithium dendrite",
            "sources": ["arxiv", "wikipedia"],
            "max_results": 5
        })

        assert resp.status_code == 202
        data = resp.json()
        assert data["task_id"] == "mock-task-id-1234"
        assert data["status"] == "started"
        assert data["query"] == "lithium dendrite"

def test_status_endpoint_returns_pending():
    with patch("app.api.v1.endpoints.ingestion.AsyncResult") as mock_async:
        mock_task = MagicMock()
        mock_task.state = "PENDING"
        mock_async.return_value = mock_task

        resp = client.get("/api/v1/ingestion/status/mock-task-id-1234")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "Pending"
        assert data["stage"] == "queued"

def test_status_endpoint_returns_progress():
    with patch("app.api.v1.endpoints.ingestion.AsyncResult") as mock_async:
        mock_task = MagicMock()
        mock_task.state = "PROGRESS"
        mock_task.info = {
            "stage": "extracting_triplets",
            "message": "Extracted 12 triplets",
            "papers_found": 8,
            "new_papers_indexed": 3
        }
        mock_async.return_value = mock_task

        resp = client.get("/api/v1/ingestion/status/mock-task-id-1234")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "In Progress"
        assert data["stage"] == "extracting_triplets"
        assert data["new_papers_indexed"] == 3

def test_status_endpoint_returns_success():
    with patch("app.api.v1.endpoints.ingestion.AsyncResult") as mock_async:
        mock_task = MagicMock()
        mock_task.state = "SUCCESS"
        mock_task.result = {
            "query": "solid state",
            "sources": ["arxiv"],
            "papers_found": 5,
            "new_papers_indexed": 4,
            "message": "Harvesting complete."
        }
        mock_async.return_value = mock_task

        resp = client.get("/api/v1/ingestion/status/mock-task-id-1234")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "Complete"
        assert data["new_papers_indexed"] == 4

def test_stats_endpoint():
    with patch("app.api.v1.endpoints.ingestion.init_literature_collection") as mock_col:
        mock_c = MagicMock()
        mock_c.count.return_value = 150
        mock_col.return_value = mock_c

        resp = client.get("/api/v1/ingestion/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "chroma_literature_chunks" in data
        assert "supported_sources" in data
        assert "arXiv" in data["supported_sources"]
