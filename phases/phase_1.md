# Phase 1: Document Processing & Embeddings (Detailed Implementation Plan)

## 1. Objective and Scope
Phase 1 focuses exclusively on the data ingestion pipeline. The goal is to build a highly robust, fault-tolerant system capable of parsing unstructured battery literature (e.g., scientific papers in PDF format, CSV datasets), chunking the text intelligently while preserving complex chemical formulas, generating dense semantic vectors using Hugging Face's `all-MiniLM-L6-v2` model, and persisting these vectors in ChromaDB. This is the foundation of the vector retrieval half of our GraphRAG engine.

---

## 2. Document Ingestion Pipeline (`app/services/ingestion/`)

### 2.1 File Parsing Architecture (`parser.py`)
Scientific literature parsing is notoriously difficult due to two-column layouts, charts, and mathematical notation.
- Implement a `DocumentParser` base class with concrete implementations for `PDFParser`, `TXTParser`, and `CSVParser`.
- **PDF Extraction:** Use `PyMuPDF` (fitz). Implement a heuristic algorithm to identify and strip out:
  - Page headers and footers.
  - The "References" or "Bibliography" section (to prevent the LLM from searching through citations).
  - Acknowledgements.
- **Formula Preservation:** Battery papers contain heavy chemical formulas (e.g., $LiNi_{0.8}Co_{0.1}Mn_{0.1}O_2$). Ensure the parser does not corrupt subscripts. If using OCR, configure it to favor chemical/mathematical parsing.

### 2.2 Advanced Text Chunking (`chunker.py`)
Standard character splitters often cut in the middle of crucial scientific context.
- Implement a custom `SemanticTextSplitter` extending LangChain's `RecursiveCharacterTextSplitter`.
- **Configuration:**
  - `chunk_size = 1000` characters (approx. 200-250 tokens).
  - `chunk_overlap = 200` characters (ensuring context isn't lost across page breaks).
  - `separators = ["\n\n", "\n", ".", " ", ""]` to ensure splits happen at paragraph or sentence boundaries.
- **Validation:** Add a regex check during chunking to ensure a chemical formula (e.g., matched by `[A-Z][a-z]?\d*\.?\d*`) is never split in half.

---

## 3. Hugging Face Embedding Configuration

### 3.1 Model Setup (`app/services/embeddings.py`)
Instead of running heavy local PyTorch installations, we will use the Hugging Face Inference API via ChromaDB's built-in functionality.
- We will configure the embedding function to point to `sentence-transformers/all-MiniLM-L6-v2`.
- **Why this model?** It is exceptionally fast, lightweight (384-dimensional vectors), and highly capable of mapping semantic relationships in scientific text without the latency of OpenAI's `text-embedding-3`.

```python
import os
from chromadb.utils import embedding_functions
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def get_huggingface_embedding_function():
    try:
        if not settings.HF_API_KEY:
            raise ValueError("Hugging Face API key is missing.")
            
        return embedding_functions.HuggingFaceEmbeddingFunction(
            api_key=settings.HF_API_KEY,
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    except Exception as e:
        logger.error(f"Failed to initialize embedding function: {str(e)}")
        raise
```

---

## 4. Vector Database (ChromaDB) Integration

### 4.1 Collection Management (`app/db/chroma_client.py`)
- Connect to the persistent ChromaDB client established in Phase 0.
- Create a collection specifically for battery literature, configured for cosine similarity which works best with Sentence Transformers.

```python
def init_literature_collection(chroma_client):
    """Initializes and returns the battery literature collection."""
    embedding_fn = get_huggingface_embedding_function()
    collection = chroma_client.get_or_create_collection(
        name="battery_literature",
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}  # Crucial for accuracy
    )
    return collection
```

### 4.2 Batch Upsert Logic (`app/services/ingestion/upsert.py`)
When processing hundreds of papers, we cannot send vectors one by one due to network overhead and API rate limits.
- Implement an async `batch_upsert` function.
- Group text chunks into batches of 100.
- Extract and attach structured metadata to each chunk:
  - `paper_title`
  - `year`
  - `authors`
  - `doi`
  - `page_number`
- Generate deterministic UUIDs based on a hash of the `(doi, chunk_index)` to prevent duplication if the same paper is ingested twice.
- Implement exponential backoff for the Hugging Face API if a 429 Too Many Requests response is hit during batch embedding.

---

## 5. Vector Search Verification & Tuning

### 5.1 Query Implementation (`app/services/retrieval/vector_search.py`)
Build a modular function to test the quality of the embeddings and retrieve context.
```python
def search_literature(collection, query: str, n_results: int = 5, filter_metadata: dict = None):
    """
    Searches the ChromaDB collection for the most relevant literature chunks.
    Allows optional metadata filtering (e.g., year > 2020).
    """
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=filter_metadata
    )
    
    # Format the results into a readable list of dictionaries
    formatted_results = []
    for i in range(len(results['documents'][0])):
        formatted_results.append({
            "content": results['documents'][0][i],
            "metadata": results['metadatas'][0][i],
            "distance": results['distances'][0][i]
        })
    return formatted_results
```

---

## 6. Execution and Verification Checklist

To sign off on Phase 1, you must manually complete and verify the following steps:
1. **Data Prep:** Prepare a folder (`/data/raw/papers`) with 5-10 sample battery research papers (PDF). Include papers discussing specific dopants (e.g., Mg doping in NMC).
2. **Ingestion Script:** Run the CLI script `python -m app.scripts.ingest_papers --dir ./data/raw/papers`.
3. **Log Verification:** Check the terminal output to ensure that the PDF parser correctly stripped headers/references, chunked the text, and generated batches of 100 without raising memory errors.
4. **Persistence Check:** Stop the FastAPI server. Verify that the `./chroma_data` directory has increased in size. Restart the server and verify the collection count persists.
5. **Retrieval Test:** Run `python -m app.scripts.test_vector_search "What happens to cycle life when NMC811 is doped with Mg?"`
6. **Relevance Validation:** Verify that the top 5 results are highly relevant text chunks from the ingested papers and that the distances returned indicate strong semantic matches (usually < 0.3 for cosine distance on highly relevant chunks).
