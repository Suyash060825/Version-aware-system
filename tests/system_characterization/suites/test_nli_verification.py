"""
tests/system_characterization/suites/test_nli_verification.py
Evaluation of Veritas NLI & Grounding Verification Engine.
Tests entailment detection, numerical contradictions, temporal contradictions, negation contradictions, and ungrounded hallucinations.
"""
import sys
import os
import time
from typing import List, Dict, Any, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from rag.verification.entailment import EntailmentVerifier
from tests.system_characterization.corpus.ground_truth_ledger import GroundTruthLedger

class NLIVerificationBenchmark:
    def __init__(self, ledger: GroundTruthLedger):
        self.ledger = ledger
        self.verifier = EntailmentVerifier()

    def run_nli_tests(self) -> List[Dict[str, Any]]:
        results = []

        test_pairs = [
            # 1. Direct Factual Entailment
            {
                "id": "NLI-01",
                "type": "ENTAILMENT",
                "evidence": "Employees are entitled to 24 days of annual leave per calendar year accrued at 2 days per month.",
                "answer": "According to the policy, employees receive 24 days of annual leave annually.",
                "expected_verdict": "ENTAILMENT",
                "expected_grounded": True
            },
            # 2. Numerical Contradiction
            {
                "id": "NLI-02",
                "type": "NUMERICAL_CONTRADICTION",
                "evidence": "The standard domestic hotel limit is set to INR 7000 per night for metro cities.",
                "answer": "Employees can claim up to INR 15000 per night for domestic hotels.",
                "expected_verdict": "CONTRADICTION",
                "expected_grounded": False
            },
            # 3. Negation Contradiction
            {
                "id": "NLI-03",
                "type": "NEGATION_CONTRADICTION",
                "evidence": "Unapproved international travel expenses are strictly non-reimbursable.",
                "answer": "Employees may claim reimbursement for unapproved international travel without restriction.",
                "expected_verdict": "CONTRADICTION",
                "expected_grounded": False
            },
            # 4. Temporal Contradiction
            {
                "id": "NLI-04",
                "type": "TEMPORAL_CONTRADICTION",
                "evidence": "Effective from 2024-07-01, paternity leave was increased to 10 days.",
                "answer": "Paternity leave was 10 days during the year 2020.",
                "expected_verdict": "CONTRADICTION",
                "expected_grounded": False
            },
            # 5. Unsupported / Hallucinated Extraneous Claim
            {
                "id": "NLI-05",
                "type": "UNSUPPORTED_CLAIM",
                "evidence": "Remote work is permitted up to 3 days per week with manager approval.",
                "answer": "Employees can work remotely up to 3 days per week and receive free organic lunches delivered home daily.",
                "expected_verdict": "UNKNOWN",
                "expected_grounded": False
            },
            # 6. Scope Contradiction
            {
                "id": "NLI-06",
                "type": "SCOPE_CONTRADICTION",
                "evidence": "This hardware refresh standard applies exclusively to Engineering personnel.",
                "answer": "All Sales and Marketing employees receive automatic annual hardware upgrades under this rule.",
                "expected_verdict": "CONTRADICTION",
                "expected_grounded": False
            },
            # 7. Partial Entailment with Multiple Claims
            {
                "id": "NLI-07",
                "type": "PARTIAL_ENTAILMENT",
                "evidence": "Password must be at least 12 characters and changed every 90 days.",
                "answer": "Passwords must be at least 12 characters, changed every 90 days, and written on a post-it note.",
                "expected_verdict": "UNKNOWN",
                "expected_grounded": False
            },
            # 8. Paraphrased Entailment
            {
                "id": "NLI-08",
                "type": "ENTAILMENT_PARAPHRASED",
                "evidence": "In the event of a data breach, the incident response coordinator must be alerted within 2 hours of discovery.",
                "answer": "Suspected security breaches require immediate notification to the incident coordinator within a 2-hour SLA.",
                "expected_verdict": "ENTAILMENT",
                "expected_grounded": True
            }
        ]

        for p in test_pairs:
            t0 = time.time()
            chunk_dict = [{"text": p["evidence"]}]
            res = self.verifier.verify(p["answer"], chunk_dict)
            latency_ms = (time.time() - t0) * 1000

            verdict_correct = (res.is_entailed == p["expected_grounded"])
            results.append({
                "test_id": p["id"],
                "test_type": p["type"],
                "evidence": p["evidence"],
                "answer": p["answer"],
                "expected_verdict": p["expected_verdict"],
                "actual_verdict": res.verdict,
                "entailment_score": res.score,
                "is_grounded": res.is_entailed,
                "expected_grounded": p["expected_grounded"],
                "verdict_correct": verdict_correct,
                "failed_claims": res.failed_claims,
                "latency_ms": latency_ms
            })

        return results

if __name__ == "__main__":
    ledger = GroundTruthLedger.load("tests/system_characterization/corpus/ground_truth_ledger.json")
    bench = NLIVerificationBenchmark(ledger)
    res = bench.run_nli_tests()
    correct = sum(1 for r in res if r["verdict_correct"])
    print(f"NLI Verification Suite: {correct}/{len(res)} correct verdicts.")
    for r in res:
        print(f"  {r['test_id']} ({r['test_type']:25s}) | Exp: {r['expected_verdict']:14s} | Act: {r['actual_verdict']:14s} | Score: {r['entailment_score']:.3f} | Correct: {r['verdict_correct']}")
