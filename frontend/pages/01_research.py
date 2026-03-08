"""
01_research.py — Research page: target input and live agent stream.

Accepts target name, runs the DeepTrace pipeline with streaming,
and displays agent activity in real time.

Architecture position: primary user-facing page, calls pipeline.stream_pipeline().
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from pipeline import stream_pipeline

st.title("◉ Research Target")

AGENT_BADGES = {
    "supervisor_plan":    "🧠 SUPERVISOR — Planning",
    "scout_agent":        "🔍 SCOUT — Searching",
    "deep_dive":          "📖 DEEP DIVE — Extracting",
    "supervisor_reflect": "🔄 SUPERVISOR — Reflecting",
    "risk_evaluator":     "⚑ RISK — Evaluating",
    "graph_builder":      "🕸 GRAPH — Building",
    "supervisor_synth":   "📝 SUPERVISOR — Synthesising",
}

with st.form("research_form"):
    target_name    = st.text_input("Target Name", value="Timothy Overturf", placeholder="Full name")
    target_context = st.text_input("Context (optional)", value="CEO of Sisu Capital",
                                   placeholder="Role, company, or background")
    submitted = st.form_submit_button("▶ Run Research")

if submitted and target_name:
    st.session_state["last_target"] = target_name
    st.session_state["last_context"] = target_context
    st.session_state["run_complete"]  = False
    st.session_state["final_state"]   = None

    progress   = st.sidebar.progress(0.0, text="Starting...")
    status_box = st.empty()
    fact_count = st.sidebar.metric("Facts Extracted", 0)
    loop_count = st.sidebar.metric("Loop", 0)

    loop_progress = {
        "supervisor_plan":    0.10, "scout_agent": 0.25,
        "deep_dive":          0.45, "supervisor_reflect": 0.55,
        "risk_evaluator":     0.75, "graph_builder": 0.88,
        "supervisor_synth":   1.00,
    }

    all_chunks = {}

    for node_name, node_output in stream_pipeline(target_name, target_context):
        badge = AGENT_BADGES.get(node_name, f"⚙ {node_name.upper()}")
        all_chunks[node_name] = node_output

        with status_box.container():
            with st.status(badge, expanded=False, state="running"):
                if "research_plan" in node_output:
                    st.write(f"Queries planned: {len(node_output['research_plan'])}")
                if "raw_results" in node_output:
                    st.write(f"Results found: {len(node_output['raw_results'])}")
                if "extracted_facts" in node_output:
                    n = len(node_output["extracted_facts"])
                    st.write(f"Facts extracted: {n}")
                    fact_count.metric("Facts Extracted", n)
                if "risk_flags" in node_output:
                    flags = node_output["risk_flags"]
                    for f in flags:
                        sev = getattr(f, "severity", "?")
                        title = getattr(f, "title", str(f))
                        st.write(f"{sev}: {title}")
                if "final_report" in node_output and node_output["final_report"]:
                    st.write("✅ Final report ready")
                if "loop_count" in node_output:
                    loop_count.metric("Loop", node_output["loop_count"])

        pct = loop_progress.get(node_name, 0.5)
        progress.progress(pct, text=badge)

    progress.progress(1.0, text="✅ Complete")
    st.success(f"Research complete for **{target_name}**. View results in Graph and Report pages.")
    st.session_state["run_complete"] = True
    st.session_state["all_chunks"]   = all_chunks
