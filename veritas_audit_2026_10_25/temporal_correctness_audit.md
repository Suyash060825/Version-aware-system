# Veritas Temporal Correctness Audit

**Audit Date:** 2026-10-25 | **Branch:** `improv` / `0ebae05`

---

## 1. Temporal Parsing & Resolution Flow

### 1.1 Resolution Architecture
**File:** [`rag/versions/resolver.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/versions/resolver.py)

- **Regex Parsers:**
  - Date ranges: `between 2023 and 2024`, `from June 2023 to July 2024`.
  - Point-in-time: `as of June 2024`, `in 2022`.
  - Boundaries: `before July 2023`, `after January 2024`, `until 2025`, `since 2021`.
  - Version numbers: `version 2.0`, `v1.2`.
  - Version diff: `between v1 and v2`, `v1 vs v2`.

---

## 2. Boundary Semantics & Known Failure Modes

### 2.1 The Pre-Dating Fallback Defect
**Code:** `rag/versions/resolver.py:237-239`
```python
# If target date is before all versions, return the earliest version
earliest = versions[-1]
if earliest.effective_from is not None and target_date < earliest.effective_from:
    return earliest
```
- **Finding (CONFIRMED CORRECTNESS DEFECT):** When a user asks about a policy's rules in 2018, but the policy was first enacted on January 1, 2020 (`v1.0`), the system silently returns `v1.0` as the authoritative answer for 2018.
- **Expected Legal/Compliance Behavior:** The system should abstain or return a factual notice: *"Policy [Title] was not yet in effect on [Target Date]; the earliest effective version is v1.0 enacted on [Date]."*
- This silent fallback directly produced the reported pre-dating resolution failure in the fullstack benchmark.

### 2.2 Date Boundary Calculations
Lines 98–104 calculate the day before a month for `before`:
```python
if month == 1:
    tq.end_date = date(year - 1, 12, 31)
else:
    prev_month = month - 1
    last_day_prev = calendar.monthrange(year, prev_month)[1]
    tq.end_date = date(year, prev_month, last_day_prev)
```
- Correct exclusive end-boundary semantics.
- However, for `as_of` without an explicit day (e.g., "as of June 2024"), L161 sets `target_date = date(year, month, 15)` (the arbitrary 15th of the month). If an amended policy version became active on June 20, 2024, a query for "as of June 2024" resolves to the 15th and retrieves the superseded version.

---

## 3. Version Diff & Comparison Execution

### 3.1 Version Comparison Logic
**File:** [`rag/engine/query_engine.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/engine/query_engine.py#L403-L509)
- Matches version tokens `v1` and `v2`.
- Queries `PolicyVersion` for both version records.
- Executes `PolicyDiffEngine.compute_diff()` on the raw text content.
- Generates a structural summary of added, removed, and modified clauses.
- **Strength:** Bypasses LLM entirely; 100% deterministic, zero hallucination risk on version diffs.
- **Weakness (Small Sample Size in Benchmark):** In `ieee_publication_v1`, version comparison accuracy is reported as 75.0% on **N=4 queries**. A single misparsed query accounts for 25% error.
