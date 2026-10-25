# Veritas Prioritized Fix Plan

**Audit Date:** 2026-10-25 | **Branch:** `improv` / `0ebae05`

---

## Priority 0 (P0): Security, Correctness, and Data-Integrity Defects

### FIX-01: Invalidate Redis Cache on Policy Amendment & Revocation
- **Source:** [`rag/cache/semantic_cache.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/cache/semantic_cache.py#L282-L295)
- **Defect:** `invalidate_version()` and `invalidate_policy()` clear in-process dictionaries but do not issue `DEL` commands to Redis, allowing stale cached answers to leak for up to 1 hour.
- **Action:** Issue Redis key pattern deletion (`l1:*`) matching the target `policy_id` / `version_id`.
- **Validation:** Test that queries hit against Redis return a cache miss immediately following a policy amendment.

### FIX-02: Fix EvidenceFilter TTL Stale Authorization Window
- **Source:** [`rag/authorization/evidence_filter.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/authorization/evidence_filter.py#L12)
- **Defect:** `_allowed_pids_cache` caches allowed policy IDs per user for 120 seconds. Revoking a user's permissions permits unauthorized access for up to 2 minutes.
- **Action:** Reduce TTL to 10 seconds and hook `clear_cache()` directly into user role and permission update handlers.
- **Validation:** Permission revocation test verifying immediate rejection of confidential queries.

### FIX-03: Close the NLI Verification Bypass Hole
- **Source:** [`rag/engine/query_engine.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/engine/query_engine.py#L721-L734)
- **Defect:** Answers containing policy name and version strings automatically set `nli_verdict="BYPASS_GROUNDED"`, completely skipping claim-level NLI contradiction verification.
- **Action:** Remove the regex bypass; ensure all generative answers pass claim-level contradiction checks. Enable NLI by default in production.
- **Validation:** Test with adversarial prompt injecting false rules into a cited policy template; verify answer rejection.

### FIX-04: Lock Concurrent Incremental Compilations
- **Source:** [`rag/compiler/incremental.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/compiler/incremental.py#L19-L46)
- **Defect:** Unprotected database read and delete-insert cycles race during concurrent compilations, producing corrupt diff states.
- **Action:** Introduce an explicit database row lock (`SELECT FOR UPDATE` on `CompilationJob`) or Redis distributed lock on `(policy_id, version_id)`.
- **Validation:** Multi-threaded compilation test on the same version ensuring serialized execution.

---

## Priority 1 (P1): Retrieval, Temporal & Answer Quality Defects

### FIX-05: Fix Temporal Pre-Dating Silent Fallback
- **Source:** [`rag/versions/resolver.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/versions/resolver.py#L237-L239)
- **Defect:** Queries for dates prior to any policy version enactment silently return the earliest version as active.
- **Action:** Check if `target_date < earliest.effective_from`; if so, abstain with an explicit out-of-scope notice.
- **Validation:** Negative temporal tests asserting abstention on pre-dated queries.

### FIX-06: Expand FlashRank Candidate Depth & Eliminate Truncation
- **Source:** [`rag/retrieval/reranker.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/retrieval/reranker.py#L105)
- **Defect:** FlashRank silently drops candidates beyond position 15, discarding relevant evidence retrieved by hybrid search.
- **Action:** Increase reranker candidate depth from 15 to 35 candidates.
- **Validation:** Recall@10 ablation demonstrating increased candidate capture without exceeding latency targets.

### FIX-07: Repair NLI Claim-Splitter Prefix Pruning
- **Source:** [`rag/verification/entailment.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/verification/entailment.py#L68-L72)
- **Defect:** The claim splitter strips sentences starting with "According to", excluding the primary factual answer from NLI verification.
- **Action:** Strip the introductory attribution clause (e.g., regex `^According to [^:]+:\s*`) while retaining the underlying claim text for NLI evaluation.
- **Validation:** Verify that cited answers produce non-empty claim sets for entailment scoring.

---

## Priority 2 (P2): Latency & Concurrency Bottlenecks

### FIX-08: Isolate and Bound Local LLM Inference
- **Source:** [`rag/engine/query_engine.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/engine/query_engine.py#L712-L715)
- **Defect:** Live generation queries take 16–27 seconds on CPU, causing extreme P99 latency spikes.
- **Action:** Enforce strict routing where only multi-clause synthesis queries reach Ollama; cap generation to `max_tokens=200` with streaming response delivery.
- **Validation:** Measure P99 latency reduction under mixed traffic.
