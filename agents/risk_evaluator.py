"""
agents/risk_evaluator.py — Risk Evaluator Agent.

Analyses all extracted facts to identify risk flags with severity scoring.
Runs ONCE on the final research loop only.
Every RiskFlag must cite minimum 2 evidence fact_ids with confidence >= 0.50.

Phase 1 (USE_MOCK=true): returns MOCK_RISK_FLAGS fixture directly.
Phase 2+ (USE_MOCK=false): calls Haiku in dev for risk evaluation.

Architecture position: fourth node in LangGraph pipeline, runs after loop convergence.
"""
import json
import logging
from pydantic import ValidationError
from config import USE_MOCK, MODELS, MAX_TOKENS, ENV
from state.agent_state import AgentState, RiskFlag
from state.llm_schemas import RiskEvaluatorResponse
from utils.anthropic_client import call_llm_structured
from prompts.risk_prompt import RISK_EVALUATOR_SYSTEM_PROMPT
from mock_responses import MOCK_RISK_FLAGS
from utils.tracing import traceable

logger = logging.getLogger(__name__)

MIN_EVIDENCE_CONFIDENCE = 0.40   # Facts below this cannot be cited as risk evidence


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

    model = MODELS["risk_evaluator"]
    usable_facts = [
        f for f in state["extracted_facts"]
        if state["confidence_map"].get(f.fact_id, f.confidence) >= MIN_EVIDENCE_CONFIDENCE
    ][:20]

    if not usable_facts:
        logger.warning("[RiskEvaluator] No usable facts — skipping risk evaluation")
        return {"risk_flags": []}

    facts_json = json.dumps([
        {
            "fact_id": f.fact_id,
            "claim": f.claim,
            "category": f.category,
            "confidence": f.confidence,
            "source": f.source_domain,
            "entities": f.entities_mentioned,
        }
        for f in usable_facts
    ], indent=2)

    user_msg = f"""Research target: {state['target_name']}
Total facts: {len(state['extracted_facts'])} | Usable facts: {len(usable_facts)}
Entities mapped: {len(state['entities'])}

VERIFIED FACTS:
{facts_json}

Identify all risk flags from these facts.

Rules:
- Every flag MUST cite at least 2 evidence_fact_ids from the list above
- Only create a flag if the evidence directly supports the risk
- severity: CRITICAL=illegal/sanctions, HIGH=material financial risk,
  MEDIUM=potential conflict/omission, LOW=minor inconsistency
- flag_ids must be unique (r001, r002, ...)"""

    try:
        parsed = call_llm_structured(
            system_prompt=RISK_EVALUATOR_SYSTEM_PROMPT,
            user_message=user_msg,
            model=model,
            max_tokens=MAX_TOKENS[ENV],
            response_model=RiskEvaluatorResponse,
        )

        flags = list(parsed.risk_flags) if parsed.risk_flags else []
        # Filter to only flags with >= 2 evidence (schema should enforce; double-check)
        flags = [f for f in flags if len(f.evidence_fact_ids) >= 2]
    except (ValidationError, Exception) as e:
        logger.warning(f"[RiskEvaluator] Structured parse failed, using no flags: {e}")
        flags = []

    logger.info(f"[RiskEvaluator] Real: {len(flags)} risk flags generated")
    return {"risk_flags": flags}
