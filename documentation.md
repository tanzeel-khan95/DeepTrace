# DeepTrace — Documentation

> For architecture diagrams and file map, see [architecture.md](architecture.md).

---

## Table of Contents

- [1. How It Works](#1-how-it-works)
- [2. Orchestration — LangGraph Pipeline](#2-orchestration--langgraph-pipeline)
- [3. Shared State — AgentState](#3-shared-state--agentstate)
- [4. Supervisor Agent](#4-supervisor-agent)
- [5. Scout Agent](#5-scout-agent)
- [6. Deep Dive Agent](#6-deep-dive-agent)
- [7. Risk Evaluator](#7-risk-evaluator)
- [8. Graph Builder](#8-graph-builder)
- [9. Confidence Scorer](#9-confidence-scorer)
- [10. Infrastructure](#10-infrastructure)
- [11. Frontend](#11-frontend)
- [12. Evaluation Framework](#12-evaluation-framework)
- [13. Configuration](#13-configuration)
- [14. Technology Decisions](#14-technology-decisions)
- [15. Optimization Levers](#15-optimization-levers)

---

## 1. How It Works

DeepTrace takes a target name (e.g. "Timothy Overturf, hedge fund manager"), runs iterative research loops until it has enough coverage, then produces a risk intelligence report backed by an entity knowledge graph.

Two phases:
- **Research Loop** — `plan → search → extract → reflect → [loop or exit]` — repeats until quality hits 0.70 or the loop cap is reached.
- **Finalization** — `risk evaluation → graph construction → report synthesis → END` — runs once.

The system self-corrects: if loop 1 misses financial data, the reflect step flags the gap and the next plan generates queries targeting it specifically.

---

## 2. Orchestration — LangGraph Pipeline

**`pipeline.py`**

LangGraph was chosen over CrewAI/AutoGen/raw LangChain for three reasons: deterministic graph execution (no hidden prompt-chaining), built-in SqliteSaver checkpointing (crash recovery without re-burning tokens), and native streaming (`graph.stream()` yields `(node_name, state_delta)` for real-time frontend updates).

Routing is **deterministic Python**, not an LLM call. `supervisor_route` checks `quality < threshold AND loop < max_loops` — predictable, auditable, cheap. Each run gets its own checkpoint namespace via `thread_id = run_id`, making every run independently resumable.

**Improvement path:** Parallelize the finalization phase (risk eval and graph building are independent). Add category-weighted quality routing instead of a single scalar threshold.

---

## 3. Shared State — AgentState

**`state/agent_state.py`**

A `TypedDict` with `operator.add` reducers on list fields (`extracted_facts`, `entities`, `relationships`, `risk_flags`, `citations`). Agents append to state — they never overwrite each other.

Pydantic models enforce boundaries: confidence clamped to `[0.0, 1.0]`, `RiskFlag` requires minimum 2 evidence facts, entity/relationship types restricted to closed sets. This is the contract that prevents hallucination from leaking across agent boundaries.

**Improvement path:** Version the `confidence_map` per loop for drift detection. Add a `contradictions` field to track conflicting facts.

---

## 4. Supervisor Agent

**`agents/supervisor.py`** | **`prompts/supervisor_prompt.py`**

Three LangGraph nodes + one pure Python router:

| Node | What it does | Output |
|------|-------------|--------|
| `supervisor_plan` | Generates research queries adapted to current gaps and findings | `SupervisorPlanResponse` (structured) |
| `supervisor_reflect` | Scores quality 0.0-1.0, identifies remaining gaps | `SupervisorReflectResponse` (structured) |
| `supervisor_synthesise` | Writes the final markdown intelligence report | Free-form text |
| `supervisor_route` | `quality < 0.70 AND loop < max → loop`, else finalize | No LLM (deterministic) |

The plan step reads prior facts + risk signals and adapts query strategy each loop. A programmatic guardrail strips queries already issued in previous loops to prevent redundant search.

**Improvement path:** Per-category quality scores in state so routing can target specific gaps (e.g. "only loop on financial coverage").

---

## 5. Scout Agent

**`agents/scout_agent.py`**

Fires all queries in parallel via `asyncio.gather()`. Primary: **Tavily Search API**. Fallback: **Haiku Web Search** — triggered only when Tavily returns ≤2 results or average relevance drops below 0.5. Results are URL-deduplicated across the batch, relevance-filtered (≥0.55), and capped at `MAX_SEARCH_RESULTS_PER_QUERY × num_queries`.

Dual sources exist because Tavily has blind spots on niche financial entities. The conditional fallback means we only pay for Haiku when the primary is genuinely insufficient.

**Improvement path:** Wire up Brave Search (config key exists). Cache source content across runs. Adaptive query count based on category coverage.

---

## 6. Deep Dive Agent

**`agents/deep_dive_agent.py`** | **`prompts/deep_dive_prompt.py`**

Takes the top 8 results (ranked by `relevance + domain_trust_boost`) and extracts structured `Fact`, `Entity`, and `Relationship` objects via LLM structured output. Routes to the correct provider SDK based on model config:

| Provider | Models | Used for |
|----------|--------|----------|
| OpenAI | `gpt-4.1-mini` | Default extraction (cheapest reliable structured output) |
| Anthropic | Claude Haiku/Opus | Supervisor, risk eval |
| Groq | `llama-3.3-70b-versatile` | Available as extraction alternative |
| Gemini | `gemini-2.5-pro` | Available as extraction alternative |

Post-extraction: duplicate facts are merged, 3-layer confidence scores are computed, and citations are built linking facts back to source URLs.

**Improvement path:** Chunked extraction for long content. Implement LLM faithfulness verification (L3 of confidence scorer). Increase source truncation from 600 chars with token budget awareness.

---

## 7. Risk Evaluator

**`agents/risk_evaluator.py`** | **`prompts/risk_prompt.py`**

Runs once after loop convergence. Produces `RiskFlag` objects from accumulated facts with severity levels: CRITICAL (illegal/sanctions), HIGH (material financial risk), MEDIUM (conflicts/omissions), LOW (minor inconsistencies).

Hard constraints: only facts with confidence ≥0.40 are eligible as evidence, and every flag must cite ≥2 evidence facts (Pydantic-enforced). This trades recall for precision — we'd rather miss a LOW flag than fabricate a HIGH one.

**Improvement path:** Temporal risk weighting (2008 violation ≠ 2024 violation). Cross-entity risk propagation via the graph. Configurable severity thresholds per client.

---

## 8. Graph Builder

**`agents/graph_builder.py`** | **`graph/neo4j_manager.py`** | **`utils/entity_canon.py`**

The only agent with zero LLM calls. Pipeline:
1. **Canonicalize** — `difflib.SequenceMatcher` merges near-duplicates above 0.85 similarity ("Tim Overturf" → "Timothy Overturf"). Merge map remaps all relationship endpoints. Self-loops are dropped.
2. **Neo4j write** — Entities as labeled nodes, relationships as directed edges, all tagged with `run_id`.
3. **D3 HTML** — Self-contained force-directed graph visualization saved to `.graph_artifacts/{run_id}.html`.

Neo4j was chosen over NetworkX-only because it enables cross-run entity queries and ad-hoc Cypher exploration by analysts.

**Improvement path:** Cross-run entity linking. ML-based canonicalization for semantic equivalents ("SEC" ↔ "Securities and Exchange Commission"). Graph-based anomaly detection via Neo4j GDS.

---

## 9. Confidence Scorer

**`evaluation/confidence_scorer.py`**

Three-layer scoring on every extracted fact:

| Layer | Weight | Signal | Cost |
|-------|--------|--------|------|
| L1: Domain Trust | 30% | Lookup table — `sec.gov` → 0.92, `linkedin.com` → 0.60, unknown → 0.40 | Free |
| L2: Cross-Reference | 40% | Supporting/contradicting source counts with multipliers | Free |
| L3: LLM Faithfulness | 30% | Claim-vs-source verification | Stubbed at 0.75 (not yet wired) |

Formula: `(L1 × 0.30) + (L2_adjusted × 0.40) + (L3 × 0.30)`, capped at 0.95.

L2 multipliers: single source → 0.90x penalty, 3+ sources → 1.15x reward, 2+ contradictions → hard cap at 0.30.

L3 is stubbed because the cost (~$0.01-0.05/fact) wasn't justified yet. The infrastructure is ready — it just needs the LLM call wired in.

---

## 10. Infrastructure

All external API calls go through shared infrastructure in `utils/`:

**Rate Limiting** (`retry.py`) — Per-provider `TokenBucket` instances (Anthropic 50/min, OpenAI 30/min, Groq 30/min, Gemini 10/min, Tavily 20/min). Continuous refill, blocks until token available.

**Retry** (`retry.py`) — `@with_retry` decorator with exponential backoff (1s → 2s → 4s) + random jitter (0-0.5s). Catches `RateLimitError`, `APITimeoutError`, `APIConnectionError` across all provider SDKs. Max 3 retries.

**Budget Guard** (`budget_guard.py`) — Per-env spending cap ($10 dev, $25 staging, $999 prod). Every LLM response triggers `record_spend()` with per-model cost estimates. Exceeding the cap raises `RuntimeError` and kills the pipeline.

**LLM Cache** (`llm_cache.py`) — Disk-based, keyed by `(prompt, model, max_tokens)`. Cache hits = zero latency, zero cost. The synthesise step bypasses cache deliberately.

**Audit Logger** (`audit_logger.py`) — JSONL per run_id. Events: `SEARCH_QUERY`, `LLM_CALL`, `LLM_RETRY`, `NODE_START`, `NODE_COMPLETE`, `NODE_FAILURE`, `ENTITY_MERGED`, `RISK_FLAG`. Append-only, grep-friendly.

**LangSmith Tracing** (`tracing.py`) — `@traceable` on every agent function. Token usage, latency breakdown, error traces, run comparison. Conditional on `LANGCHAIN_TRACING_V2=true`. Zero overhead when disabled.

---

## 11. Frontend

**`frontend/`** — Streamlit multi-page app.

| Page | What it does |
|------|-------------|
| `01_research.py` | Target input, streams pipeline node-by-node with real-time timeline |
| `02_graph.py` | Embeds D3 force-directed graph HTML, download link |
| `03_report.py` | Renders markdown report, risk flag badges, PDF export |
| `04_eval.py` | Runs persona-based evals, scoring dashboard |

Session state preserves investigation context across page navigation.

---

## 12. Evaluation Framework

**`evaluation/`**

Four personas testing different failure modes:

| Persona | Tests | Difficulty |
|---------|-------|-----------|
| Satya Nadella | Baseline extraction on high-coverage target | Easy |
| Elizabeth Holmes | Risk flag precision with contradictory sources | Medium |
| Sam Bankman-Fried | Entity graph depth on complex financial networks | Hard |
| Timothy Overturf | Graceful degradation on sparse digital footprint | Hardest |

Scoring targets: fact recall ≥0.70, risk flag precision ≥0.80, entity coverage ≥0.60, confidence calibration ≤0.15 error. Run via `python main.py --eval`.

---

## 13. Configuration

**`config.py`** | **`.env.example`**

`ENV` (`dev`/`staging`/`prod`) controls model selection, loop caps, token limits, and budget:

| | dev | staging | prod |
|---|-----|---------|------|
| Supervisor | Haiku 4.5 | Opus 4.5 | Opus 4.5 |
| Deep Dive | GPT-4.1 Mini | GPT-4.1 Mini | GPT-4.1 Mini |
| Max loops | 5 | 3 | 5 |
| Max tokens | 5000 | 1500 | 3000 |
| Budget | $10 | $25 | $999 |

`USE_MOCK=true` bypasses all API calls with fixture data — essential for onboarding and CI.

---

## 14. Technology Decisions

| Choice | Why | Alternatives Considered |
|--------|-----|------------------------|
| LangGraph | Deterministic graph, checkpointing, streaming | CrewAI, AutoGen, raw LangChain |
| Claude Haiku (supervisor) | Best structured output at cost tier | GPT-4o, Gemini |
| GPT-4.1 Mini (extraction) | Cheapest reliable structured JSON | Haiku, Groq Llama |
| Tavily + Haiku fallback | Native relevance scores + niche coverage | SerpAPI, Brave, Google CSE |
| Neo4j | Cross-run querying, Cypher, persistence | NetworkX-only, ArangoDB |
| SQLite checkpoints | Zero-ops, single-file | PostgreSQL, Redis |
| Streamlit | Fastest multi-page app with streaming | Next.js, Gradio |
| Pydantic structured output | Provider-agnostic schema validation | JSON mode, function calling |

---

## 15. Optimization Levers

**Cost:**
- Swap Deep Dive model to Groq Llama 3.3 (output cost drops ~50%)
- Tighten `MAX_TOKENS` per env (staging already at 1500)
- LLM cache hit rates of 60-80% in repeated eval runs
- Reduce loop cap if quality converges early

**Latency:**
- Parallelize finalization (risk eval + graph builder are independent)
- Haiku for time-sensitive nodes, Opus only where reasoning quality justifies the wait
- Streaming already gives real-time perceived progress

**Tokens:**
- Source truncation at 600 chars — reducible to 400 with modest recall trade-off
- Fact summaries capped at 25 per supervisor call
- Query deduplication prevents redundant extraction
- `merge_duplicate_facts()` before scoring avoids re-processing
