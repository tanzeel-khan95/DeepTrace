"""
Agent and utility tests.

These tests run with USE_MOCK=true (no API calls) to validate:
  - All agent code paths are importable
  - JSON parsing handles edge cases
  - Budget guard fires correctly
  - LLM cache writes and reads correctly
  - Supervisor mock behaviour

Tests that require real API keys are marked with @pytest.mark.integration
and are skipped in standard CI (run manually with: pytest -m integration).
"""
import os
import pytest

# Force mock mode for all tests (no API calls)
os.environ["USE_MOCK"] = "true"
os.environ["ENV"] = "dev"
# Use temp dir for cache tests so config picks it up when first imported
os.environ.setdefault("LLM_CACHE_DIR", "/tmp/test_llm_cache")
os.environ.setdefault("LLM_CACHE_ENABLED", "true")


# ─────────────────────────────────────────────────────────────────────────────
# JSON Parser Tests
# ─────────────────────────────────────────────────────────────────────────────

from utils.json_parser import extract_json, safe_extract_json, LLMParseError


def test_extract_plain_json():
    result = extract_json('{"research_quality": 0.75, "gaps_remaining": []}')
    assert result["research_quality"] == 0.75


def test_extract_json_with_fences():
    raw = '```json\n{"key": "value"}\n```'
    result = extract_json(raw)
    assert result["key"] == "value"


def test_extract_json_with_preamble():
    raw = 'Here is the analysis:\n\n{"result": "found"}'
    result = extract_json(raw)
    assert result["result"] == "found"


def test_extract_json_raises_on_garbage():
    with pytest.raises(LLMParseError):
        extract_json("This is just plain text with no JSON at all.")


def test_safe_extract_returns_fallback_on_error():
    result = safe_extract_json("not json at all", fallback={"default": True})
    assert result == {"default": True}


def test_extract_json_array():
    result = extract_json('[{"id": 1}, {"id": 2}]')
    assert len(result) == 2


# ─────────────────────────────────────────────────────────────────────────────
# Budget Guard Tests
# ─────────────────────────────────────────────────────────────────────────────

from utils.budget_guard import record_spend, get_total_spent, reset


def test_budget_guard_accumulates():
    reset()
    record_spend(1000, 500, "claude-haiku-4-5-20251001")
    assert get_total_spent() > 0


def test_budget_guard_raises_at_limit():
    reset()
    import utils.budget_guard as bg
    bg._total_spent = 999.0  # Force over limit
    with pytest.raises(RuntimeError, match="BudgetGuard"):
        bg._check_budget()
    reset()


def test_budget_guard_reset():
    record_spend(5000, 2000, "claude-haiku-4-5-20251001")
    reset()
    assert get_total_spent() == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# LLM Cache Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_llm_cache_miss_returns_none():
    from utils.llm_cache import get_cached, clear_cache
    clear_cache()
    result = get_cached("sys", "user", "claude-haiku-4-5-20251001")
    assert result is None


def test_llm_cache_save_and_retrieve():
    from utils.llm_cache import save_to_cache, get_cached, clear_cache
    clear_cache()
    save_to_cache("sys_prompt", "user_msg", "claude-haiku-4-5-20251001", '{"ok": true}')
    result = get_cached("sys_prompt", "user_msg", "claude-haiku-4-5-20251001")
    assert result == '{"ok": true}'


def test_llm_cache_disabled_returns_none():
    os.environ["LLM_CACHE_ENABLED"] = "false"
    from utils.llm_cache import get_cached
    result = get_cached("sys", "user", "haiku")
    assert result is None
    os.environ["LLM_CACHE_ENABLED"] = "true"


# ─────────────────────────────────────────────────────────────────────────────
# Agent Import Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_all_agents_importable():
    from agents.supervisor import supervisor_plan, supervisor_reflect, supervisor_synthesise
    from agents.scout_agent import run_scout
    from agents.deep_dive_agent import run_deep_dive
    from agents.risk_evaluator import run_risk_evaluator
    from agents.graph_builder import run_graph_builder
    assert True  # No ImportError = pass


def test_all_prompts_importable():
    from prompts.supervisor_prompt import SUPERVISOR_SYSTEM_PROMPT
    from prompts.deep_dive_prompt import DEEP_DIVE_SYSTEM_PROMPT
    from prompts.risk_prompt import RISK_EVALUATOR_SYSTEM_PROMPT
    from prompts.graph_prompt import GRAPH_BUILDER_SYSTEM_PROMPT
    assert len(SUPERVISOR_SYSTEM_PROMPT) > 100
    assert len(DEEP_DIVE_SYSTEM_PROMPT) > 100


def test_anthropic_client_raises_without_key():
    old_key = os.environ.pop("ANTHROPIC_API_KEY", None)
    from utils import anthropic_client
    anthropic_client._client = None  # reset singleton
    try:
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            anthropic_client.get_client()
    finally:
        if old_key is not None:
            os.environ["ANTHROPIC_API_KEY"] = old_key
        anthropic_client._client = None


# ─────────────────────────────────────────────────────────────────────────────
# Supervisor mock behaviour
# ─────────────────────────────────────────────────────────────────────────────

from state.agent_state import make_initial_state
from agents.supervisor import supervisor_plan, supervisor_reflect, supervisor_route


def test_supervisor_plan_mock_returns_plan():
    """In USE_MOCK, supervisor_plan returns research_plan and loop_count."""
    state = make_initial_state("Timothy Overturf", "CEO of Sisu Capital")
    out = supervisor_plan(state)
    assert "research_plan" in out
    assert "loop_count" in out
    assert len(out["research_plan"]) > 0
    assert out["loop_count"] == 1


def test_supervisor_reflect_mock_returns_quality():
    """In USE_MOCK, supervisor_reflect returns research_quality."""
    state = make_initial_state("Test", "")
    state["loop_count"] = 1
    state["extracted_facts"] = []
    out = supervisor_reflect(state)
    assert "research_quality" in out
    assert 0 <= out["research_quality"] <= 1.0


def test_supervisor_route_returns_scout_or_risk():
    """supervisor_route returns either scout_agent or risk_evaluator."""
    state = make_initial_state("Test", "")
    state["loop_count"] = 0
    state["research_quality"] = 0.0
    r = supervisor_route(state)
    assert r in ("scout_agent", "risk_evaluator")

    state["loop_count"] = 2
    state["research_quality"] = 0.5
    r2 = supervisor_route(state)
    assert r2 == "risk_evaluator"


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests (requires real ANTHROPIC_API_KEY — run manually)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_real_haiku_call():
    """Test one real Haiku call. Requires ANTHROPIC_API_KEY in environment."""
    os.environ["USE_MOCK"] = "false"
    from utils.anthropic_client import call_llm
    from utils.budget_guard import reset
    reset()

    result = call_llm(
        system_prompt="You are a test assistant. Respond with exactly: {\"status\": \"ok\"}",
        user_message="Test ping",
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
    )
    from utils.json_parser import extract_json
    data = extract_json(result)
    assert data.get("status") == "ok"
    os.environ["USE_MOCK"] = "true"


@pytest.mark.integration
def test_real_tavily_search():
    """Test one real Tavily search. Requires TAVILY_API_KEY in environment."""
    import asyncio
    os.environ["USE_MOCK"] = "false"
    from search.tavily_search import tavily_search
    results = asyncio.run(tavily_search("Anthropic AI company"))
    assert len(results) > 0
    assert "url" in results[0]
    os.environ["USE_MOCK"] = "true"
