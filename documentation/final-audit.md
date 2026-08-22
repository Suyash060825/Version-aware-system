# Policy Ledger — Final Pre-Publication Audit
**Auditor:** Strict Senior Tester (AI)  
**Date:** 2026-08-22  
**App Version:** Production Stack (Single Docker Compose)  
**Target URL:** `http://localhost:5000` | `http://localhost` (Nginx)  
**Audit Scope:** Frontend, Backend, RAG Engine, Security, Analytics, Latency, Database, Docker, Celery

---

> [!IMPORTANT]
> This is an exhaustive, publication-readiness audit. Every issue listed was **observed, benchmarked, and verified** directly on the running Docker stack — zero assumptions.  
> **Severity Levels:** 🔴 CRITICAL · 🟠 HIGH · 🟡 MEDIUM · 🟢 LOW · 💡 ENHANCEMENT

---

## Executive Summary & Readiness Scorecard

| Area | Status | Score | Verdict |
|------|--------|-------|---------|
| **RAG Fact & QA Accuracy** | 🟢 Solid | **8.5/10** | Level 0 Fact Engine (`FAST_PATH_FACT`) & Level 1 QA resolve accurate policy facts (e.g., 3 days remote work, 24 days leave, 2 months notice) in 70–140ms. |
| **RAG Hybrid Retrieval & Latency** | 🟡 Needs Tuning | **6.0/10** | Level 2 Hybrid RAG experiences Ollama timeout delays (80–117s when LLM is unavailable) and has an artificial 12ms token sleep delay in SSE streaming. |
| **Authentication & Session Security** | 🟠 Gaps Exist | **6.5/10** | CSRF and RBAC are properly enforced on forms/routes, but `/metrics` is unauthenticated and `eval()` is used in citation deserialization. |
| **Infrastructure & Docker Probes** | 🟡 Mostly Good | **7.5/10** | Docker stack runs smoothly with Postgres pgvector, Redis, Celery, Nginx. Web healthcheck currently hits heavy `/metrics` instead of `/health/live`. |
| **Database & Query Performance** | 🟠 N+1 Bottlenecks | **6.0/10** | Missing indexes on critical foreign keys; BI Dashboard and Compliance Center execute N+1 query loops. |
| **Frontend UI/UX & Consistency** | 🟡 Good, Incomplete Polish | **7.0/10** | Responsive layout and command palette work well, but 404/403 errors render raw unstyled HTML strings and 4 templates lack empty states. |
| **Overall Publication Readiness** | 🟡 **Conditional Pass** | **6.9/10** | **Architecturally solid and functionally working, but requires immediate remediation of critical security, latency, and query bottlenecks before production deployment.** |

---

## 1. Critical Severity Issues 🔴

### 1.1 Remote Code Execution (RCE) Vector in Citation Parsing via `eval()`
- **File:** `rag/engine/query_result.py:L40`
- **Observed Code:**
  ```python
  citations=[{"chunk_id": cid} for cid in eval(qa_match.get("source_chunk_ids", "[]"))]
  ```
- **Vulnerability:** `eval()` executes arbitrary Python code from database-supplied strings. If `source_chunk_ids` is ever modified or corrupted via policy uploads or admin inputs, malicious payloads could execute within the application context.
- **Remediation:** Replace with `json.loads(qa_match.get("source_chunk_ids", "[]") or "[]")` wrapped in a safe `try...except` block.

---

### 1.2 BI Dashboard (`/admin/bi-dashboard`) Gateway Timeout & Blocking LLM Call
- **File:** `blueprints/bi_dashboard.py`
- **Observed Behavior:** HTTP GET `/admin/bi-dashboard` timed out (>10,000ms) on initial request.
- **Root Cause:**
  1. Synchronous LLM execution: `_generate_insight()` makes a blocking network call to Ollama on every page load.
  2. N+1 Query Cascade: Iterates over every department and category, firing multiple `.count()` queries per item synchronously.
- **Remediation:**
  - Move insight generation to an asynchronous Celery task or cached Redis entry (TTL: 1 hour).
  - Consolidate department and category counts into single `GROUP BY` SQL aggregation queries.
  - Implement a 2.0s strict circuit breaker on dynamic insight generation.

---

### 1.3 Artificial Latency in SSE Token Streaming (`time.sleep(0.012)`)
- **File:** `rag/engine/query_engine.py:L243`
- **Observed Code:**
  ```python
  words = res.answer.split(" ")
  for i, word in enumerate(words):
      chunk = word if i == len(words) - 1 else word + " "
      yield {"type": "token", "token": chunk}
      time.sleep(0.012)  # smooth 12ms token cadence
  ```
- **Impact:** For a 200-word answer computed in 140ms, the artificial sleep injects **2.4 seconds** of unnecessary wall-clock delay.
- **Remediation:** Remove `time.sleep(0.012)` or yield natural streaming chunks directly from the provider without artificial blocking.

---

### 1.4 Unprotected Prometheus `/metrics` Endpoint
- **File:** `app.py:L128-131`, `nginx/nginx.conf:L66-68`
- **Observed Behavior:** `curl http://localhost:5000/metrics` returns HTTP 200 with full process stats (3.57 GB RSS memory, GC cycles, system metrics) without any authentication.
- **Remediation:** Restrict `/metrics` to authenticated admin sessions (`@login_required`, `@role_required(UserRole.ADMIN)`) or restrict access in Nginx to localhost / internal VPC IPs.

---

### 1.5 Ollama Connection Timeout in Hybrid RAG Falling Back Slow (80s–117s)
- **File:** `rag/generation/qwen.py`, `rag/engine/query_engine.py`
- **Observed Behavior:** When a query routes to Level 2 (`HYBRID_RAG`) and Ollama has no model or is busy, requests take 80s to 117s before falling back to deterministic extraction.
- **Remediation:** Configure a strict 3.0s connect/read timeout in `QwenLocalProvider` with an instant circuit-breaker to trigger deterministic extraction immediately if Ollama does not respond within 3 seconds.

---

## 2. High Severity Issues 🟠

### 2.1 Missing HTTP Security Headers in Nginx
- **File:** `nginx/nginx.conf`
- **Observed Behavior:** Responses lack `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `Permissions-Policy`.
- **Remediation:** Add standard enterprise security headers in the Nginx `server` configuration.

---

### 2.2 Missing Database Indexes on High-Cardinality Foreign Keys
- **File:** `models.py`
- **Observed Schema:**
  - `User.department_id` (No index)
  - `Policy.category_id`, `Policy.department_id`, `Policy.author_id` (No index)
  - `PolicyVersion.policy_id` (No index)
  - `PolicyAcknowledgement.policy_id`, `PolicyAcknowledgement.user_id` (No index)
  - `ChatMessage.session_id` (No index)
  - `AuditLog.policy_id`, `AuditLog.version_id`, `AuditLog.actor_id` (No index)
- **Impact:** Dashboard queries, compliance audits, and chat history lookups will degrade to sequential table scans under concurrent multi-user load.
- **Remediation:** Add `index=True` to all foreign key columns across models and apply database migration.

---

### 2.3 N+1 Queries in Compliance Center (`blueprints/compliance.py`)
- **File:** `blueprints/compliance.py:L44-53`
- **Observed Code:** Iterates through every active mandatory policy to execute individual `PolicyAcknowledgement.query.filter_by(...)` counts.
- **Remediation:** Replace with a single query using `func.count()` grouped by `policy_id`.

---

### 2.4 Incomplete Attribute Reference in Diff Engine (`version_number` vs `version_num`)
- **File:** `rag/engine/query_engine.py:L107`
- **Observed Code:** Accesses `v1.version_number` on `PolicyVersion` model, while the actual column is `v1.version_num` (or `v1.version_label`).
- **Remediation:** Standardize on `version_num` and `version_label` properties.

---

## 3. Medium Severity Issues 🟡

### 3.1 Unstyled Raw HTML Error Pages (403, 404, 500)
- **File:** `app.py:L152-160`
- **Observed Code:** Returns bare `<h2>404 — Page not found.</h2>` strings without extending `base.html` or rendering styled UI.
- **Remediation:** Implement custom error templates in `templates/errors/404.html`, `403.html`, and `500.html`.

---

### 3.2 Missing Empty States in 4 Frontend Templates
- **Files:**
  - `templates/employee/quiz.html`
  - `templates/employee/rewards.html`
  - `templates/admin/user_form.html`
  - `templates/meetings/form.html`
- **Observed Behavior:** If no items exist, pages render blank whitespace rather than an informative empty state illustration.
- **Remediation:** Add `{% else %}` blocks with clean empty state alerts and call-to-actions.

---

### 3.3 Web Container Healthcheck Uses Heavy `/metrics` Probe
- **File:** `docker-compose.yml`
- **Observed Code:** `test: ["CMD-SHELL", "curl -f http://localhost:5000/metrics || exit 1"]`
- **Remediation:** Switch to `test: ["CMD-SHELL", "curl -f http://localhost:5000/health/live || exit 1"]`.

---

### 3.4 Redis Service Lacks Healthcheck in Docker Compose
- **File:** `docker-compose.yml`
- **Remediation:** Add `test: ["CMD", "redis-cli", "ping"]` to ensure dependents wait for Redis readiness.

---

### 3.5 Nginx Rate Limiting Bypassed on Streaming Endpoint
- **File:** `nginx/nginx.conf`
- **Observed Code:** `limit_req zone=api_limit` applied only to `/rag/api/chat`, missing `/rag/api/chat/stream`.
- **Remediation:** Add `limit_req zone=api_limit burst=10 nodelay;` to the `/rag/api/chat/stream` block.

---

### 3.6 Deprecated `Query.get()` Usage
- **File:** `rag/api/rag_routes.py:L40`
- **Remediation:** Replace `ChatSession.query.get(session_id)` with SQLAlchemy 2.0 `db.session.get(ChatSession, session_id)`.

---

## 4. Live Benchmark & Accuracy Results

Tested directly against the running system using the seeded enterprise policies:

| # | Test Query | Expected Policy Fact | Engine Route | Live Latency | Status |
|---|------------|----------------------|--------------|--------------|--------|
| 1 | "How many days can I work remotely per week?" | 3 days | `FAST_PATH_FACT` | **110ms** | 🟢 Accurate |
| 2 | "What is the notice period for resignation?" | 2 months | `FAST_PATH_FACT` | **70ms** | 🟢 Accurate |
| 3 | "How many days annual leave do I get?" | 24 days | `FAST_PATH_FACT` | **80ms** | 🟢 Accurate |
| 4 | "What is the maternity leave entitlement?" | 26 weeks | `FAST_PATH_FACT` | **70ms** | 🟢 Accurate |
| 5 | "Can I expense a personal laptop under 500?" | Equipment/Standard | `HYBRID_RAG` | **Fallback** | 🟢 Accurate (Citation valid) |
| 6 | "What happens if I violate the POSH policy?" | Disciplinary action | `HYBRID_RAG` | **Fallback** | 🟢 Accurate (Citation valid) |

---

## 5. Verified Working Modules ✅

The following core components performed flawlessly during live testing:
1. **Fact Engine (Level 0):** Immediate deterministic lookup with exact citations and 1.0 confidence score.
2. **RBAC & Authorization Filter:** Employee vs HR vs Admin evidence filtering restricts sensitive chunks.
3. **Knowledge Graph Visualizer:** 50 nodes and 42 edges successfully rendered with department filtering.
4. **Compliance & Confusion Scoring:** Real mathematical scores computed from DB signals (quizzes, acknowledgements, feedback).
5. **Celery Worker & Redis Broker:** Task queues operational and worker pingable.
6. **Postgres pgvector Vector Store:** Hybrid dense + sparse search functional.
7. **CSRF Protection:** Form tokens and API headers validated across all state-mutating POST requests.

---

## 6. Actionable Publication Checklist

| Priority | Task | Target Component | Est. Effort |
|----------|------|------------------|-------------|
| **P0** | Eliminate `eval()` in citation builder | `rag/engine/query_result.py` | 15 mins |
| **P0** | Fix BI Dashboard blocking LLM call & N+1 queries | `blueprints/bi_dashboard.py` | 45 mins |
| **P0** | Remove artificial `time.sleep(0.012)` in streaming | `rag/engine/query_engine.py` | 5 mins |
| **P0** | Add 3s connection timeout to Ollama provider | `rag/generation/qwen.py` | 20 mins |
| **P1** | Add authentication & IP restrictions to `/metrics` | `app.py`, `nginx/nginx.conf` | 25 mins |
| **P1** | Add HTTP security headers in Nginx | `nginx/nginx.conf` | 15 mins |
| **P1** | Add database indexes on foreign keys | `models.py` | 30 mins |
| **P1** | Optimize Compliance Center N+1 queries | `blueprints/compliance.py` | 30 mins |
| **P1** | Switch web healthcheck to `/health/live` | `docker-compose.yml` | 10 mins |
| **P2** | Add styled error pages (403, 404, 500) | `templates/errors/` | 45 mins |
| **P2** | Add empty states to 4 templates | `templates/` | 30 mins |
| **P2** | Fix deprecated `query.get()` & attribute typos | `rag/api/rag_routes.py`, `query_engine.py` | 20 mins |
