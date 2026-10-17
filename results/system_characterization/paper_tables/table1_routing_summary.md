| Operational Tier | Primary Subsystem | Complexity Class | Traffic Share (%) | Accuracy (%) | P50 Latency (ms) | P95 Latency (ms) | LLM Call Invocation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Tier 0a | Semantic Cache (L1/L2) | Level 0 | 12.9% (111/862) | 100.0% | 5.50 | 8.96 | 0.0% (Bypassed) |
| Tier 0b | Deterministic Fact Engine | Level 0 | 60.4% (521/862) | 82.0% | 10.21 | 14.69 | 0.0% (Bypassed) |
| Tier 1 | Canonical QA Index (FAISS) | Level 1 | 6.8% (59/862) | 100.0% | 10.50 | 13.31 | 0.0% (Bypassed) |
| Tier 2 | Adaptive Hybrid RAG + Rerank | Level 2 | 16.2% (140/862) | 59.3% | 41.20 | 61.48 | 100.0% (Selective) |
| Tier 3 | Safe Abstention / Refusal | OOD / Unauth | 3.6% (31/862) | 35.5% | 33.52 | 49.19 | 0.0% (Gated) |
| Overall | Integrated Veritas System | All Levels | 100.0% (862/862) | 80.2% | 10.45 | 45.86 | 16.2% (83.8% Saved) |
