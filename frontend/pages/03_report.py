"""
03_report.py — Risk assessment report page.

Displays the final markdown report with risk flags, facts table,
and PDF download button. Uses real run data from session state when
available (from last Research run); otherwise falls back to mock data.

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


def _get(f, key, default=None):
    """Get attribute from Pydantic model or dict (RiskFlag / dict)."""
    if isinstance(f, dict):
        return f.get(key, default)
    return getattr(f, key, default)


def _flag_severity(f):
    return _get(f, "severity", "?")


def _flag_title(f):
    return _get(f, "title", str(f))


def _flag_description(f):
    return _get(f, "description", "")


def _flag_category(f):
    return _get(f, "category", "")


def _flag_confidence(f):
    return _get(f, "confidence", 0)


def _flag_evidence(f):
    return _get(f, "evidence_fact_ids", []) or []


# ── Report header ─────────────────────────────────────────────────────────────
target = st.session_state.get("last_target", "")
if not target:
    target = "No target run yet"
st.markdown(f"### Target: {target}")

# Use real run data from session state when available (after a Research run)
if st.session_state.get("run_complete") and "risk_flags" in st.session_state:
    risk_flags = st.session_state["risk_flags"]
else:
    risk_flags = MOCK_RISK_FLAGS["risk_flags"]

crit  = sum(1 for f in risk_flags if _flag_severity(f) == "CRITICAL")
high  = sum(1 for f in risk_flags if _flag_severity(f) == "HIGH")
med   = sum(1 for f in risk_flags if _flag_severity(f) == "MEDIUM")
low   = sum(1 for f in risk_flags if _flag_severity(f) == "LOW")

col1, col2, col3, col4 = st.columns(4)
col1.metric("⛔ CRITICAL", crit)
col2.metric("🔴 HIGH",     high)
col3.metric("🟡 MEDIUM",   med)
col4.metric("ℹ️ LOW",       low)

st.divider()

# ── Risk flags ────────────────────────────────────────────────────────────────
st.subheader("Risk Flags")
for flag in risk_flags:
    sev = _flag_severity(flag)
    title = _flag_title(flag)
    with st.expander(f"{SEV_ICONS.get(sev, '')} [{sev}] {title}"):
        st.markdown(_flag_description(flag))
        st.markdown(f"**Category:** `{_flag_category(flag)}` | **Confidence:** `{_flag_confidence(flag):.0%}`")
        st.markdown(f"**Evidence:** {', '.join(f'`{e}`' for e in _flag_evidence(flag))}")

st.divider()

# ── Full report ────────────────────────────────────────────────────────────────
st.subheader("Intelligence Report")
if st.session_state.get("run_complete") and st.session_state.get("final_report"):
    st.markdown(st.session_state["final_report"])
else:
    report = MOCK_SUPERVISOR_FINAL["final_report"]
    if target and target != "No target run yet":
        report = report.replace("Timothy Overturf", target)
    st.markdown(report)

st.divider()

# ── Facts table ───────────────────────────────────────────────────────────────
st.subheader("Extracted Facts")
if st.session_state.get("run_complete") and "extracted_facts" in st.session_state:
    facts = st.session_state["extracted_facts"]
else:
    facts = MOCK_DEEP_DIVE_RESULTS["extracted_facts"]

for f in facts:
    if hasattr(f, "confidence"):
        conf = f.confidence
        claim = getattr(f, "claim", "")
        fact_id = getattr(f, "fact_id", "")
        source_domain = getattr(f, "source_domain", "")
    else:
        conf = f.get("confidence", 0)
        claim = f.get("claim", "")
        fact_id = f.get("fact_id", "")
        source_domain = f.get("source_domain", "")
    color = "#00C080" if conf >= 0.85 else "#F0C000" if conf >= 0.65 else "#FF8000"
    st.markdown(
        f'<small style="color:{color}">▌</small> '
        f'<small><code>{fact_id}</code></small> '
        f'{claim} '
        f'<small style="color:#4A6A8A">({source_domain} · {conf:.0%})</small>',
        unsafe_allow_html=True,
    )
