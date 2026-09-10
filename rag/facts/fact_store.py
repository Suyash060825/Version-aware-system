"""
rag/facts/fact_store.py
Persistent, indexed store and query interface for extracted policy facts.
"""
from typing import List, Optional, Dict
from models import db, PolicyFact, Policy, PolicyVersion

class FactStore:
    def __init__(self):
        pass

    def get_fact(self, predicate: str, policy_id: Optional[int] = None, version_id: Optional[int] = None) -> Optional[PolicyFact]:
        """Fetch a single fact matching predicate and optional policy/version."""
        q = PolicyFact.query.filter(PolicyFact.predicate.ilike(f"%{predicate}%"))
        if policy_id:
            q = q.filter_by(policy_id=policy_id)
        if version_id:
            q = q.filter_by(version_id=version_id)
        return q.order_by(PolicyFact.confidence.desc(), PolicyFact.id.desc()).first()

    def search_facts(self, query: str, policy_id: Optional[int] = None, version_id: Optional[int] = None, limit: int = 5) -> List[PolicyFact]:
        """Search facts by subject, predicate, or value."""
        term = f"%{query}%"
        q = PolicyFact.query.filter(
            (PolicyFact.predicate.ilike(term)) |
            (PolicyFact.subject.ilike(term)) |
            (PolicyFact.value.ilike(term))
        )
        if policy_id:
            q = q.filter_by(policy_id=policy_id)
        if version_id:
            q = q.filter_by(version_id=version_id)
        return q.order_by(PolicyFact.confidence.desc()).limit(limit).all()

    def get_all_by_policy(self, policy_id: int, version_id: Optional[int] = None) -> List[PolicyFact]:
        q = PolicyFact.query.filter_by(policy_id=policy_id)
        if version_id:
            q = q.filter_by(version_id=version_id)
        return q.all()

    def save_facts(self, facts: List[PolicyFact]):
        for f in facts:
            db.session.add(f)
        db.session.commit()
