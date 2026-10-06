import chromadb
from chromadb.config import Settings
from app.core.config import settings

def get_chroma_client():
    """Initialize PersistentClient for local ChromaDB."""
    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)

chroma_client = get_chroma_client()

_literature_collection = None

def get_chroma_collection(name: str):
    """Helper to get or create a collection."""
    return chroma_client.get_or_create_collection(name=name)

def init_literature_collection(client=None):
    """Initializes and returns the battery literature collection."""
    global _literature_collection
    if client is None and _literature_collection is not None:
        return _literature_collection
    use_default = client is None
    if use_default:
        client = chroma_client
    from app.services.embeddings import get_huggingface_embedding_function
    embedding_fn = get_huggingface_embedding_function()
    collection = client.get_or_create_collection(
        name="battery_literature",
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}  # Crucial for accuracy
    )
    if use_default:
        _literature_collection = collection
    return collection
