"""
rag/embeddings/embedder.py
Configurable, hardware-aware embedding provider with CPU/CUDA device support.
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import List

logger = logging.getLogger(__name__)

def _get_target_device(env_var: str = "EMBEDDING_DEVICE") -> str:
    device = os.environ.get(env_var)
    if device:
        return device
    import sys
    if sys.version_info >= (3, 14):
        return "cpu"
    import torch
    if torch.cuda.is_available():
        # Check if CUDA actually works for simple ops or if triton fails
        try:
            torch.zeros(1).cuda()
            return "cuda"
        except Exception:
            return "cpu"
    return "cpu"

def _validate_vector(vec: List[float], expected_dim: int) -> List[float]:
    import math
    if not vec or len(vec) != expected_dim:
        raise ValueError(f"Vector dimension mismatch: got {len(vec) if vec else 0}, expected {expected_dim}")
    for x in vec:
        if not math.isfinite(x):
            raise ValueError("Vector contains non-finite values (NaN or Inf)")
    return vec

class BaseEmbedder(ABC):
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        pass
    
    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        pass

class SentenceTransformerEmbedder(BaseEmbedder):
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        self.device = _get_target_device("EMBEDDING_DEVICE")
        try:
            self._model = SentenceTransformer(model_name, device=self.device)
        except Exception as e:
            logger.warning(f"Failed to load {model_name} on {self.device}: {e}. Falling back to CPU.")
            self.device = "cpu"
            self._model = SentenceTransformer(model_name, device="cpu")
        self.dimension = self._model.get_sentence_embedding_dimension()
        
    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        batch_size = int(os.environ.get("EMBEDDING_BATCH_SIZE", "64"))
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = [t if (t and t.strip()) else "empty" for t in texts[i:i + batch_size]]
            batch_vecs = self._model.encode(batch, normalize_embeddings=True, show_progress_bar=False).tolist()
            for v in batch_vecs:
                all_embeddings.append(_validate_vector(v, self.dimension))
        return all_embeddings
        
    def embed_query(self, query: str) -> List[float]:
        q = (query or "").strip() or "empty"
        vec = self._model.encode(q, normalize_embeddings=True, show_progress_bar=False).tolist()
        return _validate_vector(vec, self.dimension)

class Qwen3Embedder(BaseEmbedder):
    def __init__(self, model_name: str = "Qwen/Qwen3-Embedding-0.6B"):
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        self.device = _get_target_device("EMBEDDING_DEVICE")
        try:
            self._model = SentenceTransformer(model_name, device=self.device)
        except Exception as e:
            logger.warning(f"Failed to load {model_name} on {self.device}: {e}. Falling back to CPU.")
            self.device = "cpu"
            self._model = SentenceTransformer(model_name, device="cpu")
        if hasattr(self._model, "get_embedding_dimension"):
            self.dimension = self._model.get_embedding_dimension()
        else:
            self.dimension = self._model.get_sentence_embedding_dimension()
        
    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        batch_size = int(os.environ.get("EMBEDDING_BATCH_SIZE", "64"))
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = [t if (t and t.strip()) else "empty" for t in texts[i:i + batch_size]]
            batch_vecs = self._model.encode(batch, normalize_embeddings=True, show_progress_bar=False).tolist()
            for v in batch_vecs:
                all_embeddings.append(_validate_vector(v, self.dimension))
        return all_embeddings
        
    def embed_query(self, query: str) -> List[float]:
        q = (query or "").strip() or "empty"
        try:
            vec = self._model.encode(q, prompt_name="query", normalize_embeddings=True).tolist()
        except Exception:
            vec = self._model.encode(q, normalize_embeddings=True).tolist()
        return _validate_vector(vec, self.dimension)

class FastEmbedEmbedder(BaseEmbedder):
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model_name = model_name
        self.dimension = 384
        try:
            from fastembed import TextEmbedding
            self._model = TextEmbedding(model_name=model_name)
            logger.info(f"Loaded FastEmbed ONNX model: {model_name}")
        except Exception as e:
            logger.warning(f"FastEmbed load failed: {e}. Falling back to SentenceTransformer.")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(model_name, device="cpu")
            self.dimension = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        batch_size = int(os.environ.get("EMBEDDING_BATCH_SIZE", "64"))
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = [t if (t and t.strip()) else "empty" for t in texts[i:i + batch_size]]
            if hasattr(self._model, "embed"):
                batch_vecs = [v.tolist() for v in self._model.embed(batch)]
            else:
                batch_vecs = self._model.encode(batch, normalize_embeddings=True, show_progress_bar=False).tolist()
            for v in batch_vecs:
                all_embeddings.append(_validate_vector(v, self.dimension))
        return all_embeddings

    def embed_query(self, query: str) -> List[float]:
        q = (query or "").strip() or "empty"
        if hasattr(self._model, "embed"):
            embeddings = list(self._model.embed([q]))
            vec = embeddings[0].tolist() if embeddings else []
        else:
            vec = self._model.encode(q, normalize_embeddings=True, show_progress_bar=False).tolist()
        return _validate_vector(vec, self.dimension)

_EMBEDDER = None

def get_embedder() -> BaseEmbedder:
    global _EMBEDDER
    if _EMBEDDER is None:
        engine = os.environ.get("EMBEDDING_ENGINE", "fastembed").lower()
        model = os.environ.get("EMBEDDING_MODEL", os.environ.get("FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5"))
        
        if engine in ("fastembed", "auto"):
            _EMBEDDER = FastEmbedEmbedder(model)
        elif "qwen" in model.lower():
            _EMBEDDER = Qwen3Embedder(model)
        else:
            _EMBEDDER = SentenceTransformerEmbedder(model)
    return _EMBEDDER
