"""
agents/graph_builder.py — Graph Builder Agent.

Converts Entity and Relationship objects to Cypher statements,
canonicalizes entities, writes to Neo4j, and exports D3 HTML visualization.

Architecture position: fifth and final node in LangGraph pipeline.
"""
import logging
import os

from config import GRAPH_ARTIFACT_DIR
from graph.neo4j_manager import setup_schema, write_entities, write_relationships
from graph.visualizer import generate_d3_html
from state.agent_state import AgentState
from utils.entity_canon import canonicalize_entities, remap_relationships
from utils.tracing import traceable

logger = logging.getLogger(__name__)


@traceable(name="GraphBuilder::run")
def run_graph_builder(state: AgentState) -> dict:
    """
    Canonicalize entities, write to Neo4j, generate D3 HTML, save artifact.
    Returns delta to merge into AgentState (graph_populated, graph_html, artifact_path).
    """
    run_id = state.get("run_id", "unknown")
    entities_raw = [e.model_dump() for e in state["entities"]]
    relationships_raw = [r.model_dump() for r in state["relationships"]]

    # Canonicalize before Neo4j write
    canonical_entities, merge_map = canonicalize_entities(entities_raw)
    canonical_rels = remap_relationships(relationships_raw, merge_map)

    logger.info(
        f"[GraphBuilder] Writing {len(canonical_entities)} entities, "
        f"{len(canonical_rels)} rels to Neo4j (after canonicalization)"
    )

    setup_schema()

    entity_count = write_entities(canonical_entities, run_id=run_id)
    rel_count = write_relationships(canonical_rels)

    logger.info(f"[GraphBuilder] Neo4j: {entity_count} entities, {rel_count} relationships written")

    title = f"Identity Graph: {state.get('target_name', 'Unknown')}"
    graph_html = generate_d3_html(canonical_entities, canonical_rels, title=title)

    os.makedirs(GRAPH_ARTIFACT_DIR, exist_ok=True)
    artifact_path = os.path.join(GRAPH_ARTIFACT_DIR, f"{run_id}.html")
    with open(artifact_path, "w") as f:
        f.write(graph_html)
    logger.info(f"[GraphBuilder] Saved graph artifact: {artifact_path}")

    return {
        "graph_populated": True,
        "graph_html": graph_html,
        "artifact_path": artifact_path,
    }
