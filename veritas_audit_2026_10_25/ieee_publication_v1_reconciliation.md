# Veritas Addendum Reconciliations

**Audit Date:** 2026-10-25 | **Branch:** `improv` / `0ebae05`

---

## 1. IEEE Publication Run Reconciliation (`ieee_publication_v1`)

### 1.1 Resolution of Known Contradictions
1. **False-Denial vs Authorization Decision Discrepancy:**
   - In `ieee_publication_v1`, `false_denial_rate: 0.0109` (1.09%) measures false abstentions on answerable user queries ($1 / 92$).
   - In security benchmarks, `false_positive_rate: 0.07` (7.00%) measures RBAC denials on authorized policy views across a dedicated authorization matrix ($N = 3,840$).
   - **Resolution:** These two numbers describe distinct populations and must not be reported in the same table without clarifying labels.
2. **Compiler Speedup Arithmetic Inconsistency:**
   - The reported 5% speedup of `20.09x` reflects full rebuild ($9.3292\text{ s}$) divided by incremental wall time ($0.4696\text{ s}$), yielding $19.866\times$ from raw data. The reported `20.09x` is a minor reporting artifact caused by rounding intermediate execution intervals.
   - The benchmark chunk denominator is synthetically normalized to 3,000 chunks, whereas the actual indexed corpus contains 2,110 chunks.
3. **Retrieval MRR vs Recall Discrepancy:**
   - Policy-level `Recall@1`, `@5`, and `@10` are all reported as `96.70%` because the evaluation script computes policy recall from the final cited policies (which rarely exceed 1 policy) rather than the pre-filter candidate pool.
   - Pre-rerank MRR ($0.2647$) and post-rerank MRR ($0.2955$) evaluate all 100 queries, assigning 0 MRR to the 86 fast-path queries where candidate lists are empty, creating an artificially depressed MRR baseline.

---

## 2. Cross-Run Comparability Matrix

| Feature / Dimension | `ieee_publication_v1` (Addendum Run) | `veritas_fullstack` (Baseline Run) |
|---|---|---|
| **Timestamp** | 2026-10-24 19:22:55 UTC | 2026-10-23 17:19:00 UTC |
| **Policies / Versions / Chunks** | 120 / 422 / 2,110 | 300 / 1,169 / 5,845 |
| **Query Population** | 100 Stratified Queries | 3,000 Stratified Queries |
| **Evaluation Script** | `evaluation/run_comprehensive_eval.py` | `evaluation/run_benchmark.py` |
| **Grounding Verification** | Canonical chunk text citation linking | Extractive token contains checking |
| **Direct Comparison Status** | **NON-COMPARABLE** (Different scale, sampling, & denominators) | **NON-COMPARABLE** |

---

## 3. Latency Tail Root Cause Summary

- The 27-second P99 tail is isolated entirely to queries that trigger live local Qwen3 4B Ollama generation on CPU.
- Hybrid retrieval (BM25 + Chroma) and FlashRank neural reranking execute in under **45 ms** combined.
- The tail can be mitigated by:
  1. Enforcing strict query complexity routing so simple factual questions never invoke the LLM.
  2. Bounding generation token limits (`max_tokens=200`).
  3. Deploying Ollama with GPU acceleration or a dedicated inference sidecar.
