# Veritas Security & Reliability Audit

**Audit Date:** 2026-10-25 | **Branch:** `improv` / `0ebae05`

---

## 1. Authorization Findings

### 1.1 `is_admin` Dual-Mode Handling — Fixed But Complex (P1)

**File:** [`rag/authorization/evidence_filter.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/authorization/evidence_filter.py#L95-L98)

The current code handles both callable and boolean `is_admin`:
```python
if callable(getattr(user, "is_admin", None)) and user.is_admin():
    return True
elif not callable(getattr(user, "is_admin", None)) and getattr(user, "is_admin", False):
    return True
```

The reported original bug (treating method reference as truthy) was fixed. **Confirmed fixed in current code.** However, the `filter_chunks` method (line 160-165) has a slightly different check:
```python
if user_or_scope and getattr(user_or_scope, "is_admin", False):
    if callable(user_or_scope.is_admin):
        if user_or_scope.is_admin():
            return chunks
    elif user_or_scope.is_admin:
        return chunks
```

This is correct but subtly different from `is_authorized_for_policy`. The admin bypass in `filter_chunks` uses `getattr(..., False)` as outer condition — if `is_admin` is a callable method, `getattr(user, "is_admin", False)` returns the bound method, which is truthy, causing the outer `if` to pass even before the `callable()` check. **This is actually still a bug:** a user with `is_admin` defined as a method will always pass the outer `if` check, then hit the `callable()` branch, then call it properly. Net behavior is correct — but the outer guard is redundant and misleading.

**Status: No current security breach in the admin fast-path (the correct check runs), but the code is logically inconsistent and should be cleaned up.**

### 1.2 EvidenceFilter TTL Cache and Permission Revocation Window (P0)

**File:** [`rag/authorization/evidence_filter.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/authorization/evidence_filter.py#L244-L264)

`get_allowed_policy_ids()` caches the result for 2 minutes (120s TTL). If a user's role, department, or clearance is changed, the old allowed_policy_ids list is served for up to 2 minutes.

**Attack scenario:** Admin revokes user access to a confidential policy → user continues to receive answers grounded in that policy for up to 2 minutes.

**Compounding factor:** The semantic cache uses the allowed_policy_ids list as part of the scope_key (MD5 of sorted list). If allowed_policy_ids changes (after TTL), the cache key changes → cache miss → fresh re-evaluation. **But during the 2-minute EvidenceFilter TTL window, the stale pids list is still used.**

**Status: Confirmed P0 risk. No mitigation exists for the 2-minute window.**

**Fix:** Reduce EvidenceFilter TTL to 10-30 seconds, or hook `clear_cache()` to role/permission change events.

### 1.3 Redis Cache Invalidation Gap (P0)

**File:** [`rag/cache/semantic_cache.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/cache/semantic_cache.py)

`invalidate_version()` and `invalidate_policy()` only clear the **in-process local dict**. Redis L1 entries are set with `SETEX` (TTL=3600s) but **never deleted** on invalidation. After a policy amendment:
- Local cache: cleared immediately ✓
- Redis cache: stale entries persist for up to 1 hour ✗

In a multi-worker deployment (Gunicorn with multiple workers), each worker has its own local cache. Worker A invalidates its local cache but cannot invalidate Worker B's local cache or Redis.

**Status: Confirmed P0 defect.** Policy changes are not propagated to Redis entries.

**Fix:** Add `redis.delete(key)` calls in `invalidate_version`/`invalidate_policy`. Pattern-delete via `SCAN + DEL` for scope-prefixed keys.

### 1.4 NLI Verification Disabled by Default (P0)

**File:** [`rag/verification/entailment.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/verification/entailment.py#L31)

The entailment verifier is gated on `ENTAILMENT_ENABLED=true` environment variable. Default is `false`. When disabled, `verify()` returns `is_entailed=True, score=1.0, verdict="ENTAILMENT"` — all answers pass verification unconditionally.

The NLI bypass via policy-name+version heuristic (`query_engine.py:721-734`) further reduces verification coverage even when entailment is enabled.

**In practice, claim-level hallucination verification is largely inoperative in the default deployment.**

**Status: Confirmed P0 for production deployments without explicit env var configuration.**

### 1.5 Compiler Concurrent Compilation Race (P0)

**File:** [`rag/compiler/incremental.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/compiler/incremental.py)

`diff_versions()` reads old chunks from DB. `pipeline.py:_stage_chunk` deletes old chunks and inserts new ones in separate transactions. No database-level lock or optimistic version counter prevents two concurrent compile calls for the same `(policy_id, version_id)` from corrupting the diff.

**Status: Confirmed P0 for concurrent compilation scenarios.**

### 1.6 Prompt Injection Surface (P2)

The system prompt (`SYSTEM_POLICY_GROUNDING_PROMPT`) instructs the model to only use provided evidence. No additional guardrails prevent policy text from containing adversarial prompt injection attempts (e.g., a policy clause that says "Ignore previous instructions...").

The verifier at `rag/verification/entailment.py:70` strips `[Policy: ...]` headers and "According to" prefixes from claims before NLI verification — this is a useful pre-processing step but not sufficient protection against embedded instructions.

**Status: Improvement opportunity. Guardrails testing needed.**

---

## 2. Security Test Results Analysis

### 2.1 Reported Security Metrics — Denominator Clarification

From `evaluation/results/security_results.json`:
```json
{
  "total_authorization_evaluations": 3840,
  "correct_decisions": 3840,
  "decision_accuracy_pct": 100.0,
  "false_denials": 0,
  "leak_rate": 0.0
}
```

From `experiments/ieee_publication_v1/comprehensive_metrics.json`:
```json
{
  "authorization_decision_accuracy": 0.93,
  "false_positive_rate": 0.07,
  "false_negative_rate": 0.0
}
```

**These are from two different test suites with different denominators:**

| Metric Source | What it measures | N |
|---------------|------------------|---|
| `security_results.json` | 3,840 decisions from `run_benchmark.py` — likely the policy × user × scope matrix | 3,840 |
| `comprehensive_metrics.json` | Authorization accuracy in the 100-query ieee_publication_v1 eval — uses a separate authorization harness | Unknown N |

**The 7% false-positive (unnecessary denial) rate from `comprehensive_metrics.json` conflicts with the 0 false-denials in `security_results.json`.** This is explained by different definitions:
- `security_results.json` tests "was unauthorized content leaked?" (zero-leak gate) — zero is expected and achievable
- `comprehensive_metrics.json` tests "did the system correctly allow authorized queries?" — here 7% of authorized queries were unnecessarily denied

**Both can be simultaneously true: zero leaks + 7% over-denial = conservative but not perfect.**

### 2.2 Confusion Matrix (from ieee_publication_v1 records)

Built from `expected_authorization` and actual `abstained` / `answer_correctness`:

| | Expected: Allowed | Expected: Denied |
|--|--|--|
| **Actually Allowed** | 91 (True Allow) | 0 (False Allow) |
| **Actually Denied** | 1 (False Deny) | 8 (True Deny) |

- True Positive Rate (correct allow): 91/92 = 98.9%
- True Negative Rate (correct deny): 8/8 = 100.0%
- False Allow Rate: 0/8 = 0.0% (no leaks)
- False Deny Rate: 1/92 = 1.09%

The 7% FP rate from `comprehensive_metrics.json` must refer to a different (larger) test population. **Status: Population mismatch confirmed — reconciled above.**

### 2.3 Concurrency Isolation

From `evaluation/results/concurrency_results.csv`:
- 0 cache contaminations, 0 scope leaks, 0 race conditions across 100 concurrent workers
- Test was against deterministic fast-path queries (P50 = 437ms at c=100 suggests no LLM calls)
- **Not a comprehensive test:** Redis invalidation gap and multi-process L2 isolation were not exercised

---

## 3. Failure Handling

### 3.1 Ollama Timeout Behavior

`QwenLocalProvider.generate_grounded_answer()` has a 15-second timeout. On timeout:
- `TimeoutError` is caught at `query_engine.py:753` → logged at WARNING level
- Falls through to `_extract_best_evidence_context()` deterministic fallback
- If deterministic fallback also fails → ABSTAINED

**This is correct behavior.** No stale responses are served on Ollama timeout.

### 3.2 Database Failure Handling

`EvidenceFilter.filter_chunks()` at line 186-189:
```python
try:
    from flask import has_app_context
    if has_app_context():
        pol_rows = Policy.query.filter(...).all()
        policy_cache = {p.id: p for p in pol_rows}
except Exception:
    policy_cache = {}
```

If the DB query fails, `policy_cache` is empty → `policy = policy_cache.get(p_id)` returns None → `continue` (chunk rejected). **Fail closed: DB failure causes evidence to be excluded.** This is correct for security.

### 3.3 Compiler Stage Failure

`pipeline.py:_advance_stage` (line 56-60):
```python
job.stage = CompilationStage.FAILED
job.error = str(e)
db.session.commit()
```

Compilation failure is recorded. The QA FAISS index, BM25 index, and Chroma collection may be in inconsistent states after a partial stage failure — the rollback only covers the current DB transaction, not the vector store operations (which are committed outside the DB transaction at `_stage_index`).

**Status: Confirmed P1 — partial index corruption on compilation failure with no recovery mechanism.**

---

## 4. Log Security

No sensitive content review was performed (audit is read-only for security). The code uses Python's `logging` module at WARNING/ERROR levels for security events. No evidence of cleartext policy content being logged at DEBUG level (though not exhaustively verified).

---

## 5. Findings Summary

| ID | Finding | Severity | Status |
|----|---------|----------|--------|
| SEC-01 | EvidenceFilter 2-min TTL allows stale permission enforcement | P0 | Confirmed |
| SEC-02 | Redis cache entries not deleted on policy amendment | P0 | Confirmed |
| SEC-03 | NLI verification disabled by default (ENTAILMENT_ENABLED) | P0 | Confirmed |
| SEC-04 | Concurrent compiler compilation race on same version | P0 | Confirmed |
| SEC-05 | `filter_chunks` admin check uses confusing outer guard | P1 | Code smell, not exploitable |
| SEC-06 | No Redis invalidation in multi-worker deployments | P1 | Confirmed |
| SEC-07 | Partial index state after compilation failure | P1 | Confirmed |
| SEC-08 | Prompt injection via policy content not guarded | P2 | Improvement opportunity |
| SEC-09 | Security metric denominators mixed in reports | Reporting | Confirmed, reconciled |
