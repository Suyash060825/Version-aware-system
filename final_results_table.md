# Final Audited Results Tables: Veritas System Characterization

This document contains the authoritative, publication-ready numerical tables corresponding to Tables 1–7 in [`Version_Aware_Ieee_CAMERA_READY.tex`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/Version_Aware_Ieee_CAMERA_READY.tex).

---

## Table 1: Architectural Comparison of Veritas with Related Retrieval Paradigms

| Architecture | Temporal Validity | Scope Invariant | Incr. Compilation | Adaptive Routing | Contradiction Mon. | Grounded Verif. | Audit Trace |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Standard Dense RAG | Unconstrained | Unconstrained | Full rebuild | Single path | None | None | None |
| Hybrid + RRF | Metadata filter | Optional | App-dep. | Dense+sparse | None | Heuristic | None |
| VersionRAG | Lineage graph | Not central | Lineage delta | Version-aware | None | None | None |
| Secure RAG | Unconstrained | Role/IAM filter | Full rebuild | Single path | Post-hoc | Prompt check | Partial |
| **Veritas** | **Date intervals** | **Role & clearance** | **7-stage delta** | **Fact+QA+Hyb+Diff** | **Cont. radar** | **NLI+citation** | **Audit ledger** |

---

## Table 2: Audited Evaluation Regimes and Experimental Scope

| Evaluation Regime | Corpus & Scale | Sample Size ($N$) | Primary Purpose |
| :--- | :--- | :---: | :--- |
| **Frozen Baseline** | 21 policies, 23 versions, 128 chunks | 301 queries | End-to-end Local vs. Cloud baseline fidelity |
| **Internal Repository** | Repository benchmark (`benchmark_all.json`) | 462 records | Developer regression testing; distinct from public suite |
| **Expanded Characterization** | 120 enterprise synthetic policies, 3,000 chunks | 922 queries | Granular system-characterization benchmark suite |
| **Security Matrix** | 120 policies $\times$ 32 user archetypes | 3,840 evaluations | Pre-retrieval role and confidentiality isolation |
| **Compiler Sweeps** | 3,000 structural chunks | 5 mutation trials | Incremental compile latency & re-embedding avoidance |
| **NLI Verification** | Pilot validation & dedicated suite | 20 pairs | Cross-encoder contradiction recall validation |
| **Mutation Consistency** | 20 incremental update cycles | 20 cycles | Post-mutation active/historical/tombstone integrity |
| **Concurrency Load** | Multi-worker load (1 to 100 threads) | 1,000 queries | Multi-user isolation, saturation, & lock contention |

---

## Table 3: Security and Governance Head-to-Head: Veritas vs. Baseline ($N=301$)

| System Configuration | Auth-Scope Correctness | Unsafe Leakage Rate | Authorized Ans. Ver. Acc. | Safe Abstention Precision |
| :--- | :---: | :---: | :---: | :---: |
| Naive RAG Baseline | 46.84% (141/301) | 53.16% (160/301) | 88.28% (113/128) | 0.00% (0/0) |
| **Veritas** | **100.0% (301/301)** | **0.00% (0/301)** | **88.07% (96/109)** | **100.0% (192/192)** |

*Expanded Characterization Result ($N=3,840$): 0 leaks / 3,840 evaluations ($1,840\text{ TP}, 2,000\text{ TN}, 0\text{ FP}, 0\text{ FN}$; 95% 1-sided upper bound $<0.08\%$).*

---

## Table 4: Generation Quality: Local Model vs. Cloud Model ($N=301$)

| Metric | Local (`qwen3:4b-q4_K_M`) | Cloud (`Gemini 2.0 Flash`) |
| :--- | :---: | :---: |
| **Version Resolution Rate (All Queries)** | 82.72% (249/301) | 82.72% (249/301) |
| **Version Acc. (Answered Queries)** | 86.30% (233/270) | 89.53% (231/258) |
| **Exact Correct Answer** | 27.91% (84/301) | 27.57% (83/301) |
| **Partially Correct Answer** | 20.27% (61/301) | 13.95% (42/301) |
| **Adversarial Refusal Accuracy** | 88.89% (16/18) | 100.0% (18/18) |
| **Token F1 (End-to-End RAG)** | 0.3516 | 0.3369 |
| **Token F1 (Fixed Gold Evidence, $N=100$)** | **0.9620** | **0.9650** |
| **Citation Precision** | 0.7973 | 0.7791 |
| **Citation Recall** | 0.2487 | 0.2704 |
| **Citation F1** | 0.2993 | 0.3183 |
| **System P50 Latency** | $29.65\ms$ | $71.63\ms$ |
| **System P95 Latency** | $136.49\ms$ | $85.27\ms$ |

---

## Table 5: Retrieval Subsystem Component Breakdown (Characterization, $N=922$)

| Subsystem Component | Recall@1 | Recall@5 | Recall@10 | MRR@10 | NDCG@10 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| BM25 Inverted Index Alone | 72.4% | 85.1% | 90.2% | 0.785 | 0.812 |
| Dense Vector (Chroma) Alone | 78.6% | 89.4% | 93.8% | 0.832 | 0.856 |
| Reciprocal Rank Fusion (RRF) | 88.2% | 96.1% | 98.5% | 0.915 | 0.934 |
| **RRF + FlashRank Cross-Encoder ($K=100$)** | **94.5%** | **98.8%** | **99.4%** | **0.962** | **0.978** |

*Candidate pool depth sensitivity on compound multi-clause queries ($N=50$): $K=50 \to 84.0\%$ (42/50); $K=100 \to 94.0\%$ (47/50).*

---

## Table 6: Route-Level Latency Breakdown (Local Model, $N=301$ Queries)

| Route Identifier | Traffic Share (\%) | Mean Latency ($\ms$) | P50 ($\ms$) | P95 ($\ms$) | P99 ($\ms$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `FAST_PATH_FACT` (Tier 0) | 48.50% | 20.90 | 20.19 | 33.71 | 41.54 |
| `FAST_PATH_QA` (Tier 1) | 5.65% | 23.62 | 23.28 | 29.16 | 33.54 |
| `HYBRID_RAG` (Tier 2) | 35.55% | 120.37 | 120.50 | 144.80 | 146.68 |
| `ABSTAINED` | 10.30% | 119.57 | 116.55 | 154.21 | 173.39 |
| **End-to-End System Composite** | **100.00%** | **66.57** | **29.65** | **136.49** | **146.69** |

*Characterization Suite ($N=922$): Deterministic and refusal paths accounted for 63.45% (585/922; Tier 0: 49.35%, Tier 1: 6.51%, Tier 3: 6.51%, Refusal: 1.08%). Sub-5ms P50: $0.95\ms$ (Tier 0), $1.85\ms$ (Tier 1), $2.10\ms$ (Tier 3).*

---

## Table 7: Incremental Compiler: Mutation Sweeps vs. Cold Rebuild

| Corpus & Mutation Condition | Mutated Chunks | Incremental Time | Cold Rebuild Time | Speedup Factor |
| :--- | :---: | :---: | :---: | :---: |
| **128-Chunk Fixture:** Hash No-Op | 0 chunks | $0.46\ms$ | $2,307.7\ms$ | $5{,}059.72\times$ |
| **128-Chunk Fixture:** 1-Chunk Delta | 1 chunk | $4.72\ms$ | $2,307.7\ms$ | $488.75\times$ |
| **128-Chunk Fixture:** 3-Chunk Delta | 3 chunks | $4.67\ms$ | $2,307.7\ms$ | $494.19\times$ |
| **3,000-Chunk Corpus:** 1.0% Delta | 30 chunks | $0.65\text{s}$ | $52.40\text{s}$ | $80.62\times$ |
| **3,000-Chunk Corpus:** 5.0% Delta | 150 chunks | $2.10\text{s}$ | $52.40\text{s}$ | **24.95$\times$** |
| **3,000-Chunk Corpus:** 10.0% Delta | 300 chunks | $4.80\text{s}$ | $52.40\text{s}$ | $10.92\times$ |
| **3,000-Chunk Corpus:** 25.0% Delta | 750 chunks | $12.50\text{s}$ | $52.40\text{s}$ | $4.19\times$ |
