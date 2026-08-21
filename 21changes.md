# Engineering Audit & Fixes Report

This document outlines all the critical engineering, security, and architectural fixes applied to the `Version-aware-system-21-2` codebase.

## 1. Security & Authorization
* **RAG Session Ownership (`rag/api/rag_routes.py`)**: Secured `/rag/api/chat` by explicitly verifying that the provided `session_id` belongs to the `current_user.id`. Prevents users from injecting messages into or reading from other users' sessions (403 Unauthorized).
* **Feedback Ownership (`rag/api/rag_routes.py`)**: Secured `/rag/api/feedback` to query the `message_id` and ensure the message role is `"assistant"` and the parent session belongs to `current_user.id`.
* **CSRF Protection (`rag/api/rag_routes.py`)**: Removed unsafe `@csrf.exempt` decorators from authenticated API endpoints (`/rag/api/chat`, `/rag/api/feedback`, `/rag/api/sessions/clear`).
* **Meeting IDOR (`blueprints/meetings.py`)**: Added missing authorization to the calendar export route (`/meetings/<id>/calendar.ics`). Consolidated access logic into a new `_can_view(meeting)` helper applied across all meeting endpoints.
* **Legacy Approval Authorization (`blueprints/admin.py`)**: Secured `/approvals/<approval_id>/act` by enforcing strict role checks based on the `ApprovalStage` (e.g., HR only for `HR_REVIEW`, Admin for `LEGAL_REVIEW`) and ensuring the approval targets the currently active policy version.

## 2. RAG Isolation & Data Privacy
* **Role/Department Isolation (`rag/chatbot/chat_service.py`, `whatif_ai.py`)**: Fixed a bug where employees were implicitly granted access to `Human Resources`, `IT`, and `Legal` policies. Employees are now strictly restricted to company-wide policies and their explicit department. Managers additionally gain access to `Management` policies. HR/Admin remain unrestricted.
* **Context-Aware PII Redaction (`rag/guardrails.py`, `rag/llm/prompt_builder.py`)**: Shifted PII redaction to operate securely before chunks enter the LLM prompt, rather than just scrubbing the LLM's output. 
* **Role-Based PII Visibility**: PII redaction is now role-aware. Employees receive `[REDACTED_*]` placeholders, while HR and Admins retain visibility into necessary data (e.g., employee IDs) across both the LLM context and final output.

## 3. Distributed Architecture & Multi-Worker Support
* **Celery Background Tasks (`tasks.py`, `rag/api/rag_routes.py`)**: Replaced unsafe, process-local `threading.Thread(...)` calls with a dedicated `self_healing_task` routed through Celery to ensure reliable background execution across workers.
* **Multi-Worker Chat Memory (`rag/chatbot/memory.py`)**: Migrated in-memory conversational history (`_sessions` dict) to Redis lists (`chat_mem:<session_id>`) with a 24-hour TTL, ensuring consistent context when requests bounce between different Gunicorn workers.
* **BM25 Staleness Invalidation (`rag/vectordb/chroma.py`)**: Fixed ChromaDB's local BM25 index caching for multi-worker setups. Introduced `_bump_bm25_revision()` via Redis to broadcast index mutations. Workers now check this revision and rebuild their local BM25 index on-the-fly when it diverges.

## 4. Correctness & Error Handling
* **Entailment Robustness (`rag/entailment.py`)**: Fixed a hard indentation/syntax error. Updated the implementation to dynamically reference `nli.model.config.label2id` for entailment indices and safely handle 1-D vs 2-D array outputs.
* **Self-Healing API Signature (`rag/chatbot/self_healing.py`)**: Fixed a schema mismatch in `SemanticCache.put()`. It now correctly maps citations back to `policy_id` and `version_id` properties, ensuring self-healed answers participate in version invalidation.
* **Removed Silent Failures (`rag/indexing/index_policy.py`, `rag/vectordb/chroma.py`)**: Systematically replaced dangerous `except Exception: pass` blocks with structured exception handling, `db.session.rollback()` calls, and proper logging (`logging.getLogger`).

## 5. Production Configurations & Hygiene
* **Production Database Initialization (`app.py`)**: Ensured `db.create_all()` executes strictly in non-production environments (`FLASK_ENV != "production"`). Production setups must use Alembic migrations.
* **Fail-Fast Secrets (`config.py`)**: Added validation to `ProductionConfig` that enforces a hard crash if `SECRET_KEY` or `DEFAULT_ADMIN_PASSWORD` are left as their default, insecure values.
* **Health Check Leaks (`rag/api/rag_routes.py`)**: Scrubbed `/rag/health` and `/rag/health/llm` of sensitive internal data. Endpoints no longer leak raw exception stack traces, LLM backend paths, or active model names to unauthenticated callers.
* **Artifact Cleanup**: Deleted local, persisted runtime databases (`dump.rdb`, `chroma.sqlite3`) from the source repository and aggressively updated `.gitignore` and `.dockerignore` to exclude them globally.

## 6. Testing
* **New Security Suites**: Created `tests/test_api_security.py` to assert CSRF token presence and validate that cross-user session/feedback manipulation results in `403 Unauthorized`.
* **New Entailment Suites**: Created `tests/test_entailment.py` to validate entailment evaluation, contradictions, and malformed inputs.
