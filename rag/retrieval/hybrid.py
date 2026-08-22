from typing import List, Dict
from rag.retrieval.dense import DenseRetriever
from rag.retrieval.sparse import PersistentBM25Index

class HybridRetriever:
    def __init__(self):
        self.dense = DenseRetriever()
        self.sparse = PersistentBM25Index()

    def search(self, query: str, filters: dict = None, top_k: int = 50) -> List[Dict]:
        dense_results = self.dense.search(query, filters, top_k)
        sparse_results = self.sparse.get_scores(query, filters)
        
        # RRF Fusion
        K = 60
        combined = {}
        
        for i, doc in enumerate(dense_results):
            doc_id = doc["id"]
            combined[doc_id] = {"doc": doc, "score": 1.0 / (K + i + 1)}
            
        for i, (doc_id, score, doc) in enumerate(sparse_results[:top_k]):
            if doc_id in combined:
                combined[doc_id]["score"] += 1.0 / (K + i + 1)
            else:
                combined[doc_id] = {"doc": doc, "score": 1.0 / (K + i + 1)}
                
        # Sort by RRF score
        fused = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
        
        # Format results
        final_results = []
        for item in fused[:top_k]:
            doc = item["doc"]
            doc["hybrid_score"] = item["score"]
            final_results.append(doc)
            
        return final_results
