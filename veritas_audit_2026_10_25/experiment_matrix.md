# Veritas Controlled Experiment Matrix

**Audit Date:** 2026-10-25 | **Branch:** `improv` / `0ebae05`

---

## 1. Experiment Sequence & Isolation Protocol

To isolate the individual contribution of each repair without confounding, execute the following ablation ladder. Each run must fix the random seed (`seed=42`), dataset split (120 policies / 422 versions / 2,110 chunks / 100 queries), and record query-level traces in an isolated directory.

| Run ID | Configuration | Targeted Root Cause | Primary Success Criterion |
|---|---|---|---|
| **EXP-A (Baseline)** | Current frozen code (`improv` branch) | Replicate baseline metrics | Authorized Accuracy = 94.57%, Tail = 27s |
| **EXP-B (Security & Cache Fix)** | EXP-A + EvidenceFilter TTL (15s) + Redis cache invalidation (`DEL` on amendment) | Stale auth window & orphan Redis entries | Zero stale hits on policy revocation; 100% cache invalidation |
| **EXP-C (Chunking & Structure)** | EXP-B + Clause-aware boundary snapping (protect numbers/decimals) + Table block preservation | Severed numbers, broken clauses, 0% CAT_11 | CAT_11 accuracy > 50%; Numerical Grounding = 100% |
| **EXP-D (Retrieval & Ranking)** | EXP-C + FlashRank candidate depth increased from 15 to 35 + Symmetric metadata prefixes | Candidate loss in top 15; BM25/Dense prefix asymmetry | Tier-2 Chunk Recall@5 > 98.0%; MRR gain > 15% |
| **EXP-E (Truthfulness & NLI)** | EXP-D + Remove `BYPASS_GROUNDED` regex hole + Enable NLI by default + Retain "According to" claims | Hallucination leakage; bypassed verification | Contradiction rejection rate = 100%; Hallucination < 1.0% |
| **EXP-F (Temporal Resolution)** | EXP-E + Fix pre-dating fallback (abstain with notice when date < v1.0 effective date) | Silent earliest version fallback on historical dates | Temporal CAT_E accuracy = 100%; Pre-dating abstention = 100% |
| **EXP-G (Full Optimization)** | All validated fixes combined (B through F) | End-to-end production verification | Authorized Accuracy > 95.0%; ECE < 0.08; Tail P99 < 5s (extractive) |
