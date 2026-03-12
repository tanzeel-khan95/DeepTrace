"""
Neo4j driver, connection management, schema setup, and graph writes.

Only module that directly calls the Neo4j database. All write operations
come through write_entities() and write_relationships().
"""
import logging
from typing import List, Optional

from neo4j import GraphDatabase, Driver
from graph.schema import CONSTRAINT_STATEMENTS, entity_to_cypher_merge, relationship_to_cypher_merge
from config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE

logger = logging.getLogger(__name__)
_driver: Optional[Driver] = None


def get_driver() -> Driver:
    """Return singleton Neo4j driver. Creates it on first call."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        )
        logger.info(f"[Neo4j] Connected to {NEO4J_URI}")
    return _driver


def test_connection() -> bool:
    """Verify Neo4j is reachable. Called during startup check."""
    try:
        driver = get_driver()
        with driver.session(database=NEO4J_DATABASE) as session:
            result = session.run("RETURN 1 AS ok")
            ok = result.single()["ok"]
            logger.info(f"[Neo4j] Connection test: {ok}")
            return ok == 1
    except Exception as e:
        logger.error(f"[Neo4j] Connection failed: {e}")
        return False


def setup_schema() -> None:
    """Create uniqueness constraints. Safe to call multiple times (IF NOT EXISTS)."""
    driver = get_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
        for stmt in CONSTRAINT_STATEMENTS:
            try:
                session.run(stmt)
                logger.debug(f"[Neo4j] Schema: {stmt[:60]}...")
            except Exception as e:
                logger.warning(f"[Neo4j] Schema stmt skipped: {e}")
    logger.info("[Neo4j] Schema setup complete")


def clear_graph(run_id: str) -> None:
    """Delete all nodes for a specific run_id. Used between test runs."""
    driver = get_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
        session.run("MATCH (n {run_id: $run_id}) DETACH DELETE n", run_id=run_id)
    logger.info(f"[Neo4j] Cleared graph for run_id={run_id}")


def write_entities(entities: List[dict], run_id: str) -> int:
    """
    Write entity list to Neo4j using MERGE (idempotent).
    Returns count of entities written.
    """
    driver = get_driver()
    count = 0
    with driver.session(database=NEO4J_DATABASE) as session:
        for entity in entities:
            cypher = entity_to_cypher_merge(entity)
            # Add run_id to SET clause for isolation between test runs
            cypher += f', n.run_id = "{run_id}"'
            try:
                session.run(cypher)
                count += 1
            except Exception as e:
                logger.error(f"[Neo4j] Entity write failed for {entity.get('name')}: {e}")
    logger.info(f"[Neo4j] Wrote {count}/{len(entities)} entities")
    return count


def write_relationships(relationships: List[dict]) -> int:
    """
    Write relationships to Neo4j using MERGE (idempotent).
    Returns count written.
    """
    driver = get_driver()
    count = 0
    with driver.session(database=NEO4J_DATABASE) as session:
        for rel in relationships:
            cypher = relationship_to_cypher_merge(rel)
            try:
                session.run(cypher)
                count += 1
            except Exception as e:
                logger.error(f"[Neo4j] Relationship write failed {rel}: {e}")
    logger.info(f"[Neo4j] Wrote {count}/{len(relationships)} relationships")
    return count


def fetch_graph_for_run(run_id: str) -> dict:
    """
    Fetch all nodes and edges for a run_id.
    Returns {"nodes": [...], "edges": [...]} for visualizer.
    """
    driver = get_driver()
    nodes, edges = [], []
    with driver.session(database=NEO4J_DATABASE) as session:
        # Nodes
        result = session.run(
            "MATCH (n) WHERE n.run_id = $run_id RETURN n", run_id=run_id
        )
        for record in result:
            n = dict(record["n"])
            nodes.append(n)
        # Relationships
        result = session.run(
            "MATCH (a)-[r]->(b) WHERE a.run_id = $run_id AND b.run_id = $run_id "
            "RETURN a.entity_id AS from_id, b.entity_id AS to_id, type(r) AS rel_type, "
            "r.confidence AS confidence",
            run_id=run_id,
        )
        for record in result:
            edges.append(dict(record))
    return {"nodes": nodes, "edges": edges}


def close() -> None:
    """Close the driver. Call on application shutdown."""
    global _driver
    if _driver:
        _driver.close()
        _driver = None
        logger.info("[Neo4j] Driver closed")
