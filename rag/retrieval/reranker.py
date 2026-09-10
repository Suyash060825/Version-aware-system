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
            # Score top candidates to keep CPU latency low
            eval_candidates = candidates[:min(len(candidates), 16)]
            pairs = [(query, c.get("text", "")) for c in eval_candidates]
            scores = self._model.predict(pairs)
            
            ranked = sorted(zip(scores, eval_candidates), reverse=True, key=lambda x: x[0])
            
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

class FlashRankReranker:
    def __init__(self, model_name: str = "ms-marco-TinyBERT-L-2-v2"):
        self.model_name = model_name
        try:
            from flashrank import Ranker, RerankRequest
            self._ranker = Ranker(model_name=model_name)
            self._rerank_request_cls = RerankRequest
            logger.info(f"Loaded FlashRank ONNX Reranker: {model_name}")
        except Exception as e:
            logger.warning(f"FlashRank load failed: {e}. Falling back to Qwen3 / CrossEncoder.")
            self._ranker = None

    def rank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 8) -> List[Dict[str, Any]]:
        if not candidates:
            return []
        if not self._ranker:
            return candidates[:top_k]
        try:
            passages = [{"id": i, "text": c.get("text", "")} for i, c in enumerate(candidates)]
            req = self._rerank_request_cls(query=query, passages=passages)
            ranked_passages = self._ranker.rerank(req)
            
            results = []
            for item in ranked_passages[:top_k]:
                idx = item["id"]
                c_copy = dict(candidates[idx])
                c_copy["rerank_score"] = float(item["score"])
                results.append(c_copy)
            return results
        except Exception as e:
            logger.error(f"Error in FlashRank reranking: {e}")
            return candidates[:top_k]

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 8) -> List[Dict[str, Any]]:
        return self.rank(query, candidates, top_k=top_k)

class MockReranker:
    def rank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 8) -> List[Dict[str, Any]]:
        return candidates[:top_k]

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 8) -> List[Dict[str, Any]]:
        return candidates[:top_k]

_RERANKER = None

def get_reranker():
    global _RERANKER
    if _RERANKER is None:
        mode = os.environ.get("RERANKER_MODE", "real").lower()
        engine = os.environ.get("RERANKER_ENGINE", "flashrank").lower()
        model = os.environ.get("RERANKER_MODEL", "ms-marco-TinyBERT-L-2-v2")
        if mode == "mock":
            _RERANKER = MockReranker()
        elif engine in ("flashrank", "auto"):
            try:
                _RERANKER = FlashRankReranker(os.environ.get("FLASHRANK_MODEL", model))
                if _RERANKER._ranker is None:
                    _RERANKER = Qwen3Reranker()
            except Exception:
                _RERANKER = Qwen3Reranker()
        else:
            _RERANKER = Qwen3Reranker()
    return _RERANKER
