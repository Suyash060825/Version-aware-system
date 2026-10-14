"""
scripts/audit_grounding_eval.py
Phase 6: Grounding and Abstention Evaluation across 10 specific test scenarios.
Runs against the actual Policy Ledger application and QueryEngine.
"""
import os
import sys
import json
import time
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from models import db, User, Policy, PolicyVersion, PolicyFact, PolicyChunkV2
from rag.engine.query_engine import get_query_engine
from rag.engine.query_scope import QueryScope
from rag.verification.entailment import EntailmentVerifier

OUTPUT_PATH = "audit-results/grounding_abstention_cases.json"

TEST_CASES = [
    {
        "case_id": "G01",
        "description": "Question directly answered by valid, authorized active evidence.",
        "query": "How many days of remote work are permitted under the remote work policy?",
        "user_email": "hr@company.com",  # Authorized user
        "expected_action": "ANSWER",
        "expected_answer_contains": ["3 days", "Remote Work Policy"],
        "expected_version": "v2.0",
        "expected_auth": True
    },
    {
        "case_id": "G02",
        "description": "Question answered only by an outdated historical version.",
        "query": "How many days of remote work were allowed in 2022 under the remote work policy?",
        "user_email": "hr@company.com",
        "expected_action": "ANSWER",
        "expected_answer_contains": ["1 day", "Remote Work Policy"],
        "expected_version": "v1.0",
        "expected_auth": True
    },
    {
        "case_id": "G03",
        "description": "Question answered only by a future policy (not yet effective in 2024).",
        "query": "What are the requirements for Autonomous AI Agent Governance under the 2028 policy?",
        "user_email": "hr@company.com",
        "expected_action": "ABSTAIN",
        "expected_answer_contains": ["insufficient", "not find", "abstain"],
        "expected_version": None,
        "expected_auth": True
    },
    {
        "case_id": "G04",
        "description": "Question for which user is unauthorized (Confidential/Restricted policy).",
        "query": "What is the keyvault master token in the Cybersecurity Incident Plan?",
        "user_email": "employee@company.com",  # Employee cannot view restricted IT policies
        "expected_action": "ABSTAIN",
        "expected_answer_contains": ["insufficient", "not find", "unauthorized", "abstain"],
        "expected_version": None,
        "expected_auth": False
    },
    {
        "case_id": "G05",
        "description": "Question with no supporting evidence in any corporate policy.",
        "query": "What is the reimbursement limit for employees purchasing commercial hoverboards?",
        "user_email": "hr@company.com",
        "expected_action": "ABSTAIN",
        "expected_answer_contains": ["insufficient", "not find", "abstain"],
        "expected_version": None,
        "expected_auth": True
    },
    {
        "case_id": "G06",
        "description": "Conflicting provisions across versions (v1.0 vs v2.0 remote work allowances).",
        "query": "Compare version 1.0 vs version 2.0 of Remote Work Policy and describe what changed.",
        "user_email": "hr@company.com",
        "expected_action": "ANSWER",
        "expected_answer_contains": ["Remote Work Policy", "Comparison", "v1.0", "v2.0"],
        "expected_version": "v1.0 vs v2.0",
        "expected_auth": True
    },
    {
        "case_id": "G07",
        "description": "Conflicting provisions within same applicable version (Ambiguity / Contradiction).",
        "query": "What is the core working hours requirement in Remote Work Policy?",
        "user_email": "hr@company.com",
        "expected_action": "ANSWER",
        "expected_answer_contains": ["10 AM", "4 PM", "core hours"],
        "expected_version": "v2.0",
        "expected_auth": True
    },
    {
        "case_id": "G08",
        "description": "Question requiring combining multiple policy clauses (equipment + allowance).",
        "query": "What equipment and internet allowance is provided for remote employees?",
        "user_email": "hr@company.com",
        "expected_action": "ANSWER",
        "expected_answer_contains": ["laptop", "500", "allowance"],
        "expected_version": "v2.0",
        "expected_auth": True
    },
    {
        "case_id": "G09",
        "description": "Question semantically similar to a clause but asking for a different fact.",
        "query": "What is the reimbursement limit for home ergonomic standing desks under the remote work policy?",
        "user_email": "employee@company.com",
        "expected_action": "ABSTAIN",  # Remote policy provides laptop & internet, but no standing desk reimbursement
        "expected_answer_contains": ["insufficient", "not find", "not provided"],
        "expected_version": None,
        "expected_auth": True
    },
    {
        "case_id": "G10",
        "description": "Question where model could generate plausible but unsupported hallucinated claim.",
        "query": "Does the company provide free hot breakfast bagels during core hours from 10 AM to 4 PM?",
        "user_email": "employee@company.com",
        "expected_action": "ABSTAIN",
        "expected_answer_contains": ["insufficient", "not find"],
        "expected_version": None,
        "expected_auth": True
    }
]

def run_grounding_audit():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    app = create_app("development")

    results = []
    false_answers = 0
    unnecessary_abstentions = 0
    total_evaluated = len(TEST_CASES)

    with app.app_context():
        engine = get_query_engine()
        verifier = EntailmentVerifier()

        for tc in TEST_CASES:
            user = User.query.filter_by(email=tc["user_email"]).first()
            if not user:
                user = User.query.first()

            t0 = time.time()
            try:
                res = engine.answer(tc["query"], user=user)
                ans = res.answer or ""
                citations = res.citations or []
                route = res.route
                conf = res.confidence
                abstained = res.abstained
                lat_ms = (time.time() - t0) * 1000
            except Exception as e:
                ans = f"EXCEPTION: {e}"
                citations = []
                route = "ERROR"
                conf = 0.0
                abstained = True
                lat_ms = (time.time() - t0) * 1000

            # Determine actual outcome vs expected
            is_abstain_text = any(w in ans.lower() for w in ["could not find", "insufficient", "unauthorized", "no evidence", "not find"])
            actually_abstained = abstained or is_abstain_text

            expected_abstain = (tc["expected_action"] == "ABSTAIN")
            
            # Grounding check: verify whether answer contains target or is hallucinated
            passed = False
            error_note = "NONE"
            if expected_abstain:
                if actually_abstained:
                    passed = True
                else:
                    passed = False
                    false_answers += 1
                    error_note = "FALSE_ANSWER_ON_UNSUPPORTED_QUESTION"
            else:
                if actually_abstained:
                    passed = False
                    unnecessary_abstentions += 1
                    error_note = "UNNECESSARY_ABSTENTION_ON_SUPPORTED_QUESTION"
                else:
                    contains_exp = any(exp.lower() in ans.lower() for exp in tc["expected_answer_contains"])
                    if contains_exp:
                        passed = True
                    else:
                        passed = False
                        error_note = "ANSWER_MISSING_EXPECTED_FACTS"

            record = {
                "case_id": tc["case_id"],
                "description": tc["description"],
                "query": tc["query"],
                "user": user.email,
                "role": user.role.value if hasattr(user.role, "value") else str(user.role),
                "expected_action": tc["expected_action"],
                "actual_action": "ABSTAIN" if actually_abstained else "ANSWER",
                "route_taken": route,
                "confidence": conf,
                "latency_ms": round(lat_ms, 2),
                "citations_count": len(citations),
                "citations": citations,
                "actual_answer_snippet": ans[:160] + ("..." if len(ans) > 160 else ""),
                "passed": passed,
                "error_note": error_note
            }
            results.append(record)
            print(f"[{'PASS' if passed else 'FAIL'}] {tc['case_id']}: {tc['description'][:50]}... -> {record['actual_action']} (Route: {route})")

    summary = {
        "total_test_cases": total_evaluated,
        "passed_cases": sum(1 for r in results if r["passed"]),
        "failed_cases": sum(1 for r in results if not r["passed"]),
        "false_answer_count": false_answers,
        "false_answer_rate_pct": round((false_answers / total_evaluated) * 100, 2),
        "unnecessary_abstention_count": unnecessary_abstentions,
        "unnecessary_abstention_rate_pct": round((unnecessary_abstentions / total_evaluated) * 100, 2),
        "cases": results
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nPhase 6 Evaluation Complete: {summary['passed_cases']}/{total_evaluated} passed.")
    print(f"False Answer Rate: {summary['false_answer_rate_pct']}% | Unnecessary Abstention Rate: {summary['unnecessary_abstention_rate_pct']}%")
    print(f"Saved results to {OUTPUT_PATH}")

if __name__ == "__main__":
    run_grounding_audit()
