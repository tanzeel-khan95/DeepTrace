"""
retry.py — Rate limiting and retry logic for all external API calls.

Wraps Anthropic and Tavily calls with:
  - Exponential backoff on rate limit errors (HTTP 429 / RateLimitError)
  - Jitter to prevent thundering herd on parallel agent calls
  - Maximum retry cap (configurable via LLM_MAX_RETRIES in config)
  - Token bucket rate limiter to stay within Haiku tier-1 limits (50 req/min)

Architecture position: imported by utils/anthropic_client.py and search/tavily_search.py.
"""
import asyncio
import functools
import logging
import random
import time
import threading
from typing import Callable, Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Token Bucket Rate Limiter (thread-safe for sync calls)
# ─────────────────────────────────────────────────────────────────────────────


class TokenBucket:
    """
    Thread-safe token bucket rate limiter.
    Allows `rate` requests per 60 seconds.
    Blocks the calling thread until a token is available.
    """

    def __init__(self, rate: int = 50):
        self._rate = rate  # tokens per minute
        self._tokens = float(rate)
        self._last_fill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a token is available. Thread-safe."""
        with self._lock:
            now = time.monotonic()
            delta = now - self._last_fill
            self._tokens = min(
                float(self._rate),
                self._tokens + delta * (self._rate / 60.0),
            )
            self._last_fill = now
            if self._tokens < 1.0:
                wait = (1.0 - self._tokens) / (self._rate / 60.0)
                logger.debug(f"[RateLimit] Throttling — waiting {wait:.2f}s")
                time.sleep(wait)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0


# Global rate limiter instances — one per external service
_llm_bucket = None
_search_bucket = None
_groq_bucket = None
_gemini_bucket = None
_openai_bucket = None


def get_llm_bucket() -> TokenBucket:
    global _llm_bucket
    if _llm_bucket is None:
        from config import LLM_REQUESTS_PER_MIN

        _llm_bucket = TokenBucket(rate=LLM_REQUESTS_PER_MIN)
    return _llm_bucket


def get_search_bucket() -> TokenBucket:
    global _search_bucket
    if _search_bucket is None:
        _search_bucket = TokenBucket(rate=20)  # Tavily free tier: ~20 req/min safe limit
    return _search_bucket


def get_groq_bucket() -> TokenBucket:
    """Rate limiter for Groq models."""
    global _groq_bucket
    if _groq_bucket is None:
        from config import GROQ_REQUESTS_PER_MIN

        _groq_bucket = TokenBucket(rate=GROQ_REQUESTS_PER_MIN)
    return _groq_bucket


def get_gemini_bucket() -> TokenBucket:
    """Rate limiter for Gemini models."""
    global _gemini_bucket
    if _gemini_bucket is None:
        from config import GEMINI_REQUESTS_PER_MIN

        _gemini_bucket = TokenBucket(rate=GEMINI_REQUESTS_PER_MIN)
    return _gemini_bucket


def get_openai_bucket() -> TokenBucket:
    """Rate limiter for OpenAI models."""
    global _openai_bucket
    if _openai_bucket is None:
        from config import OPENAI_REQUESTS_PER_MIN

        _openai_bucket = TokenBucket(rate=OPENAI_REQUESTS_PER_MIN)
    return _openai_bucket


# ─────────────────────────────────────────────────────────────────────────────
# Retry Decorator
# ─────────────────────────────────────────────────────────────────────────────


def with_retry(
    max_retries: int = None,
    base_delay: float = None,
    retryable_exceptions: tuple = None,
) -> Callable:
    """
    Decorator: retry a function with exponential backoff + jitter.

    Args:
        max_retries:           Max retry attempts. Defaults to LLM_MAX_RETRIES from config.
        base_delay:            Base delay in seconds. Doubles each retry. Defaults to LLM_RETRY_BASE_DELAY.
        retryable_exceptions:  Exception types that trigger a retry. Defaults to common API errors.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            from config import LLM_MAX_RETRIES, LLM_RETRY_BASE_DELAY

            _max = max_retries if max_retries is not None else LLM_MAX_RETRIES
            _delay = base_delay if base_delay is not None else LLM_RETRY_BASE_DELAY
            _errors = retryable_exceptions or _default_retryable()

            for attempt in range(_max + 1):
                try:
                    return func(*args, **kwargs)
                except _errors as e:
                    if attempt == _max:
                        logger.error(
                            f"[Retry] {func.__name__} failed after {_max} retries: {e}"
                        )
                        raise
                    wait = _delay * (2 ** attempt) + random.uniform(0, 0.5)
                    logger.warning(
                        f"[Retry] {func.__name__} attempt {attempt+1}/{_max} failed: {e}. "
                        f"Retrying in {wait:.1f}s"
                    )
                    time.sleep(wait)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            from config import LLM_MAX_RETRIES, LLM_RETRY_BASE_DELAY

            _max = max_retries if max_retries is not None else LLM_MAX_RETRIES
            _delay = base_delay if base_delay is not None else LLM_RETRY_BASE_DELAY
            _errors = retryable_exceptions or _default_retryable()

            for attempt in range(_max + 1):
                try:
                    return await func(*args, **kwargs)
                except _errors as e:
                    if attempt == _max:
                        logger.error(
                            f"[Retry] {func.__name__} failed after {_max} retries: {e}"
                        )
                        raise
                    wait = _delay * (2 ** attempt) + random.uniform(0, 0.5)
                    logger.warning(
                        f"[Retry] {func.__name__} attempt {attempt+1}/{_max} failed: {e}. "
                        f"Retrying in {wait:.1f}s"
                    )
                    await asyncio.sleep(wait)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def _default_retryable() -> tuple:
    """Return the default tuple of exception types that should trigger a retry."""
    try:
        import anthropic

        base = (
            anthropic.RateLimitError,
            anthropic.APITimeoutError,
            anthropic.APIConnectionError,
        )
    except ImportError:
        base = ()

    try:
        import groq as groq_sdk

        groq_errors = (
            getattr(groq_sdk, "RateLimitError", Exception),
            getattr(groq_sdk, "APITimeoutError", Exception),
            getattr(groq_sdk, "APIConnectionError", Exception),
        )
    except ImportError:
        groq_errors = ()

    try:
        import openai as openai_sdk

        openai_errors = (
            getattr(openai_sdk, "RateLimitError", Exception),
            getattr(openai_sdk, "APITimeoutError", Exception),
            getattr(openai_sdk, "APIConnectionError", Exception),
        )
    except ImportError:
        openai_errors = ()

    return base + groq_errors + openai_errors + (ConnectionError, TimeoutError, OSError)

