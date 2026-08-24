# Policy Ledger Enterprise — Master Startup & Deployment Guide

Welcome to **Policy Ledger Enterprise**, a high-performance, version-aware policy intelligence platform featuring sub-200ms streaming responses, multi-tier semantic caching, interactive citation drawers, and automated contradiction resolution.

---

## 1. Quick Start (Single Production Docker Stack)

The entire production ecosystem (Nginx Reverse Proxy, Web API, Celery Workers, PostgreSQL, Redis 7, and Ollama) runs via a single unified `docker-compose.yml`.

### Prerequisites
* Docker Engine 24.0+ & Docker Compose v2.20+
* 4GB+ RAM (8GB+ recommended for local LLM inference)
* Optional: NVIDIA GPU with NVIDIA Container Toolkit for GPU acceleration

### Launch Commands

```bash
# 1. Enter repository
cd Version-aware-system

# 2. Copy environment template and configure production secrets
cp .env.example .env

# 3. Build & start all services in detached mode
docker compose up --build -d
```

### Pull the Local LLM Model into Ollama
```bash
# Pull the configured Qwen model (run once)
docker exec -it policy_ledger_ollama ollama pull qwen3:4b-q4_K_M
```

### Access Services
* **Web Application:** [http://localhost](http://localhost) (via Nginx reverse proxy on port 80; TLS terminated at external load balancer)
* **Prometheus Metrics:** [http://localhost/metrics](http://localhost/metrics)
* **Liveness Probe:** [http://localhost/health/live](http://localhost/health/live)
* **Readiness Probe:** [http://localhost/health/ready](http://localhost/health/ready)

### Authentication & Initial Credentials
Configure `DEFAULT_ADMIN_PASSWORD` in your `.env` file before initial startup. User accounts can be managed securely via the administrative panel.

---

## 2. Local Virtual Environment Run (Without Docker)

For rapid local testing and development using Python 3.11:

### Step 1: Install Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### Step 2: Initialize Database & Seed Initial Policies
```bash
export FLASK_APP=app.py
export FLASK_ENV=development
python -c "from app import create_app; from models import db; app=create_app('development'); app.app_context().push(); db.create_all()"
```

### Step 3: Run the Web Server
```bash
flask run --host=0.0.0.0 --port=5000
```

### Step 4: Run Celery Background Worker (Optional)
```bash
celery -A tasks.celery_app worker --loglevel=info
```

---

## 3. Running Automated Tests & Audits

Run the complete test suite:

```bash
pytest -q
```

To run the full reproducible RAG benchmark suite:
```bash
python scripts/run_reproducible_eval.py
```

---

## 4. Key Features & How to Test Them

### A. Real-Time Token Streaming & Citation Drawer
1. Log in (or use corporate SSO / demo account).
2. Navigate to **AI Assistant** (`/rag/chat`).
3. Type a query (e.g., *"What is the remote work policy allowance?"*).
4. Notice word-by-word streaming token generation.
5. Click any citation badge on the answer to open the **Slide-Over Citation Drawer**, highlighting the exact clause, section breadcrumb, and version diff comparison.

### B. Global Command Palette (`Ctrl+K` / `Cmd+K`)
* Press `Ctrl+K` (or `Cmd+K` on macOS) anywhere in the application to open the instant search spotlight and quick navigation modal.

### C. Interactive Policy Knowledge Graph & Blast Radius
* Navigate to **Admin -> Knowledge Graph** (`/admin/knowledge-graph`) to explore interactive relationship trees. Use the **Department Filter dropdown** to focus on specific business domains.
* Navigate to **Admin -> Policies -> [Policy] -> Change Impact Preview** (`/admin/policies/<id>/blast-radius`) to view the 3-tier impact topology map before publishing amendments.

### D. Multi-Tier Semantic & Vector Cache
* Repeated or semantically equivalent questions return instantly (<5ms) from the L1/L2 vector cache without invoking the LLM.
* When an HR admin modifies a policy, the system automatically calls `invalidate_policy()`, instantly clearing stale cache records.

---

## 5. Environment Variables (`.env`) Reference

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `FLASK_ENV` | `production` | Environment mode (`development`, `testing`, `production`) |
| `SECRET_KEY` | *(Required)* | Flask session signature key |
| `JWT_SECRET_KEY` | *(Required)* | JWT signature key |
| `DEFAULT_ADMIN_PASSWORD` | *(Required)* | Password for initialized administrator account |
| `DATABASE_URL` | `postgresql://...` | PostgreSQL 16 connection URI |
| `REDIS_URL` | `redis://redis:6379/0` | Redis 7 cache & Celery broker URI |
| `LLM_BACKEND` | `ollama` | Backend engine (`ollama`, `lmstudio`, `local`, `mock`) |
| `LOCAL_LLM_MODEL` | `qwen3:4b-q4_K_M` | LLM model tag |
| `EMBEDDING_ENGINE` | `fastembed` | `fastembed`, `sentence_transformers`, `mock` |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Embedding model identifier |
| `RERANKER_ENGINE` | `flashrank` | `flashrank`, `cross_encoder`, `mock` |
| `RERANKER_MODEL` | `ms-marco-TinyBERT-L-2-v2` | Reranker model identifier |
| `SEMANTIC_CACHE_ENABLED`| `true` | Enables L1 exact + L2 cosine similarity caching |
| `SEMANTIC_CACHE_THRESHOLD`| `0.95` | Cosine similarity threshold for cache hits |

---

## 6. Container Lifecycle Management

```bash
# View live streaming logs
docker compose logs -f web celery_worker

# Check service health status
docker compose ps

# Gracefully stop all containers
docker compose down

# Stop and wipe all persistent volumes (fresh restart)
docker compose down -v
```
