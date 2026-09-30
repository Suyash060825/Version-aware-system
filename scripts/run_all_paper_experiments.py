#!/usr/bin/env python3
"""
scripts/run_all_paper_experiments.py
Master experiment runner for journal publication.
Runs all new experiments in sequence: E1–E7.
Results are saved to results/*.csv and then used to update the paper.
"""
import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def run_step(name, fn):
    print(f"\n{'='*60}")
    print(f"  RUNNING: {name}")
    print(f"{'='*60}")
    t0 = time.time()
    try:
        result = fn()
        elapsed = time.time() - t0
        print(f"  ✓ DONE in {elapsed:.1f}s")
        return True, result
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  ✗ FAILED: {e}")
        return False, None

results_log = {}

# E1: Multi-delta incremental sweep
from run_delta_sweep import run_delta_sweep
ok, data = run_step("E1: Multi-Delta Incremental Sweep", run_delta_sweep)
results_log["E1_delta_sweep"] = "OK" if ok else "FAILED"

# E2: Stratified ablation (takes longer — involves 30+15+15 queries per config)
from run_stratified_ablation import run_stratified_ablation
ok, data = run_step("E2: Stratified Ablation Study", run_stratified_ablation)
results_log["E2_stratified_ablation"] = "OK" if ok else "FAILED"

# E3: Tier 3 version-diff evaluation
from run_tier3_eval import run_tier3_eval
ok, data = run_step("E3: Tier 3 Version-Diff Evaluation", run_tier3_eval)
results_log["E3_tier3_eval"] = "OK" if ok else "FAILED"

# E4: Proper calibration (val→test split)
from run_calibration_proper import run_calibration_proper
ok, data = run_step("E4: Proper Calibration (Val→Test)", run_calibration_proper)
results_log["E4_calibration"] = "OK" if ok else "FAILED"

# E6: Strict retrieval metrics
from run_retrieval_strict import run_retrieval_strict
ok, data = run_step("E6: Strict Chunk-Level Retrieval Metrics", run_retrieval_strict)
results_log["E6_strict_retrieval"] = "OK" if ok else "FAILED"

# E7: Confidence intervals (bootstrap resampling — runs full inference again)
from run_confidence_intervals import run_confidence_intervals
ok, data = run_step("E7: Confidence Intervals (Bootstrap n=1000)", run_confidence_intervals)
results_log["E7_confidence_intervals"] = "OK" if ok else "FAILED"

print(f"\n{'='*60}")
print("  EXPERIMENT SUITE COMPLETE")
print(f"{'='*60}")
for k, v in results_log.items():
    print(f"  {k}: {v}")
print(f"\nAll results in results/ directory.")
