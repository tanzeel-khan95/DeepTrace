"""
tavily_search.py — Tavily search API client (primary search).

Phase 1 (USE_MOCK=true): returns static fixture results.
Phase 2+ (USE_MOCK=false): calls real Tavily API.

Architecture position: called by scout_agent.py.
"""
import logging
from config import USE_MOCK, TAVILY_API_KEY, MIN_RELEVANCE, MAX_SEARCH_RESULTS_PER_QUERY
from utils.retry import get_search_bucket, with_retry

logger = logging.getLogger(__name__)

async def tavily_search(query: str) -> list:
    """Execute one Tavily search query. Returns list of result dicts."""
    if USE_MOCK:
        logger.debug(f"[Tavily] MOCK search: {query[:50]}")
        return _mock_results_for_query(query)

    import asyncio
    return await asyncio.to_thread(_sync_tavily_search, query)


def _sync_tavily_search(query: str) -> list:
    """Sync Tavily search — called via asyncio.to_thread. Phase 2."""
    try:
        from tavily import TavilyClient
        if not TAVILY_API_KEY:
            logger.error("[Tavily] TAVILY_API_KEY not set — returning empty results")
            return []

        client = TavilyClient(api_key=TAVILY_API_KEY)

        @with_retry(max_retries=2, base_delay=2.0)
        def _do_tavily_search(t_client, t_query, depth, max_results):
            return t_client.search(
                query=t_query,
                search_depth=depth,
                max_results=max_results,
                include_raw_content=False,
            )

        # Rate limit Tavily calls
        get_search_bucket().acquire()

        response = _do_tavily_search(
            client,
            query,
            "basic",
            MAX_SEARCH_RESULTS_PER_QUERY,
        )

        results = []
        for r in response.get("results", []):
            domain = _extract_domain(r.get("url", ""))
            relevance = float(r.get("score", 0.5))
            if relevance >= MIN_RELEVANCE:
                results.append({
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "content": r.get("content", ""),
                    "relevance": relevance,
                    "source_domain": domain,
                    "search_source": "tavily",
                })
        logger.info(f"[Tavily] Real search: '{query[:40]}' → {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"[Tavily] API error for '{query}': {e}")
        logger.warning("[Tavily] Falling back to mock results due to API error")
        from mock_responses import MOCK_SCOUT_RESULTS
        return MOCK_SCOUT_RESULTS["raw_results"][:2]


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
