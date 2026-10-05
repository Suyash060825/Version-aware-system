# Veritas Manuscript: Camera-Ready Ordered Edits Specification

This document details the exact line-level changes required in `Version_Aware_Ieee.tex` to make the manuscript camera-ready and completely consistent with the audited characterization results.

---

## 📝 Ordered List of Camera-Ready Edits

### Edit 1: Provenance & Commit Specification
- **Location**: LaTeX Header Comments & Section V-A (`Experimental Methodology`)
- **Current Problem**: References only production commit `61d64b71` without documenting the characterization test harness commit `449e69b3`.
- **Instruction / Replacement**:
  Document both commits explicitly:
  `Production application logic was frozen at commit \texttt{61d64b71}; the expanded characterization test harness and benchmark suite were executed at commit \texttt{449e69b3}.`
- **Reason**: Maintains reproducibility and provenance integrity across both the legacy benchmark and the characterization suite.

---

### Edit 2: Abstract Refinement & Delineation
- **Location**: Abstract (lines 65–82)
- **Current Problem**: Reports 54.15% deterministic share and small fixture compiler speedups without context, and reports ECE reduction to 0.000 without noting it is calibration-split fitting.
- **Instruction / Replacement**:
  Refine abstract to clearly distinguish the two evaluation regimes:
  * Baseline Benchmark ($N=301$): 100.0% authorization decision correctness (0 leaks), 82.72% overall version resolution (86.30% local / 89.53% cloud on answered queries), 54.15% deterministic fast-path routing ($29.65\ms$ system median).
  * Expanded Characterization Suite ($N=922$): 0 observed leaks across 3,840 evaluations, 63.4% fast-path bypass, $24.95\times$ compiler speedup on 5% amendment deltas across 3,000 chunks (95.0% compute avoided), and 94.47% chunk retrieval recall ($K=100$).
  * Calibration: Note that isotonic calibration reduces validation ECE to 0.041 (0.000 on fit split), while runtime ECE is 0.2954.
- **Reason**: Accurately showcases the strongest audited characterization results without mixing numerators/denominators.

---

### Edit 3: Pre-Retrieval Authorization Phrasing Softening
- **Location**: Section I (Introduction) & Section III (Problem Formulation)
- **Current Problem**: Phrases such as "guarantees zero leakage" or "eliminates all leakage" imply formal cryptographic proofs.
- **Instruction / Replacement**:
  Replace with:
  `No unauthorized candidate evidence was observed entering the reranker or LLM prompt context across 3,840 authorization evaluations spanning 32 user archetypes and 120 policy documents (0 leaks / 3,840 trials; 95% upper bound <0.08%).`
- **Reason**: Defensible empirical statement conforming to strict peer review standards.

---

### Edit 4: NLI Model Identifier Alignment
- **Location**: Section IV-C (Security and Evidence Controls)
- **Current Problem**: Manuscript states `cross-encoder/nli-deberta-v3-base`, while the characterization audit specifies `DeBERTa-v3-large` ONNX.
- **Instruction / Replacement**:
  Clarify in text:
  `The NLI verification layer employs DeBERTa-v3 (deployed as cross-encoder/nli-deberta-v3-base in lightweight local runtime and DeBERTa-v3-large ONNX in the high-throughput characterization testbed).`
- **Reason**: Eliminates discrepancies between deployment profiles.

---

### Edit 5: Retrieval Candidate Pool Sensitivity ($K=50 \to K=100$)
- **Location**: Section IV-B (Tier 2 Hybrid Retrieval) & Section VI-C (Retrieval Quality)
- **Current Problem**: Manuscript mentions only top-50 candidate pooling without explaining compound query starvation.
- **Instruction / Replacement**:
  Retain $K=50$ as default and add sensitivity analysis:
  `While top-50 candidate pooling is default for simple lookups, sensitivity analysis on complex multi-clause queries demonstrates a depth dependency: expanding candidate depth to K=100 increases top-1 retrieval recall from 84.0% (42/50) to 94.0% (47/50), as cross-encoders cannot recover relevant chunks absent from initial candidate pools.`
- **Reason**: Explains architectural mechanics and presents a scientifically valuable sensitivity finding.

---

### Edit 6: Fixed-Gold-Evidence Generation Quality
- **Location**: Section VI-B (Temporal Validity and Generation Quality)
- **Current Problem**: End-to-end Token F1 (0.3516) and Exact Match (27.91%) are reported without isolating retrieval errors from generation capacity.
- **Instruction / Replacement**:
  Add decoupled benchmark discussion:
  `To isolate surface generation capability from upstream retrieval omissions, feeding exact gold evidence chunks directly into the model (Fixed Gold Evidence Evaluation, N=100) yields a Mean Token F1 of 0.962 and 100% target concept recall, confirming that end-to-end answer discrepancies stem primarily from passage retrieval omissions and natural paraphrastic variation rather than generative hallucination.`
- **Reason**: Clearly decouples retrieval vs. generation failure modes.

---

### Edit 7: Concurrency & Lock Contention Analysis
- **Location**: Section VI-G & Section VII (Discussion)
- **Current Problem**: Need to incorporate multi-user scaling without claiming "linear scalability".
- **Instruction / Replacement**:
  Add concurrency findings:
  `Multi-threaded load testing across 1, 10, 25, 50, and 100 concurrent workers confirmed 100% data isolation (0 scope leaks, 0 cache contaminations, 0 race conditions). Throughput scaled to 234.7 QPS at 1 worker and plateaued near 137 QPS under 50–100 workers, with median latency rising from 4.35ms to 317.82ms due to thread-lock synchronization under contention.`
- **Reason**: Honest, robust systems characterization.
