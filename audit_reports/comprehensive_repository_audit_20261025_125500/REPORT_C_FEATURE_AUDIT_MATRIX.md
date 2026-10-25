# REPORT C: FEATURE-BY-FEATURE AUDIT MATRIX

**Project:** Veritas Enterprise Policy Intelligence Platform  
**Audit Dimension:** Phase Two Complete Feature Verification (Features 1 through 24)  
**Evaluation Standard:** Production Systems & IEEE Journal Review Criteria  

---

## 1. Master Feature Verification Matrix

| Feature | Implemented? | Correctness | Security | Performance | Integration | Test Quality | Main Findings & Evidence |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **F1: Document Ingestion** | Implemented | Partially verified | Partially verified | Verified in tested scope | Partially verified | Defective | `_extract_docx()` drops all tables (`doc.paragraphs` only). `extract_document()` hardcodes `max_chars=60000` in `admin.py:310`, silently truncating large policy uploads. |
| **F2: Document Chunking** | Implemented | Defective | Verified in tested scope | Verified in tested scope | Partially verified | Defective | Dual architecture: `chunk_policy()` (with overlap) is dead code; production `structure_extractor.py` splits on double-newlines and `. ` with zero overlap, fragmenting decimal values and separating exceptions from rules. |
| **F3: Version Management & Temporal Resolution** | Implemented | Defective | Verified in tested scope | Verified in tested scope | Partially verified | Defective | `PolicyVersion.effective_to` calculates `next_ver.effective_from - 1 day` (`models.py:304`), artificially bridging validity across multi-year policy gaps. `test_audit_adversarial.py:178` avoided testing the gap. |
| **F4: Incremental Knowledge Compilation** | Implemented | Defective | Verified in tested scope | Partially verified | Defective | Incomplete | Chunks of prior versions are never updated when newer versions are compiled. Staged compilation is non-transactional; worker crashes leave orphaned SQL chunks without vector representations. |
| **F5: Sparse Retrieval** | Implemented | Partially verified | Verified in tested scope | Defective | Partially verified | Partially verified | `update_policy_version()` instantiates `BM25Okapi` over entire corpus on every delta. Parallel file writes lack file locks (`PersistentBM25Index.save()`), causing lost index updates under concurrent compilation. |
| **F6: Dense Retrieval** | Implemented | Partially verified | Verified in tested scope | Verified in tested scope | Partially verified | Partially verified | FastEmbed BGE-small dense embeddings functional via ChromaDB. However, published claims of PostgreSQL pgvector dense storage are completely fabricated (`models.py` has no vector column). |
| **F7: Hybrid Retrieval & RRF** | Implemented | Verified in tested scope | Verified in tested scope | Verified in tested scope | Verified in tested scope | Partially verified | RRF ($K=60$) is mathematically implemented. Ties systematically favor dense candidates due to insertion order in dictionary traversal (`hybrid.py:22`). |
| **F8: Cross-Encoder Reranking** | Implemented | Partially verified | Verified in tested scope | Partially verified | Partially verified | Defective | FlashRank ONNX reranker works, but silently falls back to `MockReranker` (pass-through) on failure without error reporting. Pre-rerank candidate pool is hard-truncated to 35 candidates. |
| **F9: Adaptive Multi-Tier Query Routing** | Implemented | Partially verified | Verified in tested scope | Verified in tested scope | Defective | Partially verified | Classification assigns Complexity 0 (Fact) to 4 (Reasoning), but `answer()` forces all Fact/QA queries that miss deterministic paths into extractive string slicing, preventing LLM reasoning. |
| **F10: Deterministic Answering** | Implemented | Partially verified | Verified in tested scope | Verified in tested scope | Verified in tested scope | Partially verified | `FactResolver` delivers sub-3ms responses, but outputs unqualified values (`val_unit according to policy`), omitting conditions and exceptions and creating misleading certainty for subgroup queries. |
| **F11: Local LLM Generation** | Implemented | Partially verified | Defective | Defective | Partially verified | Defective | Ollama Qwen3 local inference is functional, but exhibits an extreme 21–27s CPU latency tail. Retreived policy text is directly interpolated into prompt strings without delimiter isolation against prompt injection. |
| **F12: Evidence Construction & Citations** | Implemented | Verified in tested scope | Verified in tested scope | Verified in tested scope | Verified in tested scope | Partially verified | `_extract_best_evidence_context()` generates clean multi-sentence citations, but reordering citations based on title keyword repetition can prioritize background clauses over exceptions. |
| **F13: NLI Claim Verification & Grounding** | Implemented | Defective | Defective | Verified in tested scope | Defective | Defective | `ENTAILMENT_ENABLED` defaults to `false` in production. PyTorch is missing from environment. When enabled, `query_engine.py:724` accepts any answer where `verdict != "CONTRADICTION"`, allowing ungrounded hallucinations to pass. |
| **F14: Safe Abstention & Uncertainty** | Implemented | Verified in tested scope | Verified in tested scope | Verified in tested scope | Verified in tested scope | Verified in tested scope | Verified fail-closed abstention when candidate evidence is zero or confidence gate fails. Properly abstains with `DEFAULT_REFUSAL_MESSAGE`. |
| **F15: Authentication & RBAC Boundaries** | Implemented | Defective | Defective | Verified in tested scope | Defective | Defective | CRITICAL P0: `revoke_user_permission()` is never called in `blueprints/admin.py` when user roles or active status are modified. Redis pub/sub channel has no subscribers. Multiple admin endpoints lack role checks. |
| **F16: Semantic Cache & Redis** | Implemented | Defective | Partially verified | Partially verified | Defective | Partially verified | L2 vector cache is strictly local in-memory (`_local_l2`) and is never persisted to Redis. `invalidate_policy()` performs $O(N)$ sequential Redis GETs. L2 cache cannot be invalidated across workers. |
| **F17: Database & Transaction Integrity** | Implemented | Partially verified | Verified in tested scope | Partially verified | Partially verified | Partially verified | Relational tables properly indexed with foreign keys. However, dynamic ORM property `effective_to` causes $N+1$ queries, and pgvector schema integration is non-existent. |
| **F18: Celery & Distributed Concurrency** | Implemented | Defective | Verified in tested scope | Partially verified | Defective | Defective | `scan_contradictions_task` and `rebuild_knowledge_graph_task` are empty stubs. Concurrent compilation of different policies creates race conditions on shared BM25 and FAISS disk files. |
| **F19: API & Input Validation** | Implemented | Partially verified | Defective | Verified in tested scope | Verified in tested scope | Partially verified | `/rag/admin/dashboard` has zero role checks (accessible to employees). Input length is capped at 1,000 characters, but query guardrail allows prompt injection if keywords like "policy guidelines" appear. |
| **F20: Configuration & Deployment** | Implemented | Partially verified | Defective | Verified in tested scope | Partially verified | Partially verified | `.env` file containing plaintext production secrets is stored in the workspace directory. Docker Compose configuration is well-structured but omits `ENTAILMENT_ENABLED`. |
| **F21: Error Handling & Fallbacks** | Implemented | Defective | Defective | Verified in tested scope | Defective | Defective | Multiple silent fallbacks compromise system guarantees: LLM timeout silently falls back to unverified extractive context; NLI failure silently defaults to unverified acceptance; Redis failure defaults to stale local epochs. |
| **F22: Performance & Resource Efficiency** | Implemented | Partially verified | Verified in tested scope | Defective | Partially verified | Defective | Deterministic queries execute in <5ms, but live LLM generation incurs a 21–27s P99 latency on CPU. Latency reports hide this tail by evaluating mostly fast-path and abstained queries. |
| **F23: Observability & Diagnostics** | Implemented | Verified in tested scope | Verified in tested scope | Verified in tested scope | Verified in tested scope | Partially verified | Comprehensive Prometheus metrics registered across cache hits, retrieval latency, and model tokens. Structured logging captures query route decisions. |
| **F24: Test Suite Quality** | Implemented | Defective | Defective | Verified in tested scope | Defective | Defective | Tests assert weak invariants (e.g. `assert contra_tp > 0`). Unit tests run with mocks or in-memory SQLite, avoiding concurrent multi-worker hazards. Test authors actively altered queries to avoid testing gap bridging. |

---

## 2. Supporting Evidence Details

### Feature 1: Document Ingestion Table Loss
* **Evidence:** In `rag/parser/pdf_parser.py:150-169`, `_extract_docx()` iterates solely over `doc.paragraphs`. If an enterprise employee handbook defines salary ranges or leave accruals in a Word table (`doc.tables`), the entire table is discarded.
* **Reproduction:** Ingesting a standard `.docx` with a 4-column benefits table produces 0 characters of table text.

### Feature 3: Gap Bridging in Temporal Resolution
* **Evidence:** In `models.py:301-305`:
  ```python
  next_ver = PolicyVersion.query.filter(
      PolicyVersion.policy_id == self.policy_id,
      PolicyVersion.version_num > self.version_num
  ).order_by(PolicyVersion.version_num.asc()).first()
  if next_ver and next_ver.effective_from:
      return next_ver.effective_from - timedelta(days=1)
  ```
  If Version 1.0 has `effective_date = 2018-01-01` and Version 2.0 has `effective_date = 2021-01-01`, Version 1.0's `effective_to` becomes `2020-12-31`. The system falsely certifies that Version 1.0 was effective throughout 2019 and 2020.

### Feature 13: Entailment Verification Inversion
* **Evidence:** In `rag/engine/query_engine.py:724`:
  ```python
  is_grounded = (getattr(entail_res, "verdict", "UNKNOWN") != "CONTRADICTION")
  ```
  If the NLI model returns `verdict = "UNKNOWN"` with an entailment score of `0.02`, `is_grounded` evaluates to `True`. Answers with zero evidentiary support are certified as grounded.

### Feature 15: Missing Revocation in Administrative Handlers
* **Evidence:** In `blueprints/admin.py:885-910`, `user_toggle()` and `user_set_role()` execute `db.session.commit()` but never call `revoke_user_permission(user.id)`. The user's active epoch in Redis and memory remains unchanged, allowing deactivated or demoted users to retrieve cached privileged answers.
