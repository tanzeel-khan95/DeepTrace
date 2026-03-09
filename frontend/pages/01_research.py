"""
01_research.py — Research page: target input and live agent stream.

Accepts target name, runs the DeepTrace pipeline with streaming,
and displays agent activity in real time.

Architecture position: primary user-facing page, calls pipeline.stream_pipeline().
"""
import sys
import os
import uuid
import time

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
    target_name    = st.text_input("Target Name", value="", placeholder="e.g. Sundar Pichai")
    target_context = st.text_input("Context (optional)", value="", placeholder="e.g. CEO of Google and Alphabet")
    submitted = st.form_submit_button("▶ Run Research")


def _render_step_body(node_name: str, node_output: dict, fact_metric, loop_metric):
    """Shared renderer for a single agent step body."""
    if "research_plan" in node_output:
        st.write(f"Queries planned: {len(node_output['research_plan'])}")
    if "raw_results" in node_output:
        st.write(f"Results found: {len(node_output['raw_results'])}")
    if "extracted_facts" in node_output:
        n = len(node_output["extracted_facts"])
        st.write(f"Facts extracted: {n}")
        if fact_metric is not None:
            fact_metric.metric("Facts Extracted", n)
    if "risk_flags" in node_output:
        flags = node_output["risk_flags"]
        for f in flags:
            sev = getattr(f, "severity", "?")
            title = getattr(f, "title", str(f))
            st.write(f"{sev}: {title}")
    if "final_report" in node_output and node_output["final_report"]:
        st.write("✅ Final report ready")
    if "loop_count" in node_output and loop_metric is not None:
        loop_metric.metric("Loop", node_output["loop_count"])

    st.markdown("**Raw output**")
    st.json(node_output)


if submitted and target_name:
    st.session_state["last_target"] = target_name
    st.session_state["last_context"] = target_context
    st.session_state["run_complete"] = False
    st.session_state["final_state"] = None
    st.session_state["run_steps"] = []

    run_id = str(uuid.uuid4())
    st.session_state["run_id"] = run_id

    progress = st.sidebar.progress(0.0, text="Starting...")
    fact_count = st.sidebar.metric("Facts Extracted", 0)
    loop_count = st.sidebar.metric("Loop", 0)

    loop_progress = {
        "supervisor_plan": 0.10,
        "scout_agent": 0.25,
        "deep_dive": 0.45,
        "supervisor_reflect": 0.55,
        "risk_evaluator": 0.75,
        "graph_builder": 0.88,
        "supervisor_synth": 1.00,
    }

    all_chunks = {}
    timeline_container = st.container()

    start_ts = time.perf_counter()
    last_ts = start_ts

    for idx, (node_name, node_output) in enumerate(
        stream_pipeline(target_name, target_context, run_id=run_id), start=1
    ):
        now = time.perf_counter()
        duration = now - last_ts
        last_ts = now

        badge = AGENT_BADGES.get(node_name, f"⚙ {node_name.upper()}")
        all_chunks[node_name] = node_output

        step = {
            "order": idx,
            "node_name": node_name,
            "badge": badge,
            "duration": duration,
            "output": node_output,
        }
        st.session_state["run_steps"].append(step)

        with timeline_container:
            st.subheader("Agent run timeline")
            for s in st.session_state["run_steps"]:
                header = f"{s['order']}. {s['badge']} — {s['duration']:.1f}s"
                expanded = s is st.session_state["run_steps"][-1]
                with st.expander(header, expanded=expanded):
                    _render_step_body(
                        s["node_name"],
                        s["output"],
                        fact_metric=fact_count,
                        loop_metric=loop_count,
                    )

        pct = loop_progress.get(node_name, 0.5)
        progress.progress(pct, text=badge)

    total_time = time.perf_counter() - start_ts
    progress.progress(1.0, text=f"✅ Complete in {total_time:.1f}s")
    st.success(
        f"Research complete for **{target_name}** in {total_time:.1f} seconds. "
        "You can review each agent's output above."
    )
    st.session_state["run_complete"] = True
    st.session_state["all_chunks"] = all_chunks

    # Store real run output so Report and Graph pages show this run's data
    synth = all_chunks.get("supervisor_synth") or {}
    risk = all_chunks.get("risk_evaluator") or {}
    deep = all_chunks.get("deep_dive") or {}
    st.session_state["final_report"] = synth.get("final_report") or ""
    st.session_state["risk_flags"] = risk.get("risk_flags") or []
    st.session_state["extracted_facts"] = deep.get("extracted_facts") or []


# If there is a previous run, keep its timeline visible when the page reloads
if st.session_state.get("run_steps"):
    st.subheader("Last run — agent timeline")
    for s in st.session_state["run_steps"]:
        header = f"{s['order']}. {s['badge']} — {s['duration']:.1f}s"
        with st.expander(header, expanded=False):
            _render_step_body(
                s["node_name"],
                s["output"],
                fact_metric=None,
                loop_metric=None,
            )
