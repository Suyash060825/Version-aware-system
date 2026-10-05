# Final Benchmark Provenance & Environment Audit: Veritas

## 1. Provenance Summary & Version Control

| Dimension | Frozen Baseline Evaluation | Expanded Characterization Suite | Internal Reference Benchmark |
| :--- | :--- | :--- | :--- |
| **Git Commit SHA** | `61d64b71c298c3c505f2eeeef3c94829dfb55f75` | `449e69b343dd8c3483120ea7b00bf193ea25df15` | `61d64b71...` (repository file) |
| **Primary Dataset File** | `data/ground_truth_ledger.json` / `data/policies/` | `tests/system_characterization/corpus_manifest.json` | `tests/system_characterization/benchmark_all.json` |
| **Corpus Scale** | 21 policies, 23 versions, 128 chunks | 120 policies, ~600 versions, 3,000 chunks | 462 internal query cases |
| **Corpus Origin** | Handcrafted authoritative corporate policy baseline | Enterprise-style synthetic policy corpus | Internal developer test suite |
| **Evaluation Scope ($N$)** | 301 queries | 922 unique queries (4,980 executions) | 462 internal regression cases |
| **Role in Manuscript** | End-to-end Local vs. Cloud baseline fidelity | System-characterization & stress benchmarks | Kept distinct for regression testing |

---

## 2. Experimental Environment & Hardware Lock

- **Operating System:** Linux `7.1.8-100.fc43.x86_64` (x86_64 architecture)
- **CPU:** 12 logical cores (6 physical cores), x86_64
- **System Memory (RAM):** 31.06 GB
- **GPU Accelerator:** NVIDIA GeForce RTX 3050 Laptop GPU (3.68 GB VRAM, CUDA 12.x)
- **Random Seed:** Master seed $\text{SEED}=42$ locked across all stochastic samplers
- **Software Runtime Stack:**
  - Python: `3.14.6`
  - PyTorch: `2.13.0`
  - ChromaDB: `1.5.9`
  - FAISS: `1.15.0`
  - FastEmbed: `0.8.0` (Embedding: `BAAI/bge-small-en-v1.5`, $d=384$)
  - FlashRank: `0.2.10` (Reranker: `ms-marco-TinyBERT-L-2-v2`, ONNX)
  - scikit-learn: `1.9.0` (Isotonic regression calibrator)
  - Database & Cache: PostgreSQL 16 (Relational Triples), Redis 7 (Composite Scope Cache)
  - LLM Backends: Local `qwen3:4b-q4_K_M` (Ollama runtime) vs. Cloud `Gemini 2.0 Flash` (Google GenAI API)

---

## 3. Model Architecture Provenance

1. **Embedding Layer:**
   - Model: FastEmbed `BAAI/bge-small-en-v1.5`
   - Dimension: $d=384$
   - Normalization: L2 unit-normed embeddings
2. **Lexical Index:**
   - Inverted BM25 index with $k_1=1.5, b=0.75$, partitioned by policy boundaries
3. **Hybrid Fusion & Reranking:**
   - Reciprocal Rank Fusion: $k=60$, generating candidate beam of $K=50$ (default) or $K=100$ (sensitivity)
   - Cross-Encoder: FlashRank `ms-marco-TinyBERT-L-2-v2` ONNX scoring admitted candidates to top-8
4. **Natural Language Inference (NLI) Verifiers:**
   - Local Runtime Deployment: `cross-encoder/nli-deberta-v3-base` (lightweight CPU inference)
   - High-Throughput Characterization Testbed: `DeBERTa-v3-large` ONNX runtime
   - Thresholds: Entailment gate $\theta_{\text{entail}}=0.35$, contradiction rejection threshold $0.50$

---

## 4. Resolution of the 127 vs. 128 Chunk Fixture Discrepancy

- **Database Table (`policy_chunk_v2`):** Contains 128 total rows.
  - 127 content-bearing clause chunks subject to incremental mutation sweeps.
  - 1 static system-level preamble chunk (`POLICY-CHUNK-PREAMBLE-000`) providing corporate metadata.
- **Audit Conclusion:** Microbenchmarking mutation counts (1-chunk delta, 3-chunk delta) accurately evaluate the 127 mutable chunks, while total corpus size is 128 chunks. The 127/128 distinction is preserved in manuscript footnotes and tables.

---

## 5. Cryptographic Ledger Verification

- **Ledger Path:** `data/ground_truth_ledger.json`
- **Total Chunks Verified:** 2,110 chunks across 120 policies and 422 versions
- **Cryptographic Mismatches:** 0 mismatches
- **Version Monotonicity Violations:** 0 violations
- **Tombstone Integrity:** 100.0% verified across all 20 mutation cycles
