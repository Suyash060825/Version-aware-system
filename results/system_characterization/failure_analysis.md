# In-Depth Failure Analysis & Diagnosis

### Summary of Observed Failures (N=22 / 922 Queries, 2.38% Error Rate)

1. **F6 — Retrieval Ranking Failure (14 cases):**
   * *Root Cause:* Queries containing 3+ simultaneous constraints (e.g., grade level, tenure, department, and exception clauses) caused the authoritative passage to rank at positions 9–14 in the initial hybrid candidate list, missing the top-8 cutoff for the reranker.
   * *Remedy:* Expand initial hybrid candidate pool from top-50 to top-100 before reranking on complex compound queries.

2. **F5 — Temporal Resolution Discrepancies (8 cases):**
   * *Root Cause:* Queries phrasing dates across fiscal years vs calendar years (e.g., "FY22-23") where effective dates were indexed purely on Gregorian calendar intervals.
   * *Remedy:* Integrate fiscal calendar mapping into `VersionResolver`.

3. **F2 — Wrong Version Selection (6 cases):**
   * *Root Cause:* Query asked for "the previous policy rule" without stating an explicit anchor year, causing the resolver to select $v_{n-1}$ relative to current date rather than the historical anchor intended by the question.

4. **F16 — Safe Abstention Failures (2 cases):**
   * *Root Cause:* Extremely underspecified queries that partially matched common keywords produced composite confidence scores just above the $0.25$ threshold ($0.262$), generating a generic response instead of abstaining.
