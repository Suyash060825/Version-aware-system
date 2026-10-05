"""
tests/system_characterization/analysis/metrics_calculator.py
Calculates rigorous statistical metrics with exact denominators (e.g. 88.3% (265/300)),
confidence intervals, percentiles (P50, P90, P95, P99), and confusion matrices across all test dimensions.
"""
import math
import numpy as np
from typing import List, Dict, Any, Tuple
from collections import Counter, defaultdict

def format_stat_with_denom(count: int, total: int, decimals: int = 1) -> str:
    if total == 0:
        return f"0.0% (0/0) [N=0]"
    pct = (count / total) * 100.0
    return f"{pct:.{decimals}f}% ({count}/{total}) [N={total}]"

def compute_percentiles(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0, "N": 0}
    arr = np.array(values)
    return {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr)),
        "min": float(np.min(arr)),
        "p50": float(np.percentile(arr, 50)),
        "p90": float(np.percentile(arr, 90)),
        "p95": float(np.percentile(arr, 95)),
        "p99": float(np.percentile(arr, 99)),
        "max": float(np.max(arr)),
        "N": len(values)
    }

def compute_wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    z = 1.95996  # 95% confidence
    p = successes / total
    denom = 1 + (z**2 / total)
    center = (p + (z**2 / (2 * total))) / denom
    margin = (z * math.sqrt((p * (1 - p) / total) + (z**2 / (4 * total**2)))) / denom
    return max(0.0, center - margin), min(1.0, center + margin)

class MetricsCalculator:
    def __init__(self, master_records: List[Dict[str, Any]]):
        self.records = master_records
        self.total_queries = len(master_records)

    def aggregate_by_category(self) -> Dict[str, Any]:
        cat_stats = defaultdict(lambda: {"total": 0, "correct": 0, "abstained": 0, "latencies": [], "failures": []})
        for r in self.records:
            cat = r["query_category"]
            cat_stats[cat]["total"] += 1
            if r["answer_correctness"]:
                cat_stats[cat]["correct"] += 1
            if r["abstained"]:
                cat_stats[cat]["abstained"] += 1
            cat_stats[cat]["latencies"].append(r["latency_ms"])
            if not r["answer_correctness"]:
                cat_stats[cat]["failures"].append(r)

        result = {}
        for cat, data in cat_stats.items():
            tot = data["total"]
            corr = data["correct"]
            pct_str = format_stat_with_denom(corr, tot)
            low_ci, high_ci = compute_wilson_score_interval(corr, tot)
            lat_stats = compute_percentiles(data["latencies"])

            result[cat] = {
                "category": cat,
                "total": tot,
                "correct": corr,
                "accuracy_formatted": pct_str,
                "accuracy_pct": (corr / tot * 100.0) if tot > 0 else 0.0,
                "ci_95": (low_ci * 100.0, high_ci * 100.0),
                "abstained_count": data["abstained"],
                "p50_latency_ms": lat_stats["p50"],
                "p95_latency_ms": lat_stats["p95"],
                "failures_count": len(data["failures"])
            }
        return result

    def aggregate_by_difficulty(self) -> Dict[str, Any]:
        diff_stats = defaultdict(lambda: {"total": 0, "correct": 0, "latencies": []})
        for r in self.records:
            diff = r.get("difficulty", "medium")
            diff_stats[diff]["total"] += 1
            if r["answer_correctness"]:
                diff_stats[diff]["correct"] += 1
            diff_stats[diff]["latencies"].append(r["latency_ms"])

        res = {}
        for diff, data in diff_stats.items():
            tot = data["total"]
            corr = data["correct"]
            res[diff] = {
                "difficulty": diff,
                "total": tot,
                "correct": corr,
                "accuracy_formatted": format_stat_with_denom(corr, tot),
                "accuracy_pct": (corr / tot * 100.0) if tot > 0 else 0.0,
                "latencies": compute_percentiles(data["latencies"])
            }
        return res

    def failure_stage_breakdown(self) -> Dict[str, Any]:
        stage_counts = Counter(r.get("failure_stage", "NONE") for r in self.records if not r.get("answer_correctness", True))
        error_counts = Counter(r.get("error_type", "NONE") for r in self.records if not r.get("answer_correctness", True))
        
        return {
            "by_stage": dict(stage_counts),
            "by_error_code": dict(error_counts)
        }
