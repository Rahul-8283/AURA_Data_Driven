from functools import lru_cache
from typing import List

from fastembed import TextEmbedding

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    return TextEmbedding(EMBEDDING_MODEL)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Normalized 384-dimensional all-MiniLM-L6-v2 embeddings, computed locally with ONNX."""
    if not texts:
        return []
    return [vector.tolist() for vector in _model().embed(texts)]
