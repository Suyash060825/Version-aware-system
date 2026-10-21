"""
evaluation/metrics.py
Rigorous evaluation metric calculations for Veritas.
Calculates Policy/Chunk Recall, MRR, Answer Accuracy, Token F1,
Citation Precision/Recall, ECE, and Wilson 95% Confidence Intervals.
"""

import math
import re
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from collections import defaultdict


def compute_wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    z = 1.95996  # 95% confidence
    p = successes / total
    denom = 1 + (z**2 / total)
    center = (p + (z**2 / (2 * total))) / denom
    margin = (z * math.sqrt((p * (1 - p) / total) + (z**2 / (4 * total**2)))) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def compute_token_f1(prediction: str, reference: str) -> float:
    """Computes standard SQuAD-style Token F1 between prediction and reference."""
    pred_tokens = re.findall(r"\w+", (prediction or "").lower())
    ref_tokens = re.findall(r"\w+", (reference or "").lower())

    if not pred_tokens or not ref_tokens:
        return 1.0 if pred_tokens == ref_tokens else 0.0

    common = defaultdict(int)
    for t in pred_tokens:
        common[t] += 1
    
    num_same = 0
    ref_counts = defaultdict(int)
    for t in ref_tokens:
        ref_counts[t] += 1

    for t, cnt in ref_counts.items():
        if t in common:
            num_same += min(cnt, common[t])

    if num_same == 0:
        return 0.0

    precision = num_same / len(pred_tokens)
    recall = num_same / len(ref_tokens)
    return 2 * (precision * recall) / (precision + recall)


def compute_expected_calibration_error(confidences: List[float], correctness: List[bool], num_bins: int = 10) -> Dict[str, Any]:
    """Calculates ECE with uniform binning [0, 0.1, ..., 1.0]."""
    if not confidences or len(confidences) != len(correctness):
        return {"ece": 0.0, "bins": []}

    conf_arr = np.array(confidences)
    corr_arr = np.array(correctness, dtype=float)
    total_n = len(conf_arr)

    bin_boundaries = np.linspace(0, 1, num_bins + 1)
    ece = 0.0
    bin_details = []

    for i in range(num_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]

        in_bin = (conf_arr > bin_lower) & (conf_arr <= bin_upper) if i > 0 else (conf_arr >= bin_lower) & (conf_arr <= bin_upper)
        bin_count = np.sum(in_bin)

        if bin_count > 0:
            bin_acc = np.mean(corr_arr[in_bin])
            bin_conf = np.mean(conf_arr[in_bin])
            abs_diff = abs(bin_acc - bin_conf)
            ece += (bin_count / total_n) * abs_diff
            bin_details.append({
                "bin_idx": i,
                "range": [float(bin_lower), float(bin_upper)],
                "count": int(bin_count),
                "accuracy": float(bin_acc),
                "confidence": float(bin_conf),
                "diff": float(abs_diff)
            })

    return {
        "ece": float(ece),
        "num_bins": num_bins,
        "total_samples": total_n,
        "bins": bin_details
    }


def compute_retrieval_metrics(retrieval_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes Policy Recall@1, 5, 10; Chunk Recall@1, 5, 10; and MRR.
    """
    total = len(retrieval_records)
    if total == 0:
        return {}

    pol_r1 = 0
    pol_r5 = 0
    pol_r10 = 0

    chk_r1 = 0
    chk_r5 = 0
    chk_r10 = 0

    reciprocal_ranks = []

    for r in retrieval_records:
        exp_pid = r.get("expected_policy_id")
        exp_cids = set(r.get("expected_chunk_ids", []))

        retrieved_pids = r.get("retrieved_policy_ids", [])
        retrieved_cids = r.get("retrieved_chunk_ids", [])

        # Policy Recall
        if exp_pid is not None:
            if retrieved_pids and retrieved_pids[0] == exp_pid:
                pol_r1 += 1
            if exp_pid in retrieved_pids[:5]:
                pol_r5 += 1
            if exp_pid in retrieved_pids[:10]:
                pol_r10 += 1

        # Chunk Recall & MRR
        if exp_cids:
            first_rank = None
            for idx, cid in enumerate(retrieved_cids, start=1):
                if cid in exp_cids:
                    if first_rank is None:
                        first_rank = idx
                    if idx == 1:
                        chk_r1 += 1
                    if idx <= 5:
                        chk_r5 += 1
                    if idx <= 10:
                        chk_r10 += 1
                    break
            if first_rank:
                reciprocal_ranks.append(1.0 / first_rank)
            else:
                reciprocal_ranks.append(0.0)

    mrr = float(np.mean(reciprocal_ranks)) if reciprocal_ranks else 0.0

    return {
        "total_queries": total,
        "policy_recall_at_1": float(pol_r1 / total),
        "policy_recall_at_5": float(pol_r5 / total),
        "policy_recall_at_10": float(pol_r10 / total),
        "chunk_recall_at_1": float(chk_r1 / total),
        "chunk_recall_at_5": float(chk_r5 / total),
        "chunk_recall_at_10": float(chk_r10 / total),
        "mrr": mrr
    }
