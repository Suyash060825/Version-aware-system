| Architecture Variant | Accuracy (%) | Mean Latency (ms) | P95 Latency (ms) | Hallucination Rate (%) | Security Violations | LLM Invocation Multiplier |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Full Veritas (Baseline)** | **94.8%** | **14.2 ms** | **32.5 ms** | **0.5%** | **0 (0.0%)** | **1.00x (Baseline)** |
| w/o Fact Resolver (Tier 0) | 91.2% (-3.6%) | 26.4 ms (+85.9%) | 48.0 ms (+47.7%) | 0.9% (+0.4%) | 0 (0.0%) | 1.45x (+45%) |
| w/o Canonical QA Index (Tier 1) | 92.0% (-2.8%) | 24.1 ms (+69.7%) | 45.2 ms (+39.1%) | 0.8% (+0.3%) | 0 (0.0%) | 1.35x (+35%) |
| w/o BM25 (Dense Only) | 86.4% (-8.4%) | 13.8 ms (-2.8%) | 31.0 ms (-4.6%) | 1.2% (+0.7%) | 0 (0.0%) | 1.08x (+8%) |
| w/o Dense Retriever (BM25 Only) | 82.1% (-12.7%) | 11.5 ms (-19.0%) | 28.0 ms (-13.8%) | 1.8% (+1.3%) | 0 (0.0%) | 1.15x (+15%) |
| w/o CrossEncoder Reranker | 88.5% (-6.3%) | 8.2 ms (-42.3%) | 18.0 ms (-44.6%) | 1.4% (+0.9%) | 0 (0.0%) | 1.00x |
| w/o DeBERTa NLI Verifier | 90.1% (-4.7%) | 9.5 ms (-33.1%) | 22.0 ms (-32.3%) | 4.1% (+3.6%) | 0 (0.0%) | 1.00x |
| w/o Isotonic Calibration | 92.5% (-2.3%) | 14.1 ms (-0.7%) | 32.5 ms (0.0%) | 0.6% (+0.1%) | 0 (0.0%) | 1.00x |
| w/o Multi-Level Cache | 94.8% (0.0%) | 28.5 ms (+100.7%) | 52.0 ms (+60.0%) | 0.5% (0.0%) | 0 (0.0%) | 1.85x (+85%) |
