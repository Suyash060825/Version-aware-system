# Final Figure & Table Selection: Veritas IEEE Manuscript

## 1. Main Manuscript Figures (Primary Paper)

| Figure # | Title & Topic | File Location | Evaluation Regime & Sample Size | Primary Purpose in Manuscript |
| :---: | :--- | :--- | :--- | :--- |
| **Fig. 1** | System Architecture Pipeline | `figures/architecture.pdf` | Architectural Schema | Depicts the end-to-end 5-stage pipeline: QueryScope construction, cache check, 4-tier routing, evidence gating, and verified dispatch. |
| **Fig. 2** | Authorization Isolation & Leakage Matrix | `figures/security_scope_matrix.pdf` | Expanded Suite ($N=3,840$) | Demonstrates zero unauthorized leakage across 32 user archetypes $\times$ 120 policies (1,840 TP, 2,000 TN, 0 FP, 0 FN). |
| **Fig. 3** | Retrieval Pipeline Progression & Candidate Sensitivity | `figures/retrieval_progression.pdf` | Expanded Suite ($N=922$) | Shows monotonic recall improvement: BM25 (72.4%) $\to$ Dense (78.6%) $\to$ RRF (88.2%) $\to$ FlashRank (94.47%) and $K=50 \to K=100$ depth sensitivity. |
| **Fig. 4** | Route Distribution & Fast-Path Traffic Share | `figures/route_distribution.pdf` | Baseline ($N=301$) & Char. ($N=922$) | Visualizes the 54.15% (baseline) and 63.45% (characterization) deterministic/refusal offload bypassing LLM text generation. |
| **Fig. 5** | Incremental Compiler Speedup vs. Mutation Delta | `figures/compiler_speedup_curve.pdf` | Characterization (3,000 chunks) | Illustrates $O(|\Delta|\cdot d)$ vs. $O(N\cdot d)$ scaling: 95.0% re-embedding avoidance and $24.95\times$ speedup at 5% mutation delta. |
| **Fig. 6** | Reliability Curve & Calibration Distribution Shift | `figures/calibration_reliability.pdf` | Held-Out & Live Runtime | Contrasts in-distribution isotonic calibration (ECE 0.041) with live open-distribution query shift (ECE 0.2954). |

---

## 2. Main Manuscript Tables (Primary Paper)

| Table # | Title & Topic | Evaluated Scope ($N$) | Primary Metrics Reported |
| :---: | :--- | :--- | :--- |
| **Table 1** | Architectural Comparison with Related Paradigms | Qualitative System Comparison | Temporal validity, role scope, delta compile, tiered routing, contradiction monitoring, grounded verification, audit traces. |
| **Table 2** | Audited Evaluation Regimes and Experimental Scope | 8 Distinct Evaluation Regimes | Frozen baseline (301), internal repo (462), expanded char. (922), security (3,840), compiler (5 sweeps), NLI (20), mutation (20), concurrency (1,000). |
| **Table 3** | Security and Governance Head-to-Head | Baseline ($N=301$) & Char. ($N=3,840$) | 100.0% auth correctness, 0.00% leakage, 88.07% authorized accuracy, 100.0% safe abstention precision. |
| **Table 4** | Generation Quality: Local vs. Cloud Model | Baseline ($N=301$) & Fixed-Gold ($N=100$) | Version resolution (82.72%), local/cloud accuracy, exact match (27.91%), Fixed-Gold Token F1 (**0.9620**), citation precision (0.7973), latencies. |
| **Table 5** | Retrieval Subsystem Component Breakdown | Expanded Characterization ($N=922$) | Recall@1, Recall@5, Recall@10, MRR@10, NDCG@10 across BM25, Dense, RRF, and FlashRank cross-encoder ($K=100$). |
| **Table 6** | Route-Level Latency Breakdown | Baseline ($N=301$) & Char. ($N=922$) | Traffic percentage, Mean, P50, P95, P99 across Fact, QA, Hybrid RAG, and Abstained routes. |
| **Table 7** | Incremental Compiler: Mutation Sweeps vs. Cold Rebuild | 128-Chunk Fixture & 3,000-Chunk Corpus | Mutated chunk counts, incremental compile time, cold rebuild time, and speedup factor ($5{,}059\times$, $489\times$, $24.95\times$, $80.62\times$). |

---

## 3. Supplementary Figures (Preserved for Appendix / Extended Version)

The repository preserves 18 supplementary characterization figures located in `results/system_characterization/figures/`:
1. `latency_vs_concurrency_workers.pdf` — Multi-worker latency growth (1 to 100 threads).
2. `concurrency_qps_saturation.pdf` — Throughput saturation near 137 QPS due to lock contention.
3. `cross_session_cache_isolation_heatmap.pdf` — Verification of 0 cross-tenant cache bleeding.
4. `post_mutation_boundary_retrieval.pdf` — Point-in-time boundary date retrieval verification.
5. `tombstone_purging_timeline.pdf` — Vector and BM25 index tombstone purge confirmation.
6. `failure_mode_breakdown_pie.pdf` — Taxonomy of query abstentions and retrieval misses.
7. `compound_query_candidate_starvation.pdf` — Analysis of candidate pool omissions at $K=50$.
8. `citation_precision_recall_tradeoff.pdf` — Fine-grained section vs. sentence citation evaluation.
9. `nli_contradiction_score_distribution.pdf` — Distribution of DeBERTa-v3 contradiction probabilities.
10. `bge_embedding_cosine_clustering.pdf` — Dense semantic space separation by policy domain.
11. `bm25_sparse_term_density.pdf` — Lexical inverted index posting density.
12. `rrf_rank_correlation_scatter.pdf` — Lexical vs. dense rank fusion correlations.
13. `flashrank_score_recalibration.pdf` — Cross-encoder reranker score distributions.
14. `qwen3_4b_quantization_exact_match.pdf` — 4-bit quantization exact match sensitivity.
15. `gemini_flash_paraphrase_dispersion.pdf` — Cloud LLM token generation variability.
16. `cache_hit_ratio_over_time.pdf` — Multi-user composite cache hit dynamics.
17. `memory_footprint_scaling.pdf` — RAM footprint across 120-policy corpus.
18. `end_to_end_trace_waterfall.pdf` — Execution stage waterfall breakdown across routes.
