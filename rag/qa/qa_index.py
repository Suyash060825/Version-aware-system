import numpy as np
from typing import List, Tuple
from models import CanonicalQuestion, db

class CanonicalQAIndex:
    """
    Fast ANN search over precomputed question embeddings.
    Backed by numpy.
    Loaded from DB on startup, refreshed when new compilation completes.
    """
    def __init__(self):
        self._questions = []
        self._embeddings = None
        self._answer_ids = []
        self._revision = 0
        self._is_loaded = False
        
    def load(self):
        # We need an app context to query the DB
        try:
            questions = CanonicalQuestion.query.all()
            if not questions:
                return
                
            self._questions = []
            self._answer_ids = []
            
            # Reconstruct embeddings. In a real app, embeddings for canonical questions 
            # should be stored in the DB. For simplicity, we just rebuild them here.
            from rag.embeddings.embedder import get_embedder
            embedder = get_embedder()
            
            valid_qs = [q for q in questions if q.question.strip()]
            if not valid_qs:
                return
                
            texts = [q.question for q in valid_qs]
            emb_list = embedder.embed_query(texts) if len(texts) == 1 else embedder.embed(texts)
            
            self._questions = texts
            self._embeddings = np.array(emb_list)
            # Link back to CompiledAnswer. For simplicity, assume 1:1 mapping via question_id.
            from models import CompiledAnswer
            # We map question_id -> compiled answer
            answers = CompiledAnswer.query.all()
            ans_map = {a.question_id: a.id for a in answers}
            self._answer_ids = [ans_map.get(q.id) for q in valid_qs]
            
            self._is_loaded = True
        except Exception as e:
            pass # DB might not be initialized
            
    def search(self, query_embedding: List[float], top_k: int = 3) -> List[Tuple[float, int]]:
        """Returns [(score, answer_id), ...]"""
        if not self._is_loaded or self._embeddings is None:
            self.load()
            
        if self._embeddings is None or len(self._embeddings) == 0:
            return []
            
        q = np.array(query_embedding)
        # Cosine similarity (assuming normalized embeddings)
        scores = self._embeddings @ q
        
        # Get top K
        top_k = min(top_k, len(scores))
        top_indices = np.argsort(scores)[-top_k:][::-1]
        
        results = []
        for i in top_indices:
            ans_id = self._answer_ids[i]
            if ans_id is not None:
                results.append((float(scores[i]), ans_id))
        return results
