"""
rag/verification/entailment.py
Entailment-based grounding check for RAG responses.
Provides EntailmentVerifier class with claim extraction and DeBERTa NLI scoring.
"""
import re
import os
import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("rag.entailment")

@dataclass
class EntailmentResult:
    is_entailed: bool
    score: float
    verdict: str  # ENTAILMENT, CONTRADICTION, UNKNOWN
    failed_claims: List[str] = field(default_factory=list)
    contra_score: float = 0.0

    def __iter__(self):
        yield self.is_entailed
        yield self.score

class EntailmentVerifier:
    _shared_nli_model = None
    _shared_use_nli = True

    def __init__(self):
        # Enable entailment verification by default in production
        self.enabled = os.environ.get('ENTAILMENT_ENABLED', 'true').lower() in ('true', '1')

    @property
    def _nli_model(self):
        return EntailmentVerifier._shared_nli_model

    @_nli_model.setter
    def _nli_model(self, val):
        EntailmentVerifier._shared_nli_model = val

    @property
    def _use_nli(self):
        return EntailmentVerifier._shared_use_nli

    @_use_nli.setter
    def _use_nli(self, val):
        EntailmentVerifier._shared_use_nli = val

    def _get_nli_model(self):
        if EntailmentVerifier._shared_nli_model is None and EntailmentVerifier._shared_use_nli:
            try:
                from sentence_transformers import CrossEncoder
                device = os.environ.get("RERANKER_DEVICE", "cpu")
                EntailmentVerifier._shared_nli_model = CrossEncoder("cross-encoder/nli-deberta-v3-base", device=device)
            except Exception as e:
                logger.warning(f"Failed to load NLI model, falling back to lexical overlap: {e}")
                EntailmentVerifier._shared_use_nli = False
        return EntailmentVerifier._shared_nli_model

    def split_into_claims(self, text: str) -> List[str]:
        # Strip markdown, citations, header boilerplate
        t = re.sub(r'\[Policy:[^\]]+\]', '', text)
        t = re.sub(r'^(?:[A-Z\s&—\-]+(?:POLICY|v\d+\.\d+))', '', t, flags=re.MULTILINE)
        t = re.sub(r'Effective Date:\s*[0-9\-]+', '', t)
        sentences = re.split(r'(?<=[.!?\n])\s+', t.strip())
        claims = []
        for s in sentences:
            s_clean = s.strip().lstrip("0123456789.- ")
            # Strip citation preamble while keeping underlying substantive claims
            s_clean = re.sub(r'^(?:According to [^:]+:\s*|Based on [^:]+:\s*)', '', s_clean, flags=re.IGNORECASE).strip()
            # Only evaluate substantive claims with verbs / facts
            if len(s_clean) >= 15 and not s_clean.startswith("Table of"):
                claims.append(s_clean)
        return claims

    def verify(self, answer: str, chunks: List[Dict[str, Any]]) -> EntailmentResult:
        if not self.enabled:
            return EntailmentResult(is_entailed=True, score=1.0, verdict="ENTAILMENT", failed_claims=[])
        if not answer or not chunks:
            return EntailmentResult(is_entailed=False, score=0.0, verdict="CONTRADICTION", failed_claims=["No evidence provided"])

        claims = self.split_into_claims(answer)
        if not claims:
            return EntailmentResult(is_entailed=True, score=1.0, verdict="ENTAILMENT", failed_claims=[])

        context = " ".join([c.get("text", "") for c in chunks])
        nli = self._get_nli_model()

        if nli:
            negations = {'not', 'no', 'never', 'neither', 'none', 'cannot', "can't", "won't", "don't", 'prohibited', 'forbidden', 'disallowed', 'excluded'}
            claim_scores = [None] * len(claims)
            pairs_to_predict = []

            for i, claim in enumerate(claims):
                claim_tokens = set(re.findall(r"[a-z0-9]+", claim.lower()))
                best_chunk_text = ""
                best_overlap = -1
                for c in chunks:
                    c_text = c.get("text", "")
                    c_tokens = set(re.findall(r"[a-z0-9]+", c_text.lower()))
                    overlap = len(claim_tokens & c_tokens)
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_chunk_text = c_text
                if not best_chunk_text and chunks:
                    best_chunk_text = chunks[0].get("text", "")

                # 1. Verbatim exact match / substring check:
                # If claim text is directly in evidence, it is 100% entailed without CPU model forward pass
                c_clean = claim.lower().strip()
                chunk_clean = best_chunk_text.lower()
                if c_clean in chunk_clean or (len(c_clean) > 25 and (c_clean[:35] in chunk_clean and c_clean[-20:] in chunk_clean)):
                    claim_scores[i] = (1.0, 0.0)
                    continue

                # 2. High-fidelity lexical grounding check (>=85% token overlap, exact numbers, matching negations)
                if claim_tokens:
                    chunk_tokens = set(re.findall(r"[a-z0-9]+", chunk_clean))
                    tok_overlap = len(claim_tokens & chunk_tokens) / len(claim_tokens)
                    claim_nums = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", claim))
                    chunk_nums = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", best_chunk_text))
                    unsupported_nums = claim_nums - chunk_nums
                    claim_has_neg = bool(claim_tokens & negations)
                    chunk_has_neg = bool(chunk_tokens & negations)
                    if tok_overlap >= 0.85 and not unsupported_nums and (claim_has_neg == chunk_has_neg):
                        claim_scores[i] = (0.95, 0.0)
                        continue

                # Focus chunk context to reduce DeBERTa sequence length from 512 to compact window (reduces O(L^2) attention)
                compact_ctx = best_chunk_text
                if len(compact_ctx) > 300 and claim_tokens:
                    words = best_chunk_text.split()
                    best_w_idx = 0
                    max_w_overlap = -1
                    for w_idx in range(0, max(1, len(words) - 20), 10):
                        window = " ".join(words[w_idx:w_idx+40])
                        w_overlap = len(claim_tokens & set(re.findall(r"[a-z0-9]+", window.lower())))
                        if w_overlap > max_w_overlap:
                            max_w_overlap = w_overlap
                            best_w_idx = w_idx
                    compact_ctx = " ".join(words[best_w_idx:best_w_idx+40])

                pairs_to_predict.append((i, compact_ctx, claim))

            if pairs_to_predict:
                try:
                    pairs = [(p[1], p[2]) for p in pairs_to_predict]
                    scores = nli.predict(pairs, batch_size=min(len(pairs), 8))
                    import numpy as np
                    def softmax(x):
                        e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
                        return e_x / e_x.sum(axis=-1, keepdims=True)

                    probs = softmax(scores) if len(scores.shape) > 1 else softmax(np.array([scores]))[0]
                    label2id = {k.lower(): v for k, v in nli.config.label2id.items()}
                    entailment_idx = label2id.get('entailment', 1)
                    contradiction_idx = label2id.get('contradiction', 0)

                    if len(probs.shape) > 1:
                        e_scores = probs[:, entailment_idx]
                        c_scores = probs[:, contradiction_idx]
                    else:
                        e_scores = np.array([probs[entailment_idx]])
                        c_scores = np.array([probs[contradiction_idx]])

                    for (idx, _, _), es, cs in zip(pairs_to_predict, e_scores, c_scores):
                        claim_scores[idx] = (float(es), float(cs))
                except Exception as e:
                    logger.error(f"Error in NLI predict: {e}")

            # Combine predictions
            entail_vals = [cs[0] for cs in claim_scores if cs is not None]
            contra_vals = [cs[1] for cs in claim_scores if cs is not None]
            if len(entail_vals) == len(claims):
                avg_entail = float(sum(entail_vals) / max(len(entail_vals), 1))
                avg_contra = float(sum(contra_vals) / max(len(contra_vals), 1))

                if avg_contra > 0.65:
                    verdict = "CONTRADICTION"
                    is_entailed = False
                elif avg_entail > 0.35:
                    verdict = "ENTAILMENT"
                    is_entailed = True
                else:
                    verdict = "UNKNOWN"
                    is_entailed = False

                failed = [claims[i] for i, cs in enumerate(claim_scores) if cs and cs[1] > 0.65]
                return EntailmentResult(is_entailed=is_entailed, score=avg_entail, verdict=verdict, failed_claims=failed, contra_score=avg_contra)

        # Fallback when neural NLI model is unavailable
        # Lexical and symbolic rule verification: checks numbers, dates, negations, and token overlap
        context_tokens = set(re.findall(r"[a-z0-9]+", context.lower()))
        ctx_nums = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", context))
        negations = {'not', 'no', 'never', 'neither', 'none', 'cannot', "can't", "won't", "don't", 'prohibited', 'forbidden', 'disallowed', 'excluded'}
        ctx_has_neg = bool(context_tokens & negations)

        claim_scores = []
        failed = []
        contra_detected = False

        for claim in claims:
            claim_tokens = set(re.findall(r"[a-z0-9]+", claim.lower()))
            if not claim_tokens:
                continue
            overlap = len(claim_tokens & context_tokens) / len(claim_tokens)
            claim_scores.append(overlap)

            # 1. Number / date ground check
            claim_nums = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", claim))
            unsupported_nums = claim_nums - ctx_nums

            # 2. Negation flip check
            claim_has_neg = bool(claim_tokens & negations)

            if unsupported_nums and overlap > 0.4:
                contra_detected = True
                failed.append(f"Contradictory/unsupported quantity in: '{claim}'")
            elif claim_has_neg != ctx_has_neg and overlap > 0.6:
                contra_detected = True
                failed.append(f"Negation contradiction in: '{claim}'")
            elif overlap < 0.35:
                failed.append(f"Insufficiently supported claim: '{claim}'")

        avg_overlap = sum(claim_scores) / max(len(claim_scores), 1)

        if contra_detected:
            verdict = "CONTRADICTION"
            is_entailed = False
            avg_contra = 0.90
        elif avg_overlap >= 0.70 and not failed:
            verdict = "ENTAILMENT"
            is_entailed = True
            avg_contra = 0.05
        else:
            verdict = "UNKNOWN"
            is_entailed = False
            avg_contra = 0.15

        return EntailmentResult(is_entailed=is_entailed, score=avg_overlap, verdict=verdict, failed_claims=failed, contra_score=avg_contra)

_DEFAULT_VERIFIER = None

def get_entailment_verifier() -> EntailmentVerifier:
    global _DEFAULT_VERIFIER
    if _DEFAULT_VERIFIER is None:
        _DEFAULT_VERIFIER = EntailmentVerifier()
    return _DEFAULT_VERIFIER

def verify_entailment(answer: str, chunks: List[Dict[str, Any]]) -> Tuple[bool, float]:
    verifier = get_entailment_verifier()
    res = verifier.verify(answer, chunks)
    return res.is_entailed, res.score
