# Policy Ledger Enterprise — Master Startup & Deployment Guide

Welcome to **Policy Ledger Enterprise**, a high-performance, version-aware policy intelligence platform featuring sub-200ms streaming responses, multi-tier semantic caching, interactive citation drawers, and automated contradiction resolution.

---

## 1. Quick Start with Docker (Recommended)

The entire production ecosystem (Nginx Reverse Proxy, Web API, Celery Workers, PostgreSQL 16 with pgvector, Redis 7, and Ollama) runs via Docker Compose.

### Prerequisites
* Docker Engine & Docker Compose
* 4GB+ RAM (8GB+ recommended for local LLM inference)
* Optional: NVIDIA GPU with NVIDIA Container Toolkit

### Step-by-Step Launch Instructions

```bash
# 1. Navigate to the project directory
cd "/home/suyashpradhan/Desktop/Version aware _ Vision-chatgpt"
# Or if on another machine/path:
# cd /path/to/repository

# 2. Verify environment file exists (pre-configured)
# If starting from scratch: cp .env.example .env

# 3. Build & start all services in detached mode
docker compose up -d --build

# 4. (First time only) Initialize and seed database with 47 enterprise tables & knowledge indexes
docker compose exec -T web python seed.py

# 5. (Optional - for local LLM mode) Pull the local LLM model into Ollama
docker compose exec -T ollama ollama pull qwen3:4b-q4_K_M
```

---

## 2. Default Login Credentials

After seeding the database (`python seed.py`), the following pre-configured accounts are available:

| Role | Email | Password | Description |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin@company.com` | Defined in `.env` (`Admin@6997d0cd111c34a0`) | Full access to Admin Panel, Knowledge Graph, Audits, Metrics, User Management |
| **HR Director** | `hr@company.com` | `HR@1234` | Policy creation, version management, contradiction resolution, employee communications |
| **Employee** | `employee@company.com` | `Emp@1234` | Policy search, AI Assistant chat, citation drawer, quizzes, and acknowledgment |

---

## 3. How to Interact & Verify Everything is Working

### A. Web Interfaces
* **Main Application & Login:** [http://localhost:8080](http://localhost:8080)
* **Direct Web Container (Internal):** [http://localhost:5000](http://localhost:5000)
* **Ollama Inference Engine API:** [http://localhost:11434](http://localhost:11434)

### B. Health & Readiness Verification

Run in your terminal:
```bash
# 1. Check health status of all running containers
docker compose ps

# 2. Check Liveness Probe (Nginx -> Flask)
curl -i http://localhost:8080/health/live

# 3. Check Readiness Probe (Flask -> PostgreSQL DB connectivity)
curl -i http://localhost:8080/health/ready
```
Both health check curls should return `HTTP/1.1 200 OK` with JSON `{"status":"ok"}` and `{"database":"connected","status":"ready"}`.

### C. Live Log Streaming
```bash
# Stream logs for Web and Celery Worker
docker compose logs -f web celery_worker

# Stream all container logs
docker compose logs -f
```

### D. Key Feature Workflows to Test in Browser
1. **Login & Dashboard:** Log in as `admin@company.com` or `employee@company.com` at [http://localhost:8080](http://localhost:8080).
2. **AI Policy Chat & Citation Drawer:** Go to **AI Assistant** (`/rag/chat`). Ask questions such as:
   * *"What is the remote work policy allowance?"*
   * *"How many days of paid sick leave do I get?"*
   * Click on citation chips to open the **Slide-Over Citation Drawer** showing exact clause breadcrumbs and diffs.
3. **Global Command Palette:** Press `Ctrl+K` (or `Cmd+K`) anywhere to trigger search spotlight and quick navigation.
4. **Knowledge Graph & Blast Radius:** Navigate to **Admin -> Knowledge Graph** (`/admin/knowledge-graph`) and **Change Impact Preview** (`/admin/policies/<id>/blast-radius`).
5. **Multi-Tier Cache:** Ask the exact same or semantically identical query twice to verify instant sub-5ms cached responses.

---

## 4. How to Stop / Close Everything

### Graceful Stop (Preserves Database & Uploaded Data)
```bash
docker compose down
```

### Stop and Wipe All Persistent Volumes (Fresh Clean Slate)
```bash
docker compose down -v
```

---

## 5. Local Virtual Environment Run (Alternative - Without Docker)

For rapid Python-only local development:

```bash
# 1. Create and activate virtualenv
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# 3. Initialize & Seed SQLite database
export FLASK_APP=app.py
export FLASK_ENV=development
python seed.py

# 4. Run Flask local development server
python app.py
# Or with flask CLI:
# flask run --host=0.0.0.0 --port=5000
```

---

## 6. Automated Verification & Test Suites

To verify all system integrity, test suites, and views:

```bash
# A. Run full unit & regression test suite (41/41 passing, 0 warnings)
pytest

# B. Run comprehensive view health audit (69/69 passing across all Admin & Employee routes)
python scripts/audit_all_views.py

# C. Run policy creation lifecycle verification across all 5 pathways
python scripts/test_policy_creation_lifecycle.py
```


