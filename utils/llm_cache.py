"""
llm_cache.py — Record-and-replay LLM response cache for Phase 2 development.

Saves every real API response to .llm_cache/{hash}.json on first call.
Subsequent identical calls (same model + same prompts) return the cached response.

This means you can iterate on Streamlit UI, report formatting, and graph layout
without paying for repeated identical research runs.

Toggle: LLM_CACHE_ENABLED=true in .env (default true in dev).
Clear:  rm -rf .llm_cache/

Architecture position: called by utils/anthropic_client.py.
"""
import hashlib
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def _cache_key(system_prompt: str, user_message: str, model: str) -> str:
    """Generate deterministic cache key from call parameters."""
    raw = f"{model}::{system_prompt}::{user_message}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_path(key: str) -> str:
    from config import LLM_CACHE_DIR
    os.makedirs(LLM_CACHE_DIR, exist_ok=True)
    return os.path.join(LLM_CACHE_DIR, f"{key}.json")


def get_cached(system_prompt: str, user_message: str, model: str) -> Optional[str]:
    """
    Return cached response text if it exists, else None.
    """
    from config import LLM_CACHE_ENABLED
    if not LLM_CACHE_ENABLED:
        return None

    key = _cache_key(system_prompt, user_message, model)
    path = _cache_path(key)

    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            logger.debug(f"[LLMCache] HIT: {key[:12]}...")
            return data.get("response_text")
        except Exception as e:
            logger.warning(f"[LLMCache] Read error: {e}")
    return None


def save_to_cache(
    system_prompt: str,
    user_message: str,
    model: str,
    response_text: str,
) -> None:
    """
    Save a real API response to disk for future replay.
    """
    from config import LLM_CACHE_ENABLED
    if not LLM_CACHE_ENABLED:
        return

    key = _cache_key(system_prompt, user_message, model)
    path = _cache_path(key)

    try:
        with open(path, "w") as f:
            json.dump({
                "model": model,
                "key": key,
                "response_text": response_text,
            }, f, indent=2)
        logger.debug(f"[LLMCache] SAVED: {key[:12]}...")
    except Exception as e:
        logger.warning(f"[LLMCache] Write error: {e}")


def clear_cache() -> int:
    """Delete all cache files. Returns count deleted."""
    from config import LLM_CACHE_DIR
    if not os.path.exists(LLM_CACHE_DIR):
        return 0
    count = 0
    for f in os.listdir(LLM_CACHE_DIR):
        if f.endswith(".json"):
            os.remove(os.path.join(LLM_CACHE_DIR, f))
            count += 1
    logger.info(f"[LLMCache] Cleared {count} cached responses")
    return count


def cache_stats() -> dict:
    """Return cache hit stats for the current session."""
    from config import LLM_CACHE_DIR
    if not os.path.exists(LLM_CACHE_DIR):
        return {"entries": 0, "size_kb": 0}
    files = [f for f in os.listdir(LLM_CACHE_DIR) if f.endswith(".json")]
    size = sum(os.path.getsize(os.path.join(LLM_CACHE_DIR, f)) for f in files)
    return {"entries": len(files), "size_kb": round(size / 1024, 1)}
