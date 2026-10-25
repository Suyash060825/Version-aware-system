"""
rag/entailment.py
Entailment-based grounding check for RAG responses.
"""
import re
import os

ENTAILMENT_ENABLED = os.environ.get('ENTAILMENT_ENABLED', 'false').lower() == 'true'

_nli_model = None
_use_nli = True

def get_nli_model():
    global _nli_model, _use_nli
    if _nli_model is None and _use_nli:
        try:
            from sentence_transformers import CrossEncoder
            # Lightweight NLI model
            _nli_model = CrossEncoder("cross-encoder/nli-deberta-v3-base")
        except Exception as e:
            print(f"[Entailment] Failed to load NLI model, falling back to lexical overlap: {e}")
            _use_nli = False
    return _nli_model

def split_into_claims(text: str) -> list[str]:
    """Split text into sentence claims, stripping citations."""
    text = re.sub(r'\[Policy:[^\]]+\]', '', text)
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 10]

def verify_entailment(answer: str, chunks: list[dict]) -> tuple[bool, float]:
    """
    Verify if claims in answer are entailed by the provided chunks.
    Returns (is_entailed, groundedness_score).
    """
    if not ENTAILMENT_ENABLED:
        return True, 1.0
    if not answer or not chunks:
        return False, 0.0
        
    claims = split_into_claims(answer)
    if not claims:
        return True, 1.0
        
    context = " ".join([c.get("text", "") for c in chunks])
    
    nli = get_nli_model()
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
            c_clean = claim.lower().strip()
            chunk_clean = best_chunk_text.lower()
            if c_clean in chunk_clean or (len(c_clean) > 25 and (c_clean[:35] in chunk_clean and c_clean[-20:] in chunk_clean)):
                claim_scores[i] = 1.0
                continue

            # 2. High-fidelity lexical grounding check
            if claim_tokens:
                chunk_tokens = set(re.findall(r"[a-z0-9]+", chunk_clean))
                tok_overlap = len(claim_tokens & chunk_tokens) / len(claim_tokens)
                claim_nums = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", claim))
                chunk_nums = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", best_chunk_text))
                unsupported_nums = claim_nums - chunk_nums
                claim_has_neg = bool(claim_tokens & negations)
                chunk_has_neg = bool(chunk_tokens & negations)
                if tok_overlap >= 0.85 and not unsupported_nums and (claim_has_neg == chunk_has_neg):
                    claim_scores[i] = 0.95
                    continue

            pairs_to_predict.append((i, best_chunk_text, claim))

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
                entailment_idx = label2id.get('entailment', 2)
                
                if len(probs.shape) > 1:
                    e_scores = probs[:, entailment_idx]
                else:
                    e_scores = np.array([probs[entailment_idx]])

                for (idx, _, _), es in zip(pairs_to_predict, e_scores):
                    claim_scores[idx] = float(es)
            except Exception as e:
                print(f"[Entailment] Error in NLI predict: {e}")

        entail_vals = [cs for cs in claim_scores if cs is not None]
        if len(entail_vals) == len(claims):
            avg_score = float(sum(entail_vals) / max(len(entail_vals), 1))
            return avg_score > 0.35, avg_score

    # Lexical overlap heuristic fallback
    context_tokens = set(re.findall(r"[a-z0-9]+", context.lower()))
    claim_scores = []
    
    for claim in claims:
        claim_tokens = set(re.findall(r"[a-z0-9]+", claim.lower()))
        if not claim_tokens:
            continue
        overlap = len(claim_tokens & context_tokens) / len(claim_tokens)
        claim_scores.append(overlap)
        
    avg_overlap = sum(claim_scores) / max(len(claim_scores), 1)
    # Require 30% lexical overlap for entailment
    return avg_overlap >= 0.3, avg_overlap
