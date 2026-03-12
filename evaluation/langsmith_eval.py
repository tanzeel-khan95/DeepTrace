"""
LangSmith evaluation dataset and scorer for DeepTrace.

Creates a LangSmith dataset from the 3 evaluation personas and runs
automated scoring after each pipeline run.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_or_create_dataset(client, dataset_name: str = "deeptrace-eval-v1"):
    """
    Get or create the LangSmith evaluation dataset.
    Creates it with the 3 standard DeepTrace personas if it doesn't exist.
    """
    try:
        datasets = list(client.list_datasets(dataset_name=dataset_name))
        if datasets:
            logger.info(f"[LangSmith] Using existing dataset: {dataset_name}")
            return datasets[0]

        # Create with 3 evaluation examples
        from evaluation.eval_set import EVAL_PERSONAS

        dataset = client.create_dataset(
            dataset_name,
            description="DeepTrace identity research evaluation",
        )
        for persona in EVAL_PERSONAS:
            client.create_example(
                inputs={
                    "target_name": persona["name"],
                    "target_context": persona["context"],
                },
                outputs={
                    "expected_risk_score": persona["expected_risk_score"],
                    "expected_flag_count": persona["expected_flag_count"],
                },
                dataset_id=dataset.id,
            )
        logger.info(
            f"[LangSmith] Created dataset: {dataset_name} with {len(EVAL_PERSONAS)} examples"
        )
        return dataset

    except Exception as e:
        logger.error(f"[LangSmith] Dataset creation failed: {e}")
        return None


def score_run(run_state: dict, expected: dict) -> dict:
    """
    Score a completed pipeline run against expected outputs.
    Returns dict of metric_name → score (0.0–1.0).
    """
    scores = {}

    # Fact recall: did we find facts in all 4 expected categories?
    found_cats = {f.get("category") for f in run_state.get("extracted_facts", [])}
    expected_cats = {"biographical", "professional", "financial", "behavioral"}
    scores["extraction_coverage"] = len(found_cats & expected_cats) / 4.0

    # Risk flag count proximity
    found_flags = len(run_state.get("risk_flags", []))
    exp_flags = expected.get("expected_flag_count", 0)
    if exp_flags > 0:
        scores["risk_flag_recall"] = min(found_flags / exp_flags, 1.0)
    else:
        scores["risk_flag_recall"] = 1.0 if found_flags == 0 else 0.5

    # Research quality score
    scores["research_quality"] = float(run_state.get("research_quality", 0.0))

    # Citation completeness: % of facts with source_url populated
    facts = run_state.get("extracted_facts", [])
    if facts:
        cited = sum(1 for f in facts if f.get("source_url"))
        scores["citation_completeness"] = cited / len(facts)
    else:
        scores["citation_completeness"] = 0.0

    return scores

"""LangSmith-based evaluation for fact recall and risk precision."""
