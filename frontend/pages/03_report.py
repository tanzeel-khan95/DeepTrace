"""
03_report.py — Risk assessment report page.

Displays the final markdown report with risk flags, facts table,
and PDF download button.

Architecture position: reads from session state or mock data.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from mock_responses import MOCK_SUPERVISOR_FINAL, MOCK_RISK_FLAGS, MOCK_DEEP_DIVE_RESULTS

st.title("📄 Risk Assessment Report")

SEV_COLORS = {"CRITICAL": "#C62828", "HIGH": "#E65100", "MEDIUM": "#F9A825", "LOW": "#546E7A"}
SEV_ICONS  = {"CRITICAL": "⛔", "HIGH": "🔴", "MEDIUM": "🟡", "LOW": "ℹ️"}

# ── Report header ─────────────────────────────────────────────────────────────
target = st.session_state.get("last_target", "Timothy Overturf")
st.markdown(f"### Target: {target}")

risk_flags = MOCK_RISK_FLAGS["risk_flags"]
crit  = sum(1 for f in risk_flags if f["severity"] == "CRITICAL")
high  = sum(1 for f in risk_flags if f["severity"] == "HIGH")
med   = sum(1 for f in risk_flags if f["severity"] == "MEDIUM")
low   = sum(1 for f in risk_flags if f["severity"] == "LOW")

col1, col2, col3, col4 = st.columns(4)
col1.metric("⛔ CRITICAL", crit)
col2.metric("🔴 HIGH",     high)
col3.metric("🟡 MEDIUM",   med)
col4.metric("ℹ️ LOW",       low)

st.divider()

# ── Risk flags ────────────────────────────────────────────────────────────────
st.subheader("Risk Flags")
for flag in risk_flags:
    sev = flag["severity"]
    with st.expander(f"{SEV_ICONS[sev]} [{sev}] {flag['title']}"):
        st.markdown(flag["description"])
        st.markdown(f"**Category:** `{flag['category']}` | **Confidence:** `{flag['confidence']:.0%}`")
        st.markdown(f"**Evidence:** {', '.join(f'`{e}`' for e in flag['evidence_fact_ids'])}")

st.divider()

# ── Full report ────────────────────────────────────────────────────────────────
st.subheader("Intelligence Report")
st.markdown(MOCK_SUPERVISOR_FINAL["final_report"])

st.divider()

# ── Facts table ───────────────────────────────────────────────────────────────
st.subheader("Extracted Facts")
facts = MOCK_DEEP_DIVE_RESULTS["extracted_facts"]
for f in facts:
    conf = f["confidence"]
    color = "#00C080" if conf >= 0.85 else "#F0C000" if conf >= 0.65 else "#FF8000"
    st.markdown(
        f'<small style="color:{color}">▌</small> '
        f'<small><code>{f["fact_id"]}</code></small> '
        f'{f["claim"]} '
        f'<small style="color:#4A6A8A">({f["source_domain"]} · {conf:.0%})</small>',
        unsafe_allow_html=True,
    )
