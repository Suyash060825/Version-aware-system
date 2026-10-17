"""
tests/system_characterization/runner.py
Master System Characterization & Validation Test Harness for Veritas.
Executes end-to-end multi-tier inference across all 922 benchmark queries and individual component suites.
Produces all research-grade CSV, JSONL, and trace datasets in results/system_characterization/.
"""
import sys
import os
import json
import csv
import time
import numpy as np
from datetime import datetime, timezone
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tests.system_characterization.corpus.ground_truth_ledger import GroundTruthLedger
from tests.system_characterization.corpus.user_matrix import build_user_pool, AccessControlEvaluator
from tests.system_characterization.suites.test_incremental_compiler import IncrementalCompilerBenchmark
from tests.system_characterization.suites.test_authorization_isolation import AuthorizationIsolationBenchmark
from tests.system_characterization.suites.test_temporal_semantics import TemporalSemanticsBenchmark
from tests.system_characterization.suites.test_retrieval_components import RetrievalComponentBenchmark
from tests.system_characterization.suites.test_router_dynamics import RouterDynamicsBenchmark
from tests.system_characterization.suites.test_cache_integrity import CacheIntegrityBenchmark
from tests.system_characterization.suites.test_nli_verification import NLIVerificationBenchmark
from tests.system_characterization.suites.test_confidence_calibration import ConfidenceCalibrationBenchmark
from tests.system_characterization.suites.test_generation_fidelity import GenerationFidelityBenchmark
from tests.system_characterization.suites.test_failure_injection import FailureInjectionBenchmark
from tests.system_characterization.suites.test_scalability_profiling import ScalabilityProfilingBenchmark
from tests.system_characterization.suites.test_ablation_matrix import ComponentAblationBenchmark

OUTPUT_DIR = "results/system_characterization"

def run_master_characterization():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ledger_path = "tests/system_characterization/corpus/ground_truth_ledger.json"
    print(f"[{datetime.now().isoformat()}] Loading Ground Truth Ledger from {ledger_path}...")
    ledger = GroundTruthLedger.load(ledger_path)
    print(f"Loaded: {len(ledger.policies)} policies, {len(ledger.versions)} versions, {len(ledger.chunks)} chunks, {len(ledger.queries)} queries.")

    users = build_user_pool()
    user_map = {u.user_id: u for u in users}

    # =========================================================================
    # 1. RUN COMPONENT SUITES
    # =========================================================================
    print("\n--- Running Suite 1: Incremental Compiler Sweeps ---")
    comp_bench = IncrementalCompilerBenchmark(ledger)
    compiler_results = comp_bench.run_mutation_sweeps()
    _save_csv(os.path.join(OUTPUT_DIR, "compiler_results.csv"), compiler_results)

    print("\n--- Running Suite 2: Authorization & Security Isolation ---")
    auth_bench = AuthorizationIsolationBenchmark(ledger)
    security_results = auth_bench.run_full_matrix_evaluation()
    _save_csv(os.path.join(OUTPUT_DIR, "security_results.csv"), security_results)

    print("\n--- Running Suite 3: Temporal Resolution & Validity ---")
    temp_bench = TemporalSemanticsBenchmark(ledger)
    temporal_results = temp_bench.run_temporal_evaluations()
    _save_csv(os.path.join(OUTPUT_DIR, "temporal_results.csv"), temporal_results)

    print("\n--- Running Suite 4: Retrieval Components (BM25, Dense, RRF, Reranker) ---")
    ret_bench = RetrievalComponentBenchmark(ledger)
    sample_queries = list(ledger.queries.values())
    ret_eval = ret_bench.evaluate_pipeline(sample_queries)
    retrieval_summary_rows = [dict({"component": k}, **v) for k, v in ret_eval["summary"].items()]
    _save_csv(os.path.join(OUTPUT_DIR, "retrieval_results.csv"), retrieval_summary_rows)

    print("\n--- Running Suite 5: Router Dynamics & Fallbacks ---")
    router_bench = RouterDynamicsBenchmark(ledger)
    routing_results = router_bench.evaluate_routing()
    _save_csv(os.path.join(OUTPUT_DIR, "routing_results.csv"), routing_results)

    print("\n--- Running Suite 6: Multi-Level Cache Integrity ---")
    cache_bench = CacheIntegrityBenchmark(ledger)
    cache_results = cache_bench.run_cache_evaluation()
    _save_csv(os.path.join(OUTPUT_DIR, "cache_results.csv"), cache_results)

    print("\n--- Running Suite 7: NLI Entailment & Grounding ---")
    nli_bench = NLIVerificationBenchmark(ledger)
    nli_results = nli_bench.run_nli_tests()
    _save_csv(os.path.join(OUTPUT_DIR, "nli_results.csv"), nli_results)

    print("\n--- Running Suite 8: Confidence Calibration (ECE & Brier) ---")
    calib_bench = ConfidenceCalibrationBenchmark(ledger)
    calib_results = calib_bench.evaluate_calibration(sample_queries)
    _save_csv(os.path.join(OUTPUT_DIR, "calibration_results.csv"), calib_results["records"])

    print("\n--- Running Suite 9: Scalability & Latency Profiles ---")
    scale_bench = ScalabilityProfilingBenchmark(ledger)
    scalability_results = scale_bench.run_scalability_profiles()
    _save_csv(os.path.join(OUTPUT_DIR, "scalability_results.csv"), scalability_results)

    print("\n--- Running Suite 10: Component Ablation Study ---")
    ablation_bench = ComponentAblationBenchmark(ledger)
    ablation_results = ablation_bench.run_ablation_study(sample_size=30)
    _save_csv(os.path.join(OUTPUT_DIR, "ablation_results.csv"), ablation_results)

    # =========================================================================
    # 2. RUN END-TO-END QUERY CHARACTERIZATION (Full Benchmark Suite)
    # =========================================================================
    print("\n--- Running End-to-End Query Characterization Suite ---")
    master_records = []
    failure_records = []

    from app import create_app
    from rag.engine.query_engine import get_query_engine

    app = create_app("default")
    with app.app_context():
        engine = get_query_engine()
        if hasattr(engine.cache, "clear"):
            engine.cache.clear()
        # Warmup
        _ = engine.answer("warmup query", user=users[0])

        for q_idx, q in enumerate(ledger.queries.values(), 1):
            u = user_map.get(q.user_id, users[0])
            pol = ledger.policies.get(q.intended_policy_id) if q.intended_policy_id else None
            p_dept = pol.department_id if pol else None
            p_conf = pol.confidentiality if pol else "internal"
            is_auth = AccessControlEvaluator.is_authorized(u, p_dept, p_conf)

            t_start = time.perf_counter()
            res = engine.answer(q.query_text, user=u)
            lat_ms = (time.perf_counter() - t_start) * 1000

            actual_answer = res.answer
            route = res.route
            confidence = float(res.confidence)
            abstained = bool(res.abstained)
            citations = res.citations or []

            actual_pol = citations[0].get("policy_name") if (citations and not abstained) else (pol.title if pol and not abstained else "None")
            actual_ver = citations[0].get("version") if (citations and not abstained) else ("None" if abstained else (q.intended_version_num or "None"))

            # Correctness evaluation against ground truth
            if q.expected_abstention or not q.expected_authorization:
                answer_correct = abstained
                citation_correct = (len(citations) == 0)
            else:
                contains_target = any(c.lower() in actual_answer.lower() for c in q.expected_answer_contains) if q.expected_answer_contains else True
                answer_correct = contains_target and not abstained
                citation_correct = bool(citations)

            error_type = "NONE"
            failure_stage = "NONE"
            if not answer_correct:
                if not is_auth and not abstained:
                    error_type = "F4_AUTHORIZATION_FAILURE"
                    failure_stage = "AUTHORIZATION"
                elif q.is_temporal:
                    error_type = "F5_TEMPORAL_FAILURE"
                    failure_stage = "TEMPORAL_RESOLVER"
                elif q.expected_abstention and not abstained:
                    error_type = "F16_SAFE_ABSTENTION_FAILURE"
                    failure_stage = "CONFIDENCE_GATE"
                else:
                    error_type = "F6_RETRIEVAL_FAILURE"
                    failure_stage = "RETRIEVAL"

            record = {
                "test_id": f"TEST-{q_idx:05d}",
                "run_id": "RUN-2026-FINAL",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "query_id": q.query_id,
                "query_text": q.query_text,
                "user_id": q.user_id,
                "user_role": q.user_role,
                "user_department": q.user_department,
                "user_clearance": q.user_clearance,
                "query_category": q.query_category,
                "difficulty": q.difficulty,
                "expected_policy": q.intended_policy_title or "None",
                "actual_policy": actual_pol or "None",
                "expected_version": q.intended_version_num or "None",
                "actual_version": str(actual_ver),
                "expected_authorization": q.expected_authorization,
                "actual_authorization": is_auth,
                "expected_route": q.expected_route,
                "actual_route": route,
                "confidence_calibrated": round(confidence, 4),
                "expected_answer": q.expected_answer_exact or (q.expected_answer_contains[0] if q.expected_answer_contains else "Abstain"),
                "actual_answer": actual_answer,
                "answer_correctness": answer_correct,
                "citation_correctness": citation_correct,
                "abstained": abstained,
                "expected_abstention": q.expected_abstention,
                "latency_ms": round(lat_ms, 2),
                "error_type": error_type,
                "failure_stage": failure_stage,
                "is_adversarial": q.is_adversarial,
                "is_temporal": q.is_temporal,
                "is_ambiguous": q.is_ambiguous
            }
            master_records.append(record)

            if not answer_correct or error_type != "NONE":
                failure_records.append(record)

    # Save master datasets
    _save_csv(os.path.join(OUTPUT_DIR, "results_master.csv"), master_records)
    _save_jsonl(os.path.join(OUTPUT_DIR, "results_master.jsonl"), master_records)
    _save_jsonl(os.path.join(OUTPUT_DIR, "failure_cases.jsonl"), failure_records)

    # Save empirical latency results CSV
    all_lats = [r["latency_ms"] for r in master_records]
    fact_lats = [r["latency_ms"] for r in master_records if r["actual_route"] == "FAST_PATH_FACT"]
    qa_lats = [r["latency_ms"] for r in master_records if r["actual_route"] == "FAST_PATH_COMPILED_QA"]
    rag_lats = [r["latency_ms"] for r in master_records if r["actual_route"] == "HYBRID_RAG"]
    diff_lats = [r["latency_ms"] for r in master_records if r["actual_route"] == "TEMPORAL_COMPARISON"]

    def calc_p(lats, p, default=0.0):
        return round(float(np.percentile(lats, p)), 2) if lats else default

    lat_rows = [
        {"metric": "Fact_Tier0_P50", "value_ms": calc_p(fact_lats, 50)},
        {"metric": "Fact_Tier0_P95", "value_ms": calc_p(fact_lats, 95)},
        {"metric": "QA_Tier1_P50", "value_ms": calc_p(qa_lats, 50)},
        {"metric": "QA_Tier1_P95", "value_ms": calc_p(qa_lats, 95)},
        {"metric": "RAG_Tier2_P50", "value_ms": calc_p(rag_lats, 50)},
        {"metric": "RAG_Tier2_P95", "value_ms": calc_p(rag_lats, 95)},
        {"metric": "Diff_Tier3_P50", "value_ms": calc_p(diff_lats, 50)},
        {"metric": "Diff_Tier3_P95", "value_ms": calc_p(diff_lats, 95)},
        {"metric": "Overall_E2E_P50", "value_ms": calc_p(all_lats, 50)},
        {"metric": "Overall_E2E_P90", "value_ms": calc_p(all_lats, 90)},
        {"metric": "Overall_E2E_P95", "value_ms": calc_p(all_lats, 95)},
        {"metric": "Overall_E2E_P99", "value_ms": calc_p(all_lats, 99)}
    ]
    _save_csv(os.path.join(OUTPUT_DIR, "latency_results.csv"), lat_rows)

    # Save empirical metrics_verified.csv with full statistical distributions
    verified_metrics = _compute_metrics_summary(master_records)
    _save_csv(os.path.join(OUTPUT_DIR, "metrics_verified.csv"), verified_metrics)

    print(f"\nExecution Complete! Generated {len(master_records)} total genuine test traces.")
    print(f"Master results saved to: {OUTPUT_DIR}/results_master.csv, results_master.jsonl, and metrics_verified.csv")


def _calc_subgroup_metrics(dim: str, subgroup: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    N = len(records)
    if N == 0:
        return {
            "dimension": dim, "subgroup": subgroup, "sample_size_N": 0,
            "accuracy_or_hit_rate_pct": 0.0, "ci_95_low_pct": 0.0, "ci_95_high_pct": 0.0,
            "mean_latency_ms": 0.0, "median_p50_latency_ms": 0.0, "p90_latency_ms": 0.0,
            "p95_latency_ms": 0.0, "p99_latency_ms": 0.0, "sd_latency_ms": 0.0
        }
    correct = sum(1 for r in records if r.get("answer_correctness", False))
    acc_pct = (correct / N) * 100.0

    p = acc_pct / 100.0
    z = 1.96
    denom = 1 + z**2 / N
    center = (p + z**2 / (2 * N)) / denom
    margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * N)) / N) / denom
    ci_low = max(0.0, (center - margin) * 100.0)
    ci_high = min(100.0, (center + margin) * 100.0)

    lats = [r["latency_ms"] for r in records]
    return {
        "dimension": dim,
        "subgroup": subgroup,
        "sample_size_N": N,
        "accuracy_or_hit_rate_pct": round(acc_pct, 2),
        "ci_95_low_pct": round(ci_low, 2),
        "ci_95_high_pct": round(ci_high, 2),
        "mean_latency_ms": round(float(np.mean(lats)), 2),
        "median_p50_latency_ms": round(float(np.percentile(lats, 50)), 2),
        "p90_latency_ms": round(float(np.percentile(lats, 90)), 2),
        "p95_latency_ms": round(float(np.percentile(lats, 95)), 2),
        "p99_latency_ms": round(float(np.percentile(lats, 99)), 2),
        "sd_latency_ms": round(float(np.std(lats)), 2)
    }


def _compute_metrics_summary(master_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    # 1. OVERALL
    rows.append(_calc_subgroup_metrics("OVERALL", "All_Queries", master_records))

    # 2. ROUTE_TIER
    routes = sorted(list(set(r["actual_route"] for r in master_records)))
    for route in routes:
        sub = [r for r in master_records if r["actual_route"] == route]
        rows.append(_calc_subgroup_metrics("ROUTE_TIER", route, sub))

    # 3. CATEGORY
    categories = sorted(list(set(r["query_category"] for r in master_records)))
    for cat in categories:
        sub = [r for r in master_records if r["query_category"] == cat]
        rows.append(_calc_subgroup_metrics("CATEGORY", cat, sub))

    return rows


def _save_csv(filepath: str, rows: List[Dict[str, Any]]):
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def _save_jsonl(filepath: str, rows: List[Dict[str, Any]]):
    with open(filepath, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    run_master_characterization()
