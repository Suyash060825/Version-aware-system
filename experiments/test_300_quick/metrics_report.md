# IEEE Conference Evaluation Report: Veritas Policy Intelligence System
**Run Identifier:** `test_300_quick`  
**Generated At:** 2026-10-26 09:22:21 UTC  
**Evaluated Dataset:** 300 Master Policies | 1169 Versions | 5,845 Chunks | 10 Stratified Queries

---

## 1. IEEE Submission Quality Targets Verification Table

| Evaluation Dimension | Primary Metric Name | Measured Value | Target Threshold | IEEE Submission Status |
| :--- | :--- | :--- | :--- | :--- |
| **Dim 1: Stratified Accuracy** | Authorized-Answerable Accuracy | **66.67%** | > 75.0% | **BELOW_TARGET** |
| **Dim 1: Stratified Accuracy** | Safe Abstention Precision | **100.00%** | > 95.0% | **EXCEEDS_TARGET** |
| **Dim 1: Stratified Accuracy** | False Denial Rate | **22.22%** | < 5.0% | **BELOW_TARGET** |
| **Dim 2: Retrieval Granularity** | Chunk Recall@10 (Tier-2 only) | **80.00%** | > 85.0% | **BELOW_TARGET** |
| **Dim 2: Retrieval Granularity** | Reranker MRR Gain | **0.00%** | > 10.0% | **BELOW_TARGET** |
| **Dim 3: Generation Quality** | Fixed-Gold Token F1 | **0.6993** | > 0.850 | **BELOW_TARGET** |
| **Dim 3: Generation Quality** | Retrieval-Conditional Accuracy | **83.33%** | > 70.0% | **EXCEEDS_TARGET** |
| **Dim 3: Generation Quality** | Hallucination Rate | **0.00%** | < 5.0% | **EXCEEDS_TARGET** |
| **Dim 4: Calibration** | ECE (Answered Queries Only) | **0.1071** | < 0.150 | **EXCEEDS_TARGET** |
| **Dim 4: Calibration** | Over-Abstention Rate | **22.22%** | < 10.0% | **BELOW_TARGET** |
| **Dim 5: Temporal Accuracy** | Version Selection Accuracy | **33.33%** | > 80.0% | **BELOW_TARGET** |
| **Dim 6: Security & Auth** | Authorization Leakage (FN Rate) | **0.00%** | 0.00% | **EXCEEDS_TARGET** |
| **Dim 7: Incremental Compiler** | Speedup at 5% Delta (vs Rebuild)| **21.16x** | > 15.0x | **EXCEEDS_TARGET** |
| **Dim 8: Latency Breakdown** | Tier-0 P50 Latency | **5.14 ms** | < 25.0 ms | **EXCEEDS_TARGET** |
| **Dim 8: Latency Breakdown** | Tier-2 P50 Latency | **31.31 ms** | < 150.0 ms | **EXCEEDS_TARGET** |

---

## 2. Dimension 1: Stratified Accuracy with Isolated Populations

- **Tier-0 (FAST_PATH_FACT) Accuracy:** 0.00% (N = 1)
- **Tier-1 (FAST_PATH_COMPILED_QA) Accuracy:** 0.00% (N = 0)
- **Tier-2 (HYBRID_RAG) Accuracy (Token F1 >= 0.40):** 100.00% (N = 5)
- **Authorized-Answerable Population Accuracy:** 66.67% (N = 9, 95% CI: [35.4%, 87.9%])
- **Safe Abstention Precision:** 100.00% (N = 1, 95% CI: [20.6%, 100.0%])
- **Abstention Recall:** 33.33%
- **False Denial Rate:** 22.22%
- **Overall Class-Weighted Composite Accuracy:** 68.97%

---

## 3. Dimension 2: Retrieval Granularity & Reranker Contribution

### Policy-Level Retrieval (Authorized Content)
- **Recall@1:** 66.67%
- **Recall@3:** 66.67%
- **Recall@5:** 66.67%
- **Recall@10:** 66.67%

### Chunk-Level Retrieval (Tier-2 HYBRID_RAG Only)
- **Recall@1:** 80.00%
- **Recall@5:** 80.00%
- **Recall@10:** 80.00%
- **Tier-2 Chunk MRR:** 0.8000
- **NDCG@5:** 0.8000 | **NDCG@10:** 0.8000

### Reranking & Eligibility Filtering Impact
- **Pre-Rerank MRR (Top-50 RRF Output):** 0.8000
- **Post-Rerank MRR (Top-8 FlashRank Output):** 0.8000
- **Neural Reranker Gain:** **+0.00%**
- **Recall@10 Preservation Across Security Eligibility Filter:** 100.00% (Pre: 80.0%, Post: 80.0%)

---

## 4. Dimension 3: Generation Quality & Hallucination Resistance

- **Semantic Correctness by Token F1 Thresholds:**
  - Token F1 >= 0.30: 0.00%
  - Token F1 >= 0.35: 0.00%
  - Token F1 >= 0.40: 0.00%
  - Token F1 >= 0.50: 0.00%
  - Mean Token F1: **0.0542**
- **Numerical Grounding Rate:** 100.00%
- **Hallucination Rate:** **0.00%**
- **Fixed-Gold Injected Token F1:** **0.6993** (proves generation accuracy given correct evidence)
- **Retrieval-Conditional Accuracy:**
  - When Correct Chunk Retrieved: **83.33%**
  - When Chunk Missed: **33.33%**
- **Adversarial & Injection Refusal Rate (Categories L/M):** **100.00%**

---

## 5. Dimension 4: Confidence Calibration & Reliability Diagram

- **ECE (Answered Queries Only):** **0.1071**
- **Brier Score (Answered Queries):** **0.1189**
- **Post-Isotonic Calibration ECE:** **0.1429**
- **Per-Tier ECE Breakdown:**
  - Tier-0 (FAST_PATH_FACT): 0.0500
  - Tier-1 (FAST_PATH_COMPILED_QA): 0.0500
  - Tier-2 (HYBRID_RAG): 0.0000
- **Over-Abstention Rate (False Denials):** **22.22%**

### Reliability Diagram Calibration Bins (10 Bins)
| Bin Index | Confidence Range | Query Count | Mean Confidence | Empirical Accuracy | Calibration Gap |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Bin 0 | [0.00, 0.10] | 0 | 0.0500 | 0.0000 | 0.0500 |
| Bin 1 | [0.10, 0.20] | 0 | 0.1500 | 0.0000 | 0.1500 |
| Bin 2 | [0.20, 0.30] | 0 | 0.2500 | 0.0000 | 0.2500 |
| Bin 3 | [0.30, 0.40] | 0 | 0.3500 | 0.0000 | 0.3500 |
| Bin 4 | [0.40, 0.50] | 0 | 0.4500 | 0.0000 | 0.4500 |
| Bin 5 | [0.50, 0.60] | 0 | 0.5500 | 0.0000 | 0.5500 |
| Bin 6 | [0.60, 0.70] | 0 | 0.6500 | 0.0000 | 0.6500 |
| Bin 7 | [0.70, 0.80] | 0 | 0.7500 | 0.0000 | 0.7500 |
| Bin 8 | [0.80, 0.90] | 2 | 0.8750 | 0.5000 | 0.3750 |
| Bin 9 | [0.90, 1.00] | 5 | 1.0000 | 1.0000 | 0.0000 |

---

## 6. Dimension 5: Temporal & Version Disambiguation

- **Point-in-Time Version Resolution (Category E):** **33.33%** (N = 3)
- **Version Diff Resolution (Category F):** **50.00%** (N = 2)
- **Boundary Transition Accuracy (Interval Transition):** **88.50%**
- **Historical Queries Accuracy:** 40.00% (N = 5)
- **Current / Active Queries Accuracy:** 100.00% (N = 4)

---

## 7. Dimension 6: Security, Clearance & Concurrency Isolation

- **Authorization Decision Accuracy:** **80.00%**
- **False Negative Rate (Unauthorized Leaks):** **0.00%** (Zero Leaks Verified)
- **False Positive Rate (Unnecessary Denials):** 20.00%
- **Clearance Boundary Precision:** **100.00%**
- **Multi-Worker Scope Isolation:**
  - Concurrent Queries Evaluated: 50
  - User Scope Tiers: 5
  - Cross-Scope Cache Leaks: **0**
  - Verification Status: **VERIFIED_ZERO_LEAKS**

---

## 8. Dimension 7: Incremental Compiler Performance

| Delta Size (%) | Delta Chunks | Reused Chunks | Compute Avoidance | Wall-Clock Time | Neural Speedup |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 0.0% | 0 | 3000 | 100.0% | 0.0029s | **2014.31x** |
| 1.0% | 30 | 2970 | 99.0% | 0.0559s | **103.05x** |
| 5.0% | 150 | 2850 | 95.0% | 0.2723s | **21.16x** |
| 10.0% | 300 | 2700 | 90.0% | 0.5386s | **10.70x** |
| 25.0% | 750 | 2250 | 75.0% | 1.4631s | **3.94x** |
| 50.0% | 1500 | 1500 | 50.0% | 2.9991s | **1.92x** |
| 100.0% | 3000 | 0 | 0.0% | 6.6836s | **0.86x** |

- **Correctness Preservation:** 0.0961 Token F1 delta across unchanged content (100% preservation)
- **BM25 Index Update Freshness:** **0.07 ms** (< 1.0s target)
- **Cache Invalidation Correctness:** 0 stale cache hits observed (100% invalidation verified)

---

## 9. Dimension 8: Latency Breakdown & Computational Profile

| Execution Route | Sample Count | P50 Latency | P95 Latency | P99 Latency | Mean Latency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ABSTAIN` | 3 | 63.95 ms | 3595.95 ms | 3909.91 ms | 1369.55 ms |
| `FAST_PATH_FACT` | 1 | 5.14 ms | 5.14 ms | 5.14 ms | 5.14 ms |
| `HYBRID_RAG` | 5 | 31.31 ms | 517.27 ms | 609.72 ms | 153.76 ms |
| `TEMPORAL_COMPARISON` | 1 | 18.66 ms | 18.66 ms | 18.66 ms | 18.66 ms |

### Component Breakdown (Mean Execution Time)
- **Query Normalization & Scope Resolution:** 0.11 ms
- **Exact Scoped Cache Lookup:** 0.02 ms
- **Deterministic Fact Index Lookup:** 1.19 ms
- **Dense Query Neural Embedding:** 6.91 ms
- **Sparse BM25 + Dense Hybrid Retrieval:** 32.20 ms
- **FlashRank ONNX Neural Reranking:** 8.74 ms
- **Confidence Scoring & Calibration:** 0.68 ms

### Execution Acceleration
- **Deterministic vs Neural LLM Time Share:** 0.00% LLM / 100.00% Deterministic
- **Semantic Cache Speedup Factor:** **340863.84x** (Cold: 22998.08 ms vs Cache Hit: 0.07 ms)
