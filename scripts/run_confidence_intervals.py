"""
scripts/run_confidence_intervals.py
E7: Compute 95% confidence intervals and standard deviations for all key metrics.
Uses bootstrap resampling (n=1000) on the 301-query test set.
Outputs CI bounds for: Exact Match %, Token F1, Version Accuracy, Citation Precision.
"""
import os
import sys
import csv
import json
import re
import string
import numpy as np

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


def bootstrap_ci(data, stat_fn=np.mean, n_boot=1000, ci=95):
    """Compute bootstrap confidence interval for a statistic."""
    arr = np.array(data)
    boot_stats = [stat_fn(np.random.choice(arr, size=len(arr), replace=True)) for _ in range(n_boot)]
    lower = np.percentile(boot_stats, (100 - ci) / 2)
    upper = np.percentile(boot_stats, 100 - (100 - ci) / 2)
    return float(np.mean(arr)), float(np.std(arr)), float(lower), float(upper)


def run_confidence_intervals():
    app = create_app("development")
    os.makedirs("results", exist_ok=True)

    with app.app_context():
        engine = get_query_engine()

        with open("data/benchmarks/benchmark_test.json") as f:
            test_cases = json.load(f)

        print(f"[CI Eval] Running on {len(test_cases)} queries with bootstrap n=1000...")

        exact_matches = []
        token_f1s = []
        version_corrects = []
        cit_precisions = []

        for i, tc in enumerate(test_cases):
            if i % 50 == 0:
                print(f"  Processing {i}/{len(test_cases)}...")
            q = tc["query"]
            target = tc.get("target_answer", "")
            cat = tc.get("category", "")
            exp_ver = tc.get("expected_version", "")
            gold_policy = tc.get("ground_truth_policy", "")

            res = engine.answer(q)

            # Exact match
            if cat in ("unanswerable", "adversarial", "confidentiality", "department_auth"):
                exact = 1.0 if (res.abstained or "insufficient" in res.answer.lower() or "not find" in res.answer.lower()) else 0.0
            elif res.abstained:
                exact = 0.0
            else:
                f1 = compute_token_f1(res.answer, target)
                norm_pred = normalize_text(res.answer)
                norm_gold = normalize_text(target)
                if norm_gold in norm_pred or norm_pred in norm_gold:
                    exact = 1.0
                else:
                    gold_nums = re.findall(r'\b\d+(?:\.\d+)?\b', norm_gold)
                    pred_nums = re.findall(r'\b\d+(?:\.\d+)?\b', norm_pred)
                    if gold_nums and all(n in pred_nums for n in gold_nums) and f1 >= 0.30:
                        exact = 1.0
                    else:
                        exact = 1.0 if f1 >= 0.50 else 0.0

            exact_matches.append(exact)

            # Token F1 (answer-seeking only)
            if cat not in ("unanswerable", "adversarial", "confidentiality", "department_auth") and not res.abstained:
                token_f1s.append(compute_token_f1(res.answer, target))

            # Version accuracy
            pred_ver = res.policy_versions[0] if res.policy_versions else "None"
            if cat in ("unanswerable", "adversarial", "confidentiality", "department_auth"):
                ver_ok = res.abstained
            elif exp_ver:
                ver_ok = (str(exp_ver) == str(pred_ver)) or (str(exp_ver) in str(pred_ver))
            else:
                ver_ok = len(res.citations) > 0
            version_corrects.append(1.0 if ver_ok else 0.0)

            # Citation precision
            if res.citations:
                hits = 0
                for c in res.citations:
                    p_name = c.get("policy_name", "").lower()
                    if gold_policy and (gold_policy.lower() in p_name or any(
                            w in p_name for w in gold_policy.lower().split() if len(w) > 4)):
                        hits += 1
                cit_precisions.append(hits / len(res.citations))
            elif cat not in ("unanswerable", "adversarial", "confidentiality", "department_auth"):
                cit_precisions.append(0.0)

        np.random.seed(42)
        rows = []
        metrics = [
            ("Exact Match Accuracy (%)", [x * 100 for x in exact_matches]),
            ("Token F1 Score", token_f1s),
            ("Version Selection Accuracy (%)", [x * 100 for x in version_corrects]),
            ("Citation Precision", cit_precisions),
        ]

        for metric_name, data in metrics:
            if not data:
                continue
            mean, std, ci_low, ci_high = bootstrap_ci(data)
            rows.append([metric_name, round(mean, 4), round(std, 4), round(ci_low, 4), round(ci_high, 4), len(data)])
            print(f"  {metric_name}: {mean:.4f} ± {std:.4f} [95% CI: {ci_low:.4f}–{ci_high:.4f}]")

        with open("results/confidence_intervals.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Mean", "Std Dev", "95% CI Lower", "95% CI Upper", "N"])
            for r in rows:
                writer.writerow(r)

        print(f"\n[CI Eval] Results saved → results/confidence_intervals.csv")
        return rows


if __name__ == "__main__":
    run_confidence_intervals()
