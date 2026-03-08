"""Tests for all Pydantic schemas in agent_state.py."""
import pytest
from state.agent_state import Fact, Entity, Relationship, RiskFlag, make_initial_state


def test_fact_validates_confidence_range():
    with pytest.raises(Exception):
        Fact(fact_id="f1", claim="test", source_url="https://x.com",
             source_domain="x.com", confidence=1.5, category="biographical",
             entities_mentioned=[])

def test_fact_accepts_valid_confidence():
    f = Fact(fact_id="f1", claim="test", source_url="https://sec.gov",
             source_domain="sec.gov", confidence=0.92, category="financial",
             entities_mentioned=["Timothy Overturf"])
    assert f.confidence == 0.92

def test_risk_flag_requires_two_evidence():
    with pytest.raises(Exception):
        RiskFlag(flag_id="r1", title="test", description="test",
                 severity="HIGH", evidence_fact_ids=["f1"],  # only 1 — should fail
                 confidence=0.8, category="financial")

def test_risk_flag_accepts_two_evidence():
    r = RiskFlag(flag_id="r1", title="test", description="desc",
                 severity="CRITICAL", evidence_fact_ids=["f1", "f2"],
                 confidence=0.9, category="regulatory")
    assert r.severity == "CRITICAL"

def test_initial_state_has_empty_lists():
    state = make_initial_state("Timothy Overturf", "CEO of Sisu Capital")
    assert state["target_name"] == "Timothy Overturf"
    assert state["extracted_facts"] == []
    assert state["loop_count"] == 0
    assert state["research_quality"] == 0.0
