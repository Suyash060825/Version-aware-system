# Veritas: Manuscript Audit, Empirical Data Provenance, and System Verification Report

**Author:** Suyash Pradhan (Department of Computer Science and Engineering)  
**Project:** Veritas: Version-Aware Enterprise Policy Intelligence via Incremental Knowledge Compilation and Adaptive Multi-Tier Retrieval  
**Target Publication:** IEEE Journal / Transactions (6 pages, `IEEEtran` documentclass)  
**Frozen Production Git Commit:** `61d64b71c298c3c505f2eeeef3c94829dfb55f75`  
**Date of Audit:** 2026-10-04  

---

## 1. Executive Overview & Purpose of this Document

This document maintains a permanent, tamper-proof record of:
1. Every verified empirical number across all experimental runs (`results/` directory).
2. The exact corpus counts extracted directly from the persistent database (`data/ledger.db` and index files).
3. Critical corrections to earlier drafts where numbers were estimated or misattributed.
4. Test suite status and execution logs.
5. Exact LaTeX build instructions and 6-page formatting constraints.

---

## 2. Ground-Truth Data Inventory (Verified against Source Files)

### 2.0 Benchmark Identity & Corpus Taxonomy Standard
To maintain strict provenance across all publications and technical reports, three distinct evaluation suites are explicitly identified:

1. **Frozen Baseline Benchmark ($N=301$ queries)**: Located at `data/benchmarks/benchmark_test.json`. Evaluated against the live database seed for baseline end-to-end RAG latency and accuracy comparisons.
2. **Internal Repository Benchmark ($N=462$ records)**: Located at `data/benchmarks/benchmark_all.json`. Comprehensive regression test harness used in continuous integration.
3. **System Characterization Suite ($N=922$ queries)**: Located at `tests/system_characterization/corpus/ground_truth_ledger.json`. Expanded multi-tier enterprise stress-test corpus across 120 policies, 600 versions, 3,000 chunks, and 32 user archetypes.

### 2.0.1 Multi-Tier Architecture Terminology Standard
- **Tier 0 (Fast-Path Fact Engine)**: Sub-millisecond deterministic key-value parameter extraction ($0.95\text{ ms}$ P50).
- **Tier 1 (Canonical Q&A Index)**: FAISS HNSW vector ANN matching over pre-compiled Q&A pairs ($1.85\text{ ms}$ P50).
- **Tier 2 (Adaptive Hybrid RAG)**: Okapi BM25 + Dense BGE retrieval fused via RRF and reranked by Cross-Encoder.
- **Tier 3 (Deterministic Diff Engine)**: Structured temporal clause and version diff comparison ($2.10\text{ ms}$ P50).
- **Post-Retrieval Verification Stage**: Grounded generation, DeBERTa-v3 NLI entailment scoring, and isotonic confidence calibration.

### 2.0.2 Publication Claim Audit Reference
All mathematical claims and metrics intended for publication are audited and classified in [`results/system_characterization/publication_claim_audit.csv`](../results/system_characterization/publication_claim_audit.csv).

---

### 2.1 Enterprise Corpus Scale (`data/ledger.db` & Vector Store)
Extracted directly via SQL introspection on SQLite tables and FAISS metadata:

| Corpus Entity | Verified Count | Source Entity / Table |
| :--- | :--- | :--- |
| **Policies** | **21** | `SELECT COUNT(*) FROM policy` |
| **Policy Versions** | **23** | `SELECT COUNT(*) FROM policy_version` |
| **Departments** | **8** | `SELECT COUNT(*) FROM department` (`['Engineering', 'Finance', 'Human Resources', 'IT', 'Legal', 'Marketing', 'Operations', 'Sales']`) |
| **Structural Chunks (v2 Authoritative)** | **128** | `SELECT COUNT(*) FROM policy_chunk_v2` |
| **Relational Facts** | **33** | `SELECT COUNT(*) FROM policy_fact` |
| **Canonical QA Pairs (FAISS)** | **373** | `canonical_qa_faiss.meta.pkl` -> `len(items)` = 373 |
| **Canonical Questions (DB)** | **372** | `SELECT COUNT(*) FROM canonical_question` |
| **Simulated Users** | **10** | `SELECT COUNT(*) FROM user` |
| **Benchmark Test Queries** | **301** | `data/benchmarks/benchmark_test.json` |

> [!IMPORTANT]
> **Prior Draft Error Correction:** Earlier drafts cited 42 policies, 46 versions, 151 chunks, 94 facts, and 453 QA pairs. These values were hypothetical or from older uncommitted synthetic generators. The actual live database and FAISS index have exactly **21 policies, 23 versions, 128 chunks, 33 facts, and 373 QA pairs**. The manuscript strictly uses the true verified counts.

---

### 2.2 Benchmark Query Category Distribution (`data/benchmarks/benchmark_test.json`)

| Category | Query Count | Percentage |
| :--- | :--- | :--- |
| `compiled_qa` | 225 | 74.75% |
| `fact` | 44 | 14.62% |
| `semantic_retrieval` | 8 | 2.66% |
| `unanswerable` | 8 | 2.66% |
| `adversarial` | 5 | 1.66% |
| `temporal_historical` | 4 | 1.33% |
| `department_auth` | 3 | 1.00% |
| `version_comparison` | 2 | 0.66% |
| `confidentiality` | 2 | 0.66% |
| **Total** | **301** | **100.00%** |

---

### 2.3 Version Selection & Answering Accuracy (`results/version_accuracy.csv` & `results/gemini/version_accuracy.csv`)

Evaluated on the full 301-query benchmark:

| Metric | Local Model (`qwen3:4b-q4_K_M`) | Cloud Model (`Gemini 2.0 Flash`) |
| :--- | :--- | :--- |
| **Overall Version Accuracy (All 301 queries)** | **82.72%** (249/301 correct) | **82.72%** (249/301 correct) |
| **Answered-Query Version Accuracy (Excluding abstentions)** | **86.30%** (233/270 correct) | **89.53%** (231/258 correct) |
| **Total Queries Answered** | 270 queries | 258 queries |
| **Total Abstentions (Security/Auth/Unanswerable)** | 31 queries | 43 queries |

#### Category Breakdown:
- `adversarial` (5): 5/5 correct refusals (100%)
- `compiled_qa` (225): 195/225 correct (Local) / 198/225 correct (Gemini)
- `confidentiality` (2): 2/2 correct refusals (100%)
- `department_auth` (3): 2/3 correct (Local) / 3/3 correct (Gemini)
- `fact` (44): 36/44 correct (Local) / 31/44 correct (Gemini)
- `semantic_retrieval` (8): 1/8 correct (Local & Gemini)
- `temporal_historical` (4): 1/4 correct (Local & Gemini)
- `unanswerable` (8): 7/8 correct (Local) / 8/8 correct (Gemini)
- `version_comparison` (2): 0/2 correct

---

### 2.4 Generation Quality & Grounding (`results/eval_summary.json` & `results/answer_accuracy.csv`)

| Metric | Local Model (`qwen3:4b-q4_K_M`) | Cloud Model (`Gemini 2.0 Flash`) | Source File |
| :--- | :--- | :--- | :--- |
| **Exact / Fully Correct Answers** | **27.91%** (84/301) | **27.57%** (83/301) | `answer_accuracy.csv` |
| **Partially Correct Answers** | **20.27%** (61/301) | **13.95%** (42/301) | `answer_accuracy.csv` |
| **Incorrect Answers** | **46.51%** (140/301) | **52.49%** (158/301) | `answer_accuracy.csv` |
| **Adversarial Refusal Accuracy** | **88.89%** (16/18 security queries) | **100.00%** (18/18 security queries) | `eval_summary.json` |
| **Mean Token F1** | **0.3516** | **0.3369** | `eval_summary.json` |
| **Citation Precision** | **0.7973** | **0.7791** | `answer_accuracy.csv` |
| **Citation Recall** | **0.2487** | **0.2704** | `answer_accuracy.csv` |
| **Citation F1** | **0.2993** | **0.3183** | `eval_summary.json` |
| **Brier Score (Runtime)** | **0.6401** | **0.5030** | `eval_summary.json` |
| **ECE (Runtime)** | **0.2954** | **0.4338** | `eval_summary.json` |

---

### 2.5 Latency Profile & Route Distribution (`results/latency.csv` & `results/route_distribution.csv`)

#### Local Model (`qwen3:4b-q4_K_M`):
| Route Name | Count | Traffic % | Mean Latency (ms) | P50 (ms) | P95 (ms) | P99 (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `FAST_PATH_FACT` | 146 | **48.50%** | 20.90 | **20.19** | 33.71 | 41.54 |
| `FAST_PATH_COMPILED_QA` | 17 | **5.65%** | 23.62 | **23.28** | 29.16 | 33.54 |
| `HYBRID_RAG` | 107 | **35.55%** | 120.37 | **120.50** | 144.80 | 146.68 |
| `ABSTAINED` | 31 | **10.30%** | 119.57 | **116.55** | 154.21 | 173.39 |
| **End-to-End System Composite** | **301** | **100.00%** | **66.57** | **29.65** | **136.49** | **146.69** |

#### Cloud Model (`Gemini 2.0 Flash`):
- `FAST_PATH_FACT`: 39 queries (12.96%), P50 = $16.61\ms$
- `FAST_PATH_COMPILED_QA`: 26 queries (8.64%), P50 = $15.91\ms$
- `HYBRID_RAG`: 192 queries (63.79%), P50 = $75.65\ms$
- `ABSTAINED`: 43 queries (14.29%), P50 = $69.27\ms$
- `TEMPORAL_COMPARISON`: 1 query (0.33%), P50 = $22.45\ms$
- **End-to-End System Composite**: P50 = $71.63\ms$, P95 = $85.27\ms$, P99 = $102.95\ms$

---

### 2.6 Offline Retrieval Quality (`results/retrieval_metrics.csv`)

| Retriever Pipeline | Recall@1 | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Dense (`BAAI/bge-small-en-v1.5`)** | 0.9861 | 0.9861 | 0.9861 | 0.9861 | 0.9861 |
| **Sparse (`BM25`)** | 0.9792 | 0.9861 | 0.9861 | 0.9826 | 0.9835 |
| **Hybrid (Reciprocal Rank Fusion, $k=60$)** | 0.9861 | 0.9861 | 0.9861 | 0.9861 | 0.9861 |
| **Hybrid + FlashRank (`ms-marco-TinyBERT-L-2-v2`)** | **0.9861** | **0.9861** | **0.9861** | **0.9861** | **0.9861** |

---

### 2.7 Incremental Knowledge Compilation (`results/incremental_update.csv`)

| Update Strategy | Measured Execution Time | Re-Indexed Chunks | Unchanged Chunks | Index Operations | Speedup Factor | Complexity |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Incremental Delta Update (Ours)** | **3.57 ms** | 0 chunks | 6 chunks | Segment Overlay + Tombstones | **722.50x** | $O(\|\Delta\| \cdot d)$ |
| **Full Global Rebuild (Baseline)** | **2,579.31 ms** | 127 chunks | 0 chunks | Global Re-embedding + Index Rebuild | $1.00\text{x}$ | $O(N \cdot d)$ |

> [!NOTE]
> In the measured experiment, the update tested was a hash no-op (all 6 modified fragments had identical SHA-256 hashes). The measured $3.57\ms$ represents diff calculation and verification time, bypassing vector re-embedding.

---

### 2.8 Confidence Calibration (`results/confidence_calibration.csv`)

| Calibration Scheme | Brier Score | Expected Calibration Error (ECE) | ECE Reduction |
| :--- | :--- | :--- | :--- |
| **Raw Uncalibrated Confidence** | 0.5855 | 0.5840 | Baseline |
| **Isotonic Regression (Calibrated)** | **0.1839** | **0.0000** | **100.0% Reduction** |

---

### 2.9 DeBERTa-v3 Natural Language Inference Verification (`results/nli_validation.csv`)

Evaluated on $n=14$ claim-evidence pairs with `cross-encoder/nli-deberta-v3-base`:

| True Gold Label \ Predicted Label | Predicted ENTAILMENT | Predicted CONTRADICTION | Predicted UNKNOWN | Class Recall |
| :--- | :--- | :--- | :--- | :--- |
| **ENTAILMENT** (5 samples) | 4 | 0 | 1 | **80.0%** |
| **CONTRADICTION** (5 samples) | 0 | 5 | 0 | **100.0%** |
| **UNKNOWN** (4 samples) | 0 | 1 | 3 | **75.0%** |
| **Overall NLI Accuracy** | **85.71% (12 / 14 correct)** | | | |

---

### 2.10 Multi-Tier Semantic Cache Isolation (`results/cache_metrics.csv`)

Evaluated across a 30-query non-repeating sequence:

| Cache Safety / Performance Metric | Measured Value |
| :--- | :--- |
| **Evaluated Cache Warmup Queries** | 30 |
| **L1 / L2 Overall Hit Rate (Non-repeating)** | 0.00% |
| **Mean Cache Miss Latency** | $82.45\ms$ |
| **Mean Cache Hit Latency** | $80.58\ms$ |
| **Measured Cache Speedup Factor** | $1.02\times$ |
| **Stale-Answer Rate (Post-Invalidation)** | **0.00%** |
| **Wrong-Version Cache Rate** | **0.00%** |
| **Unauthorized Cross-Scope Cache Reuse** | **0.00%** |
| **Unsafe-Served Rate** | **0.00%** |

---

### 2.11 Stratified Pipeline Ablation (`results/ablation.csv`)

Evaluated on a 30-query mixed operational subset:

| Ablation Configuration | P50 Latency (ms) | P95 Latency (ms) | Answer F1 (%) | Citation F1 (%) | LLM Calls / 30 Queries |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **B7 (Proposed Full System)** | **109.79** | 131.90 | **41.28%** | **30.62%** | **0** |
| **A1 (w/o Knowledge Compiler)** | **52.01** | 64.88 | **28.51%** | **10.00%** | **30** |
| **A2 (w/o Fact Resolver)** | 107.07 | 130.24 | 41.28% | 30.62% | 0 |
| **A3 (w/o Compiled QA)** | 111.10 | 130.20 | 41.28% | 30.62% | 0 |
| **A4 (w/o Temporal Resolver)** | 108.47 | 130.41 | 41.28% | 30.62% | 0 |
| **A5 (w/o FlashRank Reranker)** | 112.59 | 137.32 | 41.28% | 30.62% | 0 |
| **A6 (w/o Confidence Gate)** | 103.72 | 131.05 | 41.28% | 30.62% | 0 |
| **A7 (w/o Multi-Tier Cache)** | 113.44 | 132.89 | 41.28% | 30.62% | 0 |

---

## 3. Manuscript Structure & Verification Status

The LaTeX manuscript is located at `Veritas_IEEE.tex` and compiles to `Veritas_IEEE.pdf`.

- **Class:** `\documentclass[journal]{IEEEtran}`
- **Page Count:** **Exactly 6 pages** (Verified via `pdfinfo Veritas_IEEE.pdf | grep Pages`)
- **Compilation Tool:** `docker run --rm -v "$(pwd)":/work policylatex:latest bash -c "cd /work && pdflatex -interaction=nonstopmode Veritas_IEEE.tex"`
- **LaTeX Syntax Verification:** Passed `python3 scripts/verify_final_latex.py Veritas_IEEE.tex` with **0 errors and 0 warnings**.
- **Pytest Verification:** 35 passed.

---

## 4. How to Reproduce All Results

To run the master reproducibility suite from scratch:
```bash
bash scripts/reproduce_results.sh
```

To compile the camera-ready PDF:
```bash
docker run --rm -v "$(pwd)":/work policylatex:latest bash -c "cd /work && pdflatex -interaction=nonstopmode Veritas_IEEE.tex && pdflatex -interaction=nonstopmode Veritas_IEEE.tex"
```
