"""
agents/supervisor.py — Supervisor Agent for DeepTrace.

Responsibilities:
  - plan(): Generate targeted research queries covering 5 categories
  - reflect(): Score research quality and identify gaps
  - synthesise(): Generate final markdown risk report
  - route(): Decide whether to continue looping or proceed to risk evaluation

In Phase 1 (USE_MOCK=true): all three functions return mock fixtures.
In Phase 2+ (USE_MOCK=false): calls Claude Opus 4.5 with extended thinking.

Architecture position: first and last node in the LangGraph pipeline.
Called by pipeline.py via StateGraph node registration.
"""
import logging
from langsmith import traceable
from config import USE_MOCK, MAX_LOOPS, QUALITY_THRESHOLD, ENV
from state.agent_state import AgentState
from mock_responses import (
    MOCK_SUPERVISOR_LOOP_1,
    MOCK_SUPERVISOR_LOOP_2,
    MOCK_SUPERVISOR_FINAL,
)

logger = logging.getLogger(__name__)


@traceable(name="Supervisor::plan")
def supervisor_plan(state: AgentState) -> dict:
    """
    Generate research queries for the next loop iteration.
    Returns delta to merge into AgentState.
    """
    logger.info(f"[Supervisor::plan] loop={state['loop_count']} target={state['target_name']}")

    if USE_MOCK:
        if state["loop_count"] == 0:
            result = MOCK_SUPERVISOR_LOOP_1
        else:
            result = MOCK_SUPERVISOR_LOOP_2
        logger.info(f"[Supervisor::plan] MOCK: {len(result['research_plan'])} queries generated")
        return {
            "research_plan":  result["research_plan"],
            "gaps_remaining": result["gaps_remaining"],
            "loop_count":     state["loop_count"] + 1,
        }

    # ── Phase 2+: Real Claude Opus 4.5 call ──────────────────────────────────
    raise NotImplementedError("Phase 2: implement real Supervisor LLM call here")


@traceable(name="Supervisor::reflect")
def supervisor_reflect(state: AgentState) -> dict:
    """
    Evaluate research quality after Deep Dive completes.
    Returns updated research_quality and gaps_remaining.
    """
    logger.info(f"[Supervisor::reflect] facts={len(state['extracted_facts'])} loop={state['loop_count']}")

    if USE_MOCK:
        quality = min(0.30 * state["loop_count"], 0.82)
        gaps = [] if quality >= QUALITY_THRESHOLD else ["Offshore entity details unconfirmed"]
        logger.info(f"[Supervisor::reflect] MOCK: quality={quality:.2f}")
        return {
            "research_quality": quality,
            "gaps_remaining":   gaps,
        }

    raise NotImplementedError("Phase 2: implement real Supervisor reflect here")


@traceable(name="Supervisor::synthesise")
def supervisor_synthesise(state: AgentState) -> dict:
    """
    Generate the final markdown risk intelligence report.
    Called once on the final loop.
    """
    logger.info(f"[Supervisor::synthesise] generating report for {state['target_name']}")

    if USE_MOCK:
        report = MOCK_SUPERVISOR_FINAL["final_report"].replace(
            "Timothy Overturf", state["target_name"]
        )
        logger.info("[Supervisor::synthesise] MOCK: report generated")
        return {"final_report": report}

    raise NotImplementedError("Phase 2: implement real Supervisor synthesis here")


def supervisor_route(state: AgentState) -> str:
    """
    LangGraph routing function — decides next node after each supervisor call.
    Returns node name string (NOT Command object) for compatibility.
    """
    max_loops = MAX_LOOPS[ENV]
    quality   = state.get("research_quality", 0.0)
    loop      = state.get("loop_count", 0)

    if loop >= max_loops:
        logger.info(f"[Supervisor::route] Hard stop at loop={loop} (max={max_loops})")
        return "risk_evaluator"

    if quality >= QUALITY_THRESHOLD:
        logger.info(f"[Supervisor::route] Quality threshold met: {quality:.2f}")
        return "risk_evaluator"

    logger.info(f"[Supervisor::route] Continue: loop={loop} quality={quality:.2f}")
    return "scout_agent"
