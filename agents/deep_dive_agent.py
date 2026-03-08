"""
agents/deep_dive_agent.py — Deep Dive Agent: full-page extraction and entity identification.

Takes top 10 results from raw_results, fetches full page content (Phase 2+),
extracts structured Fact and Entity objects, applies confidence scoring.

Phase 1 (USE_MOCK=true): returns MOCK_DEEP_DIVE_RESULTS fixture directly.
Phase 2+ (USE_MOCK=false): uses Gemini 2.5 Pro for long-context extraction.

Architecture position: third node in LangGraph pipeline, called after Scout.
"""
import logging
from langsmith import traceable
from config import USE_MOCK
from state.agent_state import AgentState, Fact, Entity, Relationship
from evaluation.confidence_scorer import score_facts_batch
from mock_responses import MOCK_DEEP_DIVE_RESULTS

logger = logging.getLogger(__name__)


@traceable(name="DeepDive::run")
def run_deep_dive(state: AgentState) -> dict:
    """
    Extract facts, entities, and relationships from search results.
    Returns delta to merge into AgentState.
    """
    logger.info(f"[DeepDive] Processing {len(state['raw_results'])} raw results")

    if USE_MOCK:
        data = MOCK_DEEP_DIVE_RESULTS
        # Validate through Pydantic schemas
        facts   = [Fact(**f)         for f in data["extracted_facts"]]
        entities= [Entity(**e)       for e in data["entities"]]
        rels    = [Relationship(**r) for r in data["relationships"]]
        conf_map= score_facts_batch(data["extracted_facts"])
        logger.info(f"[DeepDive] MOCK: {len(facts)} facts, {len(entities)} entities validated")
        return {
            "extracted_facts": facts,
            "entities":        entities,
            "relationships":   rels,
            "confidence_map":  conf_map,
        }

    raise NotImplementedError("Phase 2: implement Gemini 2.5 deep dive extraction here")
