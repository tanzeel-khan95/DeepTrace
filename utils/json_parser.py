"""
json_parser.py — Safe JSON extraction from LLM responses.

LLMs sometimes wrap JSON in markdown fences or add preamble text.
This module strips that and returns a clean dict/list, or raises a
structured error so agents can retry intelligently.

Architecture position: imported by all agents in Phase 2+.
"""
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class LLMParseError(Exception):
    """Raised when LLM output cannot be parsed as valid JSON."""
    def __init__(self, raw_text: str, reason: str):
        self.raw_text = raw_text
        self.reason = reason
        super().__init__(f"LLMParseError: {reason}\nRaw: {raw_text[:200]}")


def extract_json(raw_text: str) -> Any:
    """
    Extract JSON from raw LLM response text.

    Handles these common LLM formatting issues:
      - ```json ... ``` fences
      - ``` ... ``` fences (no language tag)
      - Leading explanation text before the JSON object
      - Trailing text after closing brace/bracket
      - Single quotes instead of double quotes (Haiku sometimes does this)

    Returns:
        Parsed Python dict or list

    Raises:
        LLMParseError if no valid JSON can be extracted
    """
    text = raw_text.strip()

    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object or array within the text
    for pattern in [r"\{.*\}", r"\[.*\]"]:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    # Last resort: fix single quotes (Haiku quirk)
    try:
        fixed = text.replace("'", '"')
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    raise LLMParseError(raw_text, "No valid JSON found after all extraction attempts")


def safe_extract_json(raw_text: str, fallback: Any = None) -> Any:
    """
    Like extract_json but returns fallback instead of raising on failure.
    Use when you have a reasonable default and don't want to crash.
    """
    try:
        return extract_json(raw_text)
    except LLMParseError as e:
        logger.warning(f"[JSONParser] Falling back to default: {e.reason}")
        return fallback
