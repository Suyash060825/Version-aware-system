# Veritas Truthfulness & Hallucination Audit

**Audit Date:** 2026-10-25 | **Branch:** `improv` / `0ebae05`

---

## 1. Audit of Evidence Verification & NLI Pipeline

### 1.1 Entailment Verifier Configuration
**File:** [`rag/verification/entailment.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/verification/entailment.py)

- **Model:** `cross-encoder/nli-deberta-v3-base` via HuggingFace `sentence_transformers`.
- **Default State (CONFIRMED P0 DEFECT):**
  ```python
  # Line 31
  self.enabled = os.environ.get("ENTAILMENT_ENABLED", "false").lower() == "true"
  ```
  `ENTAILMENT_ENABLED` defaults to `"false"`. In any standard deployment where this environment variable is not explicitly injected, `verify()` executes line 76:
  ```python
  if not self.enabled or not self._model:
      return EntailmentResult(is_entailed=True, score=1.0, verdict="ENTAILMENT")
  ```
  Every generated answer is rubber-stamped as fully entailed with confidence 1.0.

### 1.2 The "Bypass Grounded" Architecture Hole
**File:** [`rag/engine/query_engine.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/engine/query_engine.py#L721-L734)

Even when `ENTAILMENT_ENABLED="true"`, the verification stage contains a short-circuit bypass:
```python
# FIX 4.2 Bypass: numeric grounding passes AND contains policy name and version number
has_policy_name = any(
    c.get("policy_name", "").lower() in ans_candidate.lower()
    for c in citations if c.get("policy_name")
)
has_version = bool(re.search(r"\bv\d+(\.\d+)?\b", ans_candidate, re.IGNORECASE)) or any(
    str(c.get("version", "")).lower() in ans_candidate.lower()
    for c in citations if c.get("version")
)
if has_policy_name and has_version:
    is_grounded = True
    nli_verdict = "BYPASS_GROUNDED"
    nli_entail_score = 1.0
    nli_contra_score = 0.0
```
- **Consequence:** If the model includes boilerplate like *"According to Travel Policy v1.0..."*, NLI verification is **completely bypassed**. The model can state arbitrary ungrounded or hallucinated rules in the remainder of the sentence, and the system records `nli_verdict="BYPASS_GROUNDED"` and allows delivery.
- This directly explains why the reported hallucination rate in `ieee_publication_v1` was artificially low (1.10%): the verifier was bypassed on almost all citations that included policy names and version tokens.

### 1.3 Citation-Prefix Claim Pruning Defect
**File:** [`rag/verification/entailment.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/verification/entailment.py#L68-L72)
```python
# Strip claims that are merely citation attribution
claims = [
    c for c in claims
    if not c.lower().startswith(("according to", "based on", "table of", "section"))
]
```
The system prompt specifically instructs the model to prefix authoritative claims with *"According to [Policy]..."*. However, the NLI claim splitter explicitly discards any sentence beginning with *"according to"*. Consequently, the exact sentences that deliver factual answers are pruned from the NLI claim pool, leaving only secondary or un-attributed sentences to be checked.

---

## 2. Numerical Grounding & Hallucination Resistance

### 2.1 Implementation
**File:** [`rag/engine/query_engine.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/engine/query_engine.py#L76-L99)
- `verify_numeric_grounding` extracts all digits and percentages using `\b\d+(?:\.\d+)?%?\b`.
- Compares numerical tokens against `extract_grounding_numbers(chunks)`.
- Exceptions: single digits (0–9) and 4-digit years (19xx, 20xx) are exempt from checking.

### 2.2 Strengths & Blind Spots
- **Strength:** Effectively prevents numerical hallucination for monetary values (e.g., claiming "$5,000" when the text states "$2,500").
- **Blind Spot:** Single digits are exempt (`int(num_clean) in range(0, 10)`). A policy stating an allowance of `2` days can be hallucinated as `8` days without triggering a numerical grounding rejection.
