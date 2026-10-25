# REPORT A: EXECUTIVE AUDIT SUMMARY

**Project:** Veritas: Version-Aware Enterprise Policy Intelligence via Incremental Knowledge Compilation and Adaptive Multi-Tier Retrieval  
**Audit Conducted:** 2026-10-25  
**Auditor Classification:** Independent Principal Software Architect & Senior Retrieval / AI Safety Evaluator  
**Audit Directory:** `audit_reports/comprehensive_repository_audit_20261025_125500/`  
**Operational Status:** Read-Only Forensic Audit Phase Completed  

---

## 1. Overall Engineering & Scientific Assessment

Veritas represents an ambitious, multi-faceted enterprise policy intelligence platform that combines hybrid retrieval (dense embeddings via FastEmbed BAAI/bge-small-en-v1.5 and sparse BM25Okapi via rank-bm25), reciprocal rank fusion (RRF), cross-encoder neural reranking (FlashRank / Qwen3-Reranker-0.6B), deterministic structured fact resolution, canonical question compilation (FAISS HNSW), natural-language claim verification (NLI), and temporal version resolution.

However, a skeptical, forensic investigation of the codebase reveals a **significant gap between the architectural and research claims published in documentation/papers and the actual running code in the repository**. Several high-profile guarantees are either non-existent in the runtime path, bypassed by hardcoded heuristic escapes, disabled by default in production configurations, or distorted by artificial metric calculations.

### Summary Rating Methodology
This rating is a strict engineering assessment based on production readiness, architectural soundess, threat-model resistance, and scientific reproducibility:
* **Core Deterministic Retrieval & Caching Architecture:** `7.5 / 10` (Fast paths, FAISS overlays, and scoped L1 caches are well-structured, but suffer from concurrency race conditions and multi-worker invalidation gaps).
* **Enterprise Authorization & RBAC Boundaries:** `4.0 / 10` (CRITICAL: Authorization check functions exist and pass tests, but permission revocation is never called in production admin routes; several admin endpoints lack role checks; and cross-instance revocation relies on an unconsumed Redis pub/sub channel).
* **AI Safety & Grounding Entailment:** `3.5 / 10` (CRITICAL: Neural NLI verification is disabled by default via `ENTAILMENT_ENABLED=false` in production Docker; when enabled, answers are accepted as grounded unless actively contradicting with score > 0.65; prompt injection defenses on policy text are non-existent).
* **Scientific & Research Integrity:** `2.5 / 10` (CRITICAL DEFECT: Baseline retrieval evaluation scripts synthesized `retrieved_chunk_ids` directly from expected ground truth; Token F1 was artificially boosted with a `contains_bonus` floor of 0.70; Recall@1, 5, 10 are identical to 17 decimal places because citations were evaluated instead of candidate sets; and the claimed 5,059x incremental compilation speedup is based on comparing a no-op hash check against cold compilation).

---

## 2. Strongest Aspects of the Implementation

1. **Sub-millisecond Deterministic Fast Paths (Tier 0 & Tier 1):**  
   The combination of structured regex fact matching (`FactResolver`) and FAISS HNSW precomputed canonical Q&A (`QAMatcher`) successfully bypasses LLM inference for 55–80% of routine corporate queries, delivering genuine sub-5ms P50 latency for simple factual inquiries.
2. **Strict Pre-filtering Scope Construction (`QueryScope`):**  
   When properly invoked, `QueryScope` cleanly encapsulates `tenant_id`, `user_id`, `role`, `department_ids`, and `allowed_confidentiality`, applying hard filtering before hybrid retrieval executes in `query_engine.py`.
3. **Structured Version Interval Modeling (`models.py`):**  
   The `PolicyVersion` schema provides clean temporal fields (`effective_date`, `created_at`, `status`, `diff_json`) and supports clause-level diffing between versions via `PolicyDiffEngine`.
4. **Resilient Local-First Container Topology:**  
   The Docker Compose environment properly containerizes Nginx, Gunicorn, PostgreSQL 16 with pgvector, Redis 7, Celery, and Ollama, eliminating reliance on third-party cloud APIs.

---

## 3. Most Serious Confirmed Defects (P0 & P1)

| Finding ID | Severity | Category | File & Function | Root Defect Summary |
|---|---|---|---|---|
| **VULN-01** | **P0** | Security / RBAC | `blueprints/admin.py:885, 903` | **Permission Revocation Completely Bypassed in Admin Endpoints:** When an administrator toggles a user active status or changes their role, `revoke_user_permission()` is never called. Users retain privileged access in Redis/L1 cache for up to 3,600s. |
| **VULN-02** | **P0** | Security / RBAC | `rag/authorization/evidence_filter.py:67` | **Orphaned Redis Pub/Sub Revocation Channel:** `revoke_user_permission` publishes to `veritas:auth_revocations`, but no worker, background task, or thread in the repository ever subscribes to this channel. Multi-worker Gunicorn deployments fail to synchronize revocations. |
| **VULN-03** | **P0** | Security / Auth | `rag/api/rag_routes.py:340, 437, 470, 525` | **Missing RBAC on Admin RAG Endpoints:** `/rag/admin/dashboard` has zero role checks, allowing ordinary employees to view all search queries and costs. `/admin/delete/<id>` only checks `can_manage_policies()`, permitting managers to purge any policy from the vector index. |
| **DEF-01** | **P0** | Safety / Grounding | `rag/verification/entailment.py:31` | **NLI Verification Disabled by Default in Production:** `ENTAILMENT_ENABLED` defaults to `false`. In Docker Compose, the variable is omitted, causing `verify()` to return unconditional `ENTAILMENT` (100% grounded) on every answer. |
| **DEF-02** | **P0** | Safety / Grounding | `rag/engine/query_engine.py:724` | **Groundedness Filter Inversion (Non-Contradiction as Entailment):** In `query_engine.py`, `is_grounded = (verdict != "CONTRADICTION")`. Unsupported claims with zero entailment (e.g. `verdict == "UNKNOWN"`, score 0.05) are accepted as grounded. |
| **DEF-03** | **P0** | Temporal Correctness | `models.py:304` | **Unbounded Validity Stretching Across Version Gaps:** `effective_to` calculates `next_ver.effective_from - 1 day`. If Policy Version 1 expired in 2019 and Version 2 started in 2021, the system bridges the 2020 gap, returning Version 1 for 2020 queries when no policy was valid. |
| **DEF-04** | **P0** | Temporal Retrieval | `rag/indexing/index_policy.py:8` & `pipeline.py:236` | **Superseded Version Timestamp Orphan in Vector DB:** When compiling Version 2.0, Version 1.0 chunks in ChromaDB and BM25 are never updated. Version 1.0 retains `valid_to_ts = 32472144000` (year 2999), causing both versions to match historical interval queries. |
| **RES-01** | **P0** | Research Integrity | `evaluation/run_scale_benchmark.py:311` | **Benchmark Retrieval Synthesis Fraud:** In `run_scale_benchmark.py`, `retrieved_chunk_ids` is hardcoded as `q.expected_evidence_chunks if r["answer_correctness"] else []`, copying gold references into retrieval outputs. |
| **RES-02** | **P0** | Research Integrity | `evaluation/metrics.py:64` | **Token F1 Metric Inflation:** `compute_token_f1()` was modified to award an artificial `contains_bonus` of `max(base_f1, 0.70)` if the reference string appears in the prediction, falsifying reported F1 scores. |
| **RES-03** | **P0** | Research Integrity | `evaluation/run_benchmark.py:501` | **Evaluation of Citations Instead of Retrieval Candidates:** Benchmark scripts logged answer citations as `retrieved_policy_ids` (length 1), forcing `Recall@1 == Recall@5 == Recall@10` to 17 decimal places across all reported tables. |
| **ARCH-01** | **P1** | Architecture | `models.py:1291` & `rag/retrieval/dense.py` | **Fabricated pgvector Architecture Claim:** The IEEE paper and documentation repeatedly claim that PostgreSQL 16 with pgvector performs dense retrieval. In reality, `PolicyChunkV2` has no vector column, and dense retrieval is executed purely against ChromaDB and FAISS. |
| **PERF-01** | **P1** | Performance / Tail | `rag/generation/provider.py:121` | **Unmitigated 21-27 Second CPU LLM Latency Tail:** While deterministic queries finish in <5ms, any query requiring local Qwen 4B on CPU incurs an extreme latency spike (P99: 21,065 ms), hidden in published tables by reporting only P50/P95 over mostly-fast-path traffic. |

---

## 4. Highest-Risk Unverified Areas

1. **Concurrent Compilation Race Conditions:**  
   `PersistentBM25Index.update_policy_version()` and `CanonicalQAIndex.save()` perform uncoordinated atomic file overwrites. When multiple Celery workers compile documents simultaneously, lost updates occur, purging one worker's index changes from disk.
2. **Distributed Cache Synchronization Under Failure:**  
   The L2 semantic vector cache (`MultiLevelCache._local_l2`) is purely in-memory in each Python process and is never persisted to Redis. In multi-worker Gunicorn or multi-pod Kubernetes setups, L2 cache entries are completely isolated and never invalidated across workers.
3. **Database Connection Leaks in Background Threads:**  
   `PersistentBM25Index.rebuild_from_db()` spins up independent `create_app('default')` instances outside request contexts when triggered asynchronously, risking orphaned database connections under high thread churn.

---

## 5. Features Implemented but Insufficiently Tested

1. **Document Parsing Tables and Layouts:**  
   `_extract_docx()` only extracts `doc.paragraphs`, completely dropping `doc.tables`. Neither unit tests nor adversarial tests assert table preservation.
2. **NLI Verification with Genuine Neural Models:**  
   The test environment lacks PyTorch. All passing NLI tests actually executed the simplistic lexical keyword fallback, which suffers from a 43.6% false-negative rate on contradictions.
3. **Multi-Policy Comparative Routing:**  
   Complex queries crossing multiple departmental policies fall through to single-policy retrieval filters when semantic title similarity exceeds 0.75, suppressing cross-policy evidence.

---

## 6. Features that Appear Incomplete or Abandoned

1. **PostgreSQL pgvector Integration:**  
   Despite `pgvector>=0.2.5` in `requirements.txt` and `pgvector/pgvector:pg16` in `docker-compose.yml`, no pgvector tables or queries exist in the codebase.
2. **Celery Contradiction and Knowledge Graph Tasks:**  
   `tasks.scan_contradictions_task` and `tasks.rebuild_knowledge_graph_task` in `tasks.py` contain empty mock function bodies returning static counts without performing any processing.
3. **Original Chunker Module (`rag/chunking/chunker.py`):**  
   The system maintains two independent chunking systems: `rag/chunking/chunker.py` (sliding window with overlap) and `rag/compiler/structure_extractor.py` (sentence splitting without overlap). The production compilation pipeline only uses `structure_extractor.py`, leaving `chunker.py` dead code.

---

## 7. Five Highest-Priority Next Actions

1. **Remediate Administrative Authorization & Pub/Sub Revocation:**  
   Wire `revoke_user_permission(user_id)` into all user mutation routes in `blueprints/admin.py`, replace per-call `redis.Redis.from_url` with a pooled connection, and implement an active Redis revocation listener in application workers.
2. **Purge Synthetic Metric Manipulations:**  
   Revert `metrics.py` to standard SQuAD token F1 (delete `contains_bonus = max(base_f1, 0.70)`), remove `return ret_ver == exp_ver_seq or True` in `_chunks_match()`, and re-evaluate retrieval candidate pools rather than final citations.
3. **Fix Temporal Validity Gap-Bridging in `models.py`:**  
   Refactor `PolicyVersion.effective_to` to check for explicit policy or version expiration dates, ensuring that periods between distinct policy versions return `None` (fail-closed / abstain).
4. **Synchronize Vector Store Timestamps on Version Supersession:**  
   Update `KnowledgeCompilerPipeline._stage_index()` to retroactively update `valid_to_ts` and `is_active` for all prior versions of a policy in ChromaDB and BM25 whenever a newer version is indexed.
5. **Decouple and Align Architectural Claims:**  
   Either implement true PostgreSQL pgvector indexing in `models.py` or update the manuscript to honestly state that ChromaDB and FAISS HNSW are the sole dense vector engines.
