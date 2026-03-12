# DeepTrace — Architecture

> Multi-Agent Due Diligence & Risk Intelligence Platform  
> LangGraph | Claude | GPT-4.1 | Neo4j | Streamlit

For component details, design rationale, and optimization levers, see [documentation.md](documentation.md).

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              FRONTEND (Streamlit)                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  ┌──────────────┐                                   │
│  │  01_Research  │  │   02_Graph   │  │    03_Report     │  │   04_Eval    │                                   │
│  │  Target Input │  │  D3 Force    │  │  Risk Report +   │  │  Persona     │                                   │
│  │  + Streaming  │  │  Graph View  │  │  PDF Export      │  │  Dashboard   │                                   │
│  └──────┬───────┘  └──────────────┘  └──────────────────┘  └──────────────┘                                   │
│         │                                                                                                      │
│         ▼ stream_pipeline()                                                                                    │
└─────────┬──────────────────────────────────────────────────────────────────────────────────────────────────────┘
          │
┌─────────▼──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      ORCHESTRATION LAYER (LangGraph StateGraph)                                │
│                                                                                                                │
│  AgentState (TypedDict + Pydantic models) — shared across all nodes via operator.add reducers                  │
│                                                                                                                │
│  ┌──────────────────────────────────────────── RESEARCH LOOP ──────────────────────────────────────────────┐   │
│  │                                                                                                         │   │
│  │   START ──▶ ┌────────────────────┐    ┌───────────────┐    ┌──────────────┐    ┌────────────────────┐   │   │
│  │             │  SUPERVISOR::PLAN  │───▶│  SCOUT AGENT  │───▶│  DEEP DIVE   │───▶│SUPERVISOR::REFLECT │   │   │
│  │             │  (Query Strategy)  │    │  (Parallel    │    │  (Fact/Entity │    │  (Quality Score +  │   │   │
│  │             │                    │    │   Search)     │    │   Extraction) │    │   Gap Analysis)    │   │   │
│  │             └────────────────────┘    └───────────────┘    └──────────────┘    └─────────┬──────────┘   │   │
│  │                      ▲                                                                   │              │   │
│  │                      │                          SUPERVISOR::ROUTE                        │              │   │
│  │                      │                    ┌──────────────────────────┐                   │              │   │
│  │                      │                    │  quality < threshold     │                   │              │   │
│  │                      └────────────────────│  AND loop < max_loops?  │◀──────────────────┘              │   │
│  │                         YES (loop back)   │                          │                                  │   │
│  │                                           └──────────┬───────────────┘                                  │   │
│  └──────────────────────────────────────────────────────┼──────────────────────────────────────────────────┘   │
│                                                         │ NO (converged or max loops)                          │
│                                                         ▼                                                      │
│  ┌────────────────────────────────────────── FINALIZATION PHASE ───────────────────────────────────────────┐   │
│  │                                                                                                         │   │
│  │   ┌──────────────────┐    ┌───────────────────┐    ┌──────────────────────┐                             │   │
│  │   │  RISK EVALUATOR  │───▶│  GRAPH BUILDER    │───▶│ SUPERVISOR::SYNTH    │───▶ END                    │   │
│  │   │  (Risk Flags +   │    │  (Entity Canon +  │    │ (Final Intelligence  │                             │   │
│  │   │   Severity)      │    │   Neo4j + D3 HTML)│    │  Report Markdown)    │                             │   │
│  │   └──────────────────┘    └───────────────────┘    └──────────────────────┘                             │   │
│  │                                                                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                                                │
│  SqliteSaver Checkpointer ◀──── checkpoint after every node (thread_id = run_id)                               │
│                                                                                                                │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
          │                           │                           │
          ▼                           ▼                           ▼
┌──────────────────┐   ┌──────────────────────┐   ┌──────────────────────────┐
│  SEARCH LAYER    │   │  LLM PROVIDER LAYER  │   │  PERSISTENCE LAYER       │
│                  │   │                      │   │                          │
│  • Tavily API   │   │  • Anthropic Claude  │   │  • Neo4j (Graph DB)      │
│    (primary)    │   │    (Haiku / Opus)    │   │  • SQLite (Checkpoints)  │
│  • Haiku Web    │   │  • OpenAI GPT-4.1    │   │  • .audit_logs/ (JSONL)  │
│    Search       │   │  • Groq (Llama 3.3)  │   │  • .graph_artifacts/     │
│    (fallback)   │   │  • Gemini 2.5 Pro    │   │    (D3 HTML)             │
│                  │   │                      │   │  • .llm_cache/ (disk)    │
└──────────────────┘   └──────────────────────┘   └──────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     CROSS-CUTTING INFRASTRUCTURE                                               │
│                                                                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌────────────────┐  ┌────────────┐ │
│  │ Token Bucket │  │ Budget Guard │  │  LLM Cache    │  │ Audit Logger │  │ LangSmith      │  │ Confidence │ │
│  │ Rate Limiter │  │ (per-env $)  │  │  (disk-based) │  │ (JSONL per   │  │ Tracing        │  │ Scorer     │ │
│  │ (per-provider│  │              │  │               │  │  run)        │  │ (@traceable)   │  │ (3-layer)  │ │
│  │  buckets)    │  │              │  │               │  │              │  │                │  │            │ │
│  └──────────────┘  └──────────────┘  └───────────────┘  └──────────────┘  └────────────────┘  └────────────┘ │
│                                                                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐                                                        │
│  │ Retry +      │  │ Entity       │  │  Citation     │                                                        │
│  │ Backoff +    │  │ Canonicaliz. │  │  Builder      │                                                        │
│  │ Jitter       │  │ (difflib)    │  │               │                                                        │
│  └──────────────┘  └──────────────┘  └───────────────┘                                                        │
│                                                                                                                │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
User Input ("Timothy Overturf, hedge fund manager")
         │
         ▼
  ┌── Supervisor::Plan ──┐
  │  Generates 5-8 targeted research queries                  │
  └───────────┬───────────┘
              ▼
  ┌── Scout Agent ──┐
  │  Parallel Tavily + Haiku fallback search                  │
  │  → 15-25 raw results (deduplicated, relevance-filtered)   │
  └───────────┬─────┘
              ▼
  ┌── Deep Dive ──┐
  │  LLM extraction from top 8 results:                       │
  │  → Facts + Entities + Relationships                       │
  │  → 3-layer confidence scoring + citation building         │
  └───────────┬───┘
              ▼
  ┌── Supervisor::Reflect ──┐
  │  Quality score + gap identification                       │
  └───────────┬─────────────┘
              ▼
  ┌── Route ──┐
  │  quality < 0.70 AND loop < max? → LOOP back to Plan      │
  │  otherwise → FINALIZE                                     │
  └─────┬─────┘
        ▼
  ┌── Risk Evaluator ──┐
  │  Risk flags with severity (each backed by ≥2 facts)       │
  └───────────┬────────┘
              ▼
  ┌── Graph Builder ──┐
  │  Entity canonicalization → Neo4j write → D3 HTML          │
  └───────────┬───────┘
              ▼
  ┌── Supervisor::Synthesise ──┐
  │  Final markdown intelligence report                       │
  └───────────┬────────────────┘
              ▼
         Final State
  (Report + Graph + Risk Flags + Facts + Citations)
```

---

## File Map

```
DeepTrace/
├── main.py                          # CLI entry (Click)
├── pipeline.py                      # LangGraph StateGraph + run/stream/resume
├── config.py                        # Env-aware configuration
├── mock_responses.py                # Fixture data (USE_MOCK=true)
│
├── agents/
│   ├── supervisor.py                # Plan, Reflect, Synthesise, Route
│   ├── scout_agent.py               # Parallel search
│   ├── deep_dive_agent.py           # Fact/Entity/Relationship extraction
│   ├── risk_evaluator.py            # Risk flag generation
│   └── graph_builder.py             # Entity canon + Neo4j + D3
│
├── state/
│   ├── agent_state.py               # AgentState TypedDict + Pydantic models
│   └── llm_schemas.py               # Structured output schemas
│
├── prompts/                         # System prompts per agent
├── search/                          # Tavily, Haiku web search, scraper
├── graph/                           # Neo4j manager, D3 visualizer, Cypher schema
├── utils/                           # LLM clients, cache, retry, budget, audit, tracing
├── evaluation/                      # Personas, confidence scorer, LangSmith eval
├── frontend/                        # Streamlit app (4 pages)
└── tests/                           # pytest suite
```
