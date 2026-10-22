# Veritas Benchmark Reproduction Guide

To safely reproduce all evaluation figures from a clean shell:

## 1. Prerequisites
- Docker Engine with Docker Compose v2.
- Local NVIDIA or CPU host with at least 16 GB RAM and 20 GB disk.

## 2. Service Startup
```bash
# 1. Bring up all microservices in dependency order
docker compose up -d

# 2. Verify pgvector extension in PostgreSQL
docker compose exec -T postgres psql -U veritas -d policy_ledger -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 3. Confirm health endpoints
curl -f http://localhost:8080/health/ready
curl -f http://localhost:8080/health/llm
```

## 3. Master Evaluation Execution
Execute the master benchmark inside the standardized Python 3.11 web container:
```bash
docker compose exec -T web python3 -u evaluation/run_benchmark.py
```

## 4. Independent Metric Verification
Run the metric recomputation script locally:
```bash
python3 paper_audit_latest_20261022_161040/12_METRIC_RECOMPUTATION_SOURCE.py
```
