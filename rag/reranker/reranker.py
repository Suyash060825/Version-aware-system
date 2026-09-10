"""
rag/retrieval/reranker.py
CrossEncoder reranker with device control and CPU fallback.
"""
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger("rag.retrieval.reranker")

def _get_target_device(env_var: str = "RERANKER_DEVICE") -> str:
    device = os.environ.get(env_var)
    if device:
        return device
    import sys
    if sys.version_info >= (3, 14):
        return "cpu"
    import torch
    if torch.cuda.is_available():
        try:
            torch.zeros(1).cuda()
            return "cuda"
        except Exception:
            return "cpu"
    return "cpu"

class Qwen3Reranker:
    MODEL_NAME = "Qwen/Qwen3-Reranker-0.6B"
    
    def __init__(self):
        self.device = _get_target_device("RERANKER_DEVICE")
        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.MODEL_NAME, device=self.device)
            logger.info(f"Loaded CrossEncoder {self.MODEL_NAME} on {self.device}")
        except Exception as e:
            logger.warning(f"Failed to load CrossEncoder {self.MODEL_NAME} on {self.device}: {e}. Retrying on CPU.")
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.MODEL_NAME, device="cpu")
                self.device = "cpu"
            except Exception as e2:
                logger.error(f"Failed to load CrossEncoder on CPU: {e2}. Pass-through enabled.")
                self._model = None

    def rank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 8) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        if not self._model:
            return candidates[:top_k]

        try:
            pairs = [(query, c.get("text", "")) for c in candidates]
            scores = self._model.predict(pairs)
            
            ranked = sorted(zip(scores, candidates), reverse=True, key=lambda x: x[0])
            
            results = []
            for s, c in ranked[:top_k]:
                c_copy = dict(c)
                c_copy["rerank_score"] = float(s)
                results.append(c_copy)
            return results
        except Exception as e:
            logger.error(f"Error in reranking: {e}")
            return candidates[:top_k]

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 8) -> List[Dict[str, Any]]:
        return self.rank(query, candidates, top_k=top_k)

class MockReranker:
    def rank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 8) -> List[Dict[str, Any]]:
        return candidates[:top_k]

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 8) -> List[Dict[str, Any]]:
        return candidates[:top_k]

from rag.retrieval.reranker import get_reranker, Qwen3Reranker, FlashRankReranker, MockReranker
