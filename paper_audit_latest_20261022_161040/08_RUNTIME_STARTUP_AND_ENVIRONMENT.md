# Veritas Runtime Startup and Environment Telemetry

## 1. Operating Environment
- **Host Platform:** Linux 7.1.8-100.fc43.x86_64
- **CPU:** 11th Gen Intel(R) Core(TM) i5-11260H @ 2.60GHz (12 logical cores)
- **RAM:** 31 GiB Physical (16 GiB allocated to Docker environment)
- **GPU:** NVIDIA GeForce RTX 3050 Laptop GPU (4,096 MiB VRAM, Driver 580.178.04, CUDA 13.0)
- **Container Runtime:** Podman / Docker Engine with Docker Compose v2

## 2. Service Architecture and Status
| Service Name | Container / Image | Internal Port | External Port | Health Status |
| :--- | :--- | :--- | :--- | :--- |
| `policy_ledger_postgres` | `pgvector/pgvector:pg16` | 5432 | 127.0.0.1:5432 | HEALTHY (pgvector 0.8.6 enabled) |
| `policy_ledger_redis` | `redis:7-alpine` | 6379 | internal | HEALTHY (AOF persistence) |
| `policy_ledger_ollama` | `ollama/ollama:latest` | 11434 | 127.0.0.1:11434 | HEALTHY (Air-gapped) |
| `policy_ledger_celery` | `versionaware_vision-chatgpt-celery_worker` | N/A | internal | UP |
| `policy_ledger_web` | `versionaware_vision-chatgpt-web` | 5000 | 127.0.0.1:5000 | HEALTHY (Gunicorn Python 3.11) |
| `policy_ledger_nginx` | `nginx:1.27-alpine` | 80 | 0.0.0.0:8080 | UP |

## 3. Verified Model Runtimes
- **Generative LLM:** `qwen3:4b-q4_K_M` (Ollama local digest: `2bfd38a7daaf4b1037efe517ccb73d1a3bbd4822cf89f1a82be1569050a114e0`, 4.0B parameters, GGUF Q4_K_M).
- **Embedding Model:** `BAAI/bge-small-en-v1.5` (FastEmbed ONNX CPU runtime, 384 dimensions).
- **Reranker Model:** `ms-marco-TinyBERT-L-2-v2` (FlashRank ONNX runtime).

## 4. End-to-End Inference Verification
- **Direct Model Probe:** Sent `"Hello, respond with ONE word: VERITAS"` to Ollama. Received exact word response in 11.98s (warmup load duration 3.42s).
- **Full-Stack Application Probe:** Sent `"Summarize the remote work eligibility under company policy"` through Flask/Gunicorn `get_query_engine()`.
- **Telemetry Verified:** Route `HYBRID_RAG`, `LLM_USED: True`, Confidence `0.9588`, grounded citations retrieved from `Hybrid & Remote Work Framework`.
