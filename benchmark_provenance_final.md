# Veritas Benchmark Provenance & Evaluation Regimes

To maintain absolute scientific clarity and prevent denominator conflation, this document establishes the explicit identity, scope, purpose, and differences between the evaluation suites in this repository.

---

## 🏛️ 1. Evaluation Regimes at a Glance

```
┌───────────────────────────────┬───────────────────────────────┬───────────────────────────────┐
│ Evaluation Regime             │ Scope & Scale                 │ Primary Scientific Role       │
├───────────────────────────────┼───────────────────────────────┼───────────────────────────────┤
│ **A. Frozen Baseline          │ 21 Policies, 23 Versions,     │ Historical benchmark frozen   │
│    Benchmark ($N=301$)**      │ 128 Chunks, 10 Users,         │ at commit `61d64b71`. Used for│
│                               │ 301 Queries                   │ end-to-end Local vs Cloud RAG.│
├───────────────────────────────┼───────────────────────────────┼───────────────────────────────┤
│ **B. Internal Repository      │ 462 Test Records,             │ Continuous integration and    │
│    Harness ($N=462$)**        │ Unit & Regression Suites      │ automated platform sanity.    │
├───────────────────────────────┼───────────────────────────────┼───────────────────────────────┤
│ **C. Expanded System          │ 120 Policies, 12 Domains,     │ Large-scale multi-tier stress │
│    Characterization ($N=922$)**│ ~600 Versions, ~3,000 Chunks, │ testing, concurrency scaling, │
│                               │ 32 Users, 922 Queries         │ depth ablations (Commit `449e`│
└───────────────────────────────┴───────────────────────────────┴───────────────────────────────┘
```

---

## 🔬 2. Detailed Breakdown of Evaluation Regimes

### Regime A: Frozen Manuscript Baseline Benchmark ($N=301$)
* **Source Artifacts**: `data/benchmarks/benchmark_test.json`, `data/ledger.db`, `results/eval_summary.json`, `results/latency.csv`, `results/retrieval_metrics.csv`.
* **Corpus Scale**: 21 enterprise policies, 8 departments, 23 versions, 128 structural chunks (`policy_chunk_v2`), 33 relational facts, 373 canonical QA pairs.
* **Simulated Users**: 10 enterprise users spanning 4 clearance tiers.
* **Primary Focus**:
  * End-to-end local LLM (`qwen3:4b-q4_K_M`) vs. cloud LLM (`Gemini 2.0 Flash`) generation fidelity.
  * Policy-level offline retrieval comparison (Dense, BM25, RRF, Cross-Encoder).
  * Fast-path routing traffic share under operational lookup distributions (54.15% Tier 0/1 share).
  * Initial NLI pilot validation ($N=14$ pairs).
* **Git SHA Provenance**: Frozen production logic commit `61d64b71c298c3c505f2eeeef3c94829dfb55f75`.

### Regime B: Internal Repository Regression Harness ($N=462$)
* **Source Artifacts**: `data/benchmarks/benchmark_all.json`, `tests/test_rag_pipeline.py`, `tests/test_hardening_regression.py`.
* **Primary Focus**: Comprehensive unit, RBAC, and multi-branch edge case verification across all platform views (41/41 passing tests).

### Regime C: Expanded System Characterization Suite ($N=922$)
* **Source Artifacts**: `tests/system_characterization/corpus/ground_truth_ledger.json`, `results/system_characterization/results_master.csv`, `results/system_characterization/compiler_results.csv`, `results/system_characterization/security_results.csv`, `results/system_characterization/concurrency_results.csv`.
* **Corpus Scale**: 120 synthetic enterprise policies spanning 12 business domains, ~600 versions, 2,110 to 3,000 structural chunks tagged with SHA-256 digests.
* **Simulated Users**: 32 user archetypes spanning 4 clearance levels and 12 departmental scopes.
* **Total Executions**: 4,980 test executions, 9,840 trace observations.
* **Primary Focus**:
  * Large-scale incremental compilation sweeps across 0% to 100% mutation rates ($24.95\times$ speedup at 5% delta).
  * Full-matrix authorization isolation testing ($3,840$ evaluations; 0 leaks).
  * Fine-grained chunk-level retrieval recall & candidate pool depth ablation ($K=50 \to K=100$).
  * Multi-threaded concurrency load testing (1 to 100 workers; 0 cross-session cache bleed).
  * Decoupled fixed-gold-evidence generation fidelity ($N=100$, $0.962$ Token F1).
  * Post-mutation index and cache invalidation consistency ($N=20$).
* **Git SHA Provenance**: Audited characterization commit `449e69b343dd8c3483120ea7b00bf193ea25df15`.

---

## ⚖️ 3. Rules for Manuscript Integration

1. **Never Merge Denominators**: Do not report 54.15% (baseline) alongside 63.4% (characterization) without citing their respective sample sizes ($N=301$ vs. $N=922$).
2. **Clarify Retrieval Granularity**: Report $0.9861$ as *Policy-Level Identification Recall* on the 301-query baseline, and $94.47\%$ as *Passage/Chunk-Level Retrieval Recall* on the 922-query characterization suite.
3. **Delineate Compilation Fixtures**:
   - Small-fixture speedup: $5{,}059\times$ (no-op) and $\sim 489\times$ (1-3 chunk deltas out of 127 mutable chunks).
   - Large-scale sweep: $24.95\times$ speedup (5% amendment delta across 3,000 chunks).
