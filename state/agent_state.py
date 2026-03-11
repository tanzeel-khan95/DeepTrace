"""
agent_state.py — All Pydantic schemas and the AgentState TypedDict for DeepTrace.

This is the single source of truth for data structures. Every agent reads from
and writes to AgentState. Pydantic models enforce validation at every boundary.

Architecture position: imported by all agents, pipeline, confidence scorer, and tests.
"""
import operator
import uuid
from typing import Annotated, Dict, List, Literal, Optional, TypedDict

from pydantic import BaseModel, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# CORE DATA MODELS
# ─────────────────────────────────────────────────────────────────────────────

class Fact(BaseModel):
    """A single verified piece of information extracted from a source."""
    fact_id:             str
    claim:               str
    source_url:          str
    source_domain:       str
    confidence:          float
    category:            Literal["biographical", "financial", "network", "legal", "other"]
    entities_mentioned:  List[str]
    supporting_fact_ids: List[str] = []
    raw_source_snippet:  str = ""

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be 0.0–1.0, got {v}")
        return round(v, 4)

    @field_validator("fact_id")
    @classmethod
    def ensure_fact_id(cls, v: str) -> str:
        return v if v else str(uuid.uuid4())


class Entity(BaseModel):
    """A named entity discovered during research (person, org, fund, etc.)."""
    entity_id:   str
    name:        str
    entity_type: Literal["Person", "Organization", "Fund", "Location", "Event", "Filing"]
    attributes:  Dict[str, str] = {}
    confidence:  float
    source_fact_ids: List[str] = []

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be 0.0–1.0, got {v}")
        return round(v, 4)


class Relationship(BaseModel):
    """A directed relationship between two entities in the identity graph."""
    from_id:        str
    to_id:          str
    rel_type:       Literal[
        "WORKS_AT", "INVESTED_IN", "CONNECTED_TO",
        "FILED_WITH", "FOUNDED", "AFFILIATED_WITH",
        "BOARD_MEMBER", "MANAGED", "CONTROLS"
    ]
    attributes:     Dict[str, str] = {}
    confidence:     float
    source_fact_id: str

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be 0.0–1.0, got {v}")
        return round(v, 4)


class Citation(BaseModel):
    """Source citation for a fact (URL, domain, snippet, confidence)."""
    fact_id:      str
    url:          str
    domain:       str
    title:        str = ""
    snippet:      str = ""
    accessed_at:  str = ""
    confidence:   float = 0.0

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be 0.0–1.0, got {v}")
        return round(v, 4)


class RiskFlag(BaseModel):
    """A risk signal identified during the investigation."""
    flag_id:           str
    title:             str
    description:       str
    severity:          Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    evidence_fact_ids: List[str]   # minimum 2 required
    confidence:        float
    category:          Literal["regulatory", "financial", "network", "reputational", "legal", "biographical"]

    @field_validator("evidence_fact_ids")
    @classmethod
    def require_min_evidence(cls, v: List[str]) -> List[str]:
        if len(v) < 2:
            raise ValueError(f"RiskFlag requires minimum 2 evidence fact_ids, got {len(v)}")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be 0.0–1.0, got {v}")
        return round(v, 4)


class SearchResult(BaseModel):
    """A single raw result from Tavily or Brave search."""
    url:           str
    title:         str
    content:       str
    relevance:     float
    source_domain: str = ""

    @field_validator("relevance")
    @classmethod
    def validate_relevance(cls, v: float) -> float:
        return max(0.0, min(1.0, round(v, 4)))


# ─────────────────────────────────────────────────────────────────────────────
# AGENT STATE
# ─────────────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    """
    Shared state object passed between all LangGraph nodes.

    operator.add reducers allow multiple agents to append without
    overwriting each other's contributions in the same graph step.
    """
    # ── Input ────────────────────────────────────────────────────────────────
    target_name:    str
    target_context: Optional[str]

    # ── Planning (accumulate across loops) ───────────────────────────────────
    research_plan:   Annotated[List[str], operator.add]
    queries_issued:  Annotated[List[str], operator.add]
    gaps_remaining:  List[str]

    # ── Raw search data ───────────────────────────────────────────────────────
    raw_results:     Annotated[List[dict], operator.add]

    # ── Extracted intelligence ────────────────────────────────────────────────
    extracted_facts: Annotated[List[Fact], operator.add]
    entities:        Annotated[List[Entity], operator.add]
    relationships:   Annotated[List[Relationship], operator.add]

    # ── Risk ─────────────────────────────────────────────────────────────────
    risk_flags:      Annotated[List[RiskFlag], operator.add]

    # ── Graph ────────────────────────────────────────────────────────────────
    graph_populated: bool
    graph_html:       Optional[str]
    artifact_path:    Optional[str]

    # ── Citations (source evidence) ─────────────────────────────────────────
    citations:        Annotated[List[Citation], operator.add]

    # ── Quality tracking ─────────────────────────────────────────────────────
    confidence_map:    Dict[str, float]   # fact_id → final confidence score
    research_quality:  float              # 0.0 – 1.0 composite score
    loop_count:        int

    # ── Output ───────────────────────────────────────────────────────────────
    final_report:    Optional[str]
    run_id:          str


def make_initial_state(target_name: str, target_context: str = "", run_id: Optional[str] = None) -> AgentState:
    """Create a fresh AgentState for a new research run."""
    return AgentState(
        target_name=target_name,
        target_context=target_context,
        research_plan=[],
        queries_issued=[],
        gaps_remaining=[],
        raw_results=[],
        extracted_facts=[],
        entities=[],
        relationships=[],
        risk_flags=[],
        graph_populated=False,
        graph_html=None,
        artifact_path=None,
        citations=[],
        confidence_map={},
        research_quality=0.0,
        loop_count=0,
        final_report=None,
        run_id=run_id or str(uuid.uuid4()),
    )
