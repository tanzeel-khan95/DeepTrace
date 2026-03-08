"""
pipeline.py — LangGraph StateGraph pipeline assembly for DeepTrace.

Wires all 5 agents into a directed graph with conditional routing.
The Supervisor controls loop continuation via supervisor_route().

Graph flow:
  START → supervisor_plan → scout_agent → deep_dive → supervisor_reflect
        → [loop back OR proceed] → risk_evaluator → graph_builder
        → supervisor_synthesise → END

Architecture position: imported by main.py and Streamlit pages.
"""
import logging
from langgraph.graph import StateGraph, START, END

from state.agent_state import AgentState, make_initial_state
from agents.supervisor    import supervisor_plan, supervisor_reflect, supervisor_synthesise, supervisor_route
from agents.scout_agent   import run_scout
from agents.deep_dive_agent import run_deep_dive
from agents.risk_evaluator  import run_risk_evaluator
from agents.graph_builder   import run_graph_builder

logger = logging.getLogger(__name__)


def build_graph(checkpointer=None):
    """
    Build and compile the DeepTrace LangGraph StateGraph.

    Args:
        checkpointer: LangGraph checkpointer for state persistence.
                      Defaults to in-memory for Phase 1.
                      Use SqliteSaver for Phase 2+ to avoid losing state.
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
    Execute a full research run synchronously.
    Returns the final AgentState after pipeline completion.
    """
    initial_state = make_initial_state(target_name, target_context)
    graph = build_graph()

    logger.info(f"[Pipeline] Starting run for: {target_name}")
    final_state = graph.invoke(initial_state)
    logger.info(f"[Pipeline] Run complete. Quality: {final_state.get('research_quality', 0):.2f}")
    return final_state


def stream_pipeline(target_name: str, target_context: str = ""):
    """
    Execute a research run with streaming updates.
    Yields (node_name, state_delta) tuples for Streamlit live display.
    """
    initial_state = make_initial_state(target_name, target_context)
    graph = build_graph()

    for chunk in graph.stream(initial_state, stream_mode="updates"):
        node_name   = list(chunk.keys())[0]
        node_output = chunk[node_name]
        yield node_name, node_output
