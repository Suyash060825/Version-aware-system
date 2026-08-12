# Deployment & Local LLM Integration Guide — Policy Ledger v2

This guide outlines how to configure, serve, migrate, and deploy Policy Ledger with a production-grade local LLM inference layer (Ollama / vLLM).

---

## 1. Hardware & Model Selection Matrix

Policy text requires instruction-tuned models with low hallucination rates and reliable long-context comprehension.

| Target Environment | Hardware Specs | Recommended Model | Quantization | Backend | VRAM / RAM |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Small / CPU Server** | 4–8 Cores, 16GB RAM | `llama3.1:8b-instruct-q4_K_M` | Q4_K_M | Ollama | ~5.5 GB RAM |
| **Medium GPU Workstation** | 1x NVIDIA RTX 3090 / 4090 (24GB) | `Qwen/Qwen2.5-14B-Instruct` | AWQ / GPTQ | vLLM or Ollama | ~12–16 GB VRAM |
| **High-Throughput Enterprise** | 1–2x NVIDIA A100 / H100 (80GB) | `meta-llama/Meta-Llama-3.1-70B-Instruct` | AWQ / FP16 | vLLM | ~40–80 GB VRAM |

---

## 2. Switching LLM Backends

The application uses an abstract `LLMProvider` factory (`rag/llm_provider.py`). Configure the active backend in `.env`:

### Option A: Local Ollama (Default Dev & CPU/GPU)
```env
LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
LOCAL_LLM_MODEL=llama3.1:8b-instruct-q4_K_M
```
Start Ollama:
```bash
docker-compose up -d ollama
./scripts/pull_model.sh
```

### Option B: vLLM (High-Throughput GPU Production)
```env
LLM_BACKEND=vllm
VLLM_BASE_URL=http://localhost:8000/v1
LOCAL_LLM_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
```
Start vLLM:
```bash
docker-compose -f docker-compose.vllm.yml up -d
```

### Option C: Cloud Gemini / OpenRouter Fallback
```env
LLM_BACKEND=gemini
GEMINI_API_KEY=your_openrouter_or_gemini_api_key
LLM_MODEL=google/gemini-2.0-flash-001
```

### Cascading LLM (Module 28)
```env
LLM_BACKEND=cascade
CASCADE_PRIMARY=ollama
CASCADE_SECONDARY=gemini
```

---

## 3. Database Migrations (Alembic)

To apply schema updates (e.g. `model_name` and `model_version` columns for auditability):

```bash
# Run migration to latest revision
alembic upgrade head

# Rollback migration if needed
alembic downgrade -1
```

---

## 3.5. Redis Semantic Cache (Module 27)

To support the version-aware semantic cache, Redis is now required in production:

```env
REDIS_URL=redis://localhost:6379/0
# The cache will automatically degrade to an in-memory python dictionary if Redis is unreachable.
```

---

## 4. Production Deployment with Docker Compose & Nginx TLS

Deploy all production services (Nginx, Gunicorn, PostgreSQL, Redis, ChromaDB, Ollama):

```bash
# 1. Copy and populate production credentials
cp .env.example .env
nano .env

# 2. Spin up production stack
docker-compose -f docker-compose.prod.yml up -d --build

# 3. Warm up local model
docker-compose -f docker-compose.prod.yml exec web /app/scripts/pull_model.sh
```

### Enabling TLS with Let's Encrypt (Certbot)
1. Install Certbot on host server: `sudo apt install certbot python3-certbot-nginx`
2. Obtain certificate: `sudo certbot --nginx -d policy.yourcompany.com`
3. Certbot automatically configures TLS certificates in `/etc/letsencrypt/live/`.

---

## 5. Pre-Launch Security Checklist

- [x] **Secrets Rotated**: `SECRET_KEY` and `JWT_SECRET_KEY` set to strong random values.
- [x] **DEBUG Disabled**: `FLASK_ENV=production` set, `DEBUG=False`.
- [x] **Rate Limiting Active**: `/rag/api/chat` enforced at `20 requests/min/user` via `Flask-Limiter`.
- [x] **File Upload Security**: Magic header checking, MIME validation, and Zip-Bomb inspection active in `rag/parser/validator.py`.
- [x] **Prompt Injection Defense**: Policy chunk text wrapped in `<policy_chunk>` tags with system instructions treating content as passive data.
- [x] **Audit Traceability**: Every LLM query records `model_name` in `ChatMessage`.
- [x] **Health Checks**: Operational health monitored at `/rag/health` and `/rag/health/llm`.
- [x] **Commercial License Confirmed**: Ensure the model you run (e.g. Llama 3.1 Community License, Qwen2.5 Apache 2.0) permits your exact commercial use case.

---

## 6. Model Lifecycle & Capacity Planning

### Model Rollout Process
1. Run new models through the `eval/run_eval.py` suite against `eval/golden_questions.jsonl` in a staging environment.
2. Compare the output scorecard to your current production model.
3. Perform a manual review and sign-off.
4. Roll out gradually via environment variable swaps (e.g. updating `LOCAL_LLM_MODEL`).
5. Keep the previous model pulled/warmed in Ollama or vLLM to allow for an instant rollback.

### Capacity Planning
- **CPU Servers (e.g. 8B Q4 via Ollama)**: Expect ~10-15 tokens/sec. Suitable for ~1-2 concurrent generations before noticeable queueing delays occur.
- **Medium GPU (RTX 3090/4090 - 24GB VRAM)**: Can host a 14B AWQ model (e.g. Qwen2.5 14B) serving ~3-5 concurrent requests smoothly.
- **Enterprise GPU (A100/H100)**: Can run 70B models with vLLM's paged attention, scaling to ~20+ concurrent generations.
To scale horizontally, deploy multiple Ollama/vLLM replicas behind an Nginx upstream proxy block using a least-connections algorithm. Monitor queue depth via Prometheus to detect saturation.
