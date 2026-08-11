import os
from chromadb import EmbeddingFunction, Documents, Embeddings
from chromadb.utils import embedding_functions
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def get_huggingface_embedding_function():
    try:
        # Use ChromaDB's built-in ONNX runtime to execute all-MiniLM-L6-v2 locally.
        # This bypasses all external API dependencies and network blocking.
        return embedding_functions.DefaultEmbeddingFunction()
    except Exception as e:
        logger.error(f"Failed to initialize embedding function: {str(e)}")
        raise
