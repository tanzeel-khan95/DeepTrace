"""
agents/supervisor.py — Supervisor Agent for DeepTrace.

Responsibilities:
  - plan(): Generate targeted research queries covering 5 categories
  - reflect(): Score research quality and identify gaps
  - synthesise(): Generate final markdown risk report
  - route(): Decide whether to continue looping or proceed to risk evaluation

In Phase 1 (USE_MOCK=true): all three functions return mock fixtures.
In Phase 2+ (USE_MOCK=false): calls Claude Haiku 4.5 in dev.

Architecture position: first and last node in the LangGraph pipeline.
Called by pipeline.py via StateGraph node registration.
"""
import json
import logging
from config import USE_MOCK, MAX_LOOPS, QUALITY_THRESHOLD, ENV, MODELS, MAX_TOKENS
from pydantic import ValidationError
from state.agent_state import AgentState
from state.llm_schemas import SupervisorPlanResponse, SupervisorReflectResponse
from utils.anthropic_client import call_llm, call_llm_structured
from prompts.supervisor_prompt import SUPERVISOR_SYSTEM_PROMPT
from mock_responses import (
    MOCK_SUPERVISOR_LOOP_1,
    MOCK_SUPERVISOR_LOOP_2,
    MOCK_SUPERVISOR_FINAL,
)
from utils.tracing import traceable, log_warning_to_run

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

    # ── Phase 2+: Structured LLM call (enforced JSON schema) ─────────────────
    model = MODELS["supervisor"]

    facts = state["extracted_facts"]
    facts_summary = "\n".join(
        f"- [{f.category}] {f.claim} (conf={f.confidence:.2f}, src={f.source_domain})"
        for f in facts[:25]
    ) if facts else "None yet"

    risk_flags = state.get("risk_flags", [])
    risk_summary = "\n".join(
        f"- [{rf.severity}] {rf.title}: {rf.description[:120]}"
        for rf in risk_flags
    ) if risk_flags else "None yet"

    user_msg = f"""Research target: {state['target_name']}
Target context: {state.get('target_context', 'No additional context')}
Loop number: {state['loop_count'] + 1}
Queries already issued: {json.dumps(state['queries_issued'])}
Gaps remaining: {json.dumps(state.get('gaps_remaining', []))}

Key facts discovered so far ({len(facts)} total):
{facts_summary}

Risk signals identified so far:
{risk_summary}

Generate the next batch of targeted research queries. Adapt strategy to the current loop number and findings above."""

    try:

        parsed = call_llm_structured(
            system_prompt=SUPERVISOR_SYSTEM_PROMPT,
            user_message=user_msg,
            model=model,
            max_tokens=MAX_TOKENS[ENV],
            response_model=SupervisorPlanResponse,
        )
        research_plan = list(parsed.research_plan) if parsed.research_plan else []
        gaps_remaining = list(parsed.gaps_remaining) if parsed.gaps_remaining else []

        # Programmatic guardrail: remove any queries that were already issued
        # in previous loops to reduce repetition, even if the model repeats them.
        already_issued = set(state.get("queries_issued", []))
        research_plan = [q for q in research_plan if q not in already_issued]

    except (ValidationError, Exception) as e:
        logger.warning(f"[Supervisor::plan] Structured parse failed, using fallback: {e}")
        log_warning_to_run(f"[Supervisor::plan] Structured parse failed, using fallback: {e}")
        research_plan = [f"{state['target_name']} background career"]
        gaps_remaining = ["General background not yet found"]

    logger.info(f"[Supervisor::plan] Real: {len(research_plan)} queries")
    return {
        "research_plan": research_plan,
        "gaps_remaining": gaps_remaining,
        "loop_count": state["loop_count"] + 1,
    }


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

    model = MODELS["supervisor"]
    facts_summary = "\n".join(
        f"- [{f.category}] {f.claim} (conf={f.confidence:.2f}, src={f.source_domain})"
        for f in state["extracted_facts"][:20]
    )
    user_msg = f"""Research target: {state['target_name']}
Loop: {state['loop_count']}
Total facts extracted: {len(state['extracted_facts'])}
Total entities found: {len(state['entities'])}

Current facts:
{facts_summary if facts_summary else 'None yet'}

Gaps still remaining: {json.dumps(state.get('gaps_remaining', []))}

Score research quality 0.0-1.0 and identify remaining gaps."""

    try:
        parsed = call_llm_structured(
            system_prompt=SUPERVISOR_SYSTEM_PROMPT,
            user_message=user_msg,
            model=model,
            max_tokens=MAX_TOKENS[ENV],
            response_model=SupervisorReflectResponse,
        )
        quality = float(parsed.research_quality)
        gaps = list(parsed.gaps_remaining) if parsed.gaps_remaining else []
    except (ValidationError, Exception) as e:
        logger.warning(f"[Supervisor::reflect] Structured parse failed, using fallback: {e}")
        log_warning_to_run(f"[Supervisor::reflect] Structured parse failed, using fallback: {e}")
        quality = min(0.40 * state["loop_count"], 0.82)
        gaps = []

    logger.info(f"[Supervisor::reflect] Real: quality={quality:.2f} gaps={len(gaps)}")
    return {"research_quality": quality, "gaps_remaining": gaps}


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

    model = MODELS["supervisor"]
    risk_flags_text = "\n".join(
        f"- [{f.severity}] {f.title}: {f.description[:150]}"
        for f in state["risk_flags"]
    )
    facts_text = "\n".join(
        f"- {f.claim} (conf={f.confidence:.0%}, src={f.source_domain})"
        for f in state["extracted_facts"][:15]
    )
    entities_text = ", ".join(e.name for e in state["entities"][:10])

    synth_prompt = f"""You are generating a final intelligence report for a due diligence investigation.

Target: {state['target_name']}
Research loops completed: {state['loop_count']}
Total facts extracted: {len(state['extracted_facts'])}
Total entities mapped: {len(state['entities'])}

KEY FACTS:
{facts_text if facts_text else 'None extracted'}

ENTITY NETWORK:
{entities_text if entities_text else 'None mapped'}

RISK FLAGS IDENTIFIED:
{risk_flags_text if risk_flags_text else 'No risk flags identified'}

Generate a professional markdown risk intelligence report with:
1. Executive Summary (3-4 sentences)
2. Key Findings (bullet list)
3. Risk Flag Summary (table: Severity | Flag | Confidence)
4. Entity Network Summary
5. Confidence Assessment

Be concise. Focus on evidence-backed claims only."""

    raw = call_llm(
        system_prompt=(
            "You are a professional intelligence analyst writing due diligence reports. "
            "Write in clear, professional markdown. Be factual and evidence-based."
        ),
        user_message=synth_prompt,
        model=model,
        max_tokens=MAX_TOKENS[ENV],
        use_cache=False,
    )
    report = raw.strip()
    if not report:
        report = f"# Report: {state['target_name']}\n\nInsufficient data to generate report in Phase 2 dev mode."
    logger.info(f"[Supervisor::synthesise] Real: report={len(report)} chars")
    return {"final_report": report}


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
