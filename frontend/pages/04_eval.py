"""
04_eval.py — Evaluation dashboard for the three test personas.

Runs all 3 evaluation personas and shows pass/fail against expected findings.

Architecture position: calls pipeline.run_pipeline() for each persona.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st

from config import USE_MOCK
from evaluation.eval_set import ALL_EVAL_PERSONAS, SCORING_TARGETS
from pipeline import run_pipeline


st.title("🎯 Evaluation Dashboard")
st.markdown("Three evaluation personas with pre-defined expected findings and scoring targets.")

# Sidebar: runtime mode and scoring targets
st.sidebar.markdown("### Evaluation Mode")
if USE_MOCK:
    st.sidebar.warning(
        "USE_MOCK=true — agents use fixture data. Set USE_MOCK=false in your environment for live LLM evaluation."
    )
else:
    st.sidebar.success("USE_MOCK=false — using live LLM and search stack for evaluation.")

st.sidebar.markdown("### Scoring Targets")
for metric, target in SCORING_TARGETS.items():
    st.sidebar.markdown(f"- **{metric}**: `{target}`")

# Show evaluation personas and their expected ground truth
for persona in ALL_EVAL_PERSONAS:
    with st.expander(f"**{persona['name']}** — {persona['context']}"):
        st.markdown(f"*Context:* {persona['context']}")
        st.markdown("**Expected Facts:**")
        for fact in persona["expected_facts"]:
            st.markdown(f"- {fact}")
        st.markdown("**Expected Risk Levels:**")
        st.markdown(", ".join(f"`{level}`" for level in persona["expected_risk_levels"]))

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

        facts_found = len(state.get("extracted_facts", []))
        flags_found = len(state.get("risk_flags", []))
        quality = float(state.get("research_quality", 0.0))

        expected_facts = persona.get("expected_facts", []) or []
        recall = 0.0
        if expected_facts:
            recall = min(1.0, facts_found / len(expected_facts))

        fact_recall_target = SCORING_TARGETS.get("fact_recall", 0.0)
        pass_fact_recall = recall >= fact_recall_target

        results.append(
            {
                "persona": persona["name"],
                "facts_found": facts_found,
                "flags_found": flags_found,
                "quality": round(quality, 2),
                "fact_recall_estimate": recall,
                "fact_recall_target": fact_recall_target,
                "pass_fact_recall": pass_fact_recall,
            }
        )

        progress.progress(idx / total)

    st.session_state["eval_results"] = results
    st.success("Evaluation run complete. Results are shown below.")

if st.session_state.get("eval_results"):
    st.subheader("Evaluation Results")
    for row in st.session_state["eval_results"]:
        status = "PASS" if row["pass_fact_recall"] else "BELOW TARGET"
        st.markdown(
            f"- **{row['persona']}** — "
            f"Facts: `{row['facts_found']}` | "
            f"Flags: `{row['flags_found']}` | "
            f"Quality: `{row['quality']:.2f}` | "
            f"Fact recall ≈ `{row['fact_recall_estimate']:.0%}` "
            f"(target `{row['fact_recall_target']:.0%}`) — **{status}**"
        )
