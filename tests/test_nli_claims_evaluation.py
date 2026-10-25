import os
import pytest
from rag.verification.entailment import EntailmentVerifier
from tests.expanded_characterization.nli_eval_suite import NLIDatasetSynthesizer

def test_nli_claim_level_verification_100():
    os.environ['ENTAILMENT_ENABLED'] = 'true'
    verifier = EntailmentVerifier()

    # Generate 120 claims across 16 phenomena
    ds = NLIDatasetSynthesizer(seed=42).synthesize_dataset(120)
    claims = ds[:100]

    contra_tp, contra_fp, contra_fn, contra_tn = 0, 0, 0, 0
    unsupp_tp, unsupp_fp, unsupp_fn, unsupp_tn = 0, 0, 0, 0

    for item in claims:
        chunk = [{'text': item.premise, 'chunk_id': 'c1', 'title': 'Test Policy', 'version': '1.0'}]
        res = verifier.verify(item.hypothesis, chunk)
        pred = res.verdict.lower()
        gold = item.gold_label.lower()

        # Contradiction metrics
        if gold == "contradiction":
            if pred == "contradiction":
                contra_tp += 1
            else:
                contra_fn += 1
        else:
            if pred == "contradiction":
                contra_fp += 1
            else:
                contra_tn += 1

        # Unsupported / Neutral metrics
        if gold in ("neutral", "unknown"):
            if pred == "unknown":
                unsupp_tp += 1
            else:
                unsupp_fn += 1
        else:
            if pred == "unknown":
                unsupp_fp += 1
            else:
                unsupp_tn += 1

    contra_prec = contra_tp / (contra_tp + contra_fp) if (contra_tp + contra_fp) > 0 else 0.0
    contra_rec = contra_tp / (contra_tp + contra_fn) if (contra_tp + contra_fn) > 0 else 0.0

    print(f"\n--- NLI Verification 100-Claim Held-out Results ---")
    print(f"Contradiction: TP={contra_tp}, FP={contra_fp}, FN={contra_fn}, Precision={contra_prec:.3f}, Recall={contra_rec:.3f}")
    print(f"Unsupported Claims: TP={unsupp_tp}, FP={unsupp_fp}, FN={unsupp_fn}")

    # Acceptance criteria: Safe separation of contradictions without silent bypass
    assert contra_tp > 0
    assert contra_prec >= 0.70
