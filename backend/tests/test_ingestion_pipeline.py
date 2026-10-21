import asyncio
import pytest
import requests
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.api.v1.endpoints import ingestion as ingestion_endpoint
from app.core.celery_app import build_beat_schedule
from app.core.config import settings
from app.core.security import get_current_user
from app.models.graph import Triplet
from app.services.graph.extractor import extract_triplets_from_text
from app.services.harvesters import HarvestedDocument, HarvesterError
from app.services.llm.errors import LLMQuotaExceeded, LLMUnavailableError
from main import app
from worker import tasks
from worker.tasks import harvest_and_ingest_task, periodic_nightly_harvest, process_chroma_chunks_task


class FakeCollection:
    """In-memory stand-in for a Chroma collection with the calls the tasks use."""

    def __init__(self):
        self.docs = {}

    def upsert(self, documents, metadatas, ids):
        for document, metadata, chunk_id in zip(documents, metadatas, ids):
            self.docs[chunk_id] = {"document": document, "metadata": dict(metadata)}

    def count(self):
        return len(self.docs)

    def get(self, ids=None, where=None, limit=None, include=None):
        items = [(i, v) for i, v in self.docs.items() if ids is None or i in ids]
        if where:
            items = [(i, v) for i, v in items if all(v["metadata"].get(k) == val for k, val in where.items())]
        if limit:
            items = items[:limit]
        return {
            "ids": [i for i, _ in items],
            "documents": [v["document"] for _, v in items],
            "metadatas": [v["metadata"] for _, v in items],
        }

    def update(self, ids, metadatas):
        for chunk_id, metadata in zip(ids, metadatas):
            self.docs[chunk_id]["metadata"] = dict(metadata)


def make_doc(title, doi, source="arxiv"):
    summary = f"{title}: a layered oxide cathode study reporting capacity retention and cycle life for lithium-ion batteries."
    return HarvestedDocument(title=title, summary=summary, doi=doi, source=source)


def fake_harvester(docs=None, error=None):
    class _Harvester:
        async def harvest(self, query, max_results=10):
            if error:
                raise error
            return list(docs or [])
    return _Harvester


def run_harvest(collection, harvesters, sources=("arxiv", "wikipedia", "crossref", "pubmed")):
    classes = {
        "ArxivHarvester": harvesters.get("arxiv", fake_harvester([])),
        "WikipediaHarvester": harvesters.get("wikipedia", fake_harvester([])),
        "CrossrefHarvester": harvesters.get("crossref", fake_harvester([])),
        "PubMedHarvester": harvesters.get("pubmed", fake_harvester([])),
    }
    with patch.multiple("worker.tasks", **classes), \
         patch("worker.tasks.init_literature_collection", return_value=collection), \
         patch.object(process_chroma_chunks_task, "delay", return_value=SimpleNamespace(id="extract-1")) as delay:
        result = harvest_and_ingest_task.run("cathode doping", list(sources), 10)
    return result, delay


# --- harvest task ----------------------------------------------------------------------------

def test_harvest_indexes_new_documents_once_and_flags_them_for_extraction():
    collection = FakeCollection()
    paper_a = make_doc("Mg-doped NMC811 cathodes", "arxiv:1")
    paper_a_elsewhere = make_doc("Mg doped NMC811 cathodes!", "doi:10.1/a", source="crossref")
    paper_b = make_doc("Cobalt-free layered oxides", "pubmed:2", source="pubmed")

    result, delay = run_harvest(collection, {
        "arxiv": fake_harvester([paper_a]),
        "crossref": fake_harvester([paper_a_elsewhere]),
        "pubmed": fake_harvester([paper_b]),
        "wikipedia": fake_harvester(error=HarvesterError("Wikipedia search returned status 503")),
    })

    assert result["new_papers_indexed"] == 2
    assert result["papers_found"] == 3
    assert result["source_errors"] == {"wikipedia": "Wikipedia search returned status 503"}
    assert "Sources failed: wikipedia" in result["message"]
    assert all(v["metadata"]["graph_extracted"] is False and v["metadata"]["title_key"] for v in collection.docs.values())
    delay.assert_called_once_with(chunk_ids=list(collection.docs))
    assert result["extraction_task_id"] == "extract-1"


def test_harvesting_the_same_papers_again_indexes_nothing_and_queues_no_extraction():
    collection = FakeCollection()
    harvesters = {"arxiv": fake_harvester([make_doc("Mg-doped NMC811 cathodes", "arxiv:1")])}
    run_harvest(collection, harvesters, sources=["arxiv"])

    result, delay = run_harvest(collection, harvesters, sources=["arxiv"])

    assert result["new_papers_indexed"] == 0
    assert result["extraction_task_id"] is None
    delay.assert_not_called()


def test_harvest_fails_loudly_when_every_source_fails():
    collection = FakeCollection()
    failing = {name: fake_harvester(error=HarvesterError("status 503")) for name in ("arxiv", "wikipedia", "crossref", "pubmed")}

    with pytest.raises(HarvesterError, match="All literature sources failed"):
        run_harvest(collection, failing)


def test_harvest_rejects_a_request_with_no_valid_source():
    with pytest.raises(ValueError):
        harvest_and_ingest_task.run("cathode", ["myspace"], 5)


# --- incremental, quota-aware triplet extraction ---------------------------------------------

def seeded_collection(total, already_extracted=0):
    collection = FakeCollection()
    for i in range(total):
        collection.docs[f"c{i}"] = {"document": f"chunk text {i}", "metadata": {"graph_extracted": i < already_extracted}}
    return collection


TRIPLET = Triplet(subject_label="Material", subject="NMC811", predicate="CAN_BE_DOPED_WITH", object_label="Element", object="Mg")


def run_extraction(collection, extract, ingest=None, **kwargs):
    with patch("worker.tasks.init_literature_collection", return_value=collection), \
         patch("worker.tasks.extract_triplets_from_text", side_effect=extract) as extractor, \
         patch("worker.tasks.ingest_triplets", side_effect=ingest) as ingester:
        result = process_chroma_chunks_task.run(**kwargs)
    return result, extractor, ingester


def flagged(collection):
    return {i for i, v in collection.docs.items() if v["metadata"].get("graph_extracted")}


def test_extraction_only_touches_chunks_that_are_still_pending(monkeypatch):
    monkeypatch.setattr(settings, "GRAPH_EXTRACTION_GROUP_SIZE", 4)
    monkeypatch.setattr(settings, "GRAPH_EXTRACTION_MAX_CALLS", 10)
    collection = seeded_collection(10, already_extracted=3)

    result, extractor, ingester = run_extraction(collection, lambda text: [TRIPLET])

    assert extractor.call_count == 2  # 7 pending chunks in groups of 4
    sent = " ".join(call.args[0] for call in extractor.call_args_list)
    assert all(f"chunk text {i}" not in sent for i in range(3))
    assert flagged(collection) == {f"c{i}" for i in range(10)}
    assert result["chunks_extracted"] == 7 and result["chunks_pending"] == 0 and result["triplets_ingested"] == 2


def test_one_run_never_exceeds_the_llm_call_cap(monkeypatch):
    monkeypatch.setattr(settings, "GRAPH_EXTRACTION_GROUP_SIZE", 4)
    monkeypatch.setattr(settings, "GRAPH_EXTRACTION_MAX_CALLS", 2)
    collection = seeded_collection(30)

    result, extractor, _ = run_extraction(collection, lambda text: [])

    assert extractor.call_count == 2
    assert result["chunks_extracted"] == 8 and result["chunks_pending"] == 22


def test_extraction_can_be_restricted_to_given_chunks(monkeypatch):
    monkeypatch.setattr(settings, "GRAPH_EXTRACTION_GROUP_SIZE", 4)
    collection = seeded_collection(12)

    result, extractor, _ = run_extraction(collection, lambda text: [], chunk_ids=["c0", "c1", "c2"])

    assert extractor.call_count == 1
    assert flagged(collection) == {"c0", "c1", "c2"}


def test_extraction_stops_on_quota_and_leaves_unfinished_chunks_pending(monkeypatch):
    monkeypatch.setattr(settings, "GRAPH_EXTRACTION_GROUP_SIZE", 2)
    monkeypatch.setattr(settings, "GRAPH_EXTRACTION_MAX_CALLS", 10)
    collection = seeded_collection(6)

    result, extractor, _ = run_extraction(collection, [[TRIPLET], LLMQuotaExceeded("spent")])

    assert extractor.call_count == 2
    assert result["stopped_reason"] == "quota_exhausted"
    assert flagged(collection) == {"c0", "c1"}
    assert result["chunks_pending"] == 4


def test_extraction_gives_up_after_repeated_provider_failures(monkeypatch):
    monkeypatch.setattr(settings, "GRAPH_EXTRACTION_GROUP_SIZE", 2)
    monkeypatch.setattr(settings, "GRAPH_EXTRACTION_MAX_CALLS", 10)
    collection = seeded_collection(20)

    result, extractor, _ = run_extraction(collection, LLMUnavailableError("down"))

    assert extractor.call_count == 3
    assert result["stopped_reason"] == "llm_unavailable"
    assert flagged(collection) == set()


def test_extraction_stops_when_neo4j_rejects_a_write(monkeypatch):
    monkeypatch.setattr(settings, "GRAPH_EXTRACTION_GROUP_SIZE", 2)
    collection = seeded_collection(6)

    result, extractor, _ = run_extraction(collection, lambda text: [TRIPLET], ingest=RuntimeError("neo4j down"))

    assert extractor.call_count == 1
    assert result["stopped_reason"] == "neo4j_error"
    assert flagged(collection) == set()


# --- nightly sweep ---------------------------------------------------------------------------

def test_nightly_sweep_counts_failed_topics_instead_of_reporting_success():
    outcomes = [None, RuntimeError("boom"), None, None, None]
    with patch.object(harvest_and_ingest_task, "apply", side_effect=outcomes) as apply:
        result = periodic_nightly_harvest.run()

    assert apply.call_count == 5 and all(call.kwargs["throw"] is True for call in apply.call_args_list)
    assert result == {"status": "Partial", "topics_processed": 4, "topics_failed": 1}


def test_beat_schedule_is_opt_in():
    assert build_beat_schedule(False) == {}
    assert build_beat_schedule(True)["nightly-battery-literature-sync"]["task"] == "periodic_nightly_harvest"


# --- extractor failure modes -----------------------------------------------------------------

def openrouter_and_gemini(openrouter, gemini):
    def post(url, **kwargs):
        return openrouter if "openrouter" in url else gemini
    return post


def http_response(status=200, text="", payload=None, fail=False):
    response = MagicMock()
    response.status_code = status
    response.text = text
    response.json.return_value = payload or {}
    if fail or status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"{status} Client Error", response=response)
    return response


@pytest.fixture
def providers(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "or-key")
    monkeypatch.setattr(settings, "gemini_api_key", "gem-key")


def test_extractor_raises_quota_error_when_openrouter_quota_and_gemini_both_fail(providers):
    quota = http_response(429, text="Rate limit exceeded: free-models-per-day")
    with patch("app.services.graph.extractor.requests.post", side_effect=openrouter_and_gemini(quota, http_response(429))):
        with pytest.raises(LLMQuotaExceeded):
            extract_triplets_from_text("some text")


def test_extractor_raises_unavailable_for_ordinary_failures(providers):
    with patch("app.services.graph.extractor.requests.post",
               side_effect=openrouter_and_gemini(http_response(500), http_response(500))) as post:
        with pytest.raises(LLMUnavailableError) as excinfo:
            extract_triplets_from_text("some text")

    assert not isinstance(excinfo.value, LLMQuotaExceeded)
    assert post.call_count == 2


def test_extractor_without_any_working_provider_never_pretends_nothing_was_found(providers, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    with patch("app.services.graph.extractor.requests.post", return_value=http_response(500)):
        with pytest.raises(LLMUnavailableError):
            extract_triplets_from_text("some text")


def test_extractor_distinguishes_an_empty_answer_from_a_failure(providers):
    ok = http_response(payload={"choices": [{"message": {"content": "[]"}}]})
    with patch("app.services.graph.extractor.requests.post", return_value=ok):
        assert extract_triplets_from_text("some text") == []


def test_extractor_parses_valid_triplets_and_drops_invalid_ones(providers):
    content = ('```json\n[{"subject_label":"Material","subject":"NMC811","predicate":"CONTAINS","object_label":"Element","object":"Ni"},'
               '{"subject_label":"Material","subject":"X","predicate":"DROP TABLE","object_label":"Element","object":"Ni"}]\n```')
    ok = http_response(payload={"choices": [{"message": {"content": content}}]})
    with patch("app.services.graph.extractor.requests.post", return_value=ok):
        triplets = extract_triplets_from_text("some text")

    assert [(t.subject, t.predicate, t.object) for t in triplets] == [("NMC811", "CONTAINS", "Ni")]


# --- stats endpoint --------------------------------------------------------------------------

@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


def neo4j_returning(nodes, relationships):
    conn = MagicMock()
    session = conn.get_session.return_value.__enter__.return_value
    session.run.side_effect = [
        MagicMock(single=lambda: {"cnt": nodes}),
        MagicMock(single=lambda: {"cnt": relationships}),
    ]
    return conn


def test_stats_report_real_counts_when_stores_are_up(client, monkeypatch):
    monkeypatch.setattr(settings, "NIGHTLY_HARVEST_ENABLED", True)
    with patch.object(ingestion_endpoint, "init_literature_collection", return_value=MagicMock(count=lambda: 150)), \
         patch.object(ingestion_endpoint, "neo4j_conn", neo4j_returning(40, 175)):
        body = client.get("/api/v1/ingestion/stats").json()

    assert (body["chroma_literature_chunks"], body["neo4j_nodes"], body["neo4j_relationships"]) == (150, 40, 175)
    assert body["errors"] == {} and body["nightly_sweep_enabled"] is True


def test_stats_report_outages_as_null_not_zero(client):
    broken_neo4j = MagicMock()
    broken_neo4j.get_session.side_effect = RuntimeError("bolt://secret-host unreachable")
    with patch.object(ingestion_endpoint, "init_literature_collection", side_effect=RuntimeError("disk")), \
         patch.object(ingestion_endpoint, "neo4j_conn", broken_neo4j):
        response = client.get("/api/v1/ingestion/stats")

    body = response.json()
    assert response.status_code == 200
    assert body["chroma_literature_chunks"] is None and body["neo4j_nodes"] is None
    assert body["errors"] == {"chroma": "unavailable", "neo4j": "unavailable"}
    assert "secret-host" not in response.text


def test_stats_run_their_blocking_calls_off_the_event_loop(client):
    with patch.object(ingestion_endpoint.asyncio, "to_thread", wraps=asyncio.to_thread) as to_thread, \
         patch.object(ingestion_endpoint, "init_literature_collection", return_value=MagicMock(count=lambda: 1)), \
         patch.object(ingestion_endpoint, "neo4j_conn", neo4j_returning(1, 1)):
        client.get("/api/v1/ingestion/stats")

    called = {call.args[0] for call in to_thread.call_args_list}
    assert called == {ingestion_endpoint._chroma_count, ingestion_endpoint._neo4j_counts}


def test_a_hanging_store_is_reported_as_timed_out_within_the_limit(client, monkeypatch):
    """The blocked read waits only 2s, far longer than the 0.3s limit. Without the bound, the
    endpoint would return the read's eventual result with no error at all."""
    import threading
    monkeypatch.setattr(ingestion_endpoint, "STATS_STORE_TIMEOUT_SECONDS", 0.3)
    release = threading.Event()

    def hang(*_args, **_kwargs):
        release.wait(2)

    hanging_neo4j = MagicMock()
    hanging_neo4j.get_session.return_value.__enter__.return_value.run.side_effect = hang
    with patch.object(ingestion_endpoint, "init_literature_collection", return_value=MagicMock(count=lambda: 42)), \
         patch.object(ingestion_endpoint, "neo4j_conn", hanging_neo4j):
        body = client.get("/api/v1/ingestion/stats").json()
    release.set()

    assert body["chroma_literature_chunks"] == 42
    assert body["neo4j_nodes"] is None and body["neo4j_relationships"] is None
    assert body["errors"] == {"neo4j": "timed out"}
