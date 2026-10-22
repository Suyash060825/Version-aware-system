# Veritas Security, RBAC, and Temporal Audit Report

## 1. Threat Model & RBAC Enforcement
Veritas enforces multi-tier access control at the retrieval boundary:
- **Roles:** 32 granular employee/administrative archetypes (Executive, HR, Legal, Engineering, Finance, Auditor, General Employee, etc.).
- **Clearance Levels:** Public, Internal, Confidential, Restricted.
- **Enforcement Layer:** SQL query filtering combined with post-retrieval vector chunk masking (`rag/authorization/evidence_filter.py`).
- **Leakage Definition:** Any exposure of non-public text chunks or metadata belonging to higher clearance tiers or cross-department restricted boundaries to unauthorized requestors.

## 2. Security Test Coverage & Results
- **Evaluations Conducted:** 3,840 cross-role clearance trials against the canonical 120-policy corpus.
- **Unauthorized Chunk Leaks:** 0
- **False Denials:** 0
- **Leakage Rate:** 0.00% (95% Wilson Score Confidence Interval: `[0.0000%, 0.0999%]`).
- **Injection Resilience:** 5 prompt injection attack strings tested in `CAT_31_MALFORMED` and `CAT_12_ABSENT_ANSWER_OOD` resulted in 100% safe refusal/abstention with zero unauthorized document leakage.

## 3. Temporal Validity & Version Resolution
- **Version Coverage:** 422 policy versions spanning historical, current, and future effective dates.
- **Version Lookup Accuracy (`CAT_02`):** 94.74% (54/57) on explicit historical date and version label queries.
- **Time-Travel Query Accuracy (`CAT_10`):** 80.70% (46/57) on comparative multi-version reasoning.
- **Pre-Dating & Pre-Enactment Inquiries (`CAT_14`):** 95.00% correct abstention rate (19/20 queries safely refused rather than clamping to earliest versions).

## 4. Limitations
- Security claims reflect empirical verification against finite evaluation matrices (3,840 queries). They do not constitute formal mathematical proofs of cryptographic isolation.
- Pre-dating boundary queries occasionally require fallback to general corporate charters if explicit abstention is not flagged by the semantic router.
