"""
DeepTrace LangGraph pipeline.

Wires SqliteSaver checkpointer into run_pipeline() and stream_pipeline().
Every run has a thread_id (= run_id) for checkpoint isolation.
"""
import os
import logging
import sqlite3
from typing import Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from state.agent_state import AgentState, make_initial_state
from agents.supervisor    import supervisor_plan, supervisor_reflect, supervisor_synthesise, supervisor_route
from agents.scout_agent   import run_scout
from agents.deep_dive_agent import run_deep_dive
from agents.risk_evaluator  import run_risk_evaluator
from agents.graph_builder   import run_graph_builder

logger = logging.getLogger(__name__)


def _get_checkpointer():
    """
    Create and return a SqliteSaver instance.
    Creates the checkpoint directory if it does not exist.
    Registers state.agent_state Pydantic types so checkpoint deserialization is allowed.
    """
    from config import CHECKPOINT_DB_PATH
    db_dir = os.path.dirname(CHECKPOINT_DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    # Register our Pydantic models so msgpack deserialization is allowed and warnings are silenced.
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

    serde = JsonPlusSerializer(
        allowed_msgpack_modules=[
            ("state.agent_state", "Fact"),
            ("state.agent_state", "Entity"),
            ("state.agent_state", "Relationship"),
            ("state.agent_state", "RiskFlag"),
            ("state.agent_state", "Citation"),
        ]
    )

    conn = sqlite3.connect(CHECKPOINT_DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn, serde=serde)
    logger.info(f"[Checkpoint] SqliteSaver configured: {CHECKPOINT_DB_PATH}")
    return checkpointer


def build_graph(checkpointer=None):
    """
    Build and compile the DeepTrace LangGraph StateGraph.

    Args:
        checkpointer: LangGraph checkpointer for state persistence.
                      Defaults to in-memory if None; use SqliteSaver for persistence.
    Returns:
        Compiled LangGraph graph ready for .invoke() or .stream()
    """
    graph = StateGraph(AgentState)

    # ── Register all nodes ────────────────────────────────────────────────────
    graph.add_node("supervisor_plan",    supervisor_plan)
    graph.add_node("scout_agent",        run_scout)
    graph.add_node("deep_dive",          run_deep_dive)
    graph.add_node("supervisor_reflect", supervisor_reflect)
    graph.add_node("risk_evaluator",     run_risk_evaluator)
    graph.add_node("graph_builder",      run_graph_builder)
    graph.add_node("supervisor_synth",   supervisor_synthesise)

    # ── Wire edges ────────────────────────────────────────────────────────────
    graph.add_edge(START,                "supervisor_plan")
    graph.add_edge("supervisor_plan",    "scout_agent")
    graph.add_edge("scout_agent",        "deep_dive")
    graph.add_edge("deep_dive",          "supervisor_reflect")

    # Conditional: loop back to supervisor_plan OR proceed to risk_evaluator
    graph.add_conditional_edges(
        "supervisor_reflect",
        supervisor_route,
        {
            "scout_agent":    "supervisor_plan",   # loop: re-plan and re-search
            "risk_evaluator": "risk_evaluator",    # converged: evaluate risks
        },
    )

    graph.add_edge("risk_evaluator",  "graph_builder")
    graph.add_edge("graph_builder",   "supervisor_synth")
    graph.add_edge("supervisor_synth", END)

    # ── Compile ───────────────────────────────────────────────────────────────
    compiled = graph.compile(checkpointer=checkpointer)
    logger.info("[Pipeline] LangGraph compiled successfully")
    return compiled


def run_pipeline(target_name: str, target_context: str = "") -> AgentState:
    """
    Execute a full research run with checkpointing.
    The run_id from initial_state is used as thread_id for checkpoint isolation.
    Each run is independently resumable.
    """
    initial_state = make_initial_state(target_name, target_context)
    run_id = initial_state["run_id"]

    checkpointer = _get_checkpointer()
    graph = build_graph(checkpointer=checkpointer)

    # thread_id = run_id ensures each run has its own checkpoint namespace
    config = {"configurable": {"thread_id": run_id}}

    # Set audit logger context for this run
    try:
        from utils.audit_logger import set_run_id

        set_run_id(run_id)
    except Exception:
        # Audit logging is best-effort; do not block pipeline
        pass

    logger.info(f"[Pipeline] Starting run_id={run_id} for: {target_name}")
    final_state = graph.invoke(initial_state, config=config)
    logger.info(
        f"[Pipeline] Complete run_id={run_id} | "
        f"facts={len(final_state.get('extracted_facts', []))} | "
        f"flags={len(final_state.get('risk_flags', []))} | "
        f"quality={final_state.get('research_quality', 0):.2f}"
    )
    return final_state


def stream_pipeline(target_name: str, target_context: str = "", run_id: Optional[str] = None):
    """
    Execute with streaming and checkpointing.
    Yields (node_name, state_delta) tuples.
    If run_id is provided (e.g. from Streamlit), it is used for Neo4j isolation.
    """
    initial_state = make_initial_state(target_name, target_context, run_id=run_id)
    run_id = initial_state["run_id"]

    checkpointer = _get_checkpointer()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": run_id}}

    # Set audit logger context for this run
    try:
        from utils.audit_logger import set_run_id

        set_run_id(run_id)
    except Exception:
        pass

    for chunk in graph.stream(initial_state, config=config, stream_mode="updates"):
        node_name = list(chunk.keys())[0]
        node_output = chunk[node_name]
        yield node_name, node_output

    # Yield final merged state for frontend (Report / Graph pages)
    try:
        snap = graph.get_state(config)
        if snap.values:
            yield "final_state", dict(snap.values)
    except Exception as e:
        logger.warning(f"[Pipeline] Could not get final state: {e}")


def resume_pipeline(run_id: str) -> AgentState:
    """
    Resume an interrupted pipeline run from its last checkpoint.
    Used when a run fails mid-way and needs to be restarted.
    """
    checkpointer = _get_checkpointer()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": run_id}}

    logger.info(f"[Pipeline] Resuming run_id={run_id}")
    final_state = graph.invoke(None, config=config)
    return final_state

