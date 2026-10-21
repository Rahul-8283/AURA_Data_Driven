from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.db.literature_store import LiteratureStore, vector_literal
from app.scripts.migrate_chroma_to_pgvector import to_store_arguments
from app.services.embeddings import EMBEDDING_DIM


def test_vectors_serialize_to_a_pgvector_literal():
    assert vector_literal([0.5, -1.25, 3.0]) == "[0.5,-1.25,3.0]"


def test_row_promotes_indexed_keys_to_columns_and_keeps_the_rest_as_metadata():
    row = LiteratureStore._row("c1", "text", [0.1, 0.2],
                               {"doi": "arxiv:1", "title_key": "abc", "graph_extracted": True,
                                "source": "arxiv", "chunk_index": 0})

    assert row["doi"] == "arxiv:1" and row["title_key"] == "abc" and row["graph_extracted"] is True
    assert row["metadata"] == {"source": "arxiv", "chunk_index": 0}
    assert row["embedding"] == "[0.1,0.2]"


def test_row_defaults_missing_identifiers_to_null_and_not_extracted():
    row = LiteratureStore._row("c2", "text", [0.0], {"source": "wikipedia"})

    assert row["doi"] is None and row["title_key"] is None and row["graph_extracted"] is False


def test_search_maps_similarity_to_cosine_distance():
    client = MagicMock()
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=[
        {"id": "a", "document": "Mg doping text", "metadata": {"source": "arxiv"}, "similarity": 0.75},
    ])
    hits = LiteratureStore(client=client).search("cathode doping", 1)

    name, params = client.rpc.call_args.args
    assert name == "match_literature_chunks"
    assert params["match_count"] == 1 and params["query_embedding"].startswith("[")
    assert hits == [{"content": "Mg doping text", "metadata": {"source": "arxiv"}, "distance": pytest.approx(0.25)}]


def test_search_tolerates_missing_metadata():
    client = MagicMock()
    client.rpc.return_value.execute.return_value = SimpleNamespace(
        data=[{"id": "a", "document": "x", "metadata": None, "similarity": 1.0}])

    assert LiteratureStore(client=client).search("q")[0]["metadata"] == {}


def test_empty_count_is_zero_not_none():
    client = MagicMock()
    client.table.return_value.select.return_value.execute.return_value = SimpleNamespace(count=None)

    assert LiteratureStore(client=client).count() == 0


def test_exists_is_false_for_an_empty_identifier_set():
    client = MagicMock()
    assert LiteratureStore(client=client).exists(doi=None, title_key=None) is False
    client.table.assert_not_called()


def test_migration_shapes_a_chroma_page_for_the_store():
    args = to_store_arguments(["a"], ["doc"], [None], [[0.1] * EMBEDDING_DIM])

    assert args["ids"] == ["a"] and args["metadatas"] == [{}]
    assert len(args["embeddings"][0]) == EMBEDDING_DIM


def test_migration_rejects_vectors_of_the_wrong_dimension():
    with pytest.raises(ValueError, match="expected 384"):
        to_store_arguments(["a"], ["doc"], [{}], [[0.1, 0.2]])
