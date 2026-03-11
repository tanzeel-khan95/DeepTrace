"""
anthropic_client.py — Singleton Anthropic client for DeepTrace.

All agents import get_client() from here. This ensures:
  - The client is only instantiated once (not per-call)
  - API key validation happens at startup
  - Easy to swap for a mock in tests
  - Budget guard is always applied after each call

Structured output: use call_llm_structured() with a Pydantic response_model to
enforce JSON schema via Anthropic output_config — no raw text parsing.

Architecture position: imported by all agents in Phase 2+.
Never import anthropic directly in agent files.
"""
import logging
from typing import List,Optional, Type, TypeVar

from pydantic import BaseModel

from utils.retry import get_llm_bucket, with_retry

logger = logging.getLogger(__name__)
_client = None

T = TypeVar("T", bound=BaseModel)


def get_client():
    """
    Return singleton Anthropic client.
    Validates API key on first call.
    Raises RuntimeError if ANTHROPIC_API_KEY is not set.
    """
    global _client
    if _client is None:
        from config import ANTHROPIC_API_KEY
        if not ANTHROPIC_API_KEY:
            raise RuntimeError(
                "[AnthropicClient] ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file. See Phase 2 API Keys section."
            )
        import anthropic
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        logger.info("[AnthropicClient] Client initialised")
    return _client


def call_llm(
    system_prompt: str,
    user_message: str,
    model: str,
    max_tokens: int,
    use_cache: bool = True,
) -> str:
    """
    Make one Anthropic API call with prompt caching on the system prompt.

    Args:
        system_prompt: The system instructions (cached between calls)
        user_message:  The user turn content
        model:         Model string from config.MODELS
        max_tokens:    Hard cap — always use MAX_TOKENS[ENV] from config
        use_cache:     Whether to apply Anthropic prompt caching to system prompt

    Returns:
        Raw text content from the model response

    Side effects:
        - Records token spend in budget_guard
        - Writes to LLM cache if LLM_CACHE_ENABLED=true
    """
    from config import LLM_CACHE_ENABLED
    from utils.llm_cache import get_cached, save_to_cache

    # Check cache first (record-replay for dev iteration)
    if LLM_CACHE_ENABLED:
        cached = get_cached(system_prompt, user_message, model)
        if cached is not None:
            logger.debug(f"[LLM Cache] HIT for model={model}")
            return cached

    client = get_client()

    @with_retry()
    def _do_create(inner_client, inner_model, inner_max_tokens, inner_system_block, inner_messages):
        return inner_client.messages.create(
            model=inner_model,
            max_tokens=inner_max_tokens,
            system=inner_system_block,
            messages=inner_messages,
        )

    # Build system block with prompt caching
    if use_cache:
        system_block = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},  # Cache system prompt
            }
        ]
    else:
        system_block = system_prompt

    # Rate limit Anthropic calls
    get_llm_bucket().acquire()

    response = _do_create(
        client,
        model,
        max_tokens,
        system_block,
        [{"role": "user", "content": user_message}],
    )

    text = response.content[0].text

    # Record spend for budget guard
    from utils.budget_guard import record_spend
    record_spend(
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        model=model,
    )

    # Structured audit logging
    try:
        from utils.audit_logger import log_llm_call

        log_llm_call(
            agent="anthropic_client",
            model=model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
    except Exception as e:  # best-effort, never break main flow
        logger.debug(f"[AuditLog] LLM call audit logging failed: {e}")

    try:
        from utils.tracing import log_llm_run
        log_llm_run(model, response.usage.input_tokens, response.usage.output_tokens)
    except Exception:
        pass

    # Save to cache
    if LLM_CACHE_ENABLED:
        save_to_cache(system_prompt, user_message, model, text)

    logger.info(
        f"[LLM] model={model} in={response.usage.input_tokens} "
        f"out={response.usage.output_tokens}"
    )
    return text


def _schema_for_model(response_model: Type[BaseModel]) -> dict:
    """
    Build Anthropic-compatible JSON Schema from a Pydantic model.

    Anthropic Structured Outputs have a few constraints that differ from the
    raw JSON Schema that Pydantic emits, notably:
      - Every object type must explicitly set additionalProperties=false
      - Some numeric constraints (minimum/maximum, etc.) are not supported

    This helper normalises the schema so that the API accepts it, while we
    still rely on Pydantic for full validation on the client side.
    """
    schema = response_model.model_json_schema()

    def _tweak(node: dict) -> None:
        if not isinstance(node, dict):
            return

        t = node.get("type")
        # Objects: Anthropic requires additionalProperties to be explicitly false
        if t == "object":
            if node.get("additionalProperties") is not False:
                node["additionalProperties"] = False

        # Numbers / integers: drop bounds Anthropic doesn't support
        if t in ("number", "integer"):
            for key in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf"):
                node.pop(key, None)

        # Recurse into nested schemas
        for key in ("properties", "patternProperties", "$defs", "definitions"):
            sub = node.get(key)
            if isinstance(sub, dict):
                for v in sub.values():
                    _tweak(v)

        items = node.get("items")
        if isinstance(items, dict):
            _tweak(items)
        elif isinstance(items, list):
            for v in items:
                _tweak(v)

        for key in ("oneOf", "anyOf", "allOf"):
            arr = node.get(key)
            if isinstance(arr, list):
                for v in arr:
                    _tweak(v)

    _tweak(schema)
    return schema

class SupervisorPlanResponse(BaseModel):
    """Enforced JSON shape for supervisor_plan LLM response."""
    research_plan: List[str]
    gaps_remaining: List[str]

def call_llm_structured(
    system_prompt: str,
    user_message: str,
    model: str,
    max_tokens: int,
    response_model: Type[T],
    use_cache: bool = True,
) -> T:
    """
    Call Anthropic with enforced JSON schema (structured output). Returns
    validated Pydantic model instance — no raw text or manual JSON parsing.

    Uses output_config.format.json_schema so the API returns only valid JSON
    matching the response_model schema. Response is parsed and validated
    with response_model.model_validate().

    Args:
        system_prompt: System instructions (cached when use_cache=True)
        user_message: User turn content
        model: Model string from config.MODELS
        max_tokens: Hard cap — use MAX_TOKENS[ENV]
        response_model: Pydantic model class for the response shape
        use_cache: Whether to use prompt caching and LLM response cache

    Returns:
        Instance of response_model with validated data

    Raises:
        ValidationError: If response does not match schema (should be rare
        when API enforces schema).
    """
    from config import LLM_CACHE_ENABLED
    from utils.llm_cache import get_cached, save_to_cache

    cache_key_suffix = f"::structured::{response_model.__name__}"
    if LLM_CACHE_ENABLED:
        cached = get_cached(system_prompt, user_message + cache_key_suffix, model)
        if cached is not None:
            logger.debug(f"[LLM Cache] HIT (structured) for model={model}")
            # Cached value is JSON string for the response_model
            return response_model.model_validate_json(cached)

    client = get_client()

    if use_cache:
        system_block = [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    else:
        system_block = system_prompt

    # Preferred path: SDK helper that handles schema transformation + validation
    try:
        response = client.messages.parse(
            model=model,
            max_tokens=max_tokens,
            system=system_block,
            messages=[{"role": "user", "content": user_message}],
            output_format=response_model,
        )
        
        parsed = response.parsed_output

        from utils.budget_guard import record_spend
        record_spend(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=model,
        )
        try:
            from utils.tracing import log_llm_run
            log_llm_run(model, response.usage.input_tokens, response.usage.output_tokens)
        except Exception:
            pass

        if LLM_CACHE_ENABLED and parsed is not None:
            # Cache as JSON string for future replays
            save_to_cache(
                system_prompt,
                user_message + cache_key_suffix,
                model,
                parsed.model_dump_json(),
            )

        logger.info(
            f"[LLM] model={model} (structured/parse) "
            f"in={response.usage.input_tokens} out={response.usage.output_tokens}"
        )
        return parsed

    except Exception as e:
        logger.error(f"[LLM] Error calling {model}: {e}")
