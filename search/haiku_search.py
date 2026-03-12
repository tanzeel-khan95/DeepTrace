"""
Anthropic Haiku web search tool integration.

Uses the Anthropic web_search_20250305 tool to run web searches via Haiku.
Supplements Tavily results when Tavily has low result counts or when
targeted site-specific searches are needed.

Returns the same result dict format as tavily_search.py for drop-in compatibility.
"""
import asyncio
import logging
import re
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
    from config import USE_MOCK, HAIKU_WEB_SEARCH_ENABLED

    if USE_MOCK:
        logger.debug("[HaikuSearch] MOCK mode — returning empty list")
        return []

    if not HAIKU_WEB_SEARCH_ENABLED:
        logger.debug("[HaikuSearch] Disabled via config")
        return []

    return await asyncio.to_thread(_sync_haiku_search, query, max_results)


def _sync_haiku_search(query: str, max_results: int) -> List[dict]:
    """Sync implementation — called via asyncio.to_thread."""
    from config import MODELS

    from utils.anthropic_client import get_client
    from utils.audit_logger import log_search_query
    from utils.retry import get_search_bucket

    try:
        client = get_client()

        get_search_bucket().acquire()

        response = client.messages.create(
            model=MODELS.get("scout", "claude-haiku-4-5-20251001"),
            max_tokens=1500,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Search the web for: {query}\n\n"
                        f"Return the top {max_results} most relevant results. "
                        f"For each result include the URL and a summary of the content."
                    ),
                }
            ],
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
        block_type = getattr(block, "type", None)
        # Tool result blocks contain structured search results
        if block_type == "tool_result":
            content = getattr(block, "content", None) or []
            for item in content:
                if hasattr(item, "text") and item.text:
                    results.extend(_parse_text_results(item.text))
        # Text blocks may contain formatted search summaries
        elif block_type == "text":
            text = getattr(block, "text", None) or ""
            if text:
                results.extend(_parse_text_results(text))

    # Deduplicate by URL
    seen_urls = set()
    deduped = []
    for r in results:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            deduped.append(r)

    return deduped


def _parse_text_results(text: str) -> List[dict]:
    """Extract URL + content pairs from Haiku text response."""
    results = []
    url_pattern = re.compile(r"https?://[^\s\)\]]+")
    urls = url_pattern.findall(text)

    for url in urls:
        domain = _extract_domain(url)
        idx = text.find(url)
        start = max(0, idx - 100)
        end = min(len(text), idx + 300)
        snippet = text[start:end].strip()

        results.append({
            "url": url,
            "title": domain,
            "content": snippet,
            "relevance": 0.70,
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
