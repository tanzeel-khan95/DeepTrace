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
from config import USE_MOCK, MODELS, MAX_TOKENS, ENV, GROQ_MODELS, GEMINI_MODELS, OPENAI_MODELS
from state.agent_state import AgentState, Citation, Fact, Entity, Relationship
from state.llm_schemas import DeepDiveResponse
from utils.anthropic_client import call_llm_structured
from utils.groq_client import call_groq_structured
from utils.gemini_client import call_gemini_structured
from utils.openai_client import call_openai_structured
from prompts.deep_dive_prompt import DEEP_DIVE_SYSTEM_PROMPT
from evaluation.confidence_scorer import score_facts_batch, get_domain_trust
from evaluation.fact_utils import merge_duplicate_facts
from mock_responses import MOCK_DEEP_DIVE_RESULTS
from utils.citation_builder import build_citations
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
        conf_map = score_facts_batch(data["extracted_facts"])
        facts_as_dicts = [f.model_dump() for f in facts]
        citation_dicts = build_citations(facts_as_dicts, state.get("raw_results", []))
        citations = []
        for c in citation_dicts:
            try:
                citations.append(Citation(**c))
            except Exception as e:
                logger.warning(f"[DeepDive] Invalid citation: {e}")
        logger.info(f"[DeepDive] MOCK: {len(facts)} facts, {len(entities)} entities validated")
        return {
            "extracted_facts": facts,
            "entities": entities,
            "relationships": rels,
            "confidence_map": conf_map,
            "citations": citations,
        }

    model = MODELS["deep_dive"]

    # Prioritise highly trusted domains (e.g. sec.gov, IAPD, major financial press)
    # when selecting sources for extraction by combining Tavily relevance with
    # a domain trust boost.
    def _effective_score(result: dict) -> float:
        relevance = float(result.get("relevance", 0.0)) or 0.0
        domain = result.get("source_domain", "") or ""
        trust = get_domain_trust(domain)
        # Centre around default (0.40) so unknown domains neither gain nor lose.
        # High-trust domains like sec.gov receive a noticeable boost.
        alpha = 0.5
        return relevance + alpha * (trust - 0.40)

    results = sorted(
        state["raw_results"],
        key=_effective_score,
        reverse=True,
    )[:8]

    if not results:
        logger.warning("[DeepDive] No raw_results to process")
        return {"extracted_facts": [], "entities": [], "relationships": [], "confidence_map": {}, "citations": []}

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
    - entities_mentioned must reference names that appear in your entities list
    - Every entity must have a relation with at least one entity so it will not be an orphan node"""

    try:
        if model in GROQ_MODELS:
            parsed = call_groq_structured(
                system_prompt=DEEP_DIVE_SYSTEM_PROMPT,
                user_message=user_msg,
                model=model,
                max_tokens=MAX_TOKENS[ENV],
                response_model=DeepDiveResponse,
            )
        elif model in GEMINI_MODELS:
            parsed = call_gemini_structured(
                system_prompt=DEEP_DIVE_SYSTEM_PROMPT,
                user_message=user_msg,
                model=model,
                max_tokens=MAX_TOKENS[ENV],
                response_model=DeepDiveResponse,
            )
        elif model in OPENAI_MODELS:
            parsed = call_openai_structured(
                system_prompt=DEEP_DIVE_SYSTEM_PROMPT,
                user_message=user_msg,
                model=model,
                max_tokens=MAX_TOKENS[ENV],
                response_model=DeepDiveResponse,
            )
        else:
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

    # Collapse near-duplicate facts before scoring and citation building.
    facts = merge_duplicate_facts(facts)

    conf_map = score_facts_batch([f.model_dump() for f in facts])

    facts_as_dicts = [f.model_dump() for f in facts]
    citation_dicts = build_citations(facts_as_dicts, state.get("raw_results", []))
    citations = []
    for c in citation_dicts:
        try:
            citations.append(Citation(**c))
        except Exception as e:
            logger.warning(f"[DeepDive] Invalid citation: {e}")

    logger.info(f"[DeepDive] Real: {len(facts)} facts, {len(entities)} entities, {len(rels)} rels")
    return {
        "extracted_facts": facts,
        "entities": entities,
        "relationships": rels,
        "confidence_map": conf_map,
        "citations": citations,
    }
