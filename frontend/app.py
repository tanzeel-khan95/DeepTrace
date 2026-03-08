"""
app.py — Streamlit multi-page application entrypoint for DeepTrace.

Configures page, applies dark theme CSS, and provides shared session state.
Run with: streamlit run frontend/app.py

Architecture position: frontend entrypoint, imports from pipeline.py.
"""
import streamlit as st

st.set_page_config(
    page_title="DeepTrace — AI Research Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark theme CSS matching SRS design tokens
st.markdown("""
<style>
  .stApp { background-color: #0D1117; color: #C8D8E8; }
  .stSidebar { background-color: #040B14; }
  .stButton>button {
    background: #1B4F72; color: #C8D8E8;
    border: 1px solid #2471A3; border-radius: 4px;
  }
  .stButton>button:hover { background: #2471A3; border-color: #AED6F1; }
  .risk-critical { color: #C62828; font-weight: bold; }
  .risk-high     { color: #E65100; font-weight: bold; }
  .risk-medium   { color: #F9A825; }
  .risk-low      { color: #546E7A; }
</style>
""", unsafe_allow_html=True)

st.markdown("## ◈ DeepTrace — AI Research Intelligence")
st.markdown("Select a page from the sidebar to begin.")
st.info("Phase 1 — Mock Mode Active. All data is fixture-based. Set USE_MOCK=false for real runs.")
