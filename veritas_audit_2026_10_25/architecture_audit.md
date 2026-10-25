# Veritas Architecture Audit

**Audit Date:** 2026-10-25 | **Branch:** `improv` / `0ebae05`

---

## 1. Actual Request Pipeline (Confirmed from Code)

```
HTTP Request
    │
    ▼
Flask + Gunicorn (app.py → blueprints/rag_routes.py)
    │
    ▼
QueryEngine.answer() / QueryEngine.stream_answer()
    │
    ├─ Step 1: Normalize query (QueryRouter.normalize)
    │          + get_allowed_policy_ids (EvidenceFilter)
    │          + resolve_temporal_context (VersionResolver) [if temporal cues]
    │          + QueryScope.from_user()
    │
    ├─ Step 1.5: L1 Exact Cache Lookup (MultiLevelCache.get, L1)
    │            Key: SHA256(normalized_query | scope_key)
    │            → If HIT: return cached answer (no authz re-check)
    │
    ├─ Step 1.6: Route Classification (QueryRouter.route)
    │
    ├─ Step 2: Level 0 — Fact Resolver (FactResolver.try_resolve)
    │          → PolicyFact + CanonicalQuestion tables, deterministic lookup
    │          → FAST_PATH_FACT route
    │
    ├─ Step Embed: embed_query() [only if fact missed]
    │
    ├─ Step 1.5b: L2 Semantic Cache Lookup (cosine ≥ 0.95)
    │
    ├─ Step 3: Level 1 — QA ANN Matcher (QAMatcher.match, threshold 0.80)
    │          → Canonical QA FAISS index
    │          → Authorization + temporal validity check
    │          → FAST_PATH_COMPILED_QA route
    │
    ├─ Step 4: Level 3 — Version Diff Engine (_run_version_comparison)
    │          → TEMPORAL_COMPARISON route
    │
    ├─ Step 5: Build retrieval filters (_build_retrieval_filters)
    │          → Policy-title ANN similarity matching (0.75 threshold)
    │          → Temporal timestamp filters (valid_from_ts / valid_to_ts)
    │          → Returns None → ABSTAINED if no authorized policies
    │
    ├─ Step 6: Hybrid Retrieval (_retrieve_and_rank)
    │          → HybridRetriever.search() [Dense + BM25 → RRF]
    │          → EvidenceFilter.filter_chunks() [post-retrieval authz]
    │          → Adaptive top_k (20-100)
    │          → FlashRank Reranker (rerank_top_k=8 or 5 for fallthrough)
    │          → ConfidenceEngine.score()
    │          → Citation construction
    │
    ├─ Step 7: Confidence Gate (abstain if conf.abstain)
    │
    ├─ Step 8: LLM Generation (QwenLocalProvider, if use_llm + health_check)
    │          → generate_grounded_answer() → Ollama
    │          → verify_numeric_grounding()
    │          → NLI verification (if no policy_name+version bypass)
    │          → HYBRID_RAG route
    │
    └─ Step 9: Deterministic Fallback (_extract_best_evidence_context)
               → If LLM fails/unavailable/rejected
               → ABSTAINED if no evidence context found
```

---

## 2. Component Inventory

### 2.1 Retrieval Stack

| Component | Implementation | File | Notes |
|-----------|---------------|------|-------|
| Dense Retriever | ChromaDB (HNSW cosine) | `rag/vectordb/chroma.py` | Collection per embedding model, dimension safety |
| Sparse Retriever | BM25Okapi (rank_bm25) | `rag/retrieval/sparse.py` | Persistent pickle, incremental update |
| Hybrid Fusion | RRF (K=60) | `rag/retrieval/hybrid.py` | No query-adaptive weighting |
| Reranker | FlashRank (ms-marco-TinyBERT-L-2-v2) | `rag/reranker/reranker.py`, `rag/retrieval/reranker.py` | Duplicate module paths |
| Embedder | FastEmbed BAAI/bge-small-en-v1.5 (384-dim) | `rag/embeddings/embedder.py` | ONNX |
| Policy Title Index | FAISS L2 ANN | `rag/engine/policy_title_index.py` | For filter construction |
| QA ANN Index | FAISS | `rag/qa/qa_matcher.py` | Canonical QA pairs |
| Fact Store | PostgreSQL (PolicyFact table) | `rag/facts/fact_resolver.py` | Zero-embedding path |

### 2.2 Authorization Stack

| Component | File | Key Logic |
|-----------|------|-----------|
| EvidenceFilter | `rag/authorization/evidence_filter.py` | is_admin callable/boolean dual-mode, role + clearance + department |
| QueryScope | `rag/engine/query_scope.py` | Carries allowed_policy_ids, role, department_ids |
| allowed_policy_ids cache | EvidenceFilter._allowed_pids_cache | 2-minute TTL, per-user key, bounded at 256 entries |

### 2.3 Temporal Resolution

| Component | File | Key Logic |
|-----------|------|-----------|
| VersionResolver | `rag/versions/resolver.py` | Date regex parsing → TemporalContext |
| get_active_version | `rag/versions/resolver.py:200` | effective_from ≤ target ≤ effective_to |
| Pre-dating fallback | `rag/versions/resolver.py:237-239` | Returns earliest version when target < all effective_from dates |

### 2.4 Generation Stack

| Component | File |
|-----------|------|
| Qwen3 4B (Ollama) | `rag/generation/qwen.py` |
| Prompt templates | `rag/generation/prompts.py` |
| NLI Verifier | `rag/verification/entailment.py` |
| Confidence Engine | `rag/verification/confidence.py` |
| Citation Validator | `rag/verification/citation_validator.py` |

### 2.5 Compiler Stack

| Component | File |
|-----------|------|
| Pipeline (7 stages) | `rag/compiler/pipeline.py` |
| Incremental Update | `rag/compiler/incremental.py` |
| Chunker | `rag/chunking/chunker.py` |
| Document Normalizer | `rag/compiler/document_normalizer.py` |

---

## 3. Key Architectural Findings

### 3.1 Duplicate Reranker Module Paths (P3)
- `rag/reranker/reranker.py` and `rag/retrieval/reranker.py` both exist
- `query_engine.py` imports from `rag.retrieval.reranker` (line 29)
- Potential confusion if the two diverge

### 3.2 NLI Bypass via Policy-Name+Version Heuristic (P1)
**File:** `rag/engine/query_engine.py:721-734`
```python
if has_policy_name and has_version:
    is_grounded = True
    nli_verdict = "BYPASS_GROUNDED"
    nli_entail_score = 1.0
```
If the LLM answer contains the policy name and a version number pattern, NLI verification is **completely bypassed**. An answer containing a hallucinated claim can pass as "grounded" if it includes metadata strings from the citation. This is a significant truthfulness defect — it is the likely cause of the 1.10% hallucination rate appearing low while the underlying NLI is skipped frequently.

### 3.3 Cache Does Not Re-check Authorization on Hit (P0 — Probable)
**File:** `rag/engine/query_engine.py:534-562`  
On an L1 cache hit, the system returns the cached answer immediately without re-verifying the current user's authorization against the current policy state. If a user's permissions are revoked, the cache can serve them a previously authorized answer until TTL expires (up to 1 hour for Redis, unbounded in-memory if no eviction).

**However:** Cache key includes `scope_key` which includes role and allowed_confidentiality. If `get_allowed_policy_ids` produces a different allowed_pids list after permission change, the cache key will differ → cache miss → re-evaluation. **This is only safe if permissions change causes a different allowed_pids set.** If the permission revocation is not reflected in the EvidenceFilter's TTL-cached `_allowed_pids_cache`, stale authorization is possible for up to 2 minutes.

**Status: Probable P0 — requires live testing to confirm stale auth window.**

### 3.4 Temporal Pre-dating Fallback Returns Earliest Version (P1)
**File:** `rag/versions/resolver.py:237-239`
```python
if earliest.effective_from is not None and target_date < earliest.effective_from:
    return earliest
```
When a query asks about a date before all versions exist, the system returns the earliest version. This matches reported behavior (one pre-dating failure). The fallback is arguably reasonable but must be disclosed: "policy was not yet in effect on requested date" should be the answer, not the earliest version's content.

### 3.5 BM25 Index Tokenizes Contextual Prefix but Dense Does Not (P2)
**File:** `rag/retrieval/sparse.py:112`  
```python
contextual_text = f"[{p_name} {v_lbl} {chunk.section_path or 'General'}] {chunk.text}"
```
BM25 tokenizes `[PolicyName v1.0 SectionPath] chunk_text`, while Chroma indexes only `chunk.text`. This asymmetry means BM25 gets policy/version/section signals that dense retrieval does not, creating inconsistent retrieval behavior between the two branches of the hybrid.

### 3.6 Adaptive top_k Scaling Uses allowed_policy_ids Count (P2)
**File:** `rag/engine/query_engine.py:294-296`
```python
effective_top_k = min(50, max(20, len(scope.allowed_policy_ids) * 15))
```
For a user with 3 allowed policies, `top_k = 45`. For 4+ policies, `top_k = 50`. For unrestricted users (allowed_policy_ids=None), top_k=50. The scaling is reasonable but the magic multiplier (15) is not documented or validated.

### 3.7 Evidence Selection Truncates to Top 5 Citations (P2)
**File:** `rag/engine/query_engine.py:397-398`
```python
if len(raw_cits) >= 5:
    break
```
Context is limited to 5 unique (policy_id, section) pairs. For multi-clause questions requiring evidence from different sections of the same policy, only one section per (policy, section) combination is kept. Cross-policy questions that need evidence from more than 5 sections are silently truncated.

### 3.8 LLM Only Called for HYBRID_RAG with complexity >= LEVEL_2 (P1)
**File:** `rag/engine/query_engine.py:711` and stream path line 1036`  
In `answer()`: LLM is called if `self.llm.health_check()` passes, regardless of route.  
In `stream_answer()`: LLM is called only if `complexity >= ComplexityLevel.LEVEL_2_RETRIEVAL`.  
**These two paths have different LLM invocation logic** — a potential inconsistency between batch and streaming modes.

---

## 4. Data Flow Boundary Points

### 4.1 Authorization enforcement points
1. `EvidenceFilter.get_allowed_policy_ids()` — pre-filters retrieval candidates
2. `_build_retrieval_filters()` — passes `allowed_policy_ids` to Chroma/BM25 filters
3. `EvidenceFilter.filter_chunks()` — post-retrieval filtering of all candidates
4. `is_authorized_for_policy()` — checked for QA matcher results and diff engine results

Authorization is enforced at multiple points. No evidence of bypass in normal path.

### 4.2 Where temporal filtering occurs
1. `_build_retrieval_filters()` adds `valid_from_ts`/`valid_to_ts` timestamp filters for Chroma
2. BM25 `_matches_filters()` applies same temporal filters
3. The timestamp range is derived from `scope.target_date` (from VersionResolver)

**Gap:** Temporal filtering uses pre-computed integer timestamps stored in chunk metadata. If a policy is amended and re-indexed, old chunks with stale timestamps may persist in the Chroma collection until the full delete+reindex cycle for that version completes.

---

## 5. Dependency Graph Summary

```
query_engine.py
├── query_router.py → intent_classifier.py, complexity_classifier.py, temporal_router.py
├── evidence_filter.py → models.py (Policy, PolicyVersion)
├── hybrid.py → dense.py (Chroma), sparse.py (BM25Okapi)
├── reranker.py (rag/retrieval/) → FlashRank
├── confidence.py → evidence_pack.py
├── entailment.py → (NLI model)
├── citation_validator.py
├── qa_matcher.py → FAISS, canonical_qa_faiss.index
├── fact_resolver.py → models.py (PolicyFact, PolicyVersion)
├── policy_title_index.py → FAISS
├── version_resolver.py → models.py (PolicyVersion)
├── diff_engine.py
├── qwen.py → Ollama HTTP
└── semantic_cache.py → Redis + in-memory
```
