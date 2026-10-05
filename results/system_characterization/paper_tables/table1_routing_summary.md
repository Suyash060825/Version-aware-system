| Operational Tier | Primary Subsystem | Complexity Class | Traffic Share (%) | Accuracy (%) | P50 Latency (ms) | P95 Latency (ms) | LLM Call Invocation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 0** | Deterministic Fact Engine | Level 0 | 41.8% (385/922) | 100.0% (385/385) | 0.95 ms | 1.65 ms | 0.0% (Bypassed) |
| **Tier 1** | Canonical QA Index (FAISS) | Level 1 | 6.5% (60/922) | 98.3% (59/60) | 1.85 ms | 3.10 ms | 0.0% (Bypassed) |
| **Tier 2** | Adaptive Hybrid RAG + Rerank | Level 2 | 36.6% (337/922) | 94.7% (319/337) | 22.4 ms | 32.8 ms | 100.0% (Selective) |
| **Tier 3** | Deterministic Diff Engine | Level 3 | 6.5% (60/922) | 96.7% (58/60) | 2.10 ms | 4.20 ms | 0.0% (Bypassed) |
| **Tier 4** | Safe Abstention / Refusal | OOD / Unauth | 8.7% (80/922) | 100.0% (80/80) | 3.20 ms | 4.80 ms | 0.0% (Gated) |
| **Overall** | **Integrated Veritas System** | **All Levels** | **100.0% (922/922)** | **97.6% (900/922)** | **4.50 ms** | **29.8 ms** | **36.6% (63.4% Saved)** |
