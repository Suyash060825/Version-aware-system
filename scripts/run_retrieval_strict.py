"""
scripts/run_retrieval_strict.py
E6: Strict chunk-level retrieval metrics alongside policy-level metrics.
Computes:
  - Policy-Level Recall@k (current loose metric — any chunk from correct policy)
  - Chunk-Level Recall@k (strict — exact chunk_id match in gold_chunk_ids)
  - Precision@1, Precision@5 for all four retrievers
Reports both so the paper can correctly label the saturated 0.9861 as policy-level.
"""
import os
import sys
import csv
import json
import math
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import create_app
from models import Policy
from rag.retrieval.dense import DenseRetriever
from rag.retrieval.sparse import PersistentBM25Index
from rag.retrieval.hybrid import HybridRetriever
from rag.retrieval.reranker import get_reranker


def evaluate_hits_strict(hits, gold_chunk_ids, top_k=10):
    """Strict: exact chunk_id must appear in gold_chunk_ids."""
    if not gold_chunk_ids:
        return None
    gold_set = set()
    for gc in gold_chunk_ids:
        if isinstance(gc, str):
            # Sometimes gold_chunk_ids is a JSON string
            try:
                parsed = json.loads(gc)
                gold_set.update(parsed if isinstance(parsed, list) else [gc])
            except Exception:
                gold_set.add(gc)
        elif isinstance(gc, list):
            gold_set.update(gc)
        else:
            gold_set.add(str(gc))

    if not gold_set:
        return None

    hit_ranks = []
    for rank, h in enumerate(hits[:top_k], 1):
        cid = h.get("chunk_id") or h.get("id", "")
        if cid in gold_set:
            hit_ranks.append(rank)
            break

    if not hit_ranks:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    r = hit_ranks[0]
    # Precision@k: how many of the top-k are in gold
    hits_in_top1 = sum(1 for h in hits[:1] if (h.get("chunk_id") or h.get("id", "")) in gold_set)
    hits_in_top5 = sum(1 for h in hits[:5] if (h.get("chunk_id") or h.get("id", "")) in gold_set)
    p1 = hits_in_top1 / 1.0
    p5 = hits_in_top5 / 5.0
    r1 = 1.0 if r <= 1 else 0.0
    r5 = 1.0 if r <= 5 else 0.0
    r10 = 1.0 if r <= 10 else 0.0
    mrr = 1.0 / r
    ndcg = 1.0 / math.log2(r + 1)
    return r1, r5, r10, mrr, ndcg, p1, p5


def evaluate_hits_policy(hits, gold_policy, policy_map, top_k=10):
    """Policy-level: any chunk from the correct policy counts."""
    if not gold_policy:
        return None
    for rank, h in enumerate(hits[:top_k], 1):
        pid = h.get("policy_id")
        title = policy_map.get(pid, h.get("policy_name", ""))
        if gold_policy.lower() in title.lower() or any(
                w in title.lower() for w in gold_policy.lower().split() if len(w) > 4):
            r = rank
            r1 = 1.0 if r <= 1 else 0.0
            r5 = 1.0 if r <= 5 else 0.0
            r10 = 1.0 if r <= 10 else 0.0
            mrr = 1.0 / r
            ndcg = 1.0 / math.log2(r + 1)
            # Precision@k not well-defined for policy-level in this corpus
            return r1, r5, r10, mrr, ndcg, r1, r5
    return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0


def run_retrieval_strict():
    app = create_app("development")
    os.makedirs("results", exist_ok=True)

    with app.app_context():
        policy_map = {p.id: p.title for p in Policy.query.all()}

        dense = DenseRetriever()
        sparse = PersistentBM25Index()
        sparse.rebuild_from_db()
        reranker = get_reranker()

        with open("data/benchmarks/benchmark_test.json") as f:
            test_cases = json.load(f)

        # Filter: only cases with both gold_chunk_ids AND ground_truth_policy
        strict_cases = [tc for tc in test_cases if tc.get("gold_chunk_ids") and tc.get("ground_truth_policy")]
        policy_cases = [tc for tc in test_cases if tc.get("ground_truth_policy")]

        print(f"[Strict Retrieval] Cases with chunk IDs: {len(strict_cases)} | Policy-level: {len(policy_cases)}")

        retrievers = ["Dense (BGE-Small)", "BM25 (Sparse)", "Hybrid RRF", "Hybrid + FlashRank (Ours)"]
        strict_stats = {m: {"r1": [], "r5": [], "r10": [], "mrr": [], "ndcg": [], "p1": [], "p5": []} for m in retrievers}
        policy_stats = {m: {"r1": [], "r5": [], "r10": [], "mrr": [], "ndcg": []} for m in retrievers}

        for i, tc in enumerate(policy_cases):
            if i % 50 == 0:
                print(f"  Processing {i}/{len(policy_cases)}...")
            q = tc["query"]
            gold_cids = tc.get("gold_chunk_ids", [])
            gt_policy = tc.get("ground_truth_policy", "")

            hyb = HybridRetriever()

            d_hits = dense.search(q, top_k=20)
            b_raw = sparse.get_scores(q)
            b_hits = [c[2] for c in b_raw[:20]]
            hyb_hits = hyb.search(q, top_k=20)
            rank_hits = reranker.rank(q, hyb_hits, top_k=10)

            all_hits = {
                "Dense (BGE-Small)": d_hits,
                "BM25 (Sparse)": b_hits,
                "Hybrid RRF": hyb_hits,
                "Hybrid + FlashRank (Ours)": rank_hits,
            }

            for model, hits in all_hits.items():
                # Strict eval (only for cases with chunk IDs)
                if gold_cids and tc in strict_cases:
                    res = evaluate_hits_strict(hits, gold_cids)
                    if res is not None:
                        r1, r5, r10, mrr, ndcg, p1, p5 = res
                        strict_stats[model]["r1"].append(r1)
                        strict_stats[model]["r5"].append(r5)
                        strict_stats[model]["r10"].append(r10)
                        strict_stats[model]["mrr"].append(mrr)
                        strict_stats[model]["ndcg"].append(ndcg)
                        strict_stats[model]["p1"].append(p1)
                        strict_stats[model]["p5"].append(p5)

                # Policy-level eval
                res_p = evaluate_hits_policy(hits, gt_policy, policy_map)
                if res_p is not None:
                    r1, r5, r10, mrr, ndcg, _, _ = res_p
                    policy_stats[model]["r1"].append(r1)
                    policy_stats[model]["r5"].append(r5)
                    policy_stats[model]["r10"].append(r10)
                    policy_stats[model]["mrr"].append(mrr)
                    policy_stats[model]["ndcg"].append(ndcg)

        with open("results/retrieval_metrics_strict.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Retriever", "Eval Level",
                "R@1", "R@5", "R@10", "MRR@10", "NDCG@10",
                "P@1", "P@5", "N Queries"
            ])
            for model in retrievers:
                # Policy-level row
                p_r1 = round(float(np.mean(policy_stats[model]["r1"])), 4) if policy_stats[model]["r1"] else "-"
                p_r5 = round(float(np.mean(policy_stats[model]["r5"])), 4) if policy_stats[model]["r5"] else "-"
                p_r10 = round(float(np.mean(policy_stats[model]["r10"])), 4) if policy_stats[model]["r10"] else "-"
                p_mrr = round(float(np.mean(policy_stats[model]["mrr"])), 4) if policy_stats[model]["mrr"] else "-"
                p_ndcg = round(float(np.mean(policy_stats[model]["ndcg"])), 4) if policy_stats[model]["ndcg"] else "-"
                writer.writerow([model, "Policy-Level", p_r1, p_r5, p_r10, p_mrr, p_ndcg, "—", "—", len(policy_stats[model]["r1"])])

                # Strict chunk-level row
                if strict_stats[model]["r1"]:
                    s_r1 = round(float(np.mean(strict_stats[model]["r1"])), 4)
                    s_r5 = round(float(np.mean(strict_stats[model]["r5"])), 4)
                    s_r10 = round(float(np.mean(strict_stats[model]["r10"])), 4)
                    s_mrr = round(float(np.mean(strict_stats[model]["mrr"])), 4)
                    s_ndcg = round(float(np.mean(strict_stats[model]["ndcg"])), 4)
                    s_p1 = round(float(np.mean(strict_stats[model]["p1"])), 4)
                    s_p5 = round(float(np.mean(strict_stats[model]["p5"])), 4)
                    writer.writerow([model, "Chunk-Level (Strict)", s_r1, s_r5, s_r10, s_mrr, s_ndcg, s_p1, s_p5, len(strict_stats[model]["r1"])])
                else:
                    writer.writerow([model, "Chunk-Level (Strict)", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", 0])

        print(f"\n[Strict Retrieval] Results saved → results/retrieval_metrics_strict.csv")


if __name__ == "__main__":
    run_retrieval_strict()
