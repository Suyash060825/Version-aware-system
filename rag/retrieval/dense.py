from typing import List, Dict
from rag.vectordb.chroma import get_store
from rag.embeddings.embedder import get_embedder

class DenseRetriever:
    def __init__(self):
        self.store = get_store()
        self.embedder = get_embedder()

    def search(self, query: str, filters: dict = None, top_k: int = 50) -> List[Dict]:
        query_embedding = self.embedder.embed_query(query)
        # Filters should be normalized by whoever calls this
        results = self.store.search(
            embedding=query_embedding,
            filters=filters or {},
            top_k=top_k
        )
        return results
