# Veritas Index Consistency & Ingestion Lifecycle Report

**Audit Date:** 2026-10-21  
**Index Architectures Audited:** Okapi BM25 Sparse Index, FAISS HNSW Canonical QA Index, FastEmbed ONNX Dense Index, Multi-Level Redis Cache.

---

## 1. Index Lifecycle & Ingestion Pathways

```
[Raw Policy Ingestion (Markdown/PDF)]
               │
               ▼
   [Hierarchical Section Chunking] ──► SHA-256 Text Hash
               │
               ▼
   [Incremental Compiler Check] ────► Hash Match? ──► Reuse Vector (95% Compute Avoidance)
               │ (New Chunks)
               ▼
   [FastEmbed ONNX (384-dim)]
               │
   ┌───────────┴───────────────────────────────┐
   ▼                                           ▼
[Persistent BM25 Index]             [FAISS HNSW QA Index]
(data/bm25_index.pkl)               (data/canonical_qa_faiss.index)
   │                                           │
   └───────────┬───────────────────────────────┘
               ▼
[Multi-Level Redis Cache Invalidation]
(Clearance-scoped tenant invalidation)
```

---

## 2. Index Contracts & Synchronous Persistence

| Index Type | Storage Location | Invalidation Trigger | Synchronization Mechanism |
|---|---|---|---|
| **BM25 Inverted Index** | `data/bm25_index.pkl` | Policy mutation / version publish | Serialized pickle with revision counter. Fully rebuildable from `policy_chunk_v2` in $< 1\text{ second}$. |
| **Canonical QA FAISS** | `data/canonical_qa_faiss.index` | New canonical question generation | HNSW graph persisted to disk with companion `.meta.pkl` containing question IDs and answer mappings. |
| **Chroma Collection** | `data/chroma/` | Document compilation | Partitioned by model name (`policy_chunks_bge_small_en_v1_5`). |
| **Multi-Level Semantic Cache** | Redis (`veritas:cache:*`) | Policy publication / update | Cleared by tenant scope upon compilation completion. |

---

## 3. Retrieval Contract & RRF Harmonization

All retrievers conform to a unified contract:
- **`HybridResult`**: Contains `chunk_id`, `policy_id`, `version_id`, `content`, `score`, and `metadata` (`section_path`, `clearance_level`, `department_id`, `effective_date`).
- **Reciprocal Rank Fusion (RRF):**
  $$RRF(d) = \sum_{m \in \{dense, sparse\}} \frac{w_m}{k + \text{rank}_m(d)}$$
  with rank constant $k=60$ and weights $w_{dense}=0.6, w_{sparse}=0.4$.
- **FlashRank TinyBERT Cross-Encoder:** Evaluates top candidates, applying score sigmoid normalization before passing evidence to grounded synthesis.
