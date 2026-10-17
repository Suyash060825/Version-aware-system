| Architecture Variant | Accuracy (%) | Mean Latency (ms) | P95 Latency (ms) | Hallucination Rate (%) | Security Violations | LLM Invocation Multiplier |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Full Veritas System (Baseline) | 100.0% | 7.3 | 8.2 | 100.0% | 0 (0.0%) | 0.00x |
| w/o Fact Resolver (Tier 0 Disabled) | 100.0% | 7.8 | 10.9 | 100.0% | 0 (0.0%) | 0.00x |
| w/o Precompiled QA (Tier 1 Disabled) | 100.0% | 7.7 | 8.5 | 100.0% | 0 (0.0%) | 0.00x |
| w/o Temporal Pre-filtering | 100.0% | 8.2 | 10.3 | 100.0% | 0 (0.0%) | 0.00x |
| w/o CrossEncoder Reranker | 100.0% | 7.6 | 8.3 | 100.0% | 0 (0.0%) | 0.00x |
| w/o Confidence Gating | 100.0% | 8.4 | 9.5 | 100.0% | 0 (0.0%) | 0.00x |
| w/o Multi-Level Cache | 100.0% | 7.3 | 8.4 | 100.0% | 0 (0.0%) | 0.00x |
