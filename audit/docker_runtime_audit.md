# Veritas Docker Compose & Runtime Topology Audit

**Audit Date:** 2026-10-21  
**Runtime Engine:** Docker Engine 24.0+ with Docker Compose v2  
**Target Environment:** Isolated 6-container production stack (`docker-compose.yml`)  

---

## 1. Service Networking & Topology Matrix

| Service Name | Container Name | Base Image | Internal Hostname | Ports (Host:Container) | Health Check Command | Dependencies | Restart Policy |
|---|---|---|---|---|---|---|---|
| **nginx** | `policy_ledger_nginx` | `nginx:1.27-alpine` | `nginx` | `8080:80` | N/A (Reverse Proxy) | `web` (service_healthy) | `unless-stopped` |
| **web** | `policy_ledger_web` | Local build (`python:3.11-slim`) | `web` | `127.0.0.1:5000:5000` | `curl -f http://localhost:5000/health/live` | `postgres`, `redis`, `ollama` (all service_healthy) | `unless-stopped` |
| **celery_worker** | `policy_ledger_celery` | Local build (`python:3.11-slim`) | `celery_worker` | Internal only | Celery ping via broker | `postgres`, `redis` (both service_healthy) | `unless-stopped` |
| **postgres** | `policy_ledger_postgres` | `pgvector/pgvector:pg16` | `postgres` | `127.0.0.1:5432:5432` | `pg_isready -U postgres` | None (Datastore root) | `unless-stopped` |
| **redis** | `policy_ledger_redis` | `redis:7-alpine` | `redis` | Internal only (`6379`) | `redis-cli ping` | None (Broker root) | `unless-stopped` |
| **ollama** | `policy_ledger_ollama` | `ollama/ollama:latest` | `ollama` | `127.0.0.1:11434:11434`| `ollama list 2>/dev/null \| grep -q qwen3` | None (Inference root) | `unless-stopped` |

---

## 2. Health Checks & Startup Ordering Verification

```
   [postgres: pg_isready]   [redis: redis-cli ping]   [ollama: ollama list grep qwen3]
              │                        │                             │
              └────────────────────────┼─────────────────────────────┘
                                       │
                                       ▼
                       [web: Flask readiness /health/ready]
                       [celery_worker: tasks registered]
                                       │
                                       ▼
                         [nginx: Reverse Proxy :8080]
```

### Verified Health Endpoints
1. **Liveness Probe (`/health/live`):**
   - Command: `curl -f http://localhost:8080/health/live`
   - Response: `{"status": "ok", "service": "policy-ledger"}` (`HTTP 200 OK`)
2. **Readiness Probe (`/health/ready`):**
   - Command: `curl -f http://localhost:8080/health/ready`
   - Response: `{"database": "connected", "status": "ready"}` (`HTTP 200 OK`)
3. **LLM Engine Probe (`/health/llm`):**
   - Command: `curl -f http://localhost:8080/health/llm`
   - Response: `{"healthy": true, "model": "qwen3:4b-q4_K_M", "provider": "ollama", "timestamp": "..."}` (`HTTP 200 OK`)

---

## 3. Discrepancies Repaired

1. **Duplicate Environment Variable in `web`:**
   - `OLLAMA_BASE_URL` was declared twice in `docker-compose.yml` (`${OLLAMA_BASE_URL:-...}` and a static literal). Removed duplicate static declaration.
2. **Celery Worker Application Import Path:**
   - Fixed missing `PYTHONPATH=/app` and added defensive path injection in `tasks.py` to prevent `ModuleNotFoundError: No module named 'app'`.
3. **Database URL Connection Resilience:**
   - Removed socket lookup fallback in `config.py` that silently downgraded PostgreSQL to SQLite. Production and container runtime now strictly validate PostgreSQL connectivity at startup.
