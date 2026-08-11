import chromadb
from chromadb.config import Settings
from app.core.config import settings

def get_chroma_client():
    """Initialize PersistentClient for local ChromaDB."""
    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)

chroma_client = get_chroma_client()

def get_chroma_collection(name: str):
    """Helper to get or create a collection."""
    return chroma_client.get_or_create_collection(name=name)
