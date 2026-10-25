# Veritas Compiler Correctness & Performance Audit

**Audit Date:** 2026-10-25 | **Branch:** `improv` / `0ebae05`

---

## 1. Incremental Compilation Pipeline

**Files:** [`rag/compiler/pipeline.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/compiler/pipeline.py) and [`rag/compiler/incremental.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/compiler/incremental.py)

The compiler executes a 7-stage process:
1. `PARSING`: Raw text validation.
2. `NORMALIZED`: Document normalization & header cleanup.
3. `CHUNKED`: Structure-aware chunk generation.
4. `FACT_EXTRACTION`: Regex predicate facts extraction.
5. `QA_COMPILATION`: Canonical Q&A pair generation.
6. `EMBEDDING`: FastEmbed dense vector generation.
7. `INDEXING`: ChromaDB upsert, BM25 rebuild/delta, and cache invalidation.

---

## 2. Correctness & Equivalence Findings

### 2.1 Concurrent Compilation Race Hazard (CONFIRMED P0 DEFECT)
- `IncrementalCompiler.diff_versions()` queries existing chunks via `PolicyChunkV2.query.filter_by(version_id=...)`.
- In `pipeline.py:_stage_chunk` (lines 108–118), existing chunks are deleted:
  ```python
  PolicyChunkV2.query.filter_by(version_id=job.version_id).delete()
  db.session.add_all(pcs)
  ```
- There are no row-level locks, table locks, or distributed locks (Redis lock).
- If an amendment compilation is triggered while a background job or second worker is compiling the same version, a race condition occurs where one worker reads zero chunks or partially committed chunk sets, corrupting the diff.

### 2.2 Mid-Stage Commit & Broken Atomicity (P1)
In `pipeline.py:_stage_qa`:
- Line 146 calls `db.session.commit()` immediately after inserting canonical questions.
- Line 178 calls a second `db.session.commit()` after generating compiled answers.
- `_advance_stage()` wraps stages in a try/except with `db.session.rollback()` on error.
- Because `db.session.commit()` was executed mid-stage, any error occurring during answer generation (L150–175) leaves **orphan question rows permanently committed in the database** while marking the job `FAILED`.

### 2.3 Incremental Equivalence vs Full Rebuild
In `experiments/ieee_publication_v1/comprehensive_metrics.json`:
- `unchanged_queries_identical`: **`false`**
- `mean_token_f1_delta`: **`0.0740`**
- **Finding:** The report claims "100% preservation across unchanged content," yet the underlying JSON metric explicitly logs `unchanged_queries_identical: false` with a non-zero F1 delta (0.0740).
- This proves incremental updates do **not** produce perfectly equivalent outputs to a full rebuild. Differences arise because:
  1. BM25 term frequency statistics (`IDF`) shift when partial chunks are updated without full document collection re-indexing.
  2. In `incremental.py:30-32`, new in-memory `ChunkIR` objects replace old chunks without verifying embedding model version compatibility.
