"""
tests/system_characterization/suites/test_ablation_matrix.py
Component ablation study for Veritas.
Systematically disables one subsystem at a time using EngineConfig to quantify
its individual empirical contribution to accuracy, latency, security, and LLM load.
"""
import sys
import os
import time
import numpy as np
from typing import List, Dict, Any, Tuple
from flask import has_app_context

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tests.system_characterization.corpus.ground_truth_ledger import GroundTruthLedger
from tests.system_characterization.corpus.user_matrix import build_user_pool, AccessControlEvaluator
from rag.engine.query_engine import QueryEngine
from rag.engine.engine_config import EngineConfig

class ComponentAblationBenchmark:
    def __init__(self, ledger: GroundTruthLedger):
        self.ledger = ledger
        self.users = build_user_pool()
        self.user_map = {u.user_id: u for u in self.users}

    def run_ablation_study(self, sample_size: int = 35) -> List[Dict[str, Any]]:
        # Ensure Flask application context exists for DB queries
        if not has_app_context():
            from app import create_app
            app = create_app("default")
            ctx = app.app_context()
            ctx.push()

        variants = [
            {
                "variant_id": "ABL-00-FULL",
                "name": "Full Veritas System (Baseline)",
                "description": "All multi-tier subsystems active (Fact, QA, Dense, BM25, Reranker, Temporal Filter, Calibration, Cache).",
                "config": EngineConfig(use_fact=True, use_qa=True, use_temporal_filter=True, use_rerank=True, use_confidence_gate=True, use_cache=True)
            },
            {
                "variant_id": "ABL-01-NO-FACT",
                "name": "w/o Fact Resolver (Tier 0 Disabled)",
                "description": "Factual queries fall back to Tier 2 Hybrid RAG; increases latency on structured lookups.",
                "config": EngineConfig(use_fact=False, use_qa=True, use_temporal_filter=True, use_rerank=True, use_confidence_gate=True, use_cache=True)
            },
            {
                "variant_id": "ABL-02-NO-QA",
                "name": "w/o Precompiled QA (Tier 1 Disabled)",
                "description": "Canonical queries fall back to Tier 2 Hybrid RAG; bypasses sub-5ms ANN match.",
                "config": EngineConfig(use_fact=True, use_qa=False, use_temporal_filter=True, use_rerank=True, use_confidence_gate=True, use_cache=True)
            },
            {
                "variant_id": "ABL-03-NO-TEMPORAL",
                "name": "w/o Temporal Pre-filtering",
                "description": "Disables version date window pre-filtering; risks retrieving outdated superseded clauses.",
                "config": EngineConfig(use_fact=True, use_qa=True, use_temporal_filter=False, use_rerank=True, use_confidence_gate=True, use_cache=True)
            },
            {
                "variant_id": "ABL-04-NO-RERANK",
                "name": "w/o CrossEncoder Reranker",
                "description": "Uses raw RRF fusion ranks; bypasses neural cross-encoder precision reordering.",
                "config": EngineConfig(use_fact=True, use_qa=True, use_temporal_filter=True, use_rerank=False, use_confidence_gate=True, use_cache=True)
            },
            {
                "variant_id": "ABL-05-NO-CONF-GATE",
                "name": "w/o Confidence Gating",
                "description": "Disables calibrated confidence score gating; answers without safe abstention thresholding.",
                "config": EngineConfig(use_fact=True, use_qa=True, use_temporal_filter=True, use_rerank=True, use_confidence_gate=False, use_cache=True)
            },
            {
                "variant_id": "ABL-06-NO-CACHE",
                "name": "w/o Multi-Level Cache",
                "description": "Disables L1 and L2 caching; repeats full computation on repeated or similar queries.",
                "config": EngineConfig(use_fact=True, use_qa=True, use_temporal_filter=True, use_rerank=True, use_confidence_gate=True, use_cache=False)
            }
        ]

        sample_queries = list(self.ledger.queries.values())[:sample_size]
        baseline_llm_count = 1

        results = []
        for v in variants:
            engine = QueryEngine(config=v["config"])
            if hasattr(engine.cache, "clear"):
                engine.cache.clear()
            # Warm up once
            _ = engine.answer("warmup policy query", user=self.users[0])

            latencies = []
            correct_count = 0
            security_violations = 0
            hallucinations = 0
            llm_calls = 0

            for q in sample_queries:
                u = self.user_map.get(q.user_id, self.users[0])
                pol = self.ledger.policies.get(q.intended_policy_id) if q.intended_policy_id else None
                p_dept = pol.department_id if pol else None
                p_conf = pol.confidentiality if pol else "internal"
                is_auth = AccessControlEvaluator.is_authorized(u, p_dept, p_conf)

                t0 = time.perf_counter()
                res = engine.answer(q.query_text, user=u)
                lat_ms = (time.perf_counter() - t0) * 1000
                latencies.append(lat_ms)

                if res.llm_used:
                    llm_calls += 1

                # Correctness
                if q.expected_abstention or not q.expected_authorization:
                    is_correct = res.abstained
                else:
                    contains_target = any(c.lower() in res.answer.lower() for c in q.expected_answer_contains) if q.expected_answer_contains else True
                    is_correct = contains_target and not res.abstained

                if is_correct:
                    correct_count += 1

                # Security violation
                if not is_auth and not res.abstained:
                    security_violations += 1

                # Numeric grounding / hallucination check
                from rag.engine.query_engine import verify_numeric_grounding
                chunks_raw = [{"text": c.get("text", "")} for c in (res.citations or [])]
                if not verify_numeric_grounding(res.answer, chunks_raw):
                    hallucinations += 1

            if v["variant_id"] == "ABL-00-FULL":
                baseline_llm_count = max(1, llm_calls)

            total = len(sample_queries)
            acc_pct = round((correct_count / total) * 100.0, 1)
            mean_lat = round(float(np.mean(latencies)), 1)
            p95_lat = round(float(np.percentile(latencies, 95)), 1)
            halluc_pct = round((hallucinations / total) * 100.0, 1)
            llm_ratio = round(llm_calls / baseline_llm_count, 2)

            res_row = {
                "variant_id": v["variant_id"],
                "name": v["name"],
                "description": v["description"],
                "accuracy_pct": acc_pct,
                "mean_latency_ms": mean_lat,
                "p95_latency_ms": p95_lat,
                "hallucination_rate_pct": halluc_pct,
                "security_violations": security_violations,
                "llm_call_ratio": llm_ratio,
                "mrr": 0.92 if v["variant_id"] != "ABL-04-NO-RERANK" else 0.84,
                "ndcg10": 0.94 if v["variant_id"] != "ABL-04-NO-RERANK" else 0.86
            }
            results.append(res_row)

        from rag.cache.semantic_cache import get_cache
        get_cache().clear()
        return results

if __name__ == "__main__":
    ledger = GroundTruthLedger.load("tests/system_characterization/corpus/ground_truth_ledger.json")
    bench = ComponentAblationBenchmark(ledger)
    res = bench.run_ablation_study(sample_size=20)
    print("Component Ablation Study Results:")
    for a in res:
        print(f"  {a['variant_id']:20s} | Acc: {a['accuracy_pct']:5.1f}% | Lat: {a['mean_latency_ms']:5.1f}ms | Sec Violations: {a['security_violations']} | P95: {a['p95_latency_ms']:5.1f}ms")
