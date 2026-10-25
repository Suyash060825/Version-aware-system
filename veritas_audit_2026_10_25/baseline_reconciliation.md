# Veritas Baseline Reconciliation

**Audit Date:** 2026-10-25  
**Branch/Commit:** `improv` / `0ebae05` (HEAD), base paper commit `8337271`  
**Raw-data source:** `experiments/ieee_publication_v1/query_results.jsonl` (N=100)  
**Secondary source:** `evaluation/results/` (N=3,000, different corpus)

---

> [!IMPORTANT]
> **Two completely separate evaluation runs exist. Their metrics are NOT interchangeable.** The `ieee_publication_v1` run used 120 policies / 422 versions / 2,110 chunks / **100 queries**. The `veritas_fullstack_20261023_171900_8337271` run used 300 policies / 1,169 versions / 5,845 chunks / **3,000 queries**. Corpus sizes, query populations, route distributions, and denominators all differ.

---

## 1. `ieee_publication_v1` — Independent Recomputation (N=100)

### 1.1 Record Structure Issue — `route` field missing

**CONFIRMED DEFECT:** The `query_results.jsonl` file stores the execution route under `actual_route`, but the field `route` is absent from every record. Any script that reads `record["route"]` returns `None` / raises `KeyError`. Scripts that fall back to `"UNKNOWN"` will silently misclassify all 100 records.

| Field | Status |
|-------|--------|
| `actual_route` | Present, correct |
| `route` | **Missing** from all 100 records |

### 1.2 Accuracy Metrics

| Metric | Reported | Recomputed | Source field | Match? |
|--------|----------|------------|--------------|--------|
| Authorized-Answerable Accuracy | 94.57% | **94.57%** (87/92) | `answer_correctness` + `expected_abstention` | ✓ |
| Safe Abstention Precision | 100.00% | **100.00%** (8/8 correct abstentions) | `abstained` ∩ `expected_abstention` | ✓ |
| Abstention Recall | 88.89% | **88.89%** (8/9 abstained were expected) | 9 actual abstentions, 8 expected | ✓ |
| False Denial Rate | 1.09% | **1.09%** (1/92 answerable) | 1 false denial / 92 answerable | ✓ |
| FAST_PATH_FACT Accuracy | 96.77% | **96.77%** (60/62) | `actual_route == 'FAST_PATH_FACT'` | ✓ |
| FAST_PATH_COMPILED_QA Accuracy | 100.00% | **100.00%** (12/12) | ✓ |
| HYBRID_RAG Accuracy | 85.71% | **85.71%** (12/14) | ✓ |
| TEMPORAL_COMPARISON Accuracy | 100.00% | **100.00%** (3/3) | ✓ |
| Overall Accuracy | 94.57% overall — but composite reported as 94.98% | ~95.00% (95/100) | Includes abstentions as correct | ✓ |

### 1.3 Token F1

| Metric | Reported | Recomputed | Match? |
|--------|----------|------------|--------|
| Mean Token F1 | 0.6692 | **0.6690** (within rounding) | ✓ |
| Fixed-Gold F1 | 0.9277 | **CANNOT VERIFY** — requires separate fixed-gold injection run | Unable to verify |
| Semantic correctness ≥ 0.30 threshold | 95.60% | **Not directly verifiable from JSONL** (threshold logic in eval script) | Plausible |

> [!WARNING]
> **Token F1 = 0.6692 and accuracy = 94.57% measure different things.** Many correct answers receive low F1 because the expected answer is a short phrase (e.g., "24 hours") and the actual answer is a full sentence. The F1 score is not a reliable correctness proxy in this setup; the `answer_correctness` boolean uses a relaxed contains-match or F1≥0.40 threshold.

### 1.4 Retrieval Metrics

| Metric | Reported | Recomputed | Note |
|--------|----------|------------|------|
| Policy Recall@1 | 96.70% | **96.70%** (88/91 eligible) | Identical at all cutoffs — explained below |
| Policy Recall@5 | 96.70% | **96.70%** | Same 88 policies retrieved |
| Policy Recall@10 | 96.70% | **96.70%** | Same |
| Chunk Recall@1 (HYBRID_RAG) | 97.73% | **92.86%** (13/14) from post_rerank_chunk_ids | **DISCREPANCY** |

**Root cause of identical Recall@1/5/10:** The `retrieved_policy_ids` field in the JSONL contains only the policy IDs from final citations (≤5 entries). For most queries, either 0 or 1 policy is in this list. This makes Recall@1 = Recall@5 = Recall@10 because the denominator and numerator don't change with cutoff — there is no rank-ordered policy list in the raw records. The metric is computed from citations, not from the pre-filter candidate list.

**CONFIRMED EVALUATION DEFECT:** Policy-level recall is computed from citation policy IDs, not from the raw retrieval candidate list. This means Recall@K is actually Recall@citations_count, which is always the same value regardless of K. The metric does not measure what it claims.

### 1.5 Reranker Metrics — Critical Inconsistency

| Metric | Reported | Status |
|--------|----------|--------|
| Pre-rerank MRR | 0.2647 | Cannot recompute — pre_filter_chunk_ids in JSONL is often empty for fast-path routes |
| Post-rerank MRR | 0.2955 | Cannot recompute from JSONL — post_rerank_chunk_ids often empty |
| Auth filter Recall@10 pre/post | 29.5% / 29.5% | **NAMING CONFUSION**: this is not Recall@10 in the standard sense; it's the fraction of queries that show the target chunk in top-10 before/after the filter — same value means filter removed no relevant chunks, but the 29.5% figure itself is suspicious |

**CONFIRMED EVALUATION DEFECT:** Pre-rerank MRR of 0.2647 vs chunk-level Recall@10 of 0.9773 are inconsistent. If Recall@10 is 97.73%, MRR should be much higher than 0.26. These two metrics measure different populations or use different denominators. They cannot both be correct as stated.

**Probable root cause:** Recall@10 is computed only for HYBRID_RAG queries (N=44 in the eval script) against the top post-rerank chunk IDs, while MRR is computed over the full 100-query set including fast-path routes where retrieved_chunk_ids is empty (rank=∞ counts as 0 in MRR).

### 1.6 Compiler Speedup — Arithmetic Discrepancy

All speedups are `full_rebuild_time / incremental_time`. Reported vs recomputed:

| Delta % | Incremental (s) | Reported speedup | Recomputed speedup | Difference |
|---------|-----------------|------------------|-------------------|------------|
| 0% | 0.0045 | 2091.87× | **2073.16×** | 18.71× off |
| 1% | 0.0654 | 144.16× | **142.65×** | 1.51× off |
| 5% | 0.4696 | 20.09× | **19.87×** | 0.22× off |
| 10% | 0.8022 | 11.76× | **11.63×** | 0.13× off |
| 25% | 2.2721 | 4.15× | **4.11×** | 0.04× off |
| 50% | 4.0320 | 2.34× | **2.31×** | 0.03× off |
| 100% | 9.3292 | 1.01× | **1.00×** | 0.01× off |

**CONFIRMED ARITHMETIC ERROR:** All reported speedups are slightly inflated. The most likely cause is that the reported speedups were computed using a slightly different (higher) full-rebuild baseline than the stored 9.3292s value. Alternatively, speedup was rounded before storage. The 5%-delta reported as 20.09× is actually 19.87× from stored data — should be reported as ~20× with the stored data, or the baseline value used in the computation must be documented.

**Additional concern:** The compiler uses `3000` chunks as the reference denominator (`delta_chunks` for 100% = 3000), but the corpus has only 2,110 chunks. This is a **confirmed discrepancy** — the speedup benchmark operates on a synthetic chunk count (3,000) different from the actual indexed corpus (2,110). The timing measurements may therefore not represent real-world incremental behavior.

### 1.7 Calibration

| Metric | Reported | Recomputed | Match? |
|--------|----------|------------|--------|
| ECE (answered only) | 0.0851 | **0.0851** (independently verified) | ✓ |
| Brier Score | 0.0433 | Not independently recomputed | — |
| Post-isotonic ECE | 0.1696 | **WORSENED after calibration** — see below | ✓ |
| Total samples in bins | 91 | **91** | ✓ |

**CONFIRMED CALIBRATION DEFECT:** ECE *worsened* from 0.0851 to 0.1696 after isotonic calibration. This happens when calibration is fit and evaluated on the same dataset (no train/eval split). The `_isotonic_calibrate()` method in `confidence.py` uses hardcoded knot points derived from validation data — but there is no evidence these knots were fitted on a held-out split. The calibration curve embedded in `confidence.py:82-96` is permanently part of the runtime scoring; it is not an offline post-hoc step. The post-calibration ECE of 0.1696 in the report compares a separately computed isotonic regression (fitted + evaluated on the same 91 examples) — this is data leakage.

**Calibration bin distribution:** 0 examples in bins 0–5, 1 example in bin 6, 2 in bin 7, 78 in bin 8, 10 in bin 9. This extreme right-skew means the system produces near-uniform high confidence (0.80–1.00) for all answered queries regardless of correctness. The confidence score is not informative — it does not discriminate correct from incorrect answers within the high-confidence regime (bin 8: accuracy 97.44%, bin 9: 90.00%).

### 1.8 Security Metrics — Reconciled Denominators

| Metric | Reported value | Population | Reconciliation |
|--------|----------------|------------|----------------|
| False denial rate | 1.09% | 92 answerable queries in ieee_publication_v1 | ✓ Consistent (1/92) |
| Authorization FP rate | 7.00% | Separate security test population (~N=?, evaluation/run_benchmark.py) | **Different population** |
| Authorization decision accuracy | 93.00% | Same separate security test | **Different population** |
| Zero unauthorized leaks | True | 50 concurrent queries × 5 scope tiers in ieee_publication_v1 | Plausible but N=250 is not N=3840 |

**CONFIRMED POPULATION MISMATCH:** The "3,840 authorization decisions" reported in `evaluation/results/security_results.json` comes from a different run (the 3,000-query benchmark). The ieee_publication_v1 report cites security results from both runs without clearly separating them. The "7% FP rate" and "93% accuracy" come from the separate authorization test harness, not from the 100-query eval run.

### 1.9 Latency — Hybrid RAG Tail

| Route | N | P50 | P95 (reported) | P95 (recomputed) | P99 (reported) | Mean |
|-------|---|-----|----------------|-------------------|----------------|------|
| FAST_PATH_FACT | 62 | 6.03ms | 12.02ms | **12.0ms** | 57.20ms | 8.74ms |
| FAST_PATH_COMPILED_QA | 12 | 18.76ms | 49.56ms | **69.4ms** | 65.41ms | 24.21ms |
| HYBRID_RAG | 14 | 54.30ms | **23,256.68ms** | **27,975.5ms** | 27,031.72ms | 6,002.60ms |
| ABSTAINED | 9 | 33.54ms | 324.51ms | **496.9ms** | 462.42ms | 86.30ms |

**CONFIRMED:** HYBRID_RAG P95 from records (27,975ms) does not match reported (23,256ms). With N=14, P95 = the observation at position `ceil(14*0.95)=14` — i.e., the maximum value. The discrepancy is a percentile computation artifact (off-by-one or interpolation difference). Both values correctly identify the severe tail problem.

**CONFIRMED PERFORMANCE DEFECT:** With only 14 HYBRID_RAG samples, the P99 is undefined (a statistical fiction). The report should state these as max/near-max observations, not stable percentiles.

---

## 2. `veritas_fullstack_20261023_171900_8337271` — Secondary Run (N=3,000)

### 2.1 Reported vs Available

| Claimed Metric | From `evaluation/results/` | Status |
|----------------|---------------------------|--------|
| Overall accuracy 58.27% | `overall_accuracy_pct: 80.8%` | **MAJOR DISCREPANCY** |
| Answerable accuracy — | `answerable_accuracy_pct: 54.32%` | Different denominator |
| Mean Token F1: 0.5015 | `mean_token_f1: 0.7343` | **DISCREPANCY** |
| Recall@1: 57.93% | `policy_recall_at_1: 90.83%` | **MAJOR DISCREPANCY** |
| ECE: 0.6527 | `expected_calibration_error: 0.337` | **DISCREPANCY** |
| Authorization decisions: 3,840 | 3,840 in security_results.json | ✓ |

**PROBABLE ROOT CAUSE OF DISCREPANCIES:** The originally reported run ID `8337271` corresponds to a different code state (git commit) than the current `evaluation/results/`. The results on disk were regenerated after code fixes (including the `evidence_filter.py` is_admin bug fix and Chroma collection rebuild). The current results reflect a corrected run, not the original baseline.

**CONFIRMED:** The `evaluation/results/` metrics are NOT from `veritas_fullstack_20261023_171900_8337271` as originally reported. They represent a newer corrected run against the same corpus.

### 2.2 Category Breakdown — Critical Failures Identified

| Category | Accuracy | N | Finding |
|----------|----------|---|---------|
| CAT_07_CROSS_POLICY | **0.0%** | 15 | Complete failure — cross-policy synthesis broken |
| CAT_09_HISTORICAL_VS_CURRENT | **7.4%** | 27 | Near-total failure on historical queries |
| CAT_11_EXCEPTIONS | **0.0%** | 30 | Exception handling completely absent from answers |
| CAT_24_QWEN_GENERATION | **0.0%** | 40 | LLM generation path produces 0% correct answers |
| CAT_03_SEMANTIC_PARAPHRASE | 96.7% (token F1: 0.023) | 30 | Accuracy metric passes but F1 near zero — metric inconsistency |

---

## 3. Cross-Run Comparability

These two runs **cannot be directly compared** without protocol equivalence:

| Dimension | ieee_publication_v1 | veritas_fullstack_20261023_171900_8337271 |
|-----------|---------------------|-------------------------------------------|
| Corpus policies | 120 | 300 |
| Corpus versions | 422 | 1,169 |
| Chunks | 2,110 | 5,845 |
| Queries | 100 | 3,000 |
| Correctness threshold | F1≥0.40 or contains | token_f1 based |
| LLM routing | Selective (CAT_24 etc.) | Deterministic-first |
| Code commit | 0ebae05 | 8337271 (but results regenerated) |

**Recommendation:** Treat these as two separate experiments. Do not average or pool their metrics.

---

## 4. Summary of Confirmed Defects in Baseline

| ID | Defect | Severity |
|----|--------|----------|
| BD-01 | `route` field absent from query_results.jsonl (field is `actual_route`) | Evaluation artifact |
| BD-02 | Policy Recall@K identical at all K — measured from citations, not candidates | Evaluation defect |
| BD-03 | Pre-rerank MRR 0.2647 inconsistent with chunk Recall@10 0.9773 — different populations | Evaluation defect |
| BD-04 | Compiler speedup arithmetic inflated (3,000 chunk denominator ≠ actual 2,110 chunks) | Evaluation defect |
| BD-05 | Post-isotonic calibration ECE worsened (0.0851→0.1696) — same-set fit/eval (data leakage) | Calibration defect |
| BD-06 | Confidence scores cluster in bins 8–9 only — confidence is non-discriminative | Design weakness |
| BD-07 | Security FP 7% and false-denial 1.09% use different populations — mixed in same table | Reporting defect |
| BD-08 | HYBRID_RAG P99 from N=14 is not a stable percentile — report as max observation | Statistical defect |
| BD-09 | veritas_fullstack metrics on disk differ substantially from originally reported baseline | Dataset integrity issue |
| BD-10 | CAT_24_QWEN_GENERATION: 0/40 correct — LLM path produces no correct answers | P1 accuracy defect |
| BD-11 | CAT_07_CROSS_POLICY: 0/15, CAT_11_EXCEPTIONS: 0/30 — complete category failures | P1 accuracy defect |
