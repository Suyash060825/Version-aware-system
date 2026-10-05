"""
tests/system_characterization/suites/test_cache_integrity.py
Evaluation of Veritas Multi-Tier Semantic Cache.
Tests exact hash (L1), semantic cosine vector (L2), partition isolation across roles/clearances/dates, and post-mutation invalidation.
"""
import sys
import os
import time
import hashlib
from typing import List, Dict, Any, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from rag.cache.semantic_cache import MultiLevelCache
from rag.engine.query_scope import QueryScope
from tests.system_characterization.corpus.user_matrix import build_user_pool
from tests.system_characterization.corpus.ground_truth_ledger import GroundTruthLedger

class CacheIntegrityBenchmark:
    def __init__(self, ledger: GroundTruthLedger):
        self.ledger = ledger
        self.cache = MultiLevelCache()
        self.users = build_user_pool()

    def run_cache_evaluation(self) -> List[Dict[str, Any]]:
        results = []
        user_eng = [u for u in self.users if u.department_name == "Engineering" and u.role == "employee"][0]
        user_hr = [u for u in self.users if u.department_name == "Human Resources" and u.role == "hr"][0]
        user_contractor = [u for u in self.users if u.role == "contractor"][0]

        # Test vector helper
        def make_vec(seed: int) -> List[float]:
            import random
            rng = random.Random(seed)
            raw = [rng.gauss(0, 1) for _ in range(384)]
            norm = sum(x*x for x in raw) ** 0.5
            return [x / norm for x in raw]

        # Scenario 1: Same user + same query -> Hit
        scope_eng = QueryScope.from_user(user_eng)
        vec1 = make_vec(42)
        ans1 = {"answer": "Engineering WFH entitlement is 3 days.", "confidence": 0.95, "chunks_used": 1}
        self.cache.put(vec1, ans1["answer"], [{"policy_id": 1, "version_id": 1}], 1, scope=scope_eng, confidence=0.95)

        hit1 = self.cache.get(vec1, scope=scope_eng)
        results.append({
            "test_scenario": "SAME_USER_SAME_QUERY",
            "expected_outcome": "CACHE_HIT",
            "actual_outcome": "CACHE_HIT" if hit1 else "CACHE_MISS",
            "is_correct": (hit1 is not None),
            "leakage_detected": False
        })

        # Scenario 2: Same query + different clearance (Contractor) -> Scope Isolation (Must be MISS)
        scope_contractor = QueryScope.from_user(user_contractor)
        hit2 = self.cache.get(vec1, scope=scope_contractor)
        results.append({
            "test_scenario": "SAME_QUERY_LOWER_CLEARANCE",
            "expected_outcome": "CACHE_MISS",
            "actual_outcome": "CACHE_HIT" if hit2 else "CACHE_MISS",
            "is_correct": (hit2 is None),
            "leakage_detected": (hit2 is not None)
        })

        # Scenario 3: Same query + different department (HR vs Eng) -> Scope Isolation (Must be MISS)
        scope_hr = QueryScope.from_user(user_hr)
        hit3 = self.cache.get(vec1, scope=scope_hr)
        results.append({
            "test_scenario": "SAME_QUERY_DIFFERENT_DEPARTMENT",
            "expected_outcome": "CACHE_MISS",
            "actual_outcome": "CACHE_HIT" if hit3 else "CACHE_MISS",
            "is_correct": (hit3 is None),
            "leakage_detected": (hit3 is not None)
        })

        # Scenario 4: Same user + different query vector (cosine < 0.90) -> Must be MISS
        vec_diff = make_vec(999)
        hit4 = self.cache.get(vec_diff, scope=scope_eng)
        results.append({
            "test_scenario": "DIFFERENT_QUERY_SAME_USER",
            "expected_outcome": "CACHE_MISS",
            "actual_outcome": "CACHE_HIT" if hit4 else "CACHE_MISS",
            "is_correct": (hit4 is None),
            "leakage_detected": False
        })

        # Scenario 5: Targeted Policy Version Invalidation
        self.cache.invalidate_version(policy_id=1, version_id=1)
        hit5 = self.cache.get(vec1, scope=scope_eng)
        results.append({
            "test_scenario": "POST_UPDATE_INVALIDATION",
            "expected_outcome": "CACHE_MISS",
            "actual_outcome": "CACHE_HIT" if hit5 else "CACHE_MISS",
            "is_correct": (hit5 is None),
            "leakage_detected": (hit5 is not None)
        })

        return results

if __name__ == "__main__":
    ledger = GroundTruthLedger.load("tests/system_characterization/corpus/ground_truth_ledger.json")
    bench = CacheIntegrityBenchmark(ledger)
    res = bench.run_cache_evaluation()
    print("Cache Integrity Results:")
    for r in res:
        print(f"  {r['test_scenario']:32s} | Exp: {r['expected_outcome']:10s} | Act: {r['actual_outcome']:10s} | Correct: {r['is_correct']}")
