"""
03_report.py — Phase 3: Report page with citations, clickable links, PDF export.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from collections import defaultdict

st.set_page_config(page_title="DeepTrace — Report", layout="wide")
st.title("📋 Intelligence Report")

if "final_state" not in st.session_state or not st.session_state.final_state:
    st.info("Run a research pipeline from the Research page first.")
    st.stop()

state = st.session_state.final_state

# ── Report text ───────────────────────────────────────────────────────────────
final_report = state.get("final_report", "")
if final_report:
    st.markdown(final_report)
else:
    st.warning("No report generated.")

st.divider()

# ── Risk flags ────────────────────────────────────────────────────────────────
st.subheader("🚨 Risk Flags")
risk_flags = state.get("risk_flags", [])
if not risk_flags:
    st.success("No risk flags identified.")
else:
    SEVERITY_COLORS = {
        "CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"
    }
    for flag in risk_flags:
        if isinstance(flag, dict):
            sev = flag.get("severity", "LOW")
            title = flag.get("title", "")
            desc = flag.get("description", "")
            conf = flag.get("confidence", 0)
        else:
            sev = getattr(flag, "severity", "LOW")
            title = getattr(flag, "title", "")
            desc = getattr(flag, "description", "")
            conf = getattr(flag, "confidence", 0)
        icon = SEVERITY_COLORS.get(sev, "⚪")
        with st.expander(f"{icon} [{sev}] {title}  —  {int(conf*100)}% confidence"):
            st.write(desc)

st.divider()

# ── Citations with clickable links ────────────────────────────────────────────
st.subheader("📚 Source References")
citations = state.get("citations", [])
if not citations:
    st.info("No source citations available.")
else:
    st.caption(f"{len(citations)} sources referenced")

    by_domain = defaultdict(list)
    for c in citations:
        domain = c.get("domain", "unknown") if isinstance(c, dict) else getattr(c, "domain", "unknown")
        by_domain[domain].append(c)

    for domain, domain_citations in sorted(by_domain.items()):
        with st.expander(f"🔗 {domain}  ({len(domain_citations)} reference{'s' if len(domain_citations) > 1 else ''})"):
            for c in domain_citations:
                url = c.get("url", "") if isinstance(c, dict) else getattr(c, "url", "")
                title = c.get("title", url) if isinstance(c, dict) else getattr(c, "title", url)
                snippet = c.get("snippet", "") if isinstance(c, dict) else getattr(c, "snippet", "")
                conf = c.get("confidence", 0) if isinstance(c, dict) else getattr(c, "confidence", 0)

                st.markdown(f"**[{title}]({url})**", unsafe_allow_html=False)
                if snippet:
                    st.caption(f'"{snippet[:200]}"')
                st.caption(f"Source confidence: {int(conf*100)}%  ·  [Open source ↗]({url})")
                st.divider()

st.divider()

# ── PDF Export ────────────────────────────────────────────────────────────────
st.subheader("📥 Export")
col1, col2 = st.columns([1, 3])
with col1:
    if st.button("📄 Generate PDF", type="primary", use_container_width=True):
        with st.spinner("Generating PDF..."):
            try:
                from utils.report_exporter import export_report_pdf
                pdf_bytes = export_report_pdf(
                    target_name=state.get("target_name", "Unknown"),
                    final_report=state.get("final_report", ""),
                    risk_flags=state.get("risk_flags", []),
                    citations=state.get("citations", []),
                    run_id=state.get("run_id", "unknown"),
                )
                st.session_state["pdf_bytes"] = pdf_bytes
                st.success("PDF ready for download!")
            except RuntimeError as e:
                st.error(f"PDF generation failed: {e}")

if "pdf_bytes" in st.session_state:
    target = state.get("target_name", "report").replace(" ", "_")
    run_id = state.get("run_id", "unknown")[:8]
    st.download_button(
        label="⬇️ Download PDF Report",
        data=st.session_state["pdf_bytes"],
        file_name=f"DeepTrace_{target}_{run_id}.pdf",
        mime="application/pdf",
        use_container_width=False,
    )
