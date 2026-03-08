# DeepTrace — Phase 2: Real LLM Integration (Haiku-Only Dev Mode)
> **Cursor Implementation Guide** · Phase 2 of 4 · Claude Haiku 4.5 for ALL agents · ~$0.15–0.25 per run
>
> **Prerequisite:** Phase 1 is complete. `python main.py --target "Timothy Overturf"` runs end-to-end
> with mock data. All tests pass. Neo4j is connected and writing correctly.
>
> **Goal:** Replace every `raise NotImplementedError("Phase 2")` stub with real Anthropic API calls
> using **Claude Haiku 4.5** for ALL agents (cheapest Anthropic model, ~$1/$5 per 1M tokens).
> Also wire up Tavily search (one real API key needed). Everything else stays identical to Phase 1.
>
> **At the end of Phase 2:** `USE_MOCK=false python main.py --target "Timothy Overturf"` runs a
> complete real research pipeline. Haiku responses will be simpler than Opus/Sonnet but the
> full wiring is validated end-to-end for under $1 total.

---

## Required API Keys for Phase 2

Set these in your `.env` file before running any Phase 2 code:

```bash
# ── REQUIRED for Phase 2 ─────────────────────────────────────────────────────

USE_MOCK=false                          # ← flip this from true to false
ENV=dev                                 # keep dev — uses Haiku for everything

ANTHROPIC_API_KEY=sk-ant-...            # ← THE ONLY LLM KEY YOU NEED IN PHASE 2
                                        # Get from: https://console.anthropic.com
                                        # Used for: ALL 5 agents (Supervisor, Scout
                                        #   analysis, Deep Dive, Risk Evaluator,
                                        #   Graph Builder) — all running Haiku 4.5

TAVILY_API_KEY=tvly-...                 # ← REQUIRED for real web search (Scout)
                                        # Get from: https://app.tavily.com
                                        # Free tier: 1,000 searches/month (enough for dev)

# ── NOT needed in Phase 2 (leave blank or omit) ──────────────────────────────

OPENAI_API_KEY=                         # Phase 3+ only (GPT-4.1 for Scout in prod)
GOOGLE_API_KEY=                         # Phase 3+ only (Gemini 2.5 for Deep Dive in prod)
BRAVE_SEARCH_API_KEY=                   # Optional fallback — Brave only used if Tavily fails
LANGCHAIN_API_KEY=                      # Phase 3+ only (LangSmith tracing)
LANGCHAIN_TRACING_V2=false              # keep false in Phase 2

# ── Neo4j (unchanged from Phase 1) ───────────────────────────────────────────
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=deeptrace123
NEO4J_DATABASE=neo4j
```

### Why only two keys?

In Phase 2 `ENV=dev` mode, `config.py` routes ALL agents to `claude-haiku-4-5-20251001`.
You do not need GPT-4.1 or Gemini keys — those only activate in `ENV=staging` or `ENV=prod`
(Phase 3). Tavily free tier is enough for development search volume.

### Cost estimate for Phase 2

| Activity | Runs | Cost/run | Total |
|----------|------|----------|-------|
| Integration testing (Haiku all agents) | 30 | ~$0.20 | ~$6 |
| Debugging / iteration | 20 | ~$0.20 | ~$4 |
| **Phase 2 total** | | | **~$10** |

---

## Table of Contents

- [Section 1 — Phase 2 Rules & Strategy](#section-1--phase-2-rules--strategy)
- [Section 2 — Config Updates](#section-2--config-updates)
- [Section 3 — Anthropic Client Singleton](#section-3--anthropic-client-singleton)
- [Section 4 — Structured Output Helper](#section-4--structured-output-helper)
- [Section 5 — Supervisor Agent (Real)](#section-5--supervisor-agent-real)
- [Section 6 — Scout Agent & Tavily (Real)](#section-6--scout-agent--tavily-real)
- [Section 7 — Deep Dive Agent (Real)](#section-7--deep-dive-agent-real)
- [Section 8 — Risk Evaluator Agent (Real)](#section-8--risk-evaluator-agent-real)
- [Section 9 — Graph Builder Agent (Real)](#section-9--graph-builder-agent-real)
- [Section 10 — Confidence Scorer L3 (Real)](#section-10--confidence-scorer-l3-real)
- [Section 11 — LLM Cache (Record & Replay)](#section-11--llm-cache-record--replay)
- [Section 12 — Updated Budget Guard](#section-12--updated-budget-guard)
- [Section 13 — Phase 2 Tests](#section-13--phase-2-tests)
- [Section 14 — Phase 2 Exit Criteria & Smoke Test](#section-14--phase-2-exit-criteria--smoke-test)

---

## Section 1 — Phase 2 Rules & Strategy

> **Read before writing a single line. These rules keep Phase 2 cost under $10.**

### The Golden Rule: Touch Only the `else` Branches

Every agent in Phase 1 has this pattern:

```python
if USE_MOCK:
    return MOCK_FIXTURE          # ← DO NOT TOUCH THIS
# Phase 2: implement here
raise NotImplementedError(...)   # ← REPLACE THIS with real code
```

**In Phase 2, you only fill in the `else` path.** The `if USE_MOCK` path must remain
100% identical to Phase 1. This means you can always fall back to mock mode instantly
by setting `USE_MOCK=true` — no code changes needed.

### Haiku for Everything in Phase 2

In `config.py` the `dev` model config already maps every agent to Haiku:

```python
"dev": {
    "supervisor":     "claude-haiku-4-5-20251001",  # $1/$5 per 1M
    "scout":          "claude-haiku-4-5-20251001",
    "deep_dive":      "claude-haiku-4-5-20251001",
    "risk_evaluator": "claude-haiku-4-5-20251001",
    "graph_builder":  "claude-haiku-4-5-20251001",
},
```

**Do not change this.** Haiku's output quality is lower than Opus/Sonnet but it is
completely sufficient to validate that:
- The Anthropic API calls are wired correctly
- JSON parsing and Pydantic validation work
- LangGraph routing fires correctly on real (not mock) data
- Neo4j graph populates from real LLM-extracted entities

### Token Caps Per Agent (Phase 2 dev)

Every `client.messages.create()` call in Phase 2 MUST use:

```python
max_tokens=MAX_TOKENS[ENV]   # = 500 in dev
```

This is already defined in `config.py`. Never hardcode `max_tokens` — always use the
config constant. A runaway loop bug in dev should hit the token cap fast and cheap.

### Loop Cap (Phase 2 dev)

`MAX_LOOPS[ENV]` is already `2` for `ENV=dev`. Do not change it.
Haiku runs 2 search loops = ~4 LLM calls total per run. Cheap and fast.

### JSON Output Strategy

All agents must return structured JSON. Use this exact approach for every agent:

```python
# Always end system prompts with:
"Respond ONLY with valid JSON. No preamble, no markdown fences, no explanation."

# Always parse with fallback:
import json
text = response.content[0].text.strip()
text = text.replace("```json", "").replace("```", "").strip()
data = json.loads(text)
```

Do NOT use `instructor` library in Phase 2 — it adds complexity.
Direct JSON parsing is sufficient for Haiku validation.

### What Does NOT Change in Phase 2

- Directory structure — unchanged
- All Pydantic schemas — unchanged
- LangGraph graph wiring — unchanged
- Streamlit pages — unchanged
- Neo4j manager — unchanged
- mock_responses.py — unchanged (still works when USE_MOCK=true)
- All Phase 1 tests — must still pass

---

## Section 2 — Config Updates

> **Cursor prompt:** `@DeepTrace_Phase2_Cursor.md implement Section 2 - update config.py for Phase 2`

Update `config.py` — add these items. Do not remove anything that exists.

```python
# Add to config.py — after existing MODEL_CONFIG block

# ── Haiku model string (Phase 2 convenience constant) ─────────────────────────
HAIKU_MODEL = "claude-haiku-4-5-20251001"

# ── Phase 2 token caps (already defined, confirm these values) ────────────────
# MAX_TOKENS = {"dev": 500, "staging": 1500, "prod": 3000}   ← already in config
# MAX_LOOPS  = {"dev": 2,   "staging": 3,    "prod": 5}      ← already in config

# ── Anthropic API key ─────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")

# ── Tavily ────────────────────────────────────────────────────────────────────
# TAVILY_API_KEY already defined in Phase 1 config — confirm it reads from env

# ── LLM cache directory (Phase 2 record-replay) ──────────────────────────────
LLM_CACHE_DIR: str = os.getenv("LLM_CACHE_DIR", ".llm_cache")
LLM_CACHE_ENABLED: bool = os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true"

# ── Phase 2 startup validation ────────────────────────────────────────────────
def validate_phase2_config() -> list:
    """
    Check all required Phase 2 env vars are set.
    Returns list of missing variable names (empty = all good).
    """
    errors = []
    if not USE_MOCK:
        if not ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY — required when USE_MOCK=false")
        if not TAVILY_API_KEY:
            errors.append("TAVILY_API_KEY — required for real search")
    return errors
```

---

## Section 3 — Anthropic Client Singleton

> **Cursor prompt:** `@DeepTrace_Phase2_Cursor.md implement Section 3 - create utils/anthropic_client.py`

Create `utils/anthropic_client.py` — this is the single place all agents import
the Anthropic client from. Never create `anthropic.Anthropic()` directly in agents.

### `utils/anthropic_client.py`

```python
"""
anthropic_client.py — Singleton Anthropic client for DeepTrace.

All agents import get_client() from here. This ensures:
  - The client is only instantiated once (not per-call)
  - API key validation happens at startup
  - Easy to swap for a mock in tests
  - Budget guard is always applied after each call

Architecture position: imported by all agents in Phase 2+.
Never import anthropic directly in agent files.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)
_client = None


def get_client():
    """
    Return singleton Anthropic client.
    Validates API key on first call.
    Raises RuntimeError if ANTHROPIC_API_KEY is not set.
    """
    global _client
    if _client is None:
        import anthropic
        from config import ANTHROPIC_API_KEY
        if not ANTHROPIC_API_KEY:
            raise RuntimeError(
                "[AnthropicClient] ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file. See Phase 2 API Keys section."
            )
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        logger.info("[AnthropicClient] Client initialised")
    return _client


def call_llm(
    system_prompt: str,
    user_message: str,
    model: str,
    max_tokens: int,
    use_cache: bool = True,
) -> str:
    """
    Make one Anthropic API call with prompt caching on the system prompt.

    Args:
        system_prompt: The system instructions (cached between calls)
        user_message:  The user turn content
        model:         Model string from config.MODELS
        max_tokens:    Hard cap — always use MAX_TOKENS[ENV] from config
        use_cache:     Whether to apply Anthropic prompt caching to system prompt

    Returns:
        Raw text content from the model response

    Side effects:
        - Records token spend in budget_guard
        - Writes to LLM cache if LLM_CACHE_ENABLED=true
    """
    from config import LLM_CACHE_ENABLED
    from utils.llm_cache import get_cached, save_to_cache

    # Check cache first (record-replay for dev iteration)
    if LLM_CACHE_ENABLED:
        cached = get_cached(system_prompt, user_message, model)
        if cached is not None:
            logger.debug(f"[LLM Cache] HIT for model={model}")
            return cached

    client = get_client()

    # Build system block with prompt caching
    if use_cache:
        system_block = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},  # Cache system prompt
            }
        ]
    else:
        system_block = system_prompt

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_block,
        messages=[{"role": "user", "content": user_message}],
    )

    text = response.content[0].text

    # Record spend for budget guard
    from utils.budget_guard import record_spend
    record_spend(
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        model=model,
    )

    # Save to cache
    if LLM_CACHE_ENABLED:
        save_to_cache(system_prompt, user_message, model, text)

    logger.info(
        f"[LLM] model={model} in={response.usage.input_tokens} "
        f"out={response.usage.output_tokens}"
    )
    return text
```

---

## Section 4 — Structured Output Helper

> **Cursor prompt:** `@DeepTrace_Phase2_Cursor.md implement Section 4 - create utils/json_parser.py`

Create `utils/json_parser.py` — all agents use this to safely parse LLM JSON output.

### `utils/json_parser.py`

```python
"""
json_parser.py — Safe JSON extraction from LLM responses.

LLMs sometimes wrap JSON in markdown fences or add preamble text.
This module strips that and returns a clean dict/list, or raises a
structured error so agents can retry intelligently.

Architecture position: imported by all agents in Phase 2+.
"""
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class LLMParseError(Exception):
    """Raised when LLM output cannot be parsed as valid JSON."""
    def __init__(self, raw_text: str, reason: str):
        self.raw_text = raw_text
        self.reason = reason
        super().__init__(f"LLMParseError: {reason}\nRaw: {raw_text[:200]}")


def extract_json(raw_text: str) -> Any:
    """
    Extract JSON from raw LLM response text.

    Handles these common LLM formatting issues:
      - ```json ... ``` fences
      - ``` ... ``` fences (no language tag)
      - Leading explanation text before the JSON object
      - Trailing text after closing brace/bracket
      - Single quotes instead of double quotes (Haiku sometimes does this)

    Returns:
        Parsed Python dict or list

    Raises:
        LLMParseError if no valid JSON can be extracted
    """
    text = raw_text.strip()

    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object or array within the text
    for pattern in [r"\{.*\}", r"\[.*\]"]:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    # Last resort: fix single quotes (Haiku quirk)
    try:
        fixed = text.replace("'", '"')
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    raise LLMParseError(raw_text, "No valid JSON found after all extraction attempts")


def safe_extract_json(raw_text: str, fallback: Any = None) -> Any:
    """
    Like extract_json but returns fallback instead of raising on failure.
    Use when you have a reasonable default and don't want to crash.
    """
    try:
        return extract_json(raw_text)
    except LLMParseError as e:
        logger.warning(f"[JSONParser] Falling back to default: {e.reason}")
        return fallback
```

---

## Section 5 — Supervisor Agent (Real)

> **Cursor prompt:** `@DeepTrace_Phase2_Cursor.md implement Section 5 - replace NotImplementedError stubs in agents/supervisor.py`

Replace the three `raise NotImplementedError("Phase 2: ...")` lines in
`agents/supervisor.py`. The `if USE_MOCK` branches are untouched.

### Updated `agents/supervisor.py` — Phase 2 `else` branches

```python
"""
agents/supervisor.py — Phase 2 update.

Only the three `else` branches below are new. Everything else is identical to Phase 1.
Uses Claude Haiku 4.5 in ENV=dev. Upgraded to Opus 4.5 in ENV=staging/prod.
"""
# Add these imports at the top of the existing file:
import json
from config import MODELS, MAX_TOKENS, ENV, QUALITY_THRESHOLD
from utils.anthropic_client import call_llm
from utils.json_parser import extract_json, safe_extract_json
from prompts.supervisor_prompt import SUPERVISOR_SYSTEM_PROMPT


# ── supervisor_plan — replace NotImplementedError with: ──────────────────────

# ELSE BRANCH for supervisor_plan():
else:
    model = MODELS["supervisor"]
    user_msg = f"""Research target: {state['target_name']}
Context: {state.get('target_context', 'No additional context')}
Loop number: {state['loop_count'] + 1}
Queries already issued: {json.dumps(state['queries_issued'])}
Gaps remaining: {json.dumps(state.get('gaps_remaining', []))}
Facts found so far: {len(state['extracted_facts'])}

Generate the next batch of research queries covering all 5 categories.
Respond with JSON matching the schema in your instructions."""

    raw = call_llm(
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        user_message=user_msg,
        model=model,
        max_tokens=MAX_TOKENS[ENV],
    )
    data = safe_extract_json(raw, fallback={
        "research_plan":  [f"{state['target_name']} background career"],
        "gaps_remaining": ["General background not yet found"],
        "research_quality": 0.0,
        "loop_count": state["loop_count"] + 1,
    })
    logger.info(f"[Supervisor::plan] Real: {len(data.get('research_plan', []))} queries")
    return {
        "research_plan":  data.get("research_plan",  []),
        "gaps_remaining": data.get("gaps_remaining", []),
        "loop_count":     state["loop_count"] + 1,
    }


# ── supervisor_reflect — replace NotImplementedError with: ───────────────────

# ELSE BRANCH for supervisor_reflect():
else:
    model = MODELS["supervisor"]

    # Build a summary of current findings for the reflect prompt
    facts_summary = "\n".join(
        f"- [{f.category}] {f.claim} (conf={f.confidence:.2f}, src={f.source_domain})"
        for f in state["extracted_facts"][:20]   # Cap at 20 to save tokens
    )
    user_msg = f"""Research target: {state['target_name']}
Loop: {state['loop_count']}
Total facts extracted: {len(state['extracted_facts'])}
Total entities found: {len(state['entities'])}

Current facts:
{facts_summary if facts_summary else 'None yet'}

Gaps still remaining: {json.dumps(state.get('gaps_remaining', []))}

Score research quality 0.0-1.0 and identify remaining gaps.
Respond with JSON: {{"research_quality": 0.0, "gaps_remaining": ["gap1"]}}"""

    raw = call_llm(
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        user_message=user_msg,
        model=model,
        max_tokens=MAX_TOKENS[ENV],
    )
    data = safe_extract_json(raw, fallback={
        "research_quality": min(0.40 * state["loop_count"], 0.82),
        "gaps_remaining":   [],
    })
    quality = float(data.get("research_quality", 0.5))
    gaps    = data.get("gaps_remaining", [])
    logger.info(f"[Supervisor::reflect] Real: quality={quality:.2f} gaps={len(gaps)}")
    return {"research_quality": quality, "gaps_remaining": gaps}


# ── supervisor_synthesise — replace NotImplementedError with: ────────────────

# ELSE BRANCH for supervisor_synthesise():
else:
    model = MODELS["supervisor"]

    # Build evidence summary (cap tokens)
    risk_flags_text = "\n".join(
        f"- [{f.severity}] {f.title}: {f.description[:150]}"
        for f in state["risk_flags"]
    )
    facts_text = "\n".join(
        f"- {f.claim} (conf={f.confidence:.0%}, src={f.source_domain})"
        for f in state["extracted_facts"][:15]
    )
    entities_text = ", ".join(e.name for e in state["entities"][:10])

    synth_prompt = f"""You are generating a final intelligence report for a due diligence investigation.

Target: {state['target_name']}
Research loops completed: {state['loop_count']}
Total facts extracted: {len(state['extracted_facts'])}
Total entities mapped: {len(state['entities'])}

KEY FACTS:
{facts_text if facts_text else 'None extracted'}

ENTITY NETWORK:
{entities_text if entities_text else 'None mapped'}

RISK FLAGS IDENTIFIED:
{risk_flags_text if risk_flags_text else 'No risk flags identified'}

Generate a professional markdown risk intelligence report with:
1. Executive Summary (3-4 sentences)
2. Key Findings (bullet list)
3. Risk Flag Summary (table: Severity | Flag | Confidence)
4. Entity Network Summary
5. Confidence Assessment

Be concise. Focus on evidence-backed claims only."""

    raw = call_llm(
        system_prompt=(
            "You are a professional intelligence analyst writing due diligence reports. "
            "Write in clear, professional markdown. Be factual and evidence-based."
        ),
        user_message=synth_prompt,
        model=model,
        max_tokens=MAX_TOKENS[ENV],
        use_cache=False,   # Don't cache report — unique every time
    )
    # Report is markdown, not JSON — use raw text directly
    report = raw.strip()
    if not report:
        report = f"# Report: {state['target_name']}\n\nInsufficient data to generate report in Phase 2 dev mode."
    logger.info(f"[Supervisor::synthesise] Real: report={len(report)} chars")
    return {"final_report": report}
```

### Updated `prompts/supervisor_prompt.py` — Phase 2 additions

Add this to the bottom of the existing `SUPERVISOR_SYSTEM_PROMPT` string (do not
replace existing content — append within the triple-quoted string):

```python
# Add REFLECT_PROMPT and SYNTH_PROMPT as separate constants in supervisor_prompt.py

SUPERVISOR_REFLECT_PROMPT = """You are evaluating the quality of research conducted on a named individual.

Score research quality 0.0–1.0 across four dimensions (0.25 weight each):
  - biographical_completeness: key life facts verified with 2+ sources
  - financial_coverage: fund relationships, AUM, performance documented
  - network_mapping: key associates identified and cross-referenced
  - risk_assessment: potential red flags identified with evidence

Respond ONLY with valid JSON. No preamble, no markdown fences:
{"research_quality": 0.0, "gaps_remaining": ["gap1", "gap2"]}"""

SUPERVISOR_PLAN_PROMPT = SUPERVISOR_SYSTEM_PROMPT  # Alias for clarity
```

---

## Section 6 — Scout Agent & Tavily (Real)

> **Cursor prompt:** `@DeepTrace_Phase2_Cursor.md implement Section 6 - real Tavily search in scout_agent.py`

The Scout Agent itself needs no changes — it already calls `tavily_search()` in its
`else` branch. Only `search/tavily_search.py` needs its `else` branch filled in.

### Updated `search/tavily_search.py` — Phase 2 `else` branch

```python
"""
search/tavily_search.py — Phase 2 update.

The else branch now executes real Tavily API calls.
The if USE_MOCK branch is unchanged from Phase 1.
"""
# Replace the Phase 2 comment block in the existing else branch:

else:
    # Real Tavily search — Phase 2
    try:
        from tavily import TavilyClient   # sync client — simpler for Phase 2
        from config import TAVILY_API_KEY, MIN_RELEVANCE

        if not TAVILY_API_KEY:
            logger.error("[Tavily] TAVILY_API_KEY not set — returning empty results")
            return []

        client = TavilyClient(api_key=TAVILY_API_KEY)

        response = client.search(
            query=query,
            search_depth="basic",       # "basic" in dev to save Tavily quota
            max_results=5,
            include_raw_content=False,  # Don't fetch full pages via Tavily (Deep Dive handles that)
        )

        results = []
        for r in response.get("results", []):
            domain = _extract_domain(r.get("url", ""))
            relevance = float(r.get("score", 0.5))
            if relevance >= MIN_RELEVANCE:
                results.append({
                    "url":           r.get("url", ""),
                    "title":         r.get("title", ""),
                    "content":       r.get("content", ""),
                    "relevance":     relevance,
                    "source_domain": domain,
                })

        logger.info(f"[Tavily] Real search: '{query[:40]}' → {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"[Tavily] API error for '{query}': {e}")
        # Fallback to mock on API error — keeps pipeline alive
        logger.warning("[Tavily] Falling back to mock results due to API error")
        from mock_responses import MOCK_SCOUT_RESULTS
        return MOCK_SCOUT_RESULTS["raw_results"][:2]
```

### Note on async vs sync Scout

The Scout Agent's `_async_scout()` function calls `await tavily_search()`. For Phase 2,
switch `tavily_search.py` to use the **sync** `TavilyClient` wrapped in
`asyncio.to_thread()` to avoid issues:

```python
# In search/tavily_search.py, update the function signature for Phase 2:
async def tavily_search(query: str) -> list:
    if USE_MOCK:
        ...  # unchanged
    
    import asyncio
    # Run sync Tavily client in thread pool to keep async interface
    return await asyncio.to_thread(_sync_tavily_search, query)


def _sync_tavily_search(query: str) -> list:
    """Sync implementation — called via asyncio.to_thread."""
    from tavily import TavilyClient
    from config import TAVILY_API_KEY, MIN_RELEVANCE
    
    if not TAVILY_API_KEY:
        return []
    
    client = TavilyClient(api_key=TAVILY_API_KEY)
    response = client.search(
        query=query,
        search_depth="basic",
        max_results=5,
        include_raw_content=False,
    )
    results = []
    for r in response.get("results", []):
        domain = _extract_domain(r.get("url", ""))
        relevance = float(r.get("score", 0.5))
        if relevance >= MIN_RELEVANCE:
            results.append({
                "url":           r.get("url", ""),
                "title":         r.get("title", ""),
                "content":       r.get("content", ""),
                "relevance":     relevance,
                "source_domain": domain,
            })
    return results
```

---

## Section 7 — Deep Dive Agent (Real)

> **Cursor prompt:** `@DeepTrace_Phase2_Cursor.md implement Section 7 - replace NotImplementedError in deep_dive_agent.py`

### Updated `agents/deep_dive_agent.py` — Phase 2 `else` branch

```python
"""
agents/deep_dive_agent.py — Phase 2 update.

Replaces NotImplementedError with real Haiku-based extraction.
Takes top N search results from state, batches them into one LLM call,
extracts Facts, Entities, and Relationships as JSON.
"""
# Add these imports at the top of existing file:
import json
from config import MODELS, MAX_TOKENS, ENV
from utils.anthropic_client import call_llm
from utils.json_parser import extract_json, safe_extract_json
from prompts.deep_dive_prompt import DEEP_DIVE_SYSTEM_PROMPT
from evaluation.confidence_scorer import score_facts_batch


# ELSE BRANCH for run_deep_dive():
else:
    model = MODELS["deep_dive"]   # Haiku in dev

    # Take top 8 results by relevance (cap to save tokens in dev)
    results = sorted(
        state["raw_results"],
        key=lambda r: r.get("relevance", 0),
        reverse=True,
    )[:8]

    if not results:
        logger.warning("[DeepDive] No raw_results to process")
        return {"extracted_facts": [], "entities": [], "relationships": [], "confidence_map": {}}

    # Build content block for LLM
    content_blocks = []
    for i, r in enumerate(results):
        content_blocks.append(
            f"SOURCE {i+1}: {r.get('source_domain','unknown')} | {r.get('url','')}\n"
            f"TITLE: {r.get('title','')}\n"
            f"CONTENT: {r.get('content','')[:600]}\n"   # Cap content per source
        )
    sources_text = "\n---\n".join(content_blocks)

    user_msg = f"""Research target: {state['target_name']}
Context: {state.get('target_context', '')}

Extract all facts, entities, and relationships from these sources:

{sources_text}

Respond ONLY with valid JSON matching this schema exactly:
{{
  "extracted_facts": [
    {{
      "fact_id": "f001",
      "claim": "one specific verifiable claim",
      "source_url": "https://...",
      "source_domain": "domain.com",
      "confidence": 0.85,
      "category": "biographical|financial|network|legal|other",
      "entities_mentioned": ["Name1", "Name2"],
      "supporting_fact_ids": [],
      "raw_source_snippet": "exact quote from source"
    }}
  ],
  "entities": [
    {{
      "entity_id": "e001",
      "name": "Full Name",
      "entity_type": "Person|Organization|Fund|Location|Event|Filing",
      "attributes": {{"key": "value"}},
      "confidence": 0.90,
      "source_fact_ids": ["f001"]
    }}
  ],
  "relationships": [
    {{
      "from_id": "e001",
      "to_id": "e002",
      "rel_type": "WORKS_AT|INVESTED_IN|CONNECTED_TO|FILED_WITH|FOUNDED|AFFILIATED_WITH|BOARD_MEMBER|MANAGED|CONTROLS",
      "attributes": {{}},
      "confidence": 0.85,
      "source_fact_id": "f001"
    }}
  ]
}}

Rules:
- fact_ids must be unique strings (f001, f002, ...)
- entity_ids must be unique strings (e001, e002, ...)
- Only extract claims directly supported by the provided sources
- confidence 0.0-1.0 based on source reliability and claim specificity
- entities_mentioned must reference names that appear in your entities list"""

    raw = call_llm(
        system_prompt=DEEP_DIVE_SYSTEM_PROMPT,
        user_message=user_msg,
        model=model,
        max_tokens=MAX_TOKENS[ENV],
    )

    data = safe_extract_json(raw, fallback={
        "extracted_facts": [], "entities": [], "relationships": []
    })

    # Validate through Pydantic (catches bad LLM output early)
    from state.agent_state import Fact, Entity, Relationship
    facts, entities, rels = [], [], []

    for f in data.get("extracted_facts", []):
        try:
            facts.append(Fact(**f))
        except Exception as e:
            logger.warning(f"[DeepDive] Invalid fact skipped: {e} | data={f}")

    for e in data.get("entities", []):
        try:
            entities.append(Entity(**e))
        except Exception as ex:
            logger.warning(f"[DeepDive] Invalid entity skipped: {ex} | data={e}")

    for r in data.get("relationships", []):
        try:
            rels.append(Relationship(**r))
        except Exception as ex:
            logger.warning(f"[DeepDive] Invalid relationship skipped: {ex} | data={r}")

    # Score confidence for all valid facts
    conf_map = score_facts_batch([f.model_dump() for f in facts])

    logger.info(f"[DeepDive] Real: {len(facts)} facts, {len(entities)} entities, {len(rels)} rels")
    return {
        "extracted_facts": facts,
        "entities":        entities,
        "relationships":   rels,
        "confidence_map":  conf_map,
    }
```

### `prompts/deep_dive_prompt.py`

```python
"""
deep_dive_prompt.py — System prompt for Deep Dive Agent (Haiku/Gemini).

Architecture position: imported by agents/deep_dive_agent.py.
"""

DEEP_DIVE_SYSTEM_PROMPT = """You are a precise intelligence extraction specialist.

Your job is to extract structured facts, entities, and relationships from web sources
about a named individual. You extract only what is explicitly stated in the provided
sources — never infer, assume, or fabricate.

For each fact:
- The claim must be directly verifiable from the source text provided
- The confidence score reflects source reliability and claim specificity
- SEC.gov, Reuters, Bloomberg, FT get highest confidence (0.85-0.95)
- Unknown blogs or unverified sites get lowest confidence (0.30-0.50)

For each entity:
- Use the most complete name form found in the sources
- Include only entities with at least one direct source reference
- entity_type must be exactly: Person, Organization, Fund, Location, Event, or Filing

For each relationship:
- Both from_id and to_id must reference entity_ids you defined above
- rel_type must be exactly one of the allowed types
- Never create a relationship without a source_fact_id backing it

Respond ONLY with valid JSON. No preamble. No explanation. No markdown fences."""
```

---

## Section 8 — Risk Evaluator Agent (Real)

> **Cursor prompt:** `@DeepTrace_Phase2_Cursor.md implement Section 8 - replace NotImplementedError in risk_evaluator.py`

### Updated `agents/risk_evaluator.py` — Phase 2 `else` branch

```python
"""
agents/risk_evaluator.py — Phase 2 update.

Replaces NotImplementedError with real Haiku-based risk evaluation.
Operates on the full set of validated facts from DeepDive.
"""
# Add these imports at top of existing file:
import json
from config import MODELS, MAX_TOKENS, ENV
from utils.anthropic_client import call_llm
from utils.json_parser import safe_extract_json
from prompts.risk_prompt import RISK_EVALUATOR_SYSTEM_PROMPT


# ELSE BRANCH for run_risk_evaluator():
else:
    model = MODELS["risk_evaluator"]   # Haiku in dev

    # Build fact list for the prompt (cap at 20 facts to stay within token budget)
    usable_facts = [
        f for f in state["extracted_facts"]
        if state["confidence_map"].get(f.fact_id, f.confidence) >= MIN_EVIDENCE_CONFIDENCE
    ][:20]

    if not usable_facts:
        logger.warning("[RiskEvaluator] No usable facts — skipping risk evaluation")
        return {"risk_flags": []}

    facts_json = json.dumps([
        {
            "fact_id":      f.fact_id,
            "claim":        f.claim,
            "category":     f.category,
            "confidence":   f.confidence,
            "source":       f.source_domain,
            "entities":     f.entities_mentioned,
        }
        for f in usable_facts
    ], indent=2)

    user_msg = f"""Research target: {state['target_name']}
Total facts: {len(state['extracted_facts'])} | Usable facts: {len(usable_facts)}
Entities mapped: {len(state['entities'])}

VERIFIED FACTS:
{facts_json}

Identify all risk flags from these facts.
Respond ONLY with valid JSON:
{{
  "risk_flags": [
    {{
      "flag_id": "r001",
      "title": "Short title of risk",
      "description": "Detailed description of the risk and why it matters",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "evidence_fact_ids": ["f001", "f002"],
      "confidence": 0.85,
      "category": "regulatory|financial|network|reputational|legal"
    }}
  ]
}}

Rules:
- Every flag MUST cite at least 2 evidence_fact_ids from the list above
- Only create a flag if the evidence directly supports the risk
- severity: CRITICAL=illegal/sanctions, HIGH=material financial risk,
  MEDIUM=potential conflict/omission, LOW=minor inconsistency
- flag_ids must be unique (r001, r002, ...)"""

    raw = call_llm(
        system_prompt=RISK_EVALUATOR_SYSTEM_PROMPT,
        user_message=user_msg,
        model=model,
        max_tokens=MAX_TOKENS[ENV],
    )

    data = safe_extract_json(raw, fallback={"risk_flags": []})

    # Validate through Pydantic
    flags = []
    for flag_data in data.get("risk_flags", []):
        try:
            # Ensure minimum 2 evidence items (schema enforces this)
            if len(flag_data.get("evidence_fact_ids", [])) < 2:
                logger.warning(f"[RiskEvaluator] Skipped {flag_data.get('flag_id')}: < 2 evidence")
                continue
            flags.append(RiskFlag(**flag_data))
        except Exception as e:
            logger.warning(f"[RiskEvaluator] Invalid flag skipped: {e}")

    logger.info(f"[RiskEvaluator] Real: {len(flags)} risk flags generated")
    return {"risk_flags": flags}
```

### `prompts/risk_prompt.py`

```python
"""
risk_prompt.py — System prompt for Risk Evaluator Agent (Haiku/Sonnet).

Architecture position: imported by agents/risk_evaluator.py.
"""

RISK_EVALUATOR_SYSTEM_PROMPT = """You are a professional risk analyst specialising in
financial due diligence, regulatory compliance, and background investigations.

Your job is to identify genuine risk signals in a set of verified facts about a named
individual. A risk flag is only valid if:
  1. It is directly supported by at least 2 facts in the provided evidence
  2. The risk has a plausible real-world consequence (financial, regulatory, or reputational)
  3. It is factual, not speculative

Severity guidelines:
  CRITICAL — Evidence of sanctions violations, active fraud, criminal charges, or OFAC listing
  HIGH     — Material undisclosed financial risk, significant regulatory violations, fund failures
  MEDIUM   — Potential conflicts of interest, structural opacity, undisclosed affiliations
  LOW      — Minor biographical discrepancies, single-source unverified claims

Do NOT create risk flags for:
  - Normal business activities that are publicly disclosed
  - Standard industry practices
  - Speculation without direct fact support

Respond ONLY with valid JSON. No preamble. No explanation. No markdown fences."""
```

---

## Section 9 — Graph Builder Agent (Real)

> **Cursor prompt:** `@DeepTrace_Phase2_Cursor.md implement Section 9 - update graph_builder.py for Phase 2`

The Graph Builder in Phase 1 already writes to Neo4j using mock entity/relationship data.
In Phase 2, the same code runs — but now `state["entities"]` and `state["relationships"]`
contain REAL data extracted by DeepDive. No code changes required in `graph_builder.py`.

However, add Haiku-assisted Cypher optimisation for Phase 2:

### `prompts/graph_prompt.py`

```python
"""
graph_prompt.py — System prompt for Graph Builder Agent (Haiku).

Phase 2: Used to validate and clean entity/relationship data before Neo4j write.
Architecture position: imported by agents/graph_builder.py.
"""

GRAPH_BUILDER_SYSTEM_PROMPT = """You are a graph data specialist.
Your job is to validate and normalise entity and relationship data before it is
written to a Neo4j property graph.

When given a list of entities and relationships:
1. Merge duplicate entities (same name, different capitalization)
2. Ensure all relationship from_id and to_id values reference valid entity_ids
3. Remove any relationships whose endpoints don't exist in the entity list
4. Return the cleaned data in the same JSON schema

Respond ONLY with valid JSON. No preamble. No markdown fences."""
```

### Update `agents/graph_builder.py` — add Phase 2 Haiku validation step

```python
"""
graph_builder.py — Phase 2 update.

Adds optional Haiku-assisted entity deduplication before Neo4j write.
The core Neo4j write logic is unchanged from Phase 1.
"""
# Add this function to graph_builder.py (called from run_graph_builder):

def _deduplicate_entities_with_llm(entities: list, relationships: list) -> tuple:
    """
    Use Haiku to identify and merge duplicate entities before Neo4j write.
    Phase 2 feature — reduces graph noise from near-duplicate entity names.
    Only called when USE_MOCK=False and len(entities) > 3.
    """
    from config import MODELS, MAX_TOKENS, ENV, USE_MOCK
    if USE_MOCK or len(entities) <= 3:
        return entities, relationships

    from utils.anthropic_client import call_llm
    from utils.json_parser import safe_extract_json
    from prompts.graph_prompt import GRAPH_BUILDER_SYSTEM_PROMPT
    import json

    user_msg = f"""Clean and deduplicate this entity/relationship data:

ENTITIES: {json.dumps(entities[:15], indent=2)}
RELATIONSHIPS: {json.dumps(relationships[:20], indent=2)}

Return cleaned JSON: {{"entities": [...], "relationships": [...]}}"""

    raw = call_llm(
        system_prompt=GRAPH_BUILDER_SYSTEM_PROMPT,
        user_message=user_msg,
        model=MODELS["graph_builder"],
        max_tokens=MAX_TOKENS[ENV],
    )
    data = safe_extract_json(raw, fallback={"entities": entities, "relationships": relationships})
    return data.get("entities", entities), data.get("relationships", relationships)


# Update run_graph_builder() — add deduplication before Neo4j write:
# After: entities = [e.model_dump() for e in state["entities"]]
# Add:   entities, relationships = _deduplicate_entities_with_llm(entities, relationships)
```

---

## Section 10 — Confidence Scorer L3 (Real)

> **Cursor prompt:** `@DeepTrace_Phase2_Cursor.md implement Section 10 - replace L3 stub in confidence_scorer.py`

In Phase 1, `llm_faithfulness_stub()` always returns `0.75`.
In Phase 2, replace it with a real Haiku call — but only for HIGH/CRITICAL risk flag evidence.
For regular facts, keep using the stub (too expensive to check every fact).

### Updated `evaluation/confidence_scorer.py` — L3 real implementation

```python
"""
confidence_scorer.py — Phase 2 update.

Adds real L3 faithfulness check for high-stakes facts.
L3 stub (0.75) is still used for regular facts to save tokens.
Real L3 check only fires for facts cited in CRITICAL/HIGH risk flags.
"""

def llm_faithfulness_check(claim: str, source_snippet: str, model: str = None) -> float:
    """
    Layer 3: Real LLM faithfulness check.

    Asks Haiku whether the claim is faithfully supported by the source snippet.
    Returns 0.0–1.0 faithfulness score.

    Only called for facts that are cited as evidence for HIGH/CRITICAL risk flags.
    All other facts use llm_faithfulness_stub() to save tokens.
    """
    from config import USE_MOCK, MODELS, ENV
    if USE_MOCK:
        return llm_faithfulness_stub()

    if not source_snippet or not claim:
        return 0.50

    try:
        from utils.anthropic_client import call_llm
        from utils.json_parser import safe_extract_json

        if model is None:
            model = MODELS.get("risk_evaluator", "claude-haiku-4-5-20251001")

        prompt = f"""Does the following CLAIM accurately represent what is stated in the SOURCE?

CLAIM: {claim}

SOURCE: {source_snippet[:400]}

Respond ONLY with JSON: {{"faithful": true/false, "score": 0.0-1.0, "reason": "brief"}}
Score meaning: 1.0=fully supported, 0.5=partially supported, 0.0=not supported or contradicted"""

        raw = call_llm(
            system_prompt="You verify whether claims are faithfully supported by source text. Be precise.",
            user_message=prompt,
            model=model,
            max_tokens=150,   # Very short — just need score
        )
        data = safe_extract_json(raw, fallback={"score": 0.75})
        score = float(data.get("score", 0.75))
        return max(0.0, min(1.0, score))

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"[L3] Faithfulness check failed: {e}")
        return llm_faithfulness_stub()


def compute_final_confidence_with_l3(
    domain: str,
    supporting_count: int,
    contradicting_count: int,
    claim: str,
    source_snippet: str,
    is_high_stakes: bool = False,
) -> float:
    """
    Full 3-layer confidence score with optional real L3 check.

    Args:
        is_high_stakes: If True, calls real L3 LLM check (expensive).
                        If False, uses stub L3 (cheap).
    """
    l1 = get_domain_trust(domain)
    l2 = apply_cross_reference(l1, supporting_count, contradicting_count)

    if is_high_stakes:
        l3 = llm_faithfulness_check(claim, source_snippet)
    else:
        l3 = llm_faithfulness_stub()

    final = (l1 * 0.30) + (l2 * 0.40) + (l3 * 0.30)
    return round(min(final, MAX_FINAL_CONFIDENCE), 4)
```

---

## Section 11 — LLM Cache (Record & Replay)

> **Cursor prompt:** `@DeepTrace_Phase2_Cursor.md implement Section 11 - implement utils/llm_cache.py`

This was a stub in Phase 1. Now implement it fully — it saves every real LLM response
to disk and replays it on identical prompts. Essential for UI iteration without re-paying
for the same research run.

### `utils/llm_cache.py`

```python
"""
llm_cache.py — Record-and-replay LLM response cache for Phase 2 development.

Saves every real API response to .llm_cache/{hash}.json on first call.
Subsequent identical calls (same model + same prompts) return the cached response.

This means you can iterate on Streamlit UI, report formatting, and graph layout
without paying for repeated identical research runs.

Toggle: LLM_CACHE_ENABLED=true in .env (default true in dev).
Clear:  rm -rf .llm_cache/

Architecture position: called by utils/anthropic_client.py.
"""
import hashlib
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def _cache_key(system_prompt: str, user_message: str, model: str) -> str:
    """Generate deterministic cache key from call parameters."""
    raw = f"{model}::{system_prompt}::{user_message}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_path(key: str) -> str:
    from config import LLM_CACHE_DIR
    os.makedirs(LLM_CACHE_DIR, exist_ok=True)
    return os.path.join(LLM_CACHE_DIR, f"{key}.json")


def get_cached(system_prompt: str, user_message: str, model: str) -> Optional[str]:
    """
    Return cached response text if it exists, else None.
    """
    from config import LLM_CACHE_ENABLED
    if not LLM_CACHE_ENABLED:
        return None

    key  = _cache_key(system_prompt, user_message, model)
    path = _cache_path(key)

    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            logger.debug(f"[LLMCache] HIT: {key[:12]}...")
            return data.get("response_text")
        except Exception as e:
            logger.warning(f"[LLMCache] Read error: {e}")
    return None


def save_to_cache(
    system_prompt: str,
    user_message:  str,
    model:         str,
    response_text: str,
) -> None:
    """
    Save a real API response to disk for future replay.
    """
    from config import LLM_CACHE_ENABLED
    if not LLM_CACHE_ENABLED:
        return

    key  = _cache_key(system_prompt, user_message, model)
    path = _cache_path(key)

    try:
        with open(path, "w") as f:
            json.dump({
                "model":         model,
                "key":           key,
                "response_text": response_text,
            }, f, indent=2)
        logger.debug(f"[LLMCache] SAVED: {key[:12]}...")
    except Exception as e:
        logger.warning(f"[LLMCache] Write error: {e}")


def clear_cache() -> int:
    """Delete all cache files. Returns count deleted."""
    from config import LLM_CACHE_DIR
    if not os.path.exists(LLM_CACHE_DIR):
        return 0
    count = 0
    for f in os.listdir(LLM_CACHE_DIR):
        if f.endswith(".json"):
            os.remove(os.path.join(LLM_CACHE_DIR, f))
            count += 1
    logger.info(f"[LLMCache] Cleared {count} cached responses")
    return count


def cache_stats() -> dict:
    """Return cache hit stats for the current session."""
    from config import LLM_CACHE_DIR
    if not os.path.exists(LLM_CACHE_DIR):
        return {"entries": 0, "size_kb": 0}
    files = [f for f in os.listdir(LLM_CACHE_DIR) if f.endswith(".json")]
    size  = sum(os.path.getsize(os.path.join(LLM_CACHE_DIR, f)) for f in files)
    return {"entries": len(files), "size_kb": round(size / 1024, 1)}
```

---

## Section 12 — Updated Budget Guard

> **Cursor prompt:** `@DeepTrace_Phase2_Cursor.md implement Section 12 - update budget_guard.py for Phase 2`

`budget_guard.py` was already implemented in Phase 1. For Phase 2, add a spend
summary function and update pricing to current Haiku rates:

```python
# Add to utils/budget_guard.py — append after existing code

def spend_summary() -> str:
    """Return human-readable spend summary for CLI and Streamlit display."""
    limit = PHASE_BUDGET.get(ENV, 10.0)
    pct   = (_total_spent / limit * 100) if limit > 0 else 0
    return (
        f"Spend: ${_total_spent:.4f} / ${limit:.2f} limit "
        f"({pct:.1f}% of {ENV} budget)"
    )


# Verify Haiku pricing is correct in PRICE_PER_1M dict:
# "claude-haiku-4-5-20251001": {"in": 1.00, "out": 5.00}
# This is the cheapest Anthropic model — ~$0.15-0.25 for a full research run in dev
```

---

## Section 13 — Phase 2 Tests

> **Cursor prompt:** `@DeepTrace_Phase2_Cursor.md implement Section 13 - create tests/test_agents.py`

### `tests/test_agents.py`

```python
"""
test_agents.py — Phase 2 agent tests.

These tests run with USE_MOCK=true (no API calls) to validate:
  - All Phase 2 code paths are importable
  - JSON parsing handles edge cases
  - Budget guard fires correctly
  - LLM cache writes and reads correctly

Tests that require real API keys are marked with @pytest.mark.integration
and are skipped in standard CI (run manually with: pytest -m integration).
"""
import os
import pytest

# Force mock mode for all tests (no API calls)
os.environ["USE_MOCK"]  = "true"
os.environ["ENV"]       = "dev"


# ─────────────────────────────────────────────────────────────────────────────
# JSON Parser Tests
# ─────────────────────────────────────────────────────────────────────────────

from utils.json_parser import extract_json, safe_extract_json, LLMParseError

def test_extract_plain_json():
    result = extract_json('{"research_quality": 0.75, "gaps_remaining": []}')
    assert result["research_quality"] == 0.75

def test_extract_json_with_fences():
    raw = '```json\n{"key": "value"}\n```'
    result = extract_json(raw)
    assert result["key"] == "value"

def test_extract_json_with_preamble():
    raw = 'Here is the analysis:\n\n{"result": "found"}'
    result = extract_json(raw)
    assert result["result"] == "found"

def test_extract_json_raises_on_garbage():
    with pytest.raises(LLMParseError):
        extract_json("This is just plain text with no JSON at all.")

def test_safe_extract_returns_fallback_on_error():
    result = safe_extract_json("not json at all", fallback={"default": True})
    assert result == {"default": True}

def test_extract_json_array():
    result = extract_json('[{"id": 1}, {"id": 2}]')
    assert len(result) == 2


# ─────────────────────────────────────────────────────────────────────────────
# Budget Guard Tests
# ─────────────────────────────────────────────────────────────────────────────

from utils.budget_guard import record_spend, get_total_spent, reset

def test_budget_guard_accumulates():
    reset()
    record_spend(1000, 500, "claude-haiku-4-5-20251001")
    assert get_total_spent() > 0

def test_budget_guard_raises_at_limit():
    reset()
    from utils.budget_guard import _check_budget
    import utils.budget_guard as bg
    bg._total_spent = 999.0   # Force over limit
    with pytest.raises(RuntimeError, match="BudgetGuard"):
        bg._check_budget()
    reset()

def test_budget_guard_reset():
    record_spend(5000, 2000, "claude-haiku-4-5-20251001")
    reset()
    assert get_total_spent() == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# LLM Cache Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_llm_cache_miss_returns_none():
    os.environ["LLM_CACHE_ENABLED"] = "true"
    os.environ["LLM_CACHE_DIR"]     = "/tmp/test_llm_cache"
    from utils.llm_cache import get_cached, clear_cache
    clear_cache()
    result = get_cached("sys", "user", "claude-haiku-4-5-20251001")
    assert result is None

def test_llm_cache_save_and_retrieve():
    os.environ["LLM_CACHE_ENABLED"] = "true"
    os.environ["LLM_CACHE_DIR"]     = "/tmp/test_llm_cache"
    from utils.llm_cache import save_to_cache, get_cached, clear_cache
    clear_cache()
    save_to_cache("sys_prompt", "user_msg", "claude-haiku-4-5-20251001", '{"ok": true}')
    result = get_cached("sys_prompt", "user_msg", "claude-haiku-4-5-20251001")
    assert result == '{"ok": true}'

def test_llm_cache_disabled_returns_none():
    os.environ["LLM_CACHE_ENABLED"] = "false"
    from utils.llm_cache import get_cached
    result = get_cached("sys", "user", "haiku")
    assert result is None
    os.environ["LLM_CACHE_ENABLED"] = "true"


# ─────────────────────────────────────────────────────────────────────────────
# Agent Import Tests (Phase 2 code must be importable)
# ─────────────────────────────────────────────────────────────────────────────

def test_all_agents_importable():
    from agents.supervisor      import supervisor_plan, supervisor_reflect, supervisor_synthesise
    from agents.scout_agent     import run_scout
    from agents.deep_dive_agent import run_deep_dive
    from agents.risk_evaluator  import run_risk_evaluator
    from agents.graph_builder   import run_graph_builder
    assert True   # No ImportError = pass

def test_all_prompts_importable():
    from prompts.supervisor_prompt import SUPERVISOR_SYSTEM_PROMPT
    from prompts.deep_dive_prompt  import DEEP_DIVE_SYSTEM_PROMPT
    from prompts.risk_prompt       import RISK_EVALUATOR_SYSTEM_PROMPT
    from prompts.graph_prompt      import GRAPH_BUILDER_SYSTEM_PROMPT
    assert len(SUPERVISOR_SYSTEM_PROMPT) > 100
    assert len(DEEP_DIVE_SYSTEM_PROMPT)  > 100

def test_anthropic_client_raises_without_key():
    os.environ.pop("ANTHROPIC_API_KEY", None)
    from utils import anthropic_client
    anthropic_client._client = None   # reset singleton
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        anthropic_client.get_client()


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests (requires real ANTHROPIC_API_KEY — run manually)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_real_haiku_call():
    """Test one real Haiku call. Requires ANTHROPIC_API_KEY in environment."""
    os.environ["USE_MOCK"] = "false"
    import anthropic
    from utils.anthropic_client import call_llm
    from utils.budget_guard import reset
    reset()

    result = call_llm(
        system_prompt="You are a test assistant. Respond with exactly: {\"status\": \"ok\"}",
        user_message="Test ping",
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
    )
    from utils.json_parser import extract_json
    data = extract_json(result)
    assert data.get("status") == "ok"
    os.environ["USE_MOCK"] = "true"

@pytest.mark.integration
def test_real_tavily_search():
    """Test one real Tavily search. Requires TAVILY_API_KEY in environment."""
    import asyncio
    os.environ["USE_MOCK"] = "false"
    from search.tavily_search import tavily_search
    results = asyncio.run(tavily_search("Anthropic AI company"))
    assert len(results) > 0
    assert "url" in results[0]
    os.environ["USE_MOCK"] = "true"
```

---

## Section 14 — Phase 2 Exit Criteria & Smoke Test

> **Run all of these before declaring Phase 2 complete.**

### Pre-flight Checklist

```bash
# Confirm .env is set correctly before any real runs
cat .env | grep -E "USE_MOCK|ENV|ANTHROPIC|TAVILY"
# Expected:
# USE_MOCK=false
# ENV=dev
# ANTHROPIC_API_KEY=sk-ant-...   (real key)
# TAVILY_API_KEY=tvly-...        (real key)
```

### Step 1 — All Phase 1 tests still pass (no regressions)

```bash
USE_MOCK=true pytest tests/test_state.py tests/test_confidence.py -v
# Expected: all green
```

### Step 2 — All Phase 2 unit tests pass (no API calls)

```bash
USE_MOCK=true pytest tests/test_agents.py -v -k "not integration"
# Expected: all green
# json parser, budget guard, cache, import tests
```

### Step 3 — Config validation

```bash
python -c "
from config import validate_phase2_config
errors = validate_phase2_config()
if errors:
    print('MISSING KEYS:')
    for e in errors: print(f'  - {e}')
else:
    print('✅ All Phase 2 config keys present')
"
```

### Step 4 — Neo4j still connected

```bash
python main.py --test-connections
# Expected: Neo4j: OK
```

### Step 5 — Single real Haiku call (minimal cost test ~$0.001)

```bash
python -c "
import os; os.environ['USE_MOCK'] = 'false'
from utils.anthropic_client import call_llm
from utils.json_parser import extract_json
result = call_llm(
    system_prompt='Reply with JSON only: {\"status\": \"ok\", \"model\": \"haiku\"}',
    user_message='ping',
    model='claude-haiku-4-5-20251001',
    max_tokens=50,
)
print('Raw:', result)
data = extract_json(result)
print('Parsed:', data)
assert data.get('status') == 'ok', 'Haiku call failed'
print('✅ Haiku API call works')
"
```

### Step 6 — Single real Tavily search (~0 credits)

```bash
python -c "
import asyncio, os
os.environ['USE_MOCK'] = 'false'
from search.tavily_search import tavily_search
results = asyncio.run(tavily_search('Timothy Overturf CEO hedge fund'))
print(f'Results: {len(results)}')
for r in results[:2]:
    print(f'  - {r[\"source_domain\"]} | {r[\"title\"][:50]}')
print('✅ Tavily search works')
"
```

### Step 7 — Full real pipeline run (~$0.20)

```bash
USE_MOCK=false ENV=dev python main.py \
  --target "Timothy Overturf" \
  --context "CEO of Sisu Capital" \
  --stream
```

**Expected output (approximate):**
```
[supervisor_plan] — Haiku generates 8-10 real queries
[scout_agent]     — Tavily fetches real web results
[deep_dive]       — Haiku extracts real entities and facts
[supervisor_reflect] — Haiku scores research quality
[risk_evaluator]  — Haiku identifies risk flags
[graph_builder]   — Writes real entities to Neo4j
[supervisor_synth] — Haiku generates real report
✅ Complete | Facts: X | Flags: Y | Quality: 0.xx
```

### Step 8 — Verify Neo4j has real data

```bash
python -c "
from graph.neo4j_manager import get_driver
from config import NEO4J_DATABASE
driver = get_driver()
with driver.session(database=NEO4J_DATABASE) as s:
    count = s.run('MATCH (n) RETURN count(n) AS c').single()['c']
    print(f'Neo4j node count: {count}')
    assert count > 0, 'Neo4j is empty — graph_builder may have failed'
    print('✅ Neo4j has real data')
"
```

### Step 9 — LLM cache is working

```bash
python -c "
from utils.llm_cache import cache_stats
stats = cache_stats()
print(f'Cache entries: {stats[\"entries\"]} | Size: {stats[\"size_kb\"]} KB')
assert stats['entries'] > 0, 'Cache is empty — caching may not be working'
print('✅ LLM cache has entries from the real run')
"
# Run the pipeline again — should be faster and cost $0 (cache hits)
USE_MOCK=false ENV=dev python main.py --target "Timothy Overturf" --stream
# Expect: all LLM calls return from cache
```

### Step 10 — Streamlit shows real data

```bash
streamlit run frontend/app.py
# Navigate to page 01 — run "Timothy Overturf"
# Navigate to page 02 — graph should show real entities
# Navigate to page 03 — report should show real Haiku-generated content
```

### Phase 2 Exit Criteria Checklist

```
API INTEGRATION
[ ] ANTHROPIC_API_KEY validates without error
[ ] TAVILY_API_KEY returns real search results
[ ] call_llm() completes and returns parseable JSON
[ ] record_spend() tracks token usage after each call
[ ] Budget guard is not exceeded on a standard dev run

AGENT PIPELINE (real mode)
[ ] supervisor_plan() returns real queries (not mock)
[ ] scout_agent returns real Tavily results (not mock)
[ ] deep_dive_agent returns real Fact and Entity objects validated by Pydantic
[ ] risk_evaluator returns real RiskFlag objects with 2+ evidence IDs each
[ ] graph_builder writes real entities to Neo4j
[ ] supervisor_synthesise returns real markdown report
[ ] loop_count = 2 (MAX_LOOPS[dev]) after run completes

QUALITY
[ ] At least 3 facts extracted per real run
[ ] At least 2 entities identified per real run
[ ] At least 1 risk flag generated per real run
[ ] Neo4j has > 0 nodes after run

COST CONTROL
[ ] Total spend for one real run < $0.50 (Haiku dev mode)
[ ] LLM cache works — second identical run costs $0
[ ] Budget guard would fire at $10 (confirmed by unit test)

REGRESSION
[ ] USE_MOCK=true still runs identically to Phase 1 (no regressions)
[ ] pytest tests/ — all Phase 1 and Phase 2 unit tests pass
```

### What Changes in Phase 3

When Phase 2 exit criteria are all checked:

1. Set `ENV=staging` in `.env`
2. Add `OPENAI_API_KEY` (GPT-4.1 for Scout in staging)
3. Add `GOOGLE_API_KEY` (Gemini 2.5 for Deep Dive in staging)
4. Add `LANGCHAIN_API_KEY` and set `LANGCHAIN_TRACING_V2=true`
5. Run 3–5 capped staging runs with real prod-tier models
6. Review LangSmith traces for quality

**Cost for Phase 3:** ~$12–15 (3 staging runs at ~$0.80–1.00 each + LangSmith).

---

*DeepTrace Phase 2 Implementation Guide · Tanzeel Khan · March 2026*
*Prerequisite: Phase 1 complete · API Keys: ANTHROPIC_API_KEY + TAVILY_API_KEY only*
*Next: @DeepTrace_Phase3_Cursor.md — Staging with GPT-4.1, Gemini 2.5, LangSmith*
