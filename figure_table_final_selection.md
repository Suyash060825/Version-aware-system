# Veritas Publication: Final Figure and Table Selection

To ensure the 6-page IEEE journal paper remains mathematically dense, readable, and within formatting limits, this document selects the core **Main Paper Figures and Tables** and assigns all supplementary items to an extended technical appendix.

---

## 🏛️ 1. Main Paper Selection (Recommended Set)

### Figures for Main Paper (6 Core Figures)

1. **Fig. 1: System Architecture & Invariant Enforcement Pipeline**
   - *Placement*: Section IV (Architecture)
   - *File*: `figures/architecture.pdf` (or `figures/architecture.png`)
   - *Caption*: Veritas end-to-end architecture illustrating frozen QueryScope construction, multi-tier adaptive routing (Tiers 0–3), pre-retrieval eligibility gating, and calibrated NLI verification.

2. **Fig. 2: Multi-Tier Router Traffic Distribution & Latency Profiles**
   - *Placement*: Section VI (Results)
   - *File*: `results/system_characterization/paper_figures/fig04_router_traffic.png`
   - *Caption*: Traffic distribution and P50/P95 latency breakdown across operational routing tiers on the 922-query characterization benchmark. Fast-path routes resolve 63.4% of queries at sub-5ms latency.

3. **Fig. 3: Retrieval Pipeline Progression & Candidate Pool Depth Sensitivity**
   - *Placement*: Section VI (Results)
   - *File*: `results/system_characterization/paper_figures/fig06_retrieval_recall.png`
   - *Caption*: Recall@K progression across retrieval stages (BM25: 72.4%, Dense: 78.6%, RRF: 88.2%, Cross-Encoder: 94.5%), alongside candidate pool depth sensitivity ($K=50 \to K=100$) on compound multi-clause queries.

4. **Fig. 4: Incremental Compilation Speedup vs. Mutation Ratio**
   - *Placement*: Section VI (Results)
   - *File*: `results/system_characterization/paper_figures/fig11_mutation_vs_compile_time.png`
   - *Caption*: Total compilation time and re-embedding avoidance as a function of mutation rate on a 3,000-chunk corpus ($24.95\times$ speedup at 5% amendment delta).

5. **Fig. 5: Pre-Retrieval Authorization Confusion Matrix**
   - *Placement*: Section VI (Results)
   - *File*: `results/system_characterization/paper_figures/fig14_auth_confusion_matrix.png`
   - *Caption*: Authorization confusion matrix across 3,840 cross-user evaluations (1,840 TP, 2,000 TN, 0 FP, 0 FN; 0 observed leaks).

6. **Fig. 6: Confidence Calibration Reliability Diagram (In-Distribution vs. Runtime Shift)**
   - *Placement*: Section VI (Results)
   - *File*: `results/system_characterization/paper_figures/fig16_calibration_reliability.png`
   - *Caption*: Reliability diagram for uncalibrated logits, validation split post-isotonic calibration (ECE: 0.041), and live runtime evaluation (ECE: 0.2954).

---

### Tables for Main Paper (5 Core Tables)

1. **Table I: Architectural Paradigm Comparison**
   - *Placement*: Section II (Related Work)
   - *Content*: Comparison of Veritas against Standard Dense RAG, Hybrid+RRF, VersionRAG, and Secure RAG across temporal validity, scope invariants, incremental compilation, adaptive routing, and verification.

2. **Table II: Security and Governance Head-to-Head Comparison**
   - *Placement*: Section VI (Results)
   - *Content*: Veritas vs. Unrestricted RAG baseline on authorization accuracy, unsafe leakage rate, authorized-query version accuracy, and safe abstention precision.

3. **Table III: Generation Quality & Decoupled Evidence Fidelity**
   - *Placement*: Section VI (Results)
   - *Content*: Local (`qwen3:4b`) vs. Cloud (`Gemini 2.0 Flash`) performance on the baseline benchmark ($N=301$), alongside decoupled generation fidelity given fixed gold evidence ($N=100$, 0.962 Token F1).

4. **Table IV: Retrieval Subsystem Component Breakdown & Sensitivity**
   - *Placement*: Section VI (Results)
   - *Content*: Chunk-level Recall@1/5/10, MRR, NDCG@10, and latency for BM25, Dense, RRF, and FlashRank Cross-Encoder ($K=50$ vs. $K=100$).

5. **Table V: Incremental Compiler Performance Sweeps**
   - *Placement*: Section VI (Results)
   - *Content*: 128-chunk small fixture results alongside 3,000-chunk sweeps (0%, 1%, 5%, 10%, 25%, 50%, 100% mutation deltas, re-embedding counts, speedup factors).

---

## 📂 2. Supplementary & Technical Appendix Items

All remaining figures from the 24-figure characterization suite are designated as **Supplementary Artifacts** available in the repository:
- `fig01_coverage_matrix.png` (Domain coverage across 12 sectors)
- `fig02_corpus_distribution.png` (Corpus version distribution)
- `fig03_query_taxonomy.png` (Query difficulty taxonomy)
- `fig05_route_transitions.png` (State transition graph)
- `fig07_mrr_ndcg.png` (MRR and NDCG curves)
- `fig08_latency_distributions.png` (Expanded percentile latency boxplots)
- `fig09_corpus_vs_latency.png` (Latency vs. corpus scaling)
- `fig10_corpus_vs_compilation.png` (Compilation scaling with corpus size)
- `fig12_mutation_vs_reembed.png` (Re-embedding avoidance curve)
- `fig13_cache_hit_miss.png` (Cache hit and invalidation metrics)
- `fig15_nli_confusion_matrix.png` (DeBERTa NLI confusion matrix)
- `fig17_local_vs_cloud.png` (Local vs cloud model output distributions)
- `fig18_failure_distribution.png` & `fig19_failure_heatmap.png` (Failure taxonomy F1–F10 breakdown)
- `fig20_security_matrix.png` (Full clearance tier heatmap)
- `fig21_temporal_accuracy_dates.png` (Point-in-time temporal accuracy)
- `fig22_competing_versions.png` (Accuracy vs competing version count)
- `fig23_retrieval_vs_corpus_size.png` (Retrieval recall scaling)
- `fig24_routing_vs_difficulty.png` (Routing accuracy vs difficulty)
