"""
agents/scout_agent.py — Scout Agent: parallel search execution.

Dispatches all queries from research_plan simultaneously via asyncio.gather().
Primary: Tavily search. Haiku web search is used as a conditional secondary source
when Tavily returns 2 or fewer results or when average relevance is below 0.5.
Results are merged, deduplicated by URL, and sorted by relevance.

Phase 1 (USE_MOCK=true): returns MOCK_SCOUT_RESULTS fixture directly.
Phase 2+ (USE_MOCK=false): executes real parallel searches.

Architecture position: second node in LangGraph pipeline, called by Supervisor.
"""
import asyncio
import logging
from config import USE_MOCK, MIN_RELEVANCE, MAX_SEARCH_RESULTS_PER_QUERY
from state.agent_state import AgentState
from mock_responses import MOCK_SCOUT_RESULTS
from utils.tracing import traceable

logger = logging.getLogger(__name__)

# Thresholds for triggering Haiku web search (supplement to Tavily)
MIN_RESULTS_THRESHOLD = 2
MIN_AVG_RELEVANCE = 0.5


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


async def _fetch_one_query(query: str, idx: int) -> list:
    """
    Run Tavily for one query; if results are insufficient (count or confidence),
    supplement with Haiku web search. Return combined, deduplicated results.
    """
    from search.tavily_search import tavily_search
    from search.haiku_search import haiku_web_search
    from utils.audit_logger import log_search_query

    tavily_results = await tavily_search(query)
    for r in tavily_results:
        r["search_source"] = r.get("search_source", "tavily")

    log_search_query("scout_agent", query, "tavily", len(tavily_results))

    needs_haiku = len(tavily_results) <= MIN_RESULTS_THRESHOLD
    avg_relevance = None
    if tavily_results and not needs_haiku:
        avg_relevance = sum(r.get("relevance", 0) for r in tavily_results) / len(tavily_results)
        needs_haiku = avg_relevance < MIN_AVG_RELEVANCE

    combined = list(tavily_results)
    if needs_haiku:
        avg_str = f"{avg_relevance:.2f}" if avg_relevance is not None else "N/A"
        logger.debug(
            f"[Scout] Query {idx + 1}: supplementing with Haiku "
            f"(count={len(tavily_results)}, avg_relevance={avg_str})"
        )
        haiku_results = await haiku_web_search(query, max_results=3)
        log_search_query("scout_agent", query, "haiku_web_search", len(haiku_results))
        combined = combined + haiku_results

    seen_urls = set()
    deduped = []
    for r in combined:
        if r.get("url") and r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            deduped.append(r)

    return deduped


async def _async_scout(state: AgentState) -> dict:
    """Real async implementation for Phase 2+."""
    from utils.audit_logger import log_node_complete

    new_queries = [q for q in state["research_plan"]
                   if q not in state["queries_issued"]]

    if not new_queries:
        logger.warning("[Scout] No new queries to execute")
        return {"raw_results": [], "queries_issued": []}

    logger.info(f"[Scout] Executing {len(new_queries)} queries in parallel")
    query_results = await asyncio.gather(
        *[_fetch_one_query(q, i) for i, q in enumerate(new_queries)],
        return_exceptions=True,
    )

    all_results = []
    for batch in query_results:
        if isinstance(batch, list):
            all_results.extend(batch)
        else:
            logger.warning(f"[Scout] Query batch failed: {batch}")

    all_results = [r for r in all_results if r.get("relevance", 0) >= MIN_RELEVANCE]
    all_results.sort(key=lambda r: r.get("relevance", 0), reverse=True)
    all_results = all_results[: MAX_SEARCH_RESULTS_PER_QUERY * len(new_queries)]

    seen_urls = set(r["url"] for r in state["raw_results"])
    deduped = [r for r in all_results if r["url"] not in seen_urls]

    log_node_complete("scout_agent", {"total_results": len(deduped), "queries": len(new_queries)})
    logger.info(f"[Scout] {len(deduped)} new results after dedup")

    return {"raw_results": deduped, "queries_issued": new_queries}
