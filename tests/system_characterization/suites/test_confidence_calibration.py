"""
tests/system_characterization/suites/test_confidence_calibration.py
Evaluation of Veritas Multi-Factor Confidence Scoring & Isotonic Calibration.
Measures Expected Calibration Error (ECE), Brier Score, and reliability curves across query categories.
"""
import sys
import os
import math
import numpy as np
from typing import List, Dict, Any, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from rag.verification.confidence import ConfidenceEngine
from rag.engine.evidence_pack import EvidencePack
from tests.system_characterization.corpus.ground_truth_ledger import GroundTruthLedger

def compute_ece_and_brier(confidences: List[float], accuracies: List[int], num_bins: int = 10) -> Tuple[float, float, List[Dict[str, Any]]]:
    """
    Computes Expected Calibration Error (ECE) and Brier Score across binned predictions.
    """
    if not confidences or not accuracies:
        return 0.0, 0.0, []

    conf_arr = np.array(confidences)
    acc_arr = np.array(accuracies)

    # Brier Score = (1/N) * sum((prob - actual)^2)
    brier_score = float(np.mean((conf_arr - acc_arr) ** 2))

    bin_boundaries = np.linspace(0.0, 1.0, num_bins + 1)
    ece = 0.0
    bins_data = []

    for i in range(num_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        
        # Select items in this bin
        if i == num_bins - 1:
            in_bin = (conf_arr >= bin_lower) & (conf_arr <= bin_upper)
        else:
            in_bin = (conf_arr >= bin_lower) & (conf_arr < bin_upper)
            
        bin_size = np.sum(in_bin)
        if bin_size > 0:
            bin_acc = float(np.mean(acc_arr[in_bin]))
            bin_conf = float(np.mean(conf_arr[in_bin]))
            bin_error = abs(bin_acc - bin_conf)
            ece += (bin_size / len(confidences)) * bin_error
            bins_data.append({
                "bin_index": i,
                "bin_range": f"{bin_lower:.2f}-{bin_upper:.2f}",
                "count": int(bin_size),
                "avg_confidence": bin_conf,
                "avg_accuracy": bin_acc,
                "calibration_gap": bin_error
            })
        else:
            bins_data.append({
                "bin_index": i,
                "bin_range": f"{bin_lower:.2f}-{bin_upper:.2f}",
                "count": 0,
                "avg_confidence": (bin_lower + bin_upper) / 2,
                "avg_accuracy": 0.0,
                "calibration_gap": 0.0
            })

    return float(ece), float(brier_score), bins_data

class ConfidenceCalibrationBenchmark:
    def __init__(self, ledger: GroundTruthLedger):
        self.ledger = ledger
        self.engine = ConfidenceEngine()

    def evaluate_calibration(self, queries: List[Any]) -> Dict[str, Any]:
        raw_confs = []
        calibrated_confs = []
        outcomes = []
        records = []

        for q in queries:
            # Simulate evidence pack based on ground truth alignment
            is_valid_query = q.expected_authorization and not q.expected_abstention
            
            # Generate simulated retrieval scores and coverage
            if is_valid_query:
                retrieval_score = 0.85 if q.difficulty == "easy" else (0.65 if q.difficulty == "medium" else 0.45)
                chunks = [{"text": f"Authoritative text for {q.query_text}"}]
                actual_outcome = 1
            else:
                retrieval_score = 0.15 if q.is_adversarial else 0.20
                chunks = [{"text": "Irrelevant general text without answer"}]
                actual_outcome = 0

            pack = EvidencePack(
                query=q.query_text,
                route=q.expected_route,
                chunks=chunks,
                scores=[retrieval_score]
            )

            scored = self.engine.score(q.query_text, pack)
            
            # Uncalibrated baseline
            raw_val = (retrieval_score * 0.55) + (scored.coverage_score * 0.45)
            calib_val = scored.value

            raw_confs.append(raw_val)
            calibrated_confs.append(calib_val)
            outcomes.append(actual_outcome)

            records.append({
                "query_id": q.query_id,
                "query_category": q.query_category,
                "difficulty": q.difficulty,
                "raw_confidence": raw_val,
                "calibrated_confidence": calib_val,
                "actual_outcome": actual_outcome,
                "abstain_flag": scored.abstain,
                "is_abstention_correct": (scored.abstain == q.expected_abstention)
            })

        raw_ece, raw_brier, raw_bins = compute_ece_and_brier(raw_confs, outcomes)
        cal_ece, cal_brier, cal_bins = compute_ece_and_brier(calibrated_confs, outcomes)

        return {
            "raw_ece": raw_ece,
            "calibrated_ece": cal_ece,
            "raw_brier": raw_brier,
            "calibrated_brier": cal_brier,
            "ece_improvement_pct": ((raw_ece - cal_ece) / raw_ece * 100.0) if raw_ece > 0 else 0.0,
            "brier_improvement_pct": ((raw_brier - cal_brier) / raw_brier * 100.0) if raw_brier > 0 else 0.0,
            "calibration_bins": cal_bins,
            "records": records
        }

if __name__ == "__main__":
    ledger = GroundTruthLedger.load("tests/system_characterization/corpus/ground_truth_ledger.json")
    bench = ConfidenceCalibrationBenchmark(ledger)
    sample_q = list(ledger.queries.values())[:200]
    res = bench.evaluate_calibration(sample_q)
    print(f"Confidence Calibration: Raw ECE: {res['raw_ece']:.4f} -> Calibrated ECE: {res['calibrated_ece']:.4f} (Imp: {res['ece_improvement_pct']:.1f}%). Brier: {res['raw_brier']:.4f} -> {res['calibrated_brier']:.4f}")
