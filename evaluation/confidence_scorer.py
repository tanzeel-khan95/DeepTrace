"""
Three-layer confidence scoring system for extracted facts.

Layer 1: Source domain trust (lookup table — free, instant)
Layer 2: Cross-reference adjustment (count supporting vs contradicting sources)
Layer 3: LLM faithfulness check (optional; when absent, stubbed at 0.75)

Final formula: (L1 × 0.30) + (L2_adjusted × 0.40) + (L3 × 0.30)
"""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# ── Layer 1: Source Domain Trust Scores ──────────────────────────────────────
DOMAIN_TRUST: Dict[str, float] = {
    # Government / Regulatory — highest trust
    "sec.gov":      0.92, "finra.org":  0.92, "ftc.gov":   0.92,
    "cftc.gov":     0.92, "doj.gov":    0.92, "courts.gov":0.90,
    # Major Wire Services
    "reuters.com":  0.85, "apnews.com": 0.85, "bloomberg.com":  0.85,
    "wsj.com":      0.83, "ft.com":     0.82,
    # Established Financial Press
    "barrons.com":  0.78, "cnbc.com":   0.76, "marketwatch.com":0.75,
    "investopedia.com": 0.70,
    # Quality Business Media
    "forbes.com":   0.70, "fortune.com":0.70, "businessinsider.com":0.65,
    "techcrunch.com":0.65,
    # Company Official Sources
    "linkedin.com": 0.60,
    # Default for unknown domains
    "_default":     0.40,
}

# ── Layer 2 Adjustment Multipliers ───────────────────────────────────────────
L2_MULTIPLIERS = {
    "single_source":     0.90,   # Only 1 source — penalise
    "two_sources":       1.00,   # Baseline
    "three_plus":        1.15,   # Corroborated — reward (capped at 0.95 final)
    "one_contradiction": 0.60,   # Conflicting source found
    "two_contradictions":0.30,   # Heavy conflict — cap at 0.30
}

MAX_FINAL_CONFIDENCE = 0.95
MIN_USABLE_CONFIDENCE = 0.50   # Below this: fact is archived, not used in risk flags
DISCARD_THRESHOLD    = 0.30   # Below this: fact is discarded entirely


def get_domain_trust(domain: str) -> float:
    """Layer 1: look up domain trust score."""
    domain = domain.lower().strip()
    # Try exact match first, then root domain
    if domain in DOMAIN_TRUST:
        return DOMAIN_TRUST[domain]
    parts = domain.split(".")
    if len(parts) >= 2:
        root = ".".join(parts[-2:])
        if root in DOMAIN_TRUST:
            return DOMAIN_TRUST[root]
    return DOMAIN_TRUST["_default"]


def apply_cross_reference(l1_score: float, supporting: int, contradicting: int) -> float:
    """Layer 2: adjust L1 score based on source count and contradictions."""
    if contradicting >= 2:
        return min(l1_score * L2_MULTIPLIERS["two_contradictions"], 0.30)
    if contradicting == 1:
        adjusted = l1_score * L2_MULTIPLIERS["one_contradiction"]
    elif supporting >= 3:
        adjusted = l1_score * L2_MULTIPLIERS["three_plus"]
    elif supporting == 2:
        adjusted = l1_score * L2_MULTIPLIERS["two_sources"]
    else:
        adjusted = l1_score * L2_MULTIPLIERS["single_source"]
    return min(adjusted, MAX_FINAL_CONFIDENCE)


def llm_faithfulness_stub() -> float:
    """
    Layer 3 stub when no explicit LLM faithfulness score is provided.
    Returns neutral assumption of 0.75 so final score is not artificially penalised.
    """
    return 0.75


def compute_final_confidence(
    domain: str,
    supporting_count: int = 1,
    contradicting_count: int = 0,
    l3_faithfulness: float = None,
) -> float:
    """
    Compute final 3-layer confidence score for a fact.

    Args:
        domain: Source domain (e.g. 'sec.gov')
        supporting_count: Number of sources supporting this claim
        contradicting_count: Number of sources contradicting this claim
        l3_faithfulness: Optional explicit L3 score. If None, uses stub.

    Returns:
        Final confidence score 0.0–1.0
    """
    l1 = get_domain_trust(domain)
    l2 = apply_cross_reference(l1, supporting_count, contradicting_count)
    l3 = l3_faithfulness if l3_faithfulness is not None else llm_faithfulness_stub()

    final = (l1 * 0.30) + (l2 * 0.40) + (l3 * 0.30)
    final = round(min(final, MAX_FINAL_CONFIDENCE), 4)

    logger.debug(f"[Confidence] domain={domain} L1={l1:.2f} L2={l2:.2f} L3={l3:.2f} → {final:.4f}")
    return final


def classify_confidence(score: float) -> str:
    """Return human-readable confidence tier for a score."""
    if score >= 0.85: return "HIGH"
    if score >= 0.65: return "MEDIUM"
    if score >= 0.50: return "LOW"
    if score >= 0.30: return "UNVERIFIED"
    return "DISCARD"


def score_facts_batch(facts: List[dict]) -> Dict[str, float]:
    """
    Score a list of fact dicts and return a confidence_map {fact_id: score}.
    Used to populate AgentState.confidence_map.
    """
    confidence_map: Dict[str, float] = {}
    for fact in facts:
        score = compute_final_confidence(
            domain=fact.get("source_domain", ""),
            supporting_count=len(fact.get("supporting_fact_ids", [])) + 1,
        )
        confidence_map[fact["fact_id"]] = score
    return confidence_map
