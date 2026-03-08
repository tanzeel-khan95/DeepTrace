"""Tests for the three-layer confidence scoring system."""
import pytest
from evaluation.confidence_scorer import (
    get_domain_trust, apply_cross_reference,
    compute_final_confidence, classify_confidence,
)

def test_sec_gov_gets_high_trust():
    assert get_domain_trust("sec.gov") == 0.92

def test_unknown_domain_gets_default():
    assert get_domain_trust("obscureblog.xyz") == 0.40

def test_two_contradictions_cap():
    score = apply_cross_reference(0.92, supporting=0, contradicting=2)
    assert score <= 0.30

def test_three_sources_boost():
    base = apply_cross_reference(0.80, supporting=3, contradicting=0)
    single = apply_cross_reference(0.80, supporting=1, contradicting=0)
    assert base > single

def test_final_score_bounded():
    score = compute_final_confidence("sec.gov", supporting_count=5, contradicting_count=0)
    assert 0.0 <= score <= 0.95

def test_classify_high():
    assert classify_confidence(0.90) == "HIGH"

def test_classify_discard():
    assert classify_confidence(0.20) == "DISCARD"
