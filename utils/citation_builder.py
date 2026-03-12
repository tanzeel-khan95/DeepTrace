"""
Build source citations from facts and raw search results.

Matches each fact's source_url to a raw result to attach title, snippet, and
trust-based confidence. Citations are merged into AgentState for the report
with the exact source URL, domain, snippet, and confidence.
"""
import logging
from datetime import datetime, timezone
from typing import List

logger = logging.getLogger(__name__)


def build_citations(facts: list, raw_results: list) -> List[dict]:
    """
    Build citations by matching each fact's source_url to a raw search result.

    Args:
        facts:       List of Fact dicts (with source_url field)
        raw_results: List of raw search result dicts (from Scout)

    Returns:
        List of Citation dicts
    """
    results_by_url = {}
    for r in raw_results:
        url = r.get("url", "")
        if url:
            results_by_url[url] = r

    citations = []
    now = datetime.now(timezone.utc).isoformat()

    for fact in facts:
        url = fact.get("source_url", "") if isinstance(fact, dict) else getattr(fact, "source_url", "")
        if not url:
            continue

        result = results_by_url.get(url)
        domain = fact.get("source_domain", "") if isinstance(fact, dict) else getattr(fact, "source_domain", "")
        snippet = ""

        if result:
            raw_snip = fact.get("raw_source_snippet", "") if isinstance(fact, dict) else getattr(fact, "raw_source_snippet", "")
            snippet = raw_snip or result.get("content", "")[:300]
            title = result.get("title", domain)
        else:
            title = domain
            snippet = fact.get("raw_source_snippet", "") if isinstance(fact, dict) else getattr(fact, "raw_source_snippet", "")

        from evaluation.confidence_scorer import get_domain_trust
        conf = get_domain_trust(domain)

        fact_id = fact.get("fact_id", "") if isinstance(fact, dict) else getattr(fact, "fact_id", "")

        citations.append({
            "fact_id": fact_id,
            "url": url,
            "domain": domain,
            "title": title,
            "snippet": (snippet or "")[:400],
            "accessed_at": now,
            "confidence": conf,
        })

    logger.info(f"[CitationBuilder] Built {len(citations)} citations for {len(facts)} facts")
    return citations
