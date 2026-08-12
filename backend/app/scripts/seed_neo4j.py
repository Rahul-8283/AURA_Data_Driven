import os
import json
import logging
from app.services.graph.ingestion import ingest_triplets
from app.db.neo4j_client import neo4j_conn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_database():
    """
    Reads the ground truth seed_graph.json and inserts it into Neo4j
    to establish foundational battery physics facts.
    """
    seed_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "seed_graph.json")
    
    if not os.path.exists(seed_file_path):
        logger.error(f"Seed file not found at {seed_file_path}")
        return

    try:
        with open(seed_file_path, "r", encoding="utf-8") as f:
            triplets = json.load(f)
            
        logger.info(f"Loaded {len(triplets)} ground-truth relationships from {seed_file_path}")
        ingest_triplets(triplets)
        logger.info("Successfully seeded Neo4j database!")
        
    except Exception as e:
        logger.error(f"Failed to seed database: {e}")
        raise

if __name__ == "__main__":
    seed_database()
    neo4j_conn.close()
