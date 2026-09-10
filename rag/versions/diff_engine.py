"""
rag/versions/diff_engine.py
Deterministic structured diff engine comparing policy facts and text clauses across versions.
"""
import difflib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from models import PolicyFact

@dataclass
class FactDiff:
    predicate: str
    old_value: str
    new_value: str
    unit: str

@dataclass
class PolicyDiff:
    added: List[PolicyFact]
    removed: List[PolicyFact]
    changed: List[FactDiff]
    unchanged: List[PolicyFact]
    added_clauses: List[str]
    removed_clauses: List[str]
    changed_clauses: List[str]

class PolicyDiffEngine:
    def compute_fact_diff(self, version_a_id: int, version_b_id: int) -> PolicyDiff:
        facts_a = PolicyFact.query.filter_by(version_id=version_a_id).all()
        facts_b = PolicyFact.query.filter_by(version_id=version_b_id).all()
        
        map_a = {f"{f.subject}_{f.predicate}_{f.scope}": f for f in facts_a}
        map_b = {f"{f.subject}_{f.predicate}_{f.scope}": f for f in facts_b}
        
        added = []
        removed = []
        changed = []
        unchanged = []
        
        for key, fb in map_b.items():
            if key not in map_a:
                added.append(fb)
            else:
                fa = map_a[key]
                if fa.value != fb.value:
                    changed.append(FactDiff(
                        predicate=fb.predicate,
                        old_value=fa.value,
                        new_value=fb.value,
                        unit=fb.unit or ""
                    ))
                else:
                    unchanged.append(fb)
                    
        for key, fa in map_a.items():
            if key not in map_b:
                removed.append(fa)
                
        return PolicyDiff(
            added=added, removed=removed, changed=changed, unchanged=unchanged,
            added_clauses=[], removed_clauses=[], changed_clauses=[]
        )

    def compute_diff(self, text_a: str, text_b: str, version_a_id: Optional[int] = None, version_b_id: Optional[int] = None) -> Dict[str, Any]:
        """Compute structured diff comparing facts and clauses between two versions."""
        lines_a = [l.strip() for l in text_a.splitlines() if l.strip()]
        lines_b = [l.strip() for l in text_b.splitlines() if l.strip()]

        matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
        added_clauses = []
        removed_clauses = []
        changed_clauses = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "insert":
                added_clauses.extend(lines_b[j1:j2])
            elif tag == "delete":
                removed_clauses.extend(lines_a[i1:i2])
            elif tag == "replace":
                changed_clauses.append(f"{' '.join(lines_a[i1:i2])} -> {' '.join(lines_b[j1:j2])}")

        fact_diff_obj = None
        if version_a_id and version_b_id:
            fact_diff_obj = self.compute_fact_diff(version_a_id, version_b_id)

        return {
            "added_clauses": added_clauses,
            "removed_clauses": removed_clauses,
            "changed_clauses": changed_clauses,
            "fact_diff": fact_diff_obj
        }
