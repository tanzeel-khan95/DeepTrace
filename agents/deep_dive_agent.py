"""
agents/deep_dive_agent.py — Deep Dive Agent: extraction from search snippets.

Takes top results from raw_results (Tavily snippets only in Phase 2 — no scraper),
extracts structured Fact, Entity, Relationship objects, applies confidence scoring.

Phase 1 (USE_MOCK=true): returns MOCK_DEEP_DIVE_RESULTS fixture directly.
Phase 2+ (USE_MOCK=false): uses Haiku for extraction from snippets only.

Architecture position: third node in LangGraph pipeline, called after Scout.
"""
import logging
from pydantic import ValidationError
from config import USE_MOCK, MODELS, MAX_TOKENS, ENV
from state.agent_state import AgentState, Fact, Entity, Relationship
from state.llm_schemas import DeepDiveResponse
from utils.anthropic_client import call_llm_structured
from prompts.deep_dive_prompt import DEEP_DIVE_SYSTEM_PROMPT
from evaluation.confidence_scorer import score_facts_batch
from mock_responses import MOCK_DEEP_DIVE_RESULTS
from utils.tracing import traceable

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

    model = MODELS["deep_dive"]
    results = sorted(
        state["raw_results"],
        key=lambda r: r.get("relevance", 0),
        reverse=True,
    )[:8]

    if not results:
        logger.warning("[DeepDive] No raw_results to process")
        return {"extracted_facts": [], "entities": [], "relationships": [], "confidence_map": {}}

    content_blocks = []
    for i, r in enumerate(results):
        content_blocks.append(
            f"SOURCE {i+1}: {r.get('source_domain','unknown')} | {r.get('url','')}\n"
            f"TITLE: {r.get('title','')}\n"
            f"CONTENT: {r.get('content','')[:600]}\n"
        )
    sources_text = "\n---\n".join(content_blocks)

    user_msg = f"""Research target: {state['target_name']}
    Context: {state.get('target_context', '')}

    Extract all facts, entities, and relationships from these sources:

    {sources_text}

    Rules:
    - fact_ids must be unique strings (f001, f002, ...)
    - entity_ids must be unique strings (e001, e002, ...)
    - Only extract claims directly supported by the provided sources
    - confidence 0.0-1.0 based on source reliability and claim specificity
    - entities_mentioned must reference names that appear in your entities list"""

    try:
        parsed = call_llm_structured(
            system_prompt=DEEP_DIVE_SYSTEM_PROMPT,
            user_message=user_msg,
            model=model,
            max_tokens=MAX_TOKENS[ENV],
            response_model=DeepDiveResponse,
        )
        facts = list(parsed.extracted_facts) if parsed.extracted_facts else []
        entities = list(parsed.entities) if parsed.entities else []
        rels = list(parsed.relationships) if parsed.relationships else []
    except (ValidationError, Exception) as e:
        logger.warning(f"[DeepDive] Structured parse failed, using empty extraction: {e}")
        facts, entities, rels = [], [], []

    conf_map = score_facts_batch([f.model_dump() for f in facts])

    logger.info(f"[DeepDive] Real: {len(facts)} facts, {len(entities)} entities, {len(rels)} rels")
    return {
        "extracted_facts": facts,
        "entities": entities,
        "relationships": rels,
        "confidence_map": conf_map,
    }
