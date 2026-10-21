# VERITAS — Comprehensive Retrieval Pipeline Review

## 1. Pipeline Overview and Design

The Veritas retrieval pipeline balances deterministic speed, high semantic recall, and verifiable grounding. It guarantees that answers delivered to employees and managers are derived strictly from active, authorized policy versions.

```
Query -> Normalization -> Semantic Cache -> Canonical QA (Fast-Path) -> Hybrid Retrieval (BM25 + pgvector/Chroma) -> RRF Fusion -> FlashRank Reranker -> Clearance Scoping -> LLM Generation -> NLI Grounding -> Response
```

---

## 2. Component-by-Component Review

### 2.1 Router & Canonical QA (Deterministic Fast-Path)
- Standard compliance questions (e.g., *"What is the standard annual leave allowance?"*) are routed to the Canonical QA module.
- Lookup utilizes pre-indexed FAISS vectors (`canonical_qa_faiss.index`) matched against canonical questions (`CanonicalQuestion`).
- When a match exceeds a cosine similarity threshold of $0.92$, the pre-verified authoritative answer is returned in **<15ms**, bypassing LLM inference entirely.

### 2.2 Sparse Retrieval (BM25)
- **Tokenization**: Lowercase alphanumeric tokenization with custom policy stopword management.
- **Term Weighting**: BM25 algorithm with parameters $k_1 = 1.5, b = 0.75$.
- **Strengths**: Excels at exact term matching for policy codes, department acronyms (e.g. `IT-SEC-04`), and numeric thresholds (e.g. `14 days`).
- **Persistence**: Serialized via `pickle` with automated reload upon compilation job completion.

### 2.3 Dense Retrieval (FastEmbed ONNX)
- **Embedding Model**: `BAAI/bge-small-en-v1.5` executed locally via FastEmbed ONNX runtime.
- **Dimensionality**: Exactly 384 dimensions, normalized with L2 norm for unit cosine distance calculation.
- **PostgreSQL pgvector**: Executes vector search using the `hnsw` index (`cosine` distance metric: `<=>`).
- **ChromaDB**: Fallback/standalone persistent store with cosine similarity metric.

### 2.4 Reciprocal Rank Fusion (RRF)
- Combines sparse and dense candidate lists:
  $$RRF\_Score(d) = \frac{1}{60 + \text{rank}_{dense}(d)} + \frac{1}{60 + \text{rank}_{sparse}(d)}$$
- Fuses top-50 sparse and top-50 dense candidates into a balanced top-20 candidate pool.

### 2.5 Cross-Encoder Reranking (FlashRank)
- **Model**: `ms-marco-TinyBERT-L-2-v2` executed via ONNX.
- Reranks candidate pairs $(q, chunk)$ by computing joint token cross-attention scores.
- Re-scores and truncates the candidate list to the top-5 most relevant passages, filtering out noise.

### 2.6 Clearance & Scope Filtering (`EvidenceFilter`)
- Prior to context assembly, candidates are filtered against the caller's identity:
  1. **Confidentiality Check**: Restricts `RESTRICTED` or `CONFIDENTIAL` policies to authorized roles (e.g. `ADMIN`, `LEGAL`, or department members).
  2. **Active Version Filter**: Ensures chunks belong strictly to the currently active version of published policies.
  3. **Temporal Validity**: Filters historical revisions if an `as_of` timestamp is specified.

### 2.7 Natural Language Generation & Grounding Verification
- Context chunks are assembled into a prompt with explicit instruction to refuse extrapolation.
- Ollama generates the natural-language explanation using `qwen3:4b-q4_K_M`.
- A natural language inference (NLI) entailment check verifies that the generated claims are supported by the retrieved passages.
- If the model cannot answer with confidence or the retrieved evidence does not entail the response, the system triggers **safe abstention**.
