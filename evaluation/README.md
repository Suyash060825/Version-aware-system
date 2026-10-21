# Veritas Evaluation & Reproducible Benchmark Framework

This directory contains the publication-ready, evidence-backed evaluation harness for **Veritas** (Version-aware enterprise policy engine with hybrid retrieval, deterministic execution, and grounded generative reasoning).

The benchmark verifies quantitative and qualitative claims without external or cloud LLM dependencies, running strictly on local containerized infrastructure (Docker Compose with PostgreSQL 16 + pgvector, Redis, Celery, Ollama running `qwen3:4b-q4_K_M`, and FastEmbed `BAAI/bge-small-en-v1.5`).

---

## 1. Directory Structure

```
evaluation/
├── claim_registry.yaml             # Machine-readable registry of all 15 audited claims (CLM-001 - CLM-015)
├── corpus_generator.py             # Deterministic synthetic corpus generator (120, 500, 1k, 5k policies)
├── question_generator.py           # 36-category synthetic question and oracle ground-truth generator
├── metrics.py                      # Wilson 95% CIs, Token F1, Expected Calibration Error (ECE), MRR, Recall@K
├── run_benchmark.py                # Master execution harness (Steps 1–9)
├── README.md                       # This reproduction guide
└── results/                        # Raw experimental outputs and artifacts
    ├── environment.json            # Machine telemetry and container runtime state
    ├── corpus_manifest.json        # 120-policy corpus metadata and version chains
    ├── question_manifest.json      # 1,000 generated queries across 36 categories
    ├── scalability_results.csv     # Scaling metrics (120 to 5,000 policies)
    ├── incremental_update_benchmark.json # Compute avoidance and delta update speedup
    ├── discrepancy_reconciliation.json   # 1,000-policy indexing discrepancy empirical resolution
    ├── security_results.json       # 3,840 clearance and authorization evaluations
    ├── concurrency_results.csv     # 1 to 100 worker concurrency sweep results
    ├── query_level_results.jsonl   # Per-query telemetry (latency, route, citations, token F1)
    ├── answer_quality_metrics.json # Accuracy, latency percentiles, ECE, category breakdown
    ├── retrieval_metrics.json      # Policy Recall@K, Chunk Recall@K, MRR
    ├── generation_results.json     # Ollama live inference latency, throughput, think-tag suppression
    ├── test_summary.json           # Comprehensive test and benchmark execution summary
    ├── claim_verification_matrix.csv # Verification matrix across all 15 claims
    └── failure_log.jsonl           # Granular audit log of failed/abstaining queries
```

---

## 2. Prerequisites & Environment Setup

### System Requirements
- **OS:** Linux x86_64
- **CPU:** 8+ cores recommended (tested on 12 vCPUs)
- **RAM:** 16 GB+ recommended
- **Docker:** Engine 24.0+ with Docker Compose v2

### Local Service Architecture
The evaluation harness runs against the real Docker Compose topology:
- `web`: Flask application running Gunicorn on Python 3.11
- `postgres`: PostgreSQL 16 with `pgvector` extension enabled (`0.8.6`)
- `redis`: Redis 7.2 for distributed caching and Celery message broker
- `celery_worker`: Background policy contradiction and heavy indexing worker
- `ollama`: Ollama server serving local `qwen3:4b-q4_K_M`
- `nginx`: Reverse proxy on port 8080

---

## 3. Quickstart: Reproducing the Benchmark

### Step 1: Ensure Containers are Running and Healthy
```bash
docker compose up -d
docker compose exec -T postgres psql -U veritas -d policy_ledger -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Verify service readiness:
```bash
curl -f http://localhost:8080/health/ready
curl -f http://localhost:8080/health/llm
```

### Step 2: Execute Master Benchmark Suite
Run the benchmark directly inside the standardized Docker web container (ensuring ABI compatibility and identical Python 3.11 environment):

```bash
docker compose exec -T web python3 -u evaluation/run_benchmark.py
```

### Step 3: Run Unit, Integration, and Regression Tests
Execute the comprehensive pytest test suite inside the container:
```bash
docker compose exec -T web pytest tests/test_audit_engineering_pass.py tests/test_independent_validation.py -v
```

---

## 4. Benchmark Execution Methodology

The master harness (`run_benchmark.py`) systematically executes 9 sequential evaluation phases:

1. **Environment Capture:** Records host CPU, memory, platform, Docker network topology, and model versions to `environment.json`.
2. **Deterministic Corpus Generation:** Generates the canonical 120-policy, 422-version, 2,110-chunk evaluation corpus.
3. **Corpus Scalability & Indexing Sweep:** Measures indexing throughput (chunks/sec), BM25 construction time, and memory across 120, 500, 1,000, and 5,000 policies.
4. **Discrepancy Reconciliation:** Empirically isolates the historical 1,000-policy indexing divergence (42.45s in-memory batched ONNX FastEmbed vs 234.94s unbatched serial disk transactions).
5. **Incremental Compilation Benchmark:** Verifies compute avoidance ratio and neural embedding speedup when applying a 5% delta update against the corpus.
6. **Security & Authorization Audit:** Executes 3,840 authorization queries across 32 user roles and clearance levels, verifying 0 unauthorized chunk leaks.
7. **Concurrency & Thread Safety Sweep:** Simulates 1, 10, 25, 50, and 100 concurrent workers querying shared caches and multi-tenant scopes to verify isolation soundness.
8. **36-Category Comprehensive Query Evaluation:** Evaluates 1,000 queries spanning factual lookups, time-travel, multi-condition exceptions, out-of-distribution abstentions, and prompt injection attacks.
9. **Live Qwen Inference Benchmark:** Benchmarks live Ollama `qwen3:4b-q4_K_M` local generation, measuring latency, token throughput, and `<think>` reasoning tag suppression.

---

## 5. Statistical Rigor and Formulas

- **Wilson Score Interval (95% CI):** Used for all binomial proportions (accuracy, leak rates, cache hit rates):
  $$\hat{p} \pm \frac{z}{1 + \frac{z^2}{n}} \sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}$$
- **Expected Calibration Error (ECE):** Evaluated over 10 uniform probability bins $B_m$:
  $$\text{ECE} = \sum_{m=1}^{M} \frac{|B_m|}{N} \left| \text{acc}(B_m) - \text{conf}(B_m) \right|$$
- **Token F1:** Standard harmonic mean of precision and recall over lowercased, punctuation-stripped token bags between model response and canonical ground truth.
