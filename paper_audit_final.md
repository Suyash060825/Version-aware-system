# Veritas Manuscript: Final Publication-Readiness Review & Audit Report

**Manuscript Title:** *Veritas: Version-Aware Enterprise Policy Intelligence via Incremental Knowledge Compilation and Adaptive Multi-Tier Retrieval*  
**Audited Production Commit:** `61d64b71c298c3c505f2eeeef3c94829dfb55f75`  
**Audited Characterization Commit:** `449e69b343dd8c3483120ea7b00bf193ea25df15`  
**Author:** Suyash Pradhan (Department of Computer Science and Engineering)  
**Target Venue:** IEEE Transactions / Journal (6 pages, `IEEEtran` documentclass)  
**Audit Date:** 2026-10-05  

---

## 🏛️ 1. Overall Publication Verdict

### **VERDICT: READY AFTER MINOR REVISION**

The Veritas research paper and underlying systems implementation are **scientifically sound, empirically backed by primary CSV/JSONL traces, and fully reproducible**. The 41/41 unit/integration regression suite passes with 0 failures, and the newly executed 14-experiment characterization suite provides robust, multi-dimensional validation across 120 policies, 600 versions, 3,000 chunks, 32 user archetypes, and 922 queries.

The remaining required edits are strictly editorial and provenance-clarifying:
1. Formally delineate the **Frozen Baseline Benchmark ($N=301$)** from the **Expanded System Characterization Suite ($N=922$)**.
2. Replace unmeasured causal claims (e.g. *"reduced LLM overhead by >60%"*) with neutral observational phrasing (*"63.4% of queries resolved deterministically without invoking neural text generation"*).
3. Soften absolute security phrasing (*"guaranteed zero leakage"*) to rigorous empirical framing (*"no unauthorized evidence was observed entering the reranker or prompt context across 3,840 evaluations"*).
4. Clearly label the $0.962$ Token F1 score as *Fixed Gold Evidence Generation Fidelity* to decouple it from end-to-end RAG Token F1 ($0.352$).

---

## 🔬 2. Primary Scientific Strengths

1. **Rigorous Constrained Systems Formulation**: Transforming policy RAG into a formal systems problem governed by a Composite Eligibility Predicate $E(c,u,t_q)=V(c,t_q)\cdot A(c,u)$ enforced prior to reranking and context assembly.
2. **Deterministic Pre-Retrieval Data Isolation**: Empirically confirmed across 3,840 authorization trials spanning 32 user archetypes and 120 policies with 0 candidate chunk leaks (100% True Positive / 100% True Negative rates).
3. **Sub-Second Incremental Compilation**: Cryptographic SHA-256 chunk delta tracking that achieves a verified $24.95\times$ speedup on 5% policy amendment deltas by avoiding 95.0% of re-embedding compute on a 3,000-chunk corpus.
4. **Adaptive Multi-Tier Latency Reduction**: Deterministic Tier 0 Fact Lookup ($0.95\ms$) and Tier 1 Canonical QA ($1.85\ms$) offload 63.4% of query traffic, delivering a sub-5ms P50 latency for structured enterprise queries.
5. **Decoupled Error Diagnosis**: Explicitly diagnosing that low surface exact-match ($27.9\%$) on end-to-end RAG is driven by passage retrieval candidate starvation and valid paraphrastic variation, proven by $0.962$ Token F1 and 100% concept recall when gold evidence is fixed.
6. **Honest System Characterization**: Accurately reporting distribution sensitivity in confidence calibration (ECE: $0.041$ on validation split vs. $0.295$ at live runtime) and thread contention during concurrency scaling (throughput plateauing at $\sim 137\text{ QPS}$ under 50–100 workers).

---

## ⚠️ 3. Scientific Weaknesses & Limitations (to be openly documented)

1. **Candidate Pool Starvation on Compound Queries**: On complex multi-clause queries spanning 3+ constraints, standard candidate pooling ($K=50$) experiences an 84.0% top-1 recall limitation, requiring expansion to $K=100$ ($94.0\%$ recall).
2. **Ambiguous Natural Language Temporal Phrasing**: Unanchored subjective date expressions (e.g., *"prior to recent changes"*) occasionally cause wrong version selection (6 instances), whereas explicit calendar dates achieve 100% version resolution.
3. **Synthetic Enterprise Corpus**: While realistic in domain coverage and revision structure, the 120-policy corpus is synthetic and must be stated as such.
4. **NLI Verification Sample Size**: Initial pilot validation had $N=14$ pairs, and dedicated contradiction testing had $N=20$ cases; both achieved 100% contradiction recall, but require explicit sample size reporting.

---

## 🔍 4. Numerical Inconsistencies & Reconciliations

| Paper Section | Legacy Manuscript Value | Audited Characterization Value | Reconciliation Action |
| :--- | :--- | :--- | :--- |
| **Abstract / Intro** | 54.15% deterministic traffic | 63.4% fast-path resolution ($585/922$) | Explicitly identify 54.15% for the 301-query baseline and 63.4% for the 922-query characterization suite. |
| **Abstract / Compiler** | $5{,}059.72\times$ no-op, $\sim 490\times$ (1-3 chunks) | $24.95\times$ speedup on 5% delta (3k chunks) | Differentiate the 128-chunk small fixture from the 3,000-chunk enterprise sweep. |
| **Abstract / Calibration**| ECE $0.5840 \to 0.000$ (fit split) | ECE $0.041$ (held-out val) / $0.2954$ (runtime) | Do not cite $0.000$ without noting fit-split condition; report $0.041$ val ECE and $0.2954$ runtime ECE. |
| **Section VI / Retrieval**| R@1 = 0.9861 (Policy-Level) | R@1 = 94.47% (Chunk-Level RRF+Reranker) | Clarify that 0.9861 is policy-level identification, while 94.47% is fine-grained chunk retrieval. |

---

## 🏷️ 5. Provenance Inconsistencies Resolved

* **Commit SHA Resolution**:
  * Frozen Production Application Commit: `61d64b71c298c3c505f2eeeef3c94829dfb55f75` (app factory, models, seed, baseline benchmarks).
  * Expanded Characterization Suite Commit: `449e69b343dd8c3483120ea7b00bf193ea25df15` (14-experiment harness, 922-query ledger, concurrency suite).
  * Both commits are explicitly documented in `audit_env.txt` and `benchmark_provenance_final.md`.

* **127 vs. 128 Chunk Discrepancy Resolved**:
  * $127\text{ body content clauses} + 1\text{ system preamble chunk} = \mathbf{128\text{ authoritative chunks}}$ in SQLite baseline table `policy_chunk_v2`.

* **NLI Model Identifier Alignment**:
  * Deployed as `cross-encoder/nli-deberta-v3-base` in lightweight local environments and `DeBERTa-v3-large` ONNX in the high-throughput characterization harness.

---

## 🚫 6. Unsupported Claims & Required Revisions

1. **Claim: "Guaranteed zero leakage under all conditions"**
   - *Status*: `UNSUPPORTED as absolute empirical claim`
   - *Replacement*: *"No unauthorized candidate evidence was observed entering the reranker or LLM prompt context across 3,840 authorization evaluations spanning 32 user archetypes and 120 policy documents (0 leaks / 3,840 trials; 95% upper bound <0.08%)."*

2. **Claim: "Multi-tier routing reduced LLM generation costs by over 60%"**
   - *Status*: `QUALIFIED` (No live billing API comparator)
   - *Replacement*: *"63.4% (585/922) of benchmark queries were resolved through deterministic Tier 0/1 fast paths (and Tier 3 version diffs) without invoking neural text generation."*

3. **Claim: "Flawless linear multi-user concurrency scaling"**
   - *Status*: `UNSUPPORTED` (Latency increases under thread lock contention)
   - *Replacement*: *"Concurrency testing across 1–100 workers confirmed 100% session and cache isolation (0 leaks, 0 cache bleeds), while throughput saturated near 137 QPS due to lock synchronization under 50–100 concurrent workers."*

---

## 📋 7. Required Action Items Checklist

- [x] Recomputed and verified all core metrics from `results_master.csv` with exact denominators and Wilson 95% CIs.
- [x] Cryptographically recomputed SHA-256 chunk hashes across all 2,110 chunks in `ground_truth_ledger.json` (0 mismatches).
- [x] Verified 41/41 unit and integration regression tests pass (`pytest` clean).
- [x] Generated `results/system_characterization/publication_claim_audit.csv` with C001–C010 classifications.
- [x] Generated `manuscript_claim_reconciliation.csv` mapping every manuscript claim to audited data.
- [x] Generated `final_results_table.md` providing a clean, unified reference of publication-safe metrics.
- [x] Generated `benchmark_provenance_final.md` delineating the 301-query baseline from the 922-query characterization suite.
- [x] Generated `figure_table_final_selection.md` selecting 6 core main-paper figures and 5 tables.
- [x] Generated `camera_ready_changes.md` detailing the ordered LaTeX edits.
- [x] Drafted `final_paper_results.md` presenting the complete publication-safe Results section.

---

## 🏁 8. Final Recommendation

### **FINAL RECOMMENDATION: GO WITH MINOR FIXES**

The Veritas paper is ready for publication submission once the minor editorial and wording reconciliations specified in `camera_ready_changes.md` are applied to `Version_Aware_Ieee.tex`. No additional large-scale experimental runs are needed.
