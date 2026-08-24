"""
rag/facts/fact_resolver.py
Fast deterministic fact resolver with relevance scoring for Level 0 factual queries across 20+ policy domains.
"""
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from models import db, Policy, PolicyVersion, PolicyFact, PolicyChunkV2
from rag.facts.fact_store import FactStore

@dataclass
class FactResolutionResult:
    found: bool
    answer: Optional[str]
    citations: list
    fact: Optional[Any]
    confidence: float

class FactResolver:
    FACT_PATTERNS = [
        (r"\b(?:annual leave|paid leave|vacation days|leave entitlement|days of leave|days of annual leave|pto)\b", ["annual_leave"]),
        (r"\b(?:sick leave|medical leave)\b", ["sick_leave"]),
        (r"\b(?:maternity leave|maternity)\b", ["maternity_leave"]),
        (r"\b(?:paternity leave|paternity)\b", ["paternity_leave"]),
        (r"\b(?:bereavement leave|bereavement)\b", ["bereavement_leave"]),
        (r"\b(?:remote work|work from home|wfh|days.*remotely)\b", ["remote_work_allowance"]),
        (r"\b(?:internet allowance|internet reimbursement|wifi reimbursement)\b", ["internet_allowance"]),
        (r"\b(?:core hours|working hours|work hours|office hours)\b", ["core_hours"]),
        (r"\b(?:grace period|late arrival|arrival window)\b", ["grace_period"]),
        (r"\b(?:hotel|hotel limit|lodging limit|domestic hotel)\b", ["hotel_limit"]),
        (r"\b(?:daily allowance|per diem|metro daily allowance|metro da)\b", ["daily_allowance_metro"]),
        (r"\b(?:non-metro|non metro)\b", ["daily_allowance_non_metro"]),
        (r"\b(?:medical insurance|health insurance|mediclaim|hospitalization cover)\b", ["medical_insurance_limit"]),
        (r"\b(?:opd|opd limit|opd allowance|outpatient)\b", ["opd_limit"]),
        (r"\b(?:notice period|resignation notice|resignation period)\b", ["notice_period"]),
        (r"\b(?:pip|performance improvement plan|pip duration)\b", ["pip_duration"]),
        (r"\b(?:learning budget|training budget|education assistance|certification reimbursement)\b", ["learning_budget"]),
        (r"\b(?:laptop refresh|hardware refresh|laptop replacement)\b", ["hardware_refresh"]),
        (r"\b(?:referral bonus.*senior|senior referral|lead referral)\b", ["referral_bonus_senior"]),
        (r"\b(?:referral bonus|referral amount|referral payout)\b", ["referral_bonus_junior", "referral_bonus_senior"]),
        (r"\b(?:relocation|relocation allowance|relocation package|moving allowance)\b", ["relocation_allowance"]),
        (r"\b(?:gift limit|gift policy|accept.*gift|corporate gift)\b", ["gift_limit"]),
        (r"\b(?:incident report|report.*incident|security incident)\b", ["incident_reporting_deadline"]),
        (r"\b(?:password change|password expiration|rotate password|password rotation)\b", ["password_rotation_period"]),
    ]

    def __init__(self):
        self.store = FactStore()

    def try_resolve(self, query: str, scope: Optional[Any] = None, temporal: Optional[Any] = None, user: Optional[Any] = None) -> FactResolutionResult:
        query_lower = query.lower()
        query_words = set(re.findall(r"\b[a-z0-9]+\b", query_lower))

        target_predicates = []
        for pattern, preds in self.FACT_PATTERNS:
            if re.search(pattern, query_lower):
                target_predicates.extend(preds)

        policy_id = temporal.policy_id if temporal and hasattr(temporal, "policy_id") else None
        version_id = temporal.version_id if temporal and hasattr(temporal, "version_id") else None

        # Fetch candidate facts
        all_facts = PolicyFact.query
        if policy_id:
            all_facts = all_facts.filter_by(policy_id=policy_id)
        if version_id:
            all_facts = all_facts.filter_by(version_id=version_id)
        
        candidate_facts = all_facts.all()

        from rag.authorization.evidence_filter import EvidenceFilter
        evidence_filter = EvidenceFilter()

        best_fact = None
        best_score = -1

        for fact in candidate_facts:
            policy = db.session.get(Policy, fact.policy_id)
            version = db.session.get(PolicyVersion, fact.version_id)
            if not policy or not version:
                continue

            # Authorization Check
            if user is not None and not evidence_filter.is_authorized_for_policy(user, policy):
                continue

            # Temporal Validity Check
            tq = getattr(temporal, "temporal_query", None) if temporal else None
            t_date = getattr(temporal, "target_date", None) if temporal else None
            req_ver = getattr(temporal, "requested_version", None) if temporal else None

            if req_ver:
                if str(version.version_num) != str(req_ver) and version.version_label != req_ver and f"v{version.version_num}" != req_ver:
                    continue
            elif tq and (tq.start_date or tq.end_date):
                if not version.is_valid_for_interval(tq.start_date, tq.end_date):
                    continue
            elif t_date:
                if not version.is_valid_for_date(t_date):
                    continue

            score = 0
            pred = (fact.predicate or "").lower()
            clean_pred = pred.replace("_", " ")
            subj = (fact.subject or "").lower()
            p_title = (policy.title if policy else "").lower()

            # Active version preference when not historical
            if version and version.is_active and not (temporal and temporal.is_historic):
                score += 8

            # Predicate match
            if pred in target_predicates:
                score += 30
            elif clean_pred in query_lower:
                score += 25
            else:
                continue

            # Title overlap
            title_words = set(re.findall(r"\b[a-z0-9]+\b", p_title))
            score += len(query_words & title_words) * 5

            # Subject overlap
            subj_words = set(re.findall(r"\b[a-z0-9]+\b", subj))
            score += len(query_words & subj_words) * 3

            if score > best_score and score >= 30:
                best_score = score
                best_fact = fact

        if best_fact:
            return self._format_fact_result(best_fact)

        return FactResolutionResult(found=False, answer=None, citations=[], fact=None, confidence=0.0)

    def _format_fact_result(self, fact: PolicyFact) -> FactResolutionResult:
        policy = db.session.get(Policy, fact.policy_id)
        version = db.session.get(PolicyVersion, fact.version_id)
        
        policy_title = policy.title if policy else "Policy"
        version_num = version.version_number if version else "1.0"

        # Format deterministic natural language answer
        unit_str = f" {fact.unit}" if fact.unit and not fact.value.endswith(fact.unit) and not fact.value.startswith("Rs") else ""
        scope_str = f" ({fact.scope})" if fact.scope else ""
        
        answer = f"According to the {policy_title} (v{version_num}), the {fact.subject or fact.predicate.replace('_', ' ')} is {fact.value}{unit_str}{scope_str}."

        section = "General"
        page = 1
        if fact.source_chunk_id:
            chunk = PolicyChunkV2.query.filter_by(chunk_id=fact.source_chunk_id).first()
            if chunk:
                section = chunk.section_path or section
                page = chunk.page or page

        citations = [{
            "policy_id": fact.policy_id,
            "version_id": fact.version_id,
            "policy_name": policy_title,
            "version": version_num,
            "section": section,
            "page": page,
            "chunk_id": fact.source_chunk_id
        }]

        return FactResolutionResult(
            found=True,
            answer=answer,
            citations=citations,
            fact=fact,
            confidence=fact.confidence or 0.98
        )
