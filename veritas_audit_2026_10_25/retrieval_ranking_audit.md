# Veritas Retrieval & Ranking Audit

**Audit Date:** 2026-10-25 | **Branch:** `improv` / `0ebae05`

---

## 1. BM25 Audit

### 1.1 Implementation

**File:** [`rag/retrieval/sparse.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/retrieval/sparse.py)

- **Library:** `rank_bm25.BM25Okapi` — BM25 with Okapi term-frequency normalization
- **Default parameters:** `k1=1.5, b=0.75` (rank_bm25 defaults — not explicitly set, not documented)
- **Tokenizer:** `re.findall(r"\b\w+\b", text.lower())` — simple word tokenization
- **No stopword removal**
- **No stemming or lemmatization**
- **Contextual prefix:** `[PolicyName vLabel SectionPath]` prepended to chunk text before tokenization

### 1.2 Confirmed Issues

**Contextual prefix tokens (P2):** The policy name and version label tokens are included in the document's token list but are NOT present in the tokenized query. When a user asks "what is the annual leave limit", the BM25 scores will weight policy-name tokens (e.g., "Annual", "Leave", "Policy") as if they were body content, inflating scores for policies whose name contains common query words. For "annual leave limit", every Annual Leave policy chunk gets a BM25 boost from the prefix even if the chunk doesn't contain the answer.

**No special treatment of policy IDs or clause identifiers (P2):** Queries like "what does section 4.2 say" tokenize "4" and "2" as separate tokens due to `\b\w+\b` (the `.` is not a word character). `section` is treated as a regular word. This destroys structured identifiers.

**Numeric dates tokenized as isolated digits (P2):** "effective January 2024" tokenizes to `["effective", "january", "2024"]` which is correct. But "01/15/2024" → `["01", "15", "2024"]` loses the date semantics. Policy text with ISO-format dates will tokenize correctly.

**Sub-BM25 cache key is frozenset of allowed_indices (P2):**
```python
cache_key = (frozenset(allowed_indices), self._revision)
if cache_key != self._sub_bm25_cache_key or self._sub_bm25 is None:
    allowed_tokenized = [self._tokenized_corpus[i] for i in allowed_indices]
    self._sub_bm25 = BM25Okapi(allowed_tokenized)
```
The sub-BM25 is rebuilt when the allowed indices or revision changes. For a user with N=5 allowed policies across 2,110 total chunks, a fresh BM25Okapi is constructed on every unique access control scope change. With many users having slightly different allowed_policy_ids sets, this can rebuild repeatedly. The cache key is per-instance (not a singleton), so multi-process deployments each maintain independent caches.

**BM25 scores not normalized before RRF:** BM25 raw scores (unbounded positive floats) are used directly as ranks in RRF. Only the rank position is used, not the score value — this is correct for RRF. ✓

---

## 2. Dense Retrieval Audit

### 2.1 Implementation

**File:** [`rag/retrieval/dense.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/retrieval/dense.py) → [`rag/vectordb/chroma.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/vectordb/chroma.py)

- **Store:** ChromaDB with HNSW (cosine space)
- **Model:** BAAI/bge-small-en-v1.5, 384 dimensions, L2-normalized, via FastEmbed ONNX
- **Score:** `max(0.0, 1.0 - distance)` (cosine similarity from HNSW distance)
- **Filter:** Passed as Chroma `where` clause (pre-filtering in HNSW)
- **Default top_k:** 50 (from `_retrieve_and_rank` adaptive scaling)

### 2.2 Confirmed Issues

**Document text not enriched with policy name/version (P2):** Unlike BM25 which prepends `[PolicyName vLabel SectionPath]`, Chroma indexes only `chunk.text`. This creates an asymmetry: BM25 benefits from policy metadata in matching but dense does not. Dense retrieval cannot distinguish "annual leave" chunks from different policies unless the chunk text itself references the policy name.

**Chroma binary files deleted from working tree (Unable to verify at runtime):** The git status shows 8 Chroma collection subdirectories deleted (`D data/chroma/...`). The collection `data/chroma/915dcd07-bcdc-40d3-9a0d-91f4692ddcfd/` is untracked (new). The current Chroma index state cannot be verified without running the application. This is the index used for all reported experiments.

**Temporal pre-filtering in Chroma (P1):** Timestamp filters `valid_from_ts`/`valid_to_ts` are applied as Chroma `where` conditions. However, HNSW approximate nearest neighbor search with complex `$and` conditions can be slow or inaccurate in ChromaDB — the HNSW graph is built over all vectors and the filter is applied post-graph-traversal, not as a true pre-filter. For large corpora, this means the approximate search may not return enough valid candidates if the filter is selective.

**Score conversion from distance (P1):** `score = max(0.0, 1.0 - distance)`. For cosine space, ChromaDB returns distances in [0, 2] (where 0 = identical vectors). The conversion assumes distances in [0, 1]. For normalized vectors with cosine similarity, `cosine_distance = 1 - cosine_similarity`, so distance ∈ [0, 2]. The score formula `1.0 - distance` can return negative values for dissimilar vectors (distance > 1.0), which are clamped to 0.0. This is correct — effectively treating vectors with negative similarity as 0 score. **No defect, but the formula handles the HNSW cosine space correctly only for normalized vectors.**

---

## 3. RRF Audit

### 3.1 Implementation

**File:** [`rag/retrieval/hybrid.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/retrieval/hybrid.py)

```python
K = 60
combined[doc_id]["score"] = 1.0 / (K + rank + 1)  # 1-indexed ranks
```

**RRF formula:** `score = 1/(K + rank)` where rank is 1-indexed (i=0 → rank=1). This is the standard RRF formula with K=60 (a commonly used default). ✓

**Normalization:** `normalized_score = min(1.0, score / max_possible_rrf)` where `max_possible_rrf = 2.0 / (K + 1) ≈ 0.0328`. This scales the combined score to [0, 1]. ✓

### 3.2 Confirmed Issues

**No per-retriever weighting (P3):** RRF treats BM25 and dense retrieval as equal contributors. In practice, for exact-match queries (policy IDs, dates, numbers), BM25 should be weighted higher. For paraphrase queries, dense should dominate. A fixed K=60 with equal weighting may not be optimal for all query categories.

**BM25 score not passed to sparse.get_scores (P2):** `HybridRetriever.search` calls `self.sparse.get_scores(query, filters)` without passing the `query_embedding`. BM25 thus always uses the raw string query for scoring, even when the engine has already computed an embedding. This is expected and correct — BM25 is lexical.

**`sparse_results[:top_k]` truncation (P2):** Only the top `top_k` BM25 results enter the RRF pool. For a user with many allowed policies, BM25 may rank the relevant chunk at position 51 (just outside the top_k cutoff), causing it to never enter the RRF pool and be lost entirely.

**Candidate identifier consistency (P1):** Dense results use `doc.get("chunk_id") or doc.get("id")` as the key. BM25 results use `doc["id"]` (from `corpus[i]["id"]` set during `_do_rebuild_from_db`). Chroma returns `meta["id"] = doc_id` and `meta["chunk_id"] = doc_id`. BM25 corpus stores `"id": chunk.chunk_id` and `"chunk_id": chunk.chunk_id`. Both are set to the same value (`chunk.chunk_id`), so the identifier is consistent. ✓

---

## 4. Reranker Audit

### 4.1 Implementation

**File:** [`rag/retrieval/reranker.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/retrieval/reranker.py)

- **Model:** `ms-marco-TinyBERT-L-2-v2` via FlashRank ONNX (default)
- **Candidate limit:** 15 candidates maximum (silently drops candidates beyond index 15)
- **Score:** FlashRank returns scores in [0,1] range natively
- **Format:** `[Policy: X | Section: Y] chunk_text` prepended to passage for cross-encoder input

### 4.2 Confirmed Issues

**Silent candidate truncation at 15 (P2):** `_retrieve_and_rank` calls `hybrid_retriever.search()` with `effective_top_k` of 20-100. FlashRank only scores the first 15 candidates from this list. Candidates ranked 16–100 by RRF are silently discarded without being scored. This defeats the purpose of adaptive top_k scaling.

**Reranker lift measurement (BD-03):** Reported pre-rerank MRR = 0.2647, post-rerank MRR = 0.2955. These were computed from `pre_filter_chunk_ids` and `post_rerank_chunk_ids` in the JSONL records. For fast-path queries (FAST_PATH_FACT, FAST_PATH_COMPILED_QA), these lists are empty — contributing 0 to MRR. The aggregate MRR over all 100 queries therefore mixes routes and deflates both pre- and post-rerank values. The +11.63% lift is computed over a mixed population where most queries never go through the reranker.

**Correct lift measurement should be:** compute MRR over HYBRID_RAG queries only (N=14), using `authorized_chunk_ids` as pre-rerank ranking and `post_rerank_chunk_ids` as post-rerank ranking.

---

## 5. Metadata Filter Audit

### 5.1 Temporal Filter Construction (P1)

```python
filters["valid_from_ts"] = {"$lte": target_ts}
filters["valid_to_ts"] = {"$gte": target_ts}
```

This correctly implements `effective_from ≤ target_date ≤ effective_to`. ✓

However, `valid_to_ts = 32472144000` (year 3000) is used as the sentinel for "no end date" (open-ended). The filter `valid_to_ts >= target_ts` will correctly include chunks with this sentinel. ✓

**Gap:** `valid_from_ts = 0` (epoch 1970) is used for versions with no `effective_from` date. A filter for `target_ts > 0` (any date after 1970) would incorrectly include these chunks. However, the filter is `$lte target_ts` on `valid_from_ts`, which means "chunk's start ≤ query date" — a chunk with `valid_from_ts=0` always satisfies this condition. **This could include inappropriately undated chunks in historical queries.**

### 5.2 Authorization Pre-filter (P1)

`_build_retrieval_filters` adds `policy_id` as a filter (either exact match or `$in` list). This pre-filters Chroma before vector search. For BM25, the filter is applied post-scoring via `_matches_filters`. The ordering means BM25 may score all chunks and only filter after — correct functionally but wasteful for large corpora.

**The `policy_id` filter in Chroma `$in` with a large list can cause performance issues** — ChromaDB's HNSW implementation may not efficiently handle `$in` with many values during graph traversal.

---

## 6. Evidence Selection Audit

### 6.1 Final Context Construction

`_extract_best_evidence_context` scores sentences from the top 5 ranked chunks by word overlap with the query. It then constructs a ±1 sentence window around the best-matching sentence.

**Issues:**
- **Top 5 chunks limit (P2):** Multi-clause questions needing evidence from different policy sections may need more than 5 chunks.
- **Citations capped at 5 (P2):** `if len(raw_cits) >= 5: break` — truncates potentially relevant sources.
- **Sentence splitting uses `(?<=[.!?])\s+` (P1):** This doesn't handle bullet lists, numbered clauses, or table rows — all of which are common in policy documents. Bullet items won't be split into separate candidate sentences.
- **`_GENERIC_WORDS` filter (P2):** Words like "limit", "days", "year", "standard", "work" are considered generic and excluded from query keyword matching. For many policy questions, these ARE the substantive terms (e.g., "what is the standard work week limit").

---

## 7. Recall Failure Root Cause Analysis

From the category breakdown in `evaluation/results/answer_quality_metrics.json`:

| Category | Accuracy | Root Cause |
|----------|----------|------------|
| CAT_07_CROSS_POLICY (0%) | Requires aggregating evidence from multiple policies; evidence selection picks only 1 policy at a time | Evidence selection design |
| CAT_09_HISTORICAL_VS_CURRENT (7.4%) | Temporal routing works for point-in-time queries but fails when comparing "old vs new" without explicit version numbers | Temporal resolver doesn't handle relative historical references robustly |
| CAT_11_EXCEPTIONS (0%) | Policy exceptions are often in subordinate clauses after the main rule; sentence scoring picks the main rule, not the exception | Chunking + sentence selection |
| CAT_24_QWEN_GENERATION (0%) | `llm_used=false` in all generation_results.json records; either LLM unavailable or 0% of queries reach the LLM path | LLM availability / routing |
| CAT_03_SEMANTIC_PARAPHRASE (F1=0.023) | High accuracy but near-zero F1: paraphrased answers differ lexically from expected exact phrases; metric mismatch | Evaluation metric mismatch, not retrieval failure |

---

## 8. Summary of Retrieval Findings

| ID | Finding | Severity |
|----|---------|----------|
| RET-01 | Policy Recall@K identical at all K — artifact of using citations, not candidates | Evaluation defect |
| RET-02 | BM25 contextual prefix inflates score for policy-name keywords in query | P2 |
| RET-03 | Dense retrieval lacks policy-name context; dense/BM25 asymmetry | P2 |
| RET-04 | FlashRank silently truncates to 15 candidates from potentially 100 | P2 |
| RET-05 | `_GENERIC_WORDS` filter removes substantive policy terms from evidence scoring | P2 |
| RET-06 | Evidence selection limited to 5 citations, 5 chunks | P2 |
| RET-07 | HYBRID_RAG reranker lift computed over all routes, not HYBRID_RAG only | Evaluation defect |
| RET-08 | BM25 sub-BM25 rebuild on every unique scope change | P3 |
| RET-09 | Temporal filter includes undated chunks (valid_from_ts=0) in all queries | P1 |
| RET-10 | CAT_07_CROSS_POLICY 0% — multi-policy evidence not aggregated | P1 |
| RET-11 | CAT_11_EXCEPTIONS 0% — exception clauses not extracted by sentence scorer | P1 |
