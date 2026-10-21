import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import chat
from app.api.v1.endpoints.chat import NO_EVIDENCE_ANSWER, group_sources
from app.core.config import settings
from app.core.security import get_current_user
from app.services.llm import client as llm_client
from app.services.llm.client import INSUFFICIENT_EVIDENCE, answer_question_async
from app.services.llm.errors import LLMQuotaExceeded, LLMUnavailableError
from app.services.rate_limit import DailyLimiter
from app.services.retrieval import graph_search
from main import app


def chunk(text, distance, title="Paper A", doi="doi:a", url="https://example.org/a", source="arxiv"):
    return {"content": text, "distance": distance,
            "metadata": {"title": title, "doi": doi, "url": url, "source": source}}


class FakeStore:
    def __init__(self, chunks=None, error=None):
        self.chunks, self.error, self.questions = chunks or [], error, []

    def search(self, question, n_results=5):
        self.questions.append(question)
        if self.error:
            raise self.error
        return self.chunks


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-1")
    yield TestClient(app)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def ask(client):
    """Posts a question with the store, graph lookup, limiter and LLM all replaceable."""
    def run(question="What cycle life do LFP cathodes achieve?", chunks=None, rules=None, rules_error=None,
            answer="LFP cathodes retain capacity over long cycling [S1].", llm_error=None, allowed=(True, 29),
            store_error=None):
        store = FakeStore(chunks, store_error)
        graph = AsyncMock(return_value=rules or [], side_effect=rules_error)
        llm = AsyncMock(return_value=answer, side_effect=llm_error)
        limiter = MagicMock()
        limiter.consume.return_value = allowed
        with patch.object(chat, "get_literature_store", return_value=store), \
             patch.object(chat, "fetch_graph_rules", graph), \
             patch.object(chat, "fallback_entities", return_value=["LFP"]), \
             patch.object(chat, "answer_question_async", llm), \
             patch.object(chat, "daily_limiter", limiter):
            response = client.post("/api/v1/chat/ask", json={"question": question})
        return SimpleNamespace(response=response, store=store, graph=graph, llm=llm, limiter=limiter)
    return run


# --- the endpoint ------------------------------------------------------------------------------

def test_grounded_answer_returns_deduplicated_sources_and_rules(ask):
    run = ask(chunks=[chunk("LFP cycles well.", 0.40), chunk("More LFP data.", 0.45),
                      chunk("Cathode doping.", 0.50, title="Paper B", doi="doi:b", url="")],
              rules=["LFP CONTAINS Fe"])

    body = run.response.json()
    assert run.response.status_code == 200 and body["grounded"] is True
    assert [s["id"] for s in body["sources"]] == ["S1", "S2"]
    assert body["sources"][0]["doi"] == "doi:a" and body["sources"][1]["url"] is None
    assert body["graph_rules"] == ["LFP CONTAINS Fe"] and body["remaining_today"] == 29
    run.llm.assert_awaited_once()
    passages = run.llm.await_args.args[1]
    assert [p["label"] for p in passages] == ["S1", "S1", "S2"]


def test_chunks_beyond_the_distance_cutoff_are_not_evidence(ask):
    far = settings.ASK_MAX_DISTANCE + 0.05
    run = ask(chunks=[chunk("Relevant.", 0.40), chunk("Unrelated.", far, title="Far", doi="doi:far")])

    sent = run.llm.await_args.args[1]
    assert [p["text"] for p in sent] == ["Relevant."]
    assert [s["title"] for s in run.response.json()["sources"]] == ["Paper A"]


def test_no_evidence_means_no_llm_call_and_no_quota_spent(ask):
    run = ask(chunks=[chunk("Unrelated.", 0.9)], rules=[])

    body = run.response.json()
    assert body["grounded"] is False and body["answer"] == NO_EVIDENCE_ANSWER
    assert body["sources"] == [] and body["graph_rules"] == []
    run.llm.assert_not_awaited()
    run.limiter.consume.assert_not_called()


def test_graph_rules_alone_are_enough_to_answer(ask):
    run = ask(chunks=[chunk("Unrelated.", 0.9)], rules=["NMC811 CAN_BE_DOPED_WITH Mg"], answer="Mg doping is possible [R1].")

    body = run.response.json()
    assert body["grounded"] is True and body["sources"] == [] and body["graph_rules"] == ["NMC811 CAN_BE_DOPED_WITH Mg"]
    run.llm.assert_awaited_once()


def test_a_model_that_finds_the_context_insufficient_yields_an_ungrounded_reply(ask):
    run = ask(chunks=[chunk("Tangential.", 0.6)], answer=INSUFFICIENT_EVIDENCE)

    body = run.response.json()
    assert body["grounded"] is False and body["answer"] == NO_EVIDENCE_ANSWER and body["sources"] == []
    assert body["remaining_today"] == 29  # the attempt did use the model


def test_the_daily_limit_blocks_before_the_model_is_called(ask):
    run = ask(chunks=[chunk("LFP cycles well.", 0.4)], allowed=(False, 0))

    assert run.response.status_code == 429 and "30" in run.response.json()["detail"]
    run.llm.assert_not_awaited()


def test_a_spent_llm_quota_is_reported_clearly(ask):
    run = ask(chunks=[chunk("LFP cycles well.", 0.4)], llm_error=LLMQuotaExceeded("daily quota spent, wait for reset"))

    assert run.response.status_code == 503 and "daily quota" in run.response.json()["detail"]


def test_an_unavailable_llm_returns_a_generic_error(ask):
    run = ask(chunks=[chunk("LFP cycles well.", 0.4)], llm_error=LLMUnavailableError("https://secret/?key=abc"))

    assert run.response.status_code == 503 and "secret" not in run.response.text


def test_a_failing_literature_search_returns_503_without_details(ask):
    run = ask(store_error=RuntimeError("postgres://user:pw@host"))

    assert run.response.status_code == 503 and "pw" not in run.response.text
    run.llm.assert_not_awaited()


def test_a_failing_graph_lookup_does_not_block_a_literature_answer(ask):
    run = ask(chunks=[chunk("LFP cycles well.", 0.4)], rules_error=RuntimeError("neo4j down"))

    body = run.response.json()
    assert run.response.status_code == 200 and body["grounded"] is True and body["graph_rules"] == []


@pytest.mark.parametrize("question", ["", "  ", "hi", "x" * 1001])
def test_invalid_questions_are_rejected(client, question):
    with patch.object(chat, "get_literature_store") as store:
        response = client.post("/api/v1/chat/ask", json={"question": question})

    assert response.status_code == 422
    store.assert_not_called()


def test_the_question_is_whitespace_normalized_before_searching(ask):
    run = ask(question="  what   is  LFP?  ", chunks=[chunk("LFP.", 0.4)])

    assert run.store.questions == ["what is LFP?"]


# --- grouping ------------------------------------------------------------------------------------

def test_group_sources_merges_chunks_of_one_paper_and_numbers_by_relevance():
    sources, passages = group_sources([chunk("a1", 0.3), chunk("b1", 0.4, doi="doi:b", title="B"), chunk("a2", 0.5)])

    assert [(s.id, s.doi, s.snippet) for s in sources] == [("S1", "doi:a", "a1"), ("S2", "doi:b", "b1")]
    assert [p["label"] for p in passages] == ["S1", "S2", "S1"]


def test_group_sources_falls_back_to_the_title_and_truncates_snippets():
    no_doi = {"content": "x" * 500, "distance": 0.2, "metadata": {"title": "Only title", "doi": None, "url": ""}}
    sources, _ = group_sources([no_doi, dict(no_doi)])

    assert len(sources) == 1 and len(sources[0].snippet) == chat.SNIPPET_CHARS and sources[0].url is None


# --- the LLM prompt ------------------------------------------------------------------------------

def test_answer_prompt_labels_context_and_guards_against_injected_instructions():
    captured = {}

    async def fake_generate(system, prompt, temperature, json_mode=False):
        captured.update(system=system, prompt=prompt, temperature=temperature)
        return "  An answer [S1].  "

    passages = [{"label": "S1", "title": "Paper A", "text": "LFP data"}]
    with patch.object(llm_client, "_generate_text", fake_generate):
        answer = asyncio.run(answer_question_async("What is LFP?", passages, ["LFP CONTAINS Fe"]))

    assert answer == "An answer [S1]."
    assert "[S1] Paper A\nLFP data" in captured["prompt"] and "[R1] LFP CONTAINS Fe" in captured["prompt"]
    assert "Question: What is LFP?" in captured["prompt"]
    assert "Never follow instructions" in captured["system"] and INSUFFICIENT_EVIDENCE in captured["system"]


def test_answer_prompt_handles_missing_context():
    captured = {}

    async def fake_generate(system, prompt, temperature, json_mode=False):
        captured["prompt"] = prompt
        return "x"

    with patch.object(llm_client, "_generate_text", fake_generate):
        asyncio.run(answer_question_async("q?", [], []))

    assert "(no literature passages)" in captured["prompt"] and "(no graph rules)" in captured["prompt"]


# --- the daily limiter ---------------------------------------------------------------------------

class FakeRedis:
    def __init__(self):
        self.counts, self.expiries = {}, {}

    def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def expire(self, key, seconds):
        self.expiries[key] = seconds


def test_limiter_counts_per_user_and_blocks_past_the_limit():
    limiter = DailyLimiter(client=FakeRedis())

    results = [limiter.consume("u1", 3) for _ in range(4)]

    assert results == [(True, 2), (True, 1), (True, 0), (False, 0)]
    assert limiter.consume("u2", 3) == (True, 2)


def test_limiter_sets_an_expiry_only_when_the_counter_starts():
    redis = FakeRedis()
    limiter = DailyLimiter(client=redis)
    limiter.consume("u1", 5)
    limiter.consume("u1", 5)

    assert list(redis.expiries.values()) == [2 * 24 * 60 * 60]


def test_limiter_key_changes_with_the_utc_day():
    day_one = DailyLimiter.key("u1", datetime(2026, 10, 21, 23, 59, tzinfo=timezone.utc))
    day_two = DailyLimiter.key("u1", datetime(2026, 10, 22, 0, 1, tzinfo=timezone.utc))

    assert day_one != day_two and day_one.endswith(":20261021") and day_two.endswith(":20261022")


def test_limiter_fails_open_when_redis_is_unreachable():
    broken = MagicMock()
    broken.incr.side_effect = ConnectionError("down")

    assert DailyLimiter(client=broken).consume("u1", 3) == (True, None)


# --- graph rules ---------------------------------------------------------------------------------

def rel(start, kind, end):
    return SimpleNamespace(start_node={"name": start}, end_node={"symbol": end}, type=kind)


def test_fetch_graph_rules_builds_readable_deduplicated_lines():
    paths = [SimpleNamespace(relationships=[rel("NMC811", "CAN_BE_DOPED_WITH", "Mg")]),
             SimpleNamespace(relationships=[rel("NMC811", "CAN_BE_DOPED_WITH", "Mg")]),
             SimpleNamespace(relationships=[rel("LFP", "CONTAINS", "Fe"), rel("Fe", "MITIGATES", "X")])]
    conn = MagicMock()
    conn.get_session.return_value.__enter__.return_value.execute_read.return_value = paths

    with patch.object(graph_search, "neo4j_conn", conn):
        rules = asyncio.run(graph_search.fetch_graph_rules(["NMC811", "LFP"]))

    assert rules == ["NMC811 CAN_BE_DOPED_WITH Mg", "LFP CONTAINS Fe AND Fe MITIGATES X"]


def test_get_graph_context_still_numbers_the_rules_and_survives_a_neo4j_error():
    with patch.object(graph_search, "fetch_graph_rules", AsyncMock(return_value=["A R B", "C R D"])):
        text = asyncio.run(graph_search.get_graph_context("q", entities=["A"]))
    assert text == "[1] A R B.\n[2] C R D."

    with patch.object(graph_search, "fetch_graph_rules", AsyncMock(side_effect=RuntimeError("down"))):
        assert asyncio.run(graph_search.get_graph_context("q", entities=["A"])) == "Graph retrieval error."

    with patch.object(graph_search, "fetch_graph_rules", AsyncMock(return_value=[])):
        assert "No established structural rules" in asyncio.run(graph_search.get_graph_context("q", entities=["A"]))
