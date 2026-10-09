import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.agents.nodes.reporter import reporter_node
from app.services.retrieval.graph_search import get_material_graph

CANDIDATES = [
    {
        "composition": "LiNi0.5Mn0.5O2",
        "fitness": 412.5,
        "specific_capacity": 210.0,
        "voltage": 3.9,
        "cycle_life": 1200,
        "cost_estimate_usd_kg": 28.0,
        "reasoning": "Cobalt-free with strong cycle life.",
    }
]


@pytest.mark.asyncio
@patch("app.agents.nodes.reporter.supabase_client")
@patch("app.agents.nodes.reporter.summarize_report_async", new_callable=AsyncMock, return_value="Executive summary text.")
async def test_reporter_node_persists_and_summarizes(_summarize, mock_supabase):
    state = {
        "task_id": "task-123",
        "user_id": "user-456",
        "user_prompt": "Find a cobalt-free cathode",
        "best_candidates": CANDIDATES,
        "generation_history": [{"generation": 1, "best_score": 400.0, "average_score": 200.0}],
        "logs": [],
    }

    new_state = await reporter_node(state)

    assert new_state["final_summary"] == "Executive summary text."
    assert any("executive summary" in log.lower() for log in new_state["logs"])

    mock_supabase.table.assert_any_call("ResearchTasks")
    mock_supabase.table.assert_any_call("SavedMaterials")


@pytest.mark.asyncio
@patch("app.agents.nodes.reporter.supabase_client")
@patch(
    "app.agents.nodes.reporter.summarize_report_async",
    new_callable=AsyncMock,
    side_effect=ValueError("LLM unavailable"),
)
async def test_reporter_node_survives_llm_failure(_summarize, mock_supabase):
    state = {
        "task_id": "task-789",
        "user_id": "user-456",
        "user_prompt": "Find a cobalt-free cathode",
        "best_candidates": CANDIDATES,
        "generation_history": [],
        "logs": [],
    }

    new_state = await reporter_node(state)

    # A graceful fallback summary is written; the node never raises.
    assert "could not be generated" in new_state["final_summary"]
    mock_supabase.table.assert_any_call("ResearchTasks")


def test_get_material_graph_includes_all_parsed_elements():
    """Even elements Neo4j doesn't recognize should still be linked to the synthetic material node."""
    with patch("app.services.retrieval.graph_search.neo4j_conn") as mock_conn:
        mock_session = MagicMock()
        mock_session.execute_read.return_value = [
            {"element": "Ni", "rel_type": "DECREASES", "neighbor_labels": ["Property"], "neighbor_name": "Thermal Stability"},
        ]
        mock_conn.get_session.return_value.__enter__.return_value = mock_session

        graph = get_material_graph("LiNi0.5Mn0.5O2", ["Li", "Ni", "Mn", "O"])

    node_ids = {n["id"] for n in graph["nodes"]}
    assert "LiNi0.5Mn0.5O2" in node_ids
    assert {"Li", "Ni", "Mn", "O"}.issubset(node_ids)
    assert "Thermal Stability" in node_ids

    material_links = [l for l in graph["links"] if l["type"] == "CONTAINS"]
    assert len(material_links) == 4
