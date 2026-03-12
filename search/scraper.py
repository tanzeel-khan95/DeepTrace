"""
Async full-page content fetcher.

Used by deep_dive_agent to fetch complete page content for top results.
When USE_MOCK=true returns stub content.
"""
import logging
from config import USE_MOCK

logger = logging.getLogger(__name__)

async def fetch_page(url: str) -> str:
    """Fetch full text content of a URL. Returns empty string on failure."""
    if USE_MOCK:
        return f"[MOCK PAGE CONTENT for {url}]"

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
