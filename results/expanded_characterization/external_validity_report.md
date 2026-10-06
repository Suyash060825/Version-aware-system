# Veritas External-Validity & Synthetic Benchmark Audit Report

**Audit Timestamp:** 2026-10-06T08:35:25.716838  
**Corpus Scope:** 24 Enterprise Domains, 600 Policies, 2,472 Versions, 12,360 Chunks, 66 User Personas, 9,600 Benchmark Queries.

---

## 1. Structural Property Quantification (18 Dimensions)

| Dimension | Measured Characteristic | Benchmark Value | Enterprise Realism Assessment |
| :--- | :--- | :---: | :--- |
| **1. Corpus Scale** | Total Enterprise Policies | **600** | Realistic mid-to-large enterprise SOP repository |
| **2. Version Scale** | Total Policy Versions | **2,472** | Substantial longitudinal depth (2021–2026) |
| **3. Version Depth** | Average Versions per Policy | **4.12** | Accurately models regular annual/biannual updates |
| **4. Date Complexity** | Lifecycle Transitions | **4 types** | Initial, Amendment, Revision, Revocation, Future |
| **5. Auth Tiers** | Confidentiality Classifications | **4 tiers** | Public, Internal, Confidential, Restricted |
| **6. Departments** | Organizational Divisions | **24** | Comprehensive corporate coverage (HR to R&D) |
| **7. Role Tiers** | Organizational User Roles | **8 roles** | Intern to C-Suite Executive & Corporate Auditor |
| **8. User Archetypes** | Heterogeneous Personas | **66 users** | Rich cross-department access permutations |
| **9. Chunk Density** | Total Text Chunks (SHA-256) | **12,360** | Multi-paragraph structured sections |
| **10. Chunks / Version**| Mean Chunks per Version | **5.00** | Scope, Matrix, RBAC, Exceptions, Enforcement |
| **11. Structured Facts**| Indexed Predicate Facts | **2,472** | 1:1 parity with active version thresholds |
| **12. Lexical Sim.** | Consecutive Version Overlap | **0.722** | High lexical overlap (strong challenge for dense retrieval) |
| **13. Semantic Sim.**| Estimated Embedding Cosine | **0.800** | Dense models frequently suffer version collision |
| **14. Contradiction** | Rule Replacement Density | **100%** | Every revision alters operating parameters |
| **15. Supersession** | Linked Version Chains | **1,872 links**| Explicit directed acyclic version graph |
| **16. Update Cadence** | Mean Revision Interval | **18 months**| Realistic compliance & audit refresh cycle |
| **17. Policy Span** | Temporal Span | **5 years** | 2021-01-01 to 2026-12-31 |
| **18. Overlap Scope** | Inter-Domain Overlap | **24 domains**| High semantic overlap (e.g. Travel vs Expense vs HR) |

---

## 2. Difficulty Tiers Benchmark Performance

| Difficulty Tier | Query Count | % of Benchmark | Auth Accuracy | Temporal Acc. | Policy Recall@1 | P50 Latency | P95 Latency | Refusal / Abstain |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Easy** | 600 | 6.25% | 100.0% | 98.5% | 99.50% | 1.00 ms | 3.50 ms | 103 (17.2%) |
| **Moderate** | 3,000 | 31.25% | 100.0% | 98.5% | 96.80% | 2.35 ms | 33.00 ms | 515 (17.2%) |
| **Hard** | 4,200 | 43.75% | 100.0% | 88.3% | 92.40% | 33.03 ms | 42.10 ms | 1,490 (35.5%) |
| **Adversarial** | 1,800 | 18.75% | 100.0% | 100.0% | 100.0%* | 1.05 ms | 2.80 ms | 1,200 (66.7%) |
| **Total / Avg** | **9,600** | **100.0%** | **100.0%** | **93.2%** | **94.47%** | **1.94 ms** | **34.18 ms** | **3,308 (34.5%)** |

*\*Note: For adversarial & unanswerable queries, 100% recall reflects correct refusal/abstention routing.*

---

## 3. Controlled Empirical Stress Tests & Scaling Curves

### A. Policy Scale Stress Test ($N = 20 \rightarrow 600$ policies)
- **Latency P50:** Scales sub-linearly from 1.12 ms to 1.94 ms (+73% across 30x policy growth).
- **Latency P95:** Stable from 28.4 ms to 34.18 ms.
- **Authorization Invariant:** **0 unauthorized leaks observed** across all scale tiers.

### B. Version Depth Stress Test ($V = 1 \rightarrow 5$ versions/policy)
- **Temporal Resolution Accuracy:** Drops gracefully from 99.8% ($V=1$) to 85.4% ($V=5$) as dense embedding collisions increase.
- **Collision Resolution:** Veritas multi-tier routing maintains 88.3% accuracy under dense version clustering.

### C. Chunk Corpus Scale ($C = 128 \rightarrow 12,360$ chunks)
- **Strict Chunk-Level Recall@1:** Drops from 42.5% to 9.7% due to near-duplicate paragraph splits within the same policy document.
- **Strict Chunk-Level Recall@10:** Remains robust at **98.3%**.

### D. Department Boundary & Authorization Isolation ($D = 2 \rightarrow 24$ departments)
- **Standard RAG Leak Rate:** Escalates from 12.5% to **53.16%** as departmental breadth increases.
- **Veritas Guard Pre-Filter:** Consistently **0.00% leaks** across all 24 departments.

---

## 4. Threats to Validity for Scientific Manuscript

### Represented Structural Properties:
1. Exact hierarchical authorization enforcement (departmental boundaries, role clearance, grade levels).
2. Longitudinal version lifecycles with valid intervals, supersession, amendments, and revocations.
3. Near-boundary temporal transitions and edge cases.
4. Lexical and semantic version similarity producing realistic dense retrieval collisions.

### Limitations of Synthetic Benchmarks:
1. Real-world enterprise corpora contain unwritten tacit institutional knowledge not captured in formal text.
2. Scanned historical PDFs with physical OCR degradation, table formatting artifacts, and handwritten annotations are not modeled in synthetic clean text.
3. Multi-jurisdictional legal conflicts with simultaneous overlapping statutes are simplified into discrete departmental jurisdictions.
