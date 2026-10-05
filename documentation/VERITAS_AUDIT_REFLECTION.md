# Veritas Enterprise Policy Retrieval – Architectural Reflection & Audit Alignment

This document reflects the findings, architectural invariants, and empirical validations outlined in the **Veritas Enterprise Policy Retrieval Audit Report** against the codebase implementation and benchmark artifacts.

---

## 1. Executive Summary & Core Philosophy

Veritas transitions enterprise policy intelligence away from naive *"vector search + LLM"* architectures to a **governed knowledge supply chain**. It enforces two non-negotiable principles:
1. **Temporal Freshness & Version Soundness**: Strict resolution of policy validity intervals $\mathcal{T}(v) = [t_{\text{effective}}, t_{\text{superseded}})$.
2. **Data Privacy & Authorization by Construction**: Deterministic gating of all knowledge chunks before neural retrieval, reranking, or LLM context construction.

```
                                    [ Inbound User Query & Session Context ]
                                                       │
                                                       ▼
                                     ┌────────────────────────────────────┐
                                     │    QueryScope & Policy Gate        │
                                     │  (Dept, Role, Clearance, QueryDate)│
                                     └─────────────────┬──────────────────┘
                                                       │
                                                       ▼
                                ┌──────────────────────────────────────────────┐
                                │ Composite Pre-Retrieval Eligibility Predicate │
                                │   P_eligible = P_temporal ∧ P_authorization   │
                                └──────────────────────┬───────────────────────┘
                                                       │
                           ┌───────────────────────────┴───────────────────────────┐
                           ▼                                                       ▼
             [ 0% Leakage Guarantee ]                               [ Multi-Tier Routing Engine ]
        Unauthorized / expired chunks pruned                                       │
                                                       ┌───────────────────────────┼───────────────────────────┐
                                                       ▼                           ▼                           ▼
                                              [ Tier 0: Fact Engine ]     [ Tier 1: Canonical QA ]    [ Tier 2: Hybrid RRF ]
                                                Deterministic Lookup        FAISS HNSW Semantic ANN     BM25 + Dense + Rerank
                                                       │                           │                           │
                                                       └───────────────────────────┼───────────────────────────┘
                                                                                   │
                                                                                   ▼
                                                                     [ Grounded Answer & Ledger ]
                                                                     + DeBERTa NLI Verification
                                                                     + Isotonic Confidence Gate
```

---

## 2. Codebase Implementation Mapping

The table below maps the core architectural pillars detailed in the audit to their authoritative implementation files in this repository:

| Audit Pillar | Architectural Requirement | Codebase Implementation | Empirical Validation / Tests |
| :--- | :--- | :--- | :--- |
| **Pre-Retrieval Eligibility Predicate** | Strict deterministic gating $(P_{\text{temporal}} \land P_{\text{authorization}})$ before retrieval/reranking. | [`rag/authorization/evidence_filter.py`](rag/authorization/evidence_filter.py), [`rag/engine/query_scope.py`](rag/engine/query_scope.py) | [`tests/system_characterization/suites/test_authorization_isolation.py`](tests/system_characterization/suites/test_authorization_isolation.py) |
| **Cryptographic Incremental Compiler** | SHA-256 chunk hashing, delta detection, re-embedding only modified segments, tombstone deletions. | [`rag/compiler/incremental.py`](rag/compiler/incremental.py), [`rag/compiler/pipeline.py`](rag/compiler/pipeline.py), [`rag/compiler/document_normalizer.py`](rag/compiler/document_normalizer.py) | [`tests/system_characterization/suites/test_incremental_compiler.py`](tests/system_characterization/suites/test_incremental_compiler.py), [`results/system_characterization/compiler_results.csv`](results/system_characterization/compiler_results.csv) |
| **Multi-Tier Adaptive Routing** | Multi-tier execution: Tier 0 (Facts), Tier 1 (Canonical QA), Tier 2 (Hybrid BM25+Dense RRF), Tier 3 (Diff/LLM). | [`rag/engine/query_engine.py`](rag/engine/query_engine.py), [`rag/facts/fact_engine.py`](rag/facts/fact_engine.py), [`rag/qa/canonical_qa.py`](rag/qa/canonical_qa.py) | [`tests/system_characterization/suites/test_router_dynamics.py`](tests/system_characterization/suites/test_router_dynamics.py), [`results/system_characterization/routing_results.csv`](results/system_characterization/routing_results.csv) |
| **Hybrid Retrieval & Neural Reranking** | Lexical BM25 (Okapi) combined with Dense BGE embeddings via Reciprocal Rank Fusion (RRF) and Cross-Encoder reranking. | [`rag/retrieval/hybrid.py`](rag/retrieval/hybrid.py), [`rag/retrieval/sparse.py`](rag/retrieval/sparse.py), [`rag/retrieval/dense.py`](rag/retrieval/dense.py), [`rag/retrieval/reranker.py`](rag/retrieval/reranker.py) | [`tests/system_characterization/suites/test_retrieval_components.py`](tests/system_characterization/suites/test_retrieval_components.py), [`results/system_characterization/retrieval_results.csv`](results/system_characterization/retrieval_results.csv) |
| **NLI Entailment & Grounding** | Zero-hallucination verification using DeBERTa cross-encoder entailment scoring and interactive citation drawers. | [`rag/verification/entailment.py`](rag/verification/entailment.py), [`rag/verification/citation_validator.py`](rag/verification/citation_validator.py) | [`tests/system_characterization/suites/test_nli_verification.py`](tests/system_characterization/suites/test_nli_verification.py), [`results/system_characterization/nli_results.csv`](results/system_characterization/nli_results.csv) |
| **Confidence Calibration** | Isotonic regression post-hoc calibration over output logits to enable safe abstention. | [`rag/verification/confidence.py`](rag/verification/confidence.py) | [`tests/system_characterization/suites/test_confidence_calibration.py`](tests/system_characterization/suites/test_confidence_calibration.py), [`results/system_characterization/calibration_results.csv`](results/system_characterization/calibration_results.csv) |
| **Concurrency & Cache Isolation** | Thread-safe, multi-tenant cache isolation preventing answer bleed across users, departments, or dates. | [`rag/cache/semantic_cache.py`](rag/cache/semantic_cache.py) | [`tests/system_characterization/suites/test_concurrency_isolation.py`](tests/system_characterization/suites/test_concurrency_isolation.py), [`results/system_characterization/scalability_results.csv`](results/system_characterization/scalability_results.csv) |
| **Post-Mutation Consistency** | Instant cache invalidation, tombstone purging, and immediate version correctness upon corpus updates. | [`rag/compiler/pipeline.py`](rag/compiler/pipeline.py), [`tasks.py`](tasks.py) | [`tests/system_characterization/suites/test_post_mutation_consistency.py`](tests/system_characterization/suites/test_post_mutation_consistency.py) |

---

## 3. Key Empirical Results & System Characterization

The audit validates Veritas against a 14-experiment large-scale characterization testbed (120 synthetic policies, ~600 versions, ~3,000 chunks, 32 user archetypes, 922 queries):

```
┌───────────────────────────────────────────────┬──────────────────────┬──────────────────────────────────────────┐
│ Characterization Dimension                    │ Veritas Metric       │ Baseline / Target Standard               │
├───────────────────────────────────────────────┼──────────────────────┼──────────────────────────────────────────┤
│ Deterministic Traffic Offload (Tiers 0 & 1)  │ 63.4% of queries     │ Naive RAG = 0% (calls LLM for 100%)      │
│ Tier 0 Median Latency                         │ 0.95 ms              │ LLM Generation = 29.6 ms                 │
│ Tier 1 Median Latency                         │ 1.85 ms              │ LLM Generation = 29.6 ms                 │
│ End-to-End P50 System Latency                 │ 4.20 ms              │ LLM-Centric Baseline = 29.6 ms           │
│ Authorization Leakage Rate                    │ 0.00% (0 / 3,840)    │ Enterprise Requirement = 0.00%           │
│ Security Confusion Matrix (TP / TN)           │ 100% / 100%          │ Zero False Negatives / False Positives   │
│ Incremental Compilation Speedup (5% delta)    │ 24.9× speedup        │ >95% re-embedding compute avoided        │
│ Policy-Level Retrieval Recall@1 (RRF Hybrid)  │ >98.0%               │ BM25-only = 84.1%, Dense-only = 89.4%    │
│ DeBERTa Entailment Contradiction Recall       │ 100.0%               │ Zero hallucinated contradictions passed  │
│ Expected Calibration Error (Isotonic ECE)     │ Reduced to 0.041     │ Raw Softmax ECE = 0.295                  │
└───────────────────────────────────────────────┴──────────────────────┴──────────────────────────────────────────┘
```

---

## 4. Architectural Invariants Enforced in Production

1. **Pre-LLM Isolation Rule**:
   $$\text{EvidencePool} = \{ c \in \mathcal{C} \mid \text{ValidAt}(c, t_{\text{query}}) \land \text{CanAccess}(u_{\text{role}}, c_{\text{clearance}}) \land \text{CanAccessDept}(u_{\text{dept}}, c_{\text{dept}}) \}$$
   No candidate chunk outside $\text{EvidencePool}$ is ever submitted to neural embedding rerankers or generative prompt contexts.

2. **Immutable Audit Trail**:
   Every query execution records an immutable trace in the database, containing:
   - Requested scope ($u_{\text{id}}$, $u_{\text{dept}}$, $u_{\text{role}}$, $t_{\text{query}}$)
   - Selected execution tier (Tier 0, 1, 2, or 3)
   - Retrieved chunk IDs and cryptographic SHA-256 signatures
   - DeBERTa NLI entailment scores and confidence calibration values
   - Wall-clock latency breakdowns (retrieval vs. verification vs. generation)
