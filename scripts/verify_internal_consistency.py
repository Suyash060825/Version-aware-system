"""
scripts/verify_internal_consistency.py
Strict automated verification of internal consistency across all authoritative artifacts.
Exits with code 0 on perfect consistency, non-zero on any discrepancy.
"""
import json
import csv
import os
import sys

def verify():
    errors = []

    print("[VERIFICATION] Loading artifacts...")

    # 1. Load Raw Benchmark
    raw_path = "results/final_benchmark_raw.json"
    if not os.path.exists(raw_path):
        errors.append(f"Missing {raw_path}")
        return errors
    with open(raw_path) as f:
        raw = json.load(f)
    if len(raw) != 301:
        errors.append(f"Benchmark count is {len(raw)}, expected 301")

    # 2. Load Final Authoritative Audit JSON & CSV
    audit_json_path = "results/final_authoritative_301_audit.json"
    with open(audit_json_path) as f:
        audit_json = json.load(f)
    if len(audit_json) != 301:
        errors.append(f"Audit JSON count is {len(audit_json)}, expected 301")

    audit_csv_path = "results/final_authoritative_301_audit.csv"
    with open(audit_csv_path) as f:
        reader = list(csv.DictReader(f))
    if len(reader) != 301:
        errors.append(f"Audit CSV count is {len(reader)}, expected 301")

    # 3. Load Final Authoritative Metrics
    metrics_path = "results/final_authoritative_metrics.json"
    with open(metrics_path) as f:
        metrics = json.load(f)

    # 4. Check Version Correct count reconciliation
    raw_v_corr = 0
    for r in raw:
        exp_v = r["item"].get("expected_version")
        cits = (r.get("response") or {}).get("citations", [])
        pred_v = cits[0].get("version") if cits else None
        if exp_v and pred_v == exp_v:
            raw_v_corr += 1

    audit_v_corr = sum(1 for a in audit_json if a["version_correct"])
    csv_v_corr = sum(1 for a in reader if a["version_correct"] in [True, "True", "true"])
    metrics_v_corr = metrics["version_accuracy"]["overall_accuracy_count"]

    if not (raw_v_corr == audit_v_corr == csv_v_corr == metrics_v_corr == 96):
        errors.append(f"Version correctness mismatch: raw={raw_v_corr}, audit_json={audit_v_corr}, csv={csv_v_corr}, metrics={metrics_v_corr}, expected 96")

    # 5. Check LLM Invocations
    llm_used_count = sum(1 for r in raw if (r.get("response") or {}).get("llm_used", False))
    if llm_used_count != 0:
        errors.append(f"Raw LLM used count is {llm_used_count}, expected 0")
    if metrics["llm_invocation_behavior"]["actual_llm_invocations"] != 0:
        errors.append(f"Metrics LLM invocations is {metrics['llm_invocation_behavior']['actual_llm_invocations']}, expected 0")
    if metrics["llm_invocation_behavior"]["llm_invoked_timed_out"] != 0:
        errors.append(f"Metrics LLM timeouts is {metrics['llm_invocation_behavior']['llm_invoked_timed_out']}, expected 0")

    # 6. Check Baseline Files
    baselines_path = "results/controlled_baselines.json"
    with open(baselines_path) as f:
        c_baselines = json.load(f)

    for b_char, b_label in [
        ('A', 'Baseline A (Naive)'),
        ('B', 'Baseline B (Temporal-only)'),
        ('C', 'Baseline C (Auth-only)'),
        ('D', 'Baseline D (Temp+Auth Standard)'),
        ('E', 'Baseline E (Full Veritas)')
    ]:
        b_raw_path = f"results/baseline_{b_char}_raw.json"
        if not os.path.exists(b_raw_path):
            errors.append(f"Missing {b_raw_path}")
            continue
        with open(b_raw_path) as f:
            b_rows = json.load(f)
        if len(b_rows) != 301:
            errors.append(f"{b_raw_path} has {len(b_rows)} items, expected 301")
        b_corr = sum(1 for r in b_rows if r["correctness"])
        if c_baselines[b_label]["overall_correct"] != b_corr:
            errors.append(f"{b_label} aggregate ({c_baselines[b_label]['overall_correct']}) differs from raw file ({b_corr})")

    # 7. Check Calibration artifact
    cal_path = "results/calibration_proper.csv"
    if not os.path.exists(cal_path):
        errors.append(f"Missing {cal_path}")

    # 8. Check Retrieval strict artifact
    ret_path = "results/retrieval_metrics_strict.csv"
    if not os.path.exists(ret_path):
        errors.append(f"Missing {ret_path}")

    # 9. Check Incremental sweep artifact
    inc_path = "results/incremental_delta_sweep.csv"
    if not os.path.exists(inc_path):
        errors.append(f"Missing {inc_path}")

    # 10. Check FINAL_AUTHORITATIVE_RESULTS.md existence
    auth_doc_path = "results/FINAL_AUTHORITATIVE_RESULTS.md"
    if not os.path.exists(auth_doc_path):
        errors.append(f"Missing {auth_doc_path}")
    else:
        with open(auth_doc_path) as f:
            doc_text = f.read()
        if "AUTHORITATIVE FINAL EVIDENCE — DO NOT OVERRIDE FROM OLDER REPORTS" not in doc_text:
            errors.append("FINAL_AUTHORITATIVE_RESULTS.md missing mandatory header")
        if "96/288" not in doc_text and "96 / 288" not in doc_text:
            errors.append("FINAL_AUTHORITATIVE_RESULTS.md missing 96/288 version accuracy metric")

    return errors

if __name__ == "__main__":
    errs = verify()
    if errs:
        print(f"[FAIL] Consistency check failed with {len(errs)} errors:")
        for e in errs:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("[PASS] All internal consistency checks passed successfully (100% synchronized).")
        sys.exit(0)
