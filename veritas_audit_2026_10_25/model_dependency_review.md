# Veritas Model & Dependency Review

**Audit Date:** 2026-10-25 | **Branch:** `improv` / `0ebae05`

---

## 1. Evaluation of Existing Model Choices

| Component | Current Implementation | Observed Failure Mode / Bottleneck | Replace or Fix? |
|---|---|---|---|
| **Embedding Model** | FastEmbed ONNX `BAAI/bge-small-en-v1.5` (384-dim) | Inconsistent handling of policy title prefixes; 16.2 ms query latency on CPU | **KEEP & FIX:** Model is lightweight and capable; fix metadata prefix asymmetry between BM25 and Chroma. |
| **Vector DB** | ChromaDB (HNSW cosine) | Transient compaction lockouts; collection deletion on dimension mismatch | **REPLACE / HARDEN:** Migrate to PostgreSQL `pgvector` or harden Chroma against auto-deletion. |
| **Cross-Encoder Reranker** | FlashRank ONNX `ms-marco-TinyBERT-L-2-v2` | Silent truncation of candidates beyond top 15 | **KEEP & RECONFIGURE:** FlashRank is fast (15.9 ms); increase candidate evaluation limit from 15 to 30. |
| **Local LLM** | Qwen3 4B quantized (`q4_K_M`) via Ollama | Severe tail latency (16–27s on CPU); 0% accuracy in CAT_24 due to missing daemon | **KEEP ARCHITECTURE, RESTRICT USAGE:** Restrict live generation strictly to synthesis queries; fallback to extractive for fact lookups. |
| **NLI Verifier** | `cross-encoder/nli-deberta-v3-base` | Disabled by default via env var; bypassed by policy name regex | **ENABLE & REPAIR:** Remove regex bypass; repair "According to" claim stripping; set default enabled in production. |
| **Sparse Engine** | `rank_bm25.BM25Okapi` (Python pickle) | Inverted list rebuilds on scope changes; file locks under concurrency | **REPLACE:** Migrate to PostgreSQL `tsvector` / GIN index for native ACID, concurrency-safe BM25 search. |
