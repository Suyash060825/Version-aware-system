# In-Depth Failure Analysis & Diagnosis

### Summary of Observed Failures (N=171 / 862 Queries, 19.84% Error Rate)

1. **F5 — Temporal Resolution Discrepancies (108 cases):**
   * *Root Cause:* Queries phrasing dates across fiscal years vs calendar years or relative temporal expressions.
   * *Remedy:* Integrate fiscal calendar mapping and relative anchor resolution into `VersionResolver`.

2. **F6 — Retrieval Ranking Discrepancy (40 cases):**
   * *Root Cause:* Highly constrained multi-clause queries where passage ranked outside candidate cutoff.
   * *Remedy:* Expand initial hybrid candidate pool from top-50 to top-100 on complex compound queries.

3. **F4 — Authorization Gating Refusals (20 cases):**
   * *Root Cause:* Queries targeting restricted or cross-department policies where user role lacked clearance; correctly gated.
