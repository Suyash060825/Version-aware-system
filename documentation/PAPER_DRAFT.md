# Temporal Integrity and Cost-Aware Routing in Enterprise Policy Retrieval-Augmented Generation

## Abstract
Retrieval-Augmented Generation (RAG) has become the de facto architecture for enterprise question-answering. However, in dynamic environments like corporate policy management, standard RAG architectures face two critical challenges: temporal hallucination (answering based on superseded policy versions) and high inference costs. We present **Policy Ledger v2**, an end-to-end version-aware RAG platform. By introducing a Version-Scoped Semantic Cache (VSSC) with exact-match tiers and a Confidence-Weighted Model Cascade (CWMC) with automated circuit breakers, we achieve significant reductions in LLM inference costs while maintaining high accuracy. Furthermore, we implement a strict semantic entailment grounding check that virtually eliminates ungrounded hallucinations, enforcing temporal correctness across evolving document sets.

## 1. Introduction
Enterprise policies undergo continuous revisions. A standard RAG pipeline, which relies on dense vector retrieval, often fails to distinguish between an active policy and a recently superseded draft when both share high semantic similarity with the query. This leads to temporal hallucinations where the LLM confidently provides outdated benefits or procedures. Moreover, routing all queries to large foundation models incurs unnecessary latency and cost, especially for repetitive factual lookups (e.g., "What is the parental leave policy?").

To address these challenges, we introduce an applied architecture that integrates document versioning directly into the RAG lifecycle.

## 2. Architecture and Implementation

### 2.1 Version-Scoped Semantic Cache (VSSC)
The VSSC intercepts queries at two tiers:
1. **Exact-Match Tier**: Hashes the incoming query string (or deterministic embedding) to provide an $O(1)$ cache hit for frequent exact queries.
2. **Semantic Tier**: Uses cosine similarity over embeddings (threshold $\ge 0.95$) to serve semantically equivalent queries.

Critically, cache entries store the exact database version identifiers of the policies they cite. When a policy is updated, a signal invalidates only the cache entries citing the superseded version, eliminating stale answers without needing to purge the entire cache.

### 2.2 Confidence-Weighted Model Cascade
Not all queries require a billion-parameter model. We implemented a cascading router that defaults to a lightweight local model (e.g., Llama 3.1 8B). The system escalates to a heavier cloud model (e.g., `google/gemini-2.0-flash-001`) only when:
- The top reranked chunks fall below a confidence threshold (60%).
- The user is explicitly asking a comparative, cross-version query (detected via keyword heuristics).
This cascade is protected by a circuit breaker pattern (Closed, Open, Half-Open) to ensure high availability even when local hardware fails.

### 2.3 Layered Guardrails (Regex and Model-Based)
To prevent hallucinations and out-of-scope answers, the output undergoes a rigorous two-layered guardrail check:
1. **Regex Heuristics**: Lightweight keyword matching blocks obvious prompt injections and out-of-scope requests (e.g., requests concerning external topics).
2. **Strict Entailment Grounding**: Beyond mere citation formatting, the system passes the generated answer and retrieved chunks to an NLI Cross-Encoder (`nli-deberta-v3-base`). If the entailment score is low, the response is rejected and defaults to a safe refusal.

## 3. Evaluation Setup
We constructed a "Golden Dataset" of 100 enterprise queries covering factual lookups, cross-version diffs, adversarial prompt injections, and role-based access denials. The system was evaluated against a "Naive RAG" baseline consisting of single-pass dense retrieval and a static large model without caching or version awareness.

## 4. Results
Preliminary evaluation utilizing our automated benchmark suite (`eval/run_eval.py`) reveals:
- **Cost & Latency Reduction**: The introduction of the VSSC and Model Cascade significantly lowered average latency and drastically reduced calls to the expensive secondary model.
- **Accuracy Improvement**: By leveraging Hybrid Search (BM25 + Dense) with Reciprocal Rank Fusion (RRF), retrieval accuracy improved for keyword-heavy queries (e.g., specific acronyms or policy IDs).
- **Zero-Tolerance for Hallucination**: The combination of structural citation validation and cross-encoder entailment yielded high groundedness scores, successfully blocking hallucinated responses in adversarial edge cases.

## 5. Conclusion
Integrating version awareness deeply into the RAG pipeline—from vector store metadata to semantic cache invalidation—solves the temporal hallucination problem in dynamic document systems. Combined with cost-aware model routing and strict entailment checks, Policy Ledger v2 demonstrates a robust blueprint for deploying enterprise generative AI safely and economically.
