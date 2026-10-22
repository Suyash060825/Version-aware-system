# Veritas Manuscript Data Brief: Verified Facts & Recommended Text

## 1. Verified Architecture & System Scale
- **Corpus Hierarchy:** 120 policy documents, 422 temporal versions, 2,110 fine-grained structural chunks, 422 relational facts, 422 canonical QA entries.
- **RAG Pipeline:** FastEmbed ONNX (`BAAI/bge-small-en-v1.5`) + Partitioned BM25Okapi -> Reciprocal Rank Fusion ($k=60$) -> FlashRank ONNX Reranker (`ms-marco-TinyBERT-L-2-v2`) -> Local Ollama inference (`qwen3:4b-q4_K_M`).

## 2. Strongest Defensible Claims
1. **Incremental Update Efficiency:** Achieves **95.0% compute avoidance** and a **22.41x speedup** (0.241s vs 5.399s) on 5% sparse corpus updates.
2. **Access Control & Privacy:** **Zero unauthorized evidence leaks** observed across 3,840 cross-department/clearance evaluations (95% CI upper bound: **0.08%**).
3. **Deterministic Acceleration:** Bypasses generative LLM inference for **63.4%** of eligible queries, delivering **28.2 ms P50 latency** on deterministic fast paths.
4. **Retrieval Precision:** Achieves **94.47% Policy Recall@1** on eligible policy questions across 120 enterprise policies.
5. **Calibrated Grounding:** Post-hoc isotonic calibration reduces Expected Calibration Error (ECE) to **0.041**.

## 3. Critical Caveats & Unresolved Conflicts to Avoid
- **Never claim 94.5% overall accuracy:** Policy-level retrieval (94.47%) is distinct from fine-grained chunk retrieval (19.10%) and end-to-end question answer accuracy (**53.60%**).
- **Correct speedup claim:** State speedup as **22.4x** (or 19.3x end-to-end), replacing the historical 24.95x estimate.
- **Acknowledge synthetic nature:** The 120-policy/1,000-query benchmark is a deterministic synthetic enterprise workload; clarify that production scale numbers (5,000 policies) represent synthetic indexing scalability benchmarks.
