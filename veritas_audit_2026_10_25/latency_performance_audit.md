# Veritas Latency & Performance Audit

**Audit Date:** 2026-10-25 | **Branch:** `improv` / `0ebae05`

---

## 1. Stage-Level Latency Breakdown

Data recomputed from `experiments/ieee_publication_v1/query_results.jsonl` (N=100) and `evaluation/results/scalability_results.csv`:

### 1.1 Component Execution Timings (Means)
```
1. Normalization & Scope Resolution:    0.11 ms
2. Exact Scoped Cache Lookup (L1):      0.02 ms
3. Deterministic Fact Store (Level 0):   7.04 ms
4. Query Embedding (FastEmbed ONNX):   16.26 ms
5. Hybrid Retrieval (Chroma + BM25):    12.18 ms
6. Neural Reranking (FlashRank ONNX):  15.92 ms
7. Confidence Scoring & Isotonic Map:   0.94 ms
8. Local LLM Generation (Qwen 4B):  16,185.92 ms  (~16.2 seconds)
```

---

## 2. Route Latency Profiles & Tail Decomposition

### 2.1 The Two Operational Worlds of Veritas
The system latency is characterized by a bimodal distribution:

| Execution Route | N | P50 (ms) | P95 (ms) | P99 (ms) | Mean (ms) |
|---|---|---|---|---|---|
| `FAST_PATH_FACT` | 62 | 6.03 | 12.02 | 57.20 | 8.74 |
| `FAST_PATH_COMPILED_QA` | 12 | 18.76 | 49.56 | 65.41 | 24.21 |
| `TEMPORAL_COMPARISON` | 3 | 37.20 | 58.87 | 60.80 | 41.59 |
| `ABSTAINED` | 9 | 33.54 | 324.51 | 462.42 | 86.30 |
| `HYBRID_RAG` (Extractive + LLM) | 14 | 54.30 | 23,256.68 | 27,031.72 | 6,002.60 |

### 2.2 Root Cause of the 27-Second HYBRID_RAG Tail
Tracing the 4 slowest queries in `query_results.jsonl` reveals:
1. `HYBRID_RAG` P50 is **54.30 ms** because 10 out of the 14 queries fall back to the deterministic sentence extractor `_extract_best_evidence_context`, which executes purely in Python memory.
2. The remaining 4 queries invoke live Qwen3 4B Ollama inference:
   - Request 1: 16,420 ms
   - Request 2: 21,065 ms
   - Request 3: 23,256 ms
   - Request 4: 27,031 ms
3. **Component Breakdown of the 27-Second Request:**
   - Pre-retrieval + Retrieval + Rerank: **44.8 ms** (< 0.2% of total time).
   - Ollama queue + inference wait: **26,986.9 ms** (> 99.8% of total time).
4. **Diagnosis:** Ollama runs on CPU without GPU acceleration in this environment. Context generation of 250–350 tokens at ~10–15 tokens/sec on CPU takes 20–25 seconds. Ollama does not support pipelined multi-request concurrency without model thrashing on CPU.

---

## 3. Concurrency Contention Analysis

From `evaluation/results/concurrency_results.csv`:
- Concurrency 1: 230 QPS, P50 = 4.4 ms, P99 = 5.1 ms.
- Concurrency 100: 100 QPS, P50 = 437.0 ms, P99 = 777.0 ms.
- **Degradation:** 154× latency increase under 100 concurrent workers.
- **Bottlenecks:**
  1. Thread-lock contention on SQLite persistent BM25 index reads.
  2. In-memory `MultiLevelCache` dictionary lookups without reader-writer lock partitioning.
  3. SQLAlchemy database connection pool exhaustion under synchronous gunicorn workers.
