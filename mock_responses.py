"""
mock_responses.py — Hardcoded fixture data for Phase 1 (USE_MOCK=true).

Every agent in Phase 1 returns data from this file instead of calling an LLM.
Data is structured to match the exact Pydantic schemas in state/agent_state.py.

Target: Timothy Overturf, CEO of Sisu Capital (the assessment subject).
Additional entries cover the three evaluation personas.

Architecture position: imported by all agents when USE_MOCK=true.
Phase 2: this file is no longer imported. All agents call real APIs.
"""

# ─────────────────────────────────────────────────────────────────────────────
# SUPERVISOR MOCK
# ─────────────────────────────────────────────────────────────────────────────

MOCK_SUPERVISOR_LOOP_1 = {
    "research_plan": [
        "Timothy Overturf Sisu Capital SEC filing",
        "Timothy Overturf CEO background education career",
        "Sisu Capital fund AUM performance investors",
        "Timothy Overturf board memberships director",
        "Sisu Capital LLC regulatory history FINRA",
        "Timothy Overturf LinkedIn professional history",
        "Sisu Capital fund structure limited partners",
        "Timothy Overturf prior employment hedge fund",
        "Sisu Capital SEC Form D registration",
        "Timothy Overturf financial connections network",
    ],
    "gaps_remaining": [
        "Early career before 2015 not yet found",
        "Limited partner identities not yet confirmed",
        "Prior fund performance details missing",
    ],
    "research_quality": 0.0,
    "loop_count": 1,
}

MOCK_SUPERVISOR_LOOP_2 = {
    "research_plan": [
        "Timothy Overturf 2010 2012 2013 career history",
        "Sisu Capital LP Holdings offshore structure",
        "Timothy Overturf Apex Ventures fund manager",
    ],
    "gaps_remaining": [
        "Offshore entity beneficial ownership still unconfirmed",
    ],
    "research_quality": 0.55,
    "loop_count": 2,
}

MOCK_SUPERVISOR_FINAL = {
    "research_quality": 0.82,
    "gaps_remaining": [],
    "final_report": """# DeepTrace Risk Intelligence Report
## Target: Timothy Overturf, CEO of Sisu Capital
**Overall Risk Score: 62/100 — MEDIUM-HIGH**
**Report Generated: Phase 1 Mock Run**

---

### Executive Summary
Investigation of Timothy Overturf, CEO of Sisu Capital LLC, identified
significant undisclosed prior fund failures, an opaque offshore limited
partnership structure, and active board positions not disclosed in investor
materials. Overall risk posture is MEDIUM-HIGH.

### Key Findings
1. **Prior Fund Failure (HIGH):** Apex Ventures Fund (2015–2018) dissolved
   with an estimated 38% capital loss. This is not referenced in current
   Sisu Capital marketing materials.
2. **Offshore LP Structure (MEDIUM):** LP Holdings Ireland Ltd is the
   registered beneficial owner of Sisu Capital. This entity traces upstream
   to a Cayman SPV Trust, obscuring the identity of underlying investors.
3. **Undisclosed Board Positions (MEDIUM):** Active board seat at NovaCrest
   Inc not listed in investor disclosure materials.
4. **Biography Discrepancy (LOW):** Goldman Sachs start date is listed as
   2007 on LinkedIn but 2008 on SEC filings.

### Risk Flag Summary
| Severity | Count | Categories |
|----------|-------|------------|
| HIGH     | 1     | Financial  |
| MEDIUM   | 2     | Regulatory, Reputational |
| LOW      | 1     | Biographical |

### Confidence Assessment
All HIGH and MEDIUM findings are supported by 2+ independent sources with
combined confidence >= 0.65. LOW findings are single-source or unverified.
""",
}

# ─────────────────────────────────────────────────────────────────────────────
# SCOUT MOCK
# ─────────────────────────────────────────────────────────────────────────────

MOCK_SCOUT_RESULTS = {
    "raw_results": [
        {
            "url":   "https://sec.gov/cgi-bin/browse-edgar?action=getcompany&company=sisu+capital",
            "title": "Sisu Capital LLC — SEC EDGAR Filing",
            "content": "Sisu Capital LLC filed Form D (Notice of Exempt Offering) on 2019-03-14. "
                       "Timothy Overturf listed as Managing Member and CEO. State of incorporation: Delaware. "
                       "Total offering amount: $45,000,000. Investors: 8 accredited investors. "
                       "Date of first sale: 2019-02-01.",
            "relevance": 0.94,
            "source_domain": "sec.gov",
        },
        {
            "url":   "https://bloomberg.com/profile/timothy-overturf-sisu-capital",
            "title": "Timothy Overturf | Bloomberg Profile",
            "content": "Timothy Overturf is the founder and CEO of Sisu Capital LLC, a New York-based "
                       "hedge fund focused on distressed credit opportunities. Prior to founding Sisu Capital "
                       "in 2019, Overturf managed Apex Ventures Fund from 2015 to 2018. Apex Ventures was "
                       "dissolved in Q4 2018 following underperformance. Goldman Sachs, 2008–2014.",
            "relevance": 0.88,
            "source_domain": "bloomberg.com",
        },
        {
            "url":   "https://sec.gov/Archives/edgar/data/sisu-capital/form-d-2019.htm",
            "title": "Sisu Capital Form D 2019 — Full Text",
            "content": "Registrant: Sisu Capital LLC. Related persons: Timothy Overturf (Managing Member), "
                       "LP Holdings Ireland Ltd (5% or greater owner). Minimum investment accepted: $500,000. "
                       "Sales commissions: $0. Use of proceeds: Fund investments per private placement memorandum.",
            "relevance": 0.91,
            "source_domain": "sec.gov",
        },
        {
            "url":   "https://reuters.com/finance/apex-ventures-dissolution-2018",
            "title": "Apex Ventures Fund Dissolution — Reuters",
            "content": "Apex Ventures Fund LP, managed by Timothy Overturf, returned approximately -38% to "
                       "investors over its 2016-2018 investment period before dissolution. The fund focused on "
                       "emerging market credit. Several limited partners declined to comment on losses.",
            "relevance": 0.82,
            "source_domain": "reuters.com",
        },
        {
            "url":   "https://novacrest.com/about/board",
            "title": "NovaCrest Inc — Board of Directors",
            "content": "Board of Directors: Jane Smith (Chair), Timothy Overturf (Independent Director), "
                       "Robert Chen (CFO). Timothy Overturf joined the NovaCrest board in October 2020. "
                       "NovaCrest is a healthcare data analytics company.",
            "relevance": 0.74,
            "source_domain": "novacrest.com",
        },
        {
            "url":   "https://ft.com/content/cayman-spv-lp-holdings-ireland",
            "title": "Offshore LP Structure Analysis — FT",
            "content": "LP Holdings Ireland Ltd, identified in multiple SEC filings as a beneficial owner "
                       "of US hedge fund vehicles, is itself owned by Cayman SPV Trust No. 47. This layered "
                       "structure is used by several fund managers to obscure the identity of ultimate "
                       "beneficial owners from public filings.",
            "relevance": 0.63,
            "source_domain": "ft.com",
        },
    ],
    "queries_issued": [
        "Timothy Overturf Sisu Capital SEC filing",
        "Timothy Overturf CEO background education career",
        "Sisu Capital fund AUM performance investors",
        "Timothy Overturf board memberships director",
        "Sisu Capital LLC regulatory history FINRA",
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# DEEP DIVE MOCK
# ─────────────────────────────────────────────────────────────────────────────

MOCK_DEEP_DIVE_RESULTS = {
    "extracted_facts": [
        {
            "fact_id": "f001",
            "claim": "Timothy Overturf is the founder and CEO of Sisu Capital LLC",
            "source_url": "https://sec.gov/cgi-bin/browse-edgar?company=sisu+capital",
            "source_domain": "sec.gov",
            "confidence": 0.95,
            "category": "biographical",
            "entities_mentioned": ["Timothy Overturf", "Sisu Capital LLC"],
            "supporting_fact_ids": [],
            "raw_source_snippet": "Timothy Overturf listed as Managing Member and CEO.",
        },
        {
            "fact_id": "f002",
            "claim": "Sisu Capital LLC filed SEC Form D in 2019 with total offering of $45M",
            "source_url": "https://sec.gov/Archives/edgar/data/sisu-capital/form-d-2019.htm",
            "source_domain": "sec.gov",
            "confidence": 0.94,
            "category": "financial",
            "entities_mentioned": ["Sisu Capital LLC", "SEC"],
            "supporting_fact_ids": ["f001"],
            "raw_source_snippet": "Total offering amount: $45,000,000.",
        },
        {
            "fact_id": "f003",
            "claim": "Apex Ventures Fund returned approximately -38% to investors over 2016-2018",
            "source_url": "https://reuters.com/finance/apex-ventures-dissolution-2018",
            "source_domain": "reuters.com",
            "confidence": 0.82,
            "category": "financial",
            "entities_mentioned": ["Apex Ventures Fund", "Timothy Overturf"],
            "supporting_fact_ids": [],
            "raw_source_snippet": "returned approximately -38% to investors over its 2016-2018 period.",
        },
        {
            "fact_id": "f004",
            "claim": "Timothy Overturf managed Apex Ventures Fund from 2015 to 2018 before dissolution",
            "source_url": "https://bloomberg.com/profile/timothy-overturf-sisu-capital",
            "source_domain": "bloomberg.com",
            "confidence": 0.88,
            "category": "biographical",
            "entities_mentioned": ["Timothy Overturf", "Apex Ventures Fund"],
            "supporting_fact_ids": ["f003"],
            "raw_source_snippet": "managed Apex Ventures Fund from 2015 to 2018. Apex Ventures was dissolved.",
        },
        {
            "fact_id": "f005",
            "claim": "LP Holdings Ireland Ltd is listed as 5%+ beneficial owner in Sisu Capital's SEC filing",
            "source_url": "https://sec.gov/Archives/edgar/data/sisu-capital/form-d-2019.htm",
            "source_domain": "sec.gov",
            "confidence": 0.91,
            "category": "financial",
            "entities_mentioned": ["LP Holdings Ireland Ltd", "Sisu Capital LLC"],
            "supporting_fact_ids": ["f002"],
            "raw_source_snippet": "LP Holdings Ireland Ltd (5% or greater owner).",
        },
        {
            "fact_id": "f006",
            "claim": "LP Holdings Ireland Ltd is owned by Cayman SPV Trust No. 47",
            "source_url": "https://ft.com/content/cayman-spv-lp-holdings-ireland",
            "source_domain": "ft.com",
            "confidence": 0.63,
            "category": "financial",
            "entities_mentioned": ["LP Holdings Ireland Ltd", "Cayman SPV Trust"],
            "supporting_fact_ids": ["f005"],
            "raw_source_snippet": "LP Holdings Ireland Ltd... is itself owned by Cayman SPV Trust No. 47.",
        },
        {
            "fact_id": "f007",
            "claim": "Timothy Overturf joined the NovaCrest Inc board in October 2020",
            "source_url": "https://novacrest.com/about/board",
            "source_domain": "novacrest.com",
            "confidence": 0.74,
            "category": "network",
            "entities_mentioned": ["Timothy Overturf", "NovaCrest Inc"],
            "supporting_fact_ids": [],
            "raw_source_snippet": "Timothy Overturf joined the NovaCrest board in October 2020.",
        },
        {
            "fact_id": "f008",
            "claim": "Timothy Overturf worked at Goldman Sachs from 2008 to 2014",
            "source_url": "https://bloomberg.com/profile/timothy-overturf-sisu-capital",
            "source_domain": "bloomberg.com",
            "confidence": 0.88,
            "category": "biographical",
            "entities_mentioned": ["Timothy Overturf", "Goldman Sachs"],
            "supporting_fact_ids": [],
            "raw_source_snippet": "Goldman Sachs, 2008–2014.",
        },
    ],
    "entities": [
        {
            "entity_id": "e001",
            "name": "Timothy Overturf",
            "entity_type": "Person",
            "attributes": {"role": "CEO", "nationality": "Unknown", "location": "New York"},
            "confidence": 0.95,
            "source_fact_ids": ["f001", "f004", "f007", "f008"],
        },
        {
            "entity_id": "e002",
            "name": "Sisu Capital LLC",
            "entity_type": "Fund",
            "attributes": {"incorporated": "Delaware", "founded": "2019", "aum": "$45M"},
            "confidence": 0.94,
            "source_fact_ids": ["f001", "f002", "f005"],
        },
        {
            "entity_id": "e003",
            "name": "Apex Ventures Fund",
            "entity_type": "Fund",
            "attributes": {"period": "2015-2018", "status": "Dissolved", "performance": "-38%"},
            "confidence": 0.85,
            "source_fact_ids": ["f003", "f004"],
        },
        {
            "entity_id": "e004",
            "name": "LP Holdings Ireland Ltd",
            "entity_type": "Organization",
            "attributes": {"country": "Ireland", "type": "Offshore entity"},
            "confidence": 0.72,
            "source_fact_ids": ["f005", "f006"],
        },
        {
            "entity_id": "e005",
            "name": "Cayman SPV Trust",
            "entity_type": "Organization",
            "attributes": {"country": "Cayman Islands", "type": "Trust structure"},
            "confidence": 0.63,
            "source_fact_ids": ["f006"],
        },
        {
            "entity_id": "e006",
            "name": "NovaCrest Inc",
            "entity_type": "Organization",
            "attributes": {"sector": "Healthcare data", "role": "Board seat"},
            "confidence": 0.74,
            "source_fact_ids": ["f007"],
        },
        {
            "entity_id": "e007",
            "name": "Goldman Sachs",
            "entity_type": "Organization",
            "attributes": {"type": "Investment bank", "period": "2008-2014"},
            "confidence": 0.88,
            "source_fact_ids": ["f008"],
        },
    ],
    "relationships": [
        {"from_id": "e001", "to_id": "e002", "rel_type": "FOUNDED",
         "attributes": {"year": "2019"}, "confidence": 0.94, "source_fact_id": "f001"},
        {"from_id": "e001", "to_id": "e003", "rel_type": "MANAGED",
         "attributes": {"period": "2015-2018"}, "confidence": 0.88, "source_fact_id": "f004"},
        {"from_id": "e004", "to_id": "e002", "rel_type": "INVESTED_IN",
         "attributes": {"ownership": "5%+"}, "confidence": 0.91, "source_fact_id": "f005"},
        {"from_id": "e004", "to_id": "e005", "rel_type": "AFFILIATED_WITH",
         "attributes": {}, "confidence": 0.63, "source_fact_id": "f006"},
        {"from_id": "e001", "to_id": "e006", "rel_type": "BOARD_MEMBER",
         "attributes": {"since": "2020"}, "confidence": 0.74, "source_fact_id": "f007"},
        {"from_id": "e001", "to_id": "e007", "rel_type": "WORKS_AT",
         "attributes": {"period": "2008-2014"}, "confidence": 0.88, "source_fact_id": "f008"},
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# RISK EVALUATOR MOCK
# ─────────────────────────────────────────────────────────────────────────────

MOCK_RISK_FLAGS = {
    "risk_flags": [
        {
            "flag_id": "r001",
            "title": "Undisclosed Prior Fund Failure",
            "description": (
                "Apex Ventures Fund LP, managed by Timothy Overturf from 2015 to 2018, "
                "dissolved after returning approximately -38% to investors. This material "
                "performance failure is not referenced in Sisu Capital's current investor "
                "materials or public biography."
            ),
            "severity": "HIGH",
            "evidence_fact_ids": ["f003", "f004"],
            "confidence": 0.84,
            "category": "financial",
        },
        {
            "flag_id": "r002",
            "title": "Opaque Offshore LP Ownership Structure",
            "description": (
                "LP Holdings Ireland Ltd is registered as a 5%+ beneficial owner of Sisu "
                "Capital in SEC Form D. This entity is itself owned by Cayman SPV Trust No. 47, "
                "creating a multi-layer offshore structure that obscures ultimate beneficial "
                "ownership from public filings."
            ),
            "severity": "MEDIUM",
            "evidence_fact_ids": ["f005", "f006"],
            "confidence": 0.72,
            "category": "regulatory",
        },
        {
            "flag_id": "r003",
            "title": "Undisclosed Active Board Positions",
            "description": (
                "Timothy Overturf holds an active board seat at NovaCrest Inc (healthcare data) "
                "since October 2020. This position does not appear in Sisu Capital investor "
                "disclosure materials, which may represent a material conflict of interest "
                "omission depending on NovaCrest's investment relationship with Sisu."
            ),
            "severity": "MEDIUM",
            "evidence_fact_ids": ["f001", "f007"],
            "confidence": 0.68,
            "category": "reputational",
        },
        {
            "flag_id": "r004",
            "title": "Professional Biography Date Discrepancy",
            "description": (
                "Goldman Sachs start date listed as 2007 on LinkedIn but 2008 per SEC filing. "
                "Minor discrepancy, low risk in isolation but noted as part of overall "
                "biographical accuracy assessment."
            ),
            "severity": "LOW",
            "evidence_fact_ids": ["f001", "f008"],
            "confidence": 0.65,
            "category": "biographical",
        },
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# EVALUATION PERSONA MOCKS (3 Personas for eval set)
# ─────────────────────────────────────────────────────────────────────────────

EVAL_PERSONA_OVERTURF = {
    "name": "Timothy Overturf",
    "context": "CEO of Sisu Capital",
    "expected_facts": [
        "Founded Sisu Capital LLC in 2019",
        "Previously managed Apex Ventures Fund (2015-2018)",
        "Apex Ventures dissolved with ~38% loss",
        "LP Holdings Ireland Ltd is 5%+ beneficial owner",
        "Board member at NovaCrest Inc since 2020",
        "Previously employed at Goldman Sachs",
    ],
    "expected_risk_levels": ["HIGH", "MEDIUM", "MEDIUM", "LOW"],
}

EVAL_PERSONA_HIGH_RISK = {
    "name": "Marcus R. Delano",
    "context": "Former fund manager, SEC enforcement subject",
    "expected_facts": [
        "Subject of SEC enforcement action Case #2021-CF-00847",
        "AUM misrepresented as $180M vs actual $12M",
        "FINRA complaint #2020-11834 filed",
        "Connected to OFAC SDN-listed entity",
        "Controls Delano Family Trust → Meridian Offshore Ltd",
    ],
    "expected_risk_levels": ["CRITICAL", "CRITICAL", "HIGH", "HIGH", "MEDIUM"],
}

EVAL_PERSONA_LOW_RISK = {
    "name": "Dr. Sarah Chen",
    "context": "CEO BioNovate Inc, academic and entrepreneur",
    "expected_facts": [
        "Founded BioNovate Inc in 2010",
        "PhD Molecular Biology MIT 2002",
        "12 publications in Nature",
        "Received NIH grant $2.1M (2018)",
        "Received NSF grant $850K (2021)",
    ],
    "expected_risk_levels": ["LOW", "LOW"],
}

ALL_EVAL_PERSONAS = [
    EVAL_PERSONA_OVERTURF,
    EVAL_PERSONA_HIGH_RISK,
    EVAL_PERSONA_LOW_RISK,
]
