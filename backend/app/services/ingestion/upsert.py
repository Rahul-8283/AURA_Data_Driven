import hashlib
from tenacity import retry, wait_exponential, stop_after_attempt
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

@retry(
    wait=wait_exponential(multiplier=1, min=4, max=10),
    stop=stop_after_attempt(5)
)
def batch_upsert(store, texts: List[str], metadatas: List[Dict], ids: List[str]):
    """Embed and upsert chunks into pgvector, with exponential backoff on failure."""
    logger.info(f"Upserting batch of {len(texts)} chunks...")
    store.upsert(ids, texts, metadatas)

def process_and_upsert(store, chunks: List[str], base_metadata: Dict, doi: str) -> List[str]:
    """Processes chunks into batches of 100 and upserts them. Returns the chunk ids written."""
    batch_size = 100
    written_ids: List[str] = []
    
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i + batch_size]
        batch_metadatas = []
        batch_ids = []
        
        for j, chunk in enumerate(batch_chunks):
            chunk_index = i + j
            # Deterministic UUID based on hash of DOI and chunk_index
            hash_str = f"{doi}_{chunk_index}"
            chunk_id = hashlib.md5(hash_str.encode()).hexdigest()
            
            meta = base_metadata.copy()
            meta["chunk_index"] = chunk_index
            
            batch_metadatas.append(meta)
            batch_ids.append(chunk_id)
            
        batch_upsert(store, batch_chunks, batch_metadatas, batch_ids)
        written_ids.extend(batch_ids)

    return written_ids
