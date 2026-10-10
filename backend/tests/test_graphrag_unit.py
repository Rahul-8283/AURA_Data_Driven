import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from app.services.retrieval.graph_rag import GraphRAGService

@pytest.mark.asyncio
async def test_retrieve_context_fusion():
    """
    Tests that GraphRAGService correctly fires both Graph and Vector tasks
    concurrently and successfully merges them into the required strict template format.
    """
    query = "What happens to the thermal stability of LCO when doped with Aluminum?"
    
    mock_graph_output = "[1] LCO CONTAINS Li.\n[2] LCO CAN_BE_DOPED_WITH Al."
    mock_vector_output = "[1] (Source: test.pdf): Doping LCO with Al improves stability."
    
    # We patch the two retrieval functions so they don't actually hit the databases
    with patch("app.services.retrieval.graph_rag.get_graph_context", new_callable=AsyncMock) as mock_graph:
        with patch("app.services.retrieval.graph_rag.get_vector_context", new_callable=AsyncMock) as mock_vector:
            
            # Also patch Chroma init so it doesn't spin up the database
            with patch("app.services.retrieval.graph_rag.init_literature_collection") as mock_init_chroma:
                mock_init_chroma.return_value = "MockCollectionObject"
                
                # Make the mocked functions return our dummy strings
                mock_graph.return_value = mock_graph_output
                mock_vector.return_value = mock_vector_output
                
                # Execute the service
                combined_context = await GraphRAGService.retrieve_context(query)
                
                # Assertions
                mock_graph.assert_called_once_with(query, None)
                mock_vector.assert_called_once_with("MockCollectionObject", query, n_results=5)
                
                # Verify the final template format
                assert "=== STRUCTURAL GRAPH RULES (Absolute Truths) ===" in combined_context
                assert "=== LITERATURE EVIDENCE (Contextual Findings) ===" in combined_context
                assert mock_graph_output in combined_context
                assert mock_vector_output in combined_context

@pytest.mark.asyncio
async def test_retrieve_context_token_trimming():
    """
    Tests that the word-limit truncation logic safely cuts off excessive
    vector context to protect the LLM.
    """
    query = "Trim test query"
    
    # Create a vector output that is exactly 3005 words long
    word = "word "
    massive_vector_output = word * 3005
    
    with patch("app.services.retrieval.graph_rag.get_graph_context", new_callable=AsyncMock) as mock_graph:
        with patch("app.services.retrieval.graph_rag.get_vector_context", new_callable=AsyncMock) as mock_vector:
            with patch("app.services.retrieval.graph_rag.init_literature_collection"):
                mock_graph.return_value = "Graph Result"
                mock_vector.return_value = massive_vector_output
                
                combined_context = await GraphRAGService.retrieve_context(query)
                
                # Ensure the truncation text was added
                assert "[...Truncated for length...]" in combined_context
                
                # The total words should be around 3000 from the vector, plus the template words
                words = combined_context.split()
                # Should be severely restricted compared to the raw string
                assert len(words) < 3050 
