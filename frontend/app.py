"""
Streamlit multi-page application entrypoint for DeepTrace.

Configures page, applies dark theme CSS, and provides shared session state.
Run with: streamlit run frontend/app.py
"""
# Load .env from project root so USE_MOCK, API keys, etc. are set before any config import
import os
import sys
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
os.chdir(_project_root)
from dotenv import load_dotenv
load_dotenv(os.path.join(_project_root, ".env"))

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
# Show actual mode from config (loaded after .env)
try:
    from config import USE_MOCK
    if USE_MOCK:
        st.info("**Mock mode** — Using fixture data. Set `USE_MOCK=false` in `.env` and restart Streamlit for real API and dynamic graph/reports.")
    else:
        st.success("**Live mode** — Real API calls and dynamic graph/reports.")
except Exception:
    st.info("Set `USE_MOCK=false` in `.env` and restart Streamlit for real runs.")
