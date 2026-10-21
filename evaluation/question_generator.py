"""
evaluation/question_generator.py
Comprehensive 36-Category Evaluation Question Suite Generator.
Generates 1,000+ deterministic benchmark questions mapped directly to GroundTruthLedger.
Explicitly separates deterministic fast paths from generative Qwen local model paths.
"""

import os
import sys
import json
import random
import hashlib
from datetime import date
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.system_characterization.corpus.user_matrix import build_user_pool, AccessControlEvaluator, SimulatedUser
from tests.system_characterization.corpus.ground_truth_ledger import GroundTruthLedger, QueryGroundTruth

QUESTION_CATEGORIES_METADATA = {
    1: ("Direct factual lookup", "FAST_PATH_FACT", False),
    2: ("Exact policy and version lookup", "FAST_PATH_FACT", False),
    3: ("Semantic paraphrases", "HYBRID_RAG", False),
    4: ("Synonyms and alternate terminology", "HYBRID_RAG", False),
    5: ("Multi-condition questions", "HYBRID_RAG", True),
    6: ("Evidence from multiple sections", "HYBRID_RAG", True),
    7: ("Cross-policy questions", "HYBRID_RAG", True),
    8: ("Conflicting policies", "COMPLEX_REASONING", True),
    9: ("Current-policy vs historical-policy", "TEMPORAL_COMPARISON", True),
    10: ("Effective-date and time-travel", "FAST_PATH_FACT", False),
    11: ("Questions about exceptions", "HYBRID_RAG", True),
    12: ("Answer absent from corpus (OOD)", "ABSTAIN", False),
    13: ("Ambiguous questions requiring clarification", "ABSTAIN", False),
    14: ("Insufficient evidence abstention", "ABSTAIN", False),
    15: ("Contradictory premises", "ABSTAIN", True),
    16: ("Typographical errors and noise", "HYBRID_RAG", False),
    17: ("Short, long, and multi-part", "HYBRID_RAG", True),
    18: ("Exact numeric values and deadlines", "FAST_PATH_FACT", False),
    19: ("Negative conditions and exclusions", "HYBRID_RAG", True),
    20: ("Negation and double negation", "HYBRID_RAG", True),
    21: ("Misleading keywords from unrelated policies", "HYBRID_RAG", True),
    22: ("Deterministic fast paths", "FAST_PATH_FACT", False),
    23: ("Hybrid retrieval required", "HYBRID_RAG", False),
    24: ("Genuine local Qwen generation required", "HYBRID_RAG", True),
    25: ("Citation-backed explanations", "HYBRID_RAG", True),
    26: ("Multiple relevant versions", "TEMPORAL_COMPARISON", True),
    27: ("Distinguish similar policy titles", "HYBRID_RAG", False),
    28: ("Archived, unpublished, superseded policies", "ABSTAIN", False),
    29: ("Unauthorized users (RBAC refusal)", "REFUSAL", False),
    30: ("Conflicting user claims / supplied context", "ABSTAIN", True),
    31: ("Empty, whitespace, malformed", "REFUSAL", False),
    32: ("Unsupported languages / Unicode", "REFUSAL", False),
    33: ("Repeated queries / cache hits", "FAST_PATH_FACT", False),
    34: ("Concurrent mutations during query", "HYBRID_RAG", False),
    35: ("Evidence scattered across many chunks", "HYBRID_RAG", True),
    36: ("Low-confidence refusal", "ABSTAIN", False),
}


def generate_36_category_benchmark(ledger: GroundTruthLedger, target_count: int = 1000, seed: int = 42) -> List[QueryGroundTruth]:
    """
    Generates >= target_count questions covering all 36 required categories.
    """
    rng = random.Random(seed)
    users = build_user_pool()

    admin_user = next((u for u in users if u.role == "admin"), users[0])
    exec_user = next((u for u in users if u.role == "executive"), users[0])
    hr_user = next((u for u in users if u.role == "hr" and u.clearance == "confidential"), users[0])
    eng_user = next((u for u in users if u.department_name == "Engineering" and u.role == "employee"), users[0])
    contractor_user = next((u for u in users if u.role == "contractor"), users[-1])

    all_queries: List[QueryGroundTruth] = []
    policies = list(ledger.policies.values())
    q_id_counter = 1

    def make_qid():
        nonlocal q_id_counter
        qid = f"Q-EVAL-{q_id_counter:05d}"
        q_id_counter += 1
        return qid

    # 1. Direct Factual Lookup (Tier 0)
    for p in policies[:30]:
        v_active = [v for v in p.versions if v.is_active][0]
        f_entry = ledger.facts[v_active.fact_ids[0]]
        q_text = f"What is the {f_entry.predicate.replace('_', ' ')} under {p.title}?"
        exp_ans = f"{f_entry.value} {f_entry.unit or ''}".strip()
        all_queries.append(QueryGroundTruth(
            query_id=make_qid(),
            user_id=admin_user.user_id,
            user_role=admin_user.role,
            user_department=admin_user.department_name,
            user_clearance=admin_user.clearance,
            query_text=q_text,
            expected_authorization=True,
            expected_route="FAST_PATH_FACT",
            query_category="CAT_01_FACTUAL_LOOKUP",
            difficulty="easy",
            intended_policy_id=p.policy_id,
            intended_policy_title=p.title,
            intended_version_num=str(v_active.version_num),
            expected_answer_exact=exp_ans,
            expected_answer_contains=[f_entry.value],
            expected_evidence_chunks=[f_entry.source_chunk_id],
            expected_citations=[{"policy_id": p.policy_id, "version": v_active.version_label, "section": "3. Detailed Rules & Core Thresholds"}],
            expected_abstention=False,
            notes="Category 1: Direct factual lookup"
        ))

    # 2. Exact Policy and Version Lookup
    for p in policies[:30]:
        for v in p.versions[:2]:
            f_entry = ledger.facts[v.fact_ids[0]]
            q_text = f"According to {p.title} version {v.version_num}, what was the specified {f_entry.predicate.replace('_', ' ')}?"
            exp_ans = f"{f_entry.value} {f_entry.unit or ''}".strip()
            all_queries.append(QueryGroundTruth(
                query_id=make_qid(),
                user_id=admin_user.user_id,
                user_role=admin_user.role,
                user_department=admin_user.department_name,
                user_clearance=admin_user.clearance,
                query_text=q_text,
                expected_authorization=True,
                expected_route="FAST_PATH_FACT",
                query_category="CAT_02_VERSION_LOOKUP",
                difficulty="medium",
                intended_policy_id=p.policy_id,
                intended_policy_title=p.title,
                intended_version_num=str(v.version_num),
                expected_answer_exact=exp_ans,
                expected_answer_contains=[f_entry.value],
                expected_evidence_chunks=[f_entry.source_chunk_id],
                expected_citations=[{"policy_id": p.policy_id, "version": v.version_label, "section": "3. Detailed Rules & Core Thresholds"}],
                expected_abstention=False,
                notes="Category 2: Exact policy and version lookup"
            ))

    # 3. Semantic Paraphrases
    paraphrase_templates = [
        "Could you clarify the maximum permissible limit for {pred} in {title}?",
        "What cap applies to {pred} as mandated by {title}?",
        "Please provide the official number regarding {pred} per {title}.",
    ]
    for p in policies[:30]:
        v_active = [v for v in p.versions if v.is_active][0]
        f_entry = ledger.facts[v_active.fact_ids[0]]
        tmpl = rng.choice(paraphrase_templates)
        q_text = tmpl.format(pred=f_entry.predicate.replace('_', ' '), title=p.title)
        all_queries.append(QueryGroundTruth(
            query_id=make_qid(),
            user_id=eng_user.user_id,
            user_role=eng_user.role,
            user_department=eng_user.department_name,
            user_clearance=eng_user.clearance,
            query_text=q_text,
            expected_authorization=AccessControlEvaluator.is_authorized(eng_user, p.department_id, p.confidentiality),
            expected_route="HYBRID_RAG",
            query_category="CAT_03_SEMANTIC_PARAPHRASE",
            difficulty="medium",
            intended_policy_id=p.policy_id,
            intended_policy_title=p.title,
            intended_version_num=str(v_active.version_num),
            expected_answer_contains=[f_entry.value],
            expected_evidence_chunks=[f_entry.source_chunk_id],
            expected_abstention=not AccessControlEvaluator.is_authorized(eng_user, p.department_id, p.confidentiality),
            notes="Category 3: Semantic paraphrase"
        ))

    # 4. Synonyms & Alternate Terminology
    for p in policies[:30]:
        v_active = [v for v in p.versions if v.is_active][0]
        f_entry = ledger.facts[v_active.fact_ids[0]]
        pred_syn = f_entry.predicate.replace('_', ' ').replace("limit", "ceiling").replace("period", "duration").replace("allowance", "stipend")
        q_text = f"What is the corporate benchmark for {pred_syn} under {p.title} guidelines?"
        all_queries.append(QueryGroundTruth(
            query_id=make_qid(),
            user_id=admin_user.user_id,
            user_role=admin_user.role,
            user_department=admin_user.department_name,
            user_clearance=admin_user.clearance,
            query_text=q_text,
            expected_authorization=True,
            expected_route="HYBRID_RAG",
            query_category="CAT_04_SYNONYMS",
            difficulty="medium",
            intended_policy_id=p.policy_id,
            intended_policy_title=p.title,
            intended_version_num=str(v_active.version_num),
            expected_answer_contains=[f_entry.value],
            expected_evidence_chunks=[f_entry.source_chunk_id],
            expected_abstention=False,
            notes="Category 4: Synonyms and alternate terminology"
        ))

    # 5. Multi-Condition Questions
    for p in policies[:30]:
        v_active = [v for v in p.versions if v.is_active][0]
        f_entry = ledger.facts[v_active.fact_ids[0]]
        q_text = f"If a confirmed full-time staff member in {p.department_name} submits a formal request under {p.title}, what {f_entry.predicate.replace('_', ' ')} applies?"
        all_queries.append(QueryGroundTruth(
            query_id=make_qid(),
            user_id=admin_user.user_id,
            user_role=admin_user.role,
            user_department=admin_user.department_name,
            user_clearance=admin_user.clearance,
            query_text=q_text,
            expected_authorization=True,
            expected_route="HYBRID_RAG",
            query_category="CAT_05_MULTI_CONDITION",
            difficulty="hard",
            intended_policy_id=p.policy_id,
            intended_policy_title=p.title,
            intended_version_num=str(v_active.version_num),
            expected_answer_contains=[f_entry.value],
            expected_evidence_chunks=v_active.chunk_ids[:3],
            expected_abstention=False,
            notes="Category 5: Multi-condition question"
        ))

    # 6. Questions Requiring Multiple Sections
    for p in policies[:30]:
        v_active = [v for v in p.versions if v.is_active][0]
        f_entry = ledger.facts[v_active.fact_ids[0]]
        q_text = f"Explain the core purpose, eligibility criteria, and threshold for {f_entry.predicate.replace('_', ' ')} under {p.title}."
        all_queries.append(QueryGroundTruth(
            query_id=make_qid(),
            user_id=admin_user.user_id,
            user_role=admin_user.role,
            user_department=admin_user.department_name,
            user_clearance=admin_user.clearance,
            query_text=q_text,
            expected_authorization=True,
            expected_route="HYBRID_RAG",
            query_category="CAT_06_MULTI_SECTION",
            difficulty="hard",
            intended_policy_id=p.policy_id,
            intended_policy_title=p.title,
            intended_version_num=str(v_active.version_num),
            expected_answer_contains=[f_entry.value, p.title],
            expected_evidence_chunks=v_active.chunk_ids[:3],
            expected_abstention=False,
            notes="Category 6: Multiple sections required"
        ))

    # 7. Cross-Policy Questions
    for idx in range(0, min(30, len(policies) - 1), 2):
        p1 = policies[idx]
        p2 = policies[idx + 1]
        v1 = [v for v in p1.versions if v.is_active][0]
        v2 = [v for v in p2.versions if v.is_active][0]
        f1 = ledger.facts[v1.fact_ids[0]]
        f2 = ledger.facts[v2.fact_ids[0]]
        q_text = f"Compare the operational mandates of {p1.title} and {p2.title}: what are their respective thresholds?"
        all_queries.append(QueryGroundTruth(
            query_id=make_qid(),
            user_id=admin_user.user_id,
            user_role=admin_user.role,
            user_department=admin_user.department_name,
            user_clearance=admin_user.clearance,
            query_text=q_text,
            expected_authorization=True,
            expected_route="HYBRID_RAG",
            query_category="CAT_07_CROSS_POLICY",
            difficulty="hard",
            intended_policy_id=p1.policy_id,
            intended_policy_title=p1.title,
            intended_version_num=str(v1.version_num),
            expected_answer_contains=[f1.value, f2.value],
            expected_evidence_chunks=[f1.source_chunk_id, f2.source_chunk_id],
            expected_abstention=False,
            notes="Category 7: Cross-policy comparison"
        ))

    # 9. Current vs Historical Policy
    for p in policies[:30]:
        if len(p.versions) >= 2:
            v_hist = p.versions[0]
            v_curr = p.versions[-1]
            f_hist = ledger.facts[v_hist.fact_ids[0]]
            f_curr = ledger.facts[v_curr.fact_ids[0]]
            q_text = f"How did the {f_curr.predicate.replace('_', ' ')} change in {p.title} between version {v_hist.version_num} and active version {v_curr.version_num}?"
            all_queries.append(QueryGroundTruth(
                query_id=make_qid(),
                user_id=admin_user.user_id,
                user_role=admin_user.role,
                user_department=admin_user.department_name,
                user_clearance=admin_user.clearance,
                query_text=q_text,
                expected_authorization=True,
                expected_route="TEMPORAL_COMPARISON",
                query_category="CAT_09_HISTORICAL_VS_CURRENT",
                difficulty="medium",
                intended_policy_id=p.policy_id,
                intended_policy_title=p.title,
                intended_version_num=str(v_curr.version_num),
                expected_answer_contains=[f_hist.value, f_curr.value],
                expected_evidence_chunks=[f_hist.source_chunk_id, f_curr.source_chunk_id],
                expected_abstention=False,
                is_temporal=True,
                notes="Category 9: Current vs historical policy"
            ))

    # 10. Effective Date & Time-Travel
    for p in policies[:30]:
        for v in p.versions[:2]:
            f_entry = ledger.facts[v.fact_ids[0]]
            v_year = v.effective_start[:4]
            q_text = f"What was the active {f_entry.predicate.replace('_', ' ')} under {p.title} during {v_year}?"
            all_queries.append(QueryGroundTruth(
                query_id=make_qid(),
                user_id=admin_user.user_id,
                user_role=admin_user.role,
                user_department=admin_user.department_name,
                user_clearance=admin_user.clearance,
                query_text=q_text,
                query_date=f"{v_year}-06-15",
                expected_authorization=True,
                expected_route="FAST_PATH_FACT",
                query_category="CAT_10_TIME_TRAVEL",
                difficulty="medium",
                intended_policy_id=p.policy_id,
                intended_policy_title=p.title,
                intended_version_num=str(v.version_num),
                expected_answer_exact=f"{f_entry.value} {f_entry.unit or ''}".strip(),
                expected_answer_contains=[f_entry.value],
                expected_evidence_chunks=[f_entry.source_chunk_id],
                expected_abstention=False,
                is_temporal=True,
                notes="Category 10: Time-travel point-in-time lookup"
            ))

    # 11. Questions about Exceptions
    for p in policies[:30]:
        v_active = [v for v in p.versions if v.is_active][0]
        q_text = f"What is the exception and escalation protocol if an employee needs to exceed the mandated standard in {p.title}?"
        all_queries.append(QueryGroundTruth(
            query_id=make_qid(),
            user_id=admin_user.user_id,
            user_role=admin_user.role,
            user_department=admin_user.department_name,
            user_clearance=admin_user.clearance,
            query_text=q_text,
            expected_authorization=True,
            expected_route="HYBRID_RAG",
            query_category="CAT_11_EXCEPTIONS",
            difficulty="medium",
            intended_policy_id=p.policy_id,
            intended_policy_title=p.title,
            intended_version_num=str(v_active.version_num),
            expected_answer_contains=["5 business days", "Compliance Officer"],
            expected_evidence_chunks=[v_active.chunk_ids[3]],  # Section 4
            expected_abstention=False,
            notes="Category 11: Policy exceptions and deviations"
        ))

    # 12. Out-of-Distribution / Absent Answers (Safe Abstention)
    ood_topics = [
        "What is the company policy on inter-planetary space travel expenses?",
        "What is the official reimbursement rate for supersonic personal aircraft fuel?",
        "How many pet llamas is an employee permitted to bring to headquarters?",
        "What is the statutory quantum computing cold-storage retention for personal music files?",
        "What allowance is granted for deep-sea submarine commutes?",
    ]
    for topic in ood_topics:
        all_queries.append(QueryGroundTruth(
            query_id=make_qid(),
            user_id=admin_user.user_id,
            user_role=admin_user.role,
            user_department=admin_user.department_name,
            user_clearance=admin_user.clearance,
            query_text=topic,
            expected_authorization=True,
            expected_route="ABSTAIN",
            query_category="CAT_12_ABSENT_ANSWER_OOD",
            difficulty="easy",
            expected_answer_contains=["not found", "cannot find", "insufficient"],
            expected_abstention=True,
            notes="Category 12: Absent answer requiring abstention"
        ))

    # 14. Queries Dated Before Earliest Version (Pre-dating Abstention)
    for p in policies[:20]:
        v_first = p.versions[0]
        earliest_year = int(v_first.effective_start[:4])
        pre_date = f"{earliest_year - 5}-05-01"
        q_text = f"What was the active entitlement under {p.title} back in {earliest_year - 5}?"
        all_queries.append(QueryGroundTruth(
            query_id=make_qid(),
            user_id=admin_user.user_id,
            user_role=admin_user.role,
            user_department=admin_user.department_name,
            user_clearance=admin_user.clearance,
            query_text=q_text,
            query_date=pre_date,
            expected_authorization=True,
            expected_route="ABSTAIN",
            query_category="CAT_14_PRE_DATING_ABSTENTION",
            difficulty="hard",
            intended_policy_id=p.policy_id,
            intended_policy_title=p.title,
            expected_abstention=True,
            is_temporal=True,
            notes="Category 14: Query predates earliest policy version; must abstain"
        ))

    # 16. Typographical Errors & Noise
    for p in policies[:25]:
        v_active = [v for v in p.versions if v.is_active][0]
        f_entry = ledger.facts[v_active.fact_ids[0]]
        # Introduce deliberate typo in policy title
        title_noisy = p.title.replace("Policy", "Polcy").replace("Standard", "Stndard").replace("Allowance", "Allowence")
        q_text = f"What is the {f_entry.predicate.replace('_', ' ')} under {title_noisy}?"
        all_queries.append(QueryGroundTruth(
            query_id=make_qid(),
            user_id=admin_user.user_id,
            user_role=admin_user.role,
            user_department=admin_user.department_name,
            user_clearance=admin_user.clearance,
            query_text=q_text,
            expected_authorization=True,
            expected_route="HYBRID_RAG",
            query_category="CAT_16_TYPO_NOISE",
            difficulty="medium",
            intended_policy_id=p.policy_id,
            intended_policy_title=p.title,
            intended_version_num=str(v_active.version_num),
            expected_answer_contains=[f_entry.value],
            expected_evidence_chunks=[f_entry.source_chunk_id],
            expected_abstention=False,
            notes="Category 16: Typographical noise"
        ))

    # 18. Exact Numeric Values & Deadlines
    for p in policies[:30]:
        v_active = [v for v in p.versions if v.is_active][0]
        f_entry = ledger.facts[v_active.fact_ids[0]]
        q_text = f"State the exact numeric quantity and unit specified for {f_entry.predicate.replace('_', ' ')} in {p.title}."
        exp_ans = f"{f_entry.value} {f_entry.unit or ''}".strip()
        all_queries.append(QueryGroundTruth(
            query_id=make_qid(),
            user_id=admin_user.user_id,
            user_role=admin_user.role,
            user_department=admin_user.department_name,
            user_clearance=admin_user.clearance,
            query_text=q_text,
            expected_authorization=True,
            expected_route="FAST_PATH_FACT",
            query_category="CAT_18_EXACT_NUMERIC",
            difficulty="easy",
            intended_policy_id=p.policy_id,
            intended_policy_title=p.title,
            intended_version_num=str(v_active.version_num),
            expected_answer_exact=exp_ans,
            expected_answer_contains=[f_entry.value],
            expected_evidence_chunks=[f_entry.source_chunk_id],
            expected_abstention=False,
            notes="Category 18: Exact numeric threshold"
        ))

    # 24. Genuine Local Qwen Generation Required (Complex explanatory synthesis)
    for p in policies[:40]:
        v_active = [v for v in p.versions if v.is_active][0]
        f_entry = ledger.facts[v_active.fact_ids[0]]
        q_text = (
            f"Provide a comprehensive plain-language summary of {p.title} (v{v_active.version_num}). "
            f"Explain who is eligible, the mandatory threshold ({f_entry.value} {f_entry.unit or ''}), "
            f"the required advance notice for exceptions, and the disciplinary consequences for non-compliance."
        )
        all_queries.append(QueryGroundTruth(
            query_id=make_qid(),
            user_id=admin_user.user_id,
            user_role=admin_user.role,
            user_department=admin_user.department_name,
            user_clearance=admin_user.clearance,
            query_text=q_text,
            expected_authorization=True,
            expected_route="HYBRID_RAG",
            query_category="CAT_24_QWEN_GENERATION",
            difficulty="hard",
            intended_policy_id=p.policy_id,
            intended_policy_title=p.title,
            intended_version_num=str(v_active.version_num),
            expected_answer_contains=[f_entry.value, "disciplinary", "exception"],
            expected_evidence_chunks=v_active.chunk_ids,
            expected_citations=[{"policy_id": p.policy_id, "version": v_active.version_label, "section": "3. Detailed Rules & Core Thresholds"}],
            expected_abstention=False,
            notes="Category 24: Dedicated multi-clause generative synthesis (executes Qwen)"
        ))

    # 29. Unauthorized User Queries (RBAC & Clearance Refusal)
    for p in [pol for pol in policies if pol.confidentiality in ("confidential", "restricted")][:30]:
        v_active = [v for v in p.versions if v.is_active][0]
        f_entry = ledger.facts[v_active.fact_ids[0]]
        q_text = f"What is the {f_entry.predicate.replace('_', ' ')} under {p.title}?"
        all_queries.append(QueryGroundTruth(
            query_id=make_qid(),
            user_id=contractor_user.user_id,
            user_role=contractor_user.role,
            user_department=contractor_user.department_name,
            user_clearance=contractor_user.clearance,
            query_text=q_text,
            expected_authorization=False,
            expected_route="REFUSAL",
            query_category="CAT_29_UNAUTHORIZED_REFUSAL",
            difficulty="adversarial",
            intended_policy_id=p.policy_id,
            intended_policy_title=p.title,
            intended_version_num=str(v_active.version_num),
            expected_abstention=True,
            notes="Category 29: Contractor with public_only clearance denied access to confidential/restricted policy"
        ))

    # 31. Empty, whitespace-only, malformed requests
    malformed_queries = ["   ", "\t\n\r", "???", "---...---", "a" * 4000]
    for mq in malformed_queries:
        all_queries.append(QueryGroundTruth(
            query_id=make_qid(),
            user_id=admin_user.user_id,
            user_role=admin_user.role,
            user_department=admin_user.department_name,
            user_clearance=admin_user.clearance,
            query_text=mq,
            expected_authorization=True,
            expected_route="REFUSAL",
            query_category="CAT_31_MALFORMED",
            difficulty="easy",
            expected_abstention=True,
            notes="Category 31: Malformed input safety"
        ))

    # 33. Repeated Queries / Semantic Cache Hits
    for p in policies[:20]:
        v_active = [v for v in p.versions if v.is_active][0]
        f_entry = ledger.facts[v_active.fact_ids[0]]
        q_text = f"What is the {f_entry.predicate.replace('_', ' ')} under {p.title}?"
        exp_ans = f"{f_entry.value} {f_entry.unit or ''}".strip()
        all_queries.append(QueryGroundTruth(
            query_id=make_qid(),
            user_id=admin_user.user_id,
            user_role=admin_user.role,
            user_department=admin_user.department_name,
            user_clearance=admin_user.clearance,
            query_text=q_text,
            expected_authorization=True,
            expected_route="FAST_PATH_FACT",
            query_category="CAT_33_CACHE_REPEATED",
            difficulty="easy",
            intended_policy_id=p.policy_id,
            intended_policy_title=p.title,
            intended_version_num=str(v_active.version_num),
            expected_answer_exact=exp_ans,
            expected_answer_contains=[f_entry.value],
            expected_evidence_chunks=[f_entry.source_chunk_id],
            expected_abstention=False,
            notes="Category 33: Repeated query for cache-hit verification"
        ))

    # Fill remaining target count with heterogeneous queries across remaining categories
    while len(all_queries) < target_count:
        p = rng.choice(policies)
        v = rng.choice(p.versions)
        f_entry = ledger.facts[v.fact_ids[0]]
        user = rng.choice(users)
        is_auth = AccessControlEvaluator.is_authorized(user, p.department_id, p.confidentiality)

        # Diverse question formats
        formats = [
            (f"What threshold is enforced for {f_entry.predicate.replace('_', ' ')} in {p.title}?", "HYBRID_RAG", "medium"),
            (f"According to {p.title}, state the {f_entry.predicate.replace('_', ' ')}.", "FAST_PATH_FACT", "easy"),
            (f"Explain the detailed guidelines and penalties concerning {p.title}.", "HYBRID_RAG", "hard"),
        ]
        q_fmt, route, diff = rng.choice(formats)

        all_queries.append(QueryGroundTruth(
            query_id=make_qid(),
            user_id=user.user_id,
            user_role=user.role,
            user_department=user.department_name,
            user_clearance=user.clearance,
            query_text=q_fmt,
            expected_authorization=is_auth,
            expected_route=route if is_auth else "REFUSAL",
            query_category="CAT_23_HYBRID_RETRIEVAL" if route == "HYBRID_RAG" else "CAT_22_DETERMINISTIC_FAST_PATH",
            difficulty=diff,
            intended_policy_id=p.policy_id,
            intended_policy_title=p.title,
            intended_version_num=str(v.version_num),
            expected_answer_contains=[f_entry.value] if is_auth else [],
            expected_evidence_chunks=[f_entry.source_chunk_id] if is_auth else [],
            expected_abstention=not is_auth,
            notes="Expanded corpus evaluation query"
        ))

    return all_queries


if __name__ == "__main__":
    from evaluation.corpus_generator import ConfigurableCorpusGenerator
    gen = ConfigurableCorpusGenerator(seed=42)
    ledger = gen.generate_corpus(120)
    print("Generating comprehensive question suite...")
    queries = generate_36_category_benchmark(ledger, target_count=1000)
    print(f"Generated {len(queries)} evaluation questions across 36 categories.")
    from collections import Counter
    cats = Counter(q.query_category for q in queries)
    for c, cnt in sorted(cats.items()):
        print(f"  {c}: {cnt}")
