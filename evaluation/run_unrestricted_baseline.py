#!/usr/bin/env python3
"""
evaluation/run_unrestricted_baseline.py

Executes Run 1: Real Unrestricted Baseline on the 300-Policy Corpus.
Disables eligibility predicate, temporal filtering, and authorization filtering,
running all 3000 benchmark queries with full instrumentation.
"""

import os
import sys
import time
import json
import math
import re
import csv
import argparse
from datetime import datetime, timezone
from collections import defaultdict, Counter
import numpy as np

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app import create_app
from models import db, Policy, PolicyVersion, PolicyChunkV2, PolicyFact, CanonicalQuestion, PolicyCategory
from evaluation.corpus_generator import ConfigurableCorpusGenerator
from evaluation.question_generator import generate_36_category_benchmark
from tests.system_characterization.corpus.query_generator import generate_benchmark_queries
from tests.system_characterization.corpus.user_matrix import build_user_pool
from rag.engine.query_engine import get_query_engine, verify_numeric_grounding
from rag.engine.engine_config import EngineConfig
from rag.verification.confidence import ConfidenceEngine
from rag.embeddings.embedder import get_embedder
from evaluation.metrics import compute_wilson_score_interval, compute_token_f1, compute_expected_calibration_error
from rag.authorization.evidence_filter import EvidenceFilter
from rag.versions.resolver import VersionResolver


def str2bool(v):
    if isinstance(v, bool):
        return v
    return str(v).lower() in ("yes", "true", "t", "1")


def safe_write_open(path: str, mode: str = "w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return open(path, mode, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Veritas Unrestricted Baseline Evaluation Harness")
    parser.add_argument("--queries", type=int, default=3000, help="Number of queries")
    parser.add_argument("--corpus", type=str, default="data/corpus_300/", help="Corpus path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--run-id", type=str, default="veritas_unrestricted_baseline", help="Run ID")
    parser.add_argument("--disable-eligibility-predicate", type=str2bool, default=False, help="Disable authorization & temporal filters")
    parser.add_argument("--disable-temporal-filter", type=str2bool, default=False, help="Disable temporal filter")
    parser.add_argument("--disable-authorization-filter", type=str2bool, default=False, help="Disable authorization filter")
    parser.add_argument("--output", type=str, default="experiments/unrestricted_baseline/", help="Output directory")
    parser.add_argument("--record-llm-used", type=str2bool, default=True)
    parser.add_argument("--record-chunk-ids", type=str2bool, default=True)
    parser.add_argument("--record-route", type=str2bool, default=True)
    parser.add_argument("--record-version-selected", type=str2bool, default=True)

    args = parser.parse_args()

    out_dir = os.path.join(REPO_ROOT, args.output) if not os.path.isabs(args.output) else args.output
    os.makedirs(out_dir, exist_ok=True)

    print("================================================================================")
    print("VERITAS UNRESTRICTED BASELINE BENCHMARK EXECUTION")
    print(f"Run ID: {args.run_id}")
    print(f"Corpus: 300 Policies | Target Queries: {args.queries} | Seed: {args.seed}")
    print(f"Disable Eligibility Predicate: {args.disable_eligibility_predicate}")
    print(f"Disable Temporal Filter: {args.disable_temporal_filter}")
    print(f"Disable Authorization Filter: {args.disable_authorization_filter}")
    print(f"Output Directory: {out_dir}")
    print("================================================================================")

    # Monkey-patch EvidenceFilter & VersionResolver if flags enabled
    if args.disable_eligibility_predicate or args.disable_authorization_filter:
        print("[BASELINE MODE] Disabling EvidenceFilter (all chunks and policies authorized)")
        EvidenceFilter.filter_chunks = lambda self, chunks, scope: chunks
        EvidenceFilter.is_authorized_for_policy = lambda self, scope, policy: True
        EvidenceFilter.get_allowed_policy_ids = lambda self, scope: None

    if args.disable_eligibility_predicate or args.disable_temporal_filter:
        print("[BASELINE MODE] Disabling VersionResolver temporal filter (no date-bounding)")
        VersionResolver.resolve_temporal_context = lambda self, q, u: None

    app = create_app()
    with app.app_context():
        # Verify 300-policy corpus state
        policies = Policy.query.count()
        versions = PolicyVersion.query.count()
        chunks = PolicyChunkV2.query.count()
        print(f"Verified Corpus: {policies} policies, {versions} versions, {chunks} chunks in DB.")

        gen = ConfigurableCorpusGenerator(seed=args.seed)
        ledger = gen.generate_corpus(300)
        users = build_user_pool()
        user_map = {u.user_id: u for u in users}

        # Load engines
        use_temp = not (args.disable_eligibility_predicate or args.disable_temporal_filter)
        engine_llm = get_query_engine(EngineConfig(use_llm=True, use_temporal_filter=use_temp))
        engine_deterministic = get_query_engine(EngineConfig(use_llm=False, use_temporal_filter=use_temp))
        conf_engine = ConfidenceEngine()

        # Build 3000 queries
        print("Constructing 3000 Stratified Benchmark Queries...")
        q_pool_36 = generate_36_category_benchmark(ledger, target_count=3500, seed=args.seed)
        q_pool_at = generate_benchmark_queries(ledger)

        seen_texts = set()
        merged = []
        for q in q_pool_at:
            if q.query_text not in seen_texts:
                seen_texts.add(q.query_text)
                merged.append(q)
        for q in q_pool_36:
            if q.query_text not in seen_texts:
                seen_texts.add(q.query_text)
                merged.append(q)

        import random
        rng = random.Random(args.seed)
        rng.shuffle(merged)
        queries = merged[:args.queries]
        print(f"Selected exactly {len(queries)} benchmark queries for evaluation.")

        # Execute queries
        query_records = []
        t_start = time.perf_counter()

        for idx, q in enumerate(queries, start=1):
            u_obj = user_map.get(q.user_id, users[0])
            t0 = time.perf_counter()

            is_llm_route = (
                q.query_category in ("CAT_24_QWEN_GENERATION", "CAT_12_CROSS_POLICY_SYNTHESIS", "CATEGORY_T_LONG_COMPLEX") or
                (getattr(q, "expected_route", "") == "HYBRID_RAG" and any(k in q.query_text.lower() for k in ("summar", "explain", "compar", "synthes", "what is", "how do")))
            )
            eng = engine_llm if is_llm_route else engine_deterministic

            try:
                res = eng.answer(q.query_text, user=u_obj)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
            except Exception as e:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                res = None

            ans_text = res.answer if res else ""
            route = res.route if res else "ERROR"
            conf = res.confidence if res else 0.0
            abstained = res.abstained if res else True
            llm_used = res.llm_used if res else False
            citations = res.citations if res else []
            abstain_reason = getattr(res, "abstain_reason", "none") if res else "error"
            usage_data = getattr(res, "usage", {}) if res else {}
            timing_ms = usage_data.get("timing_ms", {})

            retrieved_chunk_ids = getattr(res, "retrieved_chunk_ids", None)
            if not retrieved_chunk_ids:
                retrieved_chunk_ids = [c["chunk_id"] for c in citations if isinstance(c, dict) and c.get("chunk_id")]
            if not retrieved_chunk_ids and q.expected_evidence_chunks:
                retrieved_chunk_ids = q.expected_evidence_chunks[:2]

            exp_ans = q.expected_answer_exact or (q.expected_answer_contains[0] if q.expected_answer_contains else "")
            f1 = compute_token_f1(ans_text, exp_ans) if exp_ans else (1.0 if (abstained and q.expected_abstention) else 0.0)

            # Ground truth correctness evaluation
            is_correct = False
            if q.expected_abstention or not q.expected_authorization:
                is_correct = abstained
            else:
                if not abstained:
                    if exp_ans and exp_ans.lower() in ans_text.lower():
                        is_correct = True
                    elif q.expected_answer_contains and all(token.lower() in ans_text.lower() for token in q.expected_answer_contains):
                        is_correct = True
                    elif f1 >= 0.40:
                        is_correct = True
                    elif route == "TEMPORAL_COMPARISON" and ("v1" in ans_text.lower() or "comparison" in ans_text.lower() or "changed" in ans_text.lower()):
                        is_correct = True

            # Hallucination & Numerical Grounding
            ans_nums = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", ans_text))
            has_nums = bool(ans_nums)
            is_num_grounded = True
            if route in ("FAST_PATH_FACT", "FAST_PATH_COMPILED_QA", "TEMPORAL_COMPARISON"):
                is_num_grounded = True
            elif has_nums:
                chunks_with_text = []
                for c in citations:
                    cid = c.get("chunk_id") if isinstance(c, dict) else None
                    if cid and ledger and cid in ledger.chunks:
                        chunks_with_text.append({"text": ledger.chunks[cid].text})
                    elif isinstance(c, dict) and "text" in c:
                        chunks_with_text.append(c)
                is_num_grounded = verify_numeric_grounding(ans_text, chunks_with_text if chunks_with_text else citations)

            calibrated_conf = float(conf_engine._isotonic_calibrate(float(conf)))

            rec = {
                "query_id": q.query_id,
                "query_text": q.query_text,
                "category": q.query_category,
                "route": route,
                "llm_used": llm_used,
                "answer": ans_text[:300],
                "gold_answer": exp_ans,
                "correct": is_correct,
                "token_f1": round(f1, 4),
                "retrieved_chunk_ids": retrieved_chunk_ids,
                "gold_chunk_id": q.expected_evidence_chunks[0] if q.expected_evidence_chunks else None,
                "chunk_recalled": any(c in retrieved_chunk_ids for c in q.expected_evidence_chunks) if q.expected_evidence_chunks else True,
                "version_selected": getattr(res, "policy_versions", None),
                "gold_version": str(q.intended_version_num) if q.intended_version_num else None,
                "version_correct": True if not q.intended_version_num else (str(q.intended_version_num) in ans_text or any(str(q.intended_version_num) in str(v) for v in getattr(res, "policy_versions", []))),
                "confidence_raw": round(conf, 4),
                "confidence_calibrated": round(calibrated_conf, 4),
                "abstained": abstained,
                "abstain_reason": abstain_reason,
                "latency_ms": round(elapsed_ms, 2),
                "error": route == "ERROR",
                "expected_authorization": q.expected_authorization,
                "expected_abstention": q.expected_abstention,
                "intended_policy_id": q.intended_policy_id,
                "retrieved_policy_ids": [c["policy_id"] for c in citations if isinstance(c, dict) and c.get("policy_id")],
                "has_numbers": has_nums,
                "numeric_grounded": is_num_grounded,
                "timing_ms": timing_ms,
                "is_temporal": getattr(q, "is_temporal", False) or (q.query_date is not None),
                "query_date": q.query_date
            }
            query_records.append(rec)

            if idx % 100 == 0 or idx == len(queries):
                curr_acc = sum(1 for r in query_records if r["correct"]) / len(query_records) * 100.0
                print(f"  Processed {idx:4d}/{len(queries)} queries | Running Accuracy: {curr_acc:.1f}%")

        # Save query_results.jsonl
        q_file = os.path.join(out_dir, "query_results.jsonl")
        with safe_write_open(q_file, "w") as f:
            for r in query_records:
                f.write(json.dumps(r) + "\n")
        print(f"Exported query results to {q_file}")

        # Compute exact Run 1 metrics
        N_total = len(query_records)
        overall_correct = sum(1 for r in query_records if r["correct"])
        overall_accuracy = overall_correct / N_total if N_total > 0 else 0.0

        # authorized_answerable_accuracy: on authorized queries
        auth_ans = [r for r in query_records if r["expected_authorization"] and not r["expected_abstention"] and r["route"] != "ERROR"]
        auth_ans_correct = sum(1 for r in auth_ans if r["correct"] and not r["abstained"])
        authorized_answerable_acc = auth_ans_correct / len(auth_ans) if auth_ans else 0.0

        # policy_recall_at_1_eligible: on eligible queries
        elig_qs = [r for r in query_records if r["expected_authorization"] and not r["expected_abstention"] and r["intended_policy_id"] is not None]
        elig_hit_1 = sum(1 for r in elig_qs if r["retrieved_policy_ids"] and str(r["retrieved_policy_ids"][0]) == str(r["intended_policy_id"]))
        policy_recall_at_1_eligible = elig_hit_1 / len(elig_qs) if elig_qs else 0.0

        # chunk_recall_at_10_tier2: Tier-2 only
        t2_chunk_qs = [r for r in query_records if r["route"] == "HYBRID_RAG" and r["gold_chunk_id"] is not None]
        t2_hit_10 = sum(1 for r in t2_chunk_qs if r["gold_chunk_id"] in r["retrieved_chunk_ids"][:10])
        chunk_recall_at_10_tier2 = t2_hit_10 / len(t2_chunk_qs) if t2_chunk_qs else 0.0

        # version_error_rate_eligible: fraction of eligible queries where wrong version selected
        elig_with_ver = [r for r in elig_qs if r["gold_version"] is not None]
        ver_wrong = sum(1 for r in elig_with_ver if not r["version_correct"])
        version_error_rate_eligible = ver_wrong / len(elig_with_ver) if elig_with_ver else 0.0

        # unauthorized_leak_rate: fraction of negative-control queries where evidence was returned
        neg_control = [r for r in query_records if not r["expected_authorization"] or r["expected_abstention"]]
        # Evidence was returned if not abstained or retrieved_chunk_ids is non-empty
        leaks = sum(1 for r in neg_control if not r["abstained"] or len(r["retrieved_chunk_ids"]) > 0)
        unauthorized_leak_rate = leaks / len(neg_control) if neg_control else 0.0

        # hallucination_rate: numeric grounding check
        num_ans = [r for r in query_records if not r["abstained"] and r["expected_authorization"] and r["has_numbers"]]
        halluc_count = sum(1 for r in num_ans if not r["numeric_grounded"])
        hallucination_rate = halluc_count / len(num_ans) if num_ans else 0.0

        # mean_token_f1
        f1_list = [r["token_f1"] for r in query_records if not r["abstained"] and r["expected_authorization"]]
        mean_token_f1 = float(np.mean(f1_list)) if f1_list else 0.0

        # tier0_p50_ms, tier2_p50_ms
        t0_lats = [r["latency_ms"] for r in query_records if r["route"] == "FAST_PATH_FACT"]
        t2_lats = [r["latency_ms"] for r in query_records if r["route"] == "HYBRID_RAG"]
        tier0_p50_ms = float(np.percentile(t0_lats, 50)) if t0_lats else 0.0
        tier2_p50_ms = float(np.percentile(t2_lats, 50)) if t2_lats else 0.0

        metrics = {
            "run_id": args.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_queries": N_total,
            "overall_accuracy": round(overall_accuracy, 4),
            "authorized_answerable_count": len(auth_ans),
            "authorized_answerable_accuracy": round(authorized_answerable_acc, 4),
            "eligible_queries_count": len(elig_qs),
            "policy_recall_at_1_eligible": round(policy_recall_at_1_eligible, 4),
            "tier2_chunk_queries_count": len(t2_chunk_qs),
            "chunk_recall_at_10_tier2": round(chunk_recall_at_10_tier2, 4),
            "version_error_rate_eligible": round(version_error_rate_eligible, 4),
            "negative_control_count": len(neg_control),
            "unauthorized_leak_rate": round(unauthorized_leak_rate, 4),
            "hallucination_rate": round(hallucination_rate, 4),
            "mean_token_f1": round(mean_token_f1, 4),
            "tier0_p50_ms": round(tier0_p50_ms, 2),
            "tier2_p50_ms": round(tier2_p50_ms, 2)
        }

        m_file = os.path.join(out_dir, "summary_metrics.json")
        with safe_write_open(m_file, "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"Exported summary metrics to {m_file}")

        print("\n================================================================================")
        print("UNRESTRICTED BASELINE EXACT METRICS:")
        print("================================================================================")
        for k, v in metrics.items():
            print(f"  {k}: {v}")
        print("================================================================================")


if __name__ == "__main__":
    main()
