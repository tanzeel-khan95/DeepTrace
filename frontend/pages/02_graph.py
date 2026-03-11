"""
02_graph.py — Phase 3: D3.js graph page with run history and artifact download.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="DeepTrace — Identity Graph", layout="wide")
st.title("🕸️ Identity Graph")

if "final_state" not in st.session_state or not st.session_state.final_state:
    st.info("Run a research pipeline from the Research page first.")
    st.stop()

state = st.session_state.final_state
run_id = state.get("run_id", "unknown")

tab1, tab2 = st.tabs(["📊 Current Run", "📁 Saved Artifacts"])

with tab1:
    graph_html = state.get("graph_html", "")
    artifact_path = state.get("artifact_path", "")
    entities = state.get("entities", [])
    rels = state.get("relationships", [])

    col1, col2, col3 = st.columns(3)
    col1.metric("Entities", len(entities))
    col2.metric("Relationships", len(rels))
    col3.metric("Run ID", run_id[:8] + "...")

    if graph_html:
        components.html(graph_html, height=620, scrolling=False)
    else:
        st.warning("No graph data available. Run the pipeline first.")

    if artifact_path and os.path.exists(artifact_path):
        with open(artifact_path, "rb") as f:
            st.download_button(
                "⬇️ Download Graph HTML",
                data=f.read(),
                file_name=f"DeepTrace_graph_{run_id[:8]}.html",
                mime="text/html",
            )

with tab2:
    st.subheader("Past Run Graphs")
    from utils.audit_logger import list_run_ids
    from config import GRAPH_ARTIFACT_DIR

    run_ids = list_run_ids()
    if not run_ids:
        st.info("No past runs found.")
    else:
        selected_run = st.selectbox("Select run", run_ids)
        artifact = os.path.join(GRAPH_ARTIFACT_DIR, f"{selected_run}.html")
        if os.path.exists(artifact):
            with open(artifact) as f:
                past_html = f.read()
            components.html(past_html, height=560, scrolling=False)
            with open(artifact, "rb") as f:
                st.download_button(
                    f"⬇️ Download {selected_run[:8]} graph",
                    data=f.read(),
                    file_name=f"DeepTrace_graph_{selected_run[:8]}.html",
                    mime="text/html",
                )
        else:
            st.warning(f"Graph artifact not found for run {selected_run[:8]}")
