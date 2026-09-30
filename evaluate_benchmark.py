import json
import collections
import re
import statistics

RAW_FILE = "results/final_benchmark_raw.json"
METRICS_FILE = "results/final_benchmark_metrics.json"

def compute_f1(a_gold, a_pred):
    gold_toks = a_gold.lower().split()
    pred_toks = a_pred.lower().split()
    common = collections.Counter(gold_toks) & collections.Counter(pred_toks)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    precision = 1.0 * num_same / len(pred_toks)
    recall = 1.0 * num_same / len(gold_toks)
    f1 = (2 * precision * recall) / (precision + recall)
    return f1

def exact_match(a_gold, a_pred):
    return a_gold.strip().lower() == a_pred.strip().lower()

with open(RAW_FILE) as f:
    results = json.load(f)

print(f"Loaded {len(results)} results.")

metrics = {
    "version_selection": {},
    "answer_quality": {
        "strict_exact_match": 0,
        "token_f1_sum": 0,
        "token_f1_avg": 0,
        "correct_abstentions": 0,
        "incorrect_answers": 0,
        "incorrect_refusals": 0
    },
    "retrieval": {
        "policy_recall_sum": 0,
        "chunk_recall_sum": 0,
    },
    "citation": {
        "precision_sum": 0,
        "recall_sum": 0
    },
    "latency": {
        "all": [],
        "route": collections.defaultdict(list)
    },
    "runtime": {
        "timeouts": 0,
        "nli_failures": 0,
        "redis_failures": 0,
        "other_errors": 0
    },
    "categories": collections.defaultdict(lambda: {"total": 0, "correct_version": 0, "correct_answer": 0, "abstained": 0})
}

version_correct = 0
version_numeric_total = 0
version_numeric_correct = 0

f1_scores = []
em_scores = []
latencies = []

for r in results:
    item = r["item"]
    cat = item["category"]
    metrics["categories"][cat]["total"] += 1
    
    if r["error"]:
        metrics["runtime"]["other_errors"] += 1
        continue
        
    res = r["response"]
    if not res:
        metrics["runtime"]["other_errors"] += 1
        continue
        
    lat = r["latency_sec"]
    latencies.append(lat)
    metrics["latency"]["all"].append(lat)
    metrics["latency"]["route"][res.get("route", "unknown")].append(lat)
    
    # Version Logic
    exp_version = item.get("expected_version")
    citations = res.get("citations", [])
    pred_versions = [c.get("version") for c in citations if c.get("version")]
    pred_version = pred_versions[0] if pred_versions else None
    
    if exp_version:
        is_numeric = exp_version.replace(".", "").isdigit()
        if is_numeric:
            version_numeric_total += 1
        if pred_version == exp_version:
            version_correct += 1
            if is_numeric:
                version_numeric_correct += 1
            metrics["categories"][cat]["correct_version"] += 1

    # Answer Quality Logic
    gold_ans = item.get("target_answer", "")
    pred_ans = res.get("answer", "")
    is_abstained = res.get("fallback", False) or "cannot provide a confident answer" in pred_ans
    
    if is_abstained:
        metrics["categories"][cat]["abstained"] += 1
        if "cannot" in gold_ans.lower() or not gold_ans:
            metrics["answer_quality"]["correct_abstentions"] += 1
        else:
            metrics["answer_quality"]["incorrect_refusals"] += 1
            metrics["categories"][cat]["incorrect"] = metrics["categories"][cat].get("incorrect", 0) + 1
    else:
        em = exact_match(gold_ans, pred_ans)
        f1 = compute_f1(gold_ans, pred_ans)
        em_scores.append(em)
        f1_scores.append(f1)
        if em:
            metrics["answer_quality"]["strict_exact_match"] += 1
            metrics["categories"][cat]["correct_answer"] += 1
        elif f1 > 0.5:
            # partial
            metrics["categories"][cat]["correct_answer"] += 1
        else:
            metrics["answer_quality"]["incorrect_answers"] += 1
            metrics["categories"][cat]["incorrect"] = metrics["categories"][cat].get("incorrect", 0) + 1

    # Timeout
    if "timeout" in pred_ans.lower() or not res.get("llm_used"):
        metrics["runtime"]["timeouts"] += 1

metrics["version_selection"]["overall"] = f"{version_correct}/{len(results)} = {version_correct/len(results):.2%}"
metrics["version_selection"]["numeric_only"] = f"{version_numeric_correct}/{version_numeric_total} = {version_numeric_correct/max(1, version_numeric_total):.2%}"

if f1_scores:
    metrics["answer_quality"]["token_f1_avg"] = sum(f1_scores)/len(f1_scores)

if latencies:
    metrics["latency"]["P50"] = statistics.median(latencies)
    metrics["latency"]["P95"] = statistics.quantiles(latencies, n=100)[94] if len(latencies) >= 20 else max(latencies)

with open(METRICS_FILE, "w") as f:
    json.dump(metrics, f, indent=2)

print(f"Metrics saved to {METRICS_FILE}")
