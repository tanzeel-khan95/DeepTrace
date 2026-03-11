"""
eval_personas.py — Ground truth personas for evaluation runs.

Contains structured due diligence and risk flag data for all evaluation
targets used in the CLI (--eval), Streamlit dashboard, and LangSmith evals.
"""

EVAL_PERSONA_SATYA_NADELLA = {
    "name": "Satya Nadella",
    "context": "Chairman and CEO of Microsoft",
    "risk_level": "LOW",
    "due_diligence": {
        "name": "Satya Nadella",
        "nationality": "American",
        "birth_year": 1967,
        "role": "Chairman and CEO of Microsoft",
        "industry": "Technology / Cloud Computing",
        "education": [
            "B.E. Electrical Engineering – Manipal Institute of Technology",
            "M.S. Computer Science – University of Wisconsin–Milwaukee",
            "MBA – University of Chicago Booth School of Business",
        ],
        "notable_positions": [
            "CEO of Microsoft (2014–present)",
            "Executive Vice President, Microsoft Cloud and Enterprise Group",
        ],
        "awards": [
            "Financial Times Person of the Year 2019",
            "TIME 100 Most Influential People",
        ],
    },
    "risk_flags_ground_truth": {
        "risk_flags": [],
        "negative_media": "None significant related to fraud, sanctions, or regulatory violations identified in major sources as of 2024.",
        "litigation": "None personally",
        "sanctions": False,
        "pep": False,
    },
    "expected_facts": [
        "Chairman and CEO of Microsoft",
        "American technology executive born in 1967",
        "Holds engineering, computer science, and MBA degrees",
        "CEO of Microsoft since 2014",
    ],
    "expected_risk_levels": [],
    "expected_risk_score": 5,
    "expected_flag_count": 0,
}

EVAL_PERSONA_ELIZABETH_HOLMES = {
    "name": "Elizabeth Holmes",
    "context": "Founder and former CEO of Theranos",
    "risk_level": "MEDIUM",
    "due_diligence": {
        "name": "Elizabeth Holmes",
        "nationality": "American",
        "birth_year": 1984,
        "role": "Founder and former CEO of Theranos",
        "industry": "Biotechnology",
        "education": [
            "Stanford University (Chemical Engineering – did not complete)",
        ],
        "company": "Theranos",
        "founded_year": 2003,
        "business_activity": "Blood-testing technology startup",
    },
    "risk_flags_ground_truth": {
        "risk_flags": [
            "Fraud charges related to misleading investors",
            "SEC civil charges in 2018",
            "Criminal conviction in 2022 for investor fraud",
        ],
        "litigation": [
            "SEC vs Elizabeth Holmes (2018)",
            "United States v. Holmes (2021 trial)",
        ],
        "regulatory_action": [
            "Theranos banned from operating labs by CMS (2016)",
        ],
        "sanctions": False,
        "pep": False,
    },
    "expected_facts": [
        "Founded Theranos in 2003",
        "American entrepreneur in biotechnology",
        "Attended Stanford University but did not complete degree",
        "Subject of SEC civil charges in 2018",
        "Criminal conviction in 2022 for investor fraud",
    ],
    "expected_risk_levels": ["CRITICAL", "CRITICAL", "HIGH"],
    "expected_risk_score": 55,
    "expected_flag_count": 3,
}

EVAL_PERSONA_SAM_BANKMAN_FRIED = {
    "name": "Sam Bankman-Fried",
    "context": "Founder and former CEO of FTX cryptocurrency exchange",
    "risk_level": "HIGH",
    "due_diligence": {
        "name": "Sam Bankman-Fried",
        "nationality": "American",
        "birth_year": 1992,
        "role": "Founder and former CEO of FTX cryptocurrency exchange",
        "industry": "Cryptocurrency / Financial trading",
        "education": [
            "MIT – Physics",
        ],
        "companies": [
            "FTX",
            "Alameda Research",
        ],
    },
    "risk_flags_ground_truth": {
        "risk_flags": [
            "Convicted of fraud and conspiracy related to FTX collapse",
            "Misappropriation of customer funds",
            "Securities and wire fraud charges",
            "Major financial misconduct affecting billions of dollars",
        ],
        "regulatory_actions": [
            "SEC charges (2022)",
            "CFTC charges",
            "U.S. Department of Justice criminal indictment",
        ],
        "financial_impact": "FTX collapse caused billions in customer losses",
        "sanctions": False,
        "pep": False,
    },
    "expected_facts": [
        "Founded FTX cryptocurrency exchange",
        "Founded or led Alameda Research",
        "American entrepreneur born in 1992 with MIT Physics background",
        "Convicted of fraud and conspiracy related to FTX collapse",
        "Misappropriation of customer funds and securities/wire fraud charges",
    ],
    "expected_risk_levels": ["CRITICAL", "CRITICAL", "CRITICAL", "HIGH"],
    "expected_risk_score": 90,
    "expected_flag_count": 4,
}

EVAL_PERSONA_TIMOTHY_OVERTURF = {
    "name": "Timothy Silas Prugh Overturf",
    "context": "CEO of Sisu Capital, LLC, an SEC-registered investment adviser",
    "risk_level": "HIGH",
    "due_diligence": {
        "name": "Timothy Silas Prugh Overturf",
        "role": "CEO of Sisu Capital, LLC",
        "industry": "Investment advisory",
        "firm": "Sisu Capital, LLC",
        "firm_status": "SEC-registered investment adviser",
        "key_relationship": "Authorized his father, Hansueli Overturf, to provide investment advice to firm clients",
        "regulatory_concerns": [
            "Hansueli Overturf provided advice despite two California suspensions: Nov 2011–Nov 2014 and Dec 2017–Dec 2019",
            "At least one suspension period overlapped with active client advisory activity",
        ],
        "fee_activity": "Sisu Capital withdrew over $2 million in portfolio management fees, performance-based fees, and commissions from client accounts (2017–2021)",
        "conflict_of_interest": "Undisclosed family relationship between CEO and advisory personnel; potential conflicts regarding fee allocation and investment recommendations",
    },
    "risk_flags_ground_truth": {
        "risk_flags": [
            "Suspended Investment Adviser Providing Client Advice (Hansueli Overturf advised Sisu clients despite California suspensions 2011–2014 and 2017–2019)",
            "Undisclosed Family Conflict of Interest in Investment Management (CEO–father relationship; fee and recommendation oversight concerns)",
        ],
        "regulatory_action": [
            "California suspension of Hansueli Overturf (Nov 2011–Nov 2014)",
            "California suspension of Hansueli Overturf (Dec 2017–Dec 2019)",
        ],
        "litigation": "SEC and related enforcement attention regarding Sisu Capital, Timothy Overturf, and Hansueli Overturf",
        "sanctions": False,
        "pep": False,
    },
    "expected_facts": [
        "Timothy Overturf is CEO of Sisu Capital, LLC",
        "Sisu Capital, LLC is an SEC-registered investment adviser",
        "Hansueli Overturf (father) provided investment advice to Sisu clients with Timothy Overturf's authorization",
        "Hansueli Overturf was suspended by California (Nov 2011–Nov 2014 and Dec 2017–Dec 2019) from acting as an investment adviser",
        "Sisu Capital withdrew over $2 million in fees from client accounts during 2017–2021",
        "Undisclosed family relationship between CEO and advisory personnel created conflict of interest concerns",
    ],
    "expected_risk_levels": ["CRITICAL", "MEDIUM"],
    "expected_risk_score": 75,
    "expected_flag_count": 2,
}

ALL_EVAL_PERSONAS = [
    EVAL_PERSONA_SATYA_NADELLA,
    EVAL_PERSONA_ELIZABETH_HOLMES,
    EVAL_PERSONA_SAM_BANKMAN_FRIED,
    EVAL_PERSONA_TIMOTHY_OVERTURF,
]

__all__ = [
    "EVAL_PERSONA_SATYA_NADELLA",
    "EVAL_PERSONA_ELIZABETH_HOLMES",
    "EVAL_PERSONA_SAM_BANKMAN_FRIED",
    "EVAL_PERSONA_TIMOTHY_OVERTURF",
    "ALL_EVAL_PERSONAS",
]

