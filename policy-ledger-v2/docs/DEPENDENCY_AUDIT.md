# Dependency Audit Report

## Summary: 2 High, 2 Medium, 2 Low

---

## 1. Missing Packages in `venv` — **HIGH**
**File:** `requirements.txt`

Three packages declared in `requirements.txt` are **not installed** in the project `venv`. They are actively used in source code.

| Package | Used In | Impact |
|---|---|---|
| `rank-bm25` | `rag/vectordb/chroma.py:139` | BM25 hybrid search silently disabled at runtime (lazy import, not a crash). |
| `matplotlib` | `eval/` scripts only | No production code affected. Low risk in production. |
| `pandas` | `eval/` scripts only | No production code affected. Low risk in production. |

**Severity:** `rank-bm25` is **HIGH** (core RAG search degraded silently). `matplotlib`/`pandas` are **LOW** (eval-only).

**Fix:** `venv/bin/pip install rank-bm25 matplotlib pandas` and ensure they appear in `requirements.lock.txt`.

---

## 2. `alembic.ini` Hard-coded Production DB URL — **HIGH**
**File:** `alembic.ini:6`

```
sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/policy_ledger
```
This hard-codes a PostgreSQL connection string with default credentials. `alembic upgrade` will fail locally against SQLite and will attempt to connect to localhost PostgreSQL in CI, leaking default credentials.

**Fix:** Set `sqlalchemy.url = %(DATABASE_URL)s` and pass the env var via `alembic -x DATABASE_URL=...` or override in `env.py`.

---

## 3. Migration Drift — Column `prompt_tokens`, `completion_tokens`, `model_used`, `cache_hit` — **MEDIUM**
**File:** `alembic/versions/002_add_chat_tokens.py` vs `models.py`

Migration 002 adds `prompt_tokens`, `completion_tokens`, `model_used`, `cache_hit` to `chat_message`. A search of `models.py` found **no corresponding columns** in the `ChatMessage` model. The migration has been applied to the DB but the ORM model is out of sync — any code that tries to `SELECT` those columns via ORM will silently get `None`, but `INSERT`/`UPDATE` via ORM will not write them.

**Fix:** Add the four columns to the `ChatMessage` model in `models.py`.

---

## 4. `.env` vs `.env.example` Drift — **MEDIUM**
**File:** `.env:15`

| Key | `.env` Value | `.env.example` Value |
|---|---|---|
| `LLM_BACKEND` | `extractive` | `ollama` |
| `DATABASE_URL` | commented out | active |

- `.env` uses `LLM_BACKEND=extractive` but `.env.example` documents `ollama` as the default. The `extractive` backend may not be the recommended starting point for new developers — this should be documented clearly in `.env.example`.
- `.env` has `DATABASE_URL` commented out (falling through to `config.py` SQLite default), while `.env.example` has it active. This discrepancy can confuse new developers.

**Fix:** Sync both files to use the same defaults or add an explanatory comment.

---

## 5. `docker-compose.yml` Uses Hardcoded Secret in Dev — **LOW**
**File:** `docker-compose.yml:17`

```yaml
- SECRET_KEY=dev-secret-key-change-in-prod
```
This is intentional for dev, but if a developer accidentally starts this compose in production, the check in `validate_production_env` would catch it. Still, a `${SECRET_KEY:-dev-secret-key-change-in-prod}` pattern is safer.

**Fix:** Use `${SECRET_KEY:-dev-secret-key-change-in-prod}` to allow override without touching the file.

---

## 6. `docker-compose.prod.yml` Missing `UPLOAD_FOLDER` volume — **LOW**
**File:** `docker-compose.prod.yml:46-48`

The prod compose uses `read_only: true` on the web container and only mounts `/tmp` and `/app/data/uploads` as tmpfs. However, `data/chroma/` (the ChromaDB persistence directory) is **not mounted** as a volume. This means the vector DB is ephemeral and will be wiped on container restart.

**Fix:** Add a named volume for `data/chroma/` in the prod compose or switch ChromaDB to its HTTP server mode.
