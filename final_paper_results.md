# Veritas Manuscript: Final Publication-Safe Results Section

*Draft of Section VI (Empirical Results and Analysis) incorporating both the Frozen Baseline Benchmark and the Expanded System Characterization Suite with complete numerical provenance.*

---

## VI. Empirical Results and Analysis

We evaluate \sys{} across two complementary regimes: (1) a **Frozen Baseline Benchmark** ($N=301$ queries across a 21-policy, 128-chunk corpus with 10 simulated users) evaluating end-to-end Local vs.\ Cloud generation fidelity; and (2) an **Expanded System Characterization Suite** ($N=922$ queries across 120 policies, 600 versions, and 3,000 chunks with 32 user archetypes) stress-testing pre-retrieval authorization isolation, candidate pool depth sensitivity, multi-threaded concurrency, and large-scale incremental compilation sweeps.

### A. Security and Pre-Retrieval Authorization Scope Enforcement
Table~II reports governance and security performance. In the baseline evaluation ($N=301$), 109 queries target authorized policy provisions while 192 represent out-of-scope departments, restricted confidentiality tiers, or adversarial jailbreaks. An unrestricted baseline evaluates retrieval without pre-reranking eligibility gating, resulting in 160 authorization violations (a 53.16\% unsafe exposure rate). In contrast, \sys{} enforces the Composite Eligibility Predicate $E(c,u,t_q)=V(c,t_q)\cdot A(c,u)$ prior to candidate admission, achieving 100.0\% authorization decision correctness (301/301) with zero unauthorized evidence leakage ($\text{TP}=109, \text{TN}=192, \text{FP}=0, \text{FN}=0$).

In the expanded characterization suite ($N=3,840$ cross-user evaluation decisions spanning 32 user archetypes and 120 policies), \sys{} similarly observed **zero unauthorized evidence leaks** entering the reranker or generative prompt context (1,840 TP, 2,000 TN, 0 FP, 0 FN; one-sided 95\% upper bound $<0.08\%$). Crucially, on authorized answerable queries, \sys{} achieves 88.07\% version accuracy (96/109 in baseline) and 88.3\% in characterization, confirming that strict pre-retrieval access gating provides security isolation without degrading retrieval fidelity on legitimate inquiries.

### B. Temporal Validity, Generation Quality, and Decoupled Fidelity
Table~III compares local (\texttt{qwen3:4b-q4\_K\_M}) and cloud (\texttt{Gemini 2.0 Flash}) models under invariant enforcement. Overall version resolution across all 301 baseline queries is 82.72\% (249/301). Among answered queries (excluding safe abstentions), version selection accuracy reaches 86.30\% (233/270) locally and 89.53\% (231/258) with Gemini. Adversarial refusal accuracy reaches 88.89\% locally (16/18) and 100.0\% with Gemini (18/18). High citation precision (0.7973 local, 0.7791 Gemini) confirms that emitted citations correspond to authoritative evidence.

While end-to-end surface exact-match accuracy is 27.91\% (Token F1: 0.3516), we decoupled generation fidelity from upstream retrieval omissions by feeding exact gold evidence chunks directly into the model (**Fixed Gold Evidence Evaluation**, $N=100$). Under fixed gold context, \sys{} achieves a **Mean Token F1 of 0.962** (95\% CI: $[0.941, 0.983]$) and 100.0\% target concept accuracy. This empirical separation confirms that end-to-end answer discrepancies stem primarily from passage retrieval omissions and valid paraphrastic surface variation rather than generative hallucination.

### C. Retrieval Subsystem Progression and Candidate Depth Sensitivity
Table~IV reports retrieval metrics across pipeline stages. In the expanded characterization suite ($N=922$ queries, 877 answerable subset), BM25 alone achieves Recall@1 of 72.4\% ($668/922$), Dense vector retrieval achieves 78.6\% ($725/922$), and Reciprocal Rank Fusion (RRF) reaches 88.2\% ($813/922$). FlashRank Cross-Encoder reranking achieves **94.47\% Recall@1** ($871/922$) and 99.4\% Recall@10 (MRR: 0.962, NDCG@10: 0.978).

Sensitivity analysis on complex multi-clause queries (Category D, $N=50$) reveals an important candidate pool depth dependency: setting candidate beam depth to $K=50$ yields 84.0\% Recall@1 (42/50), whereas expanding candidate depth to $K=100$ improves Recall@1 to **94.0\%** (47/50). Because cross-encoders only score items admitted by upstream retrieval, candidate pool depth is a governing factor for compound multi-constraint queries.

### D. Route-Level Latency and Deterministic Fast-Path Offload
In the baseline benchmark ($N=301$), deterministic fast-path routes resolve 54.15\% of traffic (Tier~0 Fact Lookup: 48.50\%, P50 $20.19\ms$; Tier~1 Canonical QA: 5.65\%, P50 $23.28\ms$), driving overall system median latency to $29.65\ms$. In the expanded characterization suite ($N=922$), deterministic fast-path routes resolve **63.4\% of queries** (Tier~0: 49.35\%, Tier~1: 6.51\%, Tier~3 Diff: 6.51\%, Refusal: 1.08\%), achieving a sub-5ms P50 latency ($0.95\ms$ for Tier~0, $1.85\ms$ for Tier~1, $2.10\ms$ for Tier~3).

### E. Incremental Knowledge Compilation Sweeps
Table~V details compiler performance across mutation sweeps. On the 128-chunk baseline fixture, hash no-ops ($|\Delta|=0$) achieve $5{,}059.72\times$ speedup ($0.46\ms$ vs.\ $2,307.71\ms$), while 1- and 3-chunk mutations achieve $488.75\times$ and $494.19\times$ speedup ($4.72\ms$ vs.\ $2,307.71\ms$). 

On the 3,000-chunk enterprise corpus sweep, SHA-256 chunk-level hash tracking avoided re-embedding for exactly **99.0\%** ($2,970/3,000$) of chunks under a 1.0\% amendment rate ($0.65\text{s}$ compile time, $80.6\times$ speedup) and exactly **95.0\%** ($2,850/3,000$) under a 5.0\% amendment rate ($2.10\text{s}$ compile time vs.\ $52.40\text{s}$ cold rebuild, **$24.95\times$ speedup**, 95\% CI: $[23.8\times, 26.1\times]$).

### F. Multi-Threaded Concurrency and Post-Mutation Consistency
Load testing across 1, 10, 25, 50, and 100 concurrent workers ($1,000$ multi-threaded queries) confirmed **100.0\% session and cache isolation** (0 scope leaks, 0 cache contaminations, 0 race conditions). Throughput scaled to $234.7\text{ QPS}$ at 1 worker and plateaued near $137\text{ QPS}$ at 50–100 workers, with median latency rising from $4.35\ms$ to $317.82\ms$ due to thread-lock synchronization under contention. Post-mutation testing across 20 update cycles confirmed 100\% active-version retrieval, preserved historical point-in-time access, 100\% tombstone purging from BM25 and vector stores, and instant L1/L2 cache invalidation.

### G. Confidence Calibration Generalization and NLI Verification
Post-hoc isotonic regression reduces Expected Calibration Error (ECE) from 0.148 to **0.041** on the held-out validation split (Brier score: 0.5855 to 0.1839). When evaluated on heterogeneous open-distribution runtime queries, runtime ECE rises to **0.2954** (Brier score: 0.6401), demonstrating empirical distribution sensitivity and prompting the use of confidence as an informational ranking signal rather than a hard binary gate. In NLI verification, the DeBERTa-v3 verifier achieved 100.0\% contradiction recall across both the pilot validation set ($5/5$) and the dedicated contradiction test suite ($20/20$).
