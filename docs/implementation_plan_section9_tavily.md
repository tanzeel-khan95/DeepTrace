# Implementation Plan: Section 9 (Extraction Coverage) + Tavily Search Improvement

## Part A — Section 9: Extraction Coverage (4 Categories as First-Class Outputs)

### Goal

Introduce four first-class coverage buckets (biographical, professional, financial, behavioral) in `AgentState`, classify extracted facts into them, compute per-category coverage scores, and use coverage gaps in the supervisor reflect step to drive targeted follow-up queries.

### 1. Update `state/agent_state.py`

**Add to `AgentState` TypedDict** (after existing fields, before `final_report`):

- `biographical_coverage:  Annotated[List[Fact], operator.add]`
- `professional_coverage:  Annotated[List[Fact], operator.add]`
- `financial_coverage:     Annotated[List[Fact], operator.add]`
- `behavioral_coverage:    Annotated[List[Fact], operator.add]`
- `coverage_scores:        dict`  (e.g. `{"biographical": 0.8, "professional": 0.6, "financial": 0.5, "behavioral": 0.3}`)
- `inconsistencies:        Annotated[List[dict], operator.add]`

**Update `make_initial_state()`** — add to the returned dict:

- `"biographical_coverage": []`
- `"professional_coverage": []`
- `"financial_coverage": []`
- `"behavioral_coverage": []`
- `"coverage_scores": {"biographical": 0.0, "professional": 0.0, "financial": 0.0, "behavioral": 0.0}`
- `"inconsistencies": []`

**Note:** The existing `Fact` model keeps `category: Literal["biographical", "financial", "network", "legal", "other"]`. No schema change required; mapping to the four buckets is done in the classifier.

### 2. Create `utils/coverage_classifier.py`

New module with:

- **`CATEGORY_MAP`** — map from Fact category to coverage bucket:
  - `"biographical"` → `"biographical_coverage"`
  - `"professional"` → `"professional_coverage"` (if Fact ever emits this)
  - `"financial"` → `"financial_coverage"`
  - `"behavioral"` → `"behavioral_coverage"`
  - `"network"` → `"professional_coverage"`
  - `"legal"` → `"behavioral_coverage"`
  - `"other"` → `"biographical_coverage"`

- **`COVERAGE_THRESHOLD`** — e.g. `0.6`; categories below this are “gaps”.

- **`classify_facts(facts: list) -> dict`**  
  - Input: list of Fact objects or dicts (with `category`).  
  - Output: dict with keys `biographical_coverage`, `professional_coverage`, `financial_coverage`, `behavioral_coverage`, each a list of facts in that bucket.

- **`compute_coverage_scores(buckets: dict) -> dict`**  
  - Input: the buckets dict from `classify_facts`.  
  - Output: `{category: score}` with scores in [0.0, 1.0]. Suggested formula:
    - 0 facts → 0.0
    - 1 fact → 0.3
    - 2 facts → 0.6
    - 3+ facts: 1.0 if avg confidence ≥ 0.7, else 0.8  
  - Category name is derived from bucket key (e.g. `biographical_coverage` → `biographical`).

- **`identify_coverage_gaps(scores: dict) -> List[str]`**  
  - Return category names where `score < COVERAGE_THRESHOLD` (e.g. 0.6).  
  - Used by supervisor_reflect to prioritise follow-up queries.

### 3. Update `agents/deep_dive_agent.py`

- After building `facts`, `entities`, `rels` and `conf_map` (and before the return):
  - Convert facts to dicts: `facts_as_dicts = [f.model_dump() for f in facts]`
  - Call `buckets = classify_facts(facts_as_dicts)` and `cov_scores = compute_coverage_scores(buckets)` (import from `utils.coverage_classifier`).
- Extend the returned delta to include:
  - `"biographical_coverage": buckets["biographical_coverage"]`
  - `"professional_coverage": buckets["professional_coverage"]`
  - `"financial_coverage": buckets["financial_coverage"]`
  - `"behavioral_coverage": buckets["behavioral_coverage"]`
  - `"coverage_scores": cov_scores`
- For mock path, add the same four coverage lists (from mock data or empty) and a default `coverage_scores` dict so state shape is consistent.

### 4. Update `agents/supervisor.py` (supervisor_reflect)

- In the non-mock branch of `supervisor_reflect`, before building `user_msg`:
  - Import `identify_coverage_gaps` from `utils.coverage_classifier`.
  - Get `current_scores = state.get("coverage_scores", {})` and `gaps_from_coverage = identify_coverage_gaps(current_scores)`.
- Extend `user_msg` to include:
  - A line or block: `COVERAGE SCORES:` and `json.dumps(current_scores, indent=2)`.
  - A line: `UNCOVERED CATEGORIES: {gaps_from_coverage}` and an instruction to prioritise queries for these categories in the next loop.
- No change to the response model or return shape; only the prompt content and thus behaviour of the supervisor.

### 5. Optional: Frontend / pipeline

- If any Streamlit page or pipeline summary displays “coverage”, extend it to read `state["coverage_scores"]` and optionally `state["biographical_coverage"]` etc. for display. Not required for the core Section 9 behaviour.

---

## Part B — Improve Tavily Search (Relevance for Identity + Context)

### Goal

Use Tavily’s **advanced** search depth so results are more relevant for identity- and context-oriented queries, at the cost of slightly higher latency and API credit usage.

### 1. Config (optional but recommended)

In `config.py`, add a single setting, e.g.:

- `TAVILY_SEARCH_DEPTH: str = os.getenv("TAVILY_SEARCH_DEPTH", "advanced")`  
  - Allowed values: `"basic"` | `"advanced"` (and optionally `"fast"` / `"ultra-fast"` if you want to support them later).

Default `"advanced"` so that by default all Tavily calls use the higher-relevance mode.

### 2. Update `search/tavily_search.py`

- Import the new config (e.g. `TAVILY_SEARCH_DEPTH`) from `config`.
- In `_sync_tavily_search`, replace the hardcoded `"basic"` passed to `_do_tavily_search(..., "basic", ...)` with `TAVILY_SEARCH_DEPTH` (or the config constant).
- Ensure the rest of the call (`query`, `max_results`, `include_raw_content`) is unchanged.
- No change to mock path or to the structure of returned result dicts.

### 3. Env and docs

- In `.env.example` (and optionally `.env`), add a commented or documented line, e.g.:
  - `# TAVILY_SEARCH_DEPTH=advanced   # basic | advanced; advanced = better relevance, more credits`
- If you have a README or runbook, note that identity/context queries benefit from `advanced` and that it uses more Tavily credits per request.

---

## Summary of Files to Touch

| File | Action |
|------|--------|
| `state/agent_state.py` | Add 6 state fields; extend `make_initial_state()` |
| `utils/coverage_classifier.py` | **New**: CATEGORY_MAP, classify_facts, compute_coverage_scores, identify_coverage_gaps |
| `agents/deep_dive_agent.py` | Classify facts, compute scores, return coverage buckets + coverage_scores |
| `agents/supervisor.py` | In reflect, add coverage_scores + gaps to user_msg |
| `config.py` | Add TAVILY_SEARCH_DEPTH (default "advanced") |
| `search/tavily_search.py` | Use TAVILY_SEARCH_DEPTH instead of hardcoded "basic" |
| `.env.example` | Document TAVILY_SEARCH_DEPTH |

---

## Data Flow (Section 9)

```mermaid
flowchart LR
  DeepDive[Deep Dive] --> Facts[extracted_facts]
  Facts --> Classify[classify_facts]
  Classify --> Buckets[4 coverage buckets]
  Buckets --> Scores[compute_coverage_scores]
  Scores --> State[AgentState]
  State --> Reflect[supervisor_reflect]
  Reflect --> Gaps[identify_coverage_gaps]
  Gaps --> NextQueries[Next loop queries]
```
