# Veritas Empirical Reproducibility Specification

**Target Paper:** *Veritas: Version-Aware Enterprise Policy Intelligence via Incremental Knowledge Compilation and Adaptive Multi-Tier Retrieval*  
**Audited Git Commit SHA:** `9425d1fcbe0674f7a49b6fd2f213f4ccb138285b`  
**Random Seed Configuration:** `SEED = 42` (Deterministic master RNG for corpus and query generation), `SEED = 42 + ConcurrencyLevel` for load testing.  
**Execution Timestamp:** 2026-10-05T16:17:49.356940+00:00

---

## 1. Hardware & Runtime Environment
- **Operating System:** Linux 6.6.137+ (x86_64)
- **Python Version:** 3.11+
- **Primary Dependencies:** PyTorch, FAISS-CPU 1.8.0, ChromaDB 0.5.5, FlashRank ONNX 0.2.9, Sentence-Transformers, DeBERTa-v3-large ONNX.
- **Local Embedded Models:** 
  - Dense Embeddings: `BAAI/bge-small-en-v1.5` (384-dimensional dense vectors)
  - Reranker: `ms-marco-TinyBERT-L-2-v2` (FlashRank ONNX)
  - NLI Entailment: `DeBERTa-v3-large` (ONNX runtime)
- **Cloud Reference Model:** `Gemini 2.0 Flash` (Temperature 0.0, zero-shot structured JSON output)

---

## 2. Corpus & Ground-Truth Dataset Inventory
- **Enterprise Corpus:** 120 synthetic policies spanning 12 business domains (HR, IT, Finance, Security, Travel, Legal, Compliance, Facilities, Procurement, Operations, Engineering, Executive).
- **Revision History:** 600 total versions (15% single-version, 20% two-version, 35% 3-4 versions, 30% 5+ versions).
- **Chunk Partitioning:** 3,000 structural chunks tagged with SHA-256 cryptographic fingerprints.
- **User Archetypes:** 32 simulated user archetypes spanning 4 clearance tiers (`public`, `internal`, `confidential`, `restricted`) and 12 departmental scopes.
- **Benchmark Evaluation Corpus:** 922 benchmark queries across 10 functional categories (Category A to Category J).

---

## 3. Step-by-Step Reproduction Workflow

```bash
# 1. Install pinned dependencies
pip install -r requirements.txt

# 2. Run the master system characterization suite (Generates raw results and failure cases)
python tests/system_characterization/runner.py

# 3. Run the master audit verification harness (Recomputes metrics, reproduces failures, concurrency tests)
python scripts/run_audit_verification.py

# 4. Verify that all 41 core system unit and integration tests pass
pytest
```

---

## 4. Artifact & Dataset Cross-Reference

| Output File / Directory | Description | Primary Metric Validated |
| :--- | :--- | :--- |
| `results/system_characterization/metrics_verified.csv` | Recomputed metrics with exact Wilson score 95% CIs and P50-P99 latencies | 97.6% overall accuracy, 4.5ms P50 latency |
| `results/system_characterization/failures_verified.jsonl` | Step-by-step reproduced failure cases with root cause classifications | 22 identified edge-cases diagnosed (F1-F10) |
| `results/system_characterization/concurrency_results.csv` | Multi-user scaling across 1, 10, 25, 50, 100 concurrent threads | 0% cache bleed, sub-linear latency scaling |
| `results/system_characterization/post_mutation_results.csv` | Post-update cache invalidation and tombstone purging checks | 100% immediate version correctness |
| `results/system_characterization/fixed_evidence_llm_comparison.csv` | Decoupled local deterministic vs cloud generative fidelity | 0.962 Token F1 on gold evidence chunks |
| `results/system_characterization/paper_tables/` | Tables 1-5 in CSV and Markdown format with exact sample sizes N | Production publication tables |
| `results/system_characterization/paper_figures/` | Figures 01-24 high-resolution publication charts | Visual distributions, heatmaps, and latency curves |
