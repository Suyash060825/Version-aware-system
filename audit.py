import json
from collections import Counter

with open("results/diagnostic_raw.json") as f:
    diag_data = json.load(f)

with open("results/final_benchmark_raw.json") as f:
    e2e_data = json.load(f)

def v_id_to_str(vid):
    if not vid: return None
    vid = str(vid)
    if vid in ["2", "4"]: return "2.0"
    return "1.0"

bucket_counts = {
    "llm_invoked": {
        "successful_generation": 0,
        "timeout_then_deterministic_fallback": 0,
        "abstention": 0,
        "timeout_then_crash": 0,
        "other": 0
    },
    "no_llm_invoked": {
        "fast_path_fact": 0,
        "canonical_qa": 0,
        "temporal_comparison": 0,
        "nli_abstention_before_llm": 0,
        "zero_chunks_refusal": 0,
        "other": 0
    }
}

incorrect_cases = []
cat_stats = {}
numeric_total = 0
excluded = 0
correct_count = 0

for i, diag in enumerate(diag_data):
    e2e = e2e_data[i]
    e2e_resp = e2e.get("response") or {}
    
    cat = diag["query_category"]
    if cat not in cat_stats:
        cat_stats[cat] = {"total": 0, "correct": 0}
        
    diag_route = diag["route"]
    e2e_route = e2e_resp.get("route")
    llm_used = e2e_resp.get("llm_used", False)
    fallback = e2e_resp.get("fallback", False)
    cits = e2e_resp.get("citations", [])
    
    # Bucket mapping
    if diag["llm_required"]:
        if llm_used:
            bucket_counts["llm_invoked"]["successful_generation"] += 1
        elif cits and not fallback:
            bucket_counts["llm_invoked"]["timeout_then_deterministic_fallback"] += 1
        elif e2e_route in ["ABSTAINED", "REFUSAL"]:
            bucket_counts["llm_invoked"]["abstention"] += 1
        elif e2e.get("error"):
            bucket_counts["llm_invoked"]["timeout_then_crash"] += 1
        else:
            bucket_counts["llm_invoked"]["other"] += 1
    else:
        if diag_route == "FAST_PATH_FACT":
            bucket_counts["no_llm_invoked"]["fast_path_fact"] += 1
        elif diag_route == "CANONICAL_QA":
            bucket_counts["no_llm_invoked"]["canonical_qa"] += 1
        elif diag_route == "TEMPORAL_COMPARISON":
            bucket_counts["no_llm_invoked"]["temporal_comparison"] += 1
        elif diag_route == "ABSTAINED":
            if diag.get("abstain_reason") == "Confidence gate rejected":
                bucket_counts["no_llm_invoked"]["nli_abstention_before_llm"] += 1
            else:
                bucket_counts["no_llm_invoked"]["zero_chunks_refusal"] += 1
        else:
            bucket_counts["no_llm_invoked"]["other"] += 1

    # Pre-generation Version Accuracy
    gold_v = diag["gold_version"]
    raw_pred = diag["predicted_version"]
    if raw_pred in ["1.0", "2.0", "1", "2"]:
        pred_v = "1.0" if raw_pred == "1" else ("2.0" if raw_pred == "2" else raw_pred)
    else:
        pred_v = v_id_to_str(raw_pred)
        
    mechanism = "retrieval_metadata"
    if diag_route == "FAST_PATH_FACT": mechanism = "fact_path"
    elif diag_route == "CANONICAL_QA": mechanism = "compiled_qa"
    elif diag_route == "TEMPORAL_COMPARISON": mechanism = "temporal_resolver"

    if gold_v:
        if gold_v.replace(".", "").isdigit():
            numeric_total += 1
            cat_stats[cat]["total"] += 1
            if pred_v == gold_v:
                correct_count += 1
                cat_stats[cat]["correct"] += 1
            else:
                incorrect_cases.append({
                    "query_id": diag["query_id"],
                    "gold": gold_v,
                    "pred": pred_v,
                    "mechanism": mechanism,
                    "route": diag_route
                })
        else:
            excluded += 1
    else:
        excluded += 1

print("=== LLM INVOKED (244) ===")
for k, v in bucket_counts["llm_invoked"].items(): print(f"{k}: {v}")

print("\n=== NO LLM INVOKED (57) ===")
for k, v in bucket_counts["no_llm_invoked"].items(): print(f"{k}: {v}")

print(f"\nTotal Queries: {sum(bucket_counts['llm_invoked'].values()) + sum(bucket_counts['no_llm_invoked'].values())}")

print("\n=== VERIFY METRICS ===")
print(f"Total: {len(diag_data)}, Excluded: {excluded}, Numeric: {numeric_total}")
print(f"Correct: {correct_count}, Incorrect: {len(incorrect_cases)}")

print("\n=== CATEGORY-WISE ===")
for k, v in cat_stats.items():
    if v["total"] > 0:
        print(f"{k}: {v['correct']}/{v['total']} ({v['correct']/v['total']:.2%})")

print("\n=== INCORRECT CASES ===")
for case in incorrect_cases:
    print(f"{case['query_id']}: Gold={case['gold']} Pred={case['pred']} ({case['mechanism']})")

