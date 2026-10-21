# Veritas Repository Inventory & Architectural Decomposition

**Target Revision:** `repo-repair-consistency` (`3aaf601`)  
**Audit Date:** 2026-10-21  
**Auditor:** Principal Software Architect, Senior Python/DevOps Engineer, Application Security Auditor  

---

## 1. Application Entry Points

| Entry Point | Path | Role & Operational Context |
|---|---|---|
| **Web Server Entry** | [`wsgi.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/wsgi.py) | Gunicorn WSGI entrypoint for production Docker deployment (`gunicorn -c gunicorn.conf.py wsgi:application`). |
| **Flask Factory** | [`app.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/app.py) | `create_app(env)` application factory, blueprint registration, extensions initialization, diagnostic logging, and health probe endpoints (`/health/live`, `/health/ready`, `/health/llm`, `/metrics`). |
| **Worker Entry** | [`tasks.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/tasks.py) | Celery application (`celery_app = make_celery()`) and task worker definitions (`tasks.compile_policy_version_task`, `tasks.scan_contradictions_task`, `tasks.dispatch_policy_digest_task`, `tasks.rebuild_knowledge_graph_task`, `tasks.self_heal_message_task`). |
| **Evaluation Entry** | [`evaluation/run_benchmark.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/evaluation/run_benchmark.py) | Master evaluation harness executing 9 sequential phases across real Docker Compose services. |
| **Seeding Entry** | [`seed.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/seed.py) / [`scripts/seed_characterization_ledger.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/scripts/seed_characterization_ledger.py) | Database seeding scripts generating initial roles, departments, policy trees, and vector records. |

---

## 2. Major Subsystems & Source Modules

### 2.1 Core Application & Blueprints (`blueprints/`)
- `blueprints/auth.py`: Authentication, MFA (TOTP / PyOTP), session management, Flask-Login routes.
- `blueprints/admin.py`: Administrative dashboard, policy ingestion, publishing workflow, user role management.
- `blueprints/employee.py`: Frontline staff policy browsing, acknowledgements, quiz attempts.
- `blueprints/search.py`: Lexical and vector search user interface.
- `blueprints/policy_ai.py`: Policy intelligence chat interface, citation exploration.
- `blueprints/workflow.py`: Multi-stage approval workflows (sequential / parallel approval chains).
- `blueprints/bi_dashboard.py`: Business intelligence metrics, Redis cache stats, policy analytics.
- `blueprints/compliance.py`: Compliance frameworks (SOC2, ISO27001, HIPAA) and policy mappings.
- `blueprints/audit_center.py`: Immutable audit logging, access trail visualization.
- `blueprints/what_if.py`: Hypothetical scenario simulation and policy blast radius modeling.
- `blueprints/governance.py`: Policy lifecycle governance, review cadences, deprecation schedules.
- `blueprints/confusion_index.py`: Ambiguity scoring and readability analysis across policies.
- `blueprints/contradiction_radar.py`: Cross-policy consistency monitoring and conflict alerts.
- `blueprints/knowledge_graph.py`: Relationship graph between policies, departments, and entities.
- `blueprints/gamification.py`: Employee policy comprehension quizzes and badges.
- `blueprints/ai_analytics.py`: Telemetry on query routing, model usage, and latency.
- `blueprints/blast_radius.py`: Structural dependency tree analysis for proposed policy amendments.
- `rag/api/rag_routes.py`: RESTful RAG API endpoints (`/api/rag/ask`, `/api/rag/feedback`, `/api/rag/compile`).

### 2.2 RAG Engine & Retrieval Pipeline (`rag/`)
- **Query Engine:** `rag/engine/query_engine.py`, `rag/engine/engine_config.py` — Coordinates multi-tier routing (Tier 0 Fact Engine, Tier 1 Canonical QA, Tier 2 Hybrid RAG, Tier 4 Safe Abstention).
- **Retrieval & Reranking:**
  - `rag/retrieval/sparse.py`: Okapi BM25 index with persistent pickle storage.
  - `rag/retrieval/dense.py`: Dense vector retrieval via pgvector / FAISS / Chroma.
  - `rag/retrieval/hybrid.py`: Reciprocal Rank Fusion (RRF) merging dense and sparse scores.
  - `rag/retrieval/reranker.py`: Cross-encoder neural reranking via FlashRank ONNX (`ms-marco-TinyBERT-L-2-v2`).
- **Knowledge Compilation & Parsing:**
  - `rag/compiler/incremental.py`: SHA-256 chunk-level hashing and 95% compute avoidance engine.
  - `rag/compiler/pipeline.py`: Full document compiler converting raw policy files into chunks, facts, and QAs.
  - `rag/chunking/semantic.py`: Section-aware hierarchical document chunking.
  - `rag/parser/`: Structured markdown and PDF parsers.
- **Fact Engine & Canonical QA:**
  - `rag/facts/fact_engine.py`: Structured numerical threshold and entitlement lookup (<1 ms).
  - `rag/qa/qa_index.py`: FAISS HNSW index of pre-compiled canonical Q&A pairs.
- **Verification & Guardrails:**
  - `rag/verification/nli_verifier.py`: DeBERTa cross-encoder entailment and contradiction detection.
  - `rag/guardrails.py`: Input prompt injection detection and PII redaction.
  - `rag/authorization/clearance.py`: Pre-retrieval clearance and department tenancy filtering.
  - `rag/cache/semantic_cache.py`: Multi-level Redis and in-memory semantic cache.

### 2.3 Provider Implementations
- `rag/llm_provider.py`: Core `LLMProvider` interface with `OllamaProvider`, `ExtractiveFallbackProvider`, `vLLMProvider`, `GeminiProvider`, and legacy `OpenAIProvider`.
- `rag/generation/provider.py`: Generation-specific `LocalLLMProvider` interface with streaming think-tag suppression (`_suppress_think_tags`).
- `rag/embeddings/embedder.py`: FastEmbed ONNX embedding generator (`BAAI/bge-small-en-v1.5`, 384 dimensions).

---

## 3. Database Schema & Tables (PostgreSQL 16 + pgvector)

47 database relations managed via SQLAlchemy in [`models.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/models.py):

| Functional Domain | Tables |
|---|---|
| **Identity & Access** | `user`, `department`, `tag`, `policy_category` |
| **Policy Lifecycle** | `policy`, `policy_version`, `policy_chunk`, `policy_chunk_v2`, `policy_tags`, `saved_policies` |
| **Workflow & Approval** | `workflow_template`, `workflow_stage`, `workflow_stage_approver`, `workflow_stage_instance`, `workflow_approval_action`, `approval_workflow` |
| **Knowledge Compilation**| `compilation_job`, `policy_fact`, `policy_entity`, `policy_relationship`, `canonical_question`, `compiled_answer` |
| **Compliance & Radar** | `compliance_framework`, `policy_frameworks`, `contradiction_flag`, `what_if_query` |
| **Audit & Governance** | `audit_log`, `indexing_job`, `feedback`, `search_history`, `saved_search`, `notification` |
| **Collaboration & Quiz**| `policy_acknowledgement`, `policy_like`, `policy_comment`, `quiz_attempt`, `onboarding_checklist_item` |
| **Meetings & Minutes** | `meeting`, `meeting_participant`, `meeting_minutes`, `meeting_decision`, `meeting_action_item`, `meeting_policies` |
| **Chat & AI Reviews** | `chat_session`, `chat_message`, `policy_ai_review`, `policy_ai_insight` |

---

## 4. Celery Background Task Registry

| Task Name | Target Function | Trigger Location | Operational Behavior |
|---|---|---|---|
| `tasks.compile_policy_version_task` | `compile_policy_version_task` | `blueprints/admin.py`, `rag/api/rag_routes.py` | Compiles policy chunks, extracts facts, updates vector embeddings, and builds canonical QAs. Retries up to 3 times on failure. |
| `tasks.scan_contradictions_task` | `scan_contradictions_task` | Periodic cron / Celery beat / manual admin trigger | Scans all published policies with DeBERTa NLI to flag contradictory clauses. |
| `tasks.dispatch_policy_digest_task` | `dispatch_policy_digest_task` | Scheduled weekly / monthly digest generator | Assembles digest of policy updates and dispatches notifications to enrolled users. |
| `tasks.rebuild_knowledge_graph_task` | `rebuild_knowledge_graph_task` | Admin system maintenance | Reconstructs relational edges between policies, departments, and compliance standards. |
| `tasks.self_heal_message_task` | `self_heal_message_task` | `rag/api/rag_routes.py` | Triggered by thumbs-down feedback to re-index or re-evaluate ambiguous queries. |

---

## 5. Unreferenced, Duplicated, or Obsolete Modules Identified

1. **Legacy Cloud SDK:** `openai>=1.51.0` in `requirements.txt` and `OpenAIProvider` in `rag/llm_provider.py` (violates local-only offline execution mandate; cloud APIs must be disabled/removed).
2. **Provider Duplication:** `OllamaProvider` defined independently in `rag/llm_provider.py` and `rag/generation/provider.py` with separate timeout and option handling.
3. **Database URL Silent Fallback:** In `config.py`, an unhandled socket exception silently rewrites `DATABASE_URL` from PostgreSQL to SQLite (`data/ledger.db`), concealing infrastructure networking failures.
4. **Dispersed Configuration Defaults:** Multiple modules implement their own fallback defaults for `REDIS_URL`, `LOCAL_LLM_MODEL`, `OLLAMA_BASE_URL`, and cache TTLs.
