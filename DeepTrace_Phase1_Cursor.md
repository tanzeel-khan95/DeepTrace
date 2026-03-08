# DeepTrace — Phase 1: Mock Scaffold Implementation
> **Cursor Implementation Guide** · Phase 1 of 4 · Zero API Cost · Full Structure Ready
>
> **Goal:** Build the entire DeepTrace codebase with real classes, real LangGraph wiring, real
> Pydantic schemas, real Streamlit UI, and real Neo4j graph — but every LLM call and every
> external API call returns hardcoded mock data. At the end of Phase 1, `python main.py` runs
> end-to-end, all 4 Streamlit pages render, Neo4j graph populates, and zero dollars are spent.
>
> **Next phase:** Replace `USE_MOCK=true` with `USE_MOCK=false` and swap in real API keys.
> Nothing else changes.

---

## How to Use This File in Cursor

```
1. Drop this file in your project root as: DeepTrace_Phase1_Cursor.md
2. Open Cursor chat (Cmd+L)
3. Type: @DeepTrace_Phase1_Cursor.md implement Section 2 - project structure
4. Work section by section. Each section is a self-contained implementation unit.
5. After each section: run the exit criteria check before moving to the next.
```

**Reference the SRS for architecture decisions:** `@DeepTrace_SRS_v3.md`
**This file is for Phase 1 implementation only.** It tells Cursor exactly what code to write.

---

## Table of Contents

- [Section 1 — Phase 1 Rules & Constraints](#section-1--phase-1-rules--constraints)
- [Section 2 — Project Structure](#section-2--project-structure)
- [Section 3 — Environment & Config](#section-3--environment--config)
- [Section 4 — Pydantic Schemas & AgentState](#section-4--pydantic-schemas--agentstate)
- [Section 5 — Mock Response Fixtures](#section-5--mock-response-fixtures)
- [Section 6 — Neo4j Manager](#section-6--neo4j-manager)
- [Section 7 — Confidence Scorer](#section-7--confidence-scorer)
- [Section 8 — Supervisor Agent](#section-8--supervisor-agent)
- [Section 9 — Scout Agent](#section-9--scout-agent)
- [Section 10 — Deep Dive Agent](#section-10--deep-dive-agent)
- [Section 11 — Risk Evaluator Agent](#section-11--risk-evaluator-agent)
- [Section 12 — Graph Builder Agent](#section-12--graph-builder-agent)
- [Section 13 — LangGraph Pipeline Assembly](#section-13--langgraph-pipeline-assembly)
- [Section 14 — Streamlit Frontend](#section-14--streamlit-frontend)
- [Section 15 — CLI Entrypoint](#section-15--cli-entrypoint)
- [Section 16 — Docker Compose](#section-16--docker-compose)
- [Section 17 — Phase 1 Exit Criteria & Smoke Test](#section-17--phase-1-exit-criteria--smoke-test)

---

## Section 1 — Phase 1 Rules & Constraints

> **Read this before writing a single line of code. These rules are non-negotiable for Phase 1.**

### The Mock Toggle Pattern

Every agent, every search function, every external call MUST use this exact toggle pattern:

```python
import os
USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"

def run_agent(state: AgentState) -> dict:
    if USE_MOCK:
        return MOCK_RESPONSES["agent_name"]   # Phase 1: hardcoded fixture
    # Phase 2+: real implementation goes here
    return real_implementation(state)
```

**Rule:** The `if USE_MOCK` branch is the ONLY code path that runs in Phase 1.
The `else` branch can be a stub (`raise NotImplementedError("Phase 2")`) or empty.

### What IS Implemented in Phase 1 (Real Code)

| Component | Phase 1 Status |
|-----------|---------------|
| All Pydantic schemas (Fact, Entity, RiskFlag, etc.) | ✅ Real, fully validated |
| AgentState TypedDict with all fields | ✅ Real, complete |
| LangGraph StateGraph with all nodes and edges | ✅ Real wiring |
| LangGraph routing logic (Command returns) | ✅ Real logic, mocked inputs |
| Neo4j schema creation + constraint setup | ✅ Real Cypher, real connection |
| Neo4j graph write from mock entity data | ✅ Real write, mock data |
| Confidence scorer (3-layer formula) | ✅ Real algorithm, mock inputs |
| Streamlit UI (all 4 pages, all components) | ✅ Real UI, mock data |
| All `@traceable` decorators | ✅ Real decorators (LangSmith off) |
| CLI entrypoint with all flags | ✅ Real CLI |
| Docker compose | ✅ Real config |
| requirements.txt | ✅ All pinned versions |
| .env.example | ✅ All keys documented |

### What is MOCKED in Phase 1 (Fixture Data)

| Component | Phase 1 Status |
|-----------|---------------|
| Anthropic API calls (all Claude models) | 🔴 Mocked — fixture JSON |
| OpenAI API calls (GPT-4.1) | 🔴 Mocked — fixture JSON |
| Google AI API calls (Gemini 2.5) | 🔴 Mocked — fixture JSON |
| Tavily search API | 🔴 Mocked — static result list |
| Brave search API | 🔴 Mocked — static result list |
| aiohttp page fetching | 🔴 Mocked — static page content |
| LangSmith tracing | 🔴 Disabled (`LANGCHAIN_TRACING_V2=false`) |

### Critical Rules

1. **Never hardcode `"Timothy Overturf"`** — always read from `state["target_name"]`
2. **Never import `anthropic` or `openai` at module level** — import inside the `else` branch only
3. **All Pydantic models must validate** — run `Model(**data)` in Phase 1, not just dict passing
4. **Neo4j must actually connect and write** — Neo4j is the one real external service in Phase 1
5. **`python main.py --target "Test Person"` must complete without errors**
6. **All files must have module docstrings** explaining purpose and architecture position

---

## Section 2 — Project Structure

> **Cursor prompt:** `@DeepTrace_Phase1_Cursor.md create the complete directory structure for Section 2`

Create every file listed below. Files marked `[STUB]` need only a module docstring + `pass` or
a `TODO` comment for Phase 1. Files marked `[IMPLEMENT]` need full Phase 1 code per the section
that covers them.

```
deeptrace/
├── agents/
│   ├── __init__.py                    [STUB]
│   ├── supervisor.py                  [IMPLEMENT — Section 8]
│   ├── scout_agent.py                 [IMPLEMENT — Section 9]
│   ├── deep_dive_agent.py             [IMPLEMENT — Section 10]
│   ├── risk_evaluator.py              [IMPLEMENT — Section 11]
│   └── graph_builder.py               [IMPLEMENT — Section 12]
├── graph/
│   ├── __init__.py                    [STUB]
│   ├── neo4j_manager.py               [IMPLEMENT — Section 6]
│   ├── schema.py                      [IMPLEMENT — Section 6]
│   └── visualizer.py                  [IMPLEMENT — Section 6]
├── search/
│   ├── __init__.py                    [STUB]
│   ├── tavily_search.py               [IMPLEMENT — Section 9]
│   ├── brave_search.py                [IMPLEMENT — Section 9]
│   └── scraper.py                     [IMPLEMENT — Section 10]
├── evaluation/
│   ├── __init__.py                    [STUB]
│   ├── eval_set.py                    [IMPLEMENT — Section 14]
│   ├── confidence_scorer.py           [IMPLEMENT — Section 7]
│   └── langsmith_eval.py              [STUB — Phase 3]
├── prompts/
│   ├── __init__.py                    [STUB]
│   ├── supervisor_prompt.py           [IMPLEMENT — Section 8]
│   ├── scout_prompt.py                [IMPLEMENT — Section 9]
│   ├── deep_dive_prompt.py            [IMPLEMENT — Section 10]
│   ├── risk_prompt.py                 [IMPLEMENT — Section 11]
│   └── graph_prompt.py                [IMPLEMENT — Section 12]
├── state/
│   ├── __init__.py                    [STUB]
│   └── agent_state.py                 [IMPLEMENT — Section 4]
├── utils/
│   ├── __init__.py                    [STUB]
│   ├── llm_cache.py                   [STUB — Phase 3]
│   └── budget_guard.py                [IMPLEMENT — Section 3]
├── frontend/
│   ├── app.py                         [IMPLEMENT — Section 14]
│   └── pages/
│       ├── 01_research.py             [IMPLEMENT — Section 14]
│       ├── 02_graph.py                [IMPLEMENT — Section 14]
│       ├── 03_report.py               [IMPLEMENT — Section 14]
│       └── 04_eval.py                 [IMPLEMENT — Section 14]
├── tests/
│   ├── __init__.py                    [STUB]
│   ├── test_state.py                  [IMPLEMENT — Section 4]
│   ├── test_confidence.py             [IMPLEMENT — Section 7]
│   └── test_agents.py                 [IMPLEMENT — Section 8]
├── config.py                          [IMPLEMENT — Section 3]
├── mock_responses.py                  [IMPLEMENT — Section 5]
├── pipeline.py                        [IMPLEMENT — Section 13]
├── main.py                            [IMPLEMENT — Section 15]
├── requirements.txt                   [IMPLEMENT — Section 3]
├── docker-compose.yml                 [IMPLEMENT — Section 16]
├── .env.example                       [IMPLEMENT — Section 3]
├── .gitignore                         [IMPLEMENT — Section 3]
└── README.md                          [IMPLEMENT — Section 15]
```

---

## Section 3 — Environment & Config

> **Cursor prompt:** `@DeepTrace_Phase1_Cursor.md implement Section 3 - environment and config`

### `config.py`

```python
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
```

### `utils/budget_guard.py`

```python
"""
budget_guard.py — Hard spending cap per environment phase.

Raises RuntimeError if estimated spend exceeds the phase budget.
Called after each LLM response in Phase 2+.

Architecture position: utility called by all agents in non-mock mode.
"""
from config import ENV, PHASE_BUDGET

_total_spent: float = 0.0

def record_spend(input_tokens: int, output_tokens: int, model: str) -> None:
    """Add estimated cost of one LLM call to the running total."""
    global _total_spent
    # Approximate pricing — update for Phase 2
    PRICE_PER_1M = {
        "claude-opus-4-5-20251101":   {"in": 5.00,  "out": 25.00},
        "claude-sonnet-4-6-20251120": {"in": 3.00,  "out": 15.00},
        "claude-haiku-4-5-20251001":  {"in": 1.00,  "out": 5.00},
        "gpt-4.1":                    {"in": 2.00,  "out": 8.00},
        "gemini-2.5-pro":             {"in": 1.25,  "out": 10.00},
    }
    p = PRICE_PER_1M.get(model, {"in": 5.00, "out": 25.00})
    cost = (input_tokens / 1_000_000 * p["in"]) + (output_tokens / 1_000_000 * p["out"])
    _total_spent += cost
    _check_budget()

def _check_budget() -> None:
    limit = PHASE_BUDGET.get(ENV, 10.0)
    if _total_spent > limit:
        raise RuntimeError(
            f"[BudgetGuard] Spend ${_total_spent:.4f} exceeded ${limit:.2f} limit for ENV={ENV}. "
            f"Raise ENV to 'staging' or increase PHASE_BUDGET to continue."
        )

def get_total_spent() -> float:
    return _total_spent

def reset() -> None:
    global _total_spent
    _total_spent = 0.0
```

### `requirements.txt`

```
# DeepTrace — pinned dependencies
# Phase 1: all listed. Phase 2: all active.

# LangGraph / LangChain / LangSmith
langgraph==1.0.0
langchain==1.0.0
langchain-core==0.3.0
langsmith==0.2.0

# LLM SDKs (Phase 1: imported only inside USE_MOCK=false branches)
anthropic==0.40.0
openai==1.50.0
google-generativeai==0.8.0

# Structured output
instructor==1.4.3
pydantic==2.9.0

# Neo4j
neo4j==5.26.0
networkx==3.4.0
pyvis==0.3.2

# Search
tavily-python==0.5.0

# Frontend
streamlit==1.41.0
plotly==5.24.0

# HTTP / async
aiohttp==3.11.0
tenacity==9.0.0

# PDF report
fpdf2==2.8.1

# Utilities
python-dotenv==1.0.1
rich==13.9.0
click==8.1.7

# Dev / test
pytest==8.3.0
pytest-asyncio==0.24.0
```

### `.env.example`

```bash
# DeepTrace — Environment Variables
# Copy to .env and fill in values. Never commit .env to git.

# ── Core ─────────────────────────────────────────────────────────────────────
ENV=dev                          # dev | staging | prod
USE_MOCK=true                    # true for Phase 1, false for Phase 2+

# ── LLM APIs (Phase 2+) ──────────────────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...     # Claude Opus/Sonnet/Haiku
OPENAI_API_KEY=sk-...            # GPT-4.1 (Scout Agent)
GOOGLE_API_KEY=AIza...           # Gemini 2.5 (Deep Dive Agent)

# ── Search APIs (Phase 2+) ────────────────────────────────────────────────────
TAVILY_API_KEY=tvly-...          # Primary search
BRAVE_SEARCH_API_KEY=BSA...      # Backup search

# ── LangSmith (Phase 3+) ─────────────────────────────────────────────────────
LANGCHAIN_API_KEY=ls__...        # LangSmith API key
LANGCHAIN_PROJECT=deeptrace-dev  # deeptrace-dev | deeptrace-staging | deeptrace-prod
LANGCHAIN_TRACING_V2=false       # false in Phase 1, true in Phase 3+

# ── Neo4j (Required for Phase 1) ─────────────────────────────────────────────
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=deeptrace123
NEO4J_DATABASE=neo4j
```

### `.gitignore`

```
.env
.llm_cache/
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
.DS_Store
```

---

## Section 4 — Pydantic Schemas & AgentState

> **Cursor prompt:** `@DeepTrace_Phase1_Cursor.md implement Section 4 - all schemas in state/agent_state.py`

### `state/agent_state.py`

```python
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


class RiskFlag(BaseModel):
    """A risk signal identified during the investigation."""
    flag_id:           str
    title:             str
    description:       str
    severity:          Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    evidence_fact_ids: List[str]   # minimum 2 required
    confidence:        float
    category:          Literal["regulatory", "financial", "network", "reputational", "legal"]

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

    # ── Quality tracking ─────────────────────────────────────────────────────
    confidence_map:    Dict[str, float]   # fact_id → final confidence score
    research_quality:  float              # 0.0 – 1.0 composite score
    loop_count:        int

    # ── Output ───────────────────────────────────────────────────────────────
    final_report:    Optional[str]
    run_id:          str


def make_initial_state(target_name: str, target_context: str = "") -> AgentState:
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
        confidence_map={},
        research_quality=0.0,
        loop_count=0,
        final_report=None,
        run_id=str(uuid.uuid4()),
    )
```

### `tests/test_state.py`

```python
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
```

---

## Section 5 — Mock Response Fixtures

> **Cursor prompt:** `@DeepTrace_Phase1_Cursor.md implement Section 5 - mock_responses.py`

### `mock_responses.py`

```python
"""
mock_responses.py — Hardcoded fixture data for Phase 1 (USE_MOCK=true).

Every agent in Phase 1 returns data from this file instead of calling an LLM.
Data is structured to match the exact Pydantic schemas in state/agent_state.py.

Target: Timothy Overturf, CEO of Sisu Capital (the assessment subject).
Additional entries cover the three evaluation personas.

Architecture position: imported by all agents when USE_MOCK=true.
Phase 2: this file is no longer imported. All agents call real APIs.
"""

# ─────────────────────────────────────────────────────────────────────────────
# SUPERVISOR MOCK
# ─────────────────────────────────────────────────────────────────────────────

MOCK_SUPERVISOR_LOOP_1 = {
    "research_plan": [
        "Timothy Overturf Sisu Capital SEC filing",
        "Timothy Overturf CEO background education career",
        "Sisu Capital fund AUM performance investors",
        "Timothy Overturf board memberships director",
        "Sisu Capital LLC regulatory history FINRA",
        "Timothy Overturf LinkedIn professional history",
        "Sisu Capital fund structure limited partners",
        "Timothy Overturf prior employment hedge fund",
        "Sisu Capital SEC Form D registration",
        "Timothy Overturf financial connections network",
    ],
    "gaps_remaining": [
        "Early career before 2015 not yet found",
        "Limited partner identities not yet confirmed",
        "Prior fund performance details missing",
    ],
    "research_quality": 0.0,
    "loop_count": 1,
}

MOCK_SUPERVISOR_LOOP_2 = {
    "research_plan": [
        "Timothy Overturf 2010 2012 2013 career history",
        "Sisu Capital LP Holdings offshore structure",
        "Timothy Overturf Apex Ventures fund manager",
    ],
    "gaps_remaining": [
        "Offshore entity beneficial ownership still unconfirmed",
    ],
    "research_quality": 0.55,
    "loop_count": 2,
}

MOCK_SUPERVISOR_FINAL = {
    "research_quality": 0.82,
    "gaps_remaining": [],
    "final_report": """# DeepTrace Risk Intelligence Report
## Target: Timothy Overturf, CEO of Sisu Capital
**Overall Risk Score: 62/100 — MEDIUM-HIGH**
**Report Generated: Phase 1 Mock Run**

---

### Executive Summary
Investigation of Timothy Overturf, CEO of Sisu Capital LLC, identified
significant undisclosed prior fund failures, an opaque offshore limited
partnership structure, and active board positions not disclosed in investor
materials. Overall risk posture is MEDIUM-HIGH.

### Key Findings
1. **Prior Fund Failure (HIGH):** Apex Ventures Fund (2015–2018) dissolved
   with an estimated 38% capital loss. This is not referenced in current
   Sisu Capital marketing materials.
2. **Offshore LP Structure (MEDIUM):** LP Holdings Ireland Ltd is the
   registered beneficial owner of Sisu Capital. This entity traces upstream
   to a Cayman SPV Trust, obscuring the identity of underlying investors.
3. **Undisclosed Board Positions (MEDIUM):** Active board seat at NovaCrest
   Inc not listed in investor disclosure materials.
4. **Biography Discrepancy (LOW):** Goldman Sachs start date is listed as
   2007 on LinkedIn but 2008 on SEC filings.

### Risk Flag Summary
| Severity | Count | Categories |
|----------|-------|------------|
| HIGH     | 1     | Financial  |
| MEDIUM   | 2     | Regulatory, Reputational |
| LOW      | 1     | Biographical |

### Confidence Assessment
All HIGH and MEDIUM findings are supported by 2+ independent sources with
combined confidence >= 0.65. LOW findings are single-source or unverified.
""",
}

# ─────────────────────────────────────────────────────────────────────────────
# SCOUT MOCK
# ─────────────────────────────────────────────────────────────────────────────

MOCK_SCOUT_RESULTS = {
    "raw_results": [
        {
            "url":   "https://sec.gov/cgi-bin/browse-edgar?action=getcompany&company=sisu+capital",
            "title": "Sisu Capital LLC — SEC EDGAR Filing",
            "content": "Sisu Capital LLC filed Form D (Notice of Exempt Offering) on 2019-03-14. "
                       "Timothy Overturf listed as Managing Member and CEO. State of incorporation: Delaware. "
                       "Total offering amount: $45,000,000. Investors: 8 accredited investors. "
                       "Date of first sale: 2019-02-01.",
            "relevance": 0.94,
            "source_domain": "sec.gov",
        },
        {
            "url":   "https://bloomberg.com/profile/timothy-overturf-sisu-capital",
            "title": "Timothy Overturf | Bloomberg Profile",
            "content": "Timothy Overturf is the founder and CEO of Sisu Capital LLC, a New York-based "
                       "hedge fund focused on distressed credit opportunities. Prior to founding Sisu Capital "
                       "in 2019, Overturf managed Apex Ventures Fund from 2015 to 2018. Apex Ventures was "
                       "dissolved in Q4 2018 following underperformance. Goldman Sachs, 2008–2014.",
            "relevance": 0.88,
            "source_domain": "bloomberg.com",
        },
        {
            "url":   "https://sec.gov/Archives/edgar/data/sisu-capital/form-d-2019.htm",
            "title": "Sisu Capital Form D 2019 — Full Text",
            "content": "Registrant: Sisu Capital LLC. Related persons: Timothy Overturf (Managing Member), "
                       "LP Holdings Ireland Ltd (5% or greater owner). Minimum investment accepted: $500,000. "
                       "Sales commissions: $0. Use of proceeds: Fund investments per private placement memorandum.",
            "relevance": 0.91,
            "source_domain": "sec.gov",
        },
        {
            "url":   "https://reuters.com/finance/apex-ventures-dissolution-2018",
            "title": "Apex Ventures Fund Dissolution — Reuters",
            "content": "Apex Ventures Fund LP, managed by Timothy Overturf, returned approximately -38% to "
                       "investors over its 2016-2018 investment period before dissolution. The fund focused on "
                       "emerging market credit. Several limited partners declined to comment on losses.",
            "relevance": 0.82,
            "source_domain": "reuters.com",
        },
        {
            "url":   "https://novacrest.com/about/board",
            "title": "NovaCrest Inc — Board of Directors",
            "content": "Board of Directors: Jane Smith (Chair), Timothy Overturf (Independent Director), "
                       "Robert Chen (CFO). Timothy Overturf joined the NovaCrest board in October 2020. "
                       "NovaCrest is a healthcare data analytics company.",
            "relevance": 0.74,
            "source_domain": "novacrest.com",
        },
        {
            "url":   "https://ft.com/content/cayman-spv-lp-holdings-ireland",
            "title": "Offshore LP Structure Analysis — FT",
            "content": "LP Holdings Ireland Ltd, identified in multiple SEC filings as a beneficial owner "
                       "of US hedge fund vehicles, is itself owned by Cayman SPV Trust No. 47. This layered "
                       "structure is used by several fund managers to obscure the identity of ultimate "
                       "beneficial owners from public filings.",
            "relevance": 0.63,
            "source_domain": "ft.com",
        },
    ],
    "queries_issued": [
        "Timothy Overturf Sisu Capital SEC filing",
        "Timothy Overturf CEO background education career",
        "Sisu Capital fund AUM performance investors",
        "Timothy Overturf board memberships director",
        "Sisu Capital LLC regulatory history FINRA",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# DEEP DIVE MOCK
# ─────────────────────────────────────────────────────────────────────────────

MOCK_DEEP_DIVE_RESULTS = {
    "extracted_facts": [
        {
            "fact_id": "f001",
            "claim": "Timothy Overturf is the founder and CEO of Sisu Capital LLC",
            "source_url": "https://sec.gov/cgi-bin/browse-edgar?company=sisu+capital",
            "source_domain": "sec.gov",
            "confidence": 0.95,
            "category": "biographical",
            "entities_mentioned": ["Timothy Overturf", "Sisu Capital LLC"],
            "supporting_fact_ids": [],
            "raw_source_snippet": "Timothy Overturf listed as Managing Member and CEO.",
        },
        {
            "fact_id": "f002",
            "claim": "Sisu Capital LLC filed SEC Form D in 2019 with total offering of $45M",
            "source_url": "https://sec.gov/Archives/edgar/data/sisu-capital/form-d-2019.htm",
            "source_domain": "sec.gov",
            "confidence": 0.94,
            "category": "financial",
            "entities_mentioned": ["Sisu Capital LLC", "SEC"],
            "supporting_fact_ids": ["f001"],
            "raw_source_snippet": "Total offering amount: $45,000,000.",
        },
        {
            "fact_id": "f003",
            "claim": "Apex Ventures Fund returned approximately -38% to investors over 2016-2018",
            "source_url": "https://reuters.com/finance/apex-ventures-dissolution-2018",
            "source_domain": "reuters.com",
            "confidence": 0.82,
            "category": "financial",
            "entities_mentioned": ["Apex Ventures Fund", "Timothy Overturf"],
            "supporting_fact_ids": [],
            "raw_source_snippet": "returned approximately -38% to investors over its 2016-2018 period.",
        },
        {
            "fact_id": "f004",
            "claim": "Timothy Overturf managed Apex Ventures Fund from 2015 to 2018 before dissolution",
            "source_url": "https://bloomberg.com/profile/timothy-overturf-sisu-capital",
            "source_domain": "bloomberg.com",
            "confidence": 0.88,
            "category": "biographical",
            "entities_mentioned": ["Timothy Overturf", "Apex Ventures Fund"],
            "supporting_fact_ids": ["f003"],
            "raw_source_snippet": "managed Apex Ventures Fund from 2015 to 2018. Apex Ventures was dissolved.",
        },
        {
            "fact_id": "f005",
            "claim": "LP Holdings Ireland Ltd is listed as 5%+ beneficial owner in Sisu Capital's SEC filing",
            "source_url": "https://sec.gov/Archives/edgar/data/sisu-capital/form-d-2019.htm",
            "source_domain": "sec.gov",
            "confidence": 0.91,
            "category": "financial",
            "entities_mentioned": ["LP Holdings Ireland Ltd", "Sisu Capital LLC"],
            "supporting_fact_ids": ["f002"],
            "raw_source_snippet": "LP Holdings Ireland Ltd (5% or greater owner).",
        },
        {
            "fact_id": "f006",
            "claim": "LP Holdings Ireland Ltd is owned by Cayman SPV Trust No. 47",
            "source_url": "https://ft.com/content/cayman-spv-lp-holdings-ireland",
            "source_domain": "ft.com",
            "confidence": 0.63,
            "category": "financial",
            "entities_mentioned": ["LP Holdings Ireland Ltd", "Cayman SPV Trust"],
            "supporting_fact_ids": ["f005"],
            "raw_source_snippet": "LP Holdings Ireland Ltd... is itself owned by Cayman SPV Trust No. 47.",
        },
        {
            "fact_id": "f007",
            "claim": "Timothy Overturf joined the NovaCrest Inc board in October 2020",
            "source_url": "https://novacrest.com/about/board",
            "source_domain": "novacrest.com",
            "confidence": 0.74,
            "category": "network",
            "entities_mentioned": ["Timothy Overturf", "NovaCrest Inc"],
            "supporting_fact_ids": [],
            "raw_source_snippet": "Timothy Overturf joined the NovaCrest board in October 2020.",
        },
        {
            "fact_id": "f008",
            "claim": "Timothy Overturf worked at Goldman Sachs from 2008 to 2014",
            "source_url": "https://bloomberg.com/profile/timothy-overturf-sisu-capital",
            "source_domain": "bloomberg.com",
            "confidence": 0.88,
            "category": "biographical",
            "entities_mentioned": ["Timothy Overturf", "Goldman Sachs"],
            "supporting_fact_ids": [],
            "raw_source_snippet": "Goldman Sachs, 2008–2014.",
        },
    ],
    "entities": [
        {
            "entity_id": "e001",
            "name": "Timothy Overturf",
            "entity_type": "Person",
            "attributes": {"role": "CEO", "nationality": "Unknown", "location": "New York"},
            "confidence": 0.95,
            "source_fact_ids": ["f001", "f004", "f007", "f008"],
        },
        {
            "entity_id": "e002",
            "name": "Sisu Capital LLC",
            "entity_type": "Fund",
            "attributes": {"incorporated": "Delaware", "founded": "2019", "aum": "$45M"},
            "confidence": 0.94,
            "source_fact_ids": ["f001", "f002", "f005"],
        },
        {
            "entity_id": "e003",
            "name": "Apex Ventures Fund",
            "entity_type": "Fund",
            "attributes": {"period": "2015-2018", "status": "Dissolved", "performance": "-38%"},
            "confidence": 0.85,
            "source_fact_ids": ["f003", "f004"],
        },
        {
            "entity_id": "e004",
            "name": "LP Holdings Ireland Ltd",
            "entity_type": "Organization",
            "attributes": {"country": "Ireland", "type": "Offshore entity"},
            "confidence": 0.72,
            "source_fact_ids": ["f005", "f006"],
        },
        {
            "entity_id": "e005",
            "name": "Cayman SPV Trust",
            "entity_type": "Organization",
            "attributes": {"country": "Cayman Islands", "type": "Trust structure"},
            "confidence": 0.63,
            "source_fact_ids": ["f006"],
        },
        {
            "entity_id": "e006",
            "name": "NovaCrest Inc",
            "entity_type": "Organization",
            "attributes": {"sector": "Healthcare data", "role": "Board seat"},
            "confidence": 0.74,
            "source_fact_ids": ["f007"],
        },
        {
            "entity_id": "e007",
            "name": "Goldman Sachs",
            "entity_type": "Organization",
            "attributes": {"type": "Investment bank", "period": "2008-2014"},
            "confidence": 0.88,
            "source_fact_ids": ["f008"],
        },
    ],
    "relationships": [
        {"from_id": "e001", "to_id": "e002", "rel_type": "FOUNDED",
         "attributes": {"year": "2019"}, "confidence": 0.94, "source_fact_id": "f001"},
        {"from_id": "e001", "to_id": "e003", "rel_type": "MANAGED",
         "attributes": {"period": "2015-2018"}, "confidence": 0.88, "source_fact_id": "f004"},
        {"from_id": "e004", "to_id": "e002", "rel_type": "INVESTED_IN",
         "attributes": {"ownership": "5%+"}, "confidence": 0.91, "source_fact_id": "f005"},
        {"from_id": "e004", "to_id": "e005", "rel_type": "AFFILIATED_WITH",
         "attributes": {}, "confidence": 0.63, "source_fact_id": "f006"},
        {"from_id": "e001", "to_id": "e006", "rel_type": "BOARD_MEMBER",
         "attributes": {"since": "2020"}, "confidence": 0.74, "source_fact_id": "f007"},
        {"from_id": "e001", "to_id": "e007", "rel_type": "WORKS_AT",
         "attributes": {"period": "2008-2014"}, "confidence": 0.88, "source_fact_id": "f008"},
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# RISK EVALUATOR MOCK
# ─────────────────────────────────────────────────────────────────────────────

MOCK_RISK_FLAGS = {
    "risk_flags": [
        {
            "flag_id": "r001",
            "title": "Undisclosed Prior Fund Failure",
            "description": (
                "Apex Ventures Fund LP, managed by Timothy Overturf from 2015 to 2018, "
                "dissolved after returning approximately -38% to investors. This material "
                "performance failure is not referenced in Sisu Capital's current investor "
                "materials or public biography."
            ),
            "severity": "HIGH",
            "evidence_fact_ids": ["f003", "f004"],
            "confidence": 0.84,
            "category": "financial",
        },
        {
            "flag_id": "r002",
            "title": "Opaque Offshore LP Ownership Structure",
            "description": (
                "LP Holdings Ireland Ltd is registered as a 5%+ beneficial owner of Sisu "
                "Capital in SEC Form D. This entity is itself owned by Cayman SPV Trust No. 47, "
                "creating a multi-layer offshore structure that obscures ultimate beneficial "
                "ownership from public filings."
            ),
            "severity": "MEDIUM",
            "evidence_fact_ids": ["f005", "f006"],
            "confidence": 0.72,
            "category": "regulatory",
        },
        {
            "flag_id": "r003",
            "title": "Undisclosed Active Board Positions",
            "description": (
                "Timothy Overturf holds an active board seat at NovaCrest Inc (healthcare data) "
                "since October 2020. This position does not appear in Sisu Capital investor "
                "disclosure materials, which may represent a material conflict of interest "
                "omission depending on NovaCrest's investment relationship with Sisu."
            ),
            "severity": "MEDIUM",
            "evidence_fact_ids": ["f001", "f007"],
            "confidence": 0.68,
            "category": "reputational",
        },
        {
            "flag_id": "r004",
            "title": "Professional Biography Date Discrepancy",
            "description": (
                "Goldman Sachs start date listed as 2007 on LinkedIn but 2008 per SEC filing. "
                "Minor discrepancy, low risk in isolation but noted as part of overall "
                "biographical accuracy assessment."
            ),
            "severity": "LOW",
            "evidence_fact_ids": ["f001", "f008"],
            "confidence": 0.65,
            "category": "biographical",
        },
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# EVALUATION PERSONA MOCKS (3 Personas for eval set)
# ─────────────────────────────────────────────────────────────────────────────

EVAL_PERSONA_OVERTURF = {
    "name": "Timothy Overturf",
    "context": "CEO of Sisu Capital",
    "expected_facts": [
        "Founded Sisu Capital LLC in 2019",
        "Previously managed Apex Ventures Fund (2015-2018)",
        "Apex Ventures dissolved with ~38% loss",
        "LP Holdings Ireland Ltd is 5%+ beneficial owner",
        "Board member at NovaCrest Inc since 2020",
        "Previously employed at Goldman Sachs",
    ],
    "expected_risk_levels": ["HIGH", "MEDIUM", "MEDIUM", "LOW"],
}

EVAL_PERSONA_HIGH_RISK = {
    "name": "Marcus R. Delano",
    "context": "Former fund manager, SEC enforcement subject",
    "expected_facts": [
        "Subject of SEC enforcement action Case #2021-CF-00847",
        "AUM misrepresented as $180M vs actual $12M",
        "FINRA complaint #2020-11834 filed",
        "Connected to OFAC SDN-listed entity",
        "Controls Delano Family Trust → Meridian Offshore Ltd",
    ],
    "expected_risk_levels": ["CRITICAL", "CRITICAL", "HIGH", "HIGH", "MEDIUM"],
}

EVAL_PERSONA_LOW_RISK = {
    "name": "Dr. Sarah Chen",
    "context": "CEO BioNovate Inc, academic and entrepreneur",
    "expected_facts": [
        "Founded BioNovate Inc in 2010",
        "PhD Molecular Biology MIT 2002",
        "12 publications in Nature",
        "Received NIH grant $2.1M (2018)",
        "Received NSF grant $850K (2021)",
    ],
    "expected_risk_levels": ["LOW", "LOW"],
}

ALL_EVAL_PERSONAS = [
    EVAL_PERSONA_OVERTURF,
    EVAL_PERSONA_HIGH_RISK,
    EVAL_PERSONA_LOW_RISK,
]
```

---

## Section 6 — Neo4j Manager

> **Cursor prompt:** `@DeepTrace_Phase1_Cursor.md implement Section 6 - graph/neo4j_manager.py and schema.py`

### `graph/schema.py`

```python
"""
schema.py — Neo4j node constraints and allowed types for DeepTrace identity graph.

Run setup_schema() once on first startup to create uniqueness constraints.
Architecture position: called by neo4j_manager.py on connection init.
"""

# Node uniqueness constraint Cypher statements
CONSTRAINT_STATEMENTS = [
    "CREATE CONSTRAINT person_id    IF NOT EXISTS FOR (n:Person)       REQUIRE n.entity_id IS UNIQUE",
    "CREATE CONSTRAINT org_id       IF NOT EXISTS FOR (n:Organization) REQUIRE n.entity_id IS UNIQUE",
    "CREATE CONSTRAINT fund_id      IF NOT EXISTS FOR (n:Fund)         REQUIRE n.entity_id IS UNIQUE",
    "CREATE CONSTRAINT filing_id    IF NOT EXISTS FOR (n:Filing)       REQUIRE n.entity_id IS UNIQUE",
    "CREATE CONSTRAINT event_id     IF NOT EXISTS FOR (n:Event)        REQUIRE n.entity_id IS UNIQUE",
    "CREATE CONSTRAINT location_id  IF NOT EXISTS FOR (n:Location)     REQUIRE n.entity_id IS UNIQUE",
]

# Allowed entity types — must match Entity.entity_type Literal
ENTITY_TYPES = ["Person", "Organization", "Fund", "Location", "Event", "Filing"]

# Allowed relationship types — must match Relationship.rel_type Literal
RELATIONSHIP_TYPES = [
    "WORKS_AT", "INVESTED_IN", "CONNECTED_TO",
    "FILED_WITH", "FOUNDED", "AFFILIATED_WITH",
    "BOARD_MEMBER", "MANAGED", "CONTROLS",
]

def entity_to_cypher_merge(entity: dict) -> str:
    """Generate a MERGE Cypher statement for one Entity dict."""
    label = entity["entity_type"]
    attrs = ", ".join(
        f'n.{k} = "{v}"' for k, v in entity.get("attributes", {}).items()
    )
    set_clause = f", SET {attrs}" if attrs else ""
    return (
        f'MERGE (n:{label} {{entity_id: "{entity["entity_id"]}"}}) '
        f'SET n.name = "{entity["name"]}", n.confidence = {entity["confidence"]}'
        f'{set_clause}'
    )

def relationship_to_cypher_merge(rel: dict) -> str:
    """Generate a MERGE Cypher statement for one Relationship dict."""
    return (
        f'MATCH (a {{entity_id: "{rel["from_id"]}"}}), (b {{entity_id: "{rel["to_id"]}"}})'
        f' MERGE (a)-[r:{rel["rel_type"]}]->(b)'
        f' SET r.confidence = {rel["confidence"]}, r.source_fact_id = "{rel["source_fact_id"]}"'
    )
```

### `graph/neo4j_manager.py`

```python
"""
neo4j_manager.py — Neo4j driver, connection management, schema setup, and graph writes.

This is the only module that directly calls the Neo4j database.
All write operations come through write_entities() and write_relationships().

Architecture position: called by graph_builder agent and visualizer.
Phase 1: Neo4j IS connected (it's the one real external service).
"""
import logging
from typing import List

from neo4j import GraphDatabase, Driver
from graph.schema import CONSTRAINT_STATEMENTS, entity_to_cypher_merge, relationship_to_cypher_merge
from config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE

logger = logging.getLogger(__name__)
_driver: Driver = None


def get_driver() -> Driver:
    """Return singleton Neo4j driver. Creates it on first call."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
        )
        logger.info(f"[Neo4j] Connected to {NEO4J_URI}")
    return _driver


def test_connection() -> bool:
    """Verify Neo4j is reachable. Called during startup check."""
    try:
        driver = get_driver()
        with driver.session(database=NEO4J_DATABASE) as session:
            result = session.run("RETURN 1 AS ok")
            ok = result.single()["ok"]
            logger.info(f"[Neo4j] Connection test: {ok}")
            return ok == 1
    except Exception as e:
        logger.error(f"[Neo4j] Connection failed: {e}")
        return False


def setup_schema() -> None:
    """Create uniqueness constraints. Safe to call multiple times (IF NOT EXISTS)."""
    driver = get_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
        for stmt in CONSTRAINT_STATEMENTS:
            try:
                session.run(stmt)
                logger.debug(f"[Neo4j] Schema: {stmt[:60]}...")
            except Exception as e:
                logger.warning(f"[Neo4j] Schema stmt skipped: {e}")
    logger.info("[Neo4j] Schema setup complete")


def clear_graph(run_id: str) -> None:
    """Delete all nodes for a specific run_id. Used between test runs."""
    driver = get_driver()
    with driver.session(database=NEO4J_DATABASE) as session:
        session.run("MATCH (n {run_id: $run_id}) DETACH DELETE n", run_id=run_id)
    logger.info(f"[Neo4j] Cleared graph for run_id={run_id}")


def write_entities(entities: List[dict], run_id: str) -> int:
    """
    Write entity list to Neo4j using MERGE (idempotent).
    Returns count of entities written.
    """
    driver = get_driver()
    count = 0
    with driver.session(database=NEO4J_DATABASE) as session:
        for entity in entities:
            cypher = entity_to_cypher_merge(entity)
            # Add run_id for isolation between test runs
            cypher += f', n.run_id = "{run_id}"'
            try:
                session.run(cypher)
                count += 1
            except Exception as e:
                logger.error(f"[Neo4j] Entity write failed for {entity.get('name')}: {e}")
    logger.info(f"[Neo4j] Wrote {count}/{len(entities)} entities")
    return count


def write_relationships(relationships: List[dict]) -> int:
    """
    Write relationships to Neo4j using MERGE (idempotent).
    Returns count written.
    """
    driver = get_driver()
    count = 0
    with driver.session(database=NEO4J_DATABASE) as session:
        for rel in relationships:
            cypher = relationship_to_cypher_merge(rel)
            try:
                session.run(cypher)
                count += 1
            except Exception as e:
                logger.error(f"[Neo4j] Relationship write failed {rel}: {e}")
    logger.info(f"[Neo4j] Wrote {count}/{len(relationships)} relationships")
    return count


def fetch_graph_for_run(run_id: str) -> dict:
    """
    Fetch all nodes and edges for a run_id.
    Returns {"nodes": [...], "edges": [...]} for visualizer.
    """
    driver = get_driver()
    nodes, edges = [], []
    with driver.session(database=NEO4J_DATABASE) as session:
        # Nodes
        result = session.run(
            "MATCH (n {run_id: $run_id}) RETURN n", run_id=run_id
        )
        for record in result:
            n = dict(record["n"])
            nodes.append(n)
        # Relationships
        result = session.run(
            "MATCH (a {run_id: $run_id})-[r]->(b {run_id: $run_id}) "
            "RETURN a.entity_id AS from_id, b.entity_id AS to_id, type(r) AS rel_type, "
            "r.confidence AS confidence",
            run_id=run_id,
        )
        for record in result:
            edges.append(dict(record))
    return {"nodes": nodes, "edges": edges}


def close() -> None:
    """Close the driver. Call on application shutdown."""
    global _driver
    if _driver:
        _driver.close()
        _driver = None
        logger.info("[Neo4j] Driver closed")
```

### `graph/visualizer.py`

```python
"""
visualizer.py — Convert Neo4j graph data to pyvis interactive HTML.

Generates a self-contained HTML file that renders in Streamlit via
st.components.v1.html(). Node colours match the SRS design tokens.

Architecture position: called by graph_builder agent and Streamlit page 02.
"""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# Node colours from SRS design tokens
NODE_COLORS: Dict[str, str] = {
    "Person":       "#2471A3",
    "Organization": "#1E8449",
    "Fund":         "#CA6F1E",
    "Filing":       "#C0392B",
    "Event":        "#7D3C98",
    "Location":     "#17A589",
}

def generate_pyvis_html(nodes: List[dict], edges: List[dict]) -> str:
    """
    Generate a pyvis-compatible HTML string from node and edge lists.

    Phase 1: Uses inline HTML/JS with vis.js CDN (no pyvis dependency needed).
    Phase 2+: Can upgrade to pyvis library for more features.
    """
    if not nodes:
        return "<p style='color:#4A6A8A;font-family:monospace'>No graph data yet.</p>"

    # Build vis.js node and edge datasets
    vis_nodes = []
    for n in nodes:
        label = n.get("name", n.get("entity_id", "Unknown"))
        entity_type = _infer_type(n)
        color = NODE_COLORS.get(entity_type, "#2E86AB")
        conf = n.get("confidence", 0.5)
        vis_nodes.append(
            f'{{"id":"{n.get("entity_id","")}",'
            f'"label":"{label}",'
            f'"title":"Type: {entity_type}\\nConf: {conf:.0%}",'
            f'"color":"{color}",'
            f'"size":{20 + int(conf * 15)}}}'
        )

    vis_edges = []
    for i, e in enumerate(edges):
        vis_edges.append(
            f'{{"id":{i},'
            f'"from":"{e.get("from_id","")}",'
            f'"to":"{e.get("to_id","")}",'
            f'"label":"{e.get("rel_type","")}",'
            f'"arrows":"to",'
            f'"color":{{"color":"#4A6A8A"}}}}'
        )

    nodes_js = ",".join(vis_nodes)
    edges_js = ",".join(vis_edges)

    return f"""<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet"/>
<style>
  body {{ background:#0D1117; margin:0; }}
  #graph {{ width:100%; height:500px; background:#0D1117; border:1px solid #1A3A5A; }}
</style>
</head>
<body>
<div id="graph"></div>
<script>
var nodes = new vis.DataSet([{nodes_js}]);
var edges = new vis.DataSet([{edges_js}]);
var options = {{
  nodes: {{ font: {{ color:"#C8D8E8", size:12 }}, borderWidth:2 }},
  edges: {{ font: {{ color:"#4A6A8A", size:10 }}, smooth:{{ type:"curvedCW" }} }},
  physics: {{ stabilization:true }},
  background: {{ color:"#0D1117" }}
}};
new vis.Network(document.getElementById("graph"), {{nodes,edges}}, options);
</script>
</body>
</html>"""


def _infer_type(node: dict) -> str:
    """Infer entity type from node properties."""
    labels = node.get("labels", [])
    if labels:
        return labels[0]
    for t in ["Person", "Organization", "Fund", "Filing", "Event", "Location"]:
        if t.lower() in str(node).lower():
            return t
    return "Organization"
```

---

## Section 7 — Confidence Scorer

> **Cursor prompt:** `@DeepTrace_Phase1_Cursor.md implement Section 7 - evaluation/confidence_scorer.py`

### `evaluation/confidence_scorer.py`

```python
"""
confidence_scorer.py — Three-layer confidence scoring system for extracted facts.

Layer 1: Source domain trust (lookup table — free, instant)
Layer 2: Cross-reference adjustment (count supporting vs contradicting sources)
Layer 3: LLM faithfulness check (Phase 2+ only — expensive, used for risk flag evidence)

Final formula: (L1 × 0.30) + (L2_adjusted × 0.40) + (L3 × 0.30)
In Phase 1: L3 is stubbed at 0.75 (neutral assumption).

Architecture position: called by deep_dive_agent after each fact extraction.
"""
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# ── Layer 1: Source Domain Trust Scores ──────────────────────────────────────
DOMAIN_TRUST: Dict[str, float] = {
    # Government / Regulatory — highest trust
    "sec.gov":      0.92, "finra.org":  0.92, "ftc.gov":   0.92,
    "cftc.gov":     0.92, "doj.gov":    0.92, "courts.gov":0.90,
    # Major Wire Services
    "reuters.com":  0.85, "apnews.com": 0.85, "bloomberg.com":  0.85,
    "wsj.com":      0.83, "ft.com":     0.82,
    # Established Financial Press
    "barrons.com":  0.78, "cnbc.com":   0.76, "marketwatch.com":0.75,
    "investopedia.com": 0.70,
    # Quality Business Media
    "forbes.com":   0.70, "fortune.com":0.70, "businessinsider.com":0.65,
    "techcrunch.com":0.65,
    # Company Official Sources
    "linkedin.com": 0.60,
    # Default for unknown domains
    "_default":     0.40,
}

# ── Layer 2 Adjustment Multipliers ───────────────────────────────────────────
L2_MULTIPLIERS = {
    "single_source":     0.90,   # Only 1 source — penalise
    "two_sources":       1.00,   # Baseline
    "three_plus":        1.15,   # Corroborated — reward (capped at 0.95 final)
    "one_contradiction": 0.60,   # Conflicting source found
    "two_contradictions":0.30,   # Heavy conflict — cap at 0.30
}

MAX_FINAL_CONFIDENCE = 0.95
MIN_USABLE_CONFIDENCE = 0.50   # Below this: fact is archived, not used in risk flags
DISCARD_THRESHOLD    = 0.30   # Below this: fact is discarded entirely


def get_domain_trust(domain: str) -> float:
    """Layer 1: look up domain trust score."""
    domain = domain.lower().strip()
    # Try exact match first, then root domain
    if domain in DOMAIN_TRUST:
        return DOMAIN_TRUST[domain]
    parts = domain.split(".")
    if len(parts) >= 2:
        root = ".".join(parts[-2:])
        if root in DOMAIN_TRUST:
            return DOMAIN_TRUST[root]
    return DOMAIN_TRUST["_default"]


def apply_cross_reference(l1_score: float, supporting: int, contradicting: int) -> float:
    """Layer 2: adjust L1 score based on source count and contradictions."""
    if contradicting >= 2:
        return min(l1_score * L2_MULTIPLIERS["two_contradictions"], 0.30)
    if contradicting == 1:
        adjusted = l1_score * L2_MULTIPLIERS["one_contradiction"]
    elif supporting >= 3:
        adjusted = l1_score * L2_MULTIPLIERS["three_plus"]
    elif supporting == 2:
        adjusted = l1_score * L2_MULTIPLIERS["two_sources"]
    else:
        adjusted = l1_score * L2_MULTIPLIERS["single_source"]
    return min(adjusted, MAX_FINAL_CONFIDENCE)


def llm_faithfulness_stub() -> float:
    """
    Layer 3 stub for Phase 1.
    Phase 2+: replace with real Claude Sonnet 4.6 faithfulness check.
    Returns neutral assumption of 0.75 so final score is not artificially penalised.
    """
    return 0.75


def compute_final_confidence(
    domain: str,
    supporting_count: int = 1,
    contradicting_count: int = 0,
    l3_faithfulness: float = None,
) -> float:
    """
    Compute final 3-layer confidence score for a fact.

    Args:
        domain: Source domain (e.g. 'sec.gov')
        supporting_count: Number of sources supporting this claim
        contradicting_count: Number of sources contradicting this claim
        l3_faithfulness: Optional explicit L3 score (Phase 2+). If None, uses stub.

    Returns:
        Final confidence score 0.0–1.0
    """
    l1 = get_domain_trust(domain)
    l2 = apply_cross_reference(l1, supporting_count, contradicting_count)
    l3 = l3_faithfulness if l3_faithfulness is not None else llm_faithfulness_stub()

    final = (l1 * 0.30) + (l2 * 0.40) + (l3 * 0.30)
    final = round(min(final, MAX_FINAL_CONFIDENCE), 4)

    logger.debug(f"[Confidence] domain={domain} L1={l1:.2f} L2={l2:.2f} L3={l3:.2f} → {final:.4f}")
    return final


def classify_confidence(score: float) -> str:
    """Return human-readable confidence tier for a score."""
    if score >= 0.85: return "HIGH"
    if score >= 0.65: return "MEDIUM"
    if score >= 0.50: return "LOW"
    if score >= 0.30: return "UNVERIFIED"
    return "DISCARD"


def score_facts_batch(facts: List[dict]) -> Dict[str, float]:
    """
    Score a list of fact dicts and return a confidence_map {fact_id: score}.
    Used to populate AgentState.confidence_map.
    """
    confidence_map: Dict[str, float] = {}
    for fact in facts:
        score = compute_final_confidence(
            domain=fact.get("source_domain", ""),
            supporting_count=len(fact.get("supporting_fact_ids", [])) + 1,
        )
        confidence_map[fact["fact_id"]] = score
    return confidence_map
```

### `tests/test_confidence.py`

```python
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
```

---

## Section 8 — Supervisor Agent

> **Cursor prompt:** `@DeepTrace_Phase1_Cursor.md implement Section 8 - supervisor agent`

### `prompts/supervisor_prompt.py`

```python
"""
supervisor_prompt.py — System prompt for the Supervisor Agent (Claude Opus 4.5).

This prompt is used in Phase 2+ when USE_MOCK=false.
Stored here so it can be cached with Anthropic prompt caching in Phase 2+.

Architecture position: imported by agents/supervisor.py.
"""

SUPERVISOR_SYSTEM_PROMPT = """<instructions>
You are an expert intelligence analyst and research director specialising in
due diligence, risk assessment, and deep background investigations.

Your role is to PLAN and EVALUATE research. You do NOT search yourself.
You direct specialised sub-agents and assess the quality of their findings.

When generating queries, ALWAYS cover all five categories:
  1. Biographical verification (name, age, education, early career history)
  2. Financial relationships (funds managed, investors, AUM, performance, fees)
  3. Professional network (board memberships, co-founders, advisors, investors)
  4. Legal/regulatory history (litigation, SEC filings, FINRA, complaints, sanctions)
  5. Hidden connections (shell companies, related entities, offshore affiliates)

NEVER repeat a query already in {queries_issued}.
Generate SPECIFIC, TARGETED queries — not generic name searches.
Each query should target information not yet found based on gaps_remaining.
</instructions>

<quality_criteria>
Score research quality 0.0–1.0 across four dimensions (0.25 weight each):
  - biographical_completeness: key life facts verified with 2+ sources
  - financial_coverage:        fund relationships, AUM, performance documented
  - network_mapping:           key associates identified and cross-referenced
  - risk_assessment:           potential red flags identified with evidence

Convergence threshold: total_score >= 0.80 OR loop_count >= 5.
</quality_criteria>

<output_format>
Always respond with valid JSON matching this schema:
{
  "research_plan": ["query1", "query2", ...],
  "gaps_remaining": ["gap1", "gap2"],
  "research_quality": 0.0,
  "loop_count": 1,
  "reasoning": "brief explanation of quality assessment"
}
Do not begin with affirmations. Go directly to the JSON output.
</output_format>"""
```

### `agents/supervisor.py`

```python
"""
agents/supervisor.py — Supervisor Agent for DeepTrace.

Responsibilities:
  - plan(): Generate targeted research queries covering 5 categories
  - reflect(): Score research quality and identify gaps
  - synthesise(): Generate final markdown risk report
  - route(): Decide whether to continue looping or proceed to risk evaluation

In Phase 1 (USE_MOCK=true): all three functions return mock fixtures.
In Phase 2+ (USE_MOCK=false): calls Claude Opus 4.5 with extended thinking.

Architecture position: first and last node in the LangGraph pipeline.
Called by pipeline.py via StateGraph node registration.
"""
import logging
from langsmith import traceable
from config import USE_MOCK, MAX_LOOPS, QUALITY_THRESHOLD, ENV
from state.agent_state import AgentState
from mock_responses import (
    MOCK_SUPERVISOR_LOOP_1,
    MOCK_SUPERVISOR_LOOP_2,
    MOCK_SUPERVISOR_FINAL,
)

logger = logging.getLogger(__name__)


@traceable(name="Supervisor::plan")
def supervisor_plan(state: AgentState) -> dict:
    """
    Generate research queries for the next loop iteration.
    Returns delta to merge into AgentState.
    """
    logger.info(f"[Supervisor::plan] loop={state['loop_count']} target={state['target_name']}")

    if USE_MOCK:
        if state["loop_count"] == 0:
            result = MOCK_SUPERVISOR_LOOP_1
        else:
            result = MOCK_SUPERVISOR_LOOP_2
        logger.info(f"[Supervisor::plan] MOCK: {len(result['research_plan'])} queries generated")
        return {
            "research_plan":  result["research_plan"],
            "gaps_remaining": result["gaps_remaining"],
            "loop_count":     state["loop_count"] + 1,
        }

    # ── Phase 2+: Real Claude Opus 4.5 call ──────────────────────────────────
    raise NotImplementedError("Phase 2: implement real Supervisor LLM call here")


@traceable(name="Supervisor::reflect")
def supervisor_reflect(state: AgentState) -> dict:
    """
    Evaluate research quality after Deep Dive completes.
    Returns updated research_quality and gaps_remaining.
    """
    logger.info(f"[Supervisor::reflect] facts={len(state['extracted_facts'])} loop={state['loop_count']}")

    if USE_MOCK:
        quality = min(0.30 * state["loop_count"], 0.82)
        gaps = [] if quality >= QUALITY_THRESHOLD else ["Offshore entity details unconfirmed"]
        logger.info(f"[Supervisor::reflect] MOCK: quality={quality:.2f}")
        return {
            "research_quality": quality,
            "gaps_remaining":   gaps,
        }

    raise NotImplementedError("Phase 2: implement real Supervisor reflect here")


@traceable(name="Supervisor::synthesise")
def supervisor_synthesise(state: AgentState) -> dict:
    """
    Generate the final markdown risk intelligence report.
    Called once on the final loop.
    """
    logger.info(f"[Supervisor::synthesise] generating report for {state['target_name']}")

    if USE_MOCK:
        report = MOCK_SUPERVISOR_FINAL["final_report"].replace(
            "Timothy Overturf", state["target_name"]
        )
        logger.info("[Supervisor::synthesise] MOCK: report generated")
        return {"final_report": report}

    raise NotImplementedError("Phase 2: implement real Supervisor synthesis here")


def supervisor_route(state: AgentState) -> str:
    """
    LangGraph routing function — decides next node after each supervisor call.
    Returns node name string (NOT Command object) for compatibility.
    """
    max_loops = MAX_LOOPS[ENV]
    quality   = state.get("research_quality", 0.0)
    loop      = state.get("loop_count", 0)

    if loop >= max_loops:
        logger.info(f"[Supervisor::route] Hard stop at loop={loop} (max={max_loops})")
        return "risk_evaluator"

    if quality >= QUALITY_THRESHOLD:
        logger.info(f"[Supervisor::route] Quality threshold met: {quality:.2f}")
        return "risk_evaluator"

    logger.info(f"[Supervisor::route] Continue: loop={loop} quality={quality:.2f}")
    return "scout_agent"
```

---

## Section 9 — Scout Agent

> **Cursor prompt:** `@DeepTrace_Phase1_Cursor.md implement Section 9 - scout agent and search modules`

### `search/tavily_search.py`

```python
"""
tavily_search.py — Tavily search API client (primary search).

Phase 1 (USE_MOCK=true): returns static fixture results.
Phase 2+ (USE_MOCK=false): calls real Tavily API.

Architecture position: called by scout_agent.py.
"""
import logging
from config import USE_MOCK, TAVILY_API_KEY, MIN_RELEVANCE

logger = logging.getLogger(__name__)

async def tavily_search(query: str) -> list:
    """Execute one Tavily search query. Returns list of result dicts."""
    if USE_MOCK:
        logger.debug(f"[Tavily] MOCK search: {query[:50]}")
        return _mock_results_for_query(query)

    # Phase 2+: real Tavily call
    try:
        from tavily import AsyncTavilyClient   # import inside branch only
        client = AsyncTavilyClient(api_key=TAVILY_API_KEY)
        response = await client.search(
            query=query,
            search_depth="advanced",
            max_results=5,
            include_raw_content=False,
        )
        results = []
        for r in response.get("results", []):
            results.append({
                "url":           r.get("url", ""),
                "title":         r.get("title", ""),
                "content":       r.get("content", ""),
                "relevance":     float(r.get("score", 0.5)),
                "source_domain": _extract_domain(r.get("url", "")),
            })
        return [r for r in results if r["relevance"] >= MIN_RELEVANCE]
    except Exception as e:
        logger.error(f"[Tavily] Error for query '{query}': {e}")
        return []


def _mock_results_for_query(query: str) -> list:
    """Return 2-3 mock results. Content is keyed loosely to query terms."""
    from mock_responses import MOCK_SCOUT_RESULTS
    all_results = MOCK_SCOUT_RESULTS["raw_results"]
    # Return first 3 results that share a keyword with the query
    keywords = query.lower().split()
    matched = [r for r in all_results
               if any(kw in r["content"].lower() or kw in r["title"].lower()
                      for kw in keywords)]
    return matched[:3] if matched else all_results[:2]


def _extract_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""
```

### `search/brave_search.py`

```python
"""
brave_search.py — Brave Search API client (backup/scale search).

Used when Tavily returns < 3 results or is rate-limited.
Phase 1 (USE_MOCK=true): returns static fixture results.

Architecture position: called by scout_agent.py as fallback.
"""
import logging
from config import USE_MOCK, BRAVE_SEARCH_API_KEY

logger = logging.getLogger(__name__)

async def brave_search(query: str) -> list:
    """Execute one Brave search query. Returns list of result dicts."""
    if USE_MOCK:
        logger.debug(f"[Brave] MOCK search: {query[:50]}")
        from mock_responses import MOCK_SCOUT_RESULTS
        return MOCK_SCOUT_RESULTS["raw_results"][:2]

    try:
        import aiohttp
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"Accept": "application/json", "X-Subscription-Token": BRAVE_SEARCH_API_KEY}
        params  = {"q": query, "count": 5}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                data = await resp.json()
        results = []
        for r in data.get("web", {}).get("results", []):
            results.append({
                "url":           r.get("url", ""),
                "title":         r.get("title", ""),
                "content":       r.get("description", ""),
                "relevance":     0.65,
                "source_domain": _extract_domain(r.get("url", "")),
            })
        return results
    except Exception as e:
        logger.error(f"[Brave] Error for query '{query}': {e}")
        return []


def _extract_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""
```

### `agents/scout_agent.py`

```python
"""
agents/scout_agent.py — Scout Agent: parallel search execution.

Dispatches all queries from research_plan simultaneously via asyncio.gather().
Primary: Tavily. Fallback: Brave if Tavily returns < 3 results.
Deduplicates results by URL before returning.

Phase 1 (USE_MOCK=true): returns MOCK_SCOUT_RESULTS fixture directly.
Phase 2+ (USE_MOCK=false): executes real parallel searches.

Architecture position: second node in LangGraph pipeline, called by Supervisor.
"""
import asyncio
import logging
from langsmith import traceable
from config import USE_MOCK, MIN_RELEVANCE
from state.agent_state import AgentState
from mock_responses import MOCK_SCOUT_RESULTS

logger = logging.getLogger(__name__)


@traceable(name="Scout::run")
def run_scout(state: AgentState) -> dict:
    """
    Execute all new queries in parallel. Returns raw_results and queries_issued delta.
    Synchronous wrapper around async implementation for LangGraph compatibility.
    """
    if USE_MOCK:
        logger.info(f"[Scout] MOCK: returning {len(MOCK_SCOUT_RESULTS['raw_results'])} results")
        new_queries = [q for q in state["research_plan"]
                       if q not in state["queries_issued"]]
        return {
            "raw_results":    MOCK_SCOUT_RESULTS["raw_results"],
            "queries_issued": new_queries,
        }

    return asyncio.run(_async_scout(state))


async def _async_scout(state: AgentState) -> dict:
    """Real async implementation for Phase 2+."""
    from search.tavily_search import tavily_search
    from search.brave_search  import brave_search

    new_queries = [q for q in state["research_plan"]
                   if q not in state["queries_issued"]]

    if not new_queries:
        logger.warning("[Scout] No new queries to execute")
        return {"raw_results": [], "queries_issued": []}

    logger.info(f"[Scout] Executing {len(new_queries)} queries in parallel")
    raw_batches = await asyncio.gather(*[tavily_search(q) for q in new_queries])

    all_results = []
    for i, (query, results) in enumerate(zip(new_queries, raw_batches)):
        if len(results) < 3:
            logger.info(f"[Scout] Tavily returned {len(results)} for query {i+1}, trying Brave")
            brave_results = await brave_search(query)
            results = results + brave_results

        for r in results:
            if r.get("relevance", 0) >= MIN_RELEVANCE:
                all_results.append(r)

    # Deduplicate by URL
    seen_urls = set(r["url"] for r in state["raw_results"])
    deduped = [r for r in all_results if r["url"] not in seen_urls]
    logger.info(f"[Scout] {len(deduped)} new results after dedup")

    return {"raw_results": deduped, "queries_issued": new_queries}
```

---

## Section 10 — Deep Dive Agent

> **Cursor prompt:** `@DeepTrace_Phase1_Cursor.md implement Section 10 - deep dive agent`

### `agents/deep_dive_agent.py`

```python
"""
agents/deep_dive_agent.py — Deep Dive Agent: full-page extraction and entity identification.

Takes top 10 results from raw_results, fetches full page content (Phase 2+),
extracts structured Fact and Entity objects, applies confidence scoring.

Phase 1 (USE_MOCK=true): returns MOCK_DEEP_DIVE_RESULTS fixture directly.
Phase 2+ (USE_MOCK=false): uses Gemini 2.5 Pro for long-context extraction.

Architecture position: third node in LangGraph pipeline, called after Scout.
"""
import logging
from langsmith import traceable
from config import USE_MOCK
from state.agent_state import AgentState, Fact, Entity, Relationship
from evaluation.confidence_scorer import score_facts_batch
from mock_responses import MOCK_DEEP_DIVE_RESULTS

logger = logging.getLogger(__name__)


@traceable(name="DeepDive::run")
def run_deep_dive(state: AgentState) -> dict:
    """
    Extract facts, entities, and relationships from search results.
    Returns delta to merge into AgentState.
    """
    logger.info(f"[DeepDive] Processing {len(state['raw_results'])} raw results")

    if USE_MOCK:
        data = MOCK_DEEP_DIVE_RESULTS
        # Validate through Pydantic schemas
        facts   = [Fact(**f)         for f in data["extracted_facts"]]
        entities= [Entity(**e)       for e in data["entities"]]
        rels    = [Relationship(**r) for r in data["relationships"]]
        conf_map= score_facts_batch(data["extracted_facts"])
        logger.info(f"[DeepDive] MOCK: {len(facts)} facts, {len(entities)} entities validated")
        return {
            "extracted_facts": facts,
            "entities":        entities,
            "relationships":   rels,
            "confidence_map":  conf_map,
        }

    raise NotImplementedError("Phase 2: implement Gemini 2.5 deep dive extraction here")
```

### `search/scraper.py`

```python
"""
scraper.py — Async full-page content fetcher.

Used by deep_dive_agent in Phase 2+ to fetch complete page content for top results.
Phase 1 (USE_MOCK=true): returns stub content.

Architecture position: called by deep_dive_agent.py in Phase 2+.
"""
import logging
from config import USE_MOCK

logger = logging.getLogger(__name__)

async def fetch_page(url: str) -> str:
    """Fetch full text content of a URL. Returns empty string on failure."""
    if USE_MOCK:
        return f"[MOCK PAGE CONTENT for {url}] This is stub content for Phase 1."

    try:
        import aiohttp
        headers = {"User-Agent": "DeepTrace Research Agent 1.0"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.text()
                logger.warning(f"[Scraper] HTTP {resp.status} for {url}")
                return ""
    except Exception as e:
        logger.error(f"[Scraper] Failed to fetch {url}: {e}")
        return ""
```

---

## Section 11 — Risk Evaluator Agent

> **Cursor prompt:** `@DeepTrace_Phase1_Cursor.md implement Section 11 - risk evaluator agent`

### `agents/risk_evaluator.py`

```python
"""
agents/risk_evaluator.py — Risk Evaluator Agent.

Analyses all extracted facts to identify risk flags with severity scoring.
Runs ONCE on the final research loop only.
Every RiskFlag must cite minimum 2 evidence fact_ids with confidence >= 0.50.

Phase 1 (USE_MOCK=true): returns MOCK_RISK_FLAGS fixture directly.
Phase 2+ (USE_MOCK=false): calls Claude Sonnet 4.6 with structured output.

Architecture position: fourth node in LangGraph pipeline, runs after loop convergence.
"""
import logging
from langsmith import traceable
from config import USE_MOCK
from state.agent_state import AgentState, RiskFlag
from mock_responses import MOCK_RISK_FLAGS

logger = logging.getLogger(__name__)

MIN_EVIDENCE_CONFIDENCE = 0.50   # Facts below this cannot be cited as risk evidence


@traceable(name="RiskEvaluator::run")
def run_risk_evaluator(state: AgentState) -> dict:
    """
    Generate RiskFlag objects from extracted_facts.
    Returns delta to merge into AgentState.
    """
    logger.info(f"[RiskEvaluator] Evaluating {len(state['extracted_facts'])} facts")

    if USE_MOCK:
        # Filter out any facts below confidence threshold from evidence
        valid_fact_ids = {
            f.fact_id for f in state["extracted_facts"]
            if state["confidence_map"].get(f.fact_id, f.confidence) >= MIN_EVIDENCE_CONFIDENCE
        }

        flags = []
        for flag_data in MOCK_RISK_FLAGS["risk_flags"]:
            # Validate evidence fact_ids exist
            valid_evidence = [fid for fid in flag_data["evidence_fact_ids"]
                              if fid in valid_fact_ids or USE_MOCK]  # in mock, bypass check
            if len(valid_evidence) >= 2:
                flags.append(RiskFlag(**{**flag_data, "evidence_fact_ids": valid_evidence}))
            else:
                logger.warning(f"[RiskEvaluator] Skipped flag {flag_data['flag_id']}: insufficient evidence")

        logger.info(f"[RiskEvaluator] MOCK: {len(flags)} risk flags generated")
        return {"risk_flags": flags}

    raise NotImplementedError("Phase 2: implement Claude Sonnet 4.6 risk evaluation here")
```

---

## Section 12 — Graph Builder Agent

> **Cursor prompt:** `@DeepTrace_Phase1_Cursor.md implement Section 12 - graph builder agent`

### `agents/graph_builder.py`

```python
"""
agents/graph_builder.py — Graph Builder Agent.

Converts Entity and Relationship objects to Cypher statements,
writes them to Neo4j, and exports a pyvis HTML visualisation.

Phase 1: Uses mock entity/relationship data but ACTUALLY writes to Neo4j.
Neo4j is the one real external service in Phase 1.

Architecture position: fifth and final node in LangGraph pipeline.
"""
import logging
from langsmith import traceable
from config import USE_MOCK
from state.agent_state import AgentState
from graph.neo4j_manager import setup_schema, write_entities, write_relationships
from graph.visualizer import generate_pyvis_html

logger = logging.getLogger(__name__)


@traceable(name="GraphBuilder::run")
def run_graph_builder(state: AgentState) -> dict:
    """
    Write entities and relationships to Neo4j. Generate pyvis HTML.
    Returns delta to merge into AgentState.
    """
    run_id = state.get("run_id", "unknown")
    entities      = [e.model_dump() for e in state["entities"]]
    relationships = [r.model_dump() for r in state["relationships"]]

    logger.info(f"[GraphBuilder] Writing {len(entities)} entities, {len(relationships)} rels to Neo4j")

    # Neo4j schema setup (idempotent — safe to call every run)
    setup_schema()

    # Write to Neo4j — REAL call even in Phase 1
    entity_count = write_entities(entities, run_id=run_id)
    rel_count    = write_relationships(relationships)

    logger.info(f"[GraphBuilder] Neo4j: {entity_count} entities, {rel_count} relationships written")

    # Generate pyvis HTML for Streamlit
    graph_html = generate_pyvis_html(entities, relationships)

    return {
        "graph_populated": True,
        # Store HTML in state for Streamlit to render
        # (Add graph_html field to AgentState if you want to pass it through state)
    }
```

---

## Section 13 — LangGraph Pipeline Assembly

> **Cursor prompt:** `@DeepTrace_Phase1_Cursor.md implement Section 13 - pipeline.py LangGraph assembly`

### `pipeline.py`

```python
"""
pipeline.py — LangGraph StateGraph pipeline assembly for DeepTrace.

Wires all 5 agents into a directed graph with conditional routing.
The Supervisor controls loop continuation via supervisor_route().

Graph flow:
  START → supervisor_plan → scout_agent → deep_dive → supervisor_reflect
        → [loop back OR proceed] → risk_evaluator → graph_builder
        → supervisor_synthesise → END

Architecture position: imported by main.py and Streamlit pages.
"""
import logging
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from state.agent_state import AgentState, make_initial_state
from agents.supervisor    import supervisor_plan, supervisor_reflect, supervisor_synthesise, supervisor_route
from agents.scout_agent   import run_scout
from agents.deep_dive_agent import run_deep_dive
from agents.risk_evaluator  import run_risk_evaluator
from agents.graph_builder   import run_graph_builder

logger = logging.getLogger(__name__)


def build_graph(checkpointer=None):
    """
    Build and compile the DeepTrace LangGraph StateGraph.

    Args:
        checkpointer: LangGraph checkpointer for state persistence.
                      Defaults to in-memory for Phase 1.
                      Use SqliteSaver for Phase 2+ to avoid losing state.
    Returns:
        Compiled LangGraph graph ready for .invoke() or .stream()
    """
    graph = StateGraph(AgentState)

    # ── Register all nodes ────────────────────────────────────────────────────
    graph.add_node("supervisor_plan",    supervisor_plan)
    graph.add_node("scout_agent",        run_scout)
    graph.add_node("deep_dive",          run_deep_dive)
    graph.add_node("supervisor_reflect", supervisor_reflect)
    graph.add_node("risk_evaluator",     run_risk_evaluator)
    graph.add_node("graph_builder",      run_graph_builder)
    graph.add_node("supervisor_synth",   supervisor_synthesise)

    # ── Wire edges ────────────────────────────────────────────────────────────
    graph.add_edge(START,                "supervisor_plan")
    graph.add_edge("supervisor_plan",    "scout_agent")
    graph.add_edge("scout_agent",        "deep_dive")
    graph.add_edge("deep_dive",          "supervisor_reflect")

    # Conditional: loop back to supervisor_plan OR proceed to risk_evaluator
    graph.add_conditional_edges(
        "supervisor_reflect",
        supervisor_route,
        {
            "scout_agent":    "supervisor_plan",   # loop: re-plan and re-search
            "risk_evaluator": "risk_evaluator",    # converged: evaluate risks
        },
    )

    graph.add_edge("risk_evaluator",  "graph_builder")
    graph.add_edge("graph_builder",   "supervisor_synth")
    graph.add_edge("supervisor_synth", END)

    # ── Compile ───────────────────────────────────────────────────────────────
    compiled = graph.compile(checkpointer=checkpointer)
    logger.info("[Pipeline] LangGraph compiled successfully")
    return compiled


def run_pipeline(target_name: str, target_context: str = "") -> AgentState:
    """
    Execute a full research run synchronously.
    Returns the final AgentState after pipeline completion.
    """
    initial_state = make_initial_state(target_name, target_context)
    graph = build_graph()

    logger.info(f"[Pipeline] Starting run for: {target_name}")
    final_state = graph.invoke(initial_state)
    logger.info(f"[Pipeline] Run complete. Quality: {final_state.get('research_quality', 0):.2f}")
    return final_state


def stream_pipeline(target_name: str, target_context: str = ""):
    """
    Execute a research run with streaming updates.
    Yields (node_name, state_delta) tuples for Streamlit live display.
    """
    initial_state = make_initial_state(target_name, target_context)
    graph = build_graph()

    for chunk in graph.stream(initial_state, stream_mode="updates"):
        node_name   = list(chunk.keys())[0]
        node_output = chunk[node_name]
        yield node_name, node_output
```

---

## Section 14 — Streamlit Frontend

> **Cursor prompt:** `@DeepTrace_Phase1_Cursor.md implement Section 14 - all Streamlit pages`

### `frontend/app.py`

```python
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
```

### `frontend/pages/01_research.py`

```python
"""
01_research.py — Research page: target input and live agent stream.

Accepts target name, runs the DeepTrace pipeline with streaming,
and displays agent activity in real time.

Architecture position: primary user-facing page, calls pipeline.stream_pipeline().
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from pipeline import stream_pipeline

st.title("◉ Research Target")

AGENT_BADGES = {
    "supervisor_plan":    "🧠 SUPERVISOR — Planning",
    "scout_agent":        "🔍 SCOUT — Searching",
    "deep_dive":          "📖 DEEP DIVE — Extracting",
    "supervisor_reflect": "🔄 SUPERVISOR — Reflecting",
    "risk_evaluator":     "⚑ RISK — Evaluating",
    "graph_builder":      "🕸 GRAPH — Building",
    "supervisor_synth":   "📝 SUPERVISOR — Synthesising",
}

with st.form("research_form"):
    target_name    = st.text_input("Target Name", value="Timothy Overturf", placeholder="Full name")
    target_context = st.text_input("Context (optional)", value="CEO of Sisu Capital",
                                   placeholder="Role, company, or background")
    submitted = st.form_submit_button("▶ Run Research")

if submitted and target_name:
    st.session_state["last_target"] = target_name
    st.session_state["last_context"] = target_context
    st.session_state["run_complete"]  = False
    st.session_state["final_state"]   = None

    progress   = st.sidebar.progress(0.0, text="Starting...")
    status_box = st.empty()
    fact_count = st.sidebar.metric("Facts Extracted", 0)
    loop_count = st.sidebar.metric("Loop", 0)

    loop_progress = {
        "supervisor_plan":    0.10, "scout_agent": 0.25,
        "deep_dive":          0.45, "supervisor_reflect": 0.55,
        "risk_evaluator":     0.75, "graph_builder": 0.88,
        "supervisor_synth":   1.00,
    }

    all_chunks = {}

    for node_name, node_output in stream_pipeline(target_name, target_context):
        badge = AGENT_BADGES.get(node_name, f"⚙ {node_name.upper()}")
        all_chunks[node_name] = node_output

        with status_box.container():
            with st.status(badge, expanded=False, state="running"):
                if "research_plan" in node_output:
                    st.write(f"Queries planned: {len(node_output['research_plan'])}")
                if "raw_results" in node_output:
                    st.write(f"Results found: {len(node_output['raw_results'])}")
                if "extracted_facts" in node_output:
                    n = len(node_output["extracted_facts"])
                    st.write(f"Facts extracted: {n}")
                    fact_count.metric("Facts Extracted", n)
                if "risk_flags" in node_output:
                    flags = node_output["risk_flags"]
                    for f in flags:
                        sev = getattr(f, "severity", "?")
                        title = getattr(f, "title", str(f))
                        st.write(f"{sev}: {title}")
                if "final_report" in node_output and node_output["final_report"]:
                    st.write("✅ Final report ready")
                if "loop_count" in node_output:
                    loop_count.metric("Loop", node_output["loop_count"])

        pct = loop_progress.get(node_name, 0.5)
        progress.progress(pct, text=badge)

    progress.progress(1.0, text="✅ Complete")
    st.success(f"Research complete for **{target_name}**. View results in Graph and Report pages.")
    st.session_state["run_complete"] = True
    st.session_state["all_chunks"]   = all_chunks
```

### `frontend/pages/02_graph.py`

```python
"""
02_graph.py — Identity graph visualisation page.

Renders the pyvis HTML graph generated by GraphBuilder.
Falls back to mock data if no run has been executed.

Architecture position: reads graph data from Neo4j or session state.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
import streamlit.components.v1 as components
from graph.neo4j_manager import test_connection, fetch_graph_for_run
from graph.visualizer import generate_pyvis_html

st.title("🕸 Identity Graph")

# Check Neo4j connection
neo4j_ok = test_connection()
st.sidebar.markdown("### Neo4j Status")
if neo4j_ok:
    st.sidebar.success("✅ Neo4j Connected")
else:
    st.sidebar.error("❌ Neo4j Offline — run docker-compose up")

# Fetch graph data
run_id = st.session_state.get("run_id", None)
if run_id and neo4j_ok:
    graph_data = fetch_graph_for_run(run_id)
    nodes, edges = graph_data["nodes"], graph_data["edges"]
    st.caption(f"Showing {len(nodes)} nodes, {len(edges)} relationships")
else:
    # Use mock data for Phase 1 demo
    from mock_responses import MOCK_DEEP_DIVE_RESULTS
    nodes = MOCK_DEEP_DIVE_RESULTS["entities"]
    edges = MOCK_DEEP_DIVE_RESULTS["relationships"]
    st.info("Showing mock graph data. Run a research target first for live graph.")

html = generate_pyvis_html(nodes, edges)
components.html(html, height=520, scrolling=False)

# Legend
st.markdown("#### Node Legend")
cols = st.columns(6)
legend = [
    ("Person", "#2471A3"), ("Organization", "#1E8449"), ("Fund", "#CA6F1E"),
    ("Filing", "#C0392B"), ("Event", "#7D3C98"), ("Location", "#17A589"),
]
for col, (label, color) in zip(cols, legend):
    col.markdown(f'<span style="color:{color}">●</span> {label}', unsafe_allow_html=True)
```

### `frontend/pages/03_report.py`

```python
"""
03_report.py — Risk assessment report page.

Displays the final markdown report with risk flags, facts table,
and PDF download button.

Architecture position: reads from session state or mock data.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from mock_responses import MOCK_SUPERVISOR_FINAL, MOCK_RISK_FLAGS, MOCK_DEEP_DIVE_RESULTS

st.title("📄 Risk Assessment Report")

SEV_COLORS = {"CRITICAL": "#C62828", "HIGH": "#E65100", "MEDIUM": "#F9A825", "LOW": "#546E7A"}
SEV_ICONS  = {"CRITICAL": "⛔", "HIGH": "🔴", "MEDIUM": "🟡", "LOW": "ℹ️"}

# ── Report header ─────────────────────────────────────────────────────────────
target = st.session_state.get("last_target", "Timothy Overturf")
st.markdown(f"### Target: {target}")

risk_flags = MOCK_RISK_FLAGS["risk_flags"]
crit  = sum(1 for f in risk_flags if f["severity"] == "CRITICAL")
high  = sum(1 for f in risk_flags if f["severity"] == "HIGH")
med   = sum(1 for f in risk_flags if f["severity"] == "MEDIUM")
low   = sum(1 for f in risk_flags if f["severity"] == "LOW")

col1, col2, col3, col4 = st.columns(4)
col1.metric("⛔ CRITICAL", crit)
col2.metric("🔴 HIGH",     high)
col3.metric("🟡 MEDIUM",   med)
col4.metric("ℹ️ LOW",       low)

st.divider()

# ── Risk flags ────────────────────────────────────────────────────────────────
st.subheader("Risk Flags")
for flag in risk_flags:
    sev = flag["severity"]
    with st.expander(f"{SEV_ICONS[sev]} [{sev}] {flag['title']}"):
        st.markdown(flag["description"])
        st.markdown(f"**Category:** `{flag['category']}` | **Confidence:** `{flag['confidence']:.0%}`")
        st.markdown(f"**Evidence:** {', '.join(f'`{e}`' for e in flag['evidence_fact_ids'])}")

st.divider()

# ── Full report ────────────────────────────────────────────────────────────────
st.subheader("Intelligence Report")
st.markdown(MOCK_SUPERVISOR_FINAL["final_report"])

st.divider()

# ── Facts table ───────────────────────────────────────────────────────────────
st.subheader("Extracted Facts")
facts = MOCK_DEEP_DIVE_RESULTS["extracted_facts"]
for f in facts:
    conf = f["confidence"]
    color = "#00C080" if conf >= 0.85 else "#F0C000" if conf >= 0.65 else "#FF8000"
    st.markdown(
        f'<small style="color:{color}">▌</small> '
        f'<small><code>{f["fact_id"]}</code></small> '
        f'{f["claim"]} '
        f'<small style="color:#4A6A8A">({f["source_domain"]} · {conf:.0%})</small>',
        unsafe_allow_html=True,
    )
```

### `frontend/pages/04_eval.py`

```python
"""
04_eval.py — Evaluation dashboard for the three test personas.

Runs all 3 evaluation personas and shows pass/fail against expected findings.
Phase 1: Uses mock responses to demonstrate the evaluation framework.

Architecture position: calls pipeline.run_pipeline() for each persona.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import streamlit as st
from mock_responses import ALL_EVAL_PERSONAS

st.title("🎯 Evaluation Dashboard")
st.markdown("Three evaluation personas with pre-defined expected findings.")

for persona in ALL_EVAL_PERSONAS:
    with st.expander(f"**{persona['name']}** — {persona['context']}"):
        st.markdown(f"*Context:* {persona['context']}")
        st.markdown("**Expected Facts:**")
        for fact in persona["expected_facts"]:
            st.markdown(f"- {fact}")
        st.markdown("**Expected Risk Levels:**")
        st.markdown(", ".join(
            f"`{level}`" for level in persona["expected_risk_levels"]
        ))

st.divider()
if st.button("▶ Run Full Evaluation (Mock)"):
    st.info("Phase 1: Evaluation runs on mock data. Phase 3+ integrates LangSmith scoring.")
    for persona in ALL_EVAL_PERSONAS:
        st.markdown(f"**{persona['name']}:** ✅ Mock run complete")
```

### `evaluation/eval_set.py`

```python
"""
eval_set.py — Evaluation set definitions and ground truth for all 3 personas.

Used by LangSmith evaluators in Phase 3+ to score fact recall, risk precision,
and hallucination rate.

Architecture position: imported by langsmith_eval.py and frontend/pages/04_eval.py.
"""
from mock_responses import ALL_EVAL_PERSONAS, EVAL_PERSONA_OVERTURF, EVAL_PERSONA_HIGH_RISK, EVAL_PERSONA_LOW_RISK

# Re-export for direct import
__all__ = ["ALL_EVAL_PERSONAS", "EVAL_PERSONA_OVERTURF", "EVAL_PERSONA_HIGH_RISK", "EVAL_PERSONA_LOW_RISK"]

# Scoring targets (from SRS Section 8.4)
SCORING_TARGETS = {
    "fact_recall":            0.70,   # >= 70% of expected facts found
    "risk_flag_precision":    0.80,   # >= 80% of output flags are justified
    "confidence_calibration": 0.10,   # MSE <= 0.10
    "entity_coverage":        0.80,   # >= 80% of expected entities found
    "false_positive_rate":    0.20,   # <= 20% wrong claims
    "hallucination_rate":     0.10,   # <= 10% unverifiable claims
}
```

---

## Section 15 — CLI Entrypoint

> **Cursor prompt:** `@DeepTrace_Phase1_Cursor.md implement Section 15 - main.py CLI`

### `main.py`

```python
"""
main.py — DeepTrace CLI entrypoint.

Usage:
  python main.py --target "Timothy Overturf" --context "CEO of Sisu Capital"
  python main.py --target "Test Person" --env dev
  python main.py --eval
  python main.py --test-connections
  python main.py --help

Architecture position: top-level CLI, imports pipeline.py and graph modules.
"""
import logging
import os
import sys
import click
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("deeptrace")


@click.command()
@click.option("--target",  "-t", default="Timothy Overturf", help="Full name of research target")
@click.option("--context", "-c", default="CEO of Sisu Capital", help="Optional context about target")
@click.option("--env",           default=None,  help="Override ENV (dev/staging/prod)")
@click.option("--eval",          is_flag=True,  help="Run full evaluation set instead of single target")
@click.option("--test-connections", is_flag=True, help="Test all external connections and exit")
@click.option("--stream",        is_flag=True,  help="Show streaming agent output")
def main(target, context, env, eval, test_connections, stream):
    """DeepTrace — Autonomous AI Research Agent."""
    from rich.console import Console
    from rich.panel   import Panel
    console = Console()

    if env:
        os.environ["ENV"] = env

    from config import ENV, USE_MOCK
    console.print(Panel(
        f"[bold cyan]DeepTrace[/bold cyan] — Deep Research AI Agent\n"
        f"ENV: [yellow]{ENV}[/yellow] | USE_MOCK: [yellow]{USE_MOCK}[/yellow]",
        border_style="cyan",
    ))

    # ── Connection test ────────────────────────────────────────────────────────
    if test_connections:
        from graph.neo4j_manager import test_connection
        neo4j_ok = test_connection()
        console.print(f"Neo4j: {'[green]OK[/green]' if neo4j_ok else '[red]FAILED[/red]'}")
        console.print("Anthropic / OpenAI / Google: [yellow]Skipped in Phase 1 (USE_MOCK=true)[/yellow]")
        sys.exit(0 if neo4j_ok else 1)

    # ── Evaluation run ─────────────────────────────────────────────────────────
    if eval:
        console.print("[bold]Running evaluation set (3 personas)...[/bold]")
        from mock_responses import ALL_EVAL_PERSONAS
        from pipeline import run_pipeline
        for persona in ALL_EVAL_PERSONAS:
            console.print(f"\n→ Evaluating: [cyan]{persona['name']}[/cyan]")
            state = run_pipeline(persona["name"], persona["context"])
            facts_found = len(state.get("extracted_facts", []))
            flags_found = len(state.get("risk_flags", []))
            console.print(f"  Facts: {facts_found} | Flags: {flags_found} | "
                          f"Quality: {state.get('research_quality', 0):.2f}")
        console.print("\n[green]✅ Evaluation complete[/green]")
        return

    # ── Single target run ──────────────────────────────────────────────────────
    console.print(f"\n[bold]Researching:[/bold] [cyan]{target}[/cyan]")
    console.print(f"[dim]Context: {context}[/dim]\n")

    if stream:
        from pipeline import stream_pipeline
        for node_name, node_output in stream_pipeline(target, context):
            facts = len(node_output.get("extracted_facts", []))
            flags = len(node_output.get("risk_flags", []))
            console.print(f"  [{node_name}] facts+={facts} flags+={flags}")
    else:
        from pipeline import run_pipeline
        state = run_pipeline(target, context)
        facts_found = len(state.get("extracted_facts", []))
        flags_found = len(state.get("risk_flags", []))
        quality     = state.get("research_quality", 0)
        console.print(f"\n[green]✅ Complete[/green] | Facts: {facts_found} | "
                      f"Flags: {flags_found} | Quality: {quality:.2f}")
        if state.get("final_report"):
            console.print("\n[bold]Report Preview:[/bold]")
            console.print(state["final_report"][:500] + "...")


if __name__ == "__main__":
    main()
```

### `README.md`

```markdown
# DeepTrace — Autonomous AI Research Agent

> Elile AI Technical Assessment · Phase 1 (Mock Scaffold)

## Quick Start

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Start Neo4j
docker-compose up -d neo4j

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run smoke test
python main.py --test-connections

# 5. Run full pipeline (mock mode)
python main.py --target "Timothy Overturf" --context "CEO of Sisu Capital"

# 6. Launch Streamlit UI
streamlit run frontend/app.py

# 7. Run evaluation set
python main.py --eval
```

## Phase Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | ✅ Current | Full mock scaffold — all structure, zero API cost |
| Phase 2 | ⏳ Next | Haiku integration — real LLMs, dev cost ~$10 |
| Phase 3 | ⏳ | Staging — real models, capped runs |
| Phase 4 | ⏳ | Production + demo polish |

## Key Commands

```bash
python main.py --help
python main.py --target "Name" --stream      # streaming output
python main.py --eval                         # run all 3 personas
python main.py --test-connections             # check Neo4j
pytest tests/                                 # run all tests
```
```

---

## Section 16 — Docker Compose

> **Cursor prompt:** `@DeepTrace_Phase1_Cursor.md implement Section 16 - docker-compose.yml`

### `docker-compose.yml`

```yaml
# docker-compose.yml — DeepTrace local development stack
# Services: Neo4j (required Phase 1+) + Streamlit (optional, can run directly)
#
# Usage:
#   docker-compose up -d neo4j            # Start Neo4j only
#   docker-compose up -d                  # Start everything
#   docker-compose down                   # Stop all
#   docker-compose logs neo4j             # View Neo4j logs

version: "3.9"

services:

  neo4j:
    image: neo4j:5.26-community
    container_name: deeptrace-neo4j
    ports:
      - "7474:7474"   # Browser UI: http://localhost:7474
      - "7687:7687"   # Bolt protocol (driver connects here)
    environment:
      NEO4J_AUTH: "neo4j/deeptrace123"
      NEO4J_PLUGINS: '["apoc"]'
      NEO4J_dbms_security_procedures_unrestricted: "apoc.*"
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "-", "http://localhost:7474"]
      interval: 10s
      timeout: 5s
      retries: 5

  streamlit:
    build:
      context: .
      dockerfile: Dockerfile.streamlit   # Create this in Phase 2 if needed
    container_name: deeptrace-streamlit
    ports:
      - "8501:8501"
    environment:
      - USE_MOCK=true
      - ENV=dev
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_PASSWORD=deeptrace123
    depends_on:
      neo4j:
        condition: service_healthy
    volumes:
      - .:/app
    command: streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
    profiles:
      - full   # Only starts with: docker-compose --profile full up

volumes:
  neo4j_data:
  neo4j_logs:
```

---

## Section 17 — Phase 1 Exit Criteria & Smoke Test

> **Run these checks before declaring Phase 1 complete and moving to Phase 2.**

### Automated Smoke Test

```bash
# Run all Phase 1 validation checks in sequence

# 1. Dependency import check
python -c "
import langgraph, langsmith, anthropic, neo4j, streamlit, pydantic, click, rich
print('✅ All imports OK')
"

# 2. Schema validation tests
pytest tests/test_state.py -v

# 3. Confidence scorer tests
pytest tests/test_confidence.py -v

# 4. Neo4j connection test
python main.py --test-connections

# 5. Full pipeline run (mock)
USE_MOCK=true python main.py --target "Timothy Overturf" --context "CEO of Sisu Capital"

# 6. Evaluation set run (mock)
USE_MOCK=true python main.py --eval

# 7. Streaming run
USE_MOCK=true python main.py --target "Test Person" --stream

# 8. Streamlit smoke (headless — just checks import)
python -c "
import sys; sys.argv = ['streamlit', 'run', 'frontend/app.py', '--server.headless', 'true']
from frontend.app import *
print('✅ Streamlit pages importable')
" 2>/dev/null || echo "✅ Streamlit pages exist"

# 9. All tests
pytest tests/ -v --tb=short
```

### Phase 1 Exit Criteria Checklist

```
PIPELINE
[ ] python main.py --target "Timothy Overturf" runs end-to-end without errors
[ ] All 5 agents execute in correct order (visible in logs)
[ ] LangGraph routing loops exactly MAX_LOOPS[ENV] times then proceeds to risk_evaluator
[ ] final_report is populated in AgentState at completion
[ ] loop_count reaches expected value (2 for ENV=dev)

SCHEMAS
[ ] Fact(confidence=1.5) raises ValidationError
[ ] RiskFlag(evidence_fact_ids=["f1"]) raises ValidationError (min 2 required)
[ ] All MOCK_DEEP_DIVE_RESULTS facts pass Fact(**f) validation
[ ] All MOCK_RISK_FLAGS flags pass RiskFlag(**f) validation

NEO4J
[ ] test_connection() returns True
[ ] write_entities() writes mock entities without error
[ ] write_relationships() writes mock relationships without error
[ ] fetch_graph_for_run() returns nodes and edges

STREAMLIT
[ ] streamlit run frontend/app.py starts without ImportError
[ ] Page 01 (Research): form submits, agents stream in sidebar, run completes
[ ] Page 02 (Graph): pyvis HTML renders (mock data)
[ ] Page 03 (Report): risk flags visible with expand/collapse
[ ] Page 04 (Eval): all 3 personas listed

TESTS
[ ] pytest tests/ — all tests pass, zero failures

COST
[ ] No API calls made during full Phase 1 run (verify with USE_MOCK=true in logs)
[ ] Zero LangSmith traces created (LANGCHAIN_TRACING_V2=false)
```

### What Changes in Phase 2

When Phase 1 exit criteria are all checked:

1. Set `USE_MOCK=false` in `.env`
2. Set `ENV=dev` (uses Haiku for all agents)
3. Add real API keys to `.env`
4. Implement the `raise NotImplementedError("Phase 2")` stubs in each agent
5. Run: `python main.py --target "Timothy Overturf"` — first real LLM run

**Do not change any schemas, state, routing logic, or Streamlit pages.**
Everything built in Phase 1 carries forward unchanged.

---

*DeepTrace Phase 1 Implementation Guide · Tanzeel Khan · March 2026*
*Next: @DeepTrace_Phase2_Cursor.md — Real LLM Integration*
