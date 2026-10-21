"""Offline discovery run: the real LangGraph pipeline with a fake LLM and no network.

Counts LLM requests per provider so the free-tier budget can be checked without
spending quota. Usage (from backend/):
    uv run python -m app.scripts.simulate_discovery_run --generations 3
"""
import argparse
import asyncio
import json
import random
import re
import sys
from collections import Counter
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.agents.state import init_research_state
from app.agents.workflow import app_graph, recursion_limit
from app.core.config import settings

calls: Counter = Counter()


def _answer(prompt: str) -> str:
    if "Predict the properties of EVERY" in prompt:
        indices = re.findall(r"### Material index (\d+)", prompt)
        return json.dumps([
            {"index": int(i), "specific_capacity": random.uniform(180, 230), "voltage": 3.8,
             "cycle_life": 1000, "cost_estimate_usd_kg": 25.0, "reasoning": "simulated"}
            for i in indices
        ])
    if "For EACH candidate" in prompt:
        indices = re.findall(r"### Candidate index (\d+)", prompt)
        return json.dumps([{"index": int(i), "is_valid": True} for i in indices])
    return "Simulated executive summary."


class FakeCompletions:
    async def create(self, model, messages, temperature):
        calls["openrouter_batch"] += 1
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=_answer(messages[-1]["content"])))])


class FakeClient:
    chat = SimpleNamespace(completions=FakeCompletions())

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False


def _requests_post(url, **_kwargs):
    response = MagicMock()
    response.raise_for_status.return_value = None
    if "openrouter.ai" in url:
        calls["planner"] += 1
        planner_json = {"target_properties": {"capacity_gt": 200}, "base_material_class": "NMC_Cathode", "excluded_elements": []}
        response.json.return_value = {"choices": [{"message": {"content": json.dumps(planner_json)}}]}
    else:
        calls["gemini"] += 1
        response.json.return_value = {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}
    return response


async def _run_graph(state: dict, live: bool) -> dict:
    with patch("app.agents.nodes.reporter.supabase_client", MagicMock()):
        if live:
            return await app_graph.ainvoke(state, config={"recursion_limit": recursion_limit(settings.GA_GENERATIONS)})
        with patch("app.services.llm.client.get_client", return_value=FakeClient()), \
             patch("app.agents.nodes.planner.requests.post", side_effect=_requests_post), \
             patch("app.services.llm.client.requests.post", side_effect=_requests_post), \
             patch("app.services.retrieval.graph_rag.init_literature_collection", return_value=None), \
             patch("app.services.retrieval.graph_search.neo4j_conn") as neo4j:
            neo4j.get_session.return_value.__enter__.return_value.execute_read.return_value = []
            return await app_graph.ainvoke(state, config={"recursion_limit": recursion_limit(settings.GA_GENERATIONS)})


async def run(generations: int, live: bool) -> int:
    settings.GA_GENERATIONS = generations
    random.seed(1)
    state = init_research_state("sim-task", "Cobalt-free cathode with high capacity", "sim-user")
    final = await _run_graph(state, live)

    if live:
        print(f"generations run:     {final['current_generation']} / {generations}")
        print(f"final population:    {len(final['current_population'])}")
        for mat in final["best_candidates"][:3]:
            print(f"  {mat['composition']}: capacity={mat['specific_capacity']:.0f} mAh/g, fitness={mat['fitness']:.1f}")
        print("log tail:", *final["logs"][-3:], sep="\n  ")
        return 0

    total = sum(calls.values())
    budget = 2 + 3 * generations
    print(f"generations run:     {final['current_generation']} / {generations}")
    print(f"final population:    {len(final['current_population'])}")
    print(f"best fitness:        {round(final['best_candidates'][0]['fitness'], 2) if final['best_candidates'] else 0}")
    print(f"LLM requests:        {total}  {dict(calls)}")
    print(f"budget (2 + 3/gen):  {budget}")
    ok = total <= budget and calls["gemini"] == 0
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generations", type=int, default=3)
    parser.add_argument("--live", action="store_true", help="use real OpenRouter, Neo4j and ChromaDB (spends quota)")
    args = parser.parse_args()
    sys.exit(asyncio.run(run(args.generations, args.live)))
