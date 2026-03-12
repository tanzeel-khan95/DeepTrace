"""
LangSmith tracing configuration and conditional @traceable decorator.

When LANGCHAIN_TRACING_V2=true, wraps all agent functions with LangSmith tracing.
When false (dev default), applies a no-op decorator — zero performance overhead.
"""
import functools
import logging
from typing import Callable

logger = logging.getLogger(__name__)

_langsmith_available = False

try:
    import langsmith  # type: ignore
    from langsmith import traceable as _ls_traceable
    import pydantic  # type: ignore

    _langsmith_available = True

    # Pydantic v2: RunTree is not fully defined until Path (RunBase.attachments) and
    # self-refs are resolved. Inject Path into run_trees namespace and rebuild.
    import pathlib
    import langsmith.run_trees as _run_trees_mod
    _run_trees_mod.Path = pathlib.Path  # type: ignore[attr-defined]
    if hasattr(_run_trees_mod.RunTree, "model_rebuild"):
        _run_trees_mod.RunTree.model_rebuild()
except ImportError:
    _ls_traceable = None


def traceable(name: str = None, run_type: str = "chain", tags: list | None = None):
    """
    Conditional @traceable decorator.

    When LANGCHAIN_TRACING=true and LangSmith is available:
      - Wraps the function with LangSmith tracing
      - Creates a named run in the configured project
      - Attaches run_type and tags for filtering in the LangSmith UI

    When LANGCHAIN_TRACING=false OR LangSmith is not available:
      - Returns the original function unchanged (zero overhead)
    """

    def decorator(func: Callable) -> Callable:
        from config import LANGCHAIN_TRACING

        if not LANGCHAIN_TRACING or not _langsmith_available:
            return func

        try:
            _name = name or func.__name__
            return _ls_traceable(
                name=_name,
                run_type=run_type,
                tags=tags or [],
            )(func)
        except Exception as e:
            logger.warning(
                f"[LangSmith] Could not apply @traceable to {func.__name__}: {e}"
            )
            return func

    return decorator


def configure_langsmith() -> bool:
    """
    Configure LangSmith environment variables at startup.
    Call once from main.py before building the pipeline graph.
    Returns True if LangSmith is active.
    """
    from config import LANGCHAIN_TRACING, LANGCHAIN_PROJECT, LANGCHAIN_API_KEY
    import os

    if not LANGCHAIN_TRACING:
        logger.info("[LangSmith] Tracing disabled (LANGCHAIN_TRACING_V2=false)")
        return False

    if not LANGCHAIN_API_KEY:
        logger.warning("[LangSmith] LANGCHAIN_API_KEY not set — tracing disabled")
        return False

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT

    logger.info(f"[LangSmith] Tracing active — project: {LANGCHAIN_PROJECT}")
    return True


def log_llm_run(model: str, input_tokens: int, output_tokens: int) -> None:
    """
    Log an LLM call to the current LangSmith run as a child span with model and token usage.
    Uses RunTree.set(usage_metadata=...) so LangSmith Tokens/Cost columns and trace tree show usage.
    No-op if tracing is disabled or LangSmith unavailable. Best-effort; never raises.
    """
    from config import LANGCHAIN_TRACING

    if not LANGCHAIN_TRACING or not _langsmith_available:
        return
    try:
        from langsmith.run_helpers import get_current_run_tree

        run = get_current_run_tree()
        if run is None:
            return
        total = input_tokens + output_tokens
        child = run.create_child(
            name=f"LLM: {model}",
            run_type="llm",
            inputs={},
            outputs={},
        )
        # LangSmith expects usage in extra.metadata.usage_metadata (input_tokens, output_tokens, total_tokens)
        # so the Tokens/Cost columns and trace tree display correctly.
        child.set(
            usage_metadata={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total,
            }
        )
        child.end(
            metadata={
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total,
            }
        )
    except Exception as e:
        logger.debug("[LangSmith] log_llm_run failed: %s", e)


def log_warning_to_run(message: str) -> None:
    """
    Append a warning message to the current LangSmith run's metadata.
    No-op if tracing is disabled or LangSmith unavailable. Best-effort; never raises.
    """
    from config import LANGCHAIN_TRACING

    if not LANGCHAIN_TRACING or not _langsmith_available:
        return
    try:
        from langsmith.run_helpers import get_current_run_tree

        run = get_current_run_tree()
        if run is None:
            return
        existing = list(run.extra.get("warnings", [])) if run.extra else []
        run.add_metadata({"warnings": existing + [message]})
    except Exception as e:
        logger.debug("[LangSmith] log_warning_to_run failed: %s", e)

