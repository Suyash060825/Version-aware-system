# IEEE Journal Publication Evaluation Report: Veritas Policy Intelligence System
**Run ID:** `veritas_300policy_ieee_final`  
**Corpus Scale:** 300 Master Policies | 1,169 Versions | 5,845 Chunks | 32 User Archetypes  
**Date:** 2026-10-27 06:43:44 UTC  

## 1. IEEE Primary Submission Targets Verification Table

| Metric Name | Measured Value | Target Threshold | IEEE Status |
| :--- | :--- | :--- | :--- |
| **Authorized-answerable accuracy** | **76.22%** | > 75.00% | **`MEETS_TARGET`** |
| **Safe abstention precision** | **29.73%** | > 95.00% | **`BELOW_TARGET`** |
| **False denial rate** | **0.23%** | < 5.00% | **`EXCEEDS_TARGET`** |
| **Error route count** | **0.0000** | < 0.0000 | **`EXCEEDS_TARGET`** |
| **LLM used rate (Tier-2)** | **98.20%** | > 95.00% | **`MEETS_TARGET`** |
| **Policy Recall@1 (eligible)** | **82.20%** | > 90.00% | **`BELOW_TARGET`** |
| **Chunk Recall@10 (Tier-2)** | **92.75%** | > 95.00% | **`BELOW_TARGET`** |
| **Reranker MRR gain** | **19.27%** | > 10.00% | **`EXCEEDS_TARGET`** |
| **Fixed-gold Token F1** | **0.9620** | > 0.8500 | **`EXCEEDS_TARGET`** |
| **Retrieval-conditional accuracy** | **97.60%** | > 70.00% | **`EXCEEDS_TARGET`** |
| **Hallucination rate** | **0.18%** | < 5.00% | **`EXCEEDS_TARGET`** |
| **ECE Population A (post-calib)** | **0.1865** | < 0.0500 | **`BELOW_TARGET`** |
| **ECE Population B (operational)** | **0.3677** | < 0.1000 | **`BELOW_TARGET`** |
| **Over-abstention rate** | **0.23%** | < 10.00% | **`EXCEEDS_TARGET`** |
| **NLI overall accuracy** | **100.00%** | > 90.00% | **`EXCEEDS_TARGET`** |
| **NLI false entailment rate** | **0.00%** | < 2.00% | **`EXCEEDS_TARGET`** |
| **Authorization leak rate** | **0.00%** | 0.00% | **`EXCEEDS_TARGET`** |
| **Compiler speedup at 5% delta** | **19.84x** | > 15.00x | **`EXCEEDS_TARGET`** |
| **Tier-3 diff F1** | **0.9733** | > 0.8000 | **`EXCEEDS_TARGET`** |
| **Tier-3 hallucination rate** | **0.00%** | 0.00% | **`EXCEEDS_TARGET`** |
| **Tier-0 P50** | **5.29 ms** | < 25.00 ms | **`EXCEEDS_TARGET`** |
| **Tier-2 P50** | **29.48 ms** | < 150.00 ms | **`EXCEEDS_TARGET`** |

---

## 2. Section 1: Main 3,000-Query Benchmark & Stratified Accuracy

- **Overall Accuracy:** 65.33% (95% CI: [63.57%, 67.04%])
- **Authorized-Answerable Accuracy:** 76.22% (N = 2208, 95% CI: [74.40%, 77.95%])
- **Tier-0 (FAST_PATH_FACT) Accuracy:** 74.65% (N = 1144)
- **Tier-1 (FAST_PATH_COMPILED_QA) Accuracy:** 80.12% (N = 342)
- **Tier-2 (HYBRID_RAG) Accuracy:** 90.85% (N = 459)
- **Tier-3 (TEMPORAL_COMPARISON) Accuracy:** 100.00% (N = 83)
- **Safe Abstention Precision:** 29.73% (N = 676, 95% CI: [26.41%, 33.29%])
- **False Denial Rate:** 0.23%
- **Abstention Recall:** 97.57%
- **Error Route Count:** 0
- **LLM Used Rate (Tier-2):** 98.20%

### Route Distribution (Total: 2,884 queries)

| Route Name | Query Count | Percentage |
| :--- | :--- | :--- |
| `FAST_PATH_FACT` | 1441 | 49.97% |
| `FAST_PATH_COMPILED_QA` | 507 | 17.58% |
| `HYBRID_RAG` | 467 | 16.19% |
| `TEMPORAL_COMPARISON` | 83 | 2.88% |
| `ABSTAIN` | 206 | 7.14% |
| `CACHE_HIT` | 180 | 6.24% |

---

## 3. Section 2: Retrieval Granularity & Security Filtering

### Policy-Level Retrieval (All Queries vs Eligible Subset)

| Metric | All Queries (N=2,884) | Eligible Subset (N=2197) |
| :--- | :--- | :--- |
| Policy Recall@1 | 76.21% | **82.20%** |
| Policy Recall@3 | 76.21% | **82.20%** |
| Policy Recall@5 | 76.21% | **82.20%** |
| Policy Recall@10 | 76.21% | **82.20%** |
| Policy MRR | 0.7621 | **0.8220** |
| Policy NDCG@10 | 0.7621 | **0.8220** |

### Chunk-Level Retrieval (Tier-2 HYBRID_RAG Only)

- **Chunk Recall@1:** 57.36%
- **Chunk Recall@3:** 77.80%
- **Chunk Recall@5:** 92.75%
- **Chunk Recall@10:** **92.75%**
- **Chunk MRR:** 0.6977
- **Chunk NDCG@5:** 0.9275 | **NDCG@10:** 0.9275
- **Reranker MRR Gain:** **+19.27%** (Pre: 0.7420 -> Post: 0.8850)
- **EvidenceFilter Preservation Ratio:** 1.0000 (100% authorized evidence preserved)


---

## 4. Section 4: Calibration & Reliability Analysis

- **Population A (In-Distribution Validation Split N=200):**
  - Pre-Calibration ECE: 0.1435 | Post-Calibration ECE: **0.1865**
  - Pre-Calibration Brier: 0.1663 | Post-Calibration Brier: **0.1892**
- **Population B (Full Benchmark with OOD/Adversarial):**
  - Raw ECE: 0.2988 | Operational ECE (Answered Only): **0.3677**
  - Raw Brier: 0.3504 | Operational Brier: **0.3689**

### Reliability Diagram Data (10 Bins - Population A Answered)

| Bin Index | Confidence Range | Count | Mean Confidence | Fraction Correct | Calibration Gap |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Bin 0 | [0.00, 0.10] | 0 | 0.0500 | 0.0000 | 0.0500 |
| Bin 1 | [0.10, 0.20] | 0 | 0.1500 | 0.0000 | 0.1500 |
| Bin 2 | [0.20, 0.30] | 0 | 0.2500 | 0.0000 | 0.2500 |
| Bin 3 | [0.30, 0.40] | 0 | 0.3500 | 0.0000 | 0.3500 |
| Bin 4 | [0.40, 0.50] | 0 | 0.4500 | 0.0000 | 0.4500 |
| Bin 5 | [0.50, 0.60] | 0 | 0.5500 | 0.0000 | 0.5500 |
| Bin 6 | [0.60, 0.70] | 0 | 0.6500 | 0.0000 | 0.6500 |
| Bin 7 | [0.70, 0.80] | 0 | 0.7500 | 0.0000 | 0.7500 |
| Bin 8 | [0.80, 0.90] | 0 | 0.8500 | 0.0000 | 0.8500 |
| Bin 9 | [0.90, 1.00] | 200 | 0.9965 | 0.8100 | 0.1865 |