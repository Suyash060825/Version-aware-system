# REPORT G: RESEARCH & EVALUATION METRIC AUDIT

**Project**: Veritas: Version-Aware Enterprise Policy Intelligence via Incremental Knowledge Compilation and Adaptive Multi-Tier Retrieval  
**Audit Date**: October 25, 2026  
**Auditor**: IEEE Senior Reviewer & Independent Empirical ML Auditor  
**Document Under Review**: `Version_Aware_Ieee_CAMERA_READY.tex`  
**Underlying Artifacts**: `experiments/veritas_fullstack_20261023_171900_8337271/`, `evaluation/`  
**Status**: Complete  

---

## 1. Executive Scientific Assessment

The paper titled *"Veritas: Version-Aware Enterprise Policy Intelligence via Incremental Knowledge Compilation and Adaptive Multi-Tier Retrieval"* presents a compelling premise: combining temporal policy resolution, incremental compiler hashing, and multi-tier query routing for enterprise compliance.

However, a forensic audit of the experimental code (`evaluation/metrics.py`, `evaluation/run_benchmark.py`, `evaluation/run_scale_benchmark.py`) alongside raw execution artifacts in `experiments/` reveals **four critical methodological vulnerabilities, two statistical distortions, and significant latency omissions**. If submitted to an IEEE transactions or conference track in its current state, these issues would warrant an immediate **Desk Reject** or **Reject** upon technical review.

---

## 2. Forensic Dissection of Paper Tables vs. Code & Raw Artifacts

### 2.1 Table 5: The "Identical Recall" Anomaly
- **Paper Claim**: In Table 5 (*Retrieval Subsystem Metrics Across Regimes*), Regime 1 reports:
  - Dense (BGE-Small): $\text{R@1} = 98.61\%$, $\text{R@5} = 98.61\%$, $\text{R@10} = 98.61\%$, $\text{MRR} = 0.9861$, $\text{NDCG@10} = 0.9861$.
  - Hybrid (RRF): $\text{R@1} = 98.61\%$, $\text{R@5} = 98.61\%$, $\text{R@10} = 98.61\%$, $\text{MRR} = 0.9861$, $\text{NDCG@10} = 0.9861$.
  - Hybrid + FlashRank: $\text{R@1} = 98.61\%$, $\text{R@5} = 98.61\%$, $\text{R@10} = 98.61\%$, $\text{MRR} = 0.9861$, $\text{NDCG@10} = 0.9861$.
- **Audit Discovery**: In information retrieval theory, it is mathematically extraordinary for Recall@1, Recall@5, and Recall@10, as well as MRR and NDCG@10, to be identical across distinct retrieval techniques down to the basis point.
- **Root Cause in Code**: In `evaluation/run_benchmark.py:501-502`, the benchmark harness does not record candidate retrieval sets from BM25 or ChromaDB. Instead, it extracts the policy citations emitted by the LLM generator:
  ```python
  # evaluation/run_benchmark.py:501-502
  retrieved_policy_ids = [extract_citation(response.answer)]
  ```
  Because the generated answer cites exactly one policy document, the candidate list passed to the evaluator has length 1. For a list of length 1:
  $$\text{Recall@1} = \text{Recall@5} = \text{Recall@10} = \text{MRR} = \text{NDCG@10}$$
- **Scientific Impact**: Table 5 does not measure retrieval subsystem recall; it measures the single-citation extraction accuracy of the generation prompt.

### 2.2 Table 6: Latency Concealment (Omitting Tier 3 CPU Generation)
- **Paper Claim**: Table 6 (*System Latency Scaling Across Corpus Tiers*) presents:
  - Enterprise Corpus (2.11k chunks): Tier 0 P50 = $4.17\ms$, Tier 1 P50 = $3.18\ms$, Tier 2 P50 = $12.89\ms$, **E2E P50 = $4.05\ms$, E2E P95 = $12.93\ms$**.
- **Audit Discovery**: An unsuspecting reader concludes that Veritas generates verified enterprise policy answers with an End-to-End P95 of 12.93 milliseconds. However, inspecting the raw benchmark logs (`experiments/.../retrieval_results.jsonl`) reveals that whenever a query misses Tier 0/1/2 and triggers Tier 3 (Ollama Qwen 4B generation on CPU), the actual execution latency is:
  $$\text{Tier 3 Generation Latency} = 21{,}854.2\ms \text{ to } 27{,}410.8\ms$$
- **Root Cause**: Table 6 redefined "E2E" to mean the weighted average of the retrieval and deterministic fast-paths, completely filtering out or isolating the Tier 3 generation phase into an unweighted separate footnote.
- **Scientific Impact**: High risk of IEEE reviewer challenge for deceptive latency reporting. An interactive enterprise system cannot claim 12ms P95 latency when generative queries take 25 seconds.

### 2.3 Table 7: The "2,034x Speedup" Artifact (Comparing Apples to Oranges)
- **Paper Claim**: Table 7 (*Incremental Compiler: Mutation Sweeps vs. Cold Rebuild*) claims:
  - 250-Chunk Hash no-op: Incremental Time = $1.70\ms$, Cold Rebuild = $3{,}448.9\ms$, **Speedup = $2{,}034.57\times$**.
  - In other runs, speedups as high as $5{,}059\times$ are highlighted.
- **Audit Discovery**: The incremental time ($1.70\ms$) measures a single SHA256 string equality check on a hash digest stored in memory/Redis. The cold rebuild ($3{,}448.9\ms$) measures tokenization, ONNX forward-pass embedding generation for 250 text chunks, and disk serialization.
- **Scientific Impact**: Claiming a $2{,}000\times$ "compilation speedup" by comparing a hash comparison against whole-corpus embedding recomputation is an apples-to-oranges benchmark artifact. A valid baseline would compare against an incremental cache without structure extraction.

---

## 3. Evaluation Code Integrity Defects

### 3.1 Artificial Metric Inflation in Token F1 (`contains_bonus`)
In `evaluation/metrics.py:59`:
```python
def compute_token_f1(prediction: str, ground_truth: str) -> float:
    # ...
    if target_clean in pred_clean:
        return max(base_f1, 0.70)
```
- **Consequence**: If the ground truth is `"90 days"`, and the model emits a 400-word paragraph containing erroneous facts but happens to include the substring `"90 days"`, the F1 score is floored at `0.70`.
- **Verdict**: Non-standard metric manipulation. Standard SQuAD/RAG Token F1 requires true harmonic mean of token precision and recall.

### 3.2 Tautological Version Chunk Matching (`or True`)
In `evaluation/metrics.py:159`:
```python
def _chunks_match(ret_chunk, exp_chunk):
    if ret_chunk.get("policy_id") == exp_chunk.get("policy_id"):
        return ret_chunk.get("version_seq") == exp_chunk.get("version_seq") or True
    return False
```
- **Consequence**: The expression evaluates to `True` unconditionally as long as the policy ID matches, regardless of whether the retrieved version was v1, v2, or v5.
- **Verdict**: Completely invalidates reported version-sequence matching accuracy in evaluation scripts where this function is called.

### 3.3 Synthetic Chunk Attribution in Scale Benchmarks
In `evaluation/run_scale_benchmark.py:311`:
```python
"retrieved_chunk_ids": q.expected_evidence_chunks if r["answer_correctness"] else []
```
- **Consequence**: The scale benchmark does not record the chunks the retriever actually returned. Instead, it populates `retrieved_chunk_ids` with `expected_evidence_chunks` whenever the answer is correct.
- **Verdict**: Circular evaluation; retrieval metrics cannot be scientifically trusted when synthesized from answer correctness.

---

## 4. Discrepancies: Paper Text vs. Real Codebase

| Feature / Claim | Claim in IEEE Paper | Reality in Codebase | Severity |
| :--- | :--- | :--- | :---: |
| **Vector Storage Engine** | PostgreSQL 16 with pgvector extension (`policy_chunk_v2.embedding vector(384)`) | ChromaDB + FAISS; `models.py` has no `Vector` column | **High** |
| **Entailment Verification** | Always active cross-encoder NLI guaranteeing 100% answer grounding | `ENTAILMENT_ENABLED = False` by default; inversion bug accepts `NEUTRAL` | **High** |
| **Retrieval Granularity** | Regime 1 reports 98.61% R@1/5/10 | Logs single answer citation; true chunk R@1 is 9.69% (Regime 2) | **High** |
| **End-to-End Latency** | P95 = $12.93\ms$ across corpus tiers | Excludes Tier 3 CPU LLM generation ($21{,}000 - 27{,}000\ms$) | **High** |
| **Incremental Speedup** | $2{,}034\times$ to $5{,}059\times$ speedup | Measures SHA256 string comparison vs full ONNX embedding | **Medium** |

---

## 5. Reviewer Vulnerability Assessment (Anticipated Peer-Review Objections)

If submitted to IEEE Transactions on Knowledge and Data Engineering (TKDE) or IEEE ICDE:

1. **Reviewer 1 (Information Retrieval Specialist)**:  
   *"Table 5 shows identical numbers for R@1, R@5, R@10, MRR, and NDCG@10 across BM25, Dense, and Hybrid. This is an indicator of experimental error or metric miscalculation. Explain how the candidate sets were formed."*  
   $\rightarrow$ **Result**: Fatal flaw; cannot be defended without admitting citations were logged instead of retrieved sets.

2. **Reviewer 2 (Systems & Benchmarking Specialist)**:  
   *"The paper claims 12.9ms P95 latency in Table 6 for an enterprise RAG system running a 4B local model on CPU. How is this possible when local autoregressive generation on CPU requires hundreds of milliseconds per token? Are generative queries included in Table 6?"*  
   $\rightarrow$ **Result**: Rejection for misleading presentation of system latency.

3. **Reviewer 3 (Reproducibility & Code Auditor)**:  
   *"Inspection of `evaluation/metrics.py` shows an arbitrary floor of 0.70 applied to Token F1 and an `or True` statement in chunk matching. The reported F1 numbers are mathematically ungrounded."*  
   $\rightarrow$ **Result**: Immediate desk reject for metric tampering.

---

## 6. Concrete Remediation Plan for Publication Integrity

To restore full scientific validity and produce an unassailable camera-ready paper:

1. **Clean Metric Implementations**:
   - Strip `contains_bonus` from `compute_token_f1()` and replace with standard SQuAD token F1.
   - Remove `or True` from `_chunks_match()`.
   - Update `run_scale_benchmark.py` to record true `retrieved_chunks`.
2. **Compute True Retrieval Candidate Metrics**:
   - Log top-1, top-5, and top-10 chunks from the hybrid retrieval candidate pool before LLM generation. Recompute Table 5 with true monotonically increasing recall curves.
3. **Transparent Latency Reporting**:
   - Update Table 6 to explicitly show:
     - Tier 0 (Fact Path): $3.1\ms$
     - Tier 1 (QA Cache): $4.1\ms$
     - Tier 2 (Hybrid RAG + FlashRank): $48.5\ms$
     - Tier 3 (Local Qwen 4B Generation on CPU): $22{,}400\ms$
     - Explain that Tier 0-2 absorb $75-80\%$ of typical corporate policy queries, shielding users from Tier 3 CPU overhead.
4. **Clarify Vector Storage Engine**:
   - Update the architecture section to describe ChromaDB + ONNX FastEmbed accurately, removing references to pgvector migrations.

---
*Report G completed in accordance with Veritas forensic audit specification.*
