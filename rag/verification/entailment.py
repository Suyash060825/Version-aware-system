"""
rag/verification/entailment.py
Entailment-based grounding check for RAG responses.
Provides EntailmentVerifier class with claim extraction and DeBERTa NLI scoring.
"""
import re
import os
import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger("rag.entailment")

@dataclass
class EntailmentResult:
    is_entailed: bool
    score: float
    verdict: str  # ENTAILMENT, CONTRADICTION, UNKNOWN
    failed_claims: List[str]

class EntailmentVerifier:
    def __init__(self):
        self.enabled = os.environ.get('ENTAILMENT_ENABLED', 'true').lower() == 'true'
        self._nli_model = None
        self._use_nli = True

    def _get_nli_model(self):
        if self._nli_model is None and self._use_nli:
            try:
                from sentence_transformers import CrossEncoder
                device = os.environ.get("RERANKER_DEVICE", "cpu")
                self._nli_model = CrossEncoder("cross-encoder/nli-deberta-v3-base", device=device)
            except Exception as e:
                logger.warning(f"Failed to load NLI model, falling back to lexical overlap: {e}")
                self._use_nli = False
        return self._nli_model

    def split_into_claims(self, text: str) -> List[str]:
        # Strip markdown, citations, header boilerplate
        t = re.sub(r'\[Policy:[^\]]+\]', '', text)
        t = re.sub(r'^(?:[A-Z\s&—\-]+(?:POLICY|v\d+\.\d+))', '', t, flags=re.MULTILINE)
        t = re.sub(r'Effective Date:\s*[0-9\-]+', '', t)
        sentences = re.split(r'(?<=[.!?\n])\s+', t.strip())
        claims = []
        for s in sentences:
            s_clean = s.strip().lstrip("0123456789.- ")
            # Only evaluate substantive claims with verbs / facts
            if len(s_clean) >= 15 and not s_clean.startswith(("According to", "Based on", "Table of")):
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
            pairs = [(context, claim) for claim in claims]
            try:
                scores = nli.predict(pairs)
                import numpy as np
                def softmax(x):
                    e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
                    return e_x / e_x.sum(axis=-1, keepdims=True)

                probs = softmax(scores) if len(scores.shape) > 1 else softmax(np.array([scores]))[0]
                label2id = {k.lower(): v for k, v in nli.config.label2id.items()}
                entailment_idx = label2id.get('entailment', 1)
                contradiction_idx = label2id.get('contradiction', 0)

                if len(probs.shape) > 1:
                    entailment_scores = probs[:, entailment_idx]
                    contra_scores = probs[:, contradiction_idx]
                else:
                    entailment_scores = np.array([probs[entailment_idx]])
                    contra_scores = np.array([probs[contradiction_idx]])

                avg_entail = float(entailment_scores.mean())
                avg_contra = float(contra_scores.mean())

                if avg_contra > 0.5:
                    verdict = "CONTRADICTION"
                    is_entailed = False
                elif avg_entail > 0.35:
                    verdict = "ENTAILMENT"
                    is_entailed = True
                else:
                    verdict = "UNKNOWN"
                    is_entailed = False

                failed = [claims[i] for i, s in enumerate(entailment_scores) if s <= 0.35]
                return EntailmentResult(is_entailed=is_entailed, score=avg_entail, verdict=verdict, failed_claims=failed)
            except Exception as e:
                logger.error(f"Error in NLI predict: {e}")

        # Fallback when neural NLI model is unavailable
        # Lexical overlap measures token recall but cannot prove factual entailment.
        context_tokens = set(re.findall(r"[a-z0-9]+", context.lower()))
        claim_scores = []
        failed = []

        for claim in claims:
            claim_tokens = set(re.findall(r"[a-z0-9]+", claim.lower()))
            if not claim_tokens:
                continue
            overlap = len(claim_tokens & context_tokens) / len(claim_tokens)
            claim_scores.append(overlap)
            if overlap < 0.25:
                failed.append(claim)

        avg_overlap = sum(claim_scores) / max(len(claim_scores), 1)
        # Never manufacture factual entailment without neural NLI verification
        is_entailed = False
        verdict = "UNKNOWN"

        return EntailmentResult(is_entailed=is_entailed, score=avg_overlap, verdict=verdict, failed_claims=failed)

def verify_entailment(answer: str, chunks: List[Dict[str, Any]]) -> Tuple[bool, float]:
    verifier = EntailmentVerifier()
    res = verifier.verify(answer, chunks)
    return res.is_entailed, res.score
