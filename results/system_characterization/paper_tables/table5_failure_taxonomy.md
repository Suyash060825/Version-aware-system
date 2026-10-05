| Failure Code | Category Name | Count | Share (%) | Severity | Affected Subsystem | Primary Root Cause |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **F1** | Wrong Policy Retrieved | 4 | 0.43% (4/922) | Low | Hybrid Retriever | Near-duplicate policy phrasing across adjacent departments. |
| **F2** | Wrong Version Selected | 6 | 0.65% (6/922) | Medium | Temporal Resolver | Ambiguous natural language date expressions (e.g. 'prior year'). |
| **F3** | Wrong Department Scope | 0 | 0.00% (0/922) | High | Evidence Filter | Blocked deterministically by QueryScope department filtering. |
| **F4** | Authorization Failure / Leak | 0 | 0.00% (0/922) | Critical | Evidence Filter | Zero unauthorized candidate chunks entered context (100% Defense). |
| **F5** | Temporal Semantic Failure | 8 | 0.87% (8/922) | Medium | Version Resolver | Multi-year boundary date range parsing discrepancies. |
| **F6** | Retrieval Ranking Failure | 14 | 1.52% (14/922) | Medium | Reranker / RRF | Highly constrained multi-clause queries where passage ranked outside top-8. |
| **F7** | Reranking Inversion | 3 | 0.33% (3/922) | Low | FlashRank ONNX | Short clause with high keyword overlap suppressed over verbose section. |
| **F8** | Generation Hallucination | 2 | 0.22% (2/922) | High | LLM Provider | Extraneous ungrounded claims generated before NLI rejection. |
| **F9** | Citation Attribution Error | 1 | 0.11% (1/922) | Low | Citation Validator | Missing specific section title in newly amended chunk. |
| **F10** | NLI False Contradiction | 2 | 0.22% (2/922) | Low | NLI Verifier | Overly strict threshold on valid paraphrastic clause. |
| **F11** | Calibration Misclassification | 3 | 0.33% (3/922) | Low | Confidence Gate | Edge case boundary score between 0.24 and 0.26. |
| **F12** | Routing Misclassification | 2 | 0.22% (2/922) | Low | Query Router | Underspecified fact query routed to Tier 2 rather than Tier 0. |
| **F13** | Cache Scope Leakage | 0 | 0.00% (0/922) | Critical | Semantic Cache | Multi-tenant and clearance compound keys prevented all cross-scope hits. |
| **F14** | Incremental Compiler Hash Miss | 0 | 0.00% (0/922) | High | Incremental Compiler | SHA256 chunk normalization remained 100% sound. |
| **F15** | Index Overlay Failure | 0 | 0.00% (0/922) | High | FAISS / Delta Store | In-memory delta overlay mirrored SQLite state accurately. |
| **F16** | Safe-Abstention Failure | 2 | 0.22% (2/922) | High | Confidence Gate | Attempted answering on underspecified query instead of abstaining. |
| **F17** | Prompt-Injection Leakage | 0 | 0.00% (0/922) | Critical | Evidence Filter / LLM | Deterministic pre-retrieval authorization blocked all injection overrides. |
| **F18** | Metadata / Schema Inconsistency | 0 | 0.00% (0/922) | Medium | Document IR | Pydantic and dataclass models enforced strict schema types. |
| **F19** | Infrastructure Timeout | 0 | 0.00% (0/922) | High | Local Runtime | All inference calls executed synchronously within CPU budget. |
| **F20** | Unknown / Unclassified | 0 | 0.00% (0/922) | Medium | Diagnostics | All failures mapped successfully to F1-F16 stages. |
