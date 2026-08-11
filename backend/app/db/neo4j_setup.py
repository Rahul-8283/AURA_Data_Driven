import logging
from app.db.neo4j_client import neo4j_conn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_constraints():
    """
    Sets up strict unique constraints in Neo4j to ensure data integrity
    and prevent duplicated nodes.
    """
    constraints_queries = [
        "CREATE CONSTRAINT element_symbol IF NOT EXISTS FOR (e:Element) REQUIRE e.symbol IS UNIQUE;",
        "CREATE CONSTRAINT material_name IF NOT EXISTS FOR (m:Material) REQUIRE m.name IS UNIQUE;",
        "CREATE CONSTRAINT property_name IF NOT EXISTS FOR (p:Property) REQUIRE p.name IS UNIQUE;",
        "CREATE CONSTRAINT degradation_name IF NOT EXISTS FOR (d:DegradationMode) REQUIRE d.name IS UNIQUE;"
    ]

    logger.info("Initializing Neo4j database constraints...")
    
    try:
        with neo4j_conn.get_session() as session:
            for query in constraints_queries:
                session.run(query)
                logger.info(f"Executed: {query}")
        
        logger.info("Successfully configured all Neo4j constraints.")
    except Exception as e:
        logger.error(f"Failed to setup Neo4j constraints: {e}")
        raise

if __name__ == "__main__":
    setup_constraints()
    neo4j_conn.close()
