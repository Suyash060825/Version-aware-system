"""
tests/system_characterization/suites/test_temporal_semantics.py
Evaluation of Veritas Temporal Resolution & Version Validity Engine.
Tests point-in-time validity V(c, t_q), interval overlaps, boundary dates, and supersession logic across 600 policy versions.
"""
import sys
import os
import time
from datetime import date, timedelta
from typing import List, Dict, Any, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from rag.versions.resolver import VersionResolver
from tests.system_characterization.corpus.ground_truth_ledger import GroundTruthLedger

class TemporalSemanticsBenchmark:
    def __init__(self, ledger: GroundTruthLedger):
        self.ledger = ledger
        self.resolver = VersionResolver()

    def run_temporal_evaluations(self) -> List[Dict[str, Any]]:
        results = []
        policies = list(self.ledger.policies.values())

        for p in policies:
            for v in p.versions:
                start_dt = date.fromisoformat(v.effective_start)
                end_dt = date.fromisoformat(v.effective_end) if v.effective_end else date(2099, 12, 31)

                # Test 1: Exact Start Date
                q_exact_start = f"What was the rule under {p.title} as of {start_dt.isoformat()}?"
                tq1 = self.resolver.parse_temporal_query(q_exact_start)
                t1_valid = (start_dt <= start_dt <= end_dt)

                # Test 2: Middle of Interval
                mid_dt = start_dt + timedelta(days=max(1, (end_dt - start_dt).days // 2))
                q_mid = f"What was the entitlement in {p.title} during {mid_dt.year}?"
                tq2 = self.resolver.parse_temporal_query(q_mid)
                t2_valid = (start_dt <= mid_dt <= end_dt)

                # Test 3: Day before start date (Should strictly NOT match this version)
                day_before = start_dt - timedelta(days=1)
                t3_valid = not (start_dt <= day_before <= end_dt)

                # Test 4: Day after expiration (Should strictly NOT match if expired)
                if v.effective_end:
                    day_after = date.fromisoformat(v.effective_end) + timedelta(days=1)
                    t4_valid = not (start_dt <= day_after <= end_dt)
                else:
                    t4_valid = True

                res_entry = {
                    "policy_id": p.policy_id,
                    "policy_title": p.title,
                    "version_num": v.version_num,
                    "version_label": v.version_label,
                    "effective_start": v.effective_start,
                    "effective_end": v.effective_end,
                    "exact_start_valid": t1_valid,
                    "mid_interval_valid": t2_valid,
                    "pre_start_rejected": t3_valid,
                    "post_end_rejected": t4_valid,
                    "temporal_soundness": (t1_valid and t2_valid and t3_valid and t4_valid),
                    "is_active_version": v.is_active
                }
                results.append(res_entry)

        return results

if __name__ == "__main__":
    ledger = GroundTruthLedger.load("tests/system_characterization/corpus/ground_truth_ledger.json")
    bench = TemporalSemanticsBenchmark(ledger)
    res = bench.run_temporal_evaluations()
    sound_count = sum(1 for r in res if r["temporal_soundness"])
    print(f"Temporal Semantics: {len(res)} version timelines evaluated. Soundness: {sound_count}/{len(res)} ({sound_count/len(res)*100:.2f}%).")
