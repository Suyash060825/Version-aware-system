# Veritas Database Schema & Data Contract Consistency Report

**Audit Date:** 2026-10-21  
**Database Engine:** PostgreSQL 16.6 (`pgvector/pgvector:pg16`) with `vector` extension version `0.8.6`  
**ORM Framework:** SQLAlchemy 3.1+ (`flask_sqlalchemy`)  
**Scope:** 47 database relations, foreign keys, unique constraints, vector dimensions, and data contracts.

---

## 1. Schema Invariants & Constraint Audit

| Table | Invariant / Constraint | Database Enforcement | Application Mapping | Status |
|---|---|---|---|---|
| **`policy`** | Unique policy code / title index | `ix_policy_policy_id`, `ix_policy_department_id` | `models.Policy` | **VERIFIED** |
| **`policy_version`** | At most one active version per policy | Partial unique index: `uix_one_active_version_per_policy` (`WHERE is_active = true`) | `models.PolicyVersion.is_active` | **VERIFIED** |
| **`policy_chunk_v2`** | Unique global chunk ID | `ix_policy_chunk_v2_chunk_id` (`UNIQUE`) | `models.PolicyChunkV2.chunk_id` | **VERIFIED** |
| **`policy_chunk_v2`** | SHA-256 Text deduplication hash | `ix_policy_chunk_v2_text_hash` (`btree`) | `models.PolicyChunkV2.text_hash` | **VERIFIED** |
| **`policy_chunk_v2`** | Multi-attribute embedding hash | `ix_policy_chunk_v2_embedding_hash` (`btree`)| `models.PolicyChunkV2.embedding_hash`| **VERIFIED** |
| **`canonical_question`**| Foreign keys to policy & version | `canonical_question_policy_id_fkey`, `version_id_fkey` | `models.CanonicalQuestion` | **VERIFIED** |
| **`compiled_answer`** | Foreign key to canonical question | `compiled_answer_canonical_question_id_fkey`| `models.CompiledAnswer` | **VERIFIED** |
| **`user`** | Unique user email & clearance | `ix_user_email` (`UNIQUE`), `clearance` | `models.User` | **VERIFIED** |

---

## 2. Vector Embedding Dimension Consistency

- **Configured Dimension:** 384 (`BAAI/bge-small-en-v1.5` dense representation).
- **Postgres pgvector:** Enabled with 384-dimensional vector support.
- **FAISS HNSW Canonical QA Index:** Configured for $D=384$ vectors with Inner Product (Cosine) metric.
- **Chroma Persistent Vector Store:** Collection `policy_chunks_bge_small_en_v1_5` strictly partitioned by model slug and vector dimension (384), preventing vector dimensionality mixing.

---

## 3. Transaction Boundaries & Concurrency Guarantees

1. **Incremental Compilation Atomicity:**
   - When a policy version is compiled via `rag.compiler.pipeline.KnowledgeCompilerPipeline`, chunks, extracted facts, and canonical QAs are persisted in a single SQLAlchemy database transaction.
   - If an embedding call fails, transaction rollback restores previous database state and marks `CompilationJob.stage = CompilationStage.FAILED`.
2. **Version Promotion Safety:**
   - When a version is promoted to active (`is_active = True`), preceding versions are demoted to `is_active = False` in the same transaction block, satisfying the PostgreSQL partial unique index `uix_one_active_version_per_policy`.
