"""
rag/retrieval/sparse.py
Persistent BM25 sparse keyword retriever with partition filtering and revision tracking.
"""
import pickle
import os
import logging
from typing import List, Tuple, Dict, Any
from rank_bm25 import BM25Okapi
from models import PolicyChunkV2

logger = logging.getLogger("rag.retrieval.sparse")

class PersistentBM25Index:
    INDEX_PATH = "data/bm25_index.pkl"
    
    def __init__(self):
        self._bm25 = None
        self._corpus: List[Dict[str, Any]] = []
        self._revision = 0
        self.load()

    def load(self):
        if os.path.exists(self.INDEX_PATH):
            try:
                with open(self.INDEX_PATH, 'rb') as f:
                    data = pickle.load(f)
                    self._bm25 = data['bm25']
                    self._corpus = data['corpus']
                    self._revision = data.get('revision', 0)
                logger.info(f"Loaded persistent BM25 index with {len(self._corpus)} documents (revision {self._revision})")
                return
            except Exception as e:
                logger.error(f"Failed to load BM25 index from {self.INDEX_PATH}: {e}. Rebuilding...")
        self.rebuild_from_db()

    def rebuild_from_db(self):
        try:
            chunks = PolicyChunkV2.query.all()
            if not chunks:
                return
                
            corpus = []
            tokenized_corpus = []
            for chunk in chunks:
                tokens = chunk.text.lower().split()
                tokenized_corpus.append(tokens)
                corpus.append({
                    "id": chunk.chunk_id,
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "policy_id": chunk.policy_id,
                    "version_id": chunk.version_id,
                    "version": str(chunk.version_id),
                    "section": chunk.section_path or "General",
                    "section_path": chunk.section_path or "General",
                    "page": chunk.page or 1
                })
                
            self._bm25 = BM25Okapi(tokenized_corpus)
            self._corpus = corpus
            self._revision += 1
            
            os.makedirs(os.path.dirname(self.INDEX_PATH), exist_ok=True)
            with open(self.INDEX_PATH, 'wb') as f:
                pickle.dump({
                    'bm25': self._bm25,
                    'corpus': self._corpus,
                    'revision': self._revision
                }, f)
            logger.info(f"Rebuilt BM25 index with {len(corpus)} chunks to {self.INDEX_PATH}")
        except Exception as e:
            logger.error(f"Failed to rebuild BM25 from DB: {e}")

    def get_scores(self, query: str, filters: dict = None) -> List[Tuple[str, float, dict]]:
        if not self._bm25 or not self._corpus:
            self.load()
        if not self._bm25 or not self._corpus:
            return []
            
        tokenized_query = query.lower().split()
        doc_scores = self._bm25.get_scores(tokenized_query)
        
        results = []
        for i, score in enumerate(doc_scores):
            if score > 0:
                doc = self._corpus[i]
                
                # Apply metadata filters
                if filters:
                    match = True
                    for k, v in filters.items():
                        if str(doc.get(k)) != str(v):
                            match = False
                            break
                    if not match:
                        continue
                        
                results.append((doc["id"], float(score), doc))
                
        return sorted(results, key=lambda x: x[1], reverse=True)
        
    @property
    def revision(self) -> int:
        return self._revision
