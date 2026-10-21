# VERITAS — Comprehensive Dashboard Validation and Truthfulness Audit Report

## 1. Executive Summary

As part of the Veritas exhaustive forensic code review and model pipeline audit (Phase 13 & Phase 14), all user-facing dashboards, analytics pages, cards, charts, and metrics were audited for correctness, consistency, transaction integrity, and truthfulness.

Every metric presented in the interface was traced directly from its frontend view template through backend route controllers to authoritative SQL queries executed against the PostgreSQL database.

---

## 2. Dashboard Inventory and Metrics Register

The complete inventory of all 18 primary dashboard metrics is registered in machine-readable format in [`audit/dashboard_metric_registry.csv`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/audit/dashboard_metric_registry.csv).

### Summary of Audited Dashboards:
1. **Executive BI Dashboard (`GET /admin/bi-dashboard`)**: Company compliance, read rate, growth trends, department compliance, AI telemetry, bottleneck SLA analytics.
2. **Main Admin Dashboard (`GET /admin/`)**: Policy lifecycle distribution (Active, In Review, Draft, Archived), knowledge compiler index status (Chunks V2, Facts, Canonical QA).
3. **AI Analytics Dashboard (`GET /admin/ai-analytics`)**: Chatbot accuracy (thumbs up/down ratio), top queries, knowledge gaps, token volume and estimated cost.
4. **Compliance Center (`GET /admin/compliance`)**: Audit readiness score, framework coverage, unacknowledged violations, AI risk aggregated score.
5. **Contradiction Radar (`GET /admin/contradictions`)**: Continuous drift monitoring, open/resolved contradiction flags.
6. **Governance Health (`GET /admin/governance`)**: Internal portfolio health index (Freshness, Cleanliness, Ownership, AI Risk).
7. **Audit Center (`GET /admin/audit-center`)**: Event frequency, top actions, user activity timelines.
8. **Employee Dashboard (`GET /dashboard`)**: Authorized active policies, unacknowledged mandatory compliance tasks, notifications.

---

## 3. Discovered Defects & Forensic Root Cause Analysis

During our line-by-line inspection and cross-checking against raw PostgreSQL records, 5 critical defects were uncovered:

### Finding DB-01: Compliance Rate Exceeding 100% (154%) in Executive BI Dashboard
- **Root Cause**: `blueprints/bi_dashboard.py` calculated the denominator using active mandatory policies (`Policy.status == ACTIVE, is_mandatory == True`) multiplied by active employees (`User.role == EMPLOYEE, is_active == True`), which evaluated to $6 \times 9 = 54$. However, the numerator queried `PolicyAcknowledgement.query.filter(acknowledged_at.isnot(None), is_mandatory == True).count()` *without* joining `Policy` or `User`. As a result, 24 acknowledgements on pending policies, 6 on HR review policies, and 1 acknowledgement by an Admin user were improperly counted, yielding 83 acks / 54 required = **154% compliance**.
- **Fix**: Replaced the unjoined count with an explicit SQL `JOIN` on `User` (`role == EMPLOYEE, is_active == True`) and filtered `policy_id.in_(active_mand_pids)`. Capped the score with `min(total_acked, total_required)` to mathematically guarantee the rate remains bounded in $[0, 100]\%$.
- **Verified Value**: **96%** (52 active employee acks / 54 required).

### Finding DB-02: Department Compliance Distortion (Operations Showing 600%)
- **Root Cause**: In `blueprints/bi_dashboard.py`, the department compliance logic previously computed:
  `dept_required = dept_employees * dept_mandatory` (where `dept_mandatory` was mandatory policies authored by department $d$), but `dept_acked` counted *all* company employees who acknowledged that department's policies.
  For Operations (1 employee, 1 mandatory policy authored), all 6 company employees acknowledged it, producing $6 / 1 =$ **600% compliance**! Conversely, Human Resources (0 employees with `role == EMPLOYEE`, 4 mandatory policies) had `dept_employees = 0`, producing `dept_required = 0` and rendering as a dash (`None`), despite 35 acknowledgements recorded.
- **Fix**: Redefined department compliance to truthfully reflect the compliance of employees assigned to department $d$ across company-wide active mandatory policies:
  $$\text{Dept Compliance} = \frac{\sum_{u \in \text{Dept Emps}} \text{acks}(u, \text{active\_mand\_policies})}{\text{Dept Emps} \times |\text{active\_mand\_policies}|}$$
- **Verified Values**:
  - Engineering: 100% (18/18)
  - Finance: 100% (9/9)
  - Human Resources: — (0 employees)
  - IT: — (0 employees)
  - Legal: — (0 employees)
  - Marketing: 78% (7/9, 2 pending acks)
  - Operations: 100% (9/9)
  - Sales: 100% (9/9)

### Finding DB-03: Tautological Read Rate (100% of Existing Rows)
- **Root Cause**: `read_rate` was previously computed as `total_reads / total_acks_all` where `total_acks_all = PolicyAcknowledgement.query.count()`. Because every acknowledgement row created during viewing had `read_at` populated, this metric invariably reported 100%, misleading leadership into believing all employees had read all policies.
- **Fix**: Updated the denominator to total potential policy reads across the employee base ($\text{Active Employees} \times \text{Active Policies} = 6 \times 14 = 84$) and numerator to active employee reads of active policies.
- **Verified Value**: **64%** (54 active policy reads / 84 potential reads).

### Finding DB-04: False Clearance of Pending Acknowledgements on View
- **Root Cause**: In `blueprints/employee.py`, `acked_ids` was populated with:
  `acked_ids = [a.policy_id for a in current_user.acknowledgements.all()]`
  If a user viewed a policy, an acknowledgement record was instantiated with `read_at` set while `acknowledged_at` remained `None`. Because the query failed to filter `acknowledged_at.isnot(None)`, the policy was prematurely excluded from `pending_acks` before the employee ever digitally signed it.
- **Fix**: Filtered `current_user.acknowledgements.filter(PolicyAcknowledgement.acknowledged_at.isnot(None)).all()`.
- **Verified Value**: Unacknowledged mandatory policies remain persistently pinned to the employee's pending task queue until signed.

### Finding DB-05: Missing Module-Level `time` Import in `rag/llm_provider.py`
- **Root Cause**: `rag/llm_provider.py` invoked `time.time()` at line 187 in `OllamaProvider.generate()` without `import time` at the module header, throwing `NameError: name 'time' is not defined`. This crashed background AI insight generation in `bi_dashboard()` and forced fallback to static heuristics.
- **Fix**: Added `import time` to module headers in `rag/llm_provider.py`.
- **Verified Value**: Local Ollama generation succeeds natively with live prompt and completion token metering.

---

## 4. Verification and Mathematical Invariants

| Invariant | Target Specification | Observed Post-Repair | Status |
| :--- | :--- | :--- | :--- |
| **Compliance Boundedness** | $0\% \le \text{Rate} \le 100\%$ | $96\%$ | PASS |
| **Department Compliance Boundedness** | $0\% \le \text{Dept Rate} \le 100\%$ | Max 100% (No 600% anomalies) | PASS |
| **Policy Lifecycle Sum** | $\text{Active} + \text{In Review} + \text{Draft} + \text{Archived} = \text{Total}$ | $14 + 6 + 1 + 0 = 21$ | PASS |
| **Vector DB Parity** | Chunks V2 count matches indexed policies | 139 chunks across 21 policies | PASS |
| **AI Feedback Accuracy** | $\text{Upvotes} / (\text{Upvotes} + \text{Downvotes})$ | $3 / (3 + 1) = 75.0\%$ | PASS |
| **RBAC Dashboard Isolation** | Unauthorized roles receive HTTP 403/302 | HTTP 403 on employee / 302 on anon | PASS |
