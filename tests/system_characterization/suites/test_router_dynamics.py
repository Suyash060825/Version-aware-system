"""
tests/system_characterization/suites/test_router_dynamics.py
Evaluation of Veritas Multi-Tier Query Router and Intent/Complexity Classifiers.
Tests route selection accuracy, confidence calibration, boundary conditions, and fallback transitions.
"""
import sys
import os
import time
from typing import List, Dict, Any, Tuple
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from rag.router.query_router import QueryRouter
from rag.router.intent_classifier import Intent
from rag.router.complexity_classifier import ComplexityLevel
from tests.system_characterization.corpus.ground_truth_ledger import GroundTruthLedger

class RouterDynamicsBenchmark:
    def __init__(self, ledger: GroundTruthLedger):
        self.ledger = ledger
        self.router = QueryRouter()

    def evaluate_routing(self) -> List[Dict[str, Any]]:
        results = []
        queries = list(self.ledger.queries.values())

        for q in queries:
            t0 = time.time()
            intent, complexity, route_name, meta = self.router.route(q.query_text)
            routing_latency_us = (time.time() - t0) * 1_000_000

            # Route mapping to expected route categories
            expected_route = q.expected_route
            route_match = (route_name == expected_route) or (expected_route in ("FAST_PATH_FACT", "FAST_PATH_COMPILED_QA") and route_name in ("FAST_PATH_FACT", "FAST_PATH_COMPILED_QA"))

            res_entry = {
                "query_id": q.query_id,
                "query_text": q.query_text,
                "query_category": q.query_category,
                "expected_route": expected_route,
                "actual_route": route_name,
                "actual_intent": intent.value if hasattr(intent, "value") else str(intent),
                "actual_complexity": int(complexity),
                "intent_confidence": meta.get("intent_confidence", 0.0),
                "route_match": route_match,
                "latency_us": routing_latency_us,
                "is_adversarial": q.is_adversarial,
                "is_ambiguous": q.is_ambiguous
            }
            results.append(res_entry)

        return results

if __name__ == "__main__":
    ledger = GroundTruthLedger.load("tests/system_characterization/corpus/ground_truth_ledger.json")
    bench = RouterDynamicsBenchmark(ledger)
    res = bench.evaluate_routing()
    correct = sum(1 for r in res if r["route_match"])
    print(f"Router Evaluation: {len(res)} queries. Match: {correct}/{len(res)} ({correct/len(res)*100:.2f}%).")
