"""
gemini_client.py — Gemini client for DeepTrace.

Provides a thin wrapper around the Google Gemini SDK with a similar interface to
utils/groq_client.py so agents can swap providers based on model name.

Structured output is implemented via Gemini native JSON mode + Pydantic validation.
"""
import logging
from typing import Type, TypeVar, Any, Dict

from pydantic import BaseModel

from config import GOOGLE_API_KEY, GEMINI_REQUESTS_PER_MIN
from utils.llm_cache import get_cached, save_to_cache
from utils.budget_guard import record_spend
from utils.retry import with_retry, get_gemini_bucket

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_client = None


def get_gemini_client():
    """
    Return singleton Gemini client.
    Validates API key on first call.
    """
    global _client
    if _client is None:
        if not GOOGLE_API_KEY:
            raise RuntimeError(
                "[GeminiClient] GOOGLE_API_KEY is not set. "
                "Add it to your .env file to use Gemini-backed models."
            )
        try:
            from google import genai
        except ImportError as e:
            raise RuntimeError(
                "[GeminiClient] google-genai package is not installed. "
                "Add `google-genai` to requirements.txt."
            ) from e

        _client = genai.Client(api_key=GOOGLE_API_KEY)
        logger.info(
            "[GeminiClient] Client initialised with rate limit "
            f"{GEMINI_REQUESTS_PER_MIN} req/min"
        )
    return _client


def _estimate_usage_from_response(response) -> tuple[int, int]:
    """
    Best-effort extraction of input/output token usage from a Gemini response.
    Falls back to (0, 0) if usage is unavailable.
    """
    try:
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return 0, 0
        input_tokens = getattr(usage, "prompt_token_count", 0) or 0
        output_tokens = getattr(usage, "candidates_token_count", 0) or 0
        return int(input_tokens), int(output_tokens)
    except Exception:
        return 0, 0


def _strip_additional_properties(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gemini's response_schema does not support `additionalProperties`.
    Recursively remove it from a Pydantic JSON schema dict.
    """
    if "additionalProperties" in schema:
        schema.pop("additionalProperties", None)
    for key, value in list(schema.items()):
        if isinstance(value, dict):
            schema[key] = _strip_additional_properties(value)
        elif isinstance(value, list):
            schema[key] = [
                _strip_additional_properties(v) if isinstance(v, dict) else v
                for v in value
            ]
    return schema


def call_gemini(
    system_prompt: str,
    user_message: str,
    model: str,
    max_tokens: int,
    use_cache: bool = True,
) -> str:
    """
    Unstructured Gemini call returning raw text.

    Mirrors utils.groq_client.call_groq for non-JSON use cases.
    """
    cache_enabled = True

    if cache_enabled and use_cache:
        cached = get_cached(system_prompt, user_message, model)
        if cached is not None:
            logger.debug(f"[Gemini LLM Cache] HIT for model={model}")
            return cached

    client = get_gemini_client()

    @with_retry()
    def _do_generate():
        # New google-genai SDK: generate_content is accessed via client.models
        return client.models.generate_content(
            model=model,
            contents=[
                {"role": "user", "parts": [{"text": f"{system_prompt}\n\n{user_message}"}]}
            ],
            config={"max_output_tokens": max_tokens},
        )

    get_gemini_bucket().acquire()
    response = _do_generate()

    text = ""
    try:
        if response and getattr(response, "candidates", None):
            parts = response.candidates[0].content.parts
            text = "".join(getattr(p, "text", "") for p in parts)
    except Exception as e:
        logger.warning(f"[Gemini LLM] Failed to read response text: {e}")

    in_tokens, out_tokens = _estimate_usage_from_response(response)
    if in_tokens or out_tokens:
        record_spend(input_tokens=in_tokens, output_tokens=out_tokens, model=model)

    if cache_enabled and use_cache:
        save_to_cache(system_prompt, user_message, model, text)

    logger.info("[Gemini LLM] model=%s", model)
    return text


def call_gemini_structured(
    system_prompt: str,
    user_message: str,
    model: str,
    max_tokens: int,
    response_model: Type[T],
    use_cache: bool = True,
) -> T:
    """
    Gemini structured output using native JSON response_schema + Pydantic validation.
    """
    cache_suffix = f"::structured::{response_model.__name__}"
    cache_enabled = True

    if cache_enabled and use_cache:
        cached = get_cached(system_prompt, user_message + cache_suffix, model)
        if cached is not None:
            logger.debug(f"[Gemini LLM Cache] HIT (structured) for model={model}")
            return response_model.model_validate_json(cached)

    client = get_gemini_client()

    from google.genai import types as genai_types  # type: ignore[import-not-found]

    # Build a JSON schema from the Pydantic model and strip unsupported keys
    # (Gemini does not allow `additionalProperties` in response_schema).
    raw_schema = response_model.model_json_schema()
    cleaned_schema = _strip_additional_properties(raw_schema)

    generation_config = genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=cleaned_schema,
        max_output_tokens=max_tokens,
    )

    @with_retry()
    def _do_generate(current_user_message: str):
        return client.models.generate_content(
            model=model,
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"text": f"{system_prompt}\n\n{current_user_message}"}
                    ],
                }
            ],
            config=generation_config,
        )

    get_gemini_bucket().acquire()

    response = _do_generate(user_message)

    # The SDK returns JSON text in the first candidate's content.
    raw_json = ""
    try:
        if response and getattr(response, "candidates", None):
            parts = response.candidates[0].content.parts
            raw_json = "".join(getattr(p, "text", "") for p in parts)
    except Exception as e:
        logger.warning(f"[Gemini Structured] Failed to read response text: {e}")

    in_tokens, out_tokens = _estimate_usage_from_response(response)
    if in_tokens or out_tokens:
        record_spend(input_tokens=in_tokens, output_tokens=out_tokens, model=model)

    parsed = response_model.model_validate_json(raw_json or "{}")

    if cache_enabled and use_cache:
        save_to_cache(
            system_prompt,
            user_message + cache_suffix,
            model,
            parsed.model_dump_json(),
        )

    logger.info("[Gemini Structured] Parsed response for model=%s", model)
    return parsed

