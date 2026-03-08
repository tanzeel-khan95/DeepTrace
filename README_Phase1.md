# DeepTrace Phase 1 — Architecture

This document describes the **complete architecture** on which Phase 1 (mock scaffold) is built. It is the single reference for how components fit together, how data flows, and what is real vs mocked.

---

## 1. High-Level Architecture

Phase 1 is a **multi-agent research pipeline** orchestrated by **LangGraph**. One shared **AgentState** flows through a directed graph of **five agents**. The **Supervisor** decides whether to loop (more research) or proceed to risk evaluation and report generation. All LLM and external API calls are **mocked**; only **Neo4j** is a real external service.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DeepTrace Phase 1 Architecture                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│   ┌──────────────┐     ┌─────────────┐     ┌─────────────┐     ┌──────────────┐  │
│   │   CLI / UI   │────▶│  pipeline   │────▶│  LangGraph  │────▶│  AgentState  │  │
│   │ main.py      │     │ pipeline.py │     │ StateGraph  │     │ (shared)     │  │
│   │ Streamlit    │     │             │     │             │     │              │  │
│   └──────────────┘     └─────────────┘     └──────┬──────┘     └──────────────┘  │
│                                                     │                             │
│         ┌───────────────────────────────────────────┼───────────────────────────┐  │
│         │              Agent nodes (all USE_MOCK)  │                           │  │
│         ▼                                           ▼                           │  │
│   supervisor_plan → scout_agent → deep_dive → supervisor_reflect                 │  │
│         ▲                    │                          │                       │  │
│         │                    │              ┌──────────┴──────────┐            │  │
│         │                    │              │ supervisor_route()  │            │  │
│         └────────────────────┘              │ "scout" | "risk"    │            │  │
│              (loop back)                    └──────────┬──────────┘            │  │
│                                                        │                        │  │
│                                              risk_evaluator → graph_builder     │  │
│                                                        │                        │  │
│                                              supervisor_synth → END             │  │
│         └───────────────────────────────────────────────────────────────────────┘  │
│                                                                                   │
│   External (Phase 1):  Neo4j (real)   │   LLMs, Tavily, Brave, Scraper (mocked)  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Directory and Module Layout

```
DeepTrace/
├── agents/                    # Five LangGraph node implementations
│   ├── supervisor.py          # Plan, reflect, synthesise, route
│   ├── scout_agent.py         # Parallel search (Tavily/Brave)
│   ├── deep_dive_agent.py     # Fact/entity extraction
│   ├── risk_evaluator.py      # RiskFlag generation
│   └── graph_builder.py       # Neo4j write + pyvis HTML
├── graph/                     # Neo4j and visualisation
│   ├── schema.py              # Cypher constraints, MERGE helpers
│   ├── neo4j_manager.py       # Driver, schema, read/write
│   └── visualizer.py          # vis.js HTML for Streamlit
├── search/                    # Search and fetch (mocked in Phase 1)
│   ├── tavily_search.py       # Primary search
│   ├── brave_search.py        # Fallback search
│   └── scraper.py             # Full-page fetch (Phase 2+)
├── evaluation/                # Confidence and eval
│   ├── confidence_scorer.py   # 3-layer fact confidence
│   ├── eval_set.py            # Eval personas and targets
│   └── langsmith_eval.py      # Stub (Phase 3)
├── prompts/                   # System prompts (used in Phase 2+)
│   ├── supervisor_prompt.py
│   ├── scout_prompt.py
│   ├── deep_dive_prompt.py
│   ├── risk_prompt.py
│   └── graph_prompt.py
├── state/
│   └── agent_state.py         # Pydantic models + AgentState TypedDict
├── utils/
│   ├── budget_guard.py        # Spend cap (Phase 2+)
│   └── llm_cache.py           # Stub (Phase 3)
├── frontend/
│   ├── app.py                 # Streamlit entry, theme
│   └── pages/
│       ├── 01_research.py     # Target input, stream pipeline
│       ├── 02_graph.py        # Identity graph (pyvis)
│       ├── 03_report.py      # Risk report + facts
│       └── 04_eval.py         # Eval dashboard (3 personas)
├── tests/
│   ├── test_state.py          # Pydantic schema tests
│   ├── test_confidence.py     # Confidence scorer tests
│   └── test_agents.py         # Supervisor mock tests
├── config.py                  # ENV, USE_MOCK, Neo4j, models, etc.
├── mock_responses.py          # All Phase 1 fixture data
├── pipeline.py                # LangGraph build, run_pipeline, stream_pipeline
├── main.py                    # CLI entry (click)
├── docker-compose.yml         # Neo4j (+ optional Streamlit)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 3. Data Architecture

### 3.1 AgentState (LangGraph state)

Single **TypedDict** shared by every node. LangGraph merges each node’s **returned dict** into this state. Fields with `Annotated[..., operator.add]` **accumulate** across steps (e.g. multiple agents appending facts); others are overwritten.

| Field | Type | Reducer | Role |
|-------|------|---------|------|
| `target_name` | str | — | Research subject (e.g. "Timothy Overturf") |
| `target_context` | Optional[str] | — | Optional context (e.g. "CEO of Sisu Capital") |
| `research_plan` | List[str] | add | Queries to run this loop |
| `queries_issued` | List[str] | add | Queries already executed |
| `gaps_remaining` | List[str] | — | Open gaps (from Supervisor) |
| `raw_results` | List[dict] | add | Raw search hits (url, title, content, relevance) |
| `extracted_facts` | List[Fact] | add | Validated facts from Deep Dive |
| `entities` | List[Entity] | add | People, orgs, funds, etc. |
| `relationships` | List[Relationship] | add | Directed edges (e.g. FOUNDED, WORKS_AT) |
| `risk_flags` | List[RiskFlag] | add | Risk signals with evidence |
| `graph_populated` | bool | — | True after Graph Builder runs |
| `confidence_map` | Dict[str, float] | — | fact_id → final confidence |
| `research_quality` | float | — | 0.0–1.0 (Supervisor) |
| `loop_count` | int | — | Current loop index |
| `final_report` | Optional[str] | — | Markdown report (Supervisor) |
| `run_id` | str | — | UUID for the run (Neo4j isolation) |

Initial state is built by **`make_initial_state(target_name, target_context)`** in `state/agent_state.py`.

### 3.2 Pydantic models (state/agent_state.py)

All structured data is validated via Pydantic:

- **Fact** — claim, source_url, source_domain, confidence (0–1), category, entities_mentioned, supporting_fact_ids, raw_source_snippet.
- **Entity** — entity_id, name, entity_type (Person | Organization | Fund | Location | Event | Filing), attributes, confidence, source_fact_ids.
- **Relationship** — from_id, to_id, rel_type (e.g. WORKS_AT, FOUNDED, INVESTED_IN), attributes, confidence, source_fact_id.
- **RiskFlag** — flag_id, title, description, severity (CRITICAL | HIGH | MEDIUM | LOW), evidence_fact_ids (min 2), confidence, category.
- **SearchResult** — url, title, content, relevance (0–1), source_domain.

Confidence and relevance are clamped/validated; RiskFlag enforces at least two evidence fact_ids.

---

## 4. Pipeline (LangGraph) Flow

### 4.1 Graph definition (pipeline.py)

- **State schema:** `AgentState`.
- **Nodes:**  
  `supervisor_plan` → `scout_agent` → `deep_dive` → `supervisor_reflect` → [conditional] → `risk_evaluator` → `graph_builder` → `supervisor_synth` → END.

### 4.2 Edges

| From | To | Type |
|------|----|------|
| START | supervisor_plan | edge |
| supervisor_plan | scout_agent | edge |
| scout_agent | deep_dive | edge |
| deep_dive | supervisor_reflect | edge |
| supervisor_reflect | * | **conditional** (supervisor_route) |
| — | supervisor_plan | if route returns `"scout_agent"` (loop) |
| — | risk_evaluator | if route returns `"risk_evaluator"` |
| risk_evaluator | graph_builder | edge |
| graph_builder | supervisor_synth | edge |
| supervisor_synth | END | edge |

### 4.3 Routing (supervisor_route)

- **Go to risk_evaluator** if `loop_count >= MAX_LOOPS[ENV]` or `research_quality >= QUALITY_THRESHOLD` (0.80).
- **Else** return `"scout_agent"` → next node is **supervisor_plan** (re-plan and run another loop).

So in Phase 1 (dev, MAX_LOOPS=2) the loop runs at most twice, then always goes to risk_evaluator → graph_builder → supervisor_synth → END.

---

## 5. Agent Responsibilities

| Agent | Node name(s) | Phase 1 behaviour | Phase 2+ |
|-------|--------------|-------------------|----------|
| **Supervisor** | supervisor_plan, supervisor_reflect, supervisor_synth | Returns mock research_plan, gaps, quality, final_report; route uses state only | Claude Opus 4.5 for plan/reflect/synth |
| **Scout** | scout_agent | Returns MOCK_SCOUT_RESULTS (raw_results, queries_issued) | Tavily + Brave, async |
| **Deep Dive** | deep_dive | Returns MOCK_DEEP_DIVE_RESULTS; validates Fact/Entity/Relationship; runs confidence_scorer | Gemini 2.5 Pro + scraper |
| **Risk Evaluator** | risk_evaluator | Returns MOCK_RISK_FLAGS; filters by confidence_map | Claude Sonnet 4.6 |
| **Graph Builder** | graph_builder | setup_schema(); write_entities/write_relationships to Neo4j (real); generate_pyvis_html | Same Neo4j + optional enhancements |

Every agent uses **`if USE_MOCK: ... else: ...`**; LLM/API imports live only in the `else` branch.

---

## 6. Confidence Scoring (evaluation/confidence_scorer.py)

Three-layer model for **fact confidence**:

- **Layer 1 — Domain trust:** Lookup by source domain (e.g. sec.gov 0.92, _default 0.40).
- **Layer 2 — Cross-reference:** Adjust by supporting/contradicting source counts (multipliers for single/two/three+ sources and contradictions).
- **Layer 3 — Faithfulness:** Phase 1 stub returns 0.75; Phase 2+ will use an LLM check.

**Final:** `(L1 × 0.30) + (L2 × 0.40) + (L3 × 0.30)`, capped at 0.95.  
**`score_facts_batch(facts)`** produces the **confidence_map** used by the Risk Evaluator and state.

---

## 7. Graph Layer (Neo4j + Visualisation)

- **schema.py** — Defines Cypher constraints (e.g. unique entity_id per label) and helpers: **entity_to_cypher_merge**, **relationship_to_cypher_merge**.
- **neo4j_manager.py** — Singleton driver, **test_connection()**, **setup_schema()**, **write_entities(entities, run_id)**, **write_relationships(relationships)**, **fetch_graph_for_run(run_id)**, **clear_graph(run_id)**. Nodes store **run_id** for per-run isolation.
- **visualizer.py** — **generate_pyvis_html(nodes, edges)** builds self-contained HTML (vis.js) for the Streamlit graph page; node colours by entity type (Person, Organization, Fund, etc.).

In Phase 1, **only Neo4j** is a real external dependency; all data written to it comes from mock-backed agents.

---

## 8. Configuration (config.py)

- **ENV** — `dev` | `staging` | `prod` (drives MAX_LOOPS, MAX_TOKENS, MODEL_CONFIG, PHASE_BUDGET).
- **USE_MOCK** — `true` in Phase 1; when `false`, agents call real LLMs/APIs.
- **LANGCHAIN_TRACING** — From LANGCHAIN_TRACING_V2 (off in Phase 1).
- **MAX_LOOPS** — dev 2, staging 3, prod 5.
- **QUALITY_THRESHOLD** — 0.80 (stop loop when research_quality ≥ this).
- **MODEL_CONFIG** — Per-env model names for each agent (used in Phase 2+).
- **Neo4j** — NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE.
- **Search** — TAVILY_API_KEY, BRAVE_SEARCH_API_KEY, MIN_RELEVANCE.

---

## 9. Mock Boundary (Phase 1 vs Phase 2+)

| Component | Phase 1 | Phase 2+ |
|-----------|--------|----------|
| Supervisor plan/reflect/synth | mock_responses (MOCK_SUPERVISOR_LOOP_1/2, MOCK_SUPERVISOR_FINAL) | Claude Opus 4.5 |
| Scout | MOCK_SCOUT_RESULTS | Tavily + Brave APIs |
| Deep Dive | MOCK_DEEP_DIVE_RESULTS + Pydantic validate + score_facts_batch | Gemini 2.5 Pro + scraper |
| Risk Evaluator | MOCK_RISK_FLAGS (filtered by confidence) | Claude Sonnet 4.6 |
| Graph Builder | Real Neo4j write + real pyvis HTML | Same |
| Tavily / Brave / scraper | Return static or stub data | Real HTTP |
| LangSmith | Disabled | Optional tracing |

**Rule:** No top-level imports of `anthropic`, `openai`, or `google.generativeai`; they are imported only inside `else` (non-mock) branches.

---

## 10. Entrypoints and Data Flow

- **CLI:** `main.py` — `--target`, `--context`, `--eval`, `--test-connections`, `--stream`. Loads `.env`, uses **run_pipeline** or **stream_pipeline** from `pipeline.py`.
- **Streamlit:** `frontend/app.py` — Multi-page app; **01_research** calls **stream_pipeline** and shows agent deltas; **02_graph** uses Neo4j or mock entities/relationships + **generate_pyvis_html**; **03_report** uses mock (or future state) report and risk flags; **04_eval** lists three eval personas and can run pipeline for each.
- **Tests:** `tests/test_state.py`, `tests/test_confidence.py`, `tests/test_agents.py` — Validate Pydantic behaviour, confidence logic, and Supervisor mock behaviour.

---

## 11. Phase 1 Design Decisions (Summary)

1. **Single shared state** — AgentState TypedDict with reducer annotations for list accumulation.
2. **Pydantic everywhere** — All fact/entity/relationship/risk structures validated at boundaries.
3. **USE_MOCK toggle** — One flag; every agent and search path branches on it; no LLM calls when true.
4. **Neo4j as only real external** — Graph is real; data written is from mock-backed agents.
5. **Supervisor-driven loop** — Loop count and research_quality drive routing; no separate “oracle” node.
6. **Confidence before risk** — confidence_map is filled by Deep Dive (via confidence_scorer); Risk Evaluator uses it to filter evidence.
7. **Stubs for Phase 2+** — Non-mock branches raise `NotImplementedError("Phase 2")` or equivalent where real implementation is deferred.

This architecture is the foundation for Phase 2 (real LLMs and APIs) without changing state shape, pipeline topology, or Neo4j integration.
