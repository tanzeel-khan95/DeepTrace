"""
scraper.py — Async full-page content fetcher.

Used by deep_dive_agent in Phase 2+ to fetch complete page content for top results.
Phase 1 (USE_MOCK=true): returns stub content.

Architecture position: called by deep_dive_agent.py in Phase 2+.
"""
import logging
from config import USE_MOCK

logger = logging.getLogger(__name__)

async def fetch_page(url: str) -> str:
    """Fetch full text content of a URL. Returns empty string on failure."""
    if USE_MOCK:
        return f"[MOCK PAGE CONTENT for {url}] This is stub content for Phase 1."

    try:
        import aiohttp
        headers = {"User-Agent": "DeepTrace Research Agent 1.0"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.text()
                logger.warning(f"[Scraper] HTTP {resp.status} for {url}")
                return ""
    except Exception as e:
        logger.error(f"[Scraper] Failed to fetch {url}: {e}")
        return ""
