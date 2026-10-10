from neo4j import GraphDatabase
from app.core.config import settings

class Neo4jConnection:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
            # Proactively recycle pooled connections before Neo4j Aura's
            # server-side idle timeout drops them, which otherwise surfaces
            # as "Failed to read from defunct connection" on the next query
            # (recovered automatically by the driver's retry, but avoidable).
            max_connection_lifetime=300,
        )

    def close(self):
        if self.driver:
            self.driver.close()

    def verify_connectivity(self):
        """Run a simple cypher query to ensure the database is reachable."""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS num")
                record = result.single()
                if record and record["num"] == 1:
                    return True
        except Exception as e:
            print(f"Neo4j connection failed: {e}")
        return False

    def get_session(self):
        return self.driver.session()

neo4j_conn = Neo4jConnection()
