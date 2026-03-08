"""
config.py — DeepTrace central configuration.

Reads environment variables and exposes typed constants used by every module.
ENV controls which model tier is active. USE_MOCK bypasses all API calls.

Architecture position: imported by all agents, pipeline, and utilities.
"""
import os
from typing import Literal

# ── Core toggles ──────────────────────────────────────────────────────────────
ENV: Literal["dev", "staging", "prod"] = os.getenv("ENV", "dev")   # type: ignore
USE_MOCK: bool = os.getenv("USE_MOCK", "true").lower() == "true"
LANGCHAIN_TRACING: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"

# ── Loop / token controls ────────────────────────────────────────────────────
MAX_LOOPS:  dict = {"dev": 2,   "staging": 3, "prod": 5}
MAX_TOKENS: dict = {"dev": 500, "staging": 1500, "prod": 3000}
QUALITY_THRESHOLD: float = 0.80   # Stop loop when research_quality >= this

# ── Model assignments per environment ────────────────────────────────────────
# Phase 1: these are never called (USE_MOCK=true). Defined now for Phase 2.
MODEL_CONFIG: dict = {
    "dev": {
        "supervisor":     "claude-haiku-4-5-20251001",
        "scout":          "claude-haiku-4-5-20251001",
        "deep_dive":      "claude-haiku-4-5-20251001",
        "risk_evaluator": "claude-haiku-4-5-20251001",
        "graph_builder":  "claude-haiku-4-5-20251001",
    },
    "staging": {
        "supervisor":     "claude-opus-4-5-20251101",
        "scout":          "gpt-4.1",
        "deep_dive":      "gemini-2.5-pro",
        "risk_evaluator": "claude-sonnet-4-6-20251120",
        "graph_builder":  "claude-haiku-4-5-20251001",
    },
    "prod": {
        "supervisor":     "claude-opus-4-5-20251101",
        "scout":          "gpt-4.1",
        "deep_dive":      "gemini-2.5-pro",
        "risk_evaluator": "claude-sonnet-4-6-20251120",
        "graph_builder":  "claude-haiku-4-5-20251001",
    },
}

# ── Active model shortcuts ────────────────────────────────────────────────────
MODELS = MODEL_CONFIG[ENV]

# ── Neo4j ─────────────────────────────────────────────────────────────────────
NEO4J_URI:      str = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USERNAME: str = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "deeptrace123")
NEO4J_DATABASE: str = os.getenv("NEO4J_DATABASE", "neo4j")

# ── Search ────────────────────────────────────────────────────────────────────
TAVILY_API_KEY:       str = os.getenv("TAVILY_API_KEY", "")
BRAVE_SEARCH_API_KEY: str = os.getenv("BRAVE_SEARCH_API_KEY", "")
MIN_RELEVANCE:        float = 0.50   # Filter search results below this score

# ── LangSmith ─────────────────────────────────────────────────────────────────
LANGSMITH_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", f"deeptrace-{ENV}")

# ── Budget guard ──────────────────────────────────────────────────────────────
PHASE_BUDGET: dict = {"dev": 10.0, "staging": 25.0, "prod": 999.0}
