# Final Veritas Benchmark Report (Authoritative 301 Evaluation)

### 1. Executive Summary
- **Total Benchmark Queries:** 301
- **Versioned Policy Queries:** 288
- **Unanswerable / Adversarial Queries:** 13
- **Overall Version Correctness:** 96/301 (31.89%)
- **Versioned-Only Accuracy:** 96/288 (33.33%)
- **Conditional Accuracy (on Answered Queries):** 96/109 (88.07%)

### 2. Authorization & Abstention Breakdown
- **Authorized Queries:** 141
- **Denied Queries (AUTH_BLOCK):** 160
- **Confidence Gate Abstentions:** 32
- **Total Abstentions:** 192
- **Total Answered Queries:** 109

### 3. LLM Runtime Behavior
- **Actual LLM Invocations:** 0
- **LLM Timeouts:** 0 (corrected from erroneous 301 report)
- **Deterministic Fast-Path / Compiled Assembly:** 109
- **Deterministic Abstentions:** 192

### 4. Latency Distribution
- **P50 Latency:** 177.84 ms
- **P95 Latency:** 239.65 ms
- **P99 Latency:** 2647.40 ms

### 5. Category Breakdown
| Category | Total | Versioned | Version Correct | Authorized | Denied | Abstained | Answered |
|---|---|---|---|---|---|---|---|
| compiled_qa | 225 | 225 | 85 | 97 | 128 | 132 | 93 |
| fact | 44 | 44 | 9 | 14 | 30 | 32 | 12 |
| semantic_retrieval | 8 | 8 | 0 | 7 | 1 | 8 | 0 |
| adversarial | 5 | 0 | 0 | 5 | 0 | 5 | 0 |
| unanswerable | 8 | 0 | 0 | 8 | 0 | 8 | 0 |
| temporal_historical | 4 | 4 | 1 | 3 | 1 | 3 | 1 |
| version_comparison | 2 | 2 | 0 | 2 | 0 | 0 | 2 |
| department_auth | 3 | 3 | 1 | 3 | 0 | 2 | 1 |
| confidentiality | 2 | 2 | 0 | 2 | 0 | 2 | 0 |
