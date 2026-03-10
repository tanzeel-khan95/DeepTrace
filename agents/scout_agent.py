"""
agents/scout_agent.py — Scout Agent: parallel search execution.

Dispatches all queries from research_plan simultaneously via asyncio.gather().
Primary: Tavily search. Deduplicates results by URL before returning.

Phase 1 (USE_MOCK=true): returns MOCK_SCOUT_RESULTS fixture directly.
Phase 2+ (USE_MOCK=false): executes real parallel searches.

Architecture position: second node in LangGraph pipeline, called by Supervisor.
"""
import asyncio
import logging
from config import USE_MOCK, MIN_RELEVANCE
from state.agent_state import AgentState
from mock_responses import MOCK_SCOUT_RESULTS
from utils.tracing import traceable

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

    new_queries = [q for q in state["research_plan"]
                   if q not in state["queries_issued"]]

    if not new_queries:
        logger.warning("[Scout] No new queries to execute")
        return {"raw_results": [], "queries_issued": []}

    logger.info(f"[Scout] Executing {len(new_queries)} queries in parallel")
    raw_batches = await asyncio.gather(*[tavily_search(q) for q in new_queries])

    all_results = []

    MIN_RESULTS_THRESHOLD = 2

    for i, (query, results) in enumerate(zip(new_queries, raw_batches)):
        if len(results) < MIN_RESULTS_THRESHOLD:
            logger.warning(
                f"[Scout] Low search coverage for query {i+1}: "
                f"{len(results)} results from Tavily for '{query[:60]}'"
            )

        for r in results:
            if r.get("relevance", 0) >= MIN_RELEVANCE:
                all_results.append(r)

    # Deduplicate by URL
    seen_urls = set(r["url"] for r in state["raw_results"])
    deduped = [r for r in all_results if r["url"] not in seen_urls]
    logger.info(f"[Scout] {len(deduped)} new results after dedup")

    return {"raw_results": deduped, "queries_issued": new_queries}
