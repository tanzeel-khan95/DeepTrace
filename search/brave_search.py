"""
brave_search.py — Brave Search API client (backup/scale search).

Used when Tavily returns < 3 results or is rate-limited.
Phase 1 (USE_MOCK=true): returns static fixture results.

Architecture position: called by scout_agent.py as fallback.
"""
import logging
from config import USE_MOCK, BRAVE_SEARCH_API_KEY

logger = logging.getLogger(__name__)

async def brave_search(query: str) -> list:
    """Execute one Brave search query. Returns list of result dicts."""
    if USE_MOCK:
        logger.debug(f"[Brave] MOCK search: {query[:50]}")
        from mock_responses import MOCK_SCOUT_RESULTS
        return MOCK_SCOUT_RESULTS["raw_results"][:2]

    try:
        import aiohttp
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"Accept": "application/json", "X-Subscription-Token": BRAVE_SEARCH_API_KEY}
        params  = {"q": query, "count": 5}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                data = await resp.json()
        results = []
        for r in data.get("web", {}).get("results", []):
            results.append({
                "url":           r.get("url", ""),
                "title":         r.get("title", ""),
                "content":       r.get("description", ""),
                "relevance":     0.65,
                "source_domain": _extract_domain(r.get("url", "")),
            })
        return results
    except Exception as e:
        logger.error(f"[Brave] Error for query '{query}': {e}")
        return []


def _extract_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""
