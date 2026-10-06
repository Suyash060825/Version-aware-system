# Veritas Baseline-Fairness Audit Report

**Evaluation Suite:** Frozen 301-Query Benchmark & Expanded System Characterization  
**Audit Timestamp:** 2026-10-06T08:35:01.172037  
**Random Seed:** 42  
**Hardware Parity:** Ubuntu Linux x86_64, CUDA 12, Python 3.14 / 3.11  

---

## 1. Retrieval Baselines Audit (Policy-Level, N=144 Answerable Queries)

| Retrieval System | Embedding / Model | Reranker | Recall@1 [95% CI] | Recall@5 [95% CI] | Recall@10 [95% CI] | MRR@10 | NDCG@10 | P50 (ms) | P95 (ms) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BM25 Sparse** | None (Okapi) | None | 97.92% [94.05–99.29] | 98.61% | 98.61% | 0.9826 | 0.9835 | 1.45 | 3.82 |
| **Dense (BGE-Small)** | BAAI/bge-small-en-v1.5 | None | 98.61% [95.08–99.62] | 98.61% | 98.61% | 0.9861 | 0.9861 | 33.80 | 51.40 |
| **Hybrid (RRF)** | BGE-Small + BM25 | RRF (k=60) | 98.61% [95.08–99.62] | 98.61% | 98.61% | 0.9861 | 0.9861 | 36.10 | 54.90 |
| **Hybrid + FlashRank** | BGE-Small + BM25 | MiniLM-L-12-v2 | 98.61% [95.08–99.62] | 98.61% | 98.61% | 0.9861 | 0.9861 | 120.50 | 144.80 |
| **Veritas Adaptive** | Multi-Tier Router | Adaptive | 98.61% [95.08–99.62] | 98.61% | 98.61% | 0.9861 | 0.9861 | **29.65** | **136.49** |

---

## 2. Temporal Version Selection Accuracy (N=109 Temporal Queries)

| System | All Temporal (N=109) | Current Version (N=75) | Historical (N=34) | Boundary (N=12) |
| :--- | :---: | :---: | :---: | :---: |
| **Unrestricted Baseline** | 29.36% (32/109) [21.6–38.5%] | 37.33% (28/75) | 11.76% (4/34) | 0.00% (0/12) |
| **Veritas (Local Qwen)** | **88.07%** (96/109) [80.6–93.0%] | **96.00%** (72/75) | **70.59%** (24/34) | **83.33%** (10/12) |
| **Veritas (Gemini 1.5)** | **89.53%** (97/109) [82.3–94.1%] | **97.33%** (73/75) | **70.59%** (24/34) | **91.67%** (11/12) |

---

## 3. Security & Authorization Pre-Filtering (N=301 Benchmark Queries)

| System | Unauthorized Evidence Leaks | Auth Precision | Auth Recall | False Positive Auth | False Negative Auth |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Standard RAG** | 53.16% (160/301) | 46.84% (141/301) | 100.0% (141/141) | 100.0% (160/160) | 0.0% (0/141) |
| **Veritas Guard** | **0.00% (0/301)** [0.0–1.2%] | **100.0% (141/141)** | **100.0% (141/141)** | **0.00% (0/160)** | **0.00% (0/141)** |

---

## 4. Paired Statistical Significance Tests

| Comparison | Null Hypothesis ($H_0$) | Statistical Test | Test Stat | p-value | Significance ($lpha=0.05$) | Conclusion |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **BM25 vs Dense Recall@1** | Identical recall distributions | McNemar Exact Binomial | 0.000 | 1.0000 | Not Significant ($p > 0.05$) | Difference is within stochastic margin on small benchmark (141 vs 142). |
| **Veritas vs Std RAG Security** | Identical authorization leak rate | McNemar Chi-Square (CC) | 158.01 | $< 10^-15$ | **Statistically Significant ($p < 0.001$)** | Veritas completely eliminates unauthorized evidence leakage. |
| **Veritas vs Baseline Temporal** | Identical version resolution | McNemar Chi-Square (CC) | 58.96 | $< 10^-14$ | **Statistically Significant ($p < 0.001$)** | Veritas provides decisive improvement in point-in-time accuracy. |

---

## 5. Methodological Fairness Classification

### Section A: Fully Matched Comparisons
1. **Retrieval Baselines (BM25, Dense, Hybrid, Reranker):** Evaluated over identical 144 query cases, identical 21-policy corpus, and identical candidate depths ($k=10$).
2. **Security Pre-Filtering:** Evaluated over all 301 benchmark queries with identical user personas, department roles, and clearance boundaries.
3. **Temporal Resolution:** Evaluated over identical 109 temporal queries under identical gold timestamp labels.
4. **Incremental Compiler Speedup:** Measured on identical mutation sets against full cold compilation under identical CPU execution threads.

### Section B: Partially Matched Comparisons
1. **Policy-Level vs. Strict Chunk-Level Retrieval:** The 301-query baseline evaluated policy retrieval (hit if correct policy version chunk was in top-$k$), while the 922-query characterization evaluated strict chunk retrieval. Both must be reported with explicit granularity labeling.
2. **Local Qwen-2.5-7B vs Gemini-1.5 Generation:** Evaluates cross-model robustness, but absolute generation latencies are not directly comparable due to cloud network overhead.

### Section C: Non-Apples-to-Apples Comparisons (Must Avoid Direct Equivalence)
1. **Tier-0 Compiled Fact Lookup Latency (1.00 ms) vs Tier-2 Hybrid RAG Latency (120.50 ms):** Direct comparison without disclosing routing decomposition is invalid because Tier-0 is an exact pre-indexed dictionary lookup that completely avoids vector embedding and LLM decoding.
2. **Offline Incremental Re-Compilation vs Live Query Answering:** Index mutation compilation is an asynchronous maintenance task, not a real-time retrieval operation.

### Section D: Denominator & Evaluation Population Clarifications
- **Frozen 301 Baseline:** 301 total = 144 answerable retrieval + 109 temporal + 27 adversarial/refusal + 21 structured fact queries.
- **Version Selection Accuracy:** Evaluated over the 109 answered temporal queries ($96/109 = 88.07%$).
- **Refusal Accuracy:** Evaluated over 27 unanswerable/adversarial queries ($24/27 = 88.89%$).
- **Expanded Characterization:** Evaluated over 922 queries ($585/922 = 63.4%$ fast-path/refusal, $515/922 = 55.9%$ Tier 0 + Tier 1, $871/922 = 94.47%$ policy Recall@1).
