# VERITAS TEMPORAL AND AUTHORIZATION CORRECTNESS TEST REPORT

**Auditor:** Senior Security & Software Test Auditor  
**Date:** October 14, 2026  
**Test Harness Files:** `tests/test_audit_adversarial.py`, `tests/test_hardening_regression.py`, `tests/system_characterization/suites/test_authorization_isolation.py`, `tests/system_characterization/suites/test_temporal_semantics.py`

---

## 1. Executive Summary

This report provides the exhaustive adversarial verification of the **composite eligibility predicate**:
$$E(c, u, t_q) = V(c, t_q) \cdot A(c, u)$$
where $V(c, t_q)$ enforces closed date-bounded temporal interval validity and $A(c, u)$ enforces role-based, department-isolated authorization before candidate evidence enters reranking, generation prompts, semantic caches, or audit trails.

---

## 2. Temporal Correctness Evaluation

### A. Test Matrix & Results

| Test Scenario | Evaluated Condition | Expected Behavior | Actual Measured Behavior | Status |
|:---|:---|:---|:---|:---|
| **T1. Active Policy Query** | Query as of current date (2024-06-01) on Policy 1 | Resolve active Version 2.0 (3 days remote) | `resolver.get_active_version` returned Version 2.0 (`is_active=True`) | **PASS** |
| **T2. Historical Version Query** | Query with explicit 2022 date on Policy 1 | Resolve historical Version 1.0 (1 day remote) | `resolver.get_active_version` returned Version 1.0 (`is_active=False`) | **PASS** |
| **T3. Semantic Supersession** | Compare clause contents across v1.0 and v2.0 | Clauses differ; superseded clause not returned for 2024 | v1.0 contains "1 day", v2.0 contains "3 days"; retrieved cleanly | **PASS** |
| **T4. Pre-Effective Date Query** | Query date (2020-01-01) prior to Policy 1 creation (2022-01-01) | Fail closed / Return `None` (policy did not exist) | **Implementation returns `versions[-1]` (earliest version v1.0)** | **QUALIFIED GAP** |
| **T5. Post-Expiration Query** | Query date (2025-01-01) after Policy 3 expired (2021-12-31) | Fail closed / Return `None` (policy has expired) | **Implementation returns `versions[0]` (latest version)** | **QUALIFIED GAP** |
| **T6. Missing Effective Dates** | PolicyVersion with `effective_date = None` | Fails closed or falls back to `created_at` | Falls back to active flag / `created_at`; does not crash | **PASS** |
| **T7. Overlapping Intervals** | Version validity ranges with overlapping intervals | Primary interval takes precedence | Order by `version_num DESC` ensures most recent version takes precedence | **PASS** |
| **T8. Version Diff Engine** | Comparison between v1.0 and v2.0 clauses | Correctly identify added, removed, and modified clauses | `PolicyDiffEngine` correctly detected added equipment and internet clauses | **PASS** |

### B. In-Depth Temporal Architectural Analysis
In `rag/versions/resolver.py` lines 236–239:
```python
if target_date:
    for v in versions:
        if v.is_valid_for_date(target_date):
            return v
    # If target date is before all versions, return the earliest version
    if target_date < versions[-1].effective_from:
        return versions[-1]
    return versions[0]
```
* **Critical Finding:** When a user queries a date **before a policy ever existed** (e.g., asking about Remote Work Policy in 1995 when the first policy was drafted in 2022), Veritas returns the 2022 version rather than returning `None` or explicitly abstaining with *"Policy was not in effect on the requested date"*.
* **Similarly for Expired Policies:** If a query date post-dates the expiration date, the resolver returns the latest version rather than returning `None`.
* **Recommendation:** The resolver should return `None` when a query date falls outside all valid $[\tau_s, \tau_e]$ intervals, allowing the query engine to trigger a safe temporal abstention.

---

## 3. Authorization Correctness Evaluation

### A. Test Matrix & Results

| Test Scenario | Evaluated Condition | Expected Behavior | Actual Measured Behavior | Status |
|:---|:---|:---|:---|:---|
| **A1. Authorized Access** | Admin requesting Restricted Security Plan | Granted access | EvidenceFilter returns `True`; chunks admitted | **PASS** |
| **A2. Unauthorized Access** | Standard Employee requesting Restricted Security Plan | Strictly blocked | EvidenceFilter returns `False`; chunks blocked before reranker | **PASS** |
| **A3. Two Roles Identical Query** | Admin vs. Employee asking for keyvault master token | Admin receives token; Employee receives refusal | Admin receives answer; Employee triggers safe abstention | **PASS** |
| **A4. Cache Scope Isolation** | Authorized user caches privileged answer; unauthorized user repeats query | Cache hit strictly denied to unauthorized user | `cache.get(emb, scope=scope_eng)` returned `None` | **PASS** |
| **A5. Temporal Cache Isolation** | Same user asks for 2022 rule, then 2024 rule | Separate cache keys; no temporal pollution | `cache.get(emb, scope=scope_2024)` returned `None` | **PASS** |
| **A6. Pre-Reranking Gate** | Unauthorized chunk passed into candidate list | Filtered out BEFORE cross-encoder reranking | `filter_chunks` stripped unauthorized chunks before `reranker.rank()` | **PASS** |
| **A7. 3,840 Matrix Evaluation** | 32 user archetypes $\times$ 120 policies (`security_results.csv`) | 0 leaks across 3,840 evaluations | **18 security leaks observed (36 leaked chunks)** | **FAIL** |

---

## 4. Detailed Root-Cause Analysis of the 18 Security Violations

In `results/system_characterization/security_results.csv`, 18 out of 3,840 evaluations produced `security_violation == True`.

### Violation Pattern 1: HR Role Admin Aliasing (10 Violations)
* **User:** `U-HR-02` (Role: `hr`, Department: `Human Resources`, Clearance: `internal`)
* **Target Policies:** Policies 21, 22, 23, 24, 25, 26, 27, 29, 30, 68 (Department: `IT & Cybersecurity`, Confidentiality: `confidential`)
* **Mechanism:**
  In `rag/engine/query_scope.py`:
  ```python
  elif getattr(user, "role", "") in ("admin", "hr"):
      is_adm = True
  ```
  Because `role == "hr"` caused `is_adm = True`, the `EvidenceFilter` executed:
  ```python
  if scope.is_admin:
      return True
  ```
  This bypassed all department isolation checks and allowed HR personnel to view IT security infrastructure passwords and keys.

### Violation Pattern 2: External Contractor Clearance Defaulting (8 Violations)
* **User:** `U-EXT-01` (Role: `contractor`, Department: `Procurement`, Clearance: `public_only`)
* **Target Policies:** Policies 61, 62, 63, 64, 65, 67, 69, 70 (Department: `Procurement`, Confidentiality: `internal`)
* **Mechanism:**
  When `QueryScope.from_user` initialized without an explicit `allowed_confidentiality` tuple, line 85 defaulted to:
  ```python
  confidentiality = ["public", "internal"]
  ```
  This granted `internal` clearance to the contractor, leaking internal procurement thresholds and vendor discount terms.

### False Rejections (144 Cases)
* **User:** `U-LEG-03` (Role: `employee`, Department: `Legal`, Clearance: `confidential`)
* **Mechanism:**
  In `evidence_filter.py` line 46:
  ```python
  if conf_str != "public" and policy.department_id is not None and scope.role not in ("admin", "executive", "legal", "hr"):
      if scope.department_ids and policy.department_id not in scope.department_ids:
          return False
  ```
  Because `U-LEG-03` had role string `"employee"` (despite department being Legal), the filter blocked access to cross-department public/internal policies.

---

## 5. Security Information Flow Verification

1. **Pre-Retrieval Stage:** Verified. `EvidenceFilter.get_allowed_policy_ids(user)` restricts the SQL/vector query boundary.
2. **Reranker Stage:** Verified. `EvidenceFilter.filter_chunks()` executes prior to FlashRank cross-encoder inference.
3. **Prompt Assembly Stage:** Verified. Only chunks surviving the pre-reranking gate are passed to LLM context.
4. **Cache Storage:** Verified. `MultiLevelCache` scope keys encode `tenant_id`, `role`, `department_ids`, `allowed_confidentiality`, `target_date`, and `requested_version`. No cross-tenant or cross-role cache contamination occurs.
5. **Audit Trail Visibility:** Verified. Audit logs record policy IDs and version labels without exposing raw unauthorized text.

---

## 6. Summary of Empirical Security Findings

* **Tested Evaluations:** 3,840
* **Correct Access Determinations:** 3,678 ($95.78\%$)
* **Security Violations (Unauthorized Leaks):** **18 ($0.469\%$)**
* **False Rejections (Authorized Blocked):** **144 ($3.75\%$)**
* **Empirical 95% Confidence Upper Bound on Leakage:** **$0.74\%$** (Contradicts manuscript claim of $<0.08\%$)
