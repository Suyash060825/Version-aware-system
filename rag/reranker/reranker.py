import os
from typing import List, Dict

class Qwen3Reranker:
    """
    Qwen3-Reranker-0.6B via CrossEncoder.
    Run AFTER metadata filtering and fusion, not on full corpus.
    """
    MODEL_NAME = "Qwen/Qwen3-Reranker-0.6B"
    
    def __init__(self):
        from sentence_transformers import CrossEncoder
        self._model = CrossEncoder(self.MODEL_NAME)
    
    def rank(self, query: str, candidates: List[dict], top_k: int = 8) -> List[dict]:
        """Reranks top-N candidates from BM25+dense to top-K."""
        if not candidates:
            return []
            
        pairs = [(query, c.get("text", "")) for c in candidates]
        scores = self._model.predict(pairs)
        
        ranked = sorted(zip(scores, candidates), reverse=True, key=lambda x: x[0])
        
        results = []
        for s, c in ranked[:top_k]:
            c_copy = dict(c)
            c_copy["rerank_score"] = float(s)
            results.append(c_copy)
            
        return results

class MockReranker:
    def rank(self, query: str, candidates: List[dict], top_k: int = 8) -> List[dict]:
        return candidates[:top_k]

_RERANKER = None

def get_reranker():
    global _RERANKER
    if _RERANKER is None:
        model = os.environ.get("RERANKER_MODEL", "mock")
        if "Qwen" in model:
            _RERANKER = Qwen3Reranker()
        else:
            _RERANKER = MockReranker()
    return _RERANKER
