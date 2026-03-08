"""
agents/graph_builder.py — Graph Builder Agent.

Converts Entity and Relationship objects to Cypher statements,
writes them to Neo4j, and exports a pyvis HTML visualisation.

Phase 1: Uses mock entity/relationship data but ACTUALLY writes to Neo4j.
Neo4j is the one real external service in Phase 1.

Architecture position: fifth and final node in LangGraph pipeline.
"""
import logging
from langsmith import traceable
from config import USE_MOCK
from state.agent_state import AgentState
from graph.neo4j_manager import setup_schema, write_entities, write_relationships
from graph.visualizer import generate_pyvis_html

logger = logging.getLogger(__name__)


@traceable(name="GraphBuilder::run")
def run_graph_builder(state: AgentState) -> dict:
    """
    Write entities and relationships to Neo4j. Generate pyvis HTML.
    Returns delta to merge into AgentState.
    """
    run_id = state.get("run_id", "unknown")
    entities      = [e.model_dump() for e in state["entities"]]
    relationships = [r.model_dump() for r in state["relationships"]]

    logger.info(f"[GraphBuilder] Writing {len(entities)} entities, {len(relationships)} rels to Neo4j")

    # Neo4j schema setup (idempotent — safe to call every run)
    setup_schema()

    # Write to Neo4j — REAL call even in Phase 1
    entity_count = write_entities(entities, run_id=run_id)
    rel_count    = write_relationships(relationships)

    logger.info(f"[GraphBuilder] Neo4j: {entity_count} entities, {rel_count} relationships written")

    # Generate pyvis HTML for Streamlit
    graph_html = generate_pyvis_html(entities, relationships)

    return {
        "graph_populated": True,
    }
