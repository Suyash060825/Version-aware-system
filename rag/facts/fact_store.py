"""
rag/facts/fact_store.py
Persistent, indexed store and query interface for extracted policy facts.
"""
from typing import List, Optional
from models import db, PolicyFact

class FactStore:
    def __init__(self):
        pass

    @staticmethod
    def _escape_like(text: str) -> str:
        return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def get_fact(self, predicate: str, policy_id: Optional[int] = None, version_id: Optional[int] = None) -> Optional[PolicyFact]:
        """Fetch a single fact matching predicate and optional policy/version."""
        safe_pred = self._escape_like(predicate)
        q = PolicyFact.query.filter(PolicyFact.predicate.ilike(f"%{safe_pred}%"))
        if policy_id:
            q = q.filter_by(policy_id=policy_id)
        if version_id:
            q = q.filter_by(version_id=version_id)
        return q.order_by(PolicyFact.confidence.desc(), PolicyFact.id.desc()).first()

    def search_facts(self, query: str, policy_id: Optional[int] = None, version_id: Optional[int] = None, limit: int = 5) -> List[PolicyFact]:
        """Search facts by subject, predicate, or value."""
        safe_query = self._escape_like(query)
        term = f"%{safe_query}%"
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
