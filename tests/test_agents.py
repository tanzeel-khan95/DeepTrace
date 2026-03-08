"""Tests for agents (Section 8: Supervisor mock behaviour)."""
import pytest
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
