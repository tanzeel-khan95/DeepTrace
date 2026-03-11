"""
eval_set.py — Evaluation set definitions and ground truth for all personas.

Used by LangSmith evaluators in Phase 3+ to score fact recall, risk precision,
and hallucination rate.

Architecture position: imported by langsmith_eval.py and frontend/pages/04_eval.py.
"""
from evaluation.eval_personas import (
    ALL_EVAL_PERSONAS,
    EVAL_PERSONA_SATYA_NADELLA,
    EVAL_PERSONA_ELIZABETH_HOLMES,
    EVAL_PERSONA_SAM_BANKMAN_FRIED,
)

# Re-export for direct import
__all__ = [
    "ALL_EVAL_PERSONAS",
    "EVAL_PERSONA_SATYA_NADELLA",
    "EVAL_PERSONA_ELIZABETH_HOLMES",
    "EVAL_PERSONA_SAM_BANKMAN_FRIED",
]

# Scoring targets (from SRS Section 8.4)
SCORING_TARGETS = {
    "fact_recall":            0.70,   # >= 70% of expected facts found
    "risk_flag_precision":    0.80,   # >= 80% of output flags are justified
    "confidence_calibration": 0.10,   # MSE <= 0.10
    "entity_coverage":        0.80,   # >= 80% of expected entities found
    "false_positive_rate":    0.20,   # <= 20% wrong claims
    "hallucination_rate":     0.10,   # <= 10% unverifiable claims
}
