"""
entity_canon.py — Entity name canonicalization and deduplication.

Merges near-duplicate entities before writing to Neo4j.
Uses string similarity (difflib) — no ML model needed.

Examples of duplicates this catches:
  "Timothy Overturf"  ↔  "Tim Overturf"       → merge to "Timothy Overturf"
  "Sisu Capital LLC"  ↔  "Sisu Capital"        → merge to "Sisu Capital LLC"
  "SEC"               ↔  "U.S. Securities and Exchange Commission" → keep both (too different)

Architecture position: called by agents/graph_builder.py before Neo4j write.
"""
import logging
from difflib import SequenceMatcher
from typing import List, Tuple

logger = logging.getLogger(__name__)


def similarity(a: str, b: str) -> float:
    """Return string similarity ratio 0.0–1.0 using SequenceMatcher."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def canonicalize_entities(entities: List[dict]) -> Tuple[List[dict], dict]:
    """
    Deduplicate and canonicalize a list of entity dicts.

    Args:
        entities: List of entity dicts (from Pydantic model_dump())

    Returns:
        Tuple of:
          - cleaned entity list (duplicates removed, canonical names applied)
          - merge_map: {old_entity_id → canonical_entity_id} for fixing relationships
    """
    from config import ENTITY_SIMILARITY_THRESHOLD
    from utils.audit_logger import log_entity_merged

    if not entities:
        return [], {}

    canonical = []
    merge_map = {}

    for entity in entities:
        name = entity.get("name", "").strip()
        etype = entity.get("entity_type", "")
        eid = entity.get("entity_id", "")

        best_match = None
        best_score = 0.0

        for canon_entity in canonical:
            if canon_entity.get("entity_type") != etype:
                continue
            score = similarity(name, canon_entity.get("name", ""))
            if score > best_score:
                best_score = score
                best_match = canon_entity

        if best_match and best_score >= ENTITY_SIMILARITY_THRESHOLD:
            canonical_id = best_match["entity_id"]
            merge_map[eid] = canonical_id

            if len(name) > len(best_match.get("name", "")):
                best_match["name"] = name

            merged_attrs = {**entity.get("attributes", {}), **best_match.get("attributes", {})}
            best_match["attributes"] = merged_attrs

            best_match["confidence"] = max(
                best_match.get("confidence", 0),
                entity.get("confidence", 0),
            )

            log_entity_merged(best_match["name"], name, best_score)
            logger.info(f"[Canon] Merged '{name}' → '{best_match['name']}' (score={best_score:.2f})")

        else:
            canonical.append(entity.copy())
            merge_map[eid] = eid

    logger.info(f"[Canon] {len(entities)} entities → {len(canonical)} after dedup")
    return canonical, merge_map


def remap_relationships(relationships: List[dict], merge_map: dict) -> List[dict]:
    """
    Update relationship from_id/to_id to point to canonical entity IDs.
    Drops relationships where either endpoint was merged into another entity
    and would create a self-loop (from_id == to_id after remapping).
    """
    updated = []
    for rel in relationships:
        new_from = merge_map.get(rel.get("from_id"), rel.get("from_id"))
        new_to = merge_map.get(rel.get("to_id"), rel.get("to_id"))

        if new_from == new_to:
            logger.debug(f"[Canon] Dropping self-loop relationship: {rel.get('rel_type')}")
            continue

        updated_rel = rel.copy()
        updated_rel["from_id"] = new_from
        updated_rel["to_id"] = new_to
        updated.append(updated_rel)

    return updated
