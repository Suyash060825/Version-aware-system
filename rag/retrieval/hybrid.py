"""
rag/retrieval/hybrid.py
Hybrid Dense + BM25 retrieval with calibrated Reciprocal Rank Fusion (RRF).
"""
from typing import List, Dict, Any
from rag.retrieval.dense import DenseRetriever
from rag.retrieval.sparse import PersistentBM25Index

class HybridRetriever:
    def __init__(self):
        self.dense = DenseRetriever()
        self.sparse = PersistentBM25Index()

    def search(self, query: str, filters: dict = None, top_k: int = 25, query_embedding: List[float] = None) -> List[Dict[str, Any]]:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=2) as executor:
            fut_dense = executor.submit(self.dense.search, query, filters, top_k=top_k, query_embedding=query_embedding)
            fut_sparse = executor.submit(self.sparse.get_scores, query, filters)
            dense_results = fut_dense.result()
            sparse_results = fut_sparse.result()
        
        # Adaptive RRF Fusion parameterization:
        # For concise keyword-heavy queries (<4 words), weight BM25 exact matches higher (K=30)
        # For natural conversational queries, standard K=60 balances semantic and lexical signals
        q_tokens = [t for t in query.strip().split() if len(t) > 1]
        K = 30 if len(q_tokens) <= 3 else 60
        combined = {}
        
        for i, doc in enumerate(dense_results):
            doc_id = doc.get("chunk_id") or doc.get("id")
            combined[doc_id] = {
                "doc": doc,
                "score": 1.0 / (K + i + 1),
                "dense_rank": i + 1,
                "sparse_rank": None
            }
            
        for i, (doc_id, score, doc) in enumerate(sparse_results[:top_k]):
            if doc_id in combined:
                combined[doc_id]["score"] += 1.0 / (K + i + 1)
                combined[doc_id]["sparse_rank"] = i + 1
            else:
                combined[doc_id] = {
                    "doc": doc,
                    "score": 1.0 / (K + i + 1),
                    "dense_rank": None,
                    "sparse_rank": i + 1
                }
                
        # Sort by RRF score
        fused = sorted(combined.values(), key=lambda x: x["score"], reverse=True)
        
        # Normalize fusion score to 0..1 range (max theoretical RRF score = 2 / (K + 1) ≈ 0.0328)
        max_possible_rrf = 2.0 / (K + 1)
        final_results = []
        for item in fused[:top_k]:
            doc = dict(item["doc"])
            normalized_score = min(1.0, item["score"] / max_possible_rrf)
            doc["hybrid_score"] = float(normalized_score)
            doc["raw_rrf_score"] = float(item["score"])
            final_results.append(doc)
            
        return final_results
