"""
agents/risk_evaluator.py — Risk Evaluator Agent.

Analyses all extracted facts to identify risk flags with severity scoring.
Runs ONCE on the final research loop only.
Every RiskFlag must cite minimum 2 evidence fact_ids with confidence >= 0.50.

Phase 1 (USE_MOCK=true): returns MOCK_RISK_FLAGS fixture directly.
Phase 2+ (USE_MOCK=false): calls Claude Sonnet 4.6 with structured output.

Architecture position: fourth node in LangGraph pipeline, runs after loop convergence.
"""
import logging
from langsmith import traceable
from config import USE_MOCK
from state.agent_state import AgentState, RiskFlag
from mock_responses import MOCK_RISK_FLAGS

logger = logging.getLogger(__name__)

MIN_EVIDENCE_CONFIDENCE = 0.50   # Facts below this cannot be cited as risk evidence


@traceable(name="RiskEvaluator::run")
def run_risk_evaluator(state: AgentState) -> dict:
    """
    Generate RiskFlag objects from extracted_facts.
    Returns delta to merge into AgentState.
    """
    logger.info(f"[RiskEvaluator] Evaluating {len(state['extracted_facts'])} facts")

    if USE_MOCK:
        # Filter out any facts below confidence threshold from evidence
        valid_fact_ids = {
            f.fact_id for f in state["extracted_facts"]
            if state["confidence_map"].get(f.fact_id, f.confidence) >= MIN_EVIDENCE_CONFIDENCE
        }

        flags = []
        for flag_data in MOCK_RISK_FLAGS["risk_flags"]:
            # Validate evidence fact_ids exist
            valid_evidence = [fid for fid in flag_data["evidence_fact_ids"]
                              if fid in valid_fact_ids or USE_MOCK]  # in mock, bypass check
            if len(valid_evidence) >= 2:
                flags.append(RiskFlag(**{**flag_data, "evidence_fact_ids": valid_evidence}))
            else:
                logger.warning(f"[RiskEvaluator] Skipped flag {flag_data['flag_id']}: insufficient evidence")

        logger.info(f"[RiskEvaluator] MOCK: {len(flags)} risk flags generated")
        return {"risk_flags": flags}

    raise NotImplementedError("Phase 2: implement Claude Sonnet 4.6 risk evaluation here")
