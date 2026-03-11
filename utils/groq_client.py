"""
groq_client.py — Groq client for DeepTrace.

Provides a thin wrapper around the Groq SDK with a similar interface to
utils/anthropic_client.py so agents can swap providers based on model name.

Structured output is implemented via Groq JSON mode + Pydantic validation.
"""
import json
import logging
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from config import GROQ_API_KEY, GROQ_REQUESTS_PER_MIN
from utils.llm_cache import get_cached, save_to_cache
from utils.budget_guard import record_spend
from utils.retry import with_retry, get_groq_bucket

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_client = None


def get_groq_client():
    """
    Return singleton Groq client.
    Validates API key on first call.
    """
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise RuntimeError(
                "[GroqClient] GROQ_API_KEY is not set. "
                "Add it to your .env file to use Groq-backed models."
            )
        from groq import Groq

        _client = Groq(api_key=GROQ_API_KEY)
        logger.info(
            "[GroqClient] Client initialised with rate limit "
            f"{GROQ_REQUESTS_PER_MIN} req/min"
        )
    return _client


def call_groq(
    system_prompt: str,
    user_message: str,
    model: str,
    max_tokens: int,
    use_cache: bool = True,
) -> str:
    """
    Unstructured Groq call returning raw text.

    Mirrors utils.anthropic_client.call_llm for non-JSON use cases.
    """
    cache_enabled = True

    if cache_enabled:
        cached = get_cached(system_prompt, user_message, model)
        if cached is not None:
            logger.debug(f"[Groq LLM Cache] HIT for model={model}")
            return cached

    client = get_groq_client()

    @with_retry()
    def _do_create():
        return client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

    get_groq_bucket().acquire()
    response = _do_create()

    content = response.choices[0].message.content or ""

    usage = getattr(response, "usage", None)
    if usage is not None:
        record_spend(
            input_tokens=getattr(usage, "prompt_tokens", 0),
            output_tokens=getattr(usage, "completion_tokens", 0),
            model=model,
        )

    if cache_enabled:
        save_to_cache(system_prompt, user_message, model, content)

    logger.info("[Groq LLM] model=%s", model)
    return content


def _build_schema_instruction(response_model: Type[BaseModel]) -> str:
    schema = response_model.model_json_schema()
    schema_str = json.dumps(schema, indent=2)
    return (
        "You are a JSON-only API.\n"
        "You MUST respond with a single JSON object that strictly matches this schema.\n"
        "Do not include any extra keys, comments, or prose.\n"
        f"JSON Schema:\n{schema_str}"
    )


def call_groq_structured(
    system_prompt: str,
    user_message: str,
    model: str,
    max_tokens: int,
    response_model: Type[T],
    use_cache: bool = True,
) -> T:
    """
    Groq structured output using JSON mode + Pydantic validation.
    """
    cache_suffix = f"::structured::{response_model.__name__}"
    cache_enabled = True

    if cache_enabled:
        cached = get_cached(system_prompt, user_message + cache_suffix, model)
        if cached is not None:
            logger.debug(f"[Groq LLM Cache] HIT (structured) for model={model}")
            return response_model.model_validate_json(cached)

    client = get_groq_client()

    schema_instruction = _build_schema_instruction(response_model)
    combined_system = f"{system_prompt.strip()}\n\n{schema_instruction}"

    def _parse_and_record(raw_content: str, usage) -> T:
        parsed = response_model.model_validate_json(raw_content)

        if usage is not None:
            record_spend(
                input_tokens=getattr(usage, "prompt_tokens", 0),
                output_tokens=getattr(usage, "completion_tokens", 0),
                model=model,
            )

        if cache_enabled:
            save_to_cache(
                system_prompt,
                user_message + cache_suffix,
                model,
                parsed.model_dump_json(),
            )

        return parsed

    @with_retry()
    def _do_create(current_user_message: str):
        return client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": combined_system},
                {"role": "user", "content": current_user_message},
            ],
        )

    get_groq_bucket().acquire()

    # First attempt
    response = _do_create(user_message)
    content = response.choices[0].message.content or ""
    usage = getattr(response, "usage", None)

    try:
        return _parse_and_record(content, usage)
    except ValidationError as e:
        logger.warning(
            "[Groq Structured] Validation failed on first attempt for model=%s: %s",
            model,
            e,
        )

        # One corrective retry with explicit error message
        corrective_user = (
            f"{user_message}\n\n"
            "The previous JSON did not validate. "
            "Fix ALL issues mentioned below and return a new JSON object that "
            "fully satisfies the schema. Do not add commentary.\n"
            f"Validation error: {str(e)}"
        )

        response = _do_create(corrective_user)
        content = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)

        try:
            return _parse_and_record(content, usage)
        except ValidationError as e2:
            logger.error(
                "[Groq Structured] Validation failed after retry for model=%s: %s",
                model,
                e2,
            )
            return response_model()  # type: ignore[call-arg]

