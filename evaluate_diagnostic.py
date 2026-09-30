import json

with open("results/diagnostic_raw.json") as f:
    diag_data = json.load(f)

with open("results/final_benchmark_raw.json") as f:
    e2e_data = json.load(f)

# Hardcoded map based on DB output
def v_id_to_str(vid):
    if not vid: return None
    vid = str(vid)
    # in db, ids 2 and 4 have version_num 2 (i.e. "2.0")
    if vid in ["2", "4"]: return "2.0"
    return "1.0"

version_res_correct = 0
version_res_numeric_total = 0
version_res_numeric_correct = 0
version_res_total = 0

llm_calls_required = 0
llm_success = 0
llm_timeout = 0

correct_abstentions = 0
incorrect_abstentions = 0

# End-to-end variables (from previous analysis)
e2e_correct = 0
e2e_numeric_total = 0
e2e_numeric_correct = 0

for i, diag in enumerate(diag_data):
    e2e = e2e_data[i]
    gold_v = diag["gold_version"]
    
    # 1 & 2. Version Resolution BEFORE LLM
    pred_v = v_id_to_str(diag["predicted_version"])
    # If route is CANONICAL_QA, pred_v is already correct string like "1.0" or "2.0". It might not need mapping if it's already "1.0".
    if diag["predicted_version"] in ["1.0", "2.0", "1", "2"]:
        if diag["predicted_version"] == "1": pred_v = "1.0"
        elif diag["predicted_version"] == "2": pred_v = "2.0"
        else: pred_v = diag["predicted_version"]
        
    if gold_v:
        version_res_total += 1
        is_num = gold_v.replace(".", "").isdigit()
        if is_num:
            version_res_numeric_total += 1
        
        if pred_v == gold_v:
            version_res_correct += 1
            if is_num:
                version_res_numeric_correct += 1
                
    # 3. End-to-End Outcome
    e2e_resp = e2e.get("response")
    if e2e_resp:
        cits = e2e_resp.get("citations", [])
        e2e_pred = cits[0].get("version") if cits else None
        if gold_v:
            if e2e_pred == gold_v:
                e2e_correct += 1
                if is_num:
                    e2e_numeric_correct += 1

    # 4 & 5. LLM Rates
    if diag["llm_required"]:
        llm_calls_required += 1
        if e2e_resp and e2e_resp.get("llm_used"):
            llm_success += 1
        else:
            # It timed out and fell back to deterministic
            llm_timeout += 1

    # 6 & 7. Abstention Rates
    # Abstention happens if e2e route is ABSTAINED or REFUSAL
    if e2e_resp and e2e_resp.get("route") in ["ABSTAINED", "REFUSAL"]:
        gold_ans = diag.get("gold_answer", "") # wait, gold answer is in e2e
        gold_ans = e2e["item"].get("target_answer", "")
        if "cannot" in gold_ans.lower() or not gold_ans:
            correct_abstentions += 1
        else:
            incorrect_abstentions += 1

print("1. Version-resolution accuracy over all applicable queries:")
print(f"   {version_res_correct}/{version_res_total} = {version_res_correct/version_res_total:.2%}")

print("2. Numeric-version-only accuracy:")
print(f"   {version_res_numeric_correct}/{version_res_numeric_total} = {version_res_numeric_correct/version_res_numeric_total:.2%}")

print("3. End-to-end version-correct outcome from the 301 benchmark:")
print(f"   {e2e_correct}/{version_res_total} = {e2e_correct/version_res_total:.2%}")

print("4. LLM generation success rate:")
print(f"   {llm_success}/{llm_calls_required} = {llm_success/max(1, llm_calls_required):.2%}")

print("5. LLM timeout rate:")
print(f"   {llm_timeout}/{llm_calls_required} = {llm_timeout/max(1, llm_calls_required):.2%}")

print("6. Correct abstention rate:")
total_abstentions = correct_abstentions + incorrect_abstentions
print(f"   {correct_abstentions}/{total_abstentions} = {correct_abstentions/max(1, total_abstentions):.2%}")

print("7. Incorrect abstention rate:")
print(f"   {incorrect_abstentions}/{total_abstentions} = {incorrect_abstentions/max(1, total_abstentions):.2%}")

