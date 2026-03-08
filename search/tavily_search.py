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
