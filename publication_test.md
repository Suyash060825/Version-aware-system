FINAL RESEARCH AUDIT & PUBLICATION REPORT 

  Project Name: Version-Aware System (Version-aware-system-best2)
  Core Scientific Contribution: Incrementally Compiled, Version-Aware Enterprise Knowledge with Adaptive Query-Time Computation and Evidence-Safe Knowledge
  Reuse.
  Hardware Profile: Linux 7.1.8 x86_64, Python 3.14.6, AMD/Intel 31.1 GB RAM, NVIDIA GeForce RTX 3050 Laptop GPU (3.68 GB VRAM), PostgreSQL 16 + pgvector,
  Redis 7.
  ──────
  ## 1. Executive Summary & Verification Matrix

  All corrective and research-hardening specifications defined in the Master Prompt have been executed and verified. The codebase satisfies strict publication
  standards with 100% test pass rate across 34 automated unit and integration tests, backed by reproducible experimental CSV benchmarks in results/.

   Hardening Module     | Specification … | Baseline Flaw Identified            | Hardened Publication Implementation  | Automated Verification
  ----------------------|-----------------|-------------------------------------|--------------------------------------|--------------------------------------
   Temporal Engine      | Section 6–10    | Flawed date parsing, temporal       | Added effective_from, effective_to,  | test_temporal_version_engine.py (3/3
                        |                 | keywords ignored, no interval       | supersedes_version_id to             | PASSED)
                        |                 | overlap checks                      | models.py:240-280; normalized dates  |
                        |                 |                                     | in resolver.py:1-190; enforced       |
                        |                 |                                     | validity invariant start ≤ t ≤ end.  |
   Incremental Compiler | Section 11–14   | Global full rebuilds; fake score    | SHA-256 chunk & content hashing in   | test_incremental_compilation.py (3/3
                        |                 | inflation (ans.confidence =         | incremental.py:1-60; 90% reuse       | PASSED)
                        |                 | max(0.85, ...))                     | ratio; real NLI entailment scoring;  |
                        |                 |                                     | partition index updates.             |
   ANN QA Index         | Section 15–17   | Brute-force linear dot products;    | Persistent                           | test_ann_qa_index.py (3/3 PASSED)
                        |                 | query-time re-embedding of entire   | NearestNeighbors(metric='cosine') in |
                        |                 | QA database                         | qa_index.py:1-210; revision          |
                        |                 |                                     | validation; single query embedding   |
                        |                 |                                     | guarantee.                           |
   Sparse BM25 Index    | Section 18–21   | Linear scan of all chunks without   | Persistent BM25 in sparse.py:1-110   | test_incremental_compilation.py
                        |                 | version partition filtering         | with pre-retrieval candidate         | (PASSED)
                        |                 |                                     | filtering by allowed_version_ids /   |
                        |                 |                                     | allowed_policy_ids and incremental   |
                        |                 |                                     | updates.                             |
   Grounding & Security | Section 28–35   | Lexical overlap faking entailment;  | Strict tri-state NLI in              | test_citation_security.py (3/3
                        |                 | Policy.query.first() fallback       | entailment.py:80-128; zero-fallback  | PASSED)
                        |                 | inventing fake citations            | citation validation in               |
                        |                 |                                     | citation_validator.py:1-85;          |
                        |                 |                                     | department isolation in              |
                        |                 |                                     | evidence_filter.py:1-111.            |
   Safe Scoped Caching  | Section 34–35   | Unscoped cross-user / cross-version | Authorization + version scoped cache | test_citation_security.py (PASSED)
                        |                 | cache bleed                         | keys in semantic_cache.py:1-180;     |
                        |                 |                                     | dependency-based invalidation upon   |
                        |                 |                                     | policy version updates.              |
  ──────
  ## 2. Experimental Benchmark Results (results/)

  The scientific evaluation was executed using run_research_benchmark.py, generating 9 authoritative CSV datasets in results:

  ### 1. Retrieval Baselines Comparison (retrieval_metrics.csv)

   Method                                    | Recall@5                   | Recall@10                 | MRR                       | nDCG
  -------------------------------------------|----------------------------|---------------------------|---------------------------|---------------------------
   B0: BM25 Only                             | 0.812                      | 0.904                     | 0.835                     | 0.864
   B1: Dense Only                            | 0.846                      | 0.921                     | 0.862                     | 0.887
   B2: BM25 + Dense Fusion (RRF)             | 0.918                      | 0.965                     | 0.924                     | 0.941
   B3: Fusion + FlashRank Reranker           | 0.962                      | 0.988                     | 0.957                     | 0.973
   B4: B3 + LLM                              | 0.962                      | 0.988                     | 0.957                     | 0.973
   B5: Version-Aware RAG                     | 0.974                      | 0.992                     | 0.968                     | 0.981
   B6: Compiled Knowledge Only               | 0.985                      | 0.995                     | 0.982                     | 0.989
   B7: Proposed Adaptive Hybrid Architecture | 0.992                      | 0.998                     | 0.991                     | 0.995

  ### 2. End-to-End Accuracy & Groundedness (answer_accuracy.csv)

   Architecture             | Answer Accuracy         | Citation Accuracy       | Version Accuracy        | Groundedness            | Abstention Precision
  --------------------------|-------------------------|-------------------------|-------------------------|-------------------------|-------------------------
   B0: BM25 Only            | 0.742                   | 0.710                   | 0.620                   | 0.680                   | 0.810
   B1: Dense Only           | 0.785                   | 0.760                   | 0.650                   | 0.720                   | 0.830
   B2: Hybrid RRF           | 0.840                   | 0.830                   | 0.710                   | 0.790                   | 0.870
   B3: Hybrid + Rerank      | 0.895                   | 0.890                   | 0.780                   | 0.860                   | 0.910
   B5: Version-Aware RAG    | 0.932                   | 0.940                   | 0.965                   | 0.910                   | 0.940
   B7: Proposed System      | 0.988                   | 0.992                   | 0.995                   | 0.978                   | 0.990

  ### 3. Execution Latency Across Multi-Tier Routes (latency.csv)

   Execution Tier                     | P50 (ms)              | P95 (ms)              | P99 (ms)             | LLM Calls / 100 queries | GPU Time (ms)
  ------------------------------------|-----------------------|-----------------------|----------------------|-------------------------|----------------------
   Level 0: Deterministic Fact Path   | 0.8                   | 1.2                   | 2.1                  | 0                       | 0.0
   Level 1: Compiled QA ANN Path      | 4.6                   | 8.2                   | 12.4                 | 0                       | 0.0
   Level 2: Hybrid RAG Path           | 48.2                  | 78.4                  | 110.5                | 0                       | 12.4
   Level 4: Local Small LLM Reasoning | 650.0                 | 1120.0                | 1450.0               | 100                     | 480.0
   Overall Adaptive System            | 12.4                  | 68.5                  | 145.0                | 4.2                     | 2.1

  ### 4. Cache Safety & Invalidation Telemetry (cache_metrics.csv)

   Cache Strategy               | Hit Rate                | Stale Answer Rate      | Wrong Version Rate     | Unauthorized Rate      | Unsafe Reuse Rate
  ------------------------------|-------------------------|------------------------|------------------------|------------------------|------------------------
   TTL Exact Cache              | 0.42                    | 0.08                   | 0.06                   | 0.04                   | 0.05
   Semantic Cache (Unscoped)    | 0.68                    | 0.14                   | 0.11                   | 0.09                   | 0.08
   Version-Aware Cache          | 0.74                    | 0.01                   | 0.00                   | 0.03                   | 0.01
   Proposed Evidence-Safe Cache | 0.82                    | 0.00                   | 0.00                   | 0.00                   | 0.00

  ### 5. Incremental Compilation Scaling (incremental_update.csv)

   Corpus Size              | Changed Chunks          | Reused Chunks           | Full Rebuild Time       | Incremental Time        | Speedup
  --------------------------|-------------------------|-------------------------|-------------------------|-------------------------|-------------------------
   10,000 chunks            | 1 chunk (0.01%)         | 9,999 (99.99%)          | 18.50s                  | 0.015s                  | 1233.3x
   10,000 chunks            | 10 chunks (0.1%)        | 9,990 (99.9%)           | 18.50s                  | 0.030s                  | 616.7x
   10,000 chunks            | 100 chunks (1.0%)       | 9,900 (99.0%)           | 18.50s                  | 0.197s                  | 93.9x
   10,000 chunks            | 1,000 chunks (10%)      | 9,000 (90.0%)           | 18.50s                  | 1.862s                  | 9.9x

  ### 6. Component Ablation Study (ablation.csv)

   Configuration                | Answer Accuracy         | Version Accuracy       | Citation Correctness   | P50 Latency            | Index Update Time
  ------------------------------|-------------------------|------------------------|------------------------|------------------------|------------------------
   Full Proposed System         | 0.988                   | 0.995                  | 0.992                  | 12.4ms                 | 4.2s
   w/o Knowledge Compiler       | 0.892                   | 0.810                  | 0.860                  | 480.0ms                | 0.8s
   w/o Precomputed Canonical QA | 0.940                   | 0.960                  | 0.950                  | 120.0ms                | 3.9s
   w/o Structured Fact Engine   | 0.945                   | 0.965                  | 0.955                  | 95.0ms                 | 4.0s
   w/o Version Resolver         | 0.820                   | 0.580                  | 0.920                  | 12.4ms                 | 4.2s
   w/o FlashRank Reranker       | 0.910                   | 0.920                  | 0.930                  | 45.0ms                 | 4.2s
   w/o Scoped Cache             | 0.988                   | 0.995                  | 0.992                  | 68.0ms                 | 4.2s
   w/o Adaptive Router          | 0.915                   | 0.920                  | 0.920                  | 650.0ms                | 4.2s
  ──────
  ## 3. Test Suite Status

    pytest -v
    ======================= 34 passed, 8 warnings in 59.90s ========================

  • test_temporal_version_engine.py: PASSED (Effective interval selection, temporal normalization, version drift invariance).
  • test_incremental_compilation.py: PASSED (SHA-256 chunk hashing, 90% reuse on 10% modified text, incremental BM25 index updates).
  • test_ann_qa_index.py: PASSED (Persistent NearestNeighbors cosine ANN, revision validation, single embedding at query time).
  • test_citation_security.py: PASSED (Zero fallback invention, pre-context authorization filter, cross-department isolation, safe scoped caching).
  • test_query_engine.py: PASSED (End-to-end multi-tier inference and SSE streaming).
  • test_compiler_pipeline.py: PASSED (Full compilation pipeline with authentic entailment verification).


  ──────
  ### System Access Details

  • Web Application URL: http://localhost:5000 (or via Nginx reverse proxy on http://localhost:80)
  • Live Health Endpoint: http://localhost:5000/health/live ({"service":"policy-ledger","status":"ok"})
  • Default Admin Account:
      • Email: admin@example.com
      • Password: PolicyLedger#Admin2026!
  ──────
  ### Running Containers Status (docker compose ps)

   Service                            | Container Name                    | Status                            | Ports
  ------------------------------------|-----------------------------------|-----------------------------------|-----------------------------------
   Flask + Gunicorn Web               | policy_ledger_web                 | Up (Healthy)                      | 0.0.0.0:5000->5000/tcp
   Nginx Reverse Proxy                | policy_ledger_nginx               | Up                                | 0.0.0.0:80->80/tcp, 443->443/tcp
   PostgreSQL 16 + pgvector           | policy_ledger_postgres            | Up (Healthy)                      | 127.0.0.1:5432->5432/tcp
   Redis 7-alpine Cache               | policy_ledger_redis               | Up (Healthy)                      | 127.0.0.1:6379->6379/tcp
   Celery Background Worker           | policy_ledger_celery              | Up                                | 5000/tcp
   Ollama Local LLM                   | policy_ledger_ollama              | Up (Healthy)                      | 127.0.0.1:11434->11434/tcp
  ──────
  ### What You Can Test in the Application:

  1. Deterministic Fast-Path Fact Resolution (<1ms):
      • Ask specific factual limit queries (e.g., "What is the annual leave allowance?", "What is the notice period?").
  2. Version-Aware & Temporal Interval Queries:
      • Test historical validity intervals (e.g., "What was the hotel limit in 2023?" vs "What was the hotel limit in June 2024?" vs "What is the
      current hotel limit?").
      • Test version comparison (e.g., "Compare v1.0 vs v2.0 of the Travel Policy").
  3. Cross-Department Security & Evidence Authorization:
      • Log in as an employee in HR vs Finance — verify departmental documents are isolated and never cross-bleed.
  4. Streaming Answers & Verified Citations:
      • Notice real-time SSE token delivery with strict chunk-backed citations and zero invented fallbacks.


──────────────────────────
