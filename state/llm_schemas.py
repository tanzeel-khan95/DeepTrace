"""
Pydantic response schemas for structured LLM output.

Used with Anthropic output_config to enforce JSON shape. Single source of truth
for what each agent's LLM call must return. Avoids raw text + fragile parsing.
"""
from typing import List, Literal, Dict, Optional

from pydantic import BaseModel, Field

# Reuse core models from agent_state for deep_dive and risk_evaluator responses
from state.agent_state import Fact, Entity, Relationship, RiskFlag


# ── Supervisor plan: research queries + gaps ──────────────────────────────────
class SupervisorPlanResponse(BaseModel):
    """Enforced JSON shape for supervisor_plan LLM response."""
    research_plan: List[str]
    gaps_remaining: List[str]


# ── Supervisor reflect: quality score + gaps ────────────────────────────────────
class SupervisorReflectResponse(BaseModel):
    """Enforced JSON shape for supervisor_reflect LLM response."""
    research_quality: float = Field(ge=0.0, le=1.0, description="Composite research quality 0-1")
    gaps_remaining: List[str] = Field(default_factory=list, description="Remaining gaps")


# ── Deep dive: facts, entities, relationships ───────────────────────────────────
class DeepDiveResponse(BaseModel):
    """Enforced JSON shape for deep_dive LLM response."""
    extracted_facts: List[Fact] = Field(default_factory=list)
    entities: List[Entity] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)


# ── Risk evaluator: risk flags ─────────────────────────────────────────────────
class RiskEvaluatorResponse(BaseModel):
    """Enforced JSON shape for risk_evaluator LLM response."""
    risk_flags: List[RiskFlag] = Field(default_factory=list)
