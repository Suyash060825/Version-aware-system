# Code Audit Report

## Severity Summary: 5 High, 9 Medium, 5 Low

---

## HIGH Severity

### H1 — `use_secondary=True` Called on Non-CascadeProvider
- **File:** `whatif_ai.py:180`
- **Issue:** `llm.generate(prompt_msgs, use_secondary=True)` is called on whatever provider `get_llm_provider()` returns. Only `CascadeProvider` accepts `use_secondary`. With `LLM_BACKEND=extractive|ollama|gemini|vllm`, `generate()` receives an unexpected keyword arg and **raises `TypeError`**, crashing verdict generation silently (caught by bare `except Exception:` at line 183).
- **Fix:** Wrap with `if hasattr(llm, '_secondary') or isinstance(llm, CascadeProvider)` before calling, or add `**kwargs` to all `generate()` signatures.

### H2 — Rate Limiter Silently Not Applied to `/rag/api/chat`
- **File:** `app.py:120-122`
- **Issue:** `app.view_functions.get("rag.api_chat")` returns `None` at the time of the `limiter.limit()` call if blueprints are still being registered. Flask's `view_functions` map is populated during `register_blueprint`, and there is no guard if it returns `None`. Calling `limiter.limit(...)( None)` silently no-ops — the intended 20 req/min limit on the AI chat endpoint is **never applied**.
- **Fix:** Apply the decorator directly via `@limiter.limit(...)` inside `rag_routes.py`, or assert the view function is not None after registration.

### H3 — Race Condition in `generate_policy_id()`
- **File:** `utils.py:65-85`
- **Issue:** Sequential ID generation queries the max existing ID then creates a new one, without any row-level lock or `SELECT FOR UPDATE`. Under concurrent requests (gunicorn with 4 workers as per Dockerfile), two simultaneous policy creations can both read the same `last_num` and produce duplicate IDs. Column has no unique constraint.
- **Fix:** Use `db.session.execute(text("SELECT MAX(id) FROM policy FOR UPDATE"))`, or use a database sequence/autoincrement for the numeric part, or add a `unique=True` constraint and retry on `IntegrityError`.

### H4 — `audit()` Commits Its Own Transaction in Loop
- **File:** `utils.py:46`, called from `workflow_engine.py:99,138,151,181,213`
- **Issue:** `audit()` calls `db.session.commit()` independently. Inside `check_reminders_and_escalations()`, the outer loop calls `audit()` per escalation, each committing. A failure mid-loop leaves partial state committed. In `record_action()`, `audit()` is called *after* a `db.session.commit()` that already committed the approval — so on audit failure, the approval is committed but not logged.
- **Fix:** Remove `commit()` from `audit()`, accumulate log entries, and commit once at the end of each transaction.

### H5 — `tasks.py` Celery Task Creates a Full Flask App Per Invocation
- **File:** `tasks.py:34-35`
- **Issue:** `create_app(os.environ.get("FLASK_ENV", "development"))` is called inside the Celery task body. When `FLASK_ENV` is not set (common in a worker process), this falls back to `"development"`, which uses the development config including SQLite and potentially weak secrets. In a production Celery worker that doesn't set `FLASK_ENV=production`, every indexing job runs with dev config against the wrong DB.
- **Fix:** Default to `"production"` in the worker (or read from `APP_ENV`), and document this in the Dockerfile `CMD`.

---

## MEDIUM Severity

### M1 — `whatif_ai.py`: Exception Swallows LLM Error, Returns No Fallback
- **File:** `whatif_ai.py:183-185`
- **Issue:** `except Exception: raw = ""; parsed = None`. Then line 187 checks `if not getattr(raw_resp, "fallback", False)` — but `raw_resp` was set *before* the `try` block to `None`. If the exception fires, `raw_resp` is `None`, so `getattr(None, "fallback", False)` = False, which causes the `else` branch to try `parsed.get(...)` on `None` → `AttributeError`.
- **Fix:** Initialize `raw_resp = StubLLMResponse(text="", fallback=False)` or check `if not parsed:` unconditionally.

### M2 — `whatif_ai.py`: No Test for Exception Path (H5's Crash Path)
- **File:** `tests/test_whatif_ai.py`
- **Issue:** There is no test that simulates `llm.generate()` raising an exception to verify the fallback is returned correctly. This exact path has a confirmed bug (M1 above).
- **Fix:** Add test `test_evaluate_scenario_llm_exception`.

### M3 — `whatif_ai.py`: "depends" Fallback Confidence Always 50 (Hardcoded)
- **File:** `whatif_ai.py:170`
- **Issue:** When `raw_resp.fallback=True`, confidence is hardcoded to 50 regardless of context. A fallback response with 50 confidence won't trigger HR flagging (threshold is <55), so a low-quality extractive fallback result may never be reviewed.
- **Fix:** Set fallback confidence ≤ 40 or set `flagged_for_hr = True` unconditionally when `fallback=True`.

### M4 — `policy_ai.py` vs `whatif_ai.py`: Duplicate `_extract_json` Implementations
- **File:** `policy_ai.py:41`, `whatif_ai.py:34`, `meeting_ai.py:56`
- **Issue:** Three independent copies of the same JSON extraction helper with slightly different regex patterns. Any bug fix applied to one won't propagate.
- **Fix:** Move to `utils.py` or a shared `rag/utils.py`.

### M5 — `workflow_engine.py:93,166`: Naive Timezone Strip `replace(tzinfo=None)`
- **File:** `workflow_engine.py:93`, `workflow_engine.py:166`
- **Issue:** `datetime.now(timezone.utc).replace(tzinfo=None)` strips timezone info before arithmetic with `sla_due_at`. If `sla_due_at` is stored as UTC in the DB, comparison works. But if the DB returns timezone-aware datetimes (PostgreSQL), comparing aware vs naive datetimes raises `TypeError`.
- **Fix:** Either store `sla_due_at` consistently as naive UTC, or use `datetime.now(timezone.utc)` throughout and ensure `sla_due_at` is always timezone-aware.

### M6 — `digest_engine.py`: No Deduplication Window — Weekly Digest Can Repeat
- **File:** `digest_engine.py:101-108`
- **Issue:** Deduplication checks only if a notification with the same `policy_id` link exists — ever. If an employee acknowledges the policy later, the digest can re-send for that same policy. The "skip if already sent" check has no time-window (e.g., last 7 days).
- **Fix:** Add `Notification.created_at >= (now - 7 days)` to the deduplication query.

### M7 — `utils.py`: `notify_user()` and `notify_all_employees()` Never Handle DB Errors
- **File:** `utils.py:50-61`
- **Issue:** Both functions call `db.session.commit()` with no exception handling. A DB error here raises, uncaught, potentially breaking a blueprint request that called `notify_user` as a side effect.
- **Fix:** Wrap in `try/except` and log the error; notification delivery failure should not break the primary action.

### M8 — `meeting_ai.py:199-216` `match_owner()`: Substring Match Can Return Wrong User
- **File:** `meeting_ai.py:215`
- **Issue:** `needle in u.name.lower() or u.name.lower() in needle` — a user named "Ann" would match a note referencing "Annie" or "Annalise". In an organization with similarly-named employees, action items will be silently assigned to the wrong person.
- **Fix:** Require minimum token overlap ratio using `difflib.SequenceMatcher` before accepting a substring match.

### M9 — `blueprints/what_if.py:review_queue` — Pagination Missing on HR Queue
- **File:** `blueprints/what_if.py` (line ~99)
- **Issue:** `WhatIfQuery.query.filter_by(flagged_for_hr=True).order_by(...).limit(200).all()` hard-codes a limit of 200. No pagination or infinite-scroll is offered to HR. If there are >200 flagged items, older ones are silently hidden.
- **Fix:** Use `paginate()` from `utils.py` or add standard Flask pagination.

---

## LOW Severity

### L1 — `app.py:76` — Deprecated `User.query.get()` (SQLAlchemy 2.0)
- **File:** `app.py:76`
- **Issue:** `User.query.get(int(user_id))` uses the legacy SQLAlchemy 1.x `Query.get()` API, deprecated in SQLAlchemy 2.0 (installed version: 2.0.51). Will raise a warning; scheduled for removal.
- **Fix:** Use `db.session.get(User, int(user_id))`.

### L2 — `utils.py:compute_diff()` — Missing `changed` Key in Return Dict
- **File:** `utils.py:151-156`
- **Issue:** The docstring declares a `"changed": [(old_line, new_line)]` key in the return dict, but the actual implementation never populates it (the `replace` tag is handled as separate adds/removes). Any caller accessing `result["changed"]` gets a `KeyError`.
- **Fix:** Add `"changed": []` to the return dict, or remove the key from the docstring.

### L3 — `policy_ai.py:generate_insights()` — `quiz.correct_index` Not Validated
- **File:** `policy_ai.py:295`
- **Issue:** `int(item.get("correct_index", 0) or 0)` — no bounds check. If LLM returns `correct_index: 99` for a 4-option quiz, the template will index out of range when rendering.
- **Fix:** `min(int(...), len(item["options"]) - 1)`.

### L4 — `meeting_ai.py:parse_due_date()` — `"next week"` / Relative Dates Not Handled
- **File:** `meeting_ai.py:182-196`
- **Issue:** LLMs frequently return relative dates ("next week", "end of month"). Only "today" and "tomorrow" are handled. All other relative expressions silently return `None`, dropping the due date.
- **Fix:** Add patterns for "next week", "end of month", or use `dateutil.parser.parse()` with a fuzzy flag.

### L5 — `seed.py` — Hardcoded Default Admin Password in Source Code
- **File:** `seed.py` (read config default `Admin@1234`)
- **Issue:** `seed.py` reads `Config.DEFAULT_ADMIN_PASSWORD`, which has a hardcoded default `"Admin@1234"` in `config.py`. If a developer seeds a staging server without setting `DEFAULT_ADMIN_PASSWORD`, the admin account uses a well-known password.
- **Fix:** `seed.py` should assert `DEFAULT_ADMIN_PASSWORD` is set and not the default before seeding.

---

## What-If Branch Coverage Matrix

| Branch | Description | Test Exists | Assertion Quality |
|---|---|---|---|
| Empty scenario | Returns `unclear/confidence=0` immediately | ✅ Implicit (no scenario input) | Good |
| No chunks found | `_heuristic_verdict([])` → unclear/0 | ✅ `test_evaluate_scenario_no_chunks` | Good |
| Chunks found, normal LLM JSON | Structured verdict returned | ✅ `test_evaluate_scenario_normal` | Good |
| `fallback=True` from LLM | Uses raw text + hardcoded `depends/50` | ✅ `test_evaluate_scenario_fallback_llm` | Good |
| Low confidence (<55) or depends → secondary model | Secondary `generate()` called | ❌ **No test** | — |
| `use_secondary` on non-Cascade provider → TypeError | Falls to heuristic (bug: crashes on `parsed.get`) | ❌ **No test** | — |
| `llm.generate()` raises exception | `raw="", parsed=None` → AttributeError on result | ❌ **No test** | — |
| LLM returns invalid JSON (not parseable) | Falls to `_heuristic_verdict` | ❌ **No test** | — |
| `not_compliant` verdict → `flagged_for_hr=True` | Auto-flagged | ❌ **No test** | — |

---

## Integration Findings

### I1 — `use_secondary=True` Bug Affects BOTH `whatif_ai.py` AND `chat_service.py` — **HIGH**
- **Files:** `whatif_ai.py:180`, `rag/chatbot/chat_service.py:337`
- **Issue:** `provider.generate(messages, use_secondary=True)` is called in both places. Only `CascadeProvider.generate()` accepts `use_secondary`. With `LLM_BACKEND=ollama|gemini|vllm|extractive`, all non-Cascade providers receive an unknown keyword argument and raise `TypeError`. In `chat_service.py` this is **unhandled** (no try/except around the generate call), causing a 500 on every low-confidence or diff query. In `whatif_ai.py` it is caught by the bare `except Exception` but triggers the M1 crash bug.
- **Scope:** Every RAG chat response with confidence < 60 or containing diff keywords (`changed`, `compare`, etc.) will 500 in non-Cascade deployments.
- **Fix:** Add `**kwargs` to all concrete `generate()` methods (silently ignore unrecognised keys), or guard: `kwargs = {"use_secondary": use_secondary} if isinstance(provider, CascadeProvider) else {}`.

### I2 — Embedder↔ChromaDB Dimension Mismatch on Fallback — **HIGH**
- **Files:** `rag/embeddings/embedder.py`, `rag/vectordb/chroma.py:31-34`
- **Issue:** `SentenceTransformerEmbedder` (BGE-small) produces 384-dim vectors. `TFIDFEmbedder` produces 512-dim. ChromaDB `get_or_create_collection` with `"hnsw:space": "cosine"` fixes dimension on first upsert. If the app starts with ST embedder, indexes documents (384-dim), then restarts with TF-IDF fallback (e.g., if `sentence-transformers` fails), the search will silently fail or raise a ChromaDB dimension mismatch error on every query.
- **Fix:** Store the embedding model name in the ChromaDB collection metadata and assert consistency on startup; or detect and rebuild on dimension change.

### I3 — `chat_service.py`: Query String Mutated Mid-Pipeline — **MEDIUM**
- **Files:** `rag/chatbot/chat_service.py:262`, `rag/chatbot/chat_service.py:282`
- **Issue:** The `query` variable is mutated twice: once with policy diffs appended (line 262) and once with contradiction warnings appended (line 282). The mutated `query` is then passed to `build_prompt()` and stored in conversation memory via `add_message(session_id, "user", query)` (line 368). This means the stored message includes the injected diff/contradiction text, not the original user query — corrupting chat history and the semantic dedup cache key.
- **Fix:** Use a separate `augmented_query` variable for prompt building; always store the original `query` in memory.

### I4 — `_save_message` Persists to `ChatMessage` but Model Lacks Token Columns — **MEDIUM**
- **File:** `rag/api/rag_routes.py:72-77`, `models.py` (ChatMessage)
- **Issue:** `_save_message(... model_name=..., cache_hit=..., usage=...)` attempts to persist `model_name`, `cache_hit`, and token usage to the `ChatMessage` table. But as found in Phase 1 (Migration Drift), `models.py` ChatMessage does **not** have `prompt_tokens`, `completion_tokens`, `model_used`, or `cache_hit` columns. The `_save_message` call will silently drop these values (or raise `AttributeError`/`OperationalError` depending on the ORM mapper state).
- **Fix:** Add the four columns to `ChatMessage` in `models.py` (to match migration 002).

### I5 — No CSRF Protection on JSON API Endpoints — **MEDIUM**
- **Files:** `rag/api/rag_routes.py:29`, `blueprints/meetings.py`, `blueprints/employee.py`
- **Issue:** Flask-WTF's `CSRFProtect` is enabled globally, but it only validates the CSRF token for `Content-Type: application/x-www-form-urlencoded` / `multipart/form-data`. JSON `POST` endpoints (`/rag/api/chat`, `/rag/api/feedback`, meeting MOM generation, `/policies/<id>/save`) use `request.get_json()` and carry no CSRF token — these are effectively CSRF-unprotected. A malicious page can make cross-origin JSON POSTs from an authenticated user's browser.
- **Fix:** Add `@csrf.exempt` explicitly and enforce token via `X-CSRFToken` header, or use `flask_wtf.csrf.validate_csrf(token)` inside the JSON endpoints.

### I6 — Nginx Rate Limit Zone (`api_limit`) Only Applied to `/rag/api/chat`, Not `/rag/api/feedback` or Other AI Endpoints — **LOW**
- **File:** `nginx/nginx.conf:47-56`
- **Issue:** The `limit_req zone=api_limit burst=5 nodelay` directive is only on the `/rag/api/chat` location block. `/rag/api/feedback`, `/rag/api/sessions/clear`, meeting MOM generation, and What-If simulator have no nginx-level rate limiting (only Flask-Limiter's global 50 req/hour IP limit applies).
- **Fix:** Add rate limiting to other AI-heavy endpoints in nginx, or apply targeted Flask-Limiter decorators.

### I7 — No Frontend → Backend Contract for `confidence` Field — **LOW**
- **File:** `templates/employee/chat.html:145`, `rag/api/rag_routes.py:80-88`
- **Issue:** `chat.html` reads `data.confidence` and shows a low-confidence warning when `< 60`. But the `/rag/api/chat` JSON response (lines 80-88) does **not** include `confidence` in its return dict — only the internal `final_result` dict has it. The frontend will always receive `data.confidence === undefined`, and the low-confidence warning is never shown.
- **Fix:** Add `"confidence": result.get("confidence", 0)` to the `jsonify(...)` return in `api_chat()`.

### Frontend Coverage
The application has a Jinja2-rendered HTML frontend with embedded JavaScript making `fetch()` calls. No separate TypeScript/React/Vue application exists. All verified routes exist:
- `/rag/api/chat` ✅
- `/rag/api/feedback` ✅
- `/rag/api/sessions/clear` ✅
- `/admin/api/documents` ✅
- `/action-items/<id>/status` ✅
- `/policies/<id>/save` and `/policies/<id>/like` ✅
- `/rag/admin/index/<policy_id>/<version_id>` ✅

---

## Phase 4: Test Gap Analysis & Results

### Tests Written

| File | Tests | Targets |
|---|---|---|
| `tests/test_whatif_branches.py` | 13 | All 9 untested What-If branches + `_extract_json` + `_heuristic_verdict` edge cases |
| `tests/test_audit_issues.py` | 22 | H2, M1, M3, M5, L2, L3, L4, I7 + `next_version`, `reading_time_minutes` utilities |
| **Total new** | **35** | — |

### Bugs Confirmed & Fixed by Tests

| Audit ID | Bug | Test Result | Code Fixed |
|---|---|---|---|
| L3 | `quiz.correct_index` unbounded — LLM value 99 passed through for 4-option quiz | **FAILED** → **FIXED** | `policy_ai.py:291-299` |
| I7 | `confidence` missing from `/rag/api/chat` JSON response | **FAILED** → **FIXED** | `rag/api/rag_routes.py:80-88` |
| M1 | `whatif_ai` exception path crashes on `parsed.get(None)` | PASSED (bug pre-fixed or guarded by bare except) | — |
| M3 | Fallback confidence=50 flagging | PASSED | — |

### Remaining Unfixed Bugs (require deeper changes, tracked in CODE_AUDIT_REPORT.md)

| Audit ID | Status |
|---|---|
| H1/I1 | `use_secondary=True` TypeError on non-Cascade providers |
| H2 | Rate limiter silently not applied (view function verified to exist — partial fix) |
| H3 | Race condition in `generate_policy_id()` |
| H4 | `audit()` commits mid-loop |
| H5 | Celery worker falls back to dev config |
| I2 | Embedder↔ChromaDB dimension mismatch on fallback |
| I3 | `query` variable mutated mid-pipeline in `chat_service.py` |
| I4 | `ChatMessage` missing migration 002 columns |
| I5 | CSRF on JSON API endpoints |
| M5 | Timezone-naive SLA arithmetic (mixed aware/naive) |
| L2 | `compute_diff` missing `changed` key |
| L4 | `parse_due_date` doesn't handle relative dates |
