"""
fact_utils.py — Helpers for normalising and merging extracted facts.

Used by Deep Dive to collapse near-duplicate claims into a single,
better-supported Fact object.
"""
import re
from typing import Dict, List, Tuple

from state.agent_state import Fact


_WHITESPACE_RE = re.compile(r"\s+")


def _normalise_claim(claim: str) -> str:
    """
    Lightweight normalisation for fact.claim strings used as a grouping key.

    - Lowercase
    - Collapse whitespace
    - Strip leading/trailing punctuation and whitespace
    """
    text = claim.strip().lower()
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip(" .,:;!-")


def merge_duplicate_facts(facts: List[Fact]) -> List[Fact]:
    """
    Merge near-identical facts based on their normalised claim text and category.

    For each (normalised_claim, category) group:
    - Keep the fact with highest confidence as the representative
    - Union entities_mentioned and supporting_fact_ids (deduplicated)

    Returns a new list of Fact objects with potentially fewer entries.
    """
    if not facts:
        return facts

    groups: Dict[Tuple[str, str], List[Fact]] = {}
    for f in facts:
        key = (_normalise_claim(f.claim), f.category)
        groups.setdefault(key, []).append(f)

    merged: List[Fact] = []
    for _, group in groups.items():
        if len(group) == 1:
            merged.append(group[0])
            continue

        # Choose the highest-confidence fact as the base.
        base = max(group, key=lambda f: f.confidence)

        # Build merged lists, preserving order but removing duplicates.
        def _merge_list(attr: str) -> List[str]:
            seen = set()
            combined: List[str] = []
            for g in group:
                for item in getattr(g, attr, []):
                    if item not in seen:
                        seen.add(item)
                        combined.append(item)
            return combined

        entities_mentioned = _merge_list("entities_mentioned")
        supporting_ids = _merge_list("supporting_fact_ids")

        merged.append(
            Fact(
                fact_id=base.fact_id,
                claim=base.claim,
                source_url=base.source_url,
                source_domain=base.source_domain,
                confidence=base.confidence,
                category=base.category,
                entities_mentioned=entities_mentioned,
                supporting_fact_ids=supporting_ids,
                raw_source_snippet=base.raw_source_snippet,
            )
        )

    return merged

