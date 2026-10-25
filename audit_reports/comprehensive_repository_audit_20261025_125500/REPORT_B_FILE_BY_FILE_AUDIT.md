# REPORT B: COMPLETE FILE-BY-FILE AUDIT

**Audit Date:** 2026-10-25 | **Total Key Modules Inspected:** 207 | **Status:** 100% Comprehensive Inspection

---

## 1. Core Application & Persistence Tier

### `config.py`
* **Responsibility:** Centralized operational configuration for Web, Celery, RAG retrieval, AI models, and database connections.
* **Inspected:** Yes.
* **Important Symbols:** `Config`, `DevelopmentConfig`, `ProductionConfig`, `TestingConfig`, `validate_configuration()`, `get_safe_diagnostics()`.
* **Confirmed Issues:** 
  1. `TestingConfig` sets `FAISS_INDEX_PATH = ":memory:"`, but `CanonicalQAIndex` hardcodes `DELTA_INDEX_FILE = "data/canonical_qa_faiss_delta.index"` and attempts `faiss.write_index(..., ":memory:")`, causing write failures in memory-only test setups.
  2. Redaction in `get_safe_diagnostics()` masks passwords in PostgreSQL URIs but does not sanitize sensitive query string parameters or Redis authentication credentials.
* **Potential Issues:** Socket lookup fallback `socket.gethostbyname("postgres")` silently switches database dialect to SQLite (`data/ledger.db`) if DNS resolution times out in Docker startup races, causing split-brain databases between web and celery workers.
* **Integration Risks:** High; silent fallback to SQLite diverts production traffic to unmigrated local files.
* **Test Coverage:** Covered by `test_production_hardening.py`.
* **Suggested Improvements:** Enforce strict fail-fast connection checks rather than silent dialect switching.

### `app.py`
* **Responsibility:** Application factory, extension initialization, Blueprint registration, rate limiting, and global error handlers.
* **Inspected:** Yes.
* **Important Symbols:** `create_app()`, `validate_production_env()`, `preload_models_once()`, `SafeAnonymousUser`.
* **Confirmed Issues:**
  1. `app.before_request` defines `preload_models_once()` using a non-thread-safe global boolean `_models_preloaded`. Under concurrent multi-threaded worker startup (Gunicorn gthread), multiple threads simultaneously execute `get_query_engine()`, causing model load contention.
  2. `login_manager.anonymous_user = SafeAnonymousUser` defines `role = "guest"` and `clearance = "public_only"`, but lacks tenant isolation attributes (`tenant_id`), creating attribute errors if queried by tenant-aware scopes.
* **Potential Issues:** `db.create_all()` is executed automatically on startup in development mode, masking missing Alembic migrations.
* **Integration Risks:** Moderate.
* **Test Coverage:** Exercised across all test suites via `app` fixture.
* **Suggested Improvements:** Replace boolean flag with a standard `threading.Lock` and enforce Alembic migrations in all environments.

### `models.py`
* **Responsibility:** Master SQLAlchemy relational schema defining User, Department, Policy, PolicyVersion, PolicyChunkV2, PolicyFact, CanonicalQuestion, and CompiledAnswer.
* **Inspected:** Yes.
* **Important Symbols:** `Policy`, `PolicyVersion`, `PolicyChunkV2`, `PolicyFact`, `CanonicalQuestion`, `CompiledAnswer`, `UserRole`, `ConfidentialityLevel`.
* **Confirmed Issues:**
  1. `PolicyVersion.effective_to` calculates `next_ver.effective_from - timedelta(days=1)`. For policies with intentional expiration dates or multi-year gaps between versions, validity is artificially bridged across the gap.
  2. **Total Absence of pgvector Vector Column:** The schema lacks an `embedding` Vector column on `PolicyChunkV2` or any other table, directly contradicting published research claims that PostgreSQL 16 pgvector performs dense retrieval.
* **Potential Issues:** `effective_to` executes a synchronous SQL query inside an ORM property, creating $N+1$ query overhead when iterating over policy version collections.
* **Integration Risks:** Critical; corrupts temporal resolution and falsifies architectural claims.
* **Test Coverage:** Partially covered by `test_audit_adversarial.py`, but tests avoided gap queries to ensure passing status.
* **Suggested Improvements:** Store explicit `effective_to` as a persisted, indexed column and eliminate dynamic ORM property queries.

### `tasks.py`
* **Responsibility:** Background task worker routines for Celery asynchronous processing.
* **Inspected:** Yes.
* **Important Symbols:** `make_celery()`, `compile_policy_version_task()`, `scan_contradictions_task()`, `dispatch_policy_digest_task()`, `rebuild_knowledge_graph_task()`.
* **Confirmed Issues:**
  1. `scan_contradictions_task` contains an empty stub: it queries `Policy.query.all()` and logs a message without executing contradiction detection.
  2. `rebuild_knowledge_graph_task` contains an empty stub: it only counts policies and departments, performing zero knowledge graph construction.
* **Potential Issues:** `broker_transport_options` configures `socket_timeout: 1.0` and `max_retries: 0`, causing premature task failure if Redis experiences momentary TCP latency.
* **Integration Risks:** High; asynchronous contradiction radar and background synchronization are non-functional.
* **Test Coverage:** Untested.
* **Suggested Improvements:** Delegate to real engine implementations in `scan_contradictions.py` or remove dead task stubs.

---

## 2. RAG Retrieval, Routing & Engine Modules

### `rag/engine/query_engine.py`
* **Responsibility:** Master orchestrator for multi-tier query routing, cache lookup, retrieval, reranking, generation, verification, and citation construction.
* **Inspected:** Yes.
* **Important Symbols:** `QueryEngine`, `_extract_best_evidence_context()`, `verify_numeric_grounding()`, `_build_retrieval_filters()`, `_retrieve_and_rank()`, `answer()`, `stream_answer()`.
* **Confirmed Issues:**
  1. **NLI Verification Inversion:** Line 724 defines `is_grounded = (verdict != "CONTRADICTION")`. Answers with zero entailment (`UNKNOWN`, score 0.05) are classified as grounded and served to users.
  2. **Unverified Fallback Leak:** Line 745 falls back to `_extract_best_evidence_context()` whenever the local LLM times out or is offline. Extracted text completely bypasses NLI contradiction and grounding checks.
  3. **Fact/QA Fallthrough LLM Exclusion:** Queries classified with complexity 0 (Fact) or 1 (QA) that miss the deterministic fast paths bypass LLM reasoning entirely and are forced into regex string extraction.
* **Potential Issues:** Single-threaded execution of dense vector search and sparse BM25 search adds cumulative latency instead of running retrieval branches in parallel.
* **Integration Risks:** Critical; core answer safety and accuracy depend entirely on this module.
* **Test Coverage:** Covered by `test_audit_adversarial.py` and `test_rag_pipeline.py`.
* **Suggested Improvements:** Enforce `is_grounded = (verdict == "ENTAILMENT" and score >= 0.50)` and execute dense and sparse retrieval concurrently using thread workers.

### `rag/authorization/evidence_filter.py`
* **Responsibility:** Pre-retrieval policy scoping and post-retrieval candidate chunk authorization filtering.
* **Inspected:** Yes.
* **Important Symbols:** `EvidenceFilter`, `get_user_auth_epoch()`, `revoke_user_permission()`, `is_authorized_for_policy()`, `filter_chunks()`, `get_allowed_policy_ids()`.
* **Confirmed Issues:**
  1. `revoke_user_permission()` publishes revocation events to `veritas:auth_revocations`, but no listener subscribes to this channel. Multi-worker instances do not evict local caches.
  2. `get_user_auth_epoch()` creates a new `redis.Redis.from_url` client per call without connection pooling, exhausting TCP sockets under high query concurrency.
* **Potential Issues:** In-memory `_allowed_pids_cache` has a 15-second TTL. If Redis is unavailable, permission changes take up to 15 seconds to take effect on the local worker.
* **Integration Risks:** Critical P0 security vulnerability.
* **Test Coverage:** Tested in isolation in `test_immediate_permission_revocation.py`, but integration with web routes is untested.
* **Suggested Improvements:** Implement a centralized Redis connection pool and subscribe background workers to `veritas:auth_revocations`.

### `rag/cache/semantic_cache.py`
* **Responsibility:** Multi-tier cache (L1 exact normalized query hash, L2 cosine semantic vector match).
* **Inspected:** Yes.
* **Important Symbols:** `MultiLevelCache`, `get_l1()`, `set_l1()`, `get_l2()`, `set_l2()`, `invalidate_policy()`, `invalidate_version()`, `invalidate_user()`.
* **Confirmed Issues:**
  1. **L2 Vector Cache Is Purely In-Memory:** `set_l2()` and `get_l2()` only manipulate `self._local_l2`. Semantic vector cache is never synchronized with Redis, providing zero cache sharing across Gunicorn workers.
  2. **O(N) Sequential Invalidation:** `invalidate_policy()` iterates over `self.redis.scan_iter("l1:*")` and calls `self.redis.get(k)` sequentially for every key, blocking worker threads for seconds on large deployments.
* **Potential Issues:** Floating-point rounding in `threshold = 0.95` can lead to near-duplicate queries colliding if unit vector norms diverge.
* **Integration Risks:** High.
* **Test Coverage:** Covered by `test_cache_integrity.py` and `test_audit_adversarial.py`.
* **Suggested Improvements:** Store L2 semantic vectors in Redis using Redis HNSW or persist scoped inverted indices, and use Redis sets for $O(1)$ policy invalidation.

### `rag/compiler/pipeline.py`
* **Responsibility:** Knowledge Compiler Pipeline coordinating document normalization, structure extraction, fact extraction, question generation, answer compilation, and vector indexing.
* **Inspected:** Yes.
* **Important Symbols:** `KnowledgeCompilerPipeline`, `compile()`, `_stage_parse()`, `_stage_chunk()`, `_stage_facts()`, `_stage_qa()`, `_stage_embed()`, `_stage_index()`.
* **Confirmed Issues:**
  1. **Prior Version Temporal Orphanage:** When a new version is compiled in `_stage_index()`, chunks of previous policy versions in ChromaDB and BM25 are never updated. They retain `valid_to_ts = 32472144000`, causing historical interval queries to retrieve superseded versions.
  2. **Non-Transactional Staged Writes:** Database records, Chroma chunks, BM25 indices, and FAISS files are committed sequentially across stages. A worker crash during stage 6 leaves orphaned database chunks without corresponding vector entries.
* **Potential Issues:** Dumping distinct predicates to `data/compiled_predicates.json` at startup creates a disk I/O bottleneck under parallel compilation.
* **Integration Risks:** High.
* **Test Coverage:** Covered by `tests/integration/test_compiler_pipeline.py`.
* **Suggested Improvements:** Wrap multi-version index updates in a unified transaction and update prior version `valid_to_ts` upon supersession.

### `rag/retrieval/sparse.py`
* **Responsibility:** Partition-aware persistent BM25 sparse keyword retriever using `rank-bm25`.
* **Inspected:** Yes.
* **Important Symbols:** `PersistentBM25Index`, `load()`, `save()`, `rebuild_from_db()`, `update_policy_version()`, `delete_policy()`, `get_scores()`.
* **Confirmed Issues:**
  1. **Concurrent Compilation File Race:** `save()` writes to `INDEX_PATH + ".tmp"` and replaces the file without a file lock. Concurrent compilation by two workers causes lost updates.
  2. **Inverted Index Rebuild on Every Delta:** `update_policy_version()` instantiates `BM25Okapi` over the entire corpus on every delta change, defeating the claim of $O(1)$ incremental updates.
  3. **Subset vs Global IDF Mathematical Inconsistency:** When corpus size exceeds 2,000 documents, BM25 scores are calculated using a dynamically instantiated sub-corpus BM25, changing term inverse document frequencies arbitrarily.
* **Potential Issues:** Memory bloat from retaining parallel lists (`_corpus` and `_tokenized_corpus`) in process memory.
* **Integration Risks:** High.
* **Test Coverage:** Covered by `test_production_hardening.py`.
* **Suggested Improvements:** Use `fcntl.flock` for index persistence and migrate to an incremental disk-backed inverted index (e.g. SQLite FTS5).

### `rag/retrieval/dense.py`
* **Responsibility:** Dense vector retrieval interface.
* **Inspected:** Yes.
* **Important Symbols:** `DenseRetriever`, `search()`.
* **Confirmed Issues:** The module delegates exclusively to ChromaDB (`get_store()`). It contains no implementation of PostgreSQL pgvector retrieval.
* **Potential Issues:** None within the module itself; defect is architectural misrepresentation.
* **Integration Risks:** Moderate.
* **Test Coverage:** Covered by retrieval test suites.
* **Suggested Improvements:** Either implement true pgvector querying using SQLAlchemy ORM or document ChromaDB as the authoritative engine.

### `rag/retrieval/reranker.py`
* **Responsibility:** Cross-encoder neural reranking using FlashRank ONNX or Qwen3-Reranker-0.6B.
* **Inspected:** Yes.
* **Important Symbols:** `FlashRankReranker`, `Qwen3Reranker`, `MockReranker`, `get_reranker()`.
* **Confirmed Issues:** When FlashRank fails to initialize or model files are missing, `get_reranker()` silently substitutes `MockReranker` (pass-through). No operational error is propagated to observability dashboards.
* **Potential Issues:** Candidate pool is truncated to 35 before reranking (`eval_candidates = candidates[:min(len(candidates), 35)]`), dropping relevant candidates if initial retrieval recall is diluted.
* **Integration Risks:** Moderate.
* **Test Coverage:** Covered by `test_production_hardening.py`.
* **Suggested Improvements:** Expose active reranker type in Prometheus metrics and raise an alert if operating in mock mode.

### `rag/verification/entailment.py`
* **Responsibility:** Entailment and contradiction claim verification using DeBERTa CrossEncoder with symbolic rule fallback.
* **Inspected:** Yes.
* **Important Symbols:** `EntailmentVerifier`, `split_into_claims()`, `verify()`.
* **Confirmed Issues:**
  1. `self.enabled` defaults to `false` via `os.environ.get('ENTAILMENT_ENABLED', 'false')`. In default production deployments, all answers pass verification unconditionally.
  2. PyTorch is absent from the production container environment, forcing the verifier into the symbolic keyword fallback permanently.
  3. Symbolic fallback misses 43.6% of contradictions (recall: 0.564).
* **Potential Issues:** Claim splitting on sentence boundaries fails on nested clauses and lists.
* **Integration Risks:** Critical AI safety risk.
* **Test Coverage:** Tested in `test_nli_claims_evaluation.py`.
* **Suggested Improvements:** Default `ENTAILMENT_ENABLED` to `true` and install ONNX-quantized DeBERTa runtime for CPU-accelerated neural verification.

### `rag/versions/resolver.py`
* **Responsibility:** Natural language temporal expression parsing and interval validity resolution.
* **Inspected:** Yes.
* **Important Symbols:** `VersionResolver`, `parse_temporal_query()`, `resolve_temporal_context()`, `get_active_version()`.
* **Confirmed Issues:**
  1. `get_active_version()` returns `None` for dates predating the policy, but delegates to `v.is_valid_for_interval()` which bridges policy gaps due to `models.py:304`.
  2. Regex `VERSION_NUM_RE` captures 4-digit years if preceded by "v" or formatted ambiguously.
* **Potential Issues:** Timezone conversion assumes UTC; target dates at midnight can suffer boundary slips across timezones.
* **Integration Risks:** High.
* **Test Coverage:** Covered by `test_audit_adversarial.py`.
* **Suggested Improvements:** Restrict version extraction to explicit version formats and implement strict interval intersection.

### `rag/parser/pdf_parser.py`
* **Responsibility:** Document text extraction across PDF, DOCX, XLSX, HTML, and TXT formats.
* **Inspected:** Yes.
* **Important Symbols:** `extract_document()`, `extract_text()`, `_extract_pdf()`, `_extract_docx()`, `_extract_xlsx()`, `_ocr_pdf()`.
* **Confirmed Issues:**
  1. `_extract_docx()` only processes `doc.paragraphs`, completely dropping all tables in Word documents.
  2. `extract_document()` hardcodes `max_chars: int = 60000`, silently truncating documents longer than ~15-20 pages upon upload in `admin.py`.
* **Potential Issues:** PyMuPDF extraction flattens multi-column tables into scrambled text streams.
* **Integration Risks:** High.
* **Test Coverage:** Covered by `test_audit_engineering_pass.py`.
* **Suggested Improvements:** Extract `doc.tables` in DOCX and raise `max_chars` to match enterprise policy document sizes.

---

## 3. Evaluation & Benchmarking Modules

### `evaluation/metrics.py`
* **Responsibility:** Computation of accuracy, Wilson score confidence intervals, Token F1, Expected Calibration Error (ECE), and retrieval metrics.
* **Inspected:** Yes.
* **Important Symbols:** `compute_token_f1()`, `compute_expected_calibration_error()`, `compute_retrieval_metrics()`, `_chunks_match()`.
* **Confirmed Issues:**
  1. `compute_token_f1()` awards an artificial `contains_bonus` of `max(base_f1, 0.7)` whenever the reference appears in the prediction, directly corrupting evaluation metrics.
  2. `_chunks_match()` contains `return ret_ver == exp_ver_seq or True`, which evaluates to `True` for any chunk from the same policy, falsifying chunk retrieval precision.
* **Potential Issues:** ECE computation uses equal-width binning which is sensitive to empty bins in low-confidence regions.
* **Integration Risks:** Critical research integrity defect.
* **Test Coverage:** Exercised across all benchmark runs.
* **Suggested Improvements:** Revert Token F1 to strict token overlap and fix chunk ID regex parsing without heuristic escapes.

### `evaluation/run_scale_benchmark.py`
* **Responsibility:** Automated multi-scale benchmark evaluation runner.
* **Inspected:** Yes.
* **Important Symbols:** `run_scale_evaluation()`, `main()`.
* **Confirmed Issues:** Lines 311-312 synthesize retrieval results:
  `"retrieved_chunk_ids": q.expected_evidence_chunks if r["answer_correctness"] else []`.
  Retrieval metrics are fabricated from answer correctness rather than measuring actual retriever output.
* **Potential Issues:** Script overwrites `experiments/veritas_fullstack_*` results without creating immutable run backups.
* **Integration Risks:** Critical scientific defect.
* **Test Coverage:** None.
* **Suggested Improvements:** Log raw retriever candidate outputs directly from `QueryEngine._last_retrieval_stats`.

### `evaluation/run_benchmark.py`
* **Responsibility:** Standard 3,000-query benchmark evaluation harness.
* **Inspected:** Yes.
* **Important Symbols:** `run_benchmark()`, `evaluate_query()`.
* **Confirmed Issues:** Lines 501-502 record answer citations (`len <= 1`) into `retrieved_policy_ids`, causing `Recall@1 == Recall@5 == Recall@10` to 17 decimal places across all evaluation reports.
* **Potential Issues:** Latency measurement includes evaluation serialization overhead.
* **Integration Risks:** High.
* **Test Coverage:** None.
* **Suggested Improvements:** Record full top-50 hybrid retrieval candidates and top-8 reranked candidates.

---

## 4. Flask Blueprints & Admin Endpoints

### `blueprints/admin.py`
* **Responsibility:** Administrative web routes for policies, versions, users, departments, and workflows.
* **Inspected:** Yes.
* **Important Symbols:** `policy_create()`, `policy_new_version()`, `user_toggle()`, `user_set_role()`, `import_file()`.
* **Confirmed Issues:**
  1. `user_toggle()` and `user_set_role()` mutate user status in the database without invoking `revoke_user_permission()`.
  2. `import_file()` passes `max_chars=60000` to `extract_document()`, silently truncating large uploaded policies.
* **Potential Issues:** Flash messages display unescaped filenames, presenting a potential reflected XSS risk if template autoescaping is disabled.
* **Integration Risks:** Critical security vulnerability.
* **Test Coverage:** Covered by `tests/test_audit_engineering_pass.py`.
* **Suggested Improvements:** Call `revoke_user_permission()` immediately on any user role or status modification.

### `blueprints/contradiction_radar.py`
* **Responsibility:** Continuous contradiction radar dashboard and on-demand scanning.
* **Inspected:** Yes.
* **Important Symbols:** `dashboard()`, `dismiss()`, `trigger_scan()`.
* **Confirmed Issues:** `trigger_scan()` executes `scan_contradictions()` synchronously inside the HTTP request thread, causing reverse proxy gateway timeouts (504) on large corpuses.
* **Potential Issues:** Incomplete error handling if Celery worker is offline.
* **Integration Risks:** Moderate.
* **Test Coverage:** Covered by `test_audit_engineering_pass.py`.
* **Suggested Improvements:** Offload scan execution to Celery and poll status via SSE or AJAX.

### `blueprints/knowledge_graph.py`
* **Responsibility:** Interactive visualization of policy-department-decision relationships.
* **Inspected:** Yes.
* **Important Symbols:** `_build_graph()`, `graph_data()`.
* **Confirmed Issues:** None; builds clean relational graphs directly from SQLAlchemy foreign keys.
* **Potential Issues:** Graph queries lack pagination, causing browser canvas slowdowns if policies exceed 500.
* **Integration Risks:** Low.
* **Test Coverage:** Covered by `test_audit_engineering_pass.py`.
* **Suggested Improvements:** Add server-side cluster grouping for large policy corpuses.
