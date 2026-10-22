# Veritas Research & Benchmark Executive Summary

## 1. Submission Recommendation: CONDITIONAL GO
- **Status:** **CONDITIONAL GO**
- **Condition:** The paper must adopt the reconciled metrics established in this audit. Specifically:
  1. Distinguish **Policy Recall@1 (94.47%)** from **End-to-End Answer Correctness (53.60%)** and **Chunk Recall@1 (19.10%)**.
  2. Revise the incremental compilation speedup from the historical **24.95x** to the measured **22.41x** (or 19.32x end-to-end transaction pipeline).
  3. Frame security results as **zero observed leaks in 3,840 tested multi-tenant cases (95% CI upper bound 0.08%)**, avoiding unprovable claims of universal cryptographic immunity.

## 2. Authoritative Benchmark Run
- **Newest Authoritative Suite:** `evaluation/run_benchmark.py` (36-category comprehensive evaluation suite).
- **Corpus Hierarchy:** 120 policies, 422 versions, 2,110 chunks, 422 facts, 422 canonical QA pairs.
- **Workload:** 1,000 queries across 20 active query categories, 3,840 security clearance trials, 4 indexing scale sweeps (up to 5,000 policies / 87,800 chunks), and 5 worker concurrency tiers.
- **Git Commit:** `945bb8e2ac0a682d65610b09f74b439a23b7b2be` on branch `improv`.

## 3. Full-Stack Application & Model Verification
- **Container Topology:** 6 Docker Compose services running and healthy (`postgres`, `redis`, `ollama`, `celery_worker`, `web`, `nginx`).
- **Local Model Serving:** Local Ollama container serving `qwen3:4b-q4_K_M` (digest `2bfd38a7daaf4b1037efe517ccb73d1a3bbd4822cf89f1a82be1569050a114e0`).
- **End-to-End Verification:** Succeeded. A real user query sent through the application runtime (`get_query_engine()`) successfully routed via `HYBRID_RAG`, retrieved policy evidence, executed local Ollama generation with thinking tag suppression, and returned a grounded response with 0.9588 confidence.

## 4. Key Recomputed Metrics Summary
| Metric Name | Observed Value | Denominator / Basis | 95% Wilson Score CI |
| :--- | :--- | :--- | :--- |
| **Overall Answer Correctness** | **53.60%** | 536 / 1,000 queries | [50.50%, 56.67%] |
| **Mean Token F1** | **0.3542** | 1,000 queries | N/A |
| **Unauthorized Evidence Leakage** | **0.00%** | 0 / 3,840 evaluations | [0.0000%, 0.0999%] |
| **Authorization Decision Accuracy** | **100.00%** | 3,840 / 3,840 evaluations | [99.90%, 100.00%] |
| **Incremental Compute Avoidance** | **95.00%** | 2,850 / 3,000 chunks | [94.16%, 95.73%] |
| **Incremental Compilation Speedup** | **22.41x** | 5.3988s cold / 0.2409s inc | N/A |
| **Policy-Level Recall@1** | **94.47%** | 871 / 922 eligible queries | [92.79%, 95.80%] |
| **Chunk-Level Recall@1** | **19.10%** | 191 / 1,000 queries | [16.78%, 21.66%] |
| **Deterministic Fast-Path P50 Latency**| **28.20 ms** | Fast-path query subset | N/A |
| **Validation ECE (Calibrated)** | **0.0410** | Held-out validation split | [0.028, 0.056] |
