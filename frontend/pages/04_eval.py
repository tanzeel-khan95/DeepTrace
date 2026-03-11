"""
04_eval.py — Evaluation dashboard for test personas.

Runs evaluation personas and shows pass/fail per criterion with expected vs actual.

Architecture position: calls pipeline.run_pipeline() for each persona.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st

from evaluation.eval_set import ALL_EVAL_PERSONAS, SCORING_TARGETS
from pipeline import run_pipeline

FACT_RECALL_TARGET = SCORING_TARGETS.get("fact_recall", 0.70)
RISK_FLAG_PRECISION_TARGET = SCORING_TARGETS.get("risk_flag_precision", 0.80)


def _compute_criteria(persona, state):
    """Compute expected vs actual and pass/fail for each criterion."""
    expected_facts = persona.get("expected_facts", []) or []
    expected_fact_count = len(expected_facts)
    expected_flag_count = int(persona.get("expected_flag_count", 0))
    expected_risk_score = float(persona.get("expected_risk_score", 0))

    facts_found = len(state.get("extracted_facts", []))
    flags_found = len(state.get("risk_flags", []))
    quality = float(state.get("research_quality", 0.0))

    # Fact recall: % of expected facts “covered” (proxy: facts_found / expected_fact_count, cap 1.0)
    if expected_fact_count > 0:
        fact_recall_actual = min(1.0, facts_found / expected_fact_count)
    else:
        fact_recall_actual = 1.0 if facts_found == 0 else 0.5
    fact_recall_met = fact_recall_actual >= FACT_RECALL_TARGET

    # Risk flag recall: found vs expected count (at least as many as expected)
    if expected_flag_count > 0:
        flag_recall_actual = min(1.0, flags_found / expected_flag_count)
        flag_count_met = flags_found >= expected_flag_count
    else:
        flag_recall_actual = 1.0 if flags_found == 0 else 0.5
        flag_count_met = flags_found == 0

    # Research quality: compare 0–1 score to expected_risk_score (0–100 scale)
    quality_pct = round(quality * 100, 1)
    quality_met = quality_pct >= (expected_risk_score * 0.85) if expected_risk_score else True

    return {
        "persona_name": persona["name"],
        "persona_context": persona.get("context", ""),
        "expected_fact_count": expected_fact_count,
        "expected_flag_count": expected_flag_count,
        "expected_risk_score": expected_risk_score,
        "facts_found": facts_found,
        "flags_found": flags_found,
        "quality": round(quality, 3),
        "quality_pct": quality_pct,
        "fact_recall_actual": fact_recall_actual,
        "fact_recall_met": fact_recall_met,
        "flag_recall_actual": flag_recall_actual,
        "flag_count_met": flag_count_met,
        "quality_met": quality_met,
        "criteria": [
            {
                "name": "Fact recall",
                "description": "Share of expected facts covered (target ≥ {:.0%})".format(FACT_RECALL_TARGET),
                "expected": f"≥ {FACT_RECALL_TARGET:.0%} (based on {expected_fact_count} expected facts)",
                "actual": f"{fact_recall_actual:.1%} ({facts_found} facts found)",
                "met": fact_recall_met,
            },
            {
                "name": "Risk flag count",
                "description": "Number of risk flags identified",
                "expected": f"{expected_flag_count}",
                "actual": f"{flags_found}",
                "met": flag_count_met,
            },
            {
                "name": "Research quality",
                "description": "Composite quality score (0–100)",
                "expected": f"≥ {expected_risk_score:.0f}",
                "actual": f"{quality_pct:.1f}",
                "met": quality_met,
            },
        ],
    }


st.title("🎯 Evaluation Dashboard")
st.markdown("Evaluation personas with expected findings and per-criterion expected vs actual.")

# Show evaluation personas and their expected ground truth
for persona in ALL_EVAL_PERSONAS:
    risk_level = persona.get("risk_level")
    title = f"**{persona['name']}** — {persona['context']}"
    if risk_level:
        title = f"{title} — `{risk_level.upper()} RISK`"

    with st.expander(title):
        st.markdown(f"*Context:* {persona['context']}")

        if "due_diligence" in persona:
            st.markdown("**Ground Truth – Due Diligence**")
            st.json(persona["due_diligence"])

        if "risk_flags_ground_truth" in persona:
            st.markdown("**Risk Flags (Ground Truth)**")
            st.json(persona["risk_flags_ground_truth"])

        expected_facts = persona.get("expected_facts")
        if expected_facts:
            st.markdown("**Expected Facts (Summary):**")
            for fact in expected_facts:
                st.markdown(f"- {fact}")

        expected_levels = persona.get("expected_risk_levels")
        if expected_levels:
            st.markdown("**Expected Risk Levels:**")
            st.markdown(", ".join(f"`{level}`" for level in expected_levels))

        st.markdown("**Expected metrics:**")
        st.markdown(f"- Expected facts: `{len(persona.get('expected_facts') or [])}` · Expected flags: `{persona.get('expected_flag_count', 0)}` · Expected risk score: `{persona.get('expected_risk_score', 0)}`")

st.divider()
st.subheader("Run Full Evaluation")

if "eval_results" not in st.session_state:
    st.session_state["eval_results"] = None

if st.button("▶ Run Full Evaluation"):
    total = len(ALL_EVAL_PERSONAS)
    progress = st.progress(0.0)
    results = []

    for idx, persona in enumerate(ALL_EVAL_PERSONAS, start=1):
        st.markdown(f"**Running pipeline for:** `{persona['name']}` — {persona['context']}")
        state = run_pipeline(persona["name"], persona["context"])
        results.append(_compute_criteria(persona, state))
        progress.progress(idx / total)

    st.session_state["eval_results"] = results
    st.success("Evaluation run complete. Results are shown below.")

if st.session_state.get("eval_results"):
    st.subheader("Evaluation Results")
    results = st.session_state["eval_results"]

    for row in results:
        n_met = sum(1 for c in row["criteria"] if c["met"])
        n_criteria = len(row["criteria"])
        overall = "PASS" if n_met == n_criteria else "PARTIAL" if n_met > 0 else "BELOW TARGET"

        ctx_short = row["persona_context"][:50] + ("…" if len(row["persona_context"]) > 50 else "")
        with st.expander(f"**{row['persona_name']}** — {ctx_short} — **{overall}** ({n_met}/{n_criteria} criteria met)"):
            st.markdown("#### Detail: expected vs actual")
            for c in row["criteria"]:
                status = "✅ Met" if c["met"] else "❌ Not met"
                st.markdown(f"**{c['name']}** — {status}")
                st.caption(c["description"])
                st.markdown(f"- **Expected:** {c['expected']}")
                st.markdown(f"- **Actual:** {c['actual']}")
                st.divider()

            st.markdown("#### Summary")
            st.markdown(
                f"| Metric | Expected | Actual |"
            )
            st.markdown("|--------|----------|--------|")
            st.markdown(f"| Facts found | {row['expected_fact_count']} (recall ≥ {FACT_RECALL_TARGET:.0%}) | {row['facts_found']} ({row['fact_recall_actual']:.1%}) |")
            st.markdown(f"| Risk flags | {row['expected_flag_count']} | {row['flags_found']} |")
            st.markdown(f"| Research quality (0–100) | ≥ {row['expected_risk_score']:.0f} | {row['quality_pct']:.1f} |")
