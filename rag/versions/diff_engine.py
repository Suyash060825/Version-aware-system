from typing import List, Dict, Any
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

class PolicyDiffEngine:
    """
    Computes a deterministic structured diff between two policy versions.
    Uses fact-level comparison when possible.
    """
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
                        unit=fb.unit
                    ))
                else:
                    unchanged.append(fb)
                    
        for key, fa in map_a.items():
            if key not in map_b:
                removed.append(fa)
                
        return PolicyDiff(added=added, removed=removed, changed=changed, unchanged=unchanged)
