"""
openai_client.py — OpenAI client for DeepTrace.

Provides a thin wrapper around the OpenAI SDK with a similar interface to
utils/groq_client.py so agents can swap providers based on model name.

Structured output is implemented via OpenAI JSON mode + Pydantic validation.
"""
import json
import logging
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from config import OPENAI_API_KEY, OPENAI_REQUESTS_PER_MIN
from utils.llm_cache import get_cached, save_to_cache
from utils.budget_guard import record_spend
from utils.retry import with_retry, get_openai_bucket

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_client = None


def get_openai_client():
    """
    Return singleton OpenAI client.
    Validates API key on first call.
    """
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError(
                "[OpenAIClient] OPENAI_API_KEY is not set. "
                "Add it to your .env file to use OpenAI-backed models."
            )
        from openai import OpenAI

        _client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info(
            "[OpenAIClient] Client initialised with rate limit "
            f"{OPENAI_REQUESTS_PER_MIN} req/min"
        )
    return _client


def call_openai(
    system_prompt: str,
    user_message: str,
    model: str,
    max_tokens: int,
    use_cache: bool = True,
) -> str:
    """
    Unstructured OpenAI call returning raw text.

    Mirrors utils.groq_client.call_groq for non-JSON use cases.
    """
    cache_enabled = True

    if cache_enabled and use_cache:
        cached = get_cached(system_prompt, user_message, model)
        if cached is not None:
            logger.debug(f"[OpenAI LLM Cache] HIT for model={model}")
            return cached

    client = get_openai_client()

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

    get_openai_bucket().acquire()
    response = _do_create()

    content = response.choices[0].message.content or ""

    usage = getattr(response, "usage", None)
    if usage is not None:
        record_spend(
            input_tokens=getattr(usage, "prompt_tokens", 0),
            output_tokens=getattr(usage, "completion_tokens", 0),
            model=model,
        )
        try:
            from utils.tracing import log_llm_run
            log_llm_run(model, getattr(usage, "prompt_tokens", 0), getattr(usage, "completion_tokens", 0))
        except Exception:
            pass

    if cache_enabled and use_cache:
        save_to_cache(system_prompt, user_message, model, content)

    logger.info("[OpenAI LLM] model=%s", model)
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


def call_openai_structured(
    system_prompt: str,
    user_message: str,
    model: str,
    max_tokens: int,
    response_model: Type[T],
    use_cache: bool = True,
) -> T:
    """
    OpenAI structured output using JSON mode + Pydantic validation.
    """
    cache_suffix = f"::structured::{response_model.__name__}"
    cache_enabled = True

    if cache_enabled and use_cache:
        cached = get_cached(system_prompt, user_message + cache_suffix, model)
        if cached is not None:
            logger.debug(f"[OpenAI LLM Cache] HIT (structured) for model={model}")
            return response_model.model_validate_json(cached)

    client = get_openai_client()

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
            try:
                from utils.tracing import log_llm_run
                log_llm_run(model, getattr(usage, "prompt_tokens", 0), getattr(usage, "completion_tokens", 0))
            except Exception:
                pass

        if cache_enabled and use_cache:
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

    get_openai_bucket().acquire()

    # First attempt
    response = _do_create(user_message)
    content = response.choices[0].message.content or ""
    usage = getattr(response, "usage", None)

    try:
        return _parse_and_record(content, usage)
    except ValidationError as e:
        logger.warning(
            "[OpenAI Structured] Validation failed on first attempt for model=%s: %s",
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
                "[OpenAI Structured] Validation failed after retry for model=%s: %s",
                model,
                e2,
            )
            return response_model()  # type: ignore[call-arg]
