"""
budget_guard.py — Hard spending cap per environment phase.

Raises RuntimeError if estimated spend exceeds the phase budget.
Called after each LLM response in Phase 2+.

Architecture position: utility called by all agents in non-mock mode.
"""
from config import ENV, PHASE_BUDGET

_total_spent: float = 0.0

def record_spend(input_tokens: int, output_tokens: int, model: str) -> None:
    """Add estimated cost of one LLM call to the running total."""
    global _total_spent
    # Approximate pricing — update for Phase 2
    PRICE_PER_1M = {
        "claude-opus-4-5-20251101":   {"in": 5.00,  "out": 25.00},
        "claude-sonnet-4-6-20251120": {"in": 3.00,  "out": 15.00},
        "claude-haiku-4-5-20251001":  {"in": 1.00,  "out": 5.00},
        "gpt-4.1":                    {"in": 2.00,  "out": 8.00},
        "gpt-4.1-mini":               {"in": 0.40,  "out": 1.60},
        "gemini-2.5-pro":             {"in": 1.25,  "out": 10.00},
        "llama-3.3-70b-versatile":    {"in": 0.59,  "out": 0.79},
    }
    p = PRICE_PER_1M.get(model, {"in": 5.00, "out": 25.00})
    cost = (input_tokens / 1_000_000 * p["in"]) + (output_tokens / 1_000_000 * p["out"])
    _total_spent += cost
    _check_budget()

def _check_budget() -> None:
    limit = PHASE_BUDGET.get(ENV, 10.0)
    if _total_spent > limit:
        raise RuntimeError(
            f"[BudgetGuard] Spend ${_total_spent:.4f} exceeded ${limit:.2f} limit for ENV={ENV}. "
            f"Raise ENV to 'staging' or increase PHASE_BUDGET to continue."
        )

def get_total_spent() -> float:
    return _total_spent


def spend_summary() -> str:
    """Return human-readable spend summary for CLI and Streamlit display."""
    limit = PHASE_BUDGET.get(ENV, 10.0)
    pct = (_total_spent / limit * 100) if limit > 0 else 0
    return (
        f"Spend: ${_total_spent:.4f} / ${limit:.2f} limit "
        f"({pct:.1f}% of {ENV} budget)"
    )


def reset() -> None:
    global _total_spent
    _total_spent = 0.0
