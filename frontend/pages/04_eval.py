"""
04_eval.py — Evaluation dashboard for the three test personas.

Runs all 3 evaluation personas and shows pass/fail against expected findings.
Phase 1: Uses mock responses to demonstrate the evaluation framework.

Architecture position: calls pipeline.run_pipeline() for each persona.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from mock_responses import ALL_EVAL_PERSONAS

st.title("🎯 Evaluation Dashboard")
st.markdown("Three evaluation personas with pre-defined expected findings.")

for persona in ALL_EVAL_PERSONAS:
    with st.expander(f"**{persona['name']}** — {persona['context']}"):
        st.markdown(f"*Context:* {persona['context']}")
        st.markdown("**Expected Facts:**")
        for fact in persona["expected_facts"]:
            st.markdown(f"- {fact}")
        st.markdown("**Expected Risk Levels:**")
        st.markdown(", ".join(
            f"`{level}`" for level in persona["expected_risk_levels"]
        ))

st.divider()
if st.button("▶ Run Full Evaluation (Mock)"):
    st.info("Phase 1: Evaluation runs on mock data. Phase 3+ integrates LangSmith scoring.")
    for persona in ALL_EVAL_PERSONAS:
        st.markdown(f"**{persona['name']}:** ✅ Mock run complete")
