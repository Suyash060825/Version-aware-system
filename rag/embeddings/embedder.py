import os
import logging
from abc import ABC, abstractmethod
from typing import List

logger = logging.getLogger(__name__)

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
        self._model = SentenceTransformer(model_name)
        self.dimension = self._model.get_sentence_embedding_dimension()
        
    def embed(self, texts: List[str]) -> List[List[float]]:
        return self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()
        
    def embed_query(self, query: str) -> List[float]:
        return self._model.encode(query, normalize_embeddings=True, show_progress_bar=False).tolist()

class Qwen3Embedder(BaseEmbedder):
    def __init__(self, model_name: str = "Qwen/Qwen3-Embedding-0.6B"):
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self.dimension = self._model.get_sentence_embedding_dimension()
        
    def embed(self, texts: List[str]) -> List[List[float]]:
        return self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()
        
    def embed_query(self, query: str) -> List[float]:
        return self._model.encode(query, prompt_name="query", normalize_embeddings=True).tolist()

_EMBEDDER = None

def get_embedder() -> BaseEmbedder:
    global _EMBEDDER
    if _EMBEDDER is None:
        model = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        if "Qwen" in model:
            _EMBEDDER = Qwen3Embedder(model)
        else:
            _EMBEDDER = SentenceTransformerEmbedder(model)
    return _EMBEDDER
