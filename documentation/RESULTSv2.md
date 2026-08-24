# Experimental Results & Performance Evaluation (v2)

**Evaluation Date**: 2026-08-24  
**Benchmark Suite**: 301 Held-Out Test Cases across 12 Policy Categories  
**Execution Environment**: Linux x86_64, Python 3.14, FastEmbed (`BAAI/bge-small-en-v1.5`), FlashRank (`ms-marco-TinyBERT-L-2-v2`), FAISS HNSW SegmentOverlay, ChromaDB, DeBERTa-v3 NLI.

---

## 1. Information Retrieval Performance

Retrieval evaluation across 301 test queries comparing dense bi-encoders, sparse BM25, Reciprocal Rank Fusion (RRF), and cross-encoder FlashRank reranking:

| Retriever Architecture | MRR@5 | NDCG@5 | Hit@1 | Hit@3 | Hit@5 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Dense Bi-Encoder (`bge-small-en-v1.5`) | 0.9905 | 0.9911 | 0.9896 | 0.9896 | 0.9931 |
| Sparse Index (`Partitioned BM25`) | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Hybrid Retrieval (`RRF` Dense + BM25) | 0.9905 | 0.9911 | 0.9896 | 0.9896 | 0.9931 |
| **Hybrid + FlashRank Reranker (Proposed)** | **0.9931** | **0.9931** | **0.9931** | **0.9931** | **0.9931** |

---

## 2. Real Latency Breakdown by Routing Tier

Empirically measured response latency (ms) across execution paths:

| Pipeline Route | Query Count | Mean (ms) | P50 (ms) | P95 (ms) | P99 (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `FAST_PATH_FACT` (Level 0 SQL Lookup) | 245 | 18.72 | 18.36 | 26.27 | 33.23 |
| `HYBRID_RAG` (Level 2 Hybrid + FlashRank) | 40 | 110.21 | 110.00 | 136.28 | 152.56 |
| `ABSTAINED` (Safety Refusal Gate) | 16 | 102.49 | 100.10 | 126.70 | 137.82 |
| **End-to-End System (Composite)** | **301** | **35.33** | **20.03** | **116.86** | **136.18** |

---

## 3. Dynamic Ablation Study

Empirical measurement of full system versus isolated component removal:

| Ablation Configuration | P50 Latency (ms) | P95 Latency (ms) | Answer F1 (%) | Citation F1 (%) | LLM Calls / 30 Queries |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **B7 (Proposed Full System)** | **88.93** | **122.66** | **36.40** | **30.30** | **0** |
| A1 (w/o Knowledge Compiler) | 42.10 | 57.68 | 24.17 | 10.00 | 30 |
| A2 (w/o Fact Resolver) | 84.98 | 107.34 | 36.40 | 30.30 | 0 |
| A3 (w/o Compiled QA) | 85.50 | 105.14 | 36.40 | 30.30 | 0 |
| A4 (w/o Temporal Resolver) | 89.75 | 113.39 | 36.40 | 30.30 | 0 |
| A5 (w/o FlashRank Reranker) | 90.52 | 108.68 | 36.40 | 30.30 | 0 |
| A6 (w/o Confidence Gate) | 88.45 | 108.99 | 36.40 | 30.30 | 0 |
| A7 (w/o Multi-Tier Cache) | 88.44 | 113.39 | 36.40 | 30.30 | 0 |

---

## 4. Scalability & ANN Benchmark

Evaluation of FAISS HNSW Segment Overlay vs Brute-Force Flat inner-product across vector collection sizes ($d = 384$):

| Vector Count ($N$) | Build Time (ms) | Memory Size (MB) | HNSW P50 (ms) | HNSW P95 (ms) | Flat P50 (ms) | HNSW Recall@5 (%) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 100 | 3.20 | 0.17 | 0.028 | 0.055 | 0.015 | 100.0% |
| 500 | 18.09 | 0.85 | 0.035 | 0.050 | 0.027 | 90.0% |
| 2,000 | 49.93 | 3.42 | 0.086 | 0.103 | 0.113 | 65.6% |
| 10,000 | 399.33 | 17.09 | 0.181 | 0.269 | 0.876 | 22.8% |

---

## 5. Incremental Delta Update vs Global Rebuild

| Update Strategy | Measured Execution Time (ms) | Re-Indexed Chunks | Re-Embedded Items | Complexity |
| :--- | :---: | :---: | :---: | :---: |
| **Incremental Delta Update (Ours)** | **0.14 ms** | **6 chunks** | **6 items** | **$\mathcal{O}(\|\Delta\|)$ Segment Overlay** |
| Full Global Rebuild (Baseline) | 2,433.39 ms | 127 chunks | 356 items | $\mathcal{O}(N)$ Complete Rebuild |
| **Measured Speedup** | **17,381.3x** | - | - | - |

---

## 6. Multi-Tier Cache Safety Verification Suite

| Safety Invariant Test | Condition Tested | Violation Count | Unsafe Rate |
| :--- | :--- | :---: | :---: |
| Department Isolation | Finance user query repeated by HR user | 0 / 1 | 0.00% |
| Version Invalidation | Query repeated post-targeted version invalidation | 0 / 1 | 0.00% |
| Scope Containment | Cross-user session query isolation | 0 / 1 | 0.00% |
| **Total Unsafe Served Rate** | - | **0 / 3** | **0.00%** |

---

## 7. Confidence Calibration & NLI Grounding Verification

- **Brier Calibration Score**: 0.7043
- **Expected Calibration Error (ECE)**: 0.2845
- **DeBERTa-v3 NLI Grounding Rate**: 83.33% (5 / 6 domain pairs correctly verified)
- **Safety Abstention Rate on Adversarial / Unanswerable Queries**: 69.23% (9 / 13)
