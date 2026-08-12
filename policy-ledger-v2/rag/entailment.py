"""
rag/entailment.py
Entailment-based grounding check for RAG responses.
"""
import re

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
    if not answer or not chunks:
        return False, 0.0
        
    claims = split_into_claims(answer)
    if not claims:
        return True, 1.0
        
    context = " ".join([c.get("text", "") for c in chunks])
    
    nli = get_nli_model()
    if nli:
        # CrossEncoder NLI models typically return logits for [contradiction, entailment, neutral]
        # or [contradiction, neutral, entailment] depending on the model.
        # cross-encoder/nli-deberta-v3-base outputs: [Contradiction, Entailment, Neutral]
        pairs = [(context, claim) for claim in claims]
        try:
            scores = nli.predict(pairs)
            entailment_scores = scores[:, 1] if len(scores.shape) > 1 else scores
            
            # Require average entailment > 0.5
            avg_score = float(entailment_scores.mean())
            return avg_score > 0.5, avg_score
        except Exception:
            pass # Fallback

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
    # Require 40% lexical overlap for entailment
    return avg_overlap >= 0.4, avg_overlap
