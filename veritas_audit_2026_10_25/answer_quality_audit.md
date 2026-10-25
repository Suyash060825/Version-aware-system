# Veritas Answer Quality Audit

**Audit Date:** 2026-10-25 | **Branch:** `improv` / `0ebae05`

---

## 1. Generation Architecture & Routing Discrepancies

### 1.1 Dual Execution Modes
Inspection of [`rag/engine/query_engine.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/engine/query_engine.py) reveals two distinct answer-generation paths with divergent routing behavior:

1. **Deterministic Fast-Paths & Grounded Extraction:**
   - Level 0: `FactResolver` (regex + exact predicate store).
   - Level 1: `QAMatcher` (precompiled FAISS canonical question embeddings).
   - Level 3: `PolicyDiffEngine` (structural clause diffs).
   - Fallback Level 2: `_extract_best_evidence_context` (multi-sentence extractive synthesis scored by query token overlap).
2. **Neural Live Generation (Qwen3 4B via Ollama):**
   - In `answer()` (batch mode, L711): Invoked if `self.config.use_llm` is True and `self.llm.health_check()` passes.
   - In `stream_answer()` (streaming mode, L1036): Invoked **only** if `complexity >= ComplexityLevel.LEVEL_2_RETRIEVAL` AND `llm_available`.
   - **Finding:** Batch answers can invoke the LLM on low-complexity queries if fast paths miss, whereas streaming forces low-complexity fallthroughs straight to extractive summarization.

---

## 2. Answer Error Taxonomy (Empirical Analysis of Benchmark Runs)

### 2.1 The 3,000-Query Benchmark (`evaluation/results/`)
Analysis of `answer_quality_metrics.json` reveals categorical failure clusters:

```
Category Accuracy Breakdown:
- CAT_01_FACTUAL_LOOKUP:       100.0%  (30/30)   - Handled via Level 0 FactResolver
- CAT_02_VERSION_LOOKUP:       100.0%  (57/57)   - Handled via Level 0/3 VersionResolver
- CAT_07_CROSS_POLICY:           0.0%  (0/15)    - Extractive fallback selects 1 policy context only
- CAT_09_HISTORICAL_VS_CURRENT:  7.4%  (2/27)    - Fails to contrast superseded vs active versions
- CAT_11_EXCEPTIONS:             0.0%  (0/30)    - Sentence overlap picks rule, drops exception clause
- CAT_24_QWEN_GENERATION:        0.0%  (0/40)    - Live generation path produces 0% valid answers
```

### 2.2 Root Causes for Catastrophic Zero-Accuracy Categories

1. **CAT_24_QWEN_GENERATION (0.0%):**
   - As confirmed by `generation_results.json`, evaluation records indicate `"llm_used": false` across all samples, and answers return `"I could not find sufficient authoritative evidence in the applicable policies."`
   - In local CI/test environments, Ollama was either unreachable, or `QwenLocalProvider.health_check()` returned false due to missing local container daemon, causing immediate short-circuiting to abstention.
   - For queries with synthesis prompts, `_extract_best_evidence_context` requires substantive keyword match (`top_sub > 0`). When synthesis questions ask open-ended queries like "Provide an overview of all employee obligations", word overlap with any single policy chunk fails the threshold.

2. **CAT_07_CROSS_POLICY (0.0%):**
   - `_extract_best_evidence_context` lines 153–155 pick a single `winning_pid` from the highest-scoring chunk.
   - Lines 169–184 attempt secondary candidate synthesis, but restrict secondary chunks to those sharing uncovered question words. Because cross-policy questions require comparing two full distinct policy regimes, the 5-chunk retrieval limit and top-5 citation cap truncate the second policy's core context.

3. **CAT_11_EXCEPTIONS (0.0%):**
   - Scored candidates rank sentences by token overlap.
   - Rules ("Employees are entitled to 20 days annual leave") match query keywords ("annual leave entitlement").
   - Disqualifying exceptions ("Except during mandatory probation or disciplinary review") match fewer keywords and receive lower overlap scores, causing them to be excluded from `context_paragraph` (L162–163: `best_idx - 1` to `best_idx + 2`).

---

## 3. Grounding, Prompt Construction, and Citation Integrity

### 3.1 Prompt Hard Truncation
In [`rag/generation/prompts.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/generation/prompts.py#L37):
```python
"text": chunk.get("text", "")[:700]
```
Retrieved passages injected into the Qwen LLM prompt are forcibly truncated to 700 characters. If the key qualifying condition or date is in the latter half of an 1,200-character chunk, the LLM literally never receives it.

### 3.2 Evaluation Metric Mismatch vs Genuine Answer Correctness
- In `CAT_03_SEMANTIC_PARAPHRASE`, reported accuracy is 96.7% while Mean Token F1 is **0.0233**.
- The evaluation script counts an answer as correct if `expected_answer_contains` tokens are present OR `f1 >= 0.40`.
- An answer stating: *"According to the Travel and Expense Policy (v2.0, Section 4.1): The per diem allowance for international lodging shall not exceed standard GSA rates"* matches the substring `["GSA"]`, achieving binary `is_correct = True`, while lexical Token F1 against the reference string `"$250 per night"` is zero.
