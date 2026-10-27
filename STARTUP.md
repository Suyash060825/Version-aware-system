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

# 4. (First time only) Initialize and seed database
# Option A: Standard 20-policy enterprise sample
docker compose exec -T web python seed.py

# Option B: Complete 120-policy evaluation characterization corpus (422 versions, 2,110 chunks, 422 facts/QAs)
docker compose exec -T web python scripts/seed_characterization_ledger.py

# 5. (Optional - for local LLM mode) Pull the local LLM model into Ollama
docker compose exec -T ollama ollama pull qwen3:4b-q4_K_M
```

---

## 2. Default Login Credentials

After seeding the database (`python seed.py` or `python scripts/seed_characterization_ledger.py`), the following pre-configured accounts are available:

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

### Verified Working Credentials

   Role                                                                   │ Email                                                                  │ Password
  ────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────
   Admin                                                                  │ admin@company.com                                                      │ Admin@123456
   Employee                                                               │ employee@company.com                                                   │ User@123456
   HR                                                                     │ hr@company.com                                                         │ Hr@123456
   CISO (Admin)                                                           │ ciso@company.com                                                       │ Ciso@123456
   Lead Architect (Employee)                                              │ eng.lead@company.com                                                   │ User@123456
  ──────----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------_=====
 Here is the exact diagnostic breakdown of both issues without modifying any code:
  ──────
  ### 1. Why Creating a New Policy Throws an "Internal Server Error" (500)
  Checking the live backend container logs (policy_ledger_web) reveals the exact crash:

    sqlalchemy.exc.PendingRollbackError: ...
    Original exception was: (psycopg.errors.UniqueViolation) duplicate key value violates unique constraint "policy_pkey"
    DETAIL: Key (id)=(23) already exists.
    [SQL: INSERT INTO policy ...]

  #### Root Cause:

  • The PostgreSQL sequence policy_id_seq has desynchronized from the actual data in the table.
  • In PostgreSQL:
      • Maximum existing id in the policy table: 120
      • Current value of sequence policy_id_seq: 23
  • When clicking Create Policy, Postgres tries to assign the next sequence ID (24 or 23), which conflicts with an already-existing row from earlier migrations/seed data, triggering a primary key collision and throwing a
  500 Internal Server Error.
  (When you're ready, this is resolved by running SELECT setval('policy_id_seq', (SELECT MAX(id) FROM policy));).
  ──────
  ### 2. Why the Confidence Score Feels "Fake and Low"
  There are two primary areas where confidence scores appear:

  #### A. In RAG Chat (rag/verification/confidence.py):

  1. Aggressive Isotonic Regression Knots (calibration_knots.json):
      • Raw composite scores pass through calibration knots designed to curb overconfidence.
      • If retrieval or coverage lands in the 0.20–0.45 range, the calibration curve heavily penalizes the score:
          • Raw 0.11 → 𝟎.𝟎
          • Raw 0.22 → 𝟎.𝟏𝟏
          • Raw 0.33 → 𝟎.𝟑𝟐
      • As a result, mid-quality matches that provide good answers are compressed downward into the 10%--35% range.
  2. Strict Evidence Coverage Penalty (_evidence_coverage):
      • The confidence engine computes a literal stemmed word overlap between the user's query tokens and the retrieved chunks.
      • If a user asks a colloquial, paraphrased, or scenario question, many query words do not literally appear in the formal policy text. This drags down coverage_conf, which carries a 45% weight
      (CONFIDENCE_RETRIEVAL_WEIGHT = 0.55).
  3. Hardcoded Fallback Values:
      • For cached entries or guardrail hits, the code assigns hardcoded confidence values (1.0 / 100% or 0.95), making scores oscillate abruptly between 20–30% (from RAG) and 95–100% (from cache/guardrails), creating a
      "fake" or synthetic feeling.


  #### B. In Scenario / "What-If" Analysis (whatif_ai.py):
  • The LLM prompt asks the model to emit a self-reported JSON "confidence": 0-100.
  • The system prompt explicitly instructs:
  │ "unclear: the provided policy excerpts don't clearly cover this scenario. Use confidence <= 40 in this case."
  │ "If nothing relevant was provided at all, return verdict 'unclear' with confidence 0."
  • Large Language Models are notoriously poor and arbitrary at estimating their own confidence on a 0–100 scale, making the output feel artificial and clustered around 0%, 20%, 40%, or 90%.
  ──────
  Skipped: No code or database changes were made.
  Risk: Until the policy_id_seq sequence is aligned, all new policy creations will fail with a 500 error.
> /model
  ⎿  Model set to Gemini 3.8 Flash (Medium)

────────────────────────────────────────────────────────────
> dont touch anything find all issues related to what if simulator and ai assistent

● Ran (grep -rn "what_if" blueprints/ app.py)
● Explored 2 files (what_if.py, whatif_ai.py)
… 36 more actions (8 reads, 26 commands, 2 tasks: 8 failed) …
● Ran 2 commands (grep -rn "DEFAULT_REFUSAL_MESSAGE" rag/ · grep -rn "build_streaming_qa_prompt" rag/)
● Explored 1 file (prompts.py) (ctrl+o to expand)

  An in-depth code and architecture audit of both the What-If Simulator and the AI Policy Assistant was conducted. No code has been touched or modified.

  Here are all the critical issues, root causes, and architectural flaws identified across both systems:
  ──────
  ### Part 1: What-If Simulator Issues (whatif_ai.py & blueprints/what_if.py)
  #### 1. ChromaDB Vector Store Parameter Call Mismatch (Silent Failure to Zero Filters)
  • In whatif_ai.py:115-120:
    try:
        hits = store.search(query_embedding=q_vec, query_text=scenario, top_k=top_k_retrieve, active_only=True, allowed_departments=allowed_depts)
    except TypeError:
        hits = store.search(embedding=q_vec, filters={}, top_k=top_k_retrieve)
  • In rag/vectordb/chroma.py, ChromaVectorStore.search signature is:
    def search(self, embedding: List[float], filters: dict, top_k: int = 50)
  • Because query_embedding and active_only do not exist as kwargs on ChromaVectorStore.search, it always raises a TypeError, silently dropping into the except block with filters={}.
  • Impact: The simulator never filters by is_active: True. Chunks from deprecated, draft, and superseded versions get pulled in and fed to the LLM. This was directly observed in database records #17 & #18 where the
  model was confused by multiple contradictory policy versions.

  #### 2. Query Mismatch: Treating Questions as Compliance Scenarios
  • In the prompt to the LLM (whatif_ai.py:34-54):
  The prompt instructs the model that the input is an action an employee wants to do (e.g., "I want to expense a laptop"), and forces one of 4 verdicts: compliant, not_compliant, depends, or unclear.
  • When a user inputs a question (e.g. "how many leaves can i take in a year"), the model cannot evaluate compliance, so it defaults to unclear with a hardcoded confidence: 40.
  • The UI also provides no semantic distinction or guidance to the user between open-ended queries (intended for AI Assistant) and actionable scenarios.

  #### 3. LLM Self-Reported Confidence Hallucination

  • The confidence score in What-If is purely a hallucinated number generated by the LLM via prompt instruction: "confidence": <integer 0-100>.
  • It does not use the retrieval ranking, cross-encoder scores, or the calibrated confidence engine.
  • The system prompt even forces artificial numbers:
  │ "If nothing relevant was provided, return verdict 'unclear' with confidence 0."
  │ "Use confidence <= 40 in this case."
  │ This causes confidence to artificially snap to 0, 40, or 100 with zero continuous statistical grounding.

  #### 4. Hardcoded Heuristic Fallback Skews All Analytics

  • If an LLM call fails or times out (whatif_ai.py:70), it produces:
  {"verdict": "unclear", "confidence": 20, ...} or {"verdict": "unclear", "confidence": 0}.
  • Every single one of these gets saved to what_if_query with flagged_for_hr = True, flooding the HR review queue with phantom low-confidence queries whenever the LLM is slightly slow or returns invalid JSON.
  ──────
  ### Part 2: AI Policy Assistant Issues (rag/engine/query_engine.py & rag/verification/confidence.py)
  #### 1. Over-Penalizing Calibration Curve (calibration_knots.json)

  • The confidence pipeline passes raw retrieval/coverage scores through an Isotonic Calibrator loaded from calibration_knots.json:
      • [0.1111, 0.0]
      • [0.2222, 0.1158]
      • [0.3333, 0.3225]
  • Even when a retriever finds good, relevant chunks (e.g., a raw composite score of 0.25 to 0.40), the calibrator drastically squashes it down to 12% – 32%.
  • In rag/chatbot/chat_service.py#L75:
    "confidence": int(result.confidence * 100)
  A 0.25 score is displayed directly as 25% to the user.

  #### 2. Fragile N-Gram Overlap in _evidence_coverage

  • In confidence.py:136-158:
      • Coverage is calculated by extracting non-stopwords from the user query, stemming them with a naive suffix-stripper (_stem), and matching them against chunk stems.
      • If a user asks a question using natural language (e.g., "Can I get paid time off when my child is born?"), while the policy chunk uses formal terminology ("Parental and Maternity Benefit Entitlement"), the
      stemmed token overlap is near 0.
      • coverage_conf drops to ~0.05. With a 45% weight in CONFIDENCE_RETRIEVAL_WEIGHT, this drags the entire composite score down into the abstention zone (< 0.20), causing the system to refuse to answer
      (DEFAULT_REFUSAL_MESSAGE).


  #### 3. Bimodal Discontinuity: Synthetic 100% vs Low 20%

  • In rag_routes.py:67 and semantic_cache.py:244:
      • Guardrail blocks, exact cached responses, or fast-path facts default to 1.0 (100%).
      • Normal RAG responses that went through semantic retrieval and calibration get calculated in the 20%–45% range.
      • The user experiences jarring swings: identical or similar queries jump between 24% and 100%, eroding user trust.


  #### 4. Streaming Answer Verification Desynchronization
  • In query_engine.py:831-845:
      • When streaming, the query engine streams LLM tokens into a buffer, but only runs grounding verification (_verify_candidate) after all tokens have already been generated and buffered.
      • If NLI verification fails (not grounded or contradictory), it throws away the buffer and returns DEFAULT_REFUSAL_MESSAGE. But because this is SSE streaming, if any tokens were already sent to the frontend, the UI
      will exhibit glitchy display behavior (abruptly cutting off or replacing text).

  ──────
  ### Part 3: Database & Infrastructure Bottlenecks Affecting Both
  1. PostgreSQL Sequence Desynchronization Across Tables:
      • Running a diagnostic query across all 42 tables revealed three primary keys are out of sync:
          • policy.id: max table value is 120, sequence is at 23 (Causes the 500 on create policy)
          • policy_version.id: max table value is 12001, sequence is at 23 (Will cause 500 when saving new versions)
          • department.id: max table value is 12, sequence is at 8

  2. Pending Rollback Cascading:
      • In blueprints/admin.py, database operations that fail inside a view do not have a dedicated db.session.rollback() in their exception handler.
      • When SQLAlchemy throws UniqueViolation, the session stays dirty. When Flask's 500 error handler tries to render templates/errors/500.html, it queries current_user.can_manage_policies(), which triggers another
      database load on the unrolled transaction and raises PendingRollbackError, masking the real error with a second 500.

  ──────
  Skipped: Code edits and DB queries were kept strictly read-only.
  Operational Risk: Any attempt to insert a new version into policy_version or a new policy into policy will immediately fail until the sequence values are updated to match their table maximums.
