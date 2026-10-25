# Veritas Cache Consistency & Invalidation Audit

**Audit Date:** 2026-10-25 | **Branch:** `improv` / `0ebae05`

---

## 1. Multi-Tier Cache Architecture

**File:** [`rag/cache/semantic_cache.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/cache/semantic_cache.py)

- **L1 Cache:** Exact normalized query hash + scope key. Checked in sub-millisecond time.
- **L2 Cache:** Cosine vector similarity scan over stored query embeddings (`threshold >= 0.95`).
- **Scope Key Composition (`_make_scope_key`, L186–202):**
  - Includes: `tenant_id`, `role`, `department_ids`, `allowed_confidentiality`, `historical`, `target_date`, `requested_version`, `allowed_policy_ids` (MD5 hash), and `is_diff_query`.
  - **Verdict:** Highly robust against cross-role and cross-tenant data leaks. Two users with different clearances produce different scope keys and cannot hit each other's cache entries.

---

## 2. Invalidation Defects & Stale Data Vulnerabilities

### 2.1 The Redis Orphan Entry Defect (CONFIRMED P0 DEFECT)
- **Code:** `semantic_cache.py:54-61` and `L282-295`
- When `Config.REDIS_URL` is configured, L1 writes to Redis using `SETEX` (TTL = 3600 seconds).
- When a policy is updated or amended, `pipeline.py:_stage_index` calls `cache.invalidate_version(policy_id, version_id)`.
- **Finding:** `invalidate_version()` scans and pops entries from `self._local_l1` (in-memory dict). **It never sends an invalidation or `DEL` command to Redis.**
- **Consequence:** After an amendment, workers querying Redis will continue receiving the stale, pre-amendment cached answer for up to **1 hour**, completely bypassing all document updates and version deprecations.

### 2.2 Multi-Worker In-Memory Drift (P1)
- `MultiLevelCache` maintains in-process local dictionaries (`_local_l1`, `_local_l2`).
- In multi-worker Gunicorn deployments without Redis (or for L2, which is never written to Redis), an invalidation executed on Worker 1 clears Worker 1's memory only. Workers 2, 3, and 4 continue to serve outdated answers until their local process TTLs expire or memory evicts.

### 2.3 Non-Thread-Safe Singleton (P1)
`get_cache()` in lines 309–313:
```python
_CACHE = None
def get_cache() -> MultiLevelCache:
    global _CACHE
    if _CACHE is None:
        _CACHE = MultiLevelCache()
    return _CACHE
```
Lacks a double-checked mutex lock. Under high concurrent startup traffic, multiple threads instantiate duplicate cache instances simultaneously.
