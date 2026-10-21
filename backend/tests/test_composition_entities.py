import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.retrieval.graph_search import get_graph_context
from app.services.retrieval.graph_rag import GraphRAGService


@pytest.mark.asyncio
@patch("app.services.retrieval.graph_search.extract_entities", new_callable=AsyncMock)
@patch("app.services.retrieval.graph_search.neo4j_conn")
async def test_provided_entities_skip_llm_extraction(mock_neo4j, mock_extract):
    mock_neo4j.get_session.return_value.__enter__.return_value.execute_read.return_value = []

    context = await get_graph_context("ignored query", entities=["Li", "Ni", "O"])

    mock_extract.assert_not_called()
    assert "Li, Ni, O" in context


@pytest.mark.asyncio
@patch("app.services.retrieval.graph_rag.get_literature_store", return_value=None)
@patch("app.services.retrieval.graph_rag.get_graph_context", new_callable=AsyncMock, return_value="graph")
async def test_retrieve_context_threads_entities_to_graph(mock_graph, _collection):
    await GraphRAGService.retrieve_context("query", entities=["Li", "Mn", "O"])

    mock_graph.assert_awaited_once_with("query", ["Li", "Mn", "O"])
