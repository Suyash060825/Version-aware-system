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


def compute_answer_contains_score(prediction: str, gold_exact: str) -> float:
    """Returns 1.0 if gold_exact normalized appears in prediction normalized, 0.0 otherwise."""
    if not gold_exact or not gold_exact.strip():
        return 0.0
    return 1.0 if gold_exact.lower().strip() in (prediction or "").lower() else 0.0


def compute_token_f1(prediction: str, reference: str) -> float:
    """Computes standard SQuAD-style Token F1 between prediction and reference with contains_bonus."""
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
    base_f1 = 2 * (precision * recall) / (precision + recall)
    return base_f1


def compute_expected_calibration_error(
    confidences: List[float],
    correctness: List[bool],
    num_bins: int = 10,
    mask: Optional[List[bool]] = None
) -> Dict[str, Any]:
    """
    Calculates ECE with uniform binning [0, 0.1, ..., 1.0].
    If mask is provided, calculates calibration only on elements where mask is True (e.g. non-abstained / answered items).
    """
    if not confidences or len(confidences) != len(correctness):
        return {"ece": 0.0, "bins": []}

    conf_arr = np.array(confidences)
    corr_arr = np.array(correctness, dtype=float)

    if mask is not None:
        mask_arr = np.array(mask, dtype=bool)
        conf_arr = conf_arr[mask_arr]
        corr_arr = corr_arr[mask_arr]

    total_n = len(conf_arr)
    if total_n == 0:
        return {"ece": 0.0, "num_bins": num_bins, "total_samples": 0, "bins": []}

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


_VER_SEQ_MAP = None

def _get_version_seq_map():
    global _VER_SEQ_MAP
    if _VER_SEQ_MAP is None:
        _VER_SEQ_MAP = {}
        try:
            from models import PolicyVersion
            p_vers = PolicyVersion.query.order_by(PolicyVersion.policy_id, PolicyVersion.id).all()
            seq_tracker = {}
            for v in p_vers:
                seq = seq_tracker.get(v.policy_id, 0) + 1
                seq_tracker[v.policy_id] = seq
                _VER_SEQ_MAP[v.id] = (v.policy_id, seq)
        except Exception:
            pass
    return _VER_SEQ_MAP


def _chunks_match(ret_cid: str, exp_cid: str) -> bool:
    if not ret_cid or not exp_cid:
        return False
    if ret_cid == exp_cid or ret_cid.startswith(exp_cid) or exp_cid.startswith(ret_cid):
        return True
    m_ret = re.match(r"^p(\d+)-v(\d+)(?:-s(\d+))?", ret_cid, re.IGNORECASE)
    m_exp = re.match(r"^CHK-0*(\d+)-V(\d+)(?:-(\d+))?", exp_cid, re.IGNORECASE)
    if m_ret and m_exp:
        ret_pol, ret_ver = int(m_ret.group(1)), int(m_ret.group(2))
        exp_pol, exp_ver_seq = int(m_exp.group(1)), int(m_exp.group(2))
        if ret_pol == exp_pol:
            vmap = _get_version_seq_map()
            if vmap and ret_ver in vmap:
                return vmap[ret_ver][1] == exp_ver_seq
            return ret_ver == exp_ver_seq
    return False


def compute_retrieval_metrics(retrieval_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes Policy Recall@1, 5, 10; Chunk Recall@1, 5, 10; and MRR (Tier-2 only and overall).
    FIX 7.2: Evaluates Policy Recall and Chunk MRR over authorized answerable queries.
    """
    total = len(retrieval_records)
    if total == 0:
        return {}

    # FIX 7.2: Policy Recall denominator is authorized queries with intended policy
    auth_policy_records = [
        r for r in retrieval_records
        if r.get("expected_policy_id") is not None and not r.get("expected_abstention", False)
    ]
    pol_denom = len(auth_policy_records) if auth_policy_records else total

    pol_r1 = 0
    pol_r5 = 0
    pol_r10 = 0

    for r in (auth_policy_records if auth_policy_records else retrieval_records):
        exp_pid = r.get("expected_policy_id")
        retrieved_pids = r.get("retrieved_policy_ids", [])
        if exp_pid is not None:
            p_match_1 = retrieved_pids and (retrieved_pids[0] == exp_pid or str(retrieved_pids[0]) == str(exp_pid))
            if p_match_1:
                pol_r1 += 1
            if any(p == exp_pid or str(p) == str(exp_pid) for p in retrieved_pids[:5]):
                pol_r5 += 1
            if any(p == exp_pid or str(p) == str(exp_pid) for p in retrieved_pids[:10]):
                pol_r10 += 1

    # FIX 7.2: Chunk Recall denominator is authorized queries with expected chunks
    auth_chunk_records = [
        r for r in retrieval_records
        if r.get("expected_chunk_ids") and not r.get("expected_abstention", False)
    ]
    chk_denom = len(auth_chunk_records) if auth_chunk_records else total

    chk_r1 = 0
    chk_r5 = 0
    chk_r10 = 0

    reciprocal_ranks = []
    tier_2_reciprocal_ranks = []

    for r in retrieval_records:
        exp_cids = set(r.get("expected_chunk_ids", []))
        retrieved_cids = r.get("retrieved_chunk_ids", [])
        is_tier_2 = r.get("is_tier_2", False)
        is_expected_abstain = r.get("expected_abstention", False)

        # Chunk Recall & MRR
        first_rank = None
        if exp_cids and not is_expected_abstain:
            for idx, cid in enumerate(retrieved_cids, start=1):
                if any(_chunks_match(cid, ec) for ec in exp_cids):
                    if first_rank is None:
                        first_rank = idx
                    if idx == 1:
                        chk_r1 += 1
                    if idx <= 5:
                        chk_r5 += 1
                    if idx <= 10:
                        chk_r10 += 1
                    break

        rr = (1.0 / first_rank) if first_rank else 0.0
        reciprocal_ranks.append(rr)
        if is_tier_2 and not is_expected_abstain:
            tier_2_reciprocal_ranks.append(rr)

    mrr_all = float(np.mean(reciprocal_ranks)) if reciprocal_ranks else 0.0
    mrr_tier_2 = float(np.mean(tier_2_reciprocal_ranks)) if tier_2_reciprocal_ranks else mrr_all

    return {
        "total_queries": total,
        "authorized_policy_queries": pol_denom,
        "policy_recall_at_1": float(pol_r1 / pol_denom),
        "policy_recall_at_5": float(pol_r5 / pol_denom),
        "policy_recall_at_10": float(pol_r10 / pol_denom),
        "chunk_recall_at_1": float(chk_r1 / chk_denom),
        "chunk_recall_at_5": float(chk_r5 / chk_denom),
        "chunk_recall_at_10": float(chk_r10 / chk_denom),
        "mrr": mrr_tier_2,
        "mrr_tier_2": mrr_tier_2,
        "mrr_all": mrr_all
    }
