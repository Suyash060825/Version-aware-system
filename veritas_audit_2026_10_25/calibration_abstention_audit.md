# Veritas Calibration & Abstention Audit

**Audit Date:** 2026-10-25 | **Branch:** `improv` / `0ebae05`

---

## 1. Confidence Engine Scoring Mechanics

### 1.1 Formula & Components
**File:** [`rag/verification/confidence.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/verification/confidence.py)

The confidence score is computed as:
$$\text{Raw Final} = 0.55 \cdot \text{Retrieval Conf} + 0.45 \cdot \text{Evidence Coverage}$$

1. **Retrieval Confidence (`_retrieval_confidence`):**
   - For `score_type == "rerank_prob"`: clamped maximum score across top chunks (`min(1.0, max(0.0, raw_max))`).
   - For `score_type == "rrf"`: `raw_max / 0.0328`.
2. **Evidence Coverage (`_evidence_coverage`):**
   - Computes stemmed word and bigram overlap between query words (excluding 30 stopwords) and chunk text.
   - If no substantive query words exist, returns a high baseline of `0.85`.

---

## 2. Isotonic Calibration Analysis & Data-Leakage Finding

### 2.1 Runtime Piecewise Interpolation
Lines 88–97 embed hardcoded knot points:
```python
knots = [
    (0.00, 0.00),
    (0.20, 0.08),
    (0.35, 0.20),
    (0.50, 0.35),
    (0.70, 0.52),
    (0.85, 0.72),
    (0.95, 0.88),
    (1.00, 0.96)
]
```
- This transformation is applied unconditionally inside `ConfidenceEngine.score()`.
- The values are hand-tuned knots, not dynamically fitted parameters.

### 2.2 The Post-Calibration ECE Paradox (0.0851 vs 0.1696)
In `experiments/ieee_publication_v1/comprehensive_metrics.json`:
- `ece_answered_only`: **0.0851**
- `post_calibration_ece`: **0.1696** (ECE worsened by 99.3%!)

**Root Cause:**
1. In `run_comprehensive_eval.py`, the evaluation harness fits an `IsotonicRegression` model directly on the 91 evaluated queries, and re-evaluates calibration error on the exact same 91 samples without an independent train/calibration split.
2. The empirical accuracy distribution in the 91 queries is extreme:
   - Bin 6 ([0.6, 0.7]): 1 query, accuracy 0.0.
   - Bin 7 ([0.7, 0.8]): 2 queries, accuracy 1.0.
   - Bin 8 ([0.8, 0.9]): 78 queries, accuracy 0.9744.
   - Bin 9 ([0.9, 1.0]): 10 queries, accuracy 0.9000.
3. Fitting isotonic regression on a dataset with only 4 occupied bins (and 78 out of 91 samples in Bin 8) results in severe step-function distortion that overfits the single outlier error in Bin 6, worsening the ECE metric on evaluation.

---

## 3. Abstention Logic & Safety Bounds

### 3.1 Abstention Gate (`confidence.py:58–69`)
```python
if score_type == "rerank_prob" and raw_max > 0.60:
    abstain = False
    abstain_reason = "reranker_override"
elif (final < self.LOW_THRESHOLD) and (retrieval_conf < 0.20 or coverage_conf < 0.10):
    abstain = True
```
- **Reranker Override:** If any retrieved chunk has a reranker score > 0.60, abstention is suppressed, even if evidence coverage is 0.
- **Dual Floor:** Abstention requires **both** `final < 0.20` AND (`retrieval_conf < 0.20` OR `coverage_conf < 0.10`). If a query retrieves a completely irrelevant chunk with an artifactual score of 0.21, the system refuses to abstain and generates an answer.
