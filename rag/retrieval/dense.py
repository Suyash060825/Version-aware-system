from typing import List, Dict
from rag.vectordb.chroma import get_store
from rag.embeddings.embedder import get_embedder

class DenseRetriever:
    def __init__(self):
        self.store = get_store()
        self.embedder = get_embedder()

    def search(self, query: str, filters: dict = None, top_k: int = 50, query_embedding: List[float] = None) -> List[Dict]:
        if query_embedding is None:
            query_embedding = self.embedder.embed_query(query)
        # Filters should be normalized by whoever calls this
        try:
            results = self.store.search(
                embedding=query_embedding,
                filters=filters or {},
                top_k=top_k
            )
            return results
        except Exception as e:
            import logging
            logging.getLogger("rag.retrieval.dense").warning(f"DenseRetriever search error: {e}")
            return []
