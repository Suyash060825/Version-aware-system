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
    value: Optional[str] = None
    unit: Optional[str] = None
    subject: Optional[str] = None
    predicate: Optional[str] = None
    policy_id: Optional[int] = None
    version_id: Optional[int] = None
    source_chunk_id: Optional[str] = None
    confidence_score: float = 0.0

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
        auth_context = scope or user
        if auth_context is None:
            # SECURITY REQUIREMENT 7: Fact route must fail closed without explicit authorization context
            return FactResolutionResult(found=False, answer=None, citations=[], fact=None, confidence=0.0)

        query_lower = query.lower()
        query_words = set(re.findall(r"\b[a-z0-9]+\b", query_lower))

        target_predicates = []
        for pattern, preds in self.FACT_PATTERNS:
            if re.search(pattern, query_lower):
                target_predicates.extend(preds)

        if not target_predicates:
            return FactResolutionResult(found=False, answer=None, citations=[], fact=None, confidence=0.0)

        policy_id = temporal.policy_id if temporal and hasattr(temporal, "policy_id") else None
        version_id = temporal.version_id if temporal and hasattr(temporal, "version_id") else None

        # PERFORMANCE & SCALE REQUIREMENT 6: SQL-level candidate pre-filtering
        query_facts = PolicyFact.query.filter(PolicyFact.predicate.in_(target_predicates))
        if policy_id:
            query_facts = query_facts.filter_by(policy_id=policy_id)
        if version_id:
            query_facts = query_facts.filter_by(version_id=version_id)
        if scope and getattr(scope, "allowed_policy_ids", None) is not None:
            query_facts = query_facts.filter(PolicyFact.policy_id.in_(scope.allowed_policy_ids))
        
        candidate_facts = query_facts.all()
        if not candidate_facts:
            return FactResolutionResult(found=False, answer=None, citations=[], fact=None, confidence=0.0)

        from rag.authorization.evidence_filter import EvidenceFilter
        evidence_filter = EvidenceFilter()

        # PERFORMANCE REQUIREMENT 11: Bulk load policies and versions (eliminates N+1 queries)
        p_ids = {f.policy_id for f in candidate_facts}
        v_ids = {f.version_id for f in candidate_facts}
        policies_map = {p.id: p for p in Policy.query.filter(Policy.id.in_(p_ids)).all()} if p_ids else {}
        versions_map = {v.id: v for v in PolicyVersion.query.filter(PolicyVersion.id.in_(v_ids)).all()} if v_ids else {}

        scored_candidates = []

        for fact in candidate_facts:
            policy = policies_map.get(fact.policy_id)
            version = versions_map.get(fact.version_id)
            if not policy or not version:
                continue

            # Authorization Check
            if not evidence_filter.is_authorized_for_policy(auth_context, policy):
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

            if score >= 30:
                scored_candidates.append((score, fact))

        if not scored_candidates:
            return FactResolutionResult(found=False, answer=None, citations=[], fact=None, confidence=0.0)

        # PRECISION & AMBIGUITY REQUIREMENTS 8 & 9: Multi-attribute semantic ambiguity comparison
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_fact = scored_candidates[0]

        if len(scored_candidates) > 1:
            second_score, second_fact = scored_candidates[1]
            # Check semantic divergence beyond just fact.value (subject, predicate, policy, version, value, unit)
            semantic_divergence = (
                second_fact.value != best_fact.value or
                second_fact.subject != best_fact.subject or
                second_fact.predicate != best_fact.predicate or
                second_fact.policy_id != best_fact.policy_id or
                second_fact.version_id != best_fact.version_id or
                second_fact.unit != best_fact.unit
            )
            if semantic_divergence and (best_score - second_score) < 10:
                return FactResolutionResult(found=False, answer=None, citations=[], fact=None, confidence=0.0)

        return self._format_fact_result(best_fact)

    def _format_fact_result(self, fact: PolicyFact) -> FactResolutionResult:
        policy = db.session.get(Policy, fact.policy_id)
        version = db.session.get(PolicyVersion, fact.version_id)
        
        policy_title = policy.title if policy else "Policy"
        version_num = version.version_number if version else "1.0"

        # Resolve authoritative source chunk (no fact response is valid without source evidence)
        section = "General"
        page = 1
        chunk = None
        if fact.source_chunk_id:
            chunk = PolicyChunkV2.query.filter_by(chunk_id=fact.source_chunk_id).first()
        if not chunk and version:
            chunk = PolicyChunkV2.query.filter_by(policy_id=fact.policy_id, version_id=version.id).first()

        if not chunk:
            return FactResolutionResult(found=False, answer=None, citations=[], fact=None, confidence=0.0)

        section = chunk.section_path or section
        page = chunk.page or page
        source_cid = chunk.chunk_id

        # Format deterministic natural language answer
        unit_str = f" {fact.unit}" if fact.unit and not fact.value.endswith(fact.unit) and not fact.value.startswith("Rs") else ""
        scope_str = f" ({fact.scope})" if fact.scope else ""
        
        answer = f"According to the {policy_title} (v{version_num}), the {fact.subject or fact.predicate.replace('_', ' ')} is {fact.value}{unit_str}{scope_str}."

        citations = [{
            "policy_id": fact.policy_id,
            "version_id": fact.version_id,
            "policy_name": policy_title,
            "version": version_num,
            "section": section,
            "page": page,
            "chunk_id": source_cid
        }]

        conf = float(fact.confidence or 0.98)
        return FactResolutionResult(
            found=True,
            answer=answer,
            citations=citations,
            fact=fact,
            confidence=conf,
            value=fact.value,
            unit=fact.unit,
            subject=fact.subject,
            predicate=fact.predicate,
            policy_id=fact.policy_id,
            version_id=fact.version_id,
            source_chunk_id=source_cid,
            confidence_score=conf
        )
