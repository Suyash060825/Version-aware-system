"""
scripts/run_calibration_proper.py
E4: Proper confidence calibration with val→test split.
- Fits Isotonic Regression on benchmark_val.json (held-out validation set)
- Evaluates calibrated confidence on benchmark_test.json (held-out test set)
- Reports Brier score, ECE (10-bin), and reliability diagram data
- Reconciles the discrepancy between confidence_calibration.csv and eval_summary.json
"""
import os
import sys
import csv
import json
import time
import re
import string
import numpy as np
from sklearn.isotonic import IsotonicRegression

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import create_app
from rag.engine.query_engine import get_query_engine


def normalize_text(text):
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[\$\€\£]', '', text)
    text = text.translate(str.maketrans('', '', string.punctuation))
    return re.sub(r'\s+', ' ', text).strip()


def compute_token_f1(pred, gold):
    pred_tokens = normalize_text(pred).split()
    gold_tokens = normalize_text(gold).split()
    if not pred_tokens or not gold_tokens:
        return 1.0 if pred_tokens == gold_tokens else 0.0
    common = set(pred_tokens) & set(gold_tokens)
    if not common:
        return 0.0
    prec = sum(1 for t in pred_tokens if t in common) / len(pred_tokens)
    rec = sum(1 for t in gold_tokens if t in common) / len(gold_tokens)
    if prec + rec == 0:
        return 0.0
    return (2 * prec * rec) / (prec + rec)


def is_correct(pred, target, abstained, cat):
    if cat in ("unanswerable", "adversarial", "confidentiality", "department_auth"):
        return abstained or "insufficient" in pred.lower() or "not find" in pred.lower()
    if abstained:
        return False
    f1 = compute_token_f1(pred, target)
    norm_pred = normalize_text(pred)
    norm_gold = normalize_text(target)
    if norm_gold in norm_pred or norm_pred in norm_gold:
        return True
    gold_nums = re.findall(r'\b\d+(?:\.\d+)?\b', norm_gold)
    pred_nums = re.findall(r'\b\d+(?:\.\d+)?\b', norm_pred)
    if gold_nums and all(n in pred_nums for n in gold_nums) and f1 >= 0.30:
        return True
    return f1 >= 0.50


def compute_ece(conf_arr, acc_arr, n_bins=10):
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    bin_data = []
    for i in range(n_bins):
        mask = (conf_arr >= bins[i]) & (conf_arr < bins[i + 1])
        n_bin = np.sum(mask)
        if n_bin > 0:
            bin_acc = float(np.mean(acc_arr[mask]))
            bin_conf = float(np.mean(conf_arr[mask]))
            ece += (n_bin / len(conf_arr)) * abs(bin_acc - bin_conf)
            bin_data.append((round((bins[i] + bins[i+1]) / 2, 2), round(bin_conf, 4), round(bin_acc, 4), int(n_bin)))
    return float(ece), bin_data


def collect_predictions(engine, cases):
    conf_scores = []
    accuracies = []
    for tc in cases:
        q = tc["query"]
        target = tc.get("target_answer", "")
        cat = tc.get("category", "")
        res = engine.answer(q)
        acc = 1.0 if is_correct(res.answer, target, res.abstained, cat) else 0.0
        conf_scores.append(float(res.confidence))
        accuracies.append(acc)
    return np.array(conf_scores), np.array(accuracies)


def run_calibration_proper():
    app = create_app("development")
    os.makedirs("results", exist_ok=True)

    with app.app_context():
        engine = get_query_engine()

        with open("data/benchmarks/benchmark_val.json") as f:
            val_cases = json.load(f)
        with open("data/benchmarks/benchmark_test.json") as f:
            test_cases = json.load(f)

        print(f"[Calibration] Val set: {len(val_cases)} | Test set: {len(test_cases)}")

        # Collect raw predictions on VAL set (for fitting calibration)
        print("[Calibration] Collecting VAL predictions for calibration fitting...")
        val_conf, val_acc = collect_predictions(engine, val_cases)

        # Collect raw predictions on TEST set (for reporting)
        print("[Calibration] Collecting TEST predictions for evaluation...")
        test_conf, test_acc = collect_predictions(engine, test_cases)

        # --- Raw metrics on TEST set ---
        brier_raw_test = float(np.mean((test_conf - test_acc) ** 2))
        ece_raw_test, bin_data_raw = compute_ece(test_conf, test_acc, n_bins=10)

        # --- Fit Isotonic Regression on VAL set ---
        iso_reg = IsotonicRegression(out_of_bounds='clip')
        iso_reg.fit(val_conf, val_acc)

        # --- Apply calibration to TEST set ---
        test_conf_cal = iso_reg.predict(test_conf)
        brier_cal_test = float(np.mean((test_conf_cal - test_acc) ** 2))
        ece_cal_test, bin_data_cal = compute_ece(test_conf_cal, test_acc, n_bins=10)

        # --- Summary metrics ---
        brier_reduction_pct = ((brier_raw_test - brier_cal_test) / brier_raw_test) * 100
        ece_reduction_pct = ((ece_raw_test - ece_cal_test) / max(ece_raw_test, 1e-9)) * 100

        print(f"[Calibration] RAW  — Brier: {brier_raw_test:.4f}, ECE: {ece_raw_test:.4f}")
        print(f"[Calibration] CAL  — Brier: {brier_cal_test:.4f}, ECE: {ece_cal_test:.4f}")
        print(f"[Calibration] Improvement — Brier: -{brier_reduction_pct:.1f}%, ECE: -{ece_reduction_pct:.1f}%")

        with open("results/calibration_proper.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Calibration Scheme", "Brier Score", "ECE (10-bin)", "Brier Reduction (%)", "ECE Reduction (%)"])
            writer.writerow([
                "Raw Confidence (Uncalibrated, Test Set)",
                round(brier_raw_test, 4), round(ece_raw_test, 4), "Baseline", "Baseline"
            ])
            writer.writerow([
                "Isotonic Regression (Fitted on Val, Evaluated on Test)",
                round(brier_cal_test, 4), round(ece_cal_test, 4),
                round(brier_reduction_pct, 1), round(ece_reduction_pct, 1)
            ])
            writer.writerow([])
            writer.writerow(["Reliability Diagram (Raw) — Bin Center", "Mean Confidence", "Mean Accuracy", "N Samples"])
            for row in bin_data_raw:
                writer.writerow(row)
            writer.writerow([])
            writer.writerow(["Reliability Diagram (Calibrated) — Bin Center", "Mean Confidence", "Mean Accuracy", "N Samples"])
            for row in bin_data_cal:
                writer.writerow(row)

        # Also write updated confidence_calibration.csv for paper consistency
        with open("results/confidence_calibration.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Calibration Scheme", "Brier Score", "Expected Calibration Error (ECE)", "ECE Reduction (%)"])
            writer.writerow([
                "Raw Confidence (Uncalibrated)",
                round(brier_raw_test, 4), round(ece_raw_test, 4), "Baseline"
            ])
            writer.writerow([
                "Isotonic Regression (Calibrated, Val→Test)",
                round(brier_cal_test, 4), round(ece_cal_test, 4),
                f"{ece_reduction_pct:.1f}%"
            ])

        print(f"[Calibration] Results saved → results/calibration_proper.csv + results/confidence_calibration.csv")
        return brier_raw_test, ece_raw_test, brier_cal_test, ece_cal_test


if __name__ == "__main__":
    run_calibration_proper()
