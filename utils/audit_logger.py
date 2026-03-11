"""
audit_logger.py — Structured JSON audit logging for DeepTrace.

Every search query, LLM decision, retry event, and node completion is
recorded as a structured JSON event in .audit_logs/{run_id}.jsonl.

One file per run (JSONL format — one JSON object per line).
Each event has: timestamp, run_id, event_type, agent, data.
"""
import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)
_lock = threading.Lock()

# Current run context (set at start of each run)
_current_run_id: str = "unknown"


def set_run_id(run_id: str) -> None:
    """Set the current run_id. Call at the start of each pipeline run."""
    global _current_run_id
    _current_run_id = run_id


def _log_path() -> str:
    from config import AUDIT_LOG_DIR

    os.makedirs(AUDIT_LOG_DIR, exist_ok=True)
    return os.path.join(AUDIT_LOG_DIR, f"{_current_run_id}.jsonl")


def log_event(
    event_type: str,
    agent: str,
    data: dict,
    run_id: str | None = None,
) -> None:
    """
    Write a structured audit event to the run's JSONL log file.

    Args:
        event_type: One of the event type constants
        agent:      Agent or module name (e.g. "supervisor", "scout_agent")
        data:       Event-specific payload dict
        run_id:     Override run_id (defaults to current run context)
    """
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id or _current_run_id,
        "event_type": event_type,
        "agent": agent,
        "data": data,
    }
    with _lock:
        try:
            with open(_log_path(), "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.warning(f"[AuditLog] Write failed: {e}")


def log_search_query(agent: str, query: str, source: str, result_count: int) -> None:
    log_event(
        "SEARCH_QUERY",
        agent,
        {"query": query, "source": source, "result_count": result_count},
    )


def log_llm_call(agent: str, model: str, input_tokens: int, output_tokens: int) -> None:
    log_event(
        "LLM_CALL",
        agent,
        {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    )


def log_llm_retry(agent: str, attempt: int, error: str) -> None:
    log_event(
        "LLM_RETRY",
        agent,
        {"attempt": attempt, "error": str(error)[:200]},
    )


def log_node_start(node: str) -> None:
    log_event("NODE_START", node, {})


def log_node_complete(node: str, summary: dict) -> None:
    log_event("NODE_COMPLETE", node, summary)


def log_node_failure(node: str, error: str, partial_results: dict | None = None) -> None:
    log_event(
        "NODE_FAILURE",
        node,
        {"error": str(error)[:500], "partial": partial_results or {}},
    )


def log_entity_merged(canonical: str, merged_from: str, similarity: float) -> None:
    log_event(
        "ENTITY_MERGED",
        "canonicalizer",
        {
            "canonical": canonical,
            "merged_from": merged_from,
            "similarity": similarity,
        },
    )


def log_inconsistency(claim_a: str, claim_b: str, inconsistency_type: str) -> None:
    log_event(
        "INCONSISTENCY",
        "inconsistency_detector",
        {
            "claim_a": claim_a[:200],
            "claim_b": claim_b[:200],
            "type": inconsistency_type,
        },
    )


def log_risk_flag(flag_id: str, title: str, severity: str, confidence: float) -> None:
    log_event(
        "RISK_FLAG",
        "risk_evaluator",
        {
            "flag_id": flag_id,
            "title": title,
            "severity": severity,
            "confidence": confidence,
        },
    )


def load_run_log(run_id: str) -> list[dict[str, Any]]:
    """
    Load all audit events for a given run_id.
    Returns list of event dicts, ordered by timestamp.
    """
    from config import AUDIT_LOG_DIR

    path = os.path.join(AUDIT_LOG_DIR, f"{run_id}.jsonl")
    if not os.path.exists(path):
        return []
    events: list[dict[str, Any]] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def list_run_ids() -> list[str]:
    """Return all run IDs that have audit logs, sorted newest first."""
    from config import AUDIT_LOG_DIR

    if not os.path.exists(AUDIT_LOG_DIR):
        return []
    files = sorted(
        [f[:-6] for f in os.listdir(AUDIT_LOG_DIR) if f.endswith(".jsonl")],
        reverse=True,
    )
    return files

