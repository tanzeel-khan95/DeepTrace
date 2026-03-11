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

# ── LangSmith / LangChain tracing ─────────────────────────────────────────────
LANGCHAIN_TRACING: bool = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", f"DeepTrace")
LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")

# ── Loop / token controls (Phase 2 cost constraint: target <$0.01/run in dev) ─
MAX_LOOPS:  dict = {"dev": 3,   "staging": 3, "prod": 5}
MAX_TOKENS: dict = {"dev": 5000, "staging": 1500, "prod": 3000}
QUALITY_THRESHOLD: float = 0.70   # Stop loop when research_quality >= this

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

# ── Haiku model string (Phase 2 convenience constant) ─────────────────────────
HAIKU_MODEL = "claude-haiku-4-5-20251001"

# ── Anthropic API key ─────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# ── LLM cache directory (Phase 2 record-replay) ───────────────────────────────
LLM_CACHE_DIR: str = os.getenv("LLM_CACHE_DIR", ".llm_cache")
LLM_CACHE_ENABLED: bool = os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true"

# ── Phase 2 startup validation ────────────────────────────────────────────────
def validate_phase2_config() -> list:
    """
    Check all required Phase 2 env vars are set.
    Returns list of missing variable names (empty = all good).
    """
    errors = []
    if not USE_MOCK:
        if not ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY — required when USE_MOCK=false")
        if not TAVILY_API_KEY:
            errors.append("TAVILY_API_KEY — required for real search")
    return errors

# ── Neo4j ─────────────────────────────────────────────────────────────────────
NEO4J_URI:      str = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USERNAME: str = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "deeptrace123")
NEO4J_DATABASE: str = os.getenv("NEO4J_DATABASE", "neo4j")

# ── Search ────────────────────────────────────────────────────────────────────
TAVILY_API_KEY:       str = os.getenv("TAVILY_API_KEY", "")
BRAVE_SEARCH_API_KEY: str = os.getenv("BRAVE_SEARCH_API_KEY", "")
MIN_RELEVANCE:        float = 0.55   # Filter search results below this score (slightly stricter)

# ── LangSmith (alias for LangChain project) ───────────────────────────────────
LANGSMITH_PROJECT: str = LANGCHAIN_PROJECT

# ── Budget guard ──────────────────────────────────────────────────────────────
PHASE_BUDGET: dict = {"dev": 10.0, "staging": 25.0, "prod": 999.0}

# ── Checkpointing ─────────────────────────────────────────────────────────────
CHECKPOINT_DB_PATH: str = os.getenv("CHECKPOINT_DB_PATH", ".checkpoints/deeptrace.db")

# ── Audit logging ─────────────────────────────────────────────────────────────
AUDIT_LOG_DIR: str = os.getenv("AUDIT_LOG_DIR", ".audit_logs")

# ── Graph artifact persistence ────────────────────────────────────────────────
GRAPH_ARTIFACT_DIR: str = os.getenv("GRAPH_ARTIFACT_DIR", ".graph_artifacts")

# ── Rate limiting ─────────────────────────────────────────────────────────────
LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_RETRY_BASE_DELAY: float = float(os.getenv("LLM_RETRY_BASE_DELAY", "1.0"))
LLM_REQUESTS_PER_MIN: int = int(os.getenv("LLM_REQUESTS_PER_MIN", "50"))  # Haiku tier 1

# ── Search feature toggles ───────────────────────────────────────────────────
HAIKU_WEB_SEARCH_ENABLED: bool = os.getenv("HAIKU_WEB_SEARCH_ENABLED", "true").lower() == "true"
MAX_SEARCH_RESULTS_PER_QUERY: int = int(os.getenv("MAX_SEARCH_RESULTS_PER_QUERY", "5"))

# ── Extraction coverage ───────────────────────────────────────────────────────
EXTRACTION_CATEGORIES = ["biographical", "professional", "financial", "behavioral"]

# ── Entity canonicalization ───────────────────────────────────────────────────
ENTITY_SIMILARITY_THRESHOLD: float = float(os.getenv("ENTITY_SIMILARITY_THRESHOLD", "0.85"))


def validate_config() -> list:
    """
    Validate configuration for Phase 2 and Phase 3.

    Returns list of error messages (empty = all good).
    """
    errors = []
    if not USE_MOCK:
        if not ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY — required when USE_MOCK=false")
        if not TAVILY_API_KEY:
            errors.append("TAVILY_API_KEY — required for real search")

    if LANGCHAIN_TRACING and not LANGCHAIN_API_KEY:
        errors.append("LANGCHAIN_API_KEY — required when LANGCHAIN_TRACING_V2=true")

    return errors


