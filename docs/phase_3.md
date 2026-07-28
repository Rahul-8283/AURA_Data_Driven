# Phase 3: Document Processing & Embeddings (Detailed Implementation Plan)

## 1. Objective and Scope
Phase 3 focuses on the data ingestion pipeline. We need to parse unstructured battery literature (PDFs, scientific text), chunk the text intelligently, generate dense semantic vectors using Hugging Face's `all-MiniLM-L6-v2` model, and store these vectors persistently in ChromaDB. This forms the retrieval half of our GraphRAG engine.

---

## 2. Document Ingestion Pipeline (`app/services/ingestion/`)

### 2.1 File Parsing (`parser.py`)
- Implement utilities to read `.txt`, `.pdf`, and `.csv` files (for dataset metadata).
- For PDFs (e.g., downloaded from arXiv or specific journals), use libraries like `PyMuPDF` (fitz) or `pdfplumber` to extract raw text while stripping out useless headers, footers, and references.
- **Crucial Step:** Battery papers contain heavy chemical formulas. Ensure the parser does not corrupt subscripts (e.g., LiCoO2 must remain intact).

### 2.2 Text Chunking (`chunker.py`)
Because LLMs have context windows and embedding models have max token limits (usually 384 or 512 for MiniLM), we must chunk the text.
- We will implement a custom `RecursiveCharacterTextSplitter` (similar to LangChain's logic).
- **Parameters:**
  - `chunk_size = 1000` characters.
  - `chunk_overlap = 200` characters (to maintain context across page breaks).
- Ensure chunks do not break mid-sentence, especially around complex chemical formulas.

---

## 3. Hugging Face Embedding Configuration

### 3.1 Model Setup (`app/services/embeddings.py`)
Instead of running heavy local PyTorch installations, we will use the Hugging Face Inference API via ChromaDB's built-in functionality, OR via the standard `requests` library if more control is needed.

- We will configure the embedding function to point to `sentence-transformers/all-MiniLM-L6-v2`.
- **Why this model?** It is exceptionally fast, lightweight, and highly capable of mapping semantic relationships in scientific text.

```python
from chromadb.utils import embedding_functions
from app.core.config import settings

def get_huggingface_embedding_function():
    return embedding_functions.HuggingFaceEmbeddingFunction(
        api_key=settings.HF_API_KEY,
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
```

---

## 4. Vector Database (ChromaDB) Integration

### 4.1 Collection Management (`app/db/chroma_client.py`)
- Connect to the persistent ChromaDB client established in Phase 1.
- Create a collection specifically for battery literature.

```python
def init_literature_collection(chroma_client):
    embedding_fn = get_huggingface_embedding_function()
    collection = chroma_client.get_or_create_collection(
        name="battery_literature",
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}  # Optimal for sentence transformers
    )
    return collection
```

### 4.2 Batch Upsert Logic (`app/services/ingestion/upsert.py`)
When processing hundreds of papers, we cannot send vectors one by one (API rate limits).
- Implement a batching mechanism to group text chunks into batches of 100.
- Extract metadata for each chunk (e.g., `paper_title`, `year`, `authors`, `doi`).
- Generate unique UUIDs for each chunk to prevent duplication.
- Call `collection.upsert(documents=[...], metadatas=[...], ids=[...])`.

---

## 5. Vector Search Verification

### 5.1 Query Implementation (`app/services/retrieval/vector_search.py`)
Build a function to test the quality of the embeddings.
- Implement `search_literature(query: str, n_results: int = 5)`.
- The function will pass the user query (e.g., "What are the common dopants for NMC811 cathodes to prevent cation mixing?") through the Hugging Face embedding function and perform a vector similarity search in ChromaDB.

---

## 6. Execution and Verification Checklist
1. Prepare a folder with 5-10 sample battery research papers (PDF or TXT).
2. Run a CLI script (e.g., `python -m app.scripts.ingest_papers`) to parse and chunk the documents.
3. Verify that the Hugging Face API key is correctly generating vectors without throwing authentication errors.
4. Verify that ChromaDB creates the `./chroma_data` directory and populates it with SQLite/Parquet files.
5. Run a test query script to search for a specific battery term; verify that the top 5 results are highly relevant text chunks from the ingested papers.
