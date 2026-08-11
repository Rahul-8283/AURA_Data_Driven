import logging
from typing import List, Dict
from app.db.neo4j_client import neo4j_conn

logger = logging.getLogger(__name__)

def merge_relationship(tx, subject_label: str, subject_val: str, predicate: str, object_label: str, object_val: str):
    """
    Safely merges a relationship into Neo4j using parameterized Cypher queries.
    Adjusts the primary key based on the node label (e.g., 'symbol' for Elements).
    """
    # Use 'symbol' as the key for Elements, 'name' for everything else
    s_key = "symbol" if subject_label == "Element" else "name"
    o_key = "symbol" if object_label == "Element" else "name"
    
    query = f"""
    MERGE (s:{subject_label} {{{s_key}: $subject_val}})
    MERGE (o:{object_label} {{{o_key}: $object_val}})
    MERGE (s)-[:{predicate}]->(o)
    """
    tx.run(query, subject_val=subject_val, object_val=object_val)

def ingest_triplets(triplets: List[Dict]):
    """
    Ingests a list of triplet dictionaries in a single database transaction.
    """
    if not triplets:
        return

    logger.info(f"Ingesting {len(triplets)} relationships into Neo4j...")
    try:
        with neo4j_conn.get_session() as session:
            session.execute_write(_ingest_triplets_tx, triplets)
        logger.info("Successfully ingested all triplets.")
    except Exception as e:
        logger.error(f"Failed to ingest triplets: {e}")
        raise

def _ingest_triplets_tx(tx, triplets: List[Dict]):
    for t in triplets:
        merge_relationship(
            tx, 
            t["subject_label"], 
            t["subject"], 
            t["predicate"], 
            t["object_label"], 
            t["object"]
        )
