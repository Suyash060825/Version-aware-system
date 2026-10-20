"""
tests/test_data.py
Authoritative centralized test data registry for Veritas policy intelligence platform.
Covers: Ingestion (all formats), Chunking, Versioning/Temporal, Storage, Retrieval,
Ranking, LLM/Streaming, Security/RBAC Matrix, and Ground-Truth QA.
"""
from datetime import date

# ==============================================================================
# 1. Ingestion Raw Test Payloads
# ==============================================================================

SAMPLE_TXT_POLICY = """ACME CORPORATION
REMOTE WORK POLICY
Version 2.0 - Effective July 1, 2023

1. Purpose and Scope
This policy outlines the guidelines and requirements for remote work arrangements at Acme Corporation. This applies to all full-time and part-time salaried employees.

2. Eligibility
Employees who have completed their 90-day probationary period and maintain satisfactory performance ratings are eligible for hybrid or full remote work upon manager approval. Contractors are not eligible for full remote equipment stipends.

3. Remote Work Schedules
Eligible employees may work remotely up to 3 days per week under the standard hybrid model. Full-time remote arrangements require Department Head and People Operations written authorization. Core collaboration hours are 10:00 AM to 3:00 PM local time.

4. Equipment and Expense Reimbursement
Acme provides a one-time home office setup reimbursement up to $500 for eligible full-time employees. Monthly high-speed internet stipend is provided at $50 per month. Hardware remains the property of Acme Corporation and must be returned upon termination.

5. Data Security and Confidentiality
All remote employees must connect via corporate VPN when accessing internal networks. Proprietary data and customer PII must never be stored on personal devices or transmitted over unencrypted public Wi-Fi without VPN tunneling.
"""

SAMPLE_MARKDOWN_POLICY = """# Travel and Expense Reimbursement Policy
**Version 3.0** | *Effective Date: January 1, 2024*

## 1. Overview
This document specifies reimbursable business expenses, expenditure caps, and submission timelines for all business travel on behalf of Acme Corporation.

## 2. Air Travel Guidelines
Domestic flights under five hours must be booked in economy class. International flights or domestic flights exceeding five consecutive hours are eligible for premium economy. Business class requires Chief Financial Officer pre-approval.

## 3. Lodging and Meals Per Diem
- Hotel lodging is reimbursed up to $220 per night in standard tier cities and $320 per night in high-cost metro areas (New York, San Francisco, London, Tokyo).
- Daily meal per diem is capped at $75 per travel day ($20 breakfast, $25 lunch, $30 dinner). Alcohol is non-reimbursable unless part of an authorized client entertainment dinner.

## 4. Submission Timelines
Expense reports must be submitted through the portal within 30 days of trip completion with attached itemized receipts. Reports submitted after 60 days are forfeited.
"""

SAMPLE_SPREADSHEET_TEXT = """
# Expense Caps
Category | Daily Limit | Approval Level | Notes
--- | --- | --- | ---
Hotel Tier 1 | $320 | Manager | Major metropolitan areas
Hotel Tier 2 | $220 | Manager | Standard cities
Meals Per Diem | $75 | Automatic | Itemized receipt required above $25
Car Rental | $65/day | Manager | Mid-size or compact only
Client Dinner | $150/person | VP | Pre-approval required

# Mileage Rates
Vehicle Type | Rate Per Mile | Effective Year
--- | --- | ---
Personal Vehicle | $0.67 | 2024
Motorcycle | $0.65 | 2024
"""

SAMPLE_OCR_PDF_TEXT = """[Page 1 — OCR]
ACME GLOBAL PRIVACY DIRECTIVE
Classification: RESTRICTED
Effective Date: 2023-01-15

1. Mandatory Data Retention Schedule
Financial records must be preserved for 7 years.
Customer transaction logs must be retained for 3 years.
Candidate resumes and hiring notes must be securely purged after 180 days.

[Page 2 — OCR]
2. Subject Access Request (SAR) SLA
All GDPR and CCPA data subject access requests must be fulfilled within 30 calendar days of verified identity submission. Escalations require Legal Counsel notification within 48 hours.
"""

SAMPLE_HTML_POLICY = """<!DOCTYPE html>
<html>
<head><title>Code of Business Conduct</title></head>
<body>
<h1>Code of Business Conduct and Ethics</h1>
<p><strong>Effective Date:</strong> October 1, 2023</p>
<h2>1. Anti-Bribery and Corruption</h2>
<p>Acme prohibits offering, giving, soliciting, or receiving bribes, kickbacks, or improper inducements of any kind.</p>
<h2>2. Gifts and Entertainment</h2>
<p>Employees may accept nominal business gifts valued under $100. Any gift exceeding $100 must be declared to Compliance within 5 business days.</p>
</body>
</html>
"""

# ==============================================================================
# 2. Multi-Version Ground Truth Temporal Dataset
# ==============================================================================

SEED_POLICIES_WITH_VERSIONS = [
    {
        "policy_id": "POL-HR-001",
        "title": "Remote Work Policy",
        "category": "Human Resources",
        "department": "Human Resources",
        "confidentiality": "internal",
        "versions": [
            {
                "version_num": 1.0,
                "version_label": "v1.0",
                "effective_date": date(2022, 1, 1),
                "expiry_date": date(2023, 6, 30),
                "is_active": False,
                "status": "superseded",
                "content": """Remote Work Policy v1.0. Effective January 1, 2022 to June 30, 2023.
1. Eligibility: Employees in good standing may work remotely up to 2 days per week.
2. Stipend: Home office stipend is $250 one-time reimbursement.
3. Internet: High-speed internet allowance is $35 per month."""
            },
            {
                "version_num": 2.0,
                "version_label": "v2.0",
                "effective_date": date(2023, 7, 1),
                "expiry_date": None,
                "is_active": True,
                "status": "approved",
                "content": """Remote Work Policy v2.0. Effective July 1, 2023 onwards.
1. Eligibility: Employees in good standing may work remotely up to 3 days per week with manager approval. Full remote requires VP sign-off.
2. Stipend: Home office stipend is increased to $500 one-time reimbursement.
3. Internet: High-speed internet allowance is increased to $50 per month."""
            }
        ]
    },
    {
        "policy_id": "POL-FIN-002",
        "title": "Travel and Expense Policy",
        "category": "Finance",
        "department": "Finance",
        "confidentiality": "internal",
        "versions": [
            {
                "version_num": 1.0,
                "version_label": "v1.0",
                "effective_date": date(2021, 1, 1),
                "expiry_date": date(2023, 12, 31),
                "is_active": False,
                "status": "superseded",
                "content": """Travel and Expense Policy v1.0. Effective 2021-2023.
1. Lodging: Daily hotel reimbursement maximum is $180 per night across all cities.
2. Meals: Daily per diem is $50 per day ($15 breakfast, $15 lunch, $20 dinner).
3. Mileage: Personal vehicle reimbursement is $0.58 per mile."""
            },
            {
                "version_num": 2.0,
                "version_label": "v2.0",
                "effective_date": date(2024, 1, 1),
                "expiry_date": None,
                "is_active": True,
                "status": "approved",
                "content": """Travel and Expense Policy v2.0. Effective January 1, 2024.
1. Lodging: Daily hotel reimbursement is $220 for standard cities and $320 for high-cost metro areas.
2. Meals: Daily meal per diem is $75 per day ($20 breakfast, $25 lunch, $30 dinner).
3. Mileage: Personal vehicle reimbursement is $0.67 per mile."""
            }
        ]
    },
    {
        "policy_id": "POL-SEC-003",
        "title": "Executive Data Protection & Security Clearance Directive",
        "category": "Security",
        "department": "Executive Management",
        "confidentiality": "restricted",
        "versions": [
            {
                "version_num": 1.0,
                "version_label": "v1.0",
                "effective_date": date(2023, 1, 1),
                "expiry_date": None,
                "is_active": True,
                "status": "approved",
                "content": """Executive Data Protection Directive v1.0. CLASSIFICATION: RESTRICTED.
1. Scope: Governs executive communications, board meeting transcripts, and M&A evaluations.
2. Key Management: Master cryptographic keys require dual-custody HSM authorization.
3. Access Controls: Access strictly restricted to Executive and Legal personnel with verified restricted clearance."""
            }
        ]
    },
    {
        "policy_id": "POL-CON-004",
        "title": "Independent Contractor Standards",
        "category": "Legal",
        "department": "Legal",
        "confidentiality": "public",
        "versions": [
            {
                "version_num": 1.0,
                "version_label": "v1.0",
                "effective_date": date(2022, 6, 1),
                "expiry_date": None,
                "is_active": True,
                "status": "approved",
                "content": """Independent Contractor Standards v1.0. Classification: PUBLIC.
1. Invoicing: Invoices must be submitted bi-weekly with net-30 payment terms.
2. Equipment: Contractors must supply their own hardware and software tooling.
3. Intellectual Property: All work product created under agreement is work-made-for-hire."""
            }
        ]
    }
]

# ==============================================================================
# 3. Ground-Truth Q&A Benchmark Pairs
# ==============================================================================

GROUND_TRUTH_QA_BENCHMARK = [
    # Current active policy queries
    {
        "id": "GT-001",
        "query": "How many days per week can employees work remotely?",
        "target_policy": "Remote Work Policy",
        "target_version": "2.0",
        "expected_facts": ["3 days", "up to 3 days"],
        "prohibited_facts": ["up to 2 days"],
        "expected_route": ["FAST_PATH_COMPILED_QA", "HYBRID_RAG", "FACT_DIRECT"],
        "must_abstain": False,
        "is_temporal": False
    },
    {
        "id": "GT-002",
        "query": "What is the monthly internet allowance?",
        "target_policy": "Remote Work Policy",
        "target_version": "2.0",
        "expected_facts": ["$50"],
        "prohibited_facts": ["$35"],
        "expected_route": ["FAST_PATH_COMPILED_QA", "HYBRID_RAG", "FACT_DIRECT"],
        "must_abstain": False,
        "is_temporal": False
    },
    {
        "id": "GT-003",
        "query": "What is the daily meal per diem reimbursement?",
        "target_policy": "Travel and Expense Policy",
        "target_version": "2.0",
        "expected_facts": ["$75"],
        "prohibited_facts": ["$50 per day"],
        "expected_route": ["FAST_PATH_COMPILED_QA", "HYBRID_RAG", "FACT_DIRECT"],
        "must_abstain": False,
        "is_temporal": False
    },
    # Historical temporal queries (replaying historical-version selection)
    {
        "id": "GT-004",
        "query": "What was the monthly internet allowance in 2022?",
        "target_policy": "Remote Work Policy",
        "target_version": "1.0",
        "expected_facts": ["$35"],
        "prohibited_facts": ["$50"],
        "expected_route": ["HYBRID_RAG", "TEMPORAL_COMPARISON", "FACT_DIRECT"],
        "must_abstain": False,
        "is_temporal": True
    },
    {
        "id": "GT-005",
        "query": "Under the 2022 policy, how many days could employees work remotely?",
        "target_policy": "Remote Work Policy",
        "target_version": "1.0",
        "expected_facts": ["2 days", "up to 2 days"],
        "prohibited_facts": ["3 days"],
        "expected_route": ["HYBRID_RAG", "FACT_DIRECT"],
        "must_abstain": False,
        "is_temporal": True
    },
    {
        "id": "GT-006",
        "query": "What was the daily meal per diem before 2024?",
        "target_policy": "Travel and Expense Policy",
        "target_version": "1.0",
        "expected_facts": ["$50"],
        "prohibited_facts": ["$75"],
        "expected_route": ["HYBRID_RAG", "FACT_DIRECT"],
        "must_abstain": False,
        "is_temporal": True
    },
    # Version comparison queries
    {
        "id": "GT-007",
        "query": "Compare remote work policy v1 vs v2",
        "target_policy": "Remote Work Policy",
        "target_version": ["1.0", "2.0"],
        "expected_facts": ["Remote", "stipend"],
        "prohibited_facts": [],
        "expected_route": ["TEMPORAL_COMPARISON"],
        "must_abstain": False,
        "is_temporal": True
    },
    # Safe abstention on unanswerable / out-of-scope / underspecified queries
    {
        "id": "GT-008",
        "query": "What is the pet insurance reimbursement limit for cats and dogs?",
        "target_policy": None,
        "target_version": None,
        "expected_facts": [],
        "prohibited_facts": [],
        "expected_route": ["ABSTAIN", "REFUSAL"],
        "must_abstain": True,
        "is_temporal": False
    },
    {
        "id": "GT-009",
        "query": "Tell me about the policy regarding flying flying space unicorns",
        "target_policy": None,
        "target_version": None,
        "expected_facts": [],
        "prohibited_facts": [],
        "expected_route": ["ABSTAIN", "REFUSAL"],
        "must_abstain": True,
        "is_temporal": False
    }
]

# ==============================================================================
# 4. Comprehensive Authorization & RBAC Matrix
# ==============================================================================

AUTHORIZATION_TEST_MATRIX = [
    # (user_role, user_clearance, user_dept_id, policy_confidentiality, policy_dept_id, expected_allow, description)
    # Admin has universal clearance
    ("admin", "restricted", 1, "restricted", 1, True, "Admin with restricted clearance accesses restricted"),
    ("admin", "public_only", 1, "restricted", 2, True, "Admin role supercedes clearance constraints"),
    ("admin", None, None, "confidential", 5, True, "Admin accesses confidential cross-department"),
    
    # Executive / Legal roles
    ("executive", "restricted", 1, "restricted", 1, True, "Executive with clearance accesses restricted"),
    ("legal", "restricted", 2, "restricted", 1, True, "Legal with restricted clearance accesses restricted"),
    ("legal", "internal", 2, "confidential", 2, True, "Legal accesses confidential"),

    # HR role
    ("hr", "confidential", 3, "confidential", 3, True, "HR accesses confidential HR policy"),
    ("hr", "confidential", 3, "confidential", 4, True, "HR accesses confidential company-wide policy"),
    ("hr", "confidential", 3, "restricted", 3, False, "HR without restricted clearance BLOCKED from restricted"),

    # Regular Employee
    ("employee", "internal", 4, "public", 1, True, "Employee accesses public policy"),
    ("employee", "internal", 4, "internal", 4, True, "Employee accesses internal own department"),
    ("employee", "internal", 4, "internal", None, True, "Employee accesses internal company-wide"),
    ("employee", "internal", 4, "internal", 5, False, "Employee BLOCKED from other department internal policy"),
    ("employee", "internal", 4, "confidential", 4, False, "Regular employee BLOCKED from confidential"),
    ("employee", "internal", 4, "restricted", 4, False, "Regular employee BLOCKED from restricted"),
    
    # Contractor
    ("contractor", "public_only", 6, "public", 6, True, "Contractor with public_only accesses public"),
    ("contractor", "public_only", 6, "internal", 6, False, "Contractor with public_only BLOCKED from internal"),
    ("contractor", None, 6, "restricted", 6, False, "Contractor BLOCKED from restricted"),
    ("contractor", None, 6, "confidential", 6, False, "Contractor BLOCKED from confidential")
]

# ==============================================================================
# 5. Performance and Latency Budgets
# ==============================================================================

LATENCY_BUDGETS_MS = {
    "dense_retrieval_p50": 50.0,
    "dense_retrieval_p95": 120.0,
    "sparse_bm25_p50": 15.0,
    "sparse_bm25_p95": 40.0,
    "reranker_p50": 45.0,
    "reranker_p95": 90.0,
    "fast_path_compiled_qa_p50": 10.0,
    "fast_path_compiled_qa_p95": 25.0,
    "end_to_end_cold_start_p95": 1500.0,
    "end_to_end_warm_p50": 60.0,
    "end_to_end_warm_p95": 250.0
}
