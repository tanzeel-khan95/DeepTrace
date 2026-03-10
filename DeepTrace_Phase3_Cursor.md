# DeepTrace — Phase 3: Production Hardening
> **Cursor Implementation Guide** · Phase 3 of 4
>
> **Prerequisite:** Phase 2 complete. `USE_MOCK=false python main.py --target "Timothy Overturf"`
> runs end-to-end with real Haiku + Tavily. All Phase 2 tests pass.
>
> **Goal:** Transform the working Phase 2 prototype into a production-hardened system with:
> LangSmith tracing · rate limiting + retries · multi-source search (Tavily + Haiku web search) ·
> state checkpointing · systematic fallback logic · extraction coverage across all 4 categories ·
> entity canonicalization + deduplication · run-scoped relationship isolation · graph artifact
> persistence · structured audit logging · source citations with clickable UI links ·
> PDF export · interactive D3.js identity graph visualization · inconsistency detection
>
> **Cost:** ~$0.02–0.05 per run (Haiku, ENV=dev). All new LLM calls use Haiku.
> LangSmith free tier: 5,000 traces/month — sufficient for all development.

---

## Required API Keys for Phase 3

```bash
# ── .env additions for Phase 3 (append to existing Phase 2 .env) ─────────────

# LangSmith (free tier — https://smith.langchain.com)
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_PROJECT=deeptrace-dev       # creates this project on first trace
LANGCHAIN_TRACING_V2=true             # flip from false to true

# Haiku Web Search — uses same ANTHROPIC_API_KEY from Phase 2 (no new key needed)
# Tavily — same TAVILY_API_KEY from Phase 2 (no new key needed)

# Remove or blank out (Brave is removed in Phase 3):
BRAVE_SEARCH_API_KEY=                 # leave blank — Brave code is deleted

# Checkpointing
CHECKPOINT_DB_PATH=.checkpoints/deeptrace.db    # SQLite checkpoint file

# Structured logging
AUDIT_LOG_DIR=.audit_logs             # persistent JSON audit logs per run

# Graph artifacts
GRAPH_ARTIFACT_DIR=.graph_artifacts   # persisted HTML graph files per run

# Phase 3 model config (still Haiku for dev — same key)
# ENV=dev → all agents still use claude-haiku-4-5-20251001
# ENV=staging → supervisor uses claude-sonnet-4-6, others stay Haiku
```

### API Key Summary

| Key | New in Phase 3? | Where to get |
|-----|----------------|--------------|
| `LANGCHAIN_API_KEY` | ✅ Yes | smith.langchain.com → Settings → API Keys |
| `ANTHROPIC_API_KEY` | No — carry over | (already set) |
| `TAVILY_API_KEY` | No — carry over | (already set) |
| `BRAVE_SEARCH_API_KEY` | ❌ Removed | (delete from .env) |

---

## Table of Contents

- [Section 1 — Phase 3 Rules & Architecture](#section-1--phase-3-rules--architecture)
- [Section 2 — Config Updates](#section-2--config-updates)
- [Section 3 — Remove Brave Search](#section-3--remove-brave-search)
- [Section 4 — Rate Limiter + Retry Decorator](#section-4--rate-limiter--retry-decorator)
- [Section 5 — LangSmith Tracing](#section-5--langsmith-tracing)
- [Section 6 — State Checkpointing](#section-6--state-checkpointing)
- [Section 7 — Structured Audit Logger](#section-7--structured-audit-logger)
- [Section 8 — Multi-Source Search (Tavily + Haiku Web Search)](#section-8--multi-source-search-tavily--haiku-web-search)
- [Section 9 — Extraction Coverage (4 Categories as First-Class Outputs)](#section-9--extraction-coverage-4-categories-as-first-class-outputs)
- [Section 10 — Entity Canonicalization + Deduplication](#section-10--entity-canonicalization--deduplication)
- [Section 11 — Inconsistency Detection + Affiliation Heuristics](#section-11--inconsistency-detection--affiliation-heuristics)
- [Section 12 — Run-Scoped Relationship Isolation](#section-12--run-scoped-relationship-isolation)
- [Section 13 — Graph Artifact Persistence](#section-13--graph-artifact-persistence)
- [Section 14 — Source Citations with Evidence Fields](#section-14--source-citations-with-evidence-fields)
- [Section 15 — Systematic Fallback Logic (All Nodes)](#section-15--systematic-fallback-logic-all-nodes)
- [Section 16 — D3.js Interactive Graph Visualization](#section-16--d3js-interactive-graph-visualization)
- [Section 17 — PDF Export](#section-17--pdf-export)
- [Section 18 — Updated Streamlit UI (Citations + Export + Graph)](#section-18--updated-streamlit-ui-citations--export--graph)
- [Section 19 — Phase 3 Tests](#section-19--phase-3-tests)
- [Section 20 — Phase 3 Exit Criteria & Smoke Test](#section-20--phase-3-exit-criteria--smoke-test)

---

## Section 1 — Phase 3 Rules & Architecture

> **Read before writing any code.**

### What Changes vs Phase 2

| Component | Phase 2 State | Phase 3 Target |
|-----------|--------------|----------------|
| Search | Tavily only | Tavily + Haiku web search tool |
| Brave search | Dead code | Deleted entirely |
| Tracing | `@traceable` decorators present but LANGCHAIN_TRACING_V2=false | LangSmith active, every agent traced |
| Checkpointing | `build_graph(checkpointer=None)` — never configured | SqliteSaver wired in `run_pipeline()` |
| Fallback logic | Per-agent ad hoc | Systematic `NodeResult` wrapper on every node |
| Extraction | 5 categories loosely | 4 explicit coverage buckets as first-class state fields |
| Entities | Raw strings, duplicates possible | Canonicalized, merged, deduped before Neo4j write |
| Relationships | Not run-scoped in DB | `run_id` property on every relationship |
| Graph artifacts | HTML generated but not saved | Saved to `.graph_artifacts/{run_id}.html` per run |
| Audit logs | Python logging only | Structured JSON per run in `.audit_logs/` |
| Citations | `source_url` field exists | Full citation objects, clickable links in UI |
| Visualization | vis.js basic | D3.js force-directed, interactive, styled |
| Export | UI button mentioned but not wired | Fully functional PDF download |
| Inconsistencies | LLM may note them | Explicit `inconsistency` schema + detection step |

### Golden Rules

1. **All new LLM calls use `call_llm()` from `utils/anthropic_client.py`** — never instantiate `anthropic.Anthropic()` elsewhere.
2. **Every node is wrapped in `NodeResult`** — nodes return success/partial/failure, never raise uncaught exceptions.
3. **LangSmith tracing is conditional** — `if LANGCHAIN_TRACING: @traceable` else no-op. Never crash if LangSmith is down.
4. **`USE_MOCK=true` still works** — Phase 1 and Phase 2 mock paths are never touched.
5. **run_id propagates everywhere** — entities, relationships, logs, artifacts, checkpoints all tagged with `run_id`.
6. **Haiku web search is additive** — it supplements Tavily results, never replaces. Tavily runs first.

---

## Section 2 — Config Updates

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 2 — update config.py for Phase 3`

```python
# Add to config.py — append after existing Phase 2 additions

import os

# ── LangSmith ─────────────────────────────────────────────────────────────────
LANGCHAIN_TRACING: bool     = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_PROJECT: str      = os.getenv("LANGCHAIN_PROJECT", f"deeptrace-{ENV}")
LANGCHAIN_API_KEY: str      = os.getenv("LANGCHAIN_API_KEY", "")

# ── Checkpointing ─────────────────────────────────────────────────────────────
CHECKPOINT_DB_PATH: str     = os.getenv("CHECKPOINT_DB_PATH", ".checkpoints/deeptrace.db")

# ── Audit logging ─────────────────────────────────────────────────────────────
AUDIT_LOG_DIR: str          = os.getenv("AUDIT_LOG_DIR", ".audit_logs")

# ── Graph artifact persistence ────────────────────────────────────────────────
GRAPH_ARTIFACT_DIR: str     = os.getenv("GRAPH_ARTIFACT_DIR", ".graph_artifacts")

# ── Rate limiting ─────────────────────────────────────────────────────────────
LLM_MAX_RETRIES: int        = int(os.getenv("LLM_MAX_RETRIES", "3"))
LLM_RETRY_BASE_DELAY: float = float(os.getenv("LLM_RETRY_BASE_DELAY", "1.0"))
LLM_REQUESTS_PER_MIN: int   = int(os.getenv("LLM_REQUESTS_PER_MIN", "50"))  # Haiku tier 1

# ── Search ────────────────────────────────────────────────────────────────────
HAIKU_WEB_SEARCH_ENABLED: bool = os.getenv("HAIKU_WEB_SEARCH_ENABLED", "true").lower() == "true"
MAX_SEARCH_RESULTS_PER_QUERY: int = int(os.getenv("MAX_SEARCH_RESULTS_PER_QUERY", "5"))

# ── Extraction coverage ───────────────────────────────────────────────────────
EXTRACTION_CATEGORIES = ["biographical", "professional", "financial", "behavioral"]

# ── Entity canonicalization ───────────────────────────────────────────────────
ENTITY_SIMILARITY_THRESHOLD: float = float(os.getenv("ENTITY_SIMILARITY_THRESHOLD", "0.85"))

# ── Phase 3 validation ────────────────────────────────────────────────────────
def validate_phase3_config() -> list:
    """Check all required Phase 3 env vars are set."""
    errors = validate_phase2_config()  # include Phase 2 checks
    if LANGCHAIN_TRACING and not LANGCHAIN_API_KEY:
        errors.append("LANGCHAIN_API_KEY — required when LANGCHAIN_TRACING_V2=true")
    return errors
```

---

## Section 3 — Remove Brave Search

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 3 — remove Brave search`

### Files to Delete

```bash
# Delete these files entirely:
rm search/brave_search.py
```

### Files to Update

**`search/tavily_search.py`** — remove all Brave imports and fallback references:
```python
# Remove these lines from tavily_search.py:
# from search.brave_search import brave_search   ← DELETE
# Any line referencing brave_search              ← DELETE
# The "fallback to Brave" comment block          ← DELETE

# The Tavily else branch already has its own error fallback to mock.
# That stays. Only the Brave-specific fallback is removed.
```

**`agents/scout_agent.py`** — remove Brave import and fallback call:
```python
# In scout_agent.py, find and remove:
# from search.brave_search import brave_search   ← DELETE
# The block: "if len(results) < 3: brave_results = await brave_search(...)" ← DELETE

# Replace with: if len(results) < MIN_RESULTS_THRESHOLD: log warning and continue
# MIN_RESULTS_THRESHOLD = 2 (defined in config or inline)
```

**`requirements.txt`** — no changes needed (Brave used only aiohttp which is kept).

**`.env.example`** — remove `BRAVE_SEARCH_API_KEY` line.

---

## Section 4 — Rate Limiter + Retry Decorator

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 4 — create utils/retry.py`

### `utils/retry.py`

```python
"""
retry.py — Rate limiting and retry logic for all external API calls.

Wraps Anthropic and Tavily calls with:
  - Exponential backoff on rate limit errors (HTTP 429 / RateLimitError)
  - Jitter to prevent thundering herd on parallel agent calls
  - Maximum retry cap (configurable via LLM_MAX_RETRIES in config)
  - Token bucket rate limiter to stay within Haiku tier-1 limits (50 req/min)

Architecture position: imported by utils/anthropic_client.py and search/tavily_search.py.
"""
import asyncio
import functools
import logging
import random
import time
import threading
from typing import Callable, Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Token Bucket Rate Limiter (thread-safe for sync calls)
# ─────────────────────────────────────────────────────────────────────────────

class TokenBucket:
    """
    Thread-safe token bucket rate limiter.
    Allows `rate` requests per 60 seconds.
    Blocks the calling thread until a token is available.
    """
    def __init__(self, rate: int = 50):
        self._rate      = rate                  # tokens per minute
        self._tokens    = float(rate)
        self._last_fill = time.monotonic()
        self._lock      = threading.Lock()

    def acquire(self) -> None:
        """Block until a token is available. Thread-safe."""
        with self._lock:
            now   = time.monotonic()
            delta = now - self._last_fill
            self._tokens     = min(float(self._rate), self._tokens + delta * (self._rate / 60.0))
            self._last_fill  = now
            if self._tokens < 1.0:
                wait = (1.0 - self._tokens) / (self._rate / 60.0)
                logger.debug(f"[RateLimit] Throttling — waiting {wait:.2f}s")
                time.sleep(wait)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0


# Global rate limiter instances — one per external service
_llm_bucket    = None
_search_bucket = None


def get_llm_bucket() -> TokenBucket:
    global _llm_bucket
    if _llm_bucket is None:
        from config import LLM_REQUESTS_PER_MIN
        _llm_bucket = TokenBucket(rate=LLM_REQUESTS_PER_MIN)
    return _llm_bucket


def get_search_bucket() -> TokenBucket:
    global _search_bucket
    if _search_bucket is None:
        _search_bucket = TokenBucket(rate=20)  # Tavily free tier: ~20 req/min safe limit
    return _search_bucket


# ─────────────────────────────────────────────────────────────────────────────
# Retry Decorator
# ─────────────────────────────────────────────────────────────────────────────

def with_retry(
    max_retries: int = None,
    base_delay:  float = None,
    retryable_exceptions: tuple = None,
):
    """
    Decorator: retry a function with exponential backoff + jitter.

    Args:
        max_retries:           Max retry attempts. Defaults to LLM_MAX_RETRIES from config.
        base_delay:            Base delay in seconds. Doubles each retry. Defaults to LLM_RETRY_BASE_DELAY.
        retryable_exceptions:  Exception types that trigger a retry. Defaults to common API errors.

    Usage:
        @with_retry()
        def call_anthropic(...): ...

        @with_retry(max_retries=2, base_delay=0.5)
        async def search_tavily(...): ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            from config import LLM_MAX_RETRIES, LLM_RETRY_BASE_DELAY
            _max     = max_retries    if max_retries    is not None else LLM_MAX_RETRIES
            _delay   = base_delay     if base_delay     is not None else LLM_RETRY_BASE_DELAY
            _errors  = retryable_exceptions or _default_retryable()

            for attempt in range(_max + 1):
                try:
                    return func(*args, **kwargs)
                except _errors as e:
                    if attempt == _max:
                        logger.error(f"[Retry] {func.__name__} failed after {_max} retries: {e}")
                        raise
                    wait = _delay * (2 ** attempt) + random.uniform(0, 0.5)
                    logger.warning(f"[Retry] {func.__name__} attempt {attempt+1}/{_max} failed: {e}. Retrying in {wait:.1f}s")
                    time.sleep(wait)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            from config import LLM_MAX_RETRIES, LLM_RETRY_BASE_DELAY
            _max    = max_retries    if max_retries    is not None else LLM_MAX_RETRIES
            _delay  = base_delay     if base_delay     is not None else LLM_RETRY_BASE_DELAY
            _errors = retryable_exceptions or _default_retryable()

            for attempt in range(_max + 1):
                try:
                    return await func(*args, **kwargs)
                except _errors as e:
                    if attempt == _max:
                        logger.error(f"[Retry] {func.__name__} failed after {_max} retries: {e}")
                        raise
                    wait = _delay * (2 ** attempt) + random.uniform(0, 0.5)
                    logger.warning(f"[Retry] {func.__name__} attempt {attempt+1}/{_max} failed: {e}. Retrying in {wait:.1f}s")
                    await asyncio.sleep(wait)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def _default_retryable() -> tuple:
    """Return the default tuple of exception types that should trigger a retry."""
    try:
        import anthropic
        base = (anthropic.RateLimitError, anthropic.APITimeoutError, anthropic.APIConnectionError)
    except ImportError:
        base = ()
    return base + (ConnectionError, TimeoutError, OSError)
```

### Update `utils/anthropic_client.py` — wire rate limiter and retry

```python
# In utils/anthropic_client.py, update call_llm() to:
# 1. Acquire a token from the rate limiter before the API call
# 2. Wrap the client.messages.create() call with the retry decorator

# Add these imports at top:
from utils.retry import get_llm_bucket, with_retry

# Wrap the inner API call function:
@with_retry()
def _do_create(client, model, max_tokens, system_block, messages):
    """Inner function — wrapped with retry decorator."""
    return client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_block,
        messages=messages,
    )

# In call_llm(), before client.messages.create():
get_llm_bucket().acquire()   # Rate limit: blocks if > 50 req/min
response = _do_create(client, model, max_tokens, system_block,
                      [{"role": "user", "content": user_message}])
```

### Update `search/tavily_search.py` — wire search rate limiter

```python
# In _sync_tavily_search(), before client.search():
from utils.retry import get_search_bucket
get_search_bucket().acquire()   # Rate limit Tavily calls

# Wrap client.search() with retry (Tavily can return 429 on free tier):
@with_retry(max_retries=2, base_delay=2.0)
def _do_tavily_search(client, query, depth, max_results):
    return client.search(
        query=query,
        search_depth=depth,
        max_results=max_results,
        include_raw_content=False,
    )
```

---

## Section 5 — LangSmith Tracing

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 5 — configure LangSmith tracing`

### `utils/tracing.py`

```python
"""
tracing.py — LangSmith tracing configuration and conditional @traceable decorator.

When LANGCHAIN_TRACING_V2=true, wraps all agent functions with LangSmith tracing.
When false (dev default), applies a no-op decorator — zero performance overhead.

Architecture position: imported by all agent files and pipeline.py.
"""
import functools
import logging
from typing import Callable

logger = logging.getLogger(__name__)

_langsmith_available = False

try:
    from langsmith import traceable as _ls_traceable
    _langsmith_available = True
except ImportError:
    _ls_traceable = None


def traceable(name: str = None, run_type: str = "chain", tags: list = None):
    """
    Conditional @traceable decorator.

    When LANGCHAIN_TRACING=true and LangSmith is available:
      - Wraps the function with LangSmith tracing
      - Creates a named run in the configured project
      - Attaches run_type and tags for filtering in the LangSmith UI

    When LANGCHAIN_TRACING=false OR LangSmith is not available:
      - Returns the original function unchanged (zero overhead)

    Usage:
        @traceable(name="supervisor_plan", run_type="chain", tags=["supervisor"])
        def supervisor_plan(state): ...
    """
    def decorator(func: Callable) -> Callable:
        from config import LANGCHAIN_TRACING
        if not LANGCHAIN_TRACING or not _langsmith_available:
            return func   # No-op — return original function unchanged

        try:
            _name = name or func.__name__
            return _ls_traceable(
                name=_name,
                run_type=run_type,
                tags=tags or [],
            )(func)
        except Exception as e:
            logger.warning(f"[LangSmith] Could not apply @traceable to {func.__name__}: {e}")
            return func

    return decorator


def configure_langsmith() -> bool:
    """
    Configure LangSmith environment variables at startup.
    Call once from main.py before building the pipeline graph.
    Returns True if LangSmith is active.
    """
    from config import LANGCHAIN_TRACING, LANGCHAIN_PROJECT, LANGCHAIN_API_KEY
    import os

    if not LANGCHAIN_TRACING:
        logger.info("[LangSmith] Tracing disabled (LANGCHAIN_TRACING_V2=false)")
        return False

    if not LANGCHAIN_API_KEY:
        logger.warning("[LangSmith] LANGCHAIN_API_KEY not set — tracing disabled")
        return False

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"]    = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"]    = LANGCHAIN_PROJECT

    logger.info(f"[LangSmith] Tracing active — project: {LANGCHAIN_PROJECT}")
    return True
```

### Update all agent files — replace existing `@traceable` imports with conditional version

```python
# In EVERY agent file, replace:
# from langsmith import traceable          ← DELETE this line

# With:
from utils.tracing import traceable       # ← ADD this line

# The @traceable decorators on functions stay identical.
# They now use the conditional version that safely no-ops when LangSmith is off.
```

**Files to update:** `agents/supervisor.py`, `agents/scout_agent.py`,
`agents/deep_dive_agent.py`, `agents/risk_evaluator.py`, `agents/graph_builder.py`

### Update `main.py` — call `configure_langsmith()` at startup

```python
# In main.py, at the top of the main CLI entry point, add:
from utils.tracing import configure_langsmith

# In the @click.command() handler, before build_graph():
configure_langsmith()
```

### `evaluation/langsmith_eval.py` — implement the stub

```python
"""
langsmith_eval.py — LangSmith evaluation dataset and scorer for DeepTrace.

Creates a LangSmith dataset from the 3 evaluation personas and runs
automated scoring after each pipeline run.

Architecture position: called from main.py --eval flag and frontend/pages/04_eval.py.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_or_create_dataset(client, dataset_name: str = "deeptrace-eval-v1"):
    """
    Get or create the LangSmith evaluation dataset.
    Creates it with the 3 standard DeepTrace personas if it doesn't exist.
    """
    try:
        datasets = list(client.list_datasets(dataset_name=dataset_name))
        if datasets:
            logger.info(f"[LangSmith] Using existing dataset: {dataset_name}")
            return datasets[0]

        # Create with 3 evaluation examples
        from evaluation.eval_set import EVAL_PERSONAS
        dataset = client.create_dataset(dataset_name, description="DeepTrace identity research evaluation")
        for persona in EVAL_PERSONAS:
            client.create_example(
                inputs={"target_name": persona["name"], "target_context": persona["context"]},
                outputs={"expected_risk_score": persona["expected_risk_score"],
                         "expected_flag_count":  persona["expected_flag_count"]},
                dataset_id=dataset.id,
            )
        logger.info(f"[LangSmith] Created dataset: {dataset_name} with {len(EVAL_PERSONAS)} examples")
        return dataset

    except Exception as e:
        logger.error(f"[LangSmith] Dataset creation failed: {e}")
        return None


def score_run(run_state: dict, expected: dict) -> dict:
    """
    Score a completed pipeline run against expected outputs.
    Returns dict of metric_name → score (0.0–1.0).
    """
    scores = {}

    # Fact recall: did we find facts in all 4 expected categories?
    found_cats = {f.get("category") for f in run_state.get("extracted_facts", [])}
    expected_cats = {"biographical", "professional", "financial", "behavioral"}
    scores["extraction_coverage"] = len(found_cats & expected_cats) / 4.0

    # Risk flag count proximity
    found_flags = len(run_state.get("risk_flags", []))
    exp_flags   = expected.get("expected_flag_count", 0)
    if exp_flags > 0:
        scores["risk_flag_recall"] = min(found_flags / exp_flags, 1.0)
    else:
        scores["risk_flag_recall"] = 1.0 if found_flags == 0 else 0.5

    # Research quality score
    scores["research_quality"] = float(run_state.get("research_quality", 0.0))

    # Citation completeness: % of facts with source_url populated
    facts = run_state.get("extracted_facts", [])
    if facts:
        cited = sum(1 for f in facts if f.get("source_url"))
        scores["citation_completeness"] = cited / len(facts)
    else:
        scores["citation_completeness"] = 0.0

    return scores
```

---

## Section 6 — State Checkpointing

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 6 — configure SqliteSaver checkpointing`

### Update `pipeline.py` — wire SqliteSaver

```python
"""
pipeline.py — Phase 3 update.

Wires SqliteSaver checkpointer into run_pipeline() and stream_pipeline().
Every run now has a thread_id (= run_id) for checkpoint isolation.
"""
import os
import logging
from langgraph.graph        import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

logger = logging.getLogger(__name__)


def _get_checkpointer():
    """
    Create and return a SqliteSaver instance.
    Creates the checkpoint directory if it does not exist.
    """
    from config import CHECKPOINT_DB_PATH
    db_dir = os.path.dirname(CHECKPOINT_DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    checkpointer = SqliteSaver.from_conn_string(CHECKPOINT_DB_PATH)
    logger.info(f"[Checkpoint] SqliteSaver configured: {CHECKPOINT_DB_PATH}")
    return checkpointer


def run_pipeline(target_name: str, target_context: str = "") -> dict:
    """
    Execute a full research run with checkpointing.
    The run_id from initial_state is used as thread_id for checkpoint isolation.
    Each run is independently resumable.
    """
    from state.agent_state import make_initial_state
    initial_state = make_initial_state(target_name, target_context)
    run_id = initial_state["run_id"]

    checkpointer = _get_checkpointer()
    graph = build_graph(checkpointer=checkpointer)

    # thread_id = run_id ensures each run has its own checkpoint namespace
    config = {"configurable": {"thread_id": run_id}}

    logger.info(f"[Pipeline] Starting run_id={run_id} for: {target_name}")
    final_state = graph.invoke(initial_state, config=config)
    logger.info(
        f"[Pipeline] Complete run_id={run_id} | "
        f"facts={len(final_state.get('extracted_facts', []))} | "
        f"flags={len(final_state.get('risk_flags', []))} | "
        f"quality={final_state.get('research_quality', 0):.2f}"
    )
    return final_state


def stream_pipeline(target_name: str, target_context: str = ""):
    """
    Execute with streaming and checkpointing.
    Yields (node_name, state_delta) tuples.
    """
    from state.agent_state import make_initial_state
    initial_state = make_initial_state(target_name, target_context)
    run_id  = initial_state["run_id"]

    checkpointer = _get_checkpointer()
    graph  = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": run_id}}

    for chunk in graph.stream(initial_state, config=config, stream_mode="updates"):
        node_name = list(chunk.keys())[0]
        yield node_name, chunk[node_name]


def resume_pipeline(run_id: str):
    """
    Resume an interrupted pipeline run from its last checkpoint.
    Used when a run fails mid-way and needs to be restarted.
    """
    checkpointer = _get_checkpointer()
    graph  = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": run_id}}

    # Pass None as input — LangGraph resumes from checkpoint
    logger.info(f"[Pipeline] Resuming run_id={run_id}")
    final_state = graph.invoke(None, config=config)
    return final_state
```

---

## Section 7 — Structured Audit Logger

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 7 — create utils/audit_logger.py`

### `utils/audit_logger.py`

```python
"""
audit_logger.py — Structured JSON audit logging for DeepTrace.

Every search query, LLM decision, retry event, and node completion is
recorded as a structured JSON event in .audit_logs/{run_id}.jsonl.

One file per run (JSONL format — one JSON object per line).
Each event has: timestamp, run_id, event_type, agent, data.

Event types:
  SEARCH_QUERY   — a search query issued with source and result count
  LLM_CALL       — an LLM call with model, tokens, and agent name
  LLM_RETRY      — a retry event with attempt number and error
  NODE_START     — a LangGraph node started
  NODE_COMPLETE  — a LangGraph node completed with output summary
  NODE_FAILURE   — a node failed with error details
  ENTITY_MERGED  — two entities were canonicalized/merged
  INCONSISTENCY  — a data inconsistency was detected
  RISK_FLAG      — a risk flag was created

Architecture position: imported by all agents and utils/anthropic_client.py.
"""
import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)
_lock  = threading.Lock()

# Current run context (set at start of each run)
_current_run_id: str = "unknown"


def set_run_id(run_id: str) -> None:
    """Set the current run_id. Call at the start of each pipeline run."""
    global _current_run_id
    _current_run_id = run_id


def _log_path() -> str:
    from config import AUDIT_LOG_DIR
    os.makedirs(AUDIT_LOG_DIR, exist_ok=True)
    return os.path.join(AUDIT_LOG_DIR, f"{_current_run_id}.jsonl")


def log_event(
    event_type: str,
    agent:      str,
    data:       dict,
    run_id:     str = None,
) -> None:
    """
    Write a structured audit event to the run's JSONL log file.

    Args:
        event_type: One of the event type constants above
        agent:      Agent or module name (e.g. "supervisor", "scout_agent")
        data:       Event-specific payload dict
        run_id:     Override run_id (defaults to current run context)
    """
    event = {
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "run_id":     run_id or _current_run_id,
        "event_type": event_type,
        "agent":      agent,
        "data":       data,
    }
    with _lock:
        try:
            with open(_log_path(), "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.warning(f"[AuditLog] Write failed: {e}")


def log_search_query(agent: str, query: str, source: str, result_count: int) -> None:
    log_event("SEARCH_QUERY", agent, {
        "query": query, "source": source, "result_count": result_count
    })


def log_llm_call(agent: str, model: str, input_tokens: int, output_tokens: int) -> None:
    log_event("LLM_CALL", agent, {
        "model": model, "input_tokens": input_tokens, "output_tokens": output_tokens
    })


def log_llm_retry(agent: str, attempt: int, error: str) -> None:
    log_event("LLM_RETRY", agent, {"attempt": attempt, "error": str(error)[:200]})


def log_node_start(node: str) -> None:
    log_event("NODE_START", node, {})


def log_node_complete(node: str, summary: dict) -> None:
    log_event("NODE_COMPLETE", node, summary)


def log_node_failure(node: str, error: str, partial_results: dict = None) -> None:
    log_event("NODE_FAILURE", node, {"error": str(error)[:500], "partial": partial_results or {}})


def log_entity_merged(canonical: str, merged_from: str, similarity: float) -> None:
    log_event("ENTITY_MERGED", "canonicalizer", {
        "canonical": canonical, "merged_from": merged_from, "similarity": similarity
    })


def log_inconsistency(claim_a: str, claim_b: str, inconsistency_type: str) -> None:
    log_event("INCONSISTENCY", "inconsistency_detector", {
        "claim_a": claim_a[:200], "claim_b": claim_b[:200], "type": inconsistency_type
    })


def log_risk_flag(flag_id: str, title: str, severity: str, confidence: float) -> None:
    log_event("RISK_FLAG", "risk_evaluator", {
        "flag_id": flag_id, "title": title, "severity": severity, "confidence": confidence
    })


def load_run_log(run_id: str) -> list:
    """
    Load all audit events for a given run_id.
    Returns list of event dicts, ordered by timestamp.
    """
    from config import AUDIT_LOG_DIR
    path = os.path.join(AUDIT_LOG_DIR, f"{run_id}.jsonl")
    if not os.path.exists(path):
        return []
    events = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


def list_run_ids() -> list:
    """Return all run IDs that have audit logs, sorted newest first."""
    from config import AUDIT_LOG_DIR
    if not os.path.exists(AUDIT_LOG_DIR):
        return []
    files = sorted(
        [f[:-6] for f in os.listdir(AUDIT_LOG_DIR) if f.endswith(".jsonl")],
        reverse=True,
    )
    return files
```

### Update `utils/anthropic_client.py` — add audit logging

```python
# In call_llm(), after record_spend():
from utils.audit_logger import log_llm_call
log_llm_call(
    agent="anthropic_client",
    model=model,
    input_tokens=response.usage.input_tokens,
    output_tokens=response.usage.output_tokens,
)
```

### Update `main.py` — set run_id in audit logger at pipeline start

```python
# In run_pipeline() before graph.invoke():
from utils.audit_logger import set_run_id
set_run_id(run_id)
```

---

## Section 8 — Multi-Source Search (Tavily + Haiku Web Search)

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 8 — add Haiku web search tool`

### `search/haiku_search.py`

```python
"""
haiku_search.py — Anthropic Haiku web search tool integration.

Uses the Anthropic web_search_20250305 tool to run web searches via Haiku.
This supplements Tavily results — useful when Tavily has low result counts
or when targeted site-specific searches are needed.

Returns the same result dict format as tavily_search.py for drop-in compatibility.

Cost: ~$0.001-0.002 per search call (Haiku + web_search tool).
Architecture position: called by agents/scout_agent.py as secondary source.
"""
import asyncio
import logging
from typing import List

logger = logging.getLogger(__name__)


async def haiku_web_search(query: str, max_results: int = 5) -> List[dict]:
    """
    Execute a web search using Haiku's built-in web_search tool.

    Args:
        query:       Search query string
        max_results: Max results to return (Haiku returns up to ~5 per call)

    Returns:
        List of result dicts with url, title, content, relevance, source_domain
    """
    from config import USE_MOCK, HAIKU_WEB_SEARCH_ENABLED, MODELS, ENV
    from utils.audit_logger import log_search_query

    if USE_MOCK:
        logger.debug("[HaikuSearch] MOCK mode — returning empty list")
        return []

    if not HAIKU_WEB_SEARCH_ENABLED:
        logger.debug("[HaikuSearch] Disabled via config")
        return []

    return await asyncio.to_thread(_sync_haiku_search, query, max_results)


def _sync_haiku_search(query: str, max_results: int) -> List[dict]:
    """Sync implementation — called via asyncio.to_thread."""
    from config import MODELS, ENV
    from utils.retry import get_search_bucket, with_retry
    from utils.audit_logger import log_search_query

    try:
        from utils.anthropic_client import get_client
        client = get_client()

        get_search_bucket().acquire()

        response = client.messages.create(
            model=MODELS.get("scout", "claude-haiku-4-5-20251001"),
            max_tokens=1500,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{
                "role": "user",
                "content": (
                    f"Search the web for: {query}\n\n"
                    f"Return the top {max_results} most relevant results. "
                    f"For each result include the URL and a summary of the content."
                )
            }],
        )

        results = _parse_haiku_search_response(response)
        log_search_query("haiku_search", query, "haiku_web_search", len(results))
        logger.info(f"[HaikuSearch] '{query[:40]}' → {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"[HaikuSearch] Failed for '{query}': {e}")
        return []


def _parse_haiku_search_response(response) -> List[dict]:
    """
    Parse Haiku web search response into standard result format.
    Handles both tool_use blocks and text blocks containing URLs.
    """
    results = []

    for block in response.content:
        # Tool result blocks contain structured search results
        if block.type == "tool_result":
            for item in (block.content or []):
                if hasattr(item, "text") and item.text:
                    results.extend(_parse_text_results(item.text))

        # Text blocks may contain formatted search summaries
        elif block.type == "text" and block.text:
            results.extend(_parse_text_results(block.text))

    # Deduplicate by URL
    seen_urls = set()
    deduped   = []
    for r in results:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            deduped.append(r)

    return deduped


def _parse_text_results(text: str) -> List[dict]:
    """Extract URL + content pairs from Haiku text response."""
    import re
    results = []
    # Match markdown-style links and surrounding context
    url_pattern = re.compile(r'https?://[^\s\)\]]+')
    urls = url_pattern.findall(text)

    for url in urls:
        domain = _extract_domain(url)
        # Use surrounding text as content snippet
        idx   = text.find(url)
        start = max(0, idx - 100)
        end   = min(len(text), idx + 300)
        snippet = text[start:end].strip()

        results.append({
            "url":           url,
            "title":         domain,
            "content":       snippet,
            "relevance":     0.70,   # Moderate confidence for Haiku-sourced results
            "source_domain": domain,
            "search_source": "haiku_web_search",
        })

    return results


def _extract_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return "unknown"
```

### Update `agents/scout_agent.py` — add Haiku search as secondary source

```python
"""
scout_agent.py — Phase 3 update.

Adds Haiku web search as a secondary source alongside Tavily.
Both run in parallel via asyncio.gather.
Results are merged, deduplicated by URL, and sorted by relevance.
Brave search references are removed entirely.
"""
# In the else branch of run_scout(), replace the Brave fallback with:

from search.haiku_search import haiku_web_search
from utils.audit_logger  import log_search_query, log_node_complete

# Run Tavily and Haiku searches in parallel for each query
async def _fetch_one_query(query: str, idx: int) -> list:
    tavily_task = tavily_search(query)
    haiku_task  = haiku_web_search(query, max_results=3)

    tavily_results, haiku_results = await asyncio.gather(
        tavily_task, haiku_task, return_exceptions=True
    )

    combined = []

    if isinstance(tavily_results, list):
        for r in tavily_results:
            r["search_source"] = r.get("search_source", "tavily")
        combined.extend(tavily_results)
        log_search_query("scout_agent", query, "tavily", len(tavily_results))
    else:
        logger.warning(f"[Scout] Tavily failed for query {idx}: {tavily_results}")

    if isinstance(haiku_results, list):
        combined.extend(haiku_results)
        log_search_query("scout_agent", query, "haiku_web_search", len(haiku_results))
    else:
        logger.warning(f"[Scout] Haiku search failed for query {idx}: {haiku_results}")

    # Deduplicate by URL
    seen_urls = set()
    deduped   = []
    for r in combined:
        if r.get("url") and r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            deduped.append(r)

    return deduped


# In the main else branch:
all_results = []
tasks = [_fetch_one_query(q, i) for i, q in enumerate(queries)]
query_results = await asyncio.gather(*tasks, return_exceptions=True)

for batch in query_results:
    if isinstance(batch, list):
        all_results.extend(batch)

# Sort by relevance descending
all_results.sort(key=lambda r: r.get("relevance", 0), reverse=True)

# Cap total results
all_results = all_results[:MAX_SEARCH_RESULTS_PER_QUERY * len(queries)]

log_node_complete("scout_agent", {"total_results": len(all_results), "queries": len(queries)})
return {"raw_results": all_results}
```

---

## Section 9 — Extraction Coverage (4 Categories as First-Class Outputs)

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 9 — 4-category extraction coverage`

### Update `state/agent_state.py` — add coverage tracking fields

```python
# Add these fields to AgentState TypedDict:

# 4-category extraction coverage (first-class outputs)
biographical_coverage:  Annotated[List[Fact], operator.add]   # facts about life/identity
professional_coverage:  Annotated[List[Fact], operator.add]   # career/role/credential facts
financial_coverage:     Annotated[List[Fact], operator.add]   # fund/investment/AUM facts
behavioral_coverage:    Annotated[List[Fact], operator.add]   # pattern/behavior/conduct facts

# Coverage completeness scores per category (0.0–1.0)
coverage_scores: dict   # {"biographical": 0.8, "professional": 0.6, ...}

# Inconsistencies detected
inconsistencies: Annotated[List[dict], operator.add]
```

### Update `make_initial_state()` — add coverage defaults

```python
# Add to make_initial_state():
"biographical_coverage":  [],
"professional_coverage":  [],
"financial_coverage":     [],
"behavioral_coverage":    [],
"coverage_scores":        {"biographical": 0.0, "professional": 0.0,
                           "financial": 0.0, "behavioral": 0.0},
"inconsistencies":        [],
```

### `utils/coverage_classifier.py`

```python
"""
coverage_classifier.py — Classify extracted facts into the 4 coverage categories.

Maps each Fact's category field (biographical/financial/network/legal/other)
to one of the 4 first-class coverage buckets used for quality scoring.

Also computes coverage_scores per category based on fact count and confidence.

Architecture position: called by agents/deep_dive_agent.py after extraction.
"""
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

# Mapping from Fact.category → coverage bucket
CATEGORY_MAP = {
    "biographical": "biographical_coverage",
    "professional": "professional_coverage",    # new category
    "financial":    "financial_coverage",
    "behavioral":   "behavioral_coverage",      # new category
    "network":      "professional_coverage",    # network → professional bucket
    "legal":        "behavioral_coverage",      # legal → behavioral bucket
    "other":        "biographical_coverage",    # fallback
}

# Minimum facts needed to consider a category "covered"
COVERAGE_THRESHOLD = 2


def classify_facts(facts: list) -> dict:
    """
    Classify a list of Fact objects (or dicts) into the 4 coverage buckets.

    Returns:
        dict with keys: biographical_coverage, professional_coverage,
                        financial_coverage, behavioral_coverage
                        (each a list of facts)
    """
    buckets = {
        "biographical_coverage":  [],
        "professional_coverage":  [],
        "financial_coverage":     [],
        "behavioral_coverage":    [],
    }

    for fact in facts:
        cat = fact.get("category") if isinstance(fact, dict) else getattr(fact, "category", "other")
        bucket_key = CATEGORY_MAP.get(cat, "biographical_coverage")
        buckets[bucket_key].append(fact)

    return buckets


def compute_coverage_scores(buckets: dict) -> dict:
    """
    Compute a 0.0–1.0 coverage score per category.

    Score formula:
      - 0 facts = 0.0
      - 1 fact  = 0.3
      - 2 facts = 0.6
      - 3+ facts, avg confidence >= 0.7 = 1.0
      - 3+ facts, avg confidence < 0.7  = 0.8
    """
    scores = {}
    for bucket_key, facts in buckets.items():
        category = bucket_key.replace("_coverage", "")
        count = len(facts)
        if count == 0:
            scores[category] = 0.0
        elif count == 1:
            scores[category] = 0.3
        elif count == 2:
            scores[category] = 0.6
        else:
            avg_conf = sum(
                (f.get("confidence") if isinstance(f, dict) else getattr(f, "confidence", 0.5))
                for f in facts
            ) / count
            scores[category] = 1.0 if avg_conf >= 0.7 else 0.8

    return scores


def identify_coverage_gaps(scores: dict) -> List[str]:
    """
    Return list of category names that are below COVERAGE_THRESHOLD score.
    Used by supervisor_reflect to generate targeted gap queries.
    """
    return [cat for cat, score in scores.items() if score < 0.6]
```

### Update `agents/deep_dive_agent.py` — populate coverage fields

```python
# After Pydantic validation of facts, add:
from utils.coverage_classifier import classify_facts, compute_coverage_scores

facts_as_dicts = [f.model_dump() for f in facts]
buckets  = classify_facts(facts_as_dicts)
cov_scores = compute_coverage_scores(buckets)

# Update return dict:
return {
    "extracted_facts":        facts,
    "entities":               entities,
    "relationships":          rels,
    "confidence_map":         conf_map,
    "biographical_coverage":  buckets["biographical_coverage"],
    "professional_coverage":  buckets["professional_coverage"],
    "financial_coverage":     buckets["financial_coverage"],
    "behavioral_coverage":    buckets["behavioral_coverage"],
    "coverage_scores":        cov_scores,
}
```

### Update `agents/supervisor.py` — use coverage gaps in reflect

```python
# In supervisor_reflect() else branch, update user_msg to include:
from utils.coverage_classifier import identify_coverage_gaps

current_scores = state.get("coverage_scores", {})
gaps_from_coverage = identify_coverage_gaps(current_scores)

user_msg = f"""...existing content...

COVERAGE SCORES:
{json.dumps(current_scores, indent=2)}

UNCOVERED CATEGORIES: {gaps_from_coverage}
Prioritise queries for these categories in the next loop."""
```

---

## Section 10 — Entity Canonicalization + Deduplication

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 10 — entity canonicalization`

### `utils/entity_canon.py`

```python
"""
entity_canon.py — Entity name canonicalization and deduplication.

Merges near-duplicate entities before writing to Neo4j.
Uses string similarity (difflib) — no ML model needed.

Examples of duplicates this catches:
  "Timothy Overturf"  ↔  "Tim Overturf"       → merge to "Timothy Overturf"
  "Sisu Capital LLC"  ↔  "Sisu Capital"        → merge to "Sisu Capital LLC"
  "SEC"               ↔  "U.S. Securities and Exchange Commission" → keep both (too different)

Architecture position: called by agents/graph_builder.py before Neo4j write.
"""
import logging
from difflib import SequenceMatcher
from typing import List, Tuple

logger = logging.getLogger(__name__)


def similarity(a: str, b: str) -> float:
    """Return string similarity ratio 0.0–1.0 using SequenceMatcher."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def canonicalize_entities(entities: List[dict]) -> Tuple[List[dict], dict]:
    """
    Deduplicate and canonicalize a list of entity dicts.

    Args:
        entities: List of entity dicts (from Pydantic model_dump())

    Returns:
        Tuple of:
          - cleaned entity list (duplicates removed, canonical names applied)
          - merge_map: {old_entity_id → canonical_entity_id} for fixing relationships
    """
    from config import ENTITY_SIMILARITY_THRESHOLD
    from utils.audit_logger import log_entity_merged

    if not entities:
        return [], {}

    canonical = []   # final list
    merge_map = {}   # old_id → canonical_id

    for entity in entities:
        name   = entity.get("name", "").strip()
        etype  = entity.get("entity_type", "")
        eid    = entity.get("entity_id", "")

        # Find best match in canonical list (same type only)
        best_match  = None
        best_score  = 0.0

        for canon_entity in canonical:
            if canon_entity.get("entity_type") != etype:
                continue   # Only merge same-type entities
            score = similarity(name, canon_entity.get("name", ""))
            if score > best_score:
                best_score  = score
                best_match  = canon_entity

        if best_match and best_score >= ENTITY_SIMILARITY_THRESHOLD:
            # Merge: map this entity_id to canonical entity_id
            canonical_id = best_match["entity_id"]
            merge_map[eid] = canonical_id

            # Prefer longer name (more complete)
            if len(name) > len(best_match.get("name", "")):
                best_match["name"] = name

            # Merge attributes (canonical wins on conflict)
            merged_attrs = {**entity.get("attributes", {}), **best_match.get("attributes", {})}
            best_match["attributes"] = merged_attrs

            # Take higher confidence
            best_match["confidence"] = max(
                best_match.get("confidence", 0),
                entity.get("confidence", 0)
            )

            log_entity_merged(best_match["name"], name, best_score)
            logger.info(f"[Canon] Merged '{name}' → '{best_match['name']}' (score={best_score:.2f})")

        else:
            # New unique entity — add to canonical list
            canonical.append(entity.copy())
            merge_map[eid] = eid   # Maps to itself

    logger.info(f"[Canon] {len(entities)} entities → {len(canonical)} after dedup")
    return canonical, merge_map


def remap_relationships(relationships: List[dict], merge_map: dict) -> List[dict]:
    """
    Update relationship from_id/to_id to point to canonical entity IDs.
    Drops relationships where either endpoint was merged into another entity
    and would create a self-loop (from_id == to_id after remapping).
    """
    updated = []
    for rel in relationships:
        new_from = merge_map.get(rel.get("from_id"), rel.get("from_id"))
        new_to   = merge_map.get(rel.get("to_id"),   rel.get("to_id"))

        if new_from == new_to:
            logger.debug(f"[Canon] Dropping self-loop relationship: {rel.get('rel_type')}")
            continue

        updated_rel = rel.copy()
        updated_rel["from_id"] = new_from
        updated_rel["to_id"]   = new_to
        updated.append(updated_rel)

    return updated
```

### Update `agents/graph_builder.py` — add canonicalization before Neo4j write

```python
# In run_graph_builder() else branch, BEFORE writing to Neo4j:
from utils.entity_canon import canonicalize_entities, remap_relationships

entities_raw      = [e.model_dump() for e in state["entities"]]
relationships_raw = [r.model_dump() for r in state["relationships"]]

# Canonicalize
canonical_entities, merge_map = canonicalize_entities(entities_raw)
canonical_rels = remap_relationships(relationships_raw, merge_map)

# Now write canonical data to Neo4j
entity_count = write_entities(canonical_entities, run_id=run_id)
rel_count    = write_relationships(canonical_rels,   run_id=run_id)
```

---

## Section 11 — Inconsistency Detection + Affiliation Heuristics

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 11 — inconsistency detection`

### `utils/inconsistency_detector.py`

```python
"""
inconsistency_detector.py — Detect factual inconsistencies and hidden affiliations.

Two detection methods:
  1. Rule-based: Fast, deterministic checks on structured fact fields
     - Date range conflicts (employment dates overlapping impossibly)
     - Numerical contradictions (AUM figures that differ by >50%)
     - Biographical contradictions (two different birth years)
     - Location conflicts (working in two places simultaneously)

  2. Affiliation heuristics: Pattern matching on entity relationships
     - Shell company indicators (entity type + name patterns)
     - Circular ownership detection (A → B → A)
     - Undisclosed fund connections (fund entity with no Person link)

Architecture position: called by agents/risk_evaluator.py.
"""
import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Rule-Based Inconsistency Detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_inconsistencies(facts: list) -> List[dict]:
    """
    Run all rule-based inconsistency checks against the fact list.

    Returns list of inconsistency dicts:
    {
      "type":        "date_conflict|numerical_contradiction|biographical_conflict|...",
      "description": "Human-readable description",
      "fact_ids":    ["f001", "f002"],
      "severity":    "HIGH|MEDIUM|LOW",
    }
    """
    inconsistencies = []
    from utils.audit_logger import log_inconsistency

    # Group facts by category for efficient lookup
    bio_facts = [f for f in facts if _get_field(f, "category") == "biographical"]
    fin_facts = [f for f in facts if _get_field(f, "category") == "financial"]

    # Check 1: Biographical contradictions (education, birthplace, age)
    inconsistencies.extend(_check_biographical_conflicts(bio_facts))

    # Check 2: Financial numerical contradictions (AUM, fund size)
    inconsistencies.extend(_check_financial_contradictions(fin_facts))

    # Check 3: Employment date overlaps
    inconsistencies.extend(_check_date_overlaps(facts))

    # Log each detected inconsistency
    for inc in inconsistencies:
        log_inconsistency(
            inc.get("description", ""),
            inc.get("description", ""),
            inc.get("type", "unknown"),
        )

    logger.info(f"[InconsistencyDetector] Found {len(inconsistencies)} inconsistencies")
    return inconsistencies


def _get_field(fact, field: str):
    """Get field from either dict or Pydantic model."""
    if isinstance(fact, dict):
        return fact.get(field)
    return getattr(fact, field, None)


def _check_biographical_conflicts(bio_facts: list) -> List[dict]:
    """Detect conflicting biographical claims (e.g., two different alma maters)."""
    conflicts = []

    # Find all education claims
    edu_facts = [f for f in bio_facts if _contains_edu_keyword(_get_field(f, "claim") or "")]
    if len(edu_facts) >= 2:
        schools = set()
        for f in edu_facts:
            school = _extract_institution(_get_field(f, "claim") or "")
            if school:
                schools.add(school)
        if len(schools) >= 3:   # 3+ different schools is suspicious
            conflicts.append({
                "type":        "biographical_conflict",
                "description": f"Multiple conflicting educational institutions found: {', '.join(list(schools)[:3])}",
                "fact_ids":    [_get_field(f, "fact_id") for f in edu_facts[:3]],
                "severity":    "MEDIUM",
            })

    return conflicts


def _check_financial_contradictions(fin_facts: list) -> List[dict]:
    """Detect contradictory AUM or fund size figures."""
    conflicts = []

    # Extract numerical values from financial claims
    amounts = []
    for f in fin_facts:
        claim = _get_field(f, "claim") or ""
        nums  = _extract_dollar_amounts(claim)
        for n in nums:
            amounts.append((n, _get_field(f, "fact_id")))

    if len(amounts) >= 2:
        vals = [a[0] for a in amounts]
        min_val, max_val = min(vals), max(vals)
        if min_val > 0 and max_val / min_val > 5.0:   # >5x discrepancy
            conflicts.append({
                "type":        "numerical_contradiction",
                "description": f"Conflicting financial figures: ${min_val:,.0f} vs ${max_val:,.0f} (>{max_val/min_val:.0f}x difference)",
                "fact_ids":    [a[1] for a in amounts[:4]],
                "severity":    "HIGH",
            })

    return conflicts


def _check_date_overlaps(facts: list) -> List[dict]:
    """Detect impossible simultaneous employment at multiple organizations."""
    # Simple heuristic: look for claims with overlapping years at different orgs
    dated_claims = []
    for f in facts:
        claim = _get_field(f, "claim") or ""
        years = re.findall(r'\b(19[5-9]\d|20[0-3]\d)\b', claim)
        if years and len(years) >= 2:
            dated_claims.append({
                "fact_id": _get_field(f, "fact_id"),
                "years":   sorted(int(y) for y in years),
                "claim":   claim[:100],
            })

    # If we have 3+ facts with overlapping date ranges, flag it
    if len(dated_claims) >= 3:
        return [{
            "type":        "date_overlap_possible",
            "description": f"Multiple simultaneous organizational affiliations detected across {len(dated_claims)} facts",
            "fact_ids":    [d["fact_id"] for d in dated_claims[:3]],
            "severity":    "LOW",
        }]
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Affiliation Heuristics
# ─────────────────────────────────────────────────────────────────────────────

def detect_affiliation_heuristics(entities: list, relationships: list) -> List[dict]:
    """
    Detect suspicious affiliation patterns in the entity graph.

    Checks:
      1. Shell company indicators (LLC/Ltd + no Person connection)
      2. Undisclosed fund connections (Fund entity with no Person link)
      3. Circular ownership (A → B → A in relationships)
    """
    flags = []

    # Check 1: Organizations with no Person connection
    org_ids  = {_get_field(e, "entity_id") for e in entities if _get_field(e, "entity_type") in ("Organization", "Fund")}
    connected_orgs = set()
    for r in relationships:
        if _get_field(r, "rel_type") in ("WORKS_AT", "FOUNDED", "CONTROLS", "MANAGED", "BOARD_MEMBER"):
            connected_orgs.add(_get_field(r, "to_id"))

    unconnected = org_ids - connected_orgs
    if unconnected:
        flags.append({
            "type":        "unconnected_organization",
            "description": f"{len(unconnected)} organization(s) found with no Person connection — possible undisclosed affiliation",
            "entity_ids":  list(unconnected)[:3],
            "severity":    "MEDIUM",
        })

    # Check 2: Shell company name patterns
    shell_patterns = [r'\bllc\b', r'\bltd\b', r'holdings?\b', r'capital\s+group', r'investment\s+co']
    for entity in entities:
        name = (_get_field(entity, "name") or "").lower()
        if any(re.search(p, name) for p in shell_patterns):
            attrs = _get_field(entity, "attributes") or {}
            if not attrs.get("jurisdiction") and not attrs.get("founded"):
                flags.append({
                    "type":        "possible_shell_entity",
                    "description": f"Entity '{_get_field(entity, 'name')}' matches shell company pattern with no jurisdiction/founding data",
                    "entity_ids":  [_get_field(entity, "entity_id")],
                    "severity":    "LOW",
                })

    # Check 3: Circular relationships
    flags.extend(_detect_circular_ownership(relationships))

    return flags


def _detect_circular_ownership(relationships: list) -> List[dict]:
    """Simple 2-hop circular ownership detection (A→B→A)."""
    edge_set = set()
    for r in relationships:
        if _get_field(r, "rel_type") in ("CONTROLS", "INVESTED_IN", "MANAGED"):
            edge_set.add((_get_field(r, "from_id"), _get_field(r, "to_id")))

    circular = []
    for (a, b) in edge_set:
        if (b, a) in edge_set:
            circular.append({"from": a, "to": b})

    if circular:
        return [{
            "type":        "circular_ownership",
            "description": f"Circular ownership/control detected: {len(circular)} pair(s) with mutual control relationships",
            "entity_ids":  [c["from"] for c in circular[:2]],
            "severity":    "HIGH",
        }]
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _contains_edu_keyword(text: str) -> bool:
    keywords = ["university", "college", "school", "degree", "bachelor", "master", "phd", "mba", "graduated"]
    return any(k in text.lower() for k in keywords)


def _extract_institution(text: str) -> str:
    """Extract likely institution name from claim text."""
    patterns = [r'(?:at|from|of)\s+([A-Z][a-zA-Z\s]+(?:University|College|School|Institute))']
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return ""


def _extract_dollar_amounts(text: str) -> List[float]:
    """Extract dollar amounts (millions/billions) from text."""
    amounts = []
    # Match: $X million/billion or $X.Xm/b
    patterns = [
        (r'\$(\d+(?:\.\d+)?)\s*billion', 1_000_000_000),
        (r'\$(\d+(?:\.\d+)?)\s*million', 1_000_000),
        (r'\$(\d+(?:\.\d+)?)[bB]',       1_000_000_000),
        (r'\$(\d+(?:\.\d+)?)[mM]',       1_000_000),
    ]
    for pattern, multiplier in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            amounts.append(float(match.group(1)) * multiplier)
    return amounts
```

### Update `agents/risk_evaluator.py` — add inconsistency detection

```python
# In run_risk_evaluator() else branch, BEFORE generating flags from LLM:
from utils.inconsistency_detector import detect_inconsistencies, detect_affiliation_heuristics

# Run deterministic checks first
rule_inconsistencies = detect_inconsistencies([f.model_dump() for f in usable_facts])
affil_flags = detect_affiliation_heuristics(
    [e.model_dump() for e in state["entities"]],
    [r.model_dump() for r in state["relationships"]],
)

# Add to state
all_inconsistencies = rule_inconsistencies + affil_flags

# Include inconsistency context in LLM prompt:
# Append to user_msg:
inconsistency_text = json.dumps(all_inconsistencies[:5], indent=2) if all_inconsistencies else "None detected"
user_msg += f"\n\nDETERMINISTIC INCONSISTENCIES ALREADY FOUND:\n{inconsistency_text}\nDo not duplicate these — generate additional LLM-identified risks only."

# In return dict, add:
return {"risk_flags": flags, "inconsistencies": all_inconsistencies}
```

---

## Section 12 — Run-Scoped Relationship Isolation

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 12 — run-scoped relationships in Neo4j`

### Update `graph/neo4j_manager.py` — add run_id to relationships

```python
# Replace write_relationships() with the run-scoped version:

def write_relationships(relationships: List[dict], run_id: str) -> int:
    """
    Write relationships to Neo4j with run_id scoping.

    Phase 3 change: run_id is now a required parameter and is set as a
    property on every relationship. This allows:
      - Querying relationships for a specific run
      - Cleaning up relationships from a specific run
      - Visualizing only the current run's graph

    Note: MERGE is still used (idempotent) but the run_id property ensures
    that re-running with the same entities creates new run-scoped relationships.
    """
    driver = get_driver()
    count  = 0

    with driver.session(database=NEO4J_DATABASE) as session:
        for rel in relationships:
            try:
                # Build Cypher that matches nodes by entity_id AND sets run_id on the rel
                cypher = (
                    f"MATCH (a {{entity_id: $from_id}}), (b {{entity_id: $to_id}}) "
                    f"MERGE (a)-[r:{rel['rel_type']}]->(b) "
                    f"SET r.run_id = $run_id, "
                    f"    r.confidence = $confidence, "
                    f"    r.source_fact_id = $source_fact_id, "
                    f"    r.created_at = datetime() "
                )
                session.run(cypher, {
                    "from_id":       rel.get("from_id"),
                    "to_id":         rel.get("to_id"),
                    "run_id":        run_id,
                    "confidence":    rel.get("confidence", 0.5),
                    "source_fact_id": rel.get("source_fact_id", ""),
                })
                count += 1
            except Exception as e:
                logger.error(f"[Neo4j] Relationship write failed: {rel} — {e}")

    logger.info(f"[Neo4j] Wrote {count}/{len(relationships)} relationships for run_id={run_id}")
    return count


def fetch_graph_for_run(run_id: str) -> dict:
    """
    Fetch all nodes and edges for a specific run_id.
    Nodes are matched by run_id property.
    Relationships are matched by run_id property on the relationship itself.
    """
    driver = get_driver()
    nodes  = []
    edges  = []

    with driver.session(database=NEO4J_DATABASE) as session:
        # Nodes scoped to run_id
        result = session.run("MATCH (n {run_id: $run_id}) RETURN n", run_id=run_id)
        for record in result:
            nodes.append(dict(record["n"]))

        # Relationships scoped to run_id (property on the relationship)
        result = session.run(
            "MATCH (a)-[r {run_id: $run_id}]->(b) "
            "RETURN a.entity_id AS from_id, b.entity_id AS to_id, "
            "       type(r) AS rel_type, r.confidence AS confidence, "
            "       r.source_fact_id AS source_fact_id",
            run_id=run_id,
        )
        for record in result:
            edges.append(dict(record))

    return {"nodes": nodes, "edges": edges}
```

---

## Section 13 — Graph Artifact Persistence

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 13 — graph artifact persistence`

### Update `agents/graph_builder.py` — save HTML artifact to disk

```python
# In run_graph_builder(), after generating graph_html, add:

from config import GRAPH_ARTIFACT_DIR
import os

# Save artifact to disk
os.makedirs(GRAPH_ARTIFACT_DIR, exist_ok=True)
artifact_path = os.path.join(GRAPH_ARTIFACT_DIR, f"{run_id}.html")
with open(artifact_path, "w") as f:
    f.write(graph_html)

logger.info(f"[GraphBuilder] Artifact saved: {artifact_path}")

# Add to return dict:
return {
    "graph_html":     graph_html,
    "artifact_path":  artifact_path,
}
```

### Add `artifact_path` to `AgentState`

```python
# In state/agent_state.py, add:
artifact_path: str   # Path to the saved HTML graph artifact for this run
```

### Add `artifact_path` default to `make_initial_state()`

```python
"artifact_path": "",
```

---

## Section 14 — Source Citations with Evidence Fields

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 14 — source citations`

### Update `state/agent_state.py` — add Citation model

```python
from typing import Optional

class Citation(BaseModel):
    """
    A source citation linked to a specific fact.
    Used for clickable source links in the UI.
    """
    fact_id:       str
    url:           str
    domain:        str
    title:         str
    snippet:       str           # The specific text from source that supports the claim
    accessed_at:   str           # ISO timestamp when this source was retrieved
    confidence:    float         # Source trust score (from domain_trust table)

# Add to AgentState:
citations: Annotated[List[Citation], operator.add]

# Add to make_initial_state():
"citations": [],
```

### `utils/citation_builder.py`

```python
"""
citation_builder.py — Build Citation objects from extracted facts and search results.

For each extracted fact, finds the matching search result and creates a Citation
with the exact source URL, domain, snippet, and confidence.

Architecture position: called by agents/deep_dive_agent.py after fact extraction.
"""
import logging
from datetime import datetime, timezone
from typing import List

logger = logging.getLogger(__name__)


def build_citations(facts: list, raw_results: list) -> List[dict]:
    """
    Build citations by matching each fact's source_url to a raw search result.

    Args:
        facts:       List of Fact dicts (with source_url field)
        raw_results: List of raw search result dicts (from Scout)

    Returns:
        List of Citation dicts
    """
    # Index raw results by URL for fast lookup
    results_by_url = {}
    for r in raw_results:
        url = r.get("url", "")
        if url:
            results_by_url[url] = r

    citations = []
    now = datetime.now(timezone.utc).isoformat()

    for fact in facts:
        url = fact.get("source_url", "") if isinstance(fact, dict) else getattr(fact, "source_url", "")
        if not url:
            continue

        result = results_by_url.get(url)
        domain = fact.get("source_domain", "") if isinstance(fact, dict) else getattr(fact, "source_domain", "")
        snippet = ""

        if result:
            # Use the raw_source_snippet if available (from DeepDive extraction)
            raw_snip = fact.get("raw_source_snippet", "") if isinstance(fact, dict) else getattr(fact, "raw_source_snippet", "")
            snippet  = raw_snip or result.get("content", "")[:300]
            title    = result.get("title", domain)
        else:
            title   = domain
            snippet = fact.get("raw_source_snippet", "") if isinstance(fact, dict) else getattr(fact, "raw_source_snippet", "")

        from evaluation.confidence_scorer import get_domain_trust
        conf = get_domain_trust(domain)

        fact_id = fact.get("fact_id", "") if isinstance(fact, dict) else getattr(fact, "fact_id", "")

        citations.append({
            "fact_id":     fact_id,
            "url":         url,
            "domain":      domain,
            "title":       title,
            "snippet":     snippet[:400],
            "accessed_at": now,
            "confidence":  conf,
        })

    logger.info(f"[CitationBuilder] Built {len(citations)} citations for {len(facts)} facts")
    return citations
```

### Update `agents/deep_dive_agent.py` — build citations

```python
# After building facts, add:
from utils.citation_builder import build_citations

citation_dicts = build_citations(facts_as_dicts, state.get("raw_results", []))
citations = []
for c in citation_dicts:
    try:
        citations.append(Citation(**c))
    except Exception as e:
        logger.warning(f"[DeepDive] Invalid citation: {e}")

# Add to return dict:
"citations": citations,
```

---

## Section 15 — Systematic Fallback Logic (All Nodes)

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 15 — NodeResult wrapper and systematic fallback`

### `utils/node_result.py`

```python
"""
node_result.py — Systematic node fallback wrapper for LangGraph nodes.

Every node in the pipeline is wrapped with @safe_node, which:
  1. Catches all unhandled exceptions
  2. Logs the failure to the audit log
  3. Returns a safe partial state (empty lists, defaults) instead of crashing
  4. Allows the pipeline to continue to the next node

This ensures that a single node failure (e.g. Tavily API down, Haiku JSON error)
doesn't terminate the entire pipeline run.

Architecture position: decorator applied to all agent functions in Phase 3.
"""
import functools
import logging
from typing import Callable

logger = logging.getLogger(__name__)


# Default empty state returned when a node fails completely
NODE_FALLBACK_DEFAULTS = {
    "supervisor_plan":    {"research_plan": [], "gaps_remaining": [], "loop_count": 1},
    "scout_agent":        {"raw_results": []},
    "deep_dive":          {"extracted_facts": [], "entities": [], "relationships": [],
                           "biographical_coverage": [], "professional_coverage": [],
                           "financial_coverage": [], "behavioral_coverage": [],
                           "coverage_scores": {}, "citations": []},
    "supervisor_reflect": {"research_quality": 0.5, "gaps_remaining": []},
    "risk_evaluator":     {"risk_flags": [], "inconsistencies": []},
    "graph_builder":      {"graph_html": "<p>Graph unavailable</p>", "artifact_path": ""},
    "supervisor_synth":   {"final_report": "Report generation failed — see logs for details."},
}


def safe_node(node_name: str):
    """
    Decorator: wrap a LangGraph node function with systematic fallback logic.

    Usage:
        @safe_node("scout_agent")
        def run_scout(state): ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(state: dict) -> dict:
            from utils.audit_logger import log_node_start, log_node_complete, log_node_failure
            log_node_start(node_name)
            try:
                result = func(state)
                summary = {k: (len(v) if isinstance(v, list) else v)
                           for k, v in result.items() if not isinstance(v, str) or len(v) < 50}
                log_node_complete(node_name, summary)
                return result
            except Exception as e:
                logger.error(f"[{node_name}] UNCAUGHT EXCEPTION: {e}", exc_info=True)
                fallback = NODE_FALLBACK_DEFAULTS.get(node_name, {})
                log_node_failure(node_name, str(e), fallback)
                return fallback

        return wrapper
    return decorator
```

### Apply `@safe_node` to all agent functions

```python
# In agents/supervisor.py:
from utils.node_result import safe_node

@safe_node("supervisor_plan")
@traceable(name="supervisor_plan", run_type="chain")
def supervisor_plan(state): ...

@safe_node("supervisor_reflect")
@traceable(name="supervisor_reflect", run_type="chain")
def supervisor_reflect(state): ...

@safe_node("supervisor_synth")
@traceable(name="supervisor_synth", run_type="chain")
def supervisor_synthesise(state): ...

# In agents/scout_agent.py:
@safe_node("scout_agent")
@traceable(name="scout_agent", run_type="chain")
def run_scout(state): ...

# In agents/deep_dive_agent.py:
@safe_node("deep_dive")
@traceable(name="deep_dive", run_type="chain")
def run_deep_dive(state): ...

# In agents/risk_evaluator.py:
@safe_node("risk_evaluator")
@traceable(name="risk_evaluator", run_type="chain")
def run_risk_evaluator(state): ...

# In agents/graph_builder.py:
@safe_node("graph_builder")
@traceable(name="graph_builder", run_type="chain")
def run_graph_builder(state): ...
```

---

## Section 16 — D3.js Interactive Graph Visualization

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 16 — replace vis.js with D3.js force-directed graph`

### Replace `graph/visualizer.py` entirely

```python
"""
visualizer.py — Phase 3: D3.js force-directed interactive identity graph.

Replaces the Phase 1/2 vis.js implementation with a production-quality
D3.js force-directed graph with:
  - Color-coded nodes by entity type (Person=blue, Organization=orange, Fund=green, etc.)
  - Edge labels showing relationship type
  - Hover tooltips with entity attributes and confidence scores
  - Click-to-expand node details panel
  - Zoom + pan navigation
  - Run-isolated: only shows entities/relationships for the current run_id
  - Dark navy theme matching DeepTrace brand

Architecture position: called by graph_builder agent and Streamlit frontend.
"""
import json
import logging

logger = logging.getLogger(__name__)

# Color scheme per entity type
ENTITY_COLORS = {
    "Person":       "#4A90D9",    # Blue
    "Organization": "#E8813A",    # Orange
    "Fund":         "#50C878",    # Green
    "Location":     "#9B59B6",    # Purple
    "Event":        "#E74C3C",    # Red
    "Filing":       "#F39C12",    # Yellow
    "default":      "#95A5A6",    # Grey
}

# Edge color per relationship type
EDGE_COLORS = {
    "WORKS_AT":      "#4A90D9",
    "INVESTED_IN":   "#50C878",
    "CONNECTED_TO":  "#95A5A6",
    "FILED_WITH":    "#F39C12",
    "FOUNDED":       "#E8813A",
    "AFFILIATED_WITH":"#9B59B6",
    "BOARD_MEMBER":  "#E74C3C",
    "MANAGED":       "#1ABC9C",
    "CONTROLS":      "#E74C3C",
    "default":       "#7F8C8D",
}


def generate_d3_html(nodes: list, edges: list, title: str = "Identity Graph") -> str:
    """
    Generate a self-contained HTML file with an interactive D3.js force-directed graph.

    Args:
        nodes: List of entity dicts (from Neo4j or state["entities"])
        edges: List of relationship dicts (from Neo4j or state["relationships"])
        title: Graph title shown in header

    Returns:
        Complete HTML string (self-contained, no external dependencies except D3 CDN)
    """
    if not nodes:
        return _empty_graph_html(title)

    # Build D3-compatible data structures
    d3_nodes = []
    for node in nodes:
        etype = node.get("entity_type", "default")
        d3_nodes.append({
            "id":         node.get("entity_id", node.get("name", "")),
            "name":       node.get("name", "Unknown"),
            "type":       etype,
            "color":      ENTITY_COLORS.get(etype, ENTITY_COLORS["default"]),
            "confidence": node.get("confidence", 0.5),
            "attributes": node.get("attributes", {}),
        })

    # Build node ID set for edge validation
    node_ids = {n["id"] for n in d3_nodes}

    d3_edges = []
    for edge in edges:
        from_id  = edge.get("from_id", "")
        to_id    = edge.get("to_id",   "")
        rel_type = edge.get("rel_type", "CONNECTED_TO")
        if from_id in node_ids and to_id in node_ids:
            d3_edges.append({
                "source":     from_id,
                "target":     to_id,
                "type":       rel_type,
                "color":      EDGE_COLORS.get(rel_type, EDGE_COLORS["default"]),
                "confidence": edge.get("confidence", 0.5),
                "label":      rel_type.replace("_", " ").title(),
            })

    graph_data = json.dumps({"nodes": d3_nodes, "links": d3_edges})
    node_count = len(d3_nodes)
    edge_count = len(d3_edges)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: #0D1B2A;
      font-family: 'Segoe UI', system-ui, sans-serif;
      color: #E8EDF2;
      overflow: hidden;
    }}
    #header {{
      position: fixed; top: 0; left: 0; right: 0;
      background: linear-gradient(135deg, #0D1B2A 0%, #1A2D45 100%);
      border-bottom: 1px solid #2A4A6A;
      padding: 12px 20px;
      display: flex; align-items: center; justify-content: space-between;
      z-index: 100;
    }}
    #header h1 {{ font-size: 16px; font-weight: 600; color: #4A90D9; }}
    #stats {{ font-size: 12px; color: #7A9AB5; }}
    #graph-container {{
      position: fixed; top: 52px; left: 0; right: 320px; bottom: 0;
    }}
    svg {{ width: 100%; height: 100%; }}
    .node circle {{
      stroke: rgba(255,255,255,0.2);
      stroke-width: 2px;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .node circle:hover {{
      stroke: #ffffff;
      stroke-width: 3px;
      filter: brightness(1.3);
    }}
    .node.selected circle {{
      stroke: #ffffff;
      stroke-width: 3px;
    }}
    .node text {{
      font-size: 11px;
      fill: #E8EDF2;
      pointer-events: none;
      text-shadow: 0 1px 3px rgba(0,0,0,0.8);
    }}
    .link {{
      stroke-opacity: 0.6;
      transition: stroke-opacity 0.2s;
    }}
    .link:hover {{ stroke-opacity: 1.0; }}
    .link-label {{
      font-size: 9px;
      fill: #7A9AB5;
      pointer-events: none;
    }}
    #tooltip {{
      position: fixed;
      background: rgba(13,27,42,0.95);
      border: 1px solid #2A4A6A;
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 12px;
      max-width: 240px;
      pointer-events: none;
      z-index: 200;
      display: none;
      backdrop-filter: blur(8px);
    }}
    #tooltip .tooltip-title {{ font-weight: 600; color: #4A90D9; margin-bottom: 6px; font-size: 13px; }}
    #tooltip .tooltip-row {{ color: #A8C0D0; margin: 3px 0; }}
    #detail-panel {{
      position: fixed; top: 52px; right: 0; width: 320px; bottom: 0;
      background: #0D1B2A;
      border-left: 1px solid #2A4A6A;
      overflow-y: auto;
      padding: 16px;
    }}
    #detail-panel h2 {{ font-size: 14px; color: #4A90D9; margin-bottom: 12px; }}
    .detail-empty {{ color: #4A6A8A; font-size: 12px; text-align: center; margin-top: 60px; }}
    .detail-card {{
      background: #1A2D45;
      border: 1px solid #2A4A6A;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 10px;
    }}
    .detail-card .card-title {{ font-weight: 600; color: #E8EDF2; font-size: 13px; margin-bottom: 6px; }}
    .detail-card .card-type {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 10px;
      font-size: 10px;
      font-weight: 600;
      margin-bottom: 8px;
    }}
    .detail-card .card-row {{ color: #A8C0D0; font-size: 11px; margin: 4px 0; }}
    .detail-card .card-attr {{ color: #7A9AB5; font-size: 10px; margin: 2px 0; }}
    .conf-bar {{
      height: 4px;
      background: #1A2D45;
      border-radius: 2px;
      margin-top: 8px;
      overflow: hidden;
    }}
    .conf-fill {{
      height: 100%;
      border-radius: 2px;
      background: linear-gradient(90deg, #E74C3C, #F39C12, #50C878);
    }}
    #legend {{
      position: fixed; bottom: 16px; left: 16px;
      background: rgba(13,27,42,0.9);
      border: 1px solid #2A4A6A;
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 11px;
    }}
    .legend-item {{ display: flex; align-items: center; margin: 3px 0; gap: 8px; color: #A8C0D0; }}
    .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
    #controls {{
      position: fixed; bottom: 16px; right: 336px;
      display: flex; gap: 8px;
    }}
    .ctrl-btn {{
      background: rgba(13,27,42,0.9);
      border: 1px solid #2A4A6A;
      color: #A8C0D0;
      padding: 6px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      transition: all 0.2s;
    }}
    .ctrl-btn:hover {{ background: #1A2D45; color: #E8EDF2; }}
  </style>
</head>
<body>
  <div id="header">
    <h1>🕵️ {title}</h1>
    <span id="stats">{node_count} entities · {edge_count} relationships</span>
  </div>

  <div id="graph-container"><svg id="graph-svg"></svg></div>

  <div id="tooltip"></div>

  <div id="detail-panel">
    <h2>Entity Details</h2>
    <div id="detail-content" class="detail-empty">Click a node to explore</div>
  </div>

  <div id="legend">
    <div style="font-weight:600;color:#4A90D9;margin-bottom:6px;font-size:11px;">Entity Types</div>
    <div class="legend-item"><div class="legend-dot" style="background:#4A90D9"></div>Person</div>
    <div class="legend-item"><div class="legend-dot" style="background:#E8813A"></div>Organization</div>
    <div class="legend-item"><div class="legend-dot" style="background:#50C878"></div>Fund</div>
    <div class="legend-item"><div class="legend-dot" style="background:#9B59B6"></div>Location</div>
    <div class="legend-item"><div class="legend-dot" style="background:#E74C3C"></div>Event</div>
    <div class="legend-item"><div class="legend-dot" style="background:#F39C12"></div>Filing</div>
  </div>

  <div id="controls">
    <button class="ctrl-btn" onclick="resetZoom()">⟳ Reset</button>
    <button class="ctrl-btn" onclick="toggleLabels()">🏷 Labels</button>
  </div>

<script>
const GRAPH_DATA = {graph_data};
let showLabels = true;

const container = document.getElementById('graph-container');
const width     = container.clientWidth;
const height    = container.clientHeight;

const svg = d3.select('#graph-svg')
  .attr('viewBox', [0, 0, width, height]);

const g = svg.append('g');

// Zoom behavior
const zoom = d3.zoom()
  .scaleExtent([0.2, 4])
  .on('zoom', (event) => g.attr('transform', event.transform));

svg.call(zoom);

// Arrow marker definitions
const defs = svg.append('defs');
const arrowTypes = [...new Set(GRAPH_DATA.links.map(l => l.type))];
arrowTypes.forEach(type => {{
  const color = GRAPH_DATA.links.find(l => l.type === type)?.color || '#7F8C8D';
  defs.append('marker')
    .attr('id', `arrow-${{type}}`)
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 22)
    .attr('refY', 0)
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', color);
}});

// Node radius by type
const nodeRadius = (type) => {{
  const sizes = {{ Person: 18, Organization: 16, Fund: 16, Location: 12, Event: 12, Filing: 12 }};
  return sizes[type] || 12;
}};

// Force simulation
const simulation = d3.forceSimulation(GRAPH_DATA.nodes)
  .force('link', d3.forceLink(GRAPH_DATA.links).id(d => d.id).distance(120).strength(0.5))
  .force('charge', d3.forceManyBody().strength(-400))
  .force('center', d3.forceCenter(width / 2, height / 2))
  .force('collision', d3.forceCollide().radius(d => nodeRadius(d.type) + 10));

// Draw edges
const link = g.append('g').attr('class', 'links')
  .selectAll('line')
  .data(GRAPH_DATA.links)
  .join('line')
  .attr('class', 'link')
  .attr('stroke', d => d.color)
  .attr('stroke-width', d => 1 + d.confidence * 2)
  .attr('marker-end', d => `url(#arrow-${{d.type}})`);

// Edge labels
const linkLabel = g.append('g').attr('class', 'link-labels')
  .selectAll('text')
  .data(GRAPH_DATA.links)
  .join('text')
  .attr('class', 'link-label')
  .text(d => d.label);

// Draw nodes
const node = g.append('g').attr('class', 'nodes')
  .selectAll('g')
  .data(GRAPH_DATA.nodes)
  .join('g')
  .attr('class', 'node')
  .call(d3.drag()
    .on('start', dragStart)
    .on('drag',  dragging)
    .on('end',   dragEnd)
  )
  .on('click', (event, d) => {{
    event.stopPropagation();
    selectNode(d);
  }})
  .on('mouseover', (event, d) => showTooltip(event, d))
  .on('mouseout',  () => hideTooltip());

node.append('circle')
  .attr('r', d => nodeRadius(d.type))
  .attr('fill', d => d.color)
  .attr('fill-opacity', 0.9);

// Node icons (emoji)
const typeIcons = {{ Person: '👤', Organization: '🏢', Fund: '💰', Location: '📍', Event: '📅', Filing: '📄' }};
node.append('text')
  .attr('text-anchor', 'middle')
  .attr('dy', '0.35em')
  .attr('font-size', d => nodeRadius(d.type) * 0.9)
  .text(d => typeIcons[d.type] || '◆');

// Node name labels
node.append('text')
  .attr('class', 'node-label')
  .attr('text-anchor', 'middle')
  .attr('dy', d => nodeRadius(d.type) + 14)
  .attr('font-size', 10)
  .text(d => d.name.length > 18 ? d.name.substring(0, 16) + '…' : d.name);

// Simulation tick
simulation.on('tick', () => {{
  link
    .attr('x1', d => d.source.x)
    .attr('y1', d => d.source.y)
    .attr('x2', d => d.target.x)
    .attr('y2', d => d.target.y);

  linkLabel
    .attr('x', d => (d.source.x + d.target.x) / 2)
    .attr('y', d => (d.source.y + d.target.y) / 2);

  node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
}});

// Drag handlers
function dragStart(event, d) {{
  if (!event.active) simulation.alphaTarget(0.3).restart();
  d.fx = d.x; d.fy = d.y;
}}
function dragging(event, d) {{ d.fx = event.x; d.fy = event.y; }}
function dragEnd(event, d) {{
  if (!event.active) simulation.alphaTarget(0);
  d.fx = null; d.fy = null;
}}

// Tooltip
function showTooltip(event, d) {{
  const conf = Math.round(d.confidence * 100);
  const tooltip = document.getElementById('tooltip');
  tooltip.innerHTML = `
    <div class="tooltip-title">${{d.name}}</div>
    <div class="tooltip-row">Type: ${{d.type}}</div>
    <div class="tooltip-row">Confidence: ${{conf}}%</div>
    ${{Object.entries(d.attributes || {{}}).slice(0,3).map(([k,v]) =>
      `<div class="tooltip-row">${{k}}: ${{v}}</div>`).join('')}}
  `;
  tooltip.style.display = 'block';
  tooltip.style.left = (event.clientX + 16) + 'px';
  tooltip.style.top  = (event.clientY - 20) + 'px';
}}
function hideTooltip() {{
  document.getElementById('tooltip').style.display = 'none';
}}

// Node detail panel
function selectNode(d) {{
  document.querySelectorAll('.node.selected').forEach(n => n.classList.remove('selected'));
  // Find and add selected class
  node.filter(n => n.id === d.id).classed('selected', true);

  const conf = Math.round(d.confidence * 100);
  const attrs = Object.entries(d.attributes || {{}});
  const color = d.color;

  // Find connected nodes
  const connectedLinks = GRAPH_DATA.links.filter(l =>
    (typeof l.source === 'object' ? l.source.id : l.source) === d.id ||
    (typeof l.target === 'object' ? l.target.id : l.target) === d.id
  );

  const panel = document.getElementById('detail-content');
  panel.innerHTML = `
    <div class="detail-card">
      <div class="card-title">${{d.name}}</div>
      <div class="card-type" style="background:${{color}}22;color:${{color}}">${{d.type}}</div>
      <div class="card-row">Confidence: ${{conf}}%</div>
      <div class="conf-bar"><div class="conf-fill" style="width:${{conf}}%"></div></div>
      ${{attrs.length > 0 ? '<div style="margin-top:8px;font-size:10px;color:#4A6A8A;font-weight:600">ATTRIBUTES</div>' : ''}}
      ${{attrs.map(([k,v]) => `<div class="card-attr">${{k}}: ${{v}}</div>`).join('')}}
    </div>
    ${{connectedLinks.length > 0 ? `
    <div style="font-size:11px;color:#4A6A8A;font-weight:600;margin:8px 0 4px">CONNECTIONS (${{connectedLinks.length}})</div>
    ${{connectedLinks.map(l => {{
      const isSource = (typeof l.source === 'object' ? l.source.id : l.source) === d.id;
      const other = isSource ? l.target : l.source;
      const otherName = typeof other === 'object' ? other.name : other;
      const arrow = isSource ? '→' : '←';
      return `<div class="detail-card" style="padding:8px">
        <div style="font-size:11px;color:#A8C0D0">${{arrow}} ${{l.label}}</div>
        <div style="font-size:12px;color:#E8EDF2">${{otherName}}</div>
        <div style="font-size:10px;color:#7A9AB5">confidence: ${{Math.round(l.confidence*100)}}%</div>
      </div>`;
    }}).join('')}}` : ''}}
  `;
}}

// Click on background deselects
svg.on('click', () => {{
  document.querySelectorAll('.node.selected').forEach(n => n.classList.remove('selected'));
  document.getElementById('detail-content').innerHTML = '<div class="detail-empty">Click a node to explore</div>';
}});

function resetZoom() {{
  svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
}}

function toggleLabels() {{
  showLabels = !showLabels;
  d3.selectAll('.node-label').style('display', showLabels ? 'block' : 'none');
  d3.selectAll('.link-label').style('display', showLabels ? 'block' : 'none');
}}
</script>
</body>
</html>"""


def _empty_graph_html(title: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>body{{background:#0D1B2A;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;font-family:sans-serif;}}</style>
</head><body>
<p style="color:#4A6A8A;font-size:14px">No entities found for "{title}"</p>
</body></html>"""
```

### Update `agents/graph_builder.py` — use new D3 visualizer

```python
# Replace:
# from graph.visualizer import generate_pyvis_html
# graph_html = generate_pyvis_html(entities, relationships)

# With:
from graph.visualizer import generate_d3_html
graph_html = generate_d3_html(canonical_entities, canonical_rels, title=f"Identity Graph: {state['target_name']}")
```

---

## Section 17 — PDF Export

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 17 — PDF export`

### `utils/report_exporter.py`

```python
"""
report_exporter.py — Export pipeline reports to PDF.

Converts the final_report markdown string + risk flags + citations into
a styled HTML document, then uses weasyprint to render it as a PDF.

Architecture position: called from Streamlit frontend/pages/03_report.py.
"""
import logging
import os
import tempfile
from datetime import datetime

logger = logging.getLogger(__name__)


def export_report_pdf(
    target_name:  str,
    final_report: str,
    risk_flags:   list,
    citations:    list,
    run_id:       str,
) -> bytes:
    """
    Generate a PDF report from pipeline results.

    Returns:
        PDF as bytes (for Streamlit st.download_button)

    Raises:
        RuntimeError if weasyprint is not installed or PDF generation fails
    """
    try:
        from weasyprint import HTML as WeasyprintHTML
    except ImportError:
        raise RuntimeError(
            "weasyprint is required for PDF export. "
            "Install with: pip install weasyprint --break-system-packages"
        )

    import markdown as md_lib
    html_content = _build_pdf_html(target_name, final_report, risk_flags, citations, run_id)

    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False) as f:
        f.write(html_content)
        tmp_path = f.name

    try:
        pdf_bytes = WeasyprintHTML(filename=tmp_path).write_pdf()
        return pdf_bytes
    finally:
        os.unlink(tmp_path)


def _severity_color(severity: str) -> str:
    colors = {
        "CRITICAL": "#E74C3C",
        "HIGH":     "#E8813A",
        "MEDIUM":   "#F39C12",
        "LOW":      "#50C878",
    }
    return colors.get(severity, "#7F8C8D")


def _build_pdf_html(target_name, final_report, risk_flags, citations, run_id) -> str:
    """Build styled HTML string for PDF rendering."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Convert markdown report to HTML
    try:
        import markdown
        report_html = markdown.markdown(final_report, extensions=["tables"])
    except ImportError:
        # Fallback: wrap in <pre> if markdown library not available
        report_html = f"<pre>{final_report}</pre>"

    # Build risk flags table
    flags_html = ""
    if risk_flags:
        rows = ""
        for flag in risk_flags:
            sev   = flag.get("severity", "LOW") if isinstance(flag, dict) else getattr(flag, "severity", "LOW")
            title = flag.get("title", "") if isinstance(flag, dict) else getattr(flag, "title", "")
            desc  = flag.get("description", "") if isinstance(flag, dict) else getattr(flag, "description", "")
            conf  = flag.get("confidence", 0) if isinstance(flag, dict) else getattr(flag, "confidence", 0)
            color = _severity_color(sev)
            rows += f"""<tr>
              <td><span style="background:{color};color:white;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:bold">{sev}</span></td>
              <td style="font-weight:600">{title}</td>
              <td>{desc}</td>
              <td>{int(conf*100)}%</td>
            </tr>"""
        flags_html = f"""
        <h2>Risk Flags</h2>
        <table>
          <thead><tr><th>Severity</th><th>Title</th><th>Description</th><th>Confidence</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>"""

    # Build citations section
    citations_html = ""
    if citations:
        items = ""
        for c in citations[:20]:   # Cap at 20 citations
            url   = c.get("url", "") if isinstance(c, dict) else getattr(c, "url", "")
            title = c.get("title", url) if isinstance(c, dict) else getattr(c, "title", url)
            snip  = c.get("snippet", "") if isinstance(c, dict) else getattr(c, "snippet", "")
            conf  = c.get("confidence", 0) if isinstance(c, dict) else getattr(c, "confidence", 0)
            items += f"""<div class="citation">
              <a href="{url}">{title}</a>
              <div class="citation-snippet">{snip[:200]}</div>
              <div class="citation-meta">Source confidence: {int(conf*100)}% · <a href="{url}">{url[:60]}</a></div>
            </div>"""
        citations_html = f"<h2>Source References</h2>{items}"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #1A2D45; font-size: 12px; line-height: 1.6; }}
  h1 {{ color: #0D1B2A; font-size: 22px; border-bottom: 3px solid #4A90D9; padding-bottom: 8px; }}
  h2 {{ color: #0D1B2A; font-size: 16px; margin-top: 28px; border-bottom: 1px solid #DEE5ED; padding-bottom: 4px; }}
  h3 {{ color: #2A4A6A; font-size: 13px; }}
  .meta {{ color: #7A9AB5; font-size: 10px; margin-bottom: 24px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 11px; }}
  th {{ background: #1A2D45; color: white; padding: 8px 10px; text-align: left; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #DEE5ED; vertical-align: top; }}
  tr:nth-child(even) td {{ background: #F5F8FC; }}
  .citation {{ margin: 12px 0; padding: 10px; border-left: 3px solid #4A90D9; background: #F5F8FC; }}
  .citation a {{ color: #4A90D9; font-weight: 600; text-decoration: none; }}
  .citation-snippet {{ color: #4A6A8A; font-size: 10px; margin: 4px 0; }}
  .citation-meta {{ color: #7A9AB5; font-size: 10px; }}
  ul {{ padding-left: 20px; }}
  li {{ margin: 4px 0; }}
  p {{ margin: 8px 0; }}
  .page-break {{ page-break-before: always; }}
</style>
</head>
<body>
  <h1>DeepTrace Intelligence Report</h1>
  <div class="meta">
    Target: <strong>{target_name}</strong> ·
    Generated: {now} ·
    Run ID: {run_id}
  </div>

  {report_html}
  {flags_html}
  <div class="page-break"></div>
  {citations_html}
</body>
</html>"""
```

### Add to `requirements.txt`

```
weasyprint==61.2
markdown==3.5.1
```

---

## Section 18 — Updated Streamlit UI (Citations + Export + Graph)

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 18 — update Streamlit pages`

### Update `frontend/pages/03_report.py` — citations with clickable links + PDF export

```python
"""
03_report.py — Phase 3: Report page with citations, clickable links, PDF export.
"""
import streamlit as st

st.set_page_config(page_title="DeepTrace — Report", layout="wide")
st.title("📋 Intelligence Report")

if "final_state" not in st.session_state or not st.session_state.final_state:
    st.info("Run a research pipeline from the Research page first.")
    st.stop()

state = st.session_state.final_state

# ── Report text ───────────────────────────────────────────────────────────────
final_report = state.get("final_report", "")
if final_report:
    st.markdown(final_report)
else:
    st.warning("No report generated.")

st.divider()

# ── Risk flags ────────────────────────────────────────────────────────────────
st.subheader("🚨 Risk Flags")
risk_flags = state.get("risk_flags", [])
if not risk_flags:
    st.success("No risk flags identified.")
else:
    SEVERITY_COLORS = {
        "CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"
    }
    for flag in risk_flags:
        sev   = getattr(flag, "severity", flag.get("severity", "LOW")) if not isinstance(flag, dict) else flag.get("severity", "LOW")
        title = getattr(flag, "title",    flag.get("title", "")) if not isinstance(flag, dict) else flag.get("title", "")
        desc  = getattr(flag, "description", flag.get("description", "")) if not isinstance(flag, dict) else flag.get("description", "")
        conf  = getattr(flag, "confidence",  flag.get("confidence", 0)) if not isinstance(flag, dict) else flag.get("confidence", 0)
        icon  = SEVERITY_COLORS.get(sev, "⚪")
        with st.expander(f"{icon} [{sev}] {title}  —  {int(conf*100)}% confidence"):
            st.write(desc)

st.divider()

# ── Citations with clickable links ────────────────────────────────────────────
st.subheader("📚 Source References")
citations = state.get("citations", [])
if not citations:
    st.info("No source citations available.")
else:
    st.caption(f"{len(citations)} sources referenced")

    # Group citations by domain for cleaner display
    from collections import defaultdict
    by_domain = defaultdict(list)
    for c in citations:
        domain = getattr(c, "domain", c.get("domain", "unknown")) if not isinstance(c, dict) else c.get("domain", "unknown")
        by_domain[domain].append(c)

    for domain, domain_citations in sorted(by_domain.items()):
        with st.expander(f"🔗 {domain}  ({len(domain_citations)} reference{'s' if len(domain_citations) > 1 else ''})"):
            for c in domain_citations:
                url     = getattr(c, "url",     c.get("url", "")) if not isinstance(c, dict) else c.get("url", "")
                title   = getattr(c, "title",   c.get("title", url)) if not isinstance(c, dict) else c.get("title", url)
                snippet = getattr(c, "snippet", c.get("snippet", "")) if not isinstance(c, dict) else c.get("snippet", "")
                conf    = getattr(c, "confidence", c.get("confidence", 0)) if not isinstance(c, dict) else c.get("confidence", 0)

                # Clickable link — opens in new browser tab
                st.markdown(f"**[{title}]({url})**", unsafe_allow_html=False)
                if snippet:
                    st.caption(f'"{snippet[:200]}"')
                st.caption(f"Source confidence: {int(conf*100)}%  ·  [Open source ↗]({url})")
                st.divider()

st.divider()

# ── PDF Export ────────────────────────────────────────────────────────────────
st.subheader("📥 Export")
col1, col2 = st.columns([1, 3])
with col1:
    if st.button("📄 Generate PDF", type="primary", use_container_width=True):
        with st.spinner("Generating PDF..."):
            try:
                from utils.report_exporter import export_report_pdf
                pdf_bytes = export_report_pdf(
                    target_name  = state.get("target_name", "Unknown"),
                    final_report = state.get("final_report", ""),
                    risk_flags   = state.get("risk_flags", []),
                    citations    = state.get("citations", []),
                    run_id       = state.get("run_id", "unknown"),
                )
                st.session_state["pdf_bytes"] = pdf_bytes
                st.success("PDF ready for download!")
            except RuntimeError as e:
                st.error(f"PDF generation failed: {e}")

if "pdf_bytes" in st.session_state:
    target = state.get("target_name", "report").replace(" ", "_")
    run_id = state.get("run_id", "unknown")[:8]
    st.download_button(
        label="⬇️ Download PDF Report",
        data=st.session_state["pdf_bytes"],
        file_name=f"DeepTrace_{target}_{run_id}.pdf",
        mime="application/pdf",
        use_container_width=False,
    )
```

### Update `frontend/pages/02_graph.py` — D3 graph with run history

```python
"""
02_graph.py — Phase 3: D3.js graph page with run history and artifact download.
"""
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="DeepTrace — Identity Graph", layout="wide")
st.title("🕸️ Identity Graph")

if "final_state" not in st.session_state or not st.session_state.final_state:
    st.info("Run a research pipeline from the Research page first.")
    st.stop()

state  = st.session_state.final_state
run_id = state.get("run_id", "unknown")

tab1, tab2 = st.tabs(["📊 Current Run", "📁 Saved Artifacts"])

with tab1:
    graph_html    = state.get("graph_html", "")
    artifact_path = state.get("artifact_path", "")
    entities      = state.get("entities", [])
    rels          = state.get("relationships", [])

    col1, col2, col3 = st.columns(3)
    col1.metric("Entities",      len(entities))
    col2.metric("Relationships", len(rels))
    col3.metric("Run ID",        run_id[:8] + "...")

    if graph_html:
        components.html(graph_html, height=620, scrolling=False)
    else:
        st.warning("No graph data available. Run the pipeline first.")

    # Download graph artifact
    if artifact_path and __import__('os').path.exists(artifact_path):
        with open(artifact_path, "rb") as f:
            st.download_button(
                "⬇️ Download Graph HTML",
                data=f,
                file_name=f"DeepTrace_graph_{run_id[:8]}.html",
                mime="text/html",
            )

with tab2:
    st.subheader("Past Run Graphs")
    from utils.audit_logger import list_run_ids
    from config import GRAPH_ARTIFACT_DIR
    import os

    run_ids = list_run_ids()
    if not run_ids:
        st.info("No past runs found.")
    else:
        selected_run = st.selectbox("Select run", run_ids)
        artifact = os.path.join(GRAPH_ARTIFACT_DIR, f"{selected_run}.html")
        if os.path.exists(artifact):
            with open(artifact) as f:
                past_html = f.read()
            components.html(past_html, height=560, scrolling=False)
            with open(artifact, "rb") as f:
                st.download_button(
                    f"⬇️ Download {selected_run[:8]} graph",
                    data=f,
                    file_name=f"DeepTrace_graph_{selected_run[:8]}.html",
                    mime="text/html",
                )
        else:
            st.warning(f"Graph artifact not found for run {selected_run[:8]}")
```

---

## Section 19 — Phase 3 Tests

> **Cursor prompt:** `@DeepTrace_Phase3_Cursor.md implement Section 19 — Phase 3 tests`

### `tests/test_phase3.py`

```python
"""
test_phase3.py — Phase 3 component tests.
All tests run with USE_MOCK=true — no API calls.
"""
import os
import pytest
os.environ["USE_MOCK"] = "true"
os.environ["ENV"]      = "dev"


# ── Retry + Rate Limiter ──────────────────────────────────────────────────────

def test_token_bucket_allows_first_request():
    from utils.retry import TokenBucket
    bucket = TokenBucket(rate=60)
    start  = __import__('time').time()
    bucket.acquire()
    assert __import__('time').time() - start < 1.0

def test_retry_decorator_on_sync():
    from utils.retry import with_retry
    call_count = [0]
    @with_retry(max_retries=2, base_delay=0.01)
    def flaky():
        call_count[0] += 1
        if call_count[0] < 3:
            raise ConnectionError("retry me")
        return "ok"
    assert flaky() == "ok"
    assert call_count[0] == 3


# ── Inconsistency Detector ────────────────────────────────────────────────────

def test_financial_contradiction_detected():
    from utils.inconsistency_detector import detect_inconsistencies
    facts = [
        {"fact_id": "f001", "category": "financial", "claim": "Fund AUM is $5 billion", "confidence": 0.85},
        {"fact_id": "f002", "category": "financial", "claim": "Fund manages $50 million in assets", "confidence": 0.80},
    ]
    result = detect_inconsistencies(facts)
    assert any(r["type"] == "numerical_contradiction" for r in result)

def test_no_false_positive_on_consistent_facts():
    from utils.inconsistency_detector import detect_inconsistencies
    facts = [
        {"fact_id": "f001", "category": "biographical", "claim": "Born in New York in 1965", "confidence": 0.9},
        {"fact_id": "f002", "category": "financial", "claim": "Manages $200M fund", "confidence": 0.8},
    ]
    assert len(detect_inconsistencies(facts)) == 0

def test_circular_ownership_detected():
    from utils.inconsistency_detector import detect_affiliation_heuristics
    entities = [
        {"entity_id": "e001", "name": "Alpha Capital", "entity_type": "Organization"},
        {"entity_id": "e002", "name": "Beta Holdings LLC", "entity_type": "Organization"},
    ]
    rels = [
        {"from_id": "e001", "to_id": "e002", "rel_type": "CONTROLS", "confidence": 0.8},
        {"from_id": "e002", "to_id": "e001", "rel_type": "CONTROLS", "confidence": 0.7},
    ]
    flags = detect_affiliation_heuristics(entities, rels)
    assert any(f["type"] == "circular_ownership" for f in flags)


# ── Entity Canonicalization ───────────────────────────────────────────────────

def test_duplicate_entities_merged():
    from utils.entity_canon import canonicalize_entities
    entities = [
        {"entity_id": "e001", "name": "Timothy Overturf", "entity_type": "Person", "confidence": 0.9, "attributes": {}},
        {"entity_id": "e002", "name": "Tim Overturf",     "entity_type": "Person", "confidence": 0.8, "attributes": {}},
    ]
    canonical, merge_map = canonicalize_entities(entities)
    assert len(canonical) == 1
    assert merge_map["e002"] == "e001"

def test_different_types_not_merged():
    from utils.entity_canon import canonicalize_entities
    entities = [
        {"entity_id": "e001", "name": "Sisu Capital", "entity_type": "Fund",         "confidence": 0.9, "attributes": {}},
        {"entity_id": "e002", "name": "Sisu Capital", "entity_type": "Organization", "confidence": 0.8, "attributes": {}},
    ]
    canonical, _ = canonicalize_entities(entities)
    assert len(canonical) == 2   # Different types — NOT merged

def test_relationship_remap():
    from utils.entity_canon import remap_relationships
    merge_map = {"e002": "e001", "e001": "e001"}
    rels = [{"from_id": "e002", "to_id": "e003", "rel_type": "WORKS_AT", "confidence": 0.8}]
    remapped = remap_relationships(rels, merge_map)
    assert remapped[0]["from_id"] == "e001"

def test_self_loop_dropped():
    from utils.entity_canon import remap_relationships
    merge_map = {"e001": "e002", "e002": "e002"}
    rels = [{"from_id": "e001", "to_id": "e002", "rel_type": "CONNECTED_TO", "confidence": 0.5}]
    remapped = remap_relationships(rels, merge_map)
    assert len(remapped) == 0


# ── Coverage Classifier ───────────────────────────────────────────────────────

def test_facts_classified_correctly():
    from utils.coverage_classifier import classify_facts
    facts = [
        {"fact_id": "f1", "category": "biographical",  "confidence": 0.9},
        {"fact_id": "f2", "category": "financial",     "confidence": 0.8},
        {"fact_id": "f3", "category": "network",       "confidence": 0.7},   # → professional
    ]
    buckets = classify_facts(facts)
    assert len(buckets["biographical_coverage"]) == 1
    assert len(buckets["financial_coverage"])    == 1
    assert len(buckets["professional_coverage"]) == 1   # network maps to professional

def test_coverage_scores_computed():
    from utils.coverage_classifier import compute_coverage_scores
    buckets = {
        "biographical_coverage":  [{"confidence": 0.9}, {"confidence": 0.85}, {"confidence": 0.88}],
        "professional_coverage":  [{"confidence": 0.7}],
        "financial_coverage":     [],
        "behavioral_coverage":    [{"confidence": 0.6}, {"confidence": 0.7}],
    }
    scores = compute_coverage_scores(buckets)
    assert scores["biographical"] == 1.0
    assert scores["professional"] == 0.3
    assert scores["financial"]    == 0.0


# ── Audit Logger ─────────────────────────────────────────────────────────────

def test_audit_logger_writes_and_reads():
    os.environ["AUDIT_LOG_DIR"] = "/tmp/test_audit_logs"
    import shutil
    shutil.rmtree("/tmp/test_audit_logs", ignore_errors=True)

    from utils.audit_logger import set_run_id, log_search_query, load_run_log
    set_run_id("test-run-123")
    log_search_query("scout", "test query", "tavily", 5)
    events = load_run_log("test-run-123")
    assert len(events) >= 1
    assert events[0]["event_type"] == "SEARCH_QUERY"
    assert events[0]["data"]["query"] == "test query"


# ── Node Result / Safe Node ───────────────────────────────────────────────────

def test_safe_node_catches_exception():
    os.environ["AUDIT_LOG_DIR"] = "/tmp/test_audit_logs"
    from utils.node_result import safe_node
    @safe_node("scout_agent")
    def bad_node(state):
        raise ValueError("simulated node failure")
    result = bad_node({})
    assert "raw_results" in result   # fallback default returned
    assert result["raw_results"] == []

def test_safe_node_passes_through_success():
    from utils.node_result import safe_node
    @safe_node("scout_agent")
    def good_node(state):
        return {"raw_results": [{"url": "https://example.com"}]}
    result = good_node({})
    assert len(result["raw_results"]) == 1


# ── Citation Builder ──────────────────────────────────────────────────────────

def test_citations_built_from_facts_and_results():
    from utils.citation_builder import build_citations
    facts = [{"fact_id": "f001", "source_url": "https://sec.gov/filing123",
              "source_domain": "sec.gov", "raw_source_snippet": "Annual report filing"}]
    results = [{"url": "https://sec.gov/filing123", "title": "SEC Filing",
                "content": "Annual report for Sisu Capital"}]
    citations = build_citations(facts, results)
    assert len(citations) == 1
    assert citations[0]["url"] == "https://sec.gov/filing123"
    assert citations[0]["domain"] == "sec.gov"
    assert citations[0]["confidence"] > 0.8   # sec.gov is high trust


# ── D3 Visualizer ─────────────────────────────────────────────────────────────

def test_d3_html_generates_without_error():
    from graph.visualizer import generate_d3_html
    nodes = [{"entity_id": "e001", "name": "Timothy Overturf", "entity_type": "Person",
               "confidence": 0.9, "attributes": {}}]
    edges = []
    html = generate_d3_html(nodes, edges, title="Test")
    assert "d3" in html
    assert "Timothy Overturf" in html
    assert len(html) > 1000

def test_d3_empty_graph_returns_placeholder():
    from graph.visualizer import generate_d3_html
    html = generate_d3_html([], [], title="Empty Test")
    assert "No entities found" in html

def test_d3_handles_edges_with_valid_node_ids():
    from graph.visualizer import generate_d3_html
    nodes = [
        {"entity_id": "e001", "name": "Person A", "entity_type": "Person",    "confidence": 0.9, "attributes": {}},
        {"entity_id": "e002", "name": "Org B",    "entity_type": "Organization","confidence": 0.8, "attributes": {}},
    ]
    edges = [{"from_id": "e001", "to_id": "e002", "rel_type": "WORKS_AT", "confidence": 0.85}]
    html = generate_d3_html(nodes, edges)
    assert "Person A" in html
    assert "Org B" in html
```

---

## Section 20 — Phase 3 Exit Criteria & Smoke Test

### Pre-flight

```bash
# Confirm .env has Phase 3 keys
cat .env | grep -E "LANGCHAIN|LANGSMITH|CHECKPOINT|ARTIFACT|HAIKU_WEB"
# Expected:
# LANGCHAIN_API_KEY=ls__...
# LANGCHAIN_PROJECT=deeptrace-dev
# LANGCHAIN_TRACING_V2=true
# CHECKPOINT_DB_PATH=.checkpoints/deeptrace.db
# GRAPH_ARTIFACT_DIR=.graph_artifacts
# HAIKU_WEB_SEARCH_ENABLED=true
```

### Step 1 — No regressions

```bash
USE_MOCK=true pytest tests/ -q
# All tests must pass — Phase 1, 2, and 3
```

### Step 2 — Phase 3 unit tests

```bash
USE_MOCK=true pytest tests/test_phase3.py -v
# All 22 tests must pass
```

### Step 3 — Config validation

```bash
python -c "
from config import validate_phase3_config
errors = validate_phase3_config()
if errors: [print(f'  MISSING: {e}') for e in errors]
else: print('✅ All Phase 3 config keys present')
"
```

### Step 4 — LangSmith connection test

```bash
python -c "
from utils.tracing import configure_langsmith
ok = configure_langsmith()
print('✅ LangSmith active' if ok else '⚠️ LangSmith disabled')
"
```

### Step 5 — Brave search is gone

```bash
python -c "
import os
assert not os.path.exists('search/brave_search.py'), 'brave_search.py still exists!'
from agents.scout_agent import run_scout
import inspect
src = inspect.getsource(run_scout)
assert 'brave' not in src.lower(), 'Brave reference found in scout_agent!'
print('✅ Brave search fully removed')
"
```

### Step 6 — Full real pipeline run with all Phase 3 features

```bash
USE_MOCK=false ENV=dev python main.py \
  --target "Timothy Overturf" \
  --context "CEO of Sisu Capital" \
  --stream
```

**Expected output:**
```
[LangSmith] Tracing active — project: deeptrace-dev
[Checkpoint] SqliteSaver configured: .checkpoints/deeptrace.db
[supervisor_plan] → Haiku generates queries
[scout_agent] → Tavily + Haiku web search running in parallel
[deep_dive] → Facts extracted with 4-category coverage
[supervisor_reflect] → Quality score with coverage gaps
[risk_evaluator] → LLM flags + deterministic inconsistencies
[graph_builder] → Canonical entities written to Neo4j
[graph_builder] → D3 graph artifact saved: .graph_artifacts/{run_id}.html
[supervisor_synth] → Report with citations
✅ Complete
```

### Step 7 — Verify Phase 3 artifacts

```bash
# Audit log
ls .audit_logs/
python -c "
from utils.audit_logger import list_run_ids, load_run_log
run_id = list_run_ids()[0]
events = load_run_log(run_id)
types  = [e['event_type'] for e in events]
print('Event types found:', set(types))
assert 'SEARCH_QUERY' in types, 'No search queries logged'
assert 'NODE_COMPLETE' in types, 'No node completions logged'
print('✅ Audit log has structured events')
"

# Graph artifact
ls .graph_artifacts/
python -c "
from utils.audit_logger import list_run_ids
from config import GRAPH_ARTIFACT_DIR
import os
run_id = list_run_ids()[0]
path = os.path.join(GRAPH_ARTIFACT_DIR, f'{run_id}.html')
assert os.path.exists(path), f'Graph artifact missing: {path}'
with open(path) as f: content = f.read()
assert 'd3' in content, 'D3.js not in graph HTML'
assert len(content) > 5000, 'Graph HTML too small'
print(f'✅ D3 graph artifact exists: {len(content)} chars')
"

# Checkpoint
ls .checkpoints/
python -c "
import os
assert os.path.exists('.checkpoints/deeptrace.db'), 'Checkpoint DB missing'
size = os.path.getsize('.checkpoints/deeptrace.db')
assert size > 0, 'Checkpoint DB is empty'
print(f'✅ Checkpoint DB exists: {size} bytes')
"
```

### Step 8 — LangSmith traces visible

```bash
# Open: https://smith.langchain.com → your project → Traces
# You should see one trace with child spans per agent node
python -c "print('Open https://smith.langchain.com and check for traces in project: deeptrace-dev')"
```

### Step 9 — Relationships are run-scoped in Neo4j

```bash
python -c "
from graph.neo4j_manager import get_driver
from config import NEO4J_DATABASE
from utils.audit_logger import list_run_ids
run_id = list_run_ids()[0]
driver = get_driver()
with driver.session(database=NEO4J_DATABASE) as s:
    # Relationships should have run_id property
    result = s.run('MATCH ()-[r {run_id: \$rid}]->() RETURN count(r) AS c', rid=run_id)
    count  = result.single()['c']
    print(f'Relationships with run_id={run_id[:8]}...: {count}')
    assert count >= 0   # may be 0 if no relationships extracted, that is OK
    # Verify no relationships WITHOUT run_id
    result2 = s.run('MATCH ()-[r]->() WHERE r.run_id IS NULL RETURN count(r) AS c')
    unscoped = result2.single()['c']
    assert unscoped == 0, f'{unscoped} unscoped relationships found!'
    print('✅ All relationships are run-scoped')
"
```

### Step 10 — Streamlit Phase 3 UI

```bash
streamlit run frontend/app.py
# Page 01: Run pipeline → observe streaming with parallel search source badges
# Page 02: Graph → D3 interactive graph — try hover, click, zoom, drag nodes
# Page 02: Switch to Saved Artifacts tab → past graph HTML loads
# Page 03: Report → citations grouped by domain with clickable links
# Page 03: Click "Generate PDF" → download button appears → PDF downloads
# Page 04: Eval → coverage scores per category shown
```

### Phase 3 Exit Criteria Checklist

```
INFRASTRUCTURE
[ ] LangSmith active — traces visible in smith.langchain.com
[ ] SqliteSaver checkpointing — .checkpoints/deeptrace.db created
[ ] Audit logs — .audit_logs/{run_id}.jsonl created per run
[ ] Graph artifacts — .graph_artifacts/{run_id}.html saved per run
[ ] Brave search removed — brave_search.py deleted, no references remain

SEARCH & RESILIENCE
[ ] Tavily + Haiku web search running in parallel per query
[ ] Rate limiter active — no HTTP 429 errors on burst queries
[ ] Retry decorator active — transient errors retried with backoff
[ ] @safe_node on all agents — pipeline survives individual node failure

EXTRACTION & QUALITY
[ ] 4-category coverage in state: biographical, professional, financial, behavioral
[ ] coverage_scores computed after each deep_dive run
[ ] supervisor_reflect uses coverage gaps to generate targeted queries
[ ] Citations built for all facts with source_url populated

ENTITY INTEGRITY
[ ] Entity canonicalization runs before Neo4j write
[ ] Near-duplicate entities merged (similarity ≥ 0.85)
[ ] Relationship endpoints remapped after merge
[ ] Self-loop relationships dropped

INCONSISTENCY DETECTION
[ ] Financial numerical contradictions detected deterministically
[ ] Biographical conflicts detected deterministically
[ ] Circular ownership detected from relationship graph
[ ] Shell company heuristics applied to organization entities

DATA ISOLATION
[ ] Every relationship has run_id property in Neo4j
[ ] fetch_graph_for_run() returns only current run's relationships
[ ] No unscoped relationships (run_id IS NULL) in DB

VISUALIZATION
[ ] D3.js force-directed graph renders in Streamlit
[ ] Nodes color-coded by entity type with legend
[ ] Hover tooltips show entity name, type, confidence, attributes
[ ] Click selects node and shows detail panel with connections
[ ] Zoom + pan + drag nodes all functional
[ ] Edge labels show relationship type

CITATIONS & EXPORT
[ ] Citations grouped by domain in UI
[ ] Every citation has a clickable [Open source ↗] link
[ ] PDF export generates and downloads successfully
[ ] Graph HTML downloadable from page 02

REGRESSION
[ ] USE_MOCK=true still works identically to Phase 1
[ ] All Phase 1, 2, and 3 unit tests pass
```

---

*DeepTrace Phase 3 Implementation Guide · Tanzeel Khan · March 2026*
*Prerequisites: Phase 1 + Phase 2 complete · New keys: LANGCHAIN_API_KEY only*
*Next: Phase 4 — Production model upgrade (Opus/Sonnet), LangSmith evaluators, staging validation*
